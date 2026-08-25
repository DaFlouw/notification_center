"""Laufzeitcontainer der Integration.

Haelt die gemeinsam genutzten Bausteine (Konfiguration, Event Store, Rule
Engine und Notification-Engine) zusammen und regelt deren Start und Stopp. Es
gibt genau eine Instanz pro Home-Assistant-Installation (Spezifikation 4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant

from .discovery.engine import DiscoveryEngine
from .notifications.engine import NotificationEngine
from .notifications.models import CloseReason
from .rules.engine import RuleEngine
from .rules.intents import NotificationIntent
from .storage.config_models import ConfigDocument
from .storage.config_store import ConfigStore
from .storage.event_store_async import AsyncEventStore

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationCenterRuntime:
    """Alles, was zur Laufzeit gebraucht wird."""

    hass: HomeAssistant
    config_store: ConfigStore
    event_store: AsyncEventStore
    rule_engine: RuleEngine = field(init=False)
    notification_engine: NotificationEngine = field(init=False)
    discovery: DiscoveryEngine = field(init=False)

    def __post_init__(self) -> None:
        self.notification_engine = NotificationEngine(
            self.hass, self.event_store, self.config_store
        )
        self.rule_engine = RuleEngine(
            self.hass,
            self.config_store,
            self._async_handle_intents,
        )
        self.discovery = DiscoveryEngine(self.hass, self.config_store)

    @classmethod
    def create(cls, hass: HomeAssistant) -> NotificationCenterRuntime:
        return cls(
            hass=hass,
            config_store=ConfigStore(hass),
            event_store=AsyncEventStore(hass),
        )

    @property
    def config(self) -> ConfigDocument:
        return self.config_store.document

    # -- Lebenszyklus ----------------------------------------------------

    async def async_start(self) -> None:
        """Laedt die Ablagen und startet beide Engines."""
        await self.config_store.async_load()
        await self.event_store.async_open()

        # Aufraeumen einmal beim Start: das Log kann waehrend eines langen
        # Stillstands ueber seine Grenzen gewachsen sein. Danach geschieht es
        # beim Tageswechsel, nicht in einer Schleife.
        entfernt = await self.event_store.async_cleanup(
            retention_days=self.config.settings.retention_days,
            max_events=self.config.settings.max_events,
        )
        if entfernt:
            _LOGGER.debug("Beim Start %s alte Ereignisse entfernt", entfernt)

        await self.notification_engine.async_start()
        await self.rule_engine.async_start()

    async def async_stop(self) -> None:
        """Haelt die Engines an, sichert und schliesst die Ablagen."""
        await self.rule_engine.async_stop()
        await self.notification_engine.async_stop()
        await self.config_store.async_shutdown()
        await self.event_store.async_close()

    # -- Konfigurationsaenderungen ---------------------------------------

    async def async_config_changed(self) -> None:
        """Nach jeder Aenderung an Entities oder Regeln aufzurufen."""
        self.config_store.schedule_save()
        self.rule_engine.async_refresh_tracking()

    async def async_remove_entity(self, entity_id: str) -> None:
        """Entfernt eine Entity aus der Ueberwachung (Spezifikation 78)."""
        entfernte_regeln = self.config.remove_entity(entity_id)
        await self.notification_engine.async_close_rules(
            entfernte_regeln, CloseReason.ENTITY_REMOVED
        )
        await self.async_config_changed()

    async def async_disable_rule(self, rule_id: str) -> None:
        """Deaktiviert eine Regel und beendet ihre Notification (Spez. 77)."""
        regel = self.config.rules.get(rule_id)
        if regel is None or not regel.enabled:
            return

        regel.enabled = False
        await self.notification_engine.async_close_rules([rule_id], CloseReason.RULE_DISABLED)
        await self.async_config_changed()

    async def async_set_paused(self, paused: bool) -> None:
        """Schaltet den globalen Pause-Modus (Spezifikation 42, 43).

        Beim Fortsetzen werden die aktuellen Zustaende neu bewertet, damit
        Notifications entstehen, die waehrend der Pause faellig geworden sind.
        Bestehende aktive Notifications bleiben waehrend der Pause unberuehrt.
        """
        if self.config.settings.paused == paused:
            return

        self.config.settings.paused = paused
        self.config_store.schedule_save()

        if not paused:
            await self.rule_engine.async_evaluate_all()

    # -- Verbindung der Engines ------------------------------------------

    async def _async_handle_intents(self, intents: list[NotificationIntent]) -> None:
        """Reicht die Absichten der Rule Engine an die Notification-Engine."""
        await self.notification_engine.async_apply(intents)
