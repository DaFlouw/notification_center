"""Persistenter Event Store auf Basis einer lokalen SQLite-Datei.

Bewusste Entscheidungen:

* **Eigene SQLite-Datei** statt des Home-Assistant-Storage-Helpers. Der Store
  haelt seinen Inhalt vollstaendig im Arbeitsspeicher und schreibt bei jeder
  Aenderung die komplette Datei neu; bei bis zu 50.000 Ereignissen mit
  serverseitigem Filtern, Suchen, Sortieren, Paginieren und Cleanup
  (Spezifikation 48, 49, 61, 83) ist das nicht tragbar. Es handelt sich um
  eine Datei im Konfigurationsverzeichnis, nicht um eine externe Datenbank:
  kein Server, kein Dienst, vom Home-Assistant-Backup abgedeckt.
* **Getrennt von der Recorder-Datenbank**, damit weder Purge-Logik noch
  Schemaaenderungen von Home Assistant hineinwirken.
* **Synchron und ohne Home-Assistant-Importe.** Der Aufrufer fuehrt die
  Methoden im Executor aus. Dadurch bleibt der Store ohne HA-Runtime testbar.

Zeiten werden als UTC-Epoch (REAL) gespeichert: kompakt, sortierbar und ohne
Zeitzonen-Mehrdeutigkeit. Fuer die Volltextsuche existiert eine vorab
kleingeschriebene Spalte, weil SQLites LIKE nur ASCII korrekt kleinschreibt
und deutsche Umlaute sonst durchfallen.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..const import DEFAULT_PAGE_SIZE, EVENT_DB_SCHEMA_VERSION, MAX_PAGE_SIZE
from ..notifications.models import (
    CloseReason,
    NotificationEvent,
    NotificationSource,
    NotificationType,
    utc_now,
)

_LOGGER = logging.getLogger(__name__)

_COLUMNS = (
    "event_id",
    "schema_version",
    "source",
    "type",
    "active",
    "start_time",
    "end_time",
    "title",
    "message",
    "search_text",
    "entity_id",
    "device_id",
    "area_id",
    "rule_id",
    "rule_group_id",
    "level",
    "notification_id",
    "owner",
    "close_reason",
)

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS events (
    event_id        TEXT PRIMARY KEY,
    schema_version  INTEGER NOT NULL,
    source          TEXT    NOT NULL,
    type            TEXT    NOT NULL,
    active          INTEGER NOT NULL,
    start_time      REAL    NOT NULL,
    end_time        REAL,
    title           TEXT,
    message         TEXT    NOT NULL,
    search_text     TEXT    NOT NULL,
    entity_id       TEXT,
    device_id       TEXT,
    area_id         TEXT,
    rule_id         TEXT,
    rule_group_id   TEXT,
    level           INTEGER,
    notification_id TEXT,
    owner           TEXT,
    close_reason    TEXT
);

-- Standardsortierung der Historie: neueste zuerst (Spezifikation 34).
CREATE INDEX IF NOT EXISTS idx_events_start
    ON events (start_time DESC);

-- Wiederherstellung nach Neustart liest nur die aktiven Ereignisse.
CREATE INDEX IF NOT EXISTS idx_events_active
    ON events (start_time DESC) WHERE active = 1;

CREATE INDEX IF NOT EXISTS idx_events_type
    ON events (type, start_time DESC);

CREATE INDEX IF NOT EXISTS idx_events_entity
    ON events (entity_id, start_time DESC);

CREATE INDEX IF NOT EXISTS idx_events_source
    ON events (source, start_time DESC);

CREATE INDEX IF NOT EXISTS idx_events_area
    ON events (area_id, start_time DESC);

-- Owner und notification_id sind zusammen eindeutig (Spezifikation 25).
CREATE INDEX IF NOT EXISTS idx_events_owner
    ON events (owner, notification_id) WHERE source = 'automation';
"""


def _to_epoch(value: datetime | None) -> float | None:
    if value is None:
        return None
    return value.timestamp()


def _from_epoch(value: float | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, UTC)


def _search_text(event: NotificationEvent) -> str:
    """Vorab kleingeschriebenes Suchfeld (Spezifikation 60)."""
    parts = [event.message, event.title or "", event.entity_id or "", event.owner or ""]
    return " ".join(parts).lower()


@dataclass(slots=True)
class EventQuery:
    """Serverseitige Filter fuer die Historie (Spezifikation 59 bis 61)."""

    types: Sequence[NotificationType] | None = None
    sources: Sequence[NotificationSource] | None = None
    entity_ids: Sequence[str] | None = None
    device_ids: Sequence[str] | None = None
    area_ids: Sequence[str] | None = None
    search: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    active_only: bool = False
    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0


@dataclass(slots=True)
class EventPage:
    """Ergebnisseite einer Historienabfrage."""

    events: list[NotificationEvent] = field(default_factory=list)
    total: int = 0
    offset: int = 0

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.events) < self.total


