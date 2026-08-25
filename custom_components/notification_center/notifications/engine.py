"""Fuehrt die Absichten der Rule Engine aus.

Diese Schicht erzeugt und beendet Notifications, schreibt sie in den Event
Store und haelt die Zaehler aktuell. Die Entscheidung *ob* etwas geschieht,
faellt in ``rules/``; hier faellt nur die Entscheidung *wie* es festgehalten
wird.

Ein Ereignis wird beim Auftreten sofort gespeichert und beim Ende derselbe
Datensatz aktualisiert (Spezifikation 31). Die Zaehler werden dabei
fortgeschrieben und nie aus dem Log berechnet (Spezifikation 45).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from ..const import DOMAIN, EVENT_NOTIFICATION
from ..rules.intents import IntentKind, NotificationIntent
from ..storage.config_models import ConfigDocument
from ..storage.config_store import ConfigStore
from ..storage.event_store_async import AsyncEventStore
from .lifecycle import ActiveNotifications, Counts, rule_key
from .models import (
    CloseReason,
    NotificationEvent,
    NotificationSource,
)

_LOGGER = logging.getLogger(__name__)

#: Signal, auf das die Zaehler-Entities hoeren.
SIGNAL_COUNTS_UPDATED = f"{DOMAIN}_counts_updated"


class NotificationEngine:
    """Erzeugt, aktualisiert und beendet Notifications."""

    def __init__(
        self,
        hass: HomeAssistant,
        event_store: AsyncEventStore,
        config_store: ConfigStore,
    ) -> None:
        self._hass = hass
        self._store = event_store
        self._config_store = config_store
        self._active = ActiveNotifications()
        self._unsub_midnight: CALLBACK_TYPE | None = None

    @property
    def _config(self) -> ConfigDocument:
        """Immer der aktuelle Stand; der Store ersetzt sein Dokument beim Laden."""
        return self._config_store.document

    # -- Lesen -----------------------------------------------------------

    @property
    def counts(self) -> Counts:
        return self._active.counts

    def active_events(self) -> list[NotificationEvent]:
        return self._active.events()

    # -- Lebenszyklus ----------------------------------------------------

    async def async_start(self) -> None:
        """Stellt den Zustand her und richtet den Tageswechsel ein."""
        await self.async_restore()

        # Mitternacht in der Home-Assistant-Zeitzone: Tageszaehler
        # zuruecksetzen und aufraeumen. Der einzige zeitgesteuerte Vorgang
        # ohne konkreten Anlass, und er laeuft einmal taeglich.
        self._unsub_midnight = async_track_time_change(
            self._hass, self._handle_midnight, hour=0, minute=0, second=0
        )

    async def async_stop(self) -> None:
        if self._unsub_midnight is not None:
            self._unsub_midnight()
            self._unsub_midnight = None

    async def async_restore(self) -> None:
        """Baut aktive Notifications und Zaehler nach einem Neustart auf.

        Kostet genau zwei Abfragen: die aktiven Ereignisse ueber den
        Teilindex und eine Zaehlabfrage fuer den heutigen Tag. Das Log wird
        dabei nicht durchlaufen (Spezifikation 45, 83).
        """
        tagesbeginn = self._start_of_day()
        aktive = await self._store.async_active_events()
        heute = await self._store.async_count_since(tagesbeginn)

        self._active.restore(aktive, day_start=tagesbeginn, events_today=heute)
        _LOGGER.debug(
            "Wiederhergestellt: %s aktive Notifications, %s Ereignisse heute",
            len(aktive),
            heute,
        )
        self._notify_change()

    # -- Absichten ausfuehren --------------------------------------------

    async def async_apply(self, intents: Iterable[NotificationIntent]) -> None:
        """Fuehrt die Absichten der Rule Engine aus.

        Beendigungen laufen vor Neuanlagen, damit bei einer Eskalation die
        alte Stufe abgeschlossen ist, bevor die neue beginnt.
        """
        jetzt = dt_util.utcnow()
        geaendert = False

        sortiert = sorted(intents, key=lambda i: 0 if i.kind is IntentKind.STOP else 1)

        for intent in sortiert:
            try:
                if intent.kind is IntentKind.STOP:
                    geaendert |= await self._async_stop(intent, jetzt)
                else:
                    geaendert |= await self._async_start(intent, jetzt)
            except Exception:
                # Ein Fehler an einer Notification darf die uebrigen nicht
                # verhindern (Spezifikation 82).
                _LOGGER.exception(
                    "Absicht %s fuer Regel %s konnte nicht ausgefuehrt werden",
                    intent.kind,
                    intent.rule_id,
                )

        if geaendert:
            self._notify_change()

    async def _async_start(self, intent: NotificationIntent, now: datetime) -> bool:
        key = rule_key(intent.rule_id)
        if key in self._active:
            # Die Notification laeuft bereits; der Zustand hat sich nur
            # innerhalb der Bedingung bewegt.
            return False

        ereignis = NotificationEvent(
            message=intent.message(),
            type=intent.rule.type,
            source=NotificationSource.ENTITY_RULE,
            start_time=intent.since or now,
            title=intent.rule.title,
            entity_id=intent.snapshot.entity_id,
            device_id=intent.snapshot.device_id,
            area_id=intent.snapshot.area_id,
            rule_id=intent.rule_id,
            rule_group_id=intent.rule.group_id,
            level=intent.level,
        )

        self._active.put(ereignis)
        await self._store.async_add(ereignis)
        self._fire(ereignis, "started")
        return True

    async def _async_stop(self, intent: NotificationIntent, now: datetime) -> bool:
        reason = intent.reason or CloseReason.CONDITION_CLEARED
        return await self.async_close_key(rule_key(intent.rule_id), reason, now=now)

    # -- Beenden von aussen ----------------------------------------------

    async def async_close_key(
        self,
        key: str,
        reason: CloseReason,
        *,
        now: datetime | None = None,
        notify: bool = False,
    ) -> bool:
        """Beendet eine Notification und schliesst ihren Log-Eintrag ab."""
        ereignis = self._active.close(key, now or dt_util.utcnow(), reason)
        if ereignis is None:
            return False

        await self._store.async_update(ereignis)
        self._fire(ereignis, "ended")
        if notify:
            self._notify_change()
        return True

    async def async_close_rules(self, rule_ids: Iterable[str], reason: CloseReason) -> int:
        """Beendet die Notifications bestimmter Regeln.

        Wird beim Deaktivieren einer Regel und beim Entfernen oder Ersetzen
        einer Entity gebraucht (Spezifikation 66, 77, 78).
        """
        jetzt = dt_util.utcnow()
        beendet = 0
        for key in self._active.keys_for_rules(rule_ids):
            if await self.async_close_key(key, reason, now=jetzt):
                beendet += 1

        if beendet:
            self._notify_change()
        return beendet

    # -- Tageswechsel ----------------------------------------------------

    async def _handle_midnight(self, _now: datetime) -> None:
        """Setzt den Tageszaehler zurueck und raeumt das Log auf."""
        self._active.roll_day(self._start_of_day())
        self._notify_change()

        entfernt = await self._store.async_cleanup(
            retention_days=self._config.settings.retention_days,
            max_events=self._config.settings.max_events,
        )
        if entfernt:
            _LOGGER.debug("Beim Tageswechsel %s Ereignisse entfernt", entfernt)

    def _start_of_day(self) -> datetime:
        """Mitternacht des heutigen Tages in der Home-Assistant-Zeitzone.

        Die Grenze richtet sich nach der lokalen Zeit, gespeichert wird der
        Zeitpunkt in UTC (Spezifikation 36).
        """
        lokal = dt_util.now()
        beginn = lokal.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt_util.as_utc(beginn)

    # -- Benachrichtigungen ----------------------------------------------

    @callback
    def _notify_change(self) -> None:
        """Meldet den Zaehler-Entities, dass sich etwas geaendert hat."""
        async_dispatcher_send(self._hass, SIGNAL_COUNTS_UPDATED)

    @callback
    def _fire(self, event: NotificationEvent, action: str) -> None:
        """Feuert ein Ereignis auf dem Home-Assistant-Eventbus.

        Damit koennen Automationen auf Notifications reagieren, ohne dass das
        Notification Center sie kennen muss.
        """
        self._hass.bus.async_fire(
            EVENT_NOTIFICATION,
            {"action": action, **event.to_dict()},
        )
