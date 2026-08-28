"""Lebenszyklus der aktiven Notifications und die daraus gepflegten Zaehler.

Ohne Home-Assistant-Importe und damit ohne HA-Runtime testbar.

Der Kern ist eine Menge aktiver Notifications, die nach ihrem Schluessel
adressiert werden. Die Zaehler werden bei jeder Aenderung fortgeschrieben und
nie aus dem Log berechnet (Spezifikation 45, 83): das Log kann 50.000
Eintraege umfassen, die Zahl der aktiven Notifications liegt dagegen im
zweistelligen Bereich.

Nach einem Neustart wird der Zustand aus genau zwei Abfragen rekonstruiert:
den aktiven Ereignissen und der Zahl der heutigen Ereignisse.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import (
    CloseReason,
    NotificationEvent,
    NotificationSource,
    NotificationType,
    automation_key,
)


def rule_key(rule_id: str) -> str:
    """Schluessel einer entity-basierten Notification.

    Je Regel gibt es hoechstens eine aktive Notification. Bei Regelgruppen ist
    das die jeweils hoechste gueltige Stufe; die Stufen sind eigene Regeln und
    damit eigene Schluessel.
    """
    return f"rule:{rule_id}"


def automation_notification_key(owner: str, notification_id: str) -> str:
    return f"auto:{automation_key(owner, notification_id)}"


def key_for(event: NotificationEvent) -> str:
    """Schluessel eines Ereignisses, unabhaengig von seiner Herkunft."""
    if event.source is NotificationSource.AUTOMATION:
        if event.owner is None or event.notification_id is None:
            raise ValueError("Automations-Notification braucht owner und notification_id")
        return automation_notification_key(event.owner, event.notification_id)

    if event.rule_id is None:
        raise ValueError("Entity-Notification braucht eine rule_id")
    return rule_key(event.rule_id)


@dataclass(frozen=True, slots=True)
class Counts:
    """Momentaufnahme der Zaehler (Spezifikation 44)."""

    info: int = 0
    warning: int = 0
    alarm: int = 0
    events_today: int = 0

    @property
    def active(self) -> int:
        return self.info + self.warning + self.alarm

    def to_dict(self) -> dict[str, int]:
        return {
            "info": self.info,
            "warning": self.warning,
            "alarm": self.alarm,
            "active": self.active,
            "events_today": self.events_today,
        }


@dataclass(slots=True)
class ActiveNotifications:
    """Die aktiven Notifications samt fortgeschriebener Zaehler."""

    _by_key: dict[str, NotificationEvent] = field(default_factory=dict)
    _by_type: dict[NotificationType, int] = field(
        default_factory=lambda: dict.fromkeys(NotificationType, 0)
    )
    #: Der Typ, unter dem ein Schluessel gezaehlt wird.
    #:
    #: Bewusst getrennt von ``event.type``: die Aufrufer aendern eine laufende
    #: Notification an Ort und Stelle und reichen dasselbe Objekt herein. Wer
    #: beim Abbuchen ``event.type`` liest, liest dann bereits den neuen Wert
    #: und zieht vom falschen Zaehler ab. Diese Buchfuehrung gehoert hierher
    #: und nicht in die Hand der Aufrufer.
    _type_by_key: dict[str, NotificationType] = field(default_factory=dict)
    _events_today: int = 0
    _day_start: datetime | None = None

    # -- Lesen -----------------------------------------------------------

    def __len__(self) -> int:
        return len(self._by_key)

    def __contains__(self, key: object) -> bool:
        return key in self._by_key

    def get(self, key: str) -> NotificationEvent | None:
        return self._by_key.get(key)

    @property
    def counts(self) -> Counts:
        return Counts(
            info=self._by_type[NotificationType.INFO],
            warning=self._by_type[NotificationType.WARNING],
            alarm=self._by_type[NotificationType.ALARM],
            events_today=self._events_today,
        )

    def events(self) -> list[NotificationEvent]:
        """Aktive Notifications, neueste zuerst (Spezifikation 52)."""
        return sorted(self._by_key.values(), key=lambda e: e.start_time, reverse=True)

    def by_type(self, type: NotificationType) -> list[NotificationEvent]:
        return [event for event in self.events() if event.type is type]

    def keys_for_rules(self, rule_ids: Iterable[str]) -> list[str]:
        """Schluessel der aktiven Notifications bestimmter Regeln."""
        gesucht = {rule_key(rule_id) for rule_id in rule_ids}
        return [key for key in self._by_key if key in gesucht]

    # -- Schreiben -------------------------------------------------------

    def put(self, event: NotificationEvent) -> NotificationEvent | None:
        """Legt eine Notification an oder ersetzt eine bestehende.

        Gibt den vorherigen Stand zurueck, falls es einen gab. Das Ersetzen
        deckt das idempotente ``create`` der Automations-API ab
        (Spezifikation 26): derselbe Owner mit derselben ID ueberschreibt,
        auch mit geaendertem Typ, und erzeugt keinen zweiten Log-Eintrag.
        """
        if not event.active:
            raise ValueError("Nur aktive Ereignisse gehoeren in die aktive Menge")

        key = key_for(event)
        vorher = self._by_key.get(key)

        gezaehlt = self._type_by_key.pop(key, None)
        if gezaehlt is not None:
            self._by_type[gezaehlt] -= 1
        else:
            self._count_new(event)

        self._by_key[key] = event
        self._type_by_key[key] = event.type
        self._by_type[event.type] += 1
        return vorher

    def close(self, key: str, end_time: datetime, reason: CloseReason) -> NotificationEvent | None:
        """Beendet eine Notification. Unbekannte Schluessel sind wirkungslos."""
        event = self._by_key.pop(key, None)
        if event is None:
            return None

        gezaehlt = self._type_by_key.pop(key, event.type)
        self._by_type[gezaehlt] -= 1
        event.close(end_time, reason)
        return event

    def close_all(self, end_time: datetime, reason: CloseReason) -> list[NotificationEvent]:
        geschlossen: list[NotificationEvent] = []
        for key in list(self._by_key):
            event = self.close(key, end_time, reason)
            if event is not None:
                geschlossen.append(event)
        return geschlossen

    # -- Zaehler ---------------------------------------------------------

    def _count_new(self, event: NotificationEvent) -> None:
        """Zaehlt ein neu entstandenes Ereignis fuer den heutigen Tag."""
        if self._day_start is not None and event.start_time >= self._day_start:
            self._events_today += 1

    def note_closed_event(self, event: NotificationEvent) -> None:
        """Zaehlt ein Ereignis, das nie in der aktiven Menge lag.

        Betrifft Automations-Notifications mit Dauer null und Ereignisse, die
        im selben Auswertungsschritt beginnen und enden.
        """
        self._count_new(event)

    def roll_day(self, day_start: datetime, events_today: int = 0) -> None:
        """Setzt den Tageszaehler auf einen neuen Tag.

        Wird um Mitternacht in der Home-Assistant-Zeitzone aufgerufen und beim
        Start mit dem aus der Datenbank ermittelten Wert.
        """
        self._day_start = day_start
        self._events_today = events_today

    # -- Wiederherstellung -----------------------------------------------

    def restore(
        self,
        events: Iterable[NotificationEvent],
        *,
        day_start: datetime,
        events_today: int,
    ) -> None:
        """Stellt den Zustand nach einem Neustart her (Spezifikation 37, 45).

        Die Zaehler ergeben sich aus den wiederhergestellten Notifications und
        einer einzigen Zaehlabfrage, nicht aus einem Durchlauf durch das Log.
        """
        self._by_key.clear()
        self._type_by_key.clear()
        self._by_type = dict.fromkeys(NotificationType, 0)
        self._day_start = day_start
        self._events_today = events_today

        for event in events:
            try:
                key = key_for(event)
            except ValueError:
                # Ein unvollstaendiger Datensatz darf die Wiederherstellung
                # der uebrigen nicht verhindern.
                continue
            self._by_key[key] = event
            self._type_by_key[key] = event.type
            self._by_type[event.type] += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "counts": self.counts.to_dict(),
            "active": [event.to_dict() for event in self.events()],
        }
