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
from datetime import datetime, timedelta

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from ..const import DOMAIN, EVENT_NOTIFICATION
from ..rules.intents import IntentKind, NotificationIntent
from ..storage.config_models import ConfigDocument
from ..storage.config_store import ConfigStore
from ..storage.event_store_async import AsyncEventStore
from .lifecycle import (
    ActiveNotifications,
    Counts,
    automation_notification_key,
    rule_key,
)
from .models import (
    CloseReason,
    NotificationEvent,
    NotificationSource,
    NotificationType,
)

_LOGGER = logging.getLogger(__name__)

#: Signal, auf das die Zaehler-Entities hoeren.
SIGNAL_COUNTS_UPDATED = f"{DOMAIN}_counts_updated"

#: Nach so vielen neuen Ereignissen wird zwischendurch aufgeraeumt.
#:
#: Der Cleanup laeuft sonst nur beim Start und um Mitternacht. Ein
#: Ereignissturm koennte die Mengengrenze bis dahin deutlich ueberschreiten.
CLEANUP_AFTER_EVENTS = 500


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
        self._expiry_timers: dict[str, CALLBACK_TYPE] = {}
        self._seit_cleanup = 0

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

    def active_rule_starts(self) -> dict[str, datetime]:
        """Laufende Regel-Meldungen: Regel-Kennung und Beginn.

        Die Rule Engine braucht das nach einem Neustart, um ihren Zustand mit
        dem wiederhergestellten in Deckung zu bringen. Ohne diesen Abgleich
        haelt sie jede Regel fuer unerfuellt und beendet nichts mehr.
        """
        return {
            ereignis.rule_id: ereignis.start_time
            for ereignis in self._active.events()
            if ereignis.source is NotificationSource.ENTITY_RULE and ereignis.rule_id is not None
        }

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
        for key in list(self._expiry_timers):
            self._cancel_expiry(key)

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
        await self._async_maybe_cleanup()
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

    # -- Automations-API (Spezifikation 23 bis 30) -----------------------

    async def async_create_automation(
        self,
        *,
        owner: str,
        notification_id: str,
        type: NotificationType,
        message: str,
        title: str | None = None,
        entity_id: str | None = None,
        duration: timedelta | None = None,
    ) -> str | None:
        """Erzeugt oder ueberschreibt eine Automations-Notification.

        Der Aufruf ist idempotent: dieselbe Kombination aus Owner und ID
        ueberschreibt die bestehende Notification, auch mit geaendertem Typ,
        und erzeugt keinen zweiten Log-Eintrag (Spezifikation 26, 75).

        Waehrend einer Pause entsteht nichts und es wird nichts protokolliert
        (Spezifikation 42). Solche Aufrufe werden spaeter nicht nachgeholt
        (Spezifikation 43).
        """
        if self._config.settings.paused:
            _LOGGER.debug("Notification %s/%s waehrend der Pause verworfen", owner, notification_id)
            return None

        key = automation_notification_key(owner, notification_id)
        jetzt = dt_util.utcnow()
        bestehend = self._active.get(key)

        if bestehend is not None:
            bestehend.type = type
            bestehend.message = message
            bestehend.title = title
            bestehend.entity_id = entity_id
            self._active.put(bestehend)
            await self._store.async_update(bestehend)
            self._fire(bestehend, "updated")
            self._schedule_expiry(key, bestehend.start_time, duration)
            self._notify_change()
            return bestehend.event_id

        ereignis = NotificationEvent(
            message=message,
            type=type,
            source=NotificationSource.AUTOMATION,
            start_time=jetzt,
            title=title,
            entity_id=entity_id,
            owner=owner,
            notification_id=notification_id,
        )
        self._active.put(ereignis)
        await self._store.async_add(ereignis)
        self._fire(ereignis, "started")
        self._schedule_expiry(key, ereignis.start_time, duration)
        self._notify_change()
        await self._async_maybe_cleanup()
        return ereignis.event_id

    async def async_update_automation(
        self,
        *,
        owner: str,
        notification_id: str,
        type: NotificationType | None = None,
        message: str | None = None,
        title: str | None = None,
        entity_id: str | None = None,
        clear_title: bool = False,
        clear_entity_id: bool = False,
    ) -> bool:
        """Aendert eine laufende Automations-Notification (Spezifikation 27).

        Zwischenaktualisierungen erzeugen keinen eigenen Log-Eintrag; der
        Datensatz behaelt seinen Beginn und traegt am Ende den letzten Stand
        (Spezifikation 75).
        """
        key = automation_notification_key(owner, notification_id)
        ereignis = self._active.get(key)
        if ereignis is None:
            _LOGGER.warning(
                "Keine aktive Notification %s/%s zum Aktualisieren", owner, notification_id
            )
            return False

        if type is not None:
            ereignis.type = type
        if message is not None:
            ereignis.message = message
        if title is not None or clear_title:
            ereignis.title = title
        if entity_id is not None or clear_entity_id:
            ereignis.entity_id = entity_id

        self._active.put(ereignis)
        await self._store.async_update(ereignis)
        self._fire(ereignis, "updated")
        self._notify_change()
        return True

    async def async_dismiss_automation(self, *, owner: str, notification_id: str) -> bool:
        """Beendet eine Automations-Notification (Spezifikation 28).

        Das ist die einzige Notification-Art, die sich von aussen beenden
        laesst; entity-basierte Notifications enden ueber ihren Zustand.
        """
        key = automation_notification_key(owner, notification_id)
        self._cancel_expiry(key)
        beendet = await self.async_close_key(key, CloseReason.DISMISSED, notify=True)
        if not beendet:
            _LOGGER.debug("Keine aktive Notification %s/%s zum Beenden", owner, notification_id)
        return beendet

    # -- Ablaufende Notifications (Spezifikation 29) ---------------------

    @callback
    def _schedule_expiry(self, key: str, start_time: datetime, duration: timedelta | None) -> None:
        """Setzt oder loescht den Ablauftimer einer Automations-Notification."""
        self._cancel_expiry(key)
        if duration is None:
            return

        ablauf = start_time + duration

        @callback
        def _abgelaufen(_now: datetime) -> None:
            self._expiry_timers.pop(key, None)
            self._hass.async_create_task(
                self.async_close_key(key, CloseReason.EXPIRED, notify=True)
            )

        self._expiry_timers[key] = async_track_point_in_utc_time(self._hass, _abgelaufen, ablauf)

    @callback
    def _cancel_expiry(self, key: str) -> None:
        unsub = self._expiry_timers.pop(key, None)
        if unsub is not None:
            unsub()

    # -- Aufraeumen ------------------------------------------------------

    async def _async_maybe_cleanup(self) -> None:
        """Raeumt zwischendurch auf, ohne bei jedem Ereignis zu arbeiten."""
        self._seit_cleanup += 1
        if self._seit_cleanup < CLEANUP_AFTER_EVENTS:
            return

        self._seit_cleanup = 0
        entfernt = await self._store.async_cleanup(
            retention_days=self._config.settings.retention_days,
            max_events=self._config.settings.max_events,
        )
        if entfernt:
            _LOGGER.debug("Zwischendurch %s Ereignisse entfernt", entfernt)

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
