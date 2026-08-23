"""Datenmodelle fuer Notifications und Ereignisse.

Dieses Modul enthaelt bewusst keine Home-Assistant-Importe. Es beschreibt
ausschliesslich die Domaene und ist damit ohne HA-Runtime testbar.

Zeiten werden intern immer als zeitzonenbewusste UTC-Zeitstempel gefuehrt
(Spezifikation 36). Die Umrechnung in die Home-Assistant-Zeitzone passiert
erst bei der Darstellung.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ..const import MODEL_SCHEMA_VERSION


class NotificationType(StrEnum):
    """Schweregrad einer Notification."""

    INFO = "info"
    WARNING = "warning"
    ALARM = "alarm"

    @property
    def severity(self) -> int:
        """Numerische Rangfolge fuer Eskalationsvergleiche."""
        return _SEVERITY[self]


_SEVERITY: dict[NotificationType, int] = {
    NotificationType.INFO: 1,
    NotificationType.WARNING: 2,
    NotificationType.ALARM: 3,
}


class NotificationSource(StrEnum):
    """Herkunft einer Notification."""

    ENTITY_RULE = "entity_rule"
    AUTOMATION = "automation"


class CloseReason(StrEnum):
    """Grund fuer das Beenden einer Notification.

    Wird fuer Diagnose und Tests gefuehrt, nicht im Dashboard angezeigt.
    """

    CONDITION_CLEARED = "condition_cleared"
    ESCALATED = "escalated"
    DEESCALATED = "deescalated"
    RULE_DISABLED = "rule_disabled"
    ENTITY_REMOVED = "entity_removed"
    ENTITY_REPLACED = "entity_replaced"
    DISMISSED = "dismissed"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


def utc_now() -> datetime:
    """Aktuelle UTC-Zeit. Eigene Funktion, damit Tests sie ersetzen koennen."""
    return datetime.now(UTC)


def new_event_id() -> str:
    """Erzeugt eine neue Event-ID."""
    return uuid.uuid4().hex


@dataclass(slots=True)
class NotificationEvent:
    """Ein Ereignis im Event Store (Spezifikation 32).

    Ein Ereignis wird beim Auftreten sofort mit ``active=True`` gespeichert und
    beim Ende **derselbe** Datensatz aktualisiert. Es gibt bewusst keine
    getrennten Start- und End-Datensaetze (Spezifikation 31).
    """

    message: str
    type: NotificationType
    source: NotificationSource
    start_time: datetime

    event_id: str = field(default_factory=new_event_id)
    end_time: datetime | None = None
    active: bool = True

    title: str | None = None
    entity_id: str | None = None
    device_id: str | None = None
    area_id: str | None = None

    rule_id: str | None = None
    rule_group_id: str | None = None
    level: int | None = None

    notification_id: str | None = None
    owner: str | None = None

    close_reason: CloseReason | None = None
    schema_version: int = MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.start_time.tzinfo is None:
            raise ValueError("start_time muss zeitzonenbewusst sein")
        if self.end_time is not None and self.end_time.tzinfo is None:
            raise ValueError("end_time muss zeitzonenbewusst sein")

    # -- Dauer ----------------------------------------------------------

    def duration(self, now: datetime | None = None) -> float:
        """Dauer in Sekunden.

        Fuer abgeschlossene Ereignisse die tatsaechliche Laufzeit, fuer aktive
        Ereignisse dynamisch aus ``now - start_time`` (Spezifikation 33).
        """
        end = self.end_time if self.end_time is not None else (now or utc_now())
        return max(0.0, (end - self.start_time).total_seconds())

    # -- Zustandsuebergang ----------------------------------------------

    def close(self, end_time: datetime, reason: CloseReason) -> None:
        """Schliesst das Ereignis ab. Mehrfaches Schliessen ist wirkungslos."""
        if not self.active:
            return
        if end_time < self.start_time:
            end_time = self.start_time
        self.end_time = end_time
        self.active = False
        self.close_reason = reason

    # -- Serialisierung --------------------------------------------------

    def to_dict(self, now: datetime | None = None) -> dict[str, Any]:
        """Darstellung fuer API und Frontend. Zeiten als ISO-8601 in UTC."""
        return {
            "event_id": self.event_id,
            "schema_version": self.schema_version,
            "source": str(self.source),
            "type": str(self.type),
            "active": self.active,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration(now),
            "title": self.title,
            "message": self.message,
            "entity_id": self.entity_id,
            "device_id": self.device_id,
            "area_id": self.area_id,
            "rule_id": self.rule_id,
            "rule_group_id": self.rule_group_id,
            "level": self.level,
            "notification_id": self.notification_id,
            "owner": self.owner,
        }


def automation_key(owner: str, notification_id: str) -> str:
    """Eindeutiger Schluessel einer Automations-Notification.

    Owner und ID zusammen sind eindeutig; zwei Owner duerfen dieselbe ID
    verwenden, ohne sich zu beeinflussen (Spezifikation 25).
    """
    return f"{owner}\x1f{notification_id}"