class EventStore:
    """Synchroner SQLite-Event-Store.

    Nicht direkt aus dem Event-Loop aufrufen: alle Methoden blockieren und
    gehoeren in den Executor.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    # -- Lebenszyklus ----------------------------------------------------

    def open(self) -> None:
        """Oeffnet die Datenbank und bringt das Schema auf den aktuellen Stand."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL erlaubt Lesen waehrend eines Schreibvorgangs und vermeidet die
        # haeufigen fsyncs des Rollback-Journals.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        self._conn = conn
        self._migrate()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("EventStore wurde nicht geoeffnet")
        return self._conn

    def _migrate(self) -> None:
        """Fuehrt ausstehende Schemamigrationen aus.

        Die Schemaversion steht in ``PRAGMA user_version``. Migrationen werden
        aufsteigend angewendet.
        """
        with self._lock:
            db = self._db
            current = int(db.execute("PRAGMA user_version").fetchone()[0])
            if current > EVENT_DB_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Event-Datenbank hat Schemaversion {current}, unterstuetzt wird "
                    f"hoechstens {EVENT_DB_SCHEMA_VERSION}. Vermutlich wurde die "
                    "Integration heruntergestuft."
                )
            if current < 1:
                db.executescript(_SCHEMA_V1)
                db.execute("PRAGMA user_version=1")
                current = 1
                _LOGGER.debug("Event-Datenbank auf Schemaversion 1 angelegt")
            # Kuenftige Migrationen folgen hier aufsteigend.
            db.commit()

    # -- Schreiben -------------------------------------------------------

    def add(self, event: NotificationEvent) -> None:
        """Speichert ein neues Ereignis. Aktive Ereignisse sind sofort sichtbar."""
        self._upsert(event)

    def update(self, event: NotificationEvent) -> None:
        """Aktualisiert ein bestehendes Ereignis anhand seiner ``event_id``.

        Wird sowohl fuer Zwischenaktualisierungen als auch beim Abschluss
        verwendet: es entsteht kein zweiter Datensatz (Spezifikation 31).
        """
        self._upsert(event)

    def add_all(self, events: Iterable[NotificationEvent]) -> None:
        rows = [self._to_row(event) for event in events]
        if not rows:
            return
        with self._lock:
            self._db.executemany(self._upsert_sql(), rows)
            self._db.commit()

    def _upsert(self, event: NotificationEvent) -> None:
        with self._lock:
            self._db.execute(self._upsert_sql(), self._to_row(event))
            self._db.commit()

    @staticmethod
    def _upsert_sql() -> str:
        placeholders = ", ".join(f":{name}" for name in _COLUMNS)
        assignments = ", ".join(
            f"{name}=excluded.{name}" for name in _COLUMNS if name != "event_id"
        )
        return (
            f"INSERT INTO events ({', '.join(_COLUMNS)}) VALUES ({placeholders}) "
            f"ON CONFLICT(event_id) DO UPDATE SET {assignments}"
        )

    @staticmethod
    def _to_row(event: NotificationEvent) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "schema_version": event.schema_version,
            "source": str(event.source),
            "type": str(event.type),
            "active": 1 if event.active else 0,
            "start_time": _to_epoch(event.start_time),
            "end_time": _to_epoch(event.end_time),
            "title": event.title,
            "message": event.message,
            "search_text": _search_text(event),
            "entity_id": event.entity_id,
            "device_id": event.device_id,
            "area_id": event.area_id,
            "rule_id": event.rule_id,
            "rule_group_id": event.rule_group_id,
            "level": event.level,
            "notification_id": event.notification_id,
            "owner": event.owner,
            "close_reason": str(event.close_reason) if event.close_reason else None,
        }

    @staticmethod
    def _from_row(row: sqlite3.Row) -> NotificationEvent:
        start = _from_epoch(row["start_time"])
        if start is None:
            raise ValueError("Ereignis ohne Startzeit in der Datenbank")
        return NotificationEvent(
            event_id=row["event_id"],
            schema_version=row["schema_version"],
            source=NotificationSource(row["source"]),
            type=NotificationType(row["type"]),
            active=bool(row["active"]),
            start_time=start,
            end_time=_from_epoch(row["end_time"]),
            title=row["title"],
            message=row["message"],
            entity_id=row["entity_id"],
            device_id=row["device_id"],
            area_id=row["area_id"],
            rule_id=row["rule_id"],
            rule_group_id=row["rule_group_id"],
            level=row["level"],
            notification_id=row["notification_id"],
            owner=row["owner"],
            close_reason=CloseReason(row["close_reason"]) if row["close_reason"] else None,
        )

    # -- Lesen -----------------------------------------------------------

    def get(self, event_id: str) -> NotificationEvent | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def active_events(self) -> list[NotificationEvent]:
        """Alle aktiven Ereignisse, neueste zuerst.

        Grundlage der Wiederherstellung nach einem Neustart und der
        Zaehlerrekonstruktion. Nutzt den partiellen Index und liest niemals
        das gesamte Log.
        """
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM events WHERE active = 1 ORDER BY start_time DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def find_automation_event(self, owner: str, notification_id: str) -> NotificationEvent | None:
        """Aktives Ereignis einer Automations-Notification (Owner + ID)."""
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM events WHERE source = ? AND owner = ? AND notification_id = ? "
                "AND active = 1 ORDER BY start_time DESC LIMIT 1",
                (str(NotificationSource.AUTOMATION), owner, notification_id),
            ).fetchone()
        return self._from_row(row) if row else None

    def query(self, query: EventQuery) -> EventPage:
        """Gefilterte, sortierte und seitenweise Historienabfrage."""
        where, params = self._build_where(query)
        clause = f" WHERE {where}" if where else ""

        limit = max(1, min(query.limit, MAX_PAGE_SIZE))
        offset = max(0, query.offset)

        with self._lock:
            total = int(
                self._db.execute(f"SELECT COUNT(*) FROM events{clause}", params).fetchone()[0]
            )
            rows = self._db.execute(
                f"SELECT * FROM events{clause} ORDER BY start_time DESC, event_id DESC "
                "LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()

        return EventPage(
            events=[self._from_row(row) for row in rows],
            total=total,
            offset=offset,
        )

    def count_since(self, since: datetime) -> int:
        """Anzahl Ereignisse ab einem Zeitpunkt, Grundlage fuer 'Ereignisse heute'."""
        with self._lock:
            return int(
                self._db.execute(
                    "SELECT COUNT(*) FROM events WHERE start_time >= ?",
                    (_to_epoch(since),),
                ).fetchone()[0]
            )

    def total_count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    @staticmethod
    def _build_where(query: EventQuery) -> tuple[str, list[Any]]:
        conditions: list[str] = []
        params: list[Any] = []

        def add_in(column: str, values: Sequence[str] | None) -> None:
            if not values:
                return
            placeholders = ", ".join("?" for _ in values)
            conditions.append(f"{column} IN ({placeholders})")
            params.extend(values)

        add_in("type", [str(value) for value in query.types] if query.types else None)
        add_in("source", [str(value) for value in query.sources] if query.sources else None)
        add_in("entity_id", query.entity_ids)
        add_in("device_id", query.device_ids)
        add_in("area_id", query.area_ids)

        if query.active_only:
            conditions.append("active = 1")
        if query.start is not None:
            conditions.append("start_time >= ?")
            params.append(_to_epoch(query.start))
        if query.end is not None:
            conditions.append("start_time < ?")
            params.append(_to_epoch(query.end))
        if query.search:
            term = query.search.lower()
            for special in ("\\", "%", "_"):
                term = term.replace(special, "\\" + special)
            conditions.append("search_text LIKE ? ESCAPE '\\'")
            params.append(f"%{term}%")

        return " AND ".join(conditions), params

    # -- Loeschen --------------------------------------------------------

    def delete(self, event_id: str) -> bool:
        """Loescht ein einzelnes abgeschlossenes Ereignis.

        Aktive Ereignisse werden nicht geloescht: eine laufende Notification
        wuerde sonst ihren Datensatz verlieren.
        """
        with self._lock:
            cursor = self._db.execute(
                "DELETE FROM events WHERE event_id = ? AND active = 0", (event_id,)
            )
            self._db.commit()
            return cursor.rowcount > 0

    def delete_all(self, *, keep_active: bool = True) -> int:
        """Leert das Log. Aktive Ereignisse bleiben standardmaessig erhalten."""
        clause = " WHERE active = 0" if keep_active else ""
        with self._lock:
            cursor = self._db.execute(f"DELETE FROM events{clause}")
            self._db.commit()
            return cursor.rowcount

    def cleanup(
        self,
        *,
        retention_days: int,
        max_events: int,
        now: datetime | None = None,
    ) -> int:
        """Wendet beide Aufbewahrungsgrenzen an (Spezifikation 38).

        ``retention_days=0`` bedeutet unbegrenzt; die Mengengrenze gilt
        trotzdem. Aeltestes zuerst, aktive Ereignisse werden nie entfernt.
        """
        removed = 0
        reference = now or utc_now()

        with self._lock:
            db = self._db
            if retention_days > 0:
                cutoff = reference.timestamp() - retention_days * 86400
                cursor = db.execute(
                    "DELETE FROM events WHERE active = 0 AND start_time < ?", (cutoff,)
                )
                removed += cursor.rowcount

            if max_events > 0:
                total = int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
                surplus = total - max_events
                if surplus > 0:
                    cursor = db.execute(
                        "DELETE FROM events WHERE event_id IN ("
                        "  SELECT event_id FROM events WHERE active = 0"
                        "  ORDER BY start_time ASC LIMIT ?"
                        ")",
                        (surplus,),
                    )
                    removed += cursor.rowcount

            db.commit()

        if removed:
            _LOGGER.debug("Event Store bereinigt: %s Eintraege entfernt", removed)
        return removed

    def vacuum(self) -> None:
        """Gibt Speicher nach groesseren Loeschvorgaengen frei."""
        with self._lock:
            self._db.execute("VACUUM")
