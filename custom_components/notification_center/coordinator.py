"""Laufzeitcontainer der Integration.

Haelt die gemeinsam genutzten Bausteine (Konfiguration, Event Store und Rule
Engine) zusammen und regelt deren Start und Stopp. Es gibt genau eine Instanz
pro Home-Assistant-Installation (Spezifikation 4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant

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

    #: Sammelstelle der zuletzt erzeugten Absichten.
    #:
    #: Die Notification-Engine aus Phase 3 tritt hier an die Stelle der
    #: Ablage. Bis dahin bleibt die Naht sichtbar, statt sie zu verstecken.
    pending_intents: list[NotificationIntent] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rule_engine = RuleEngine(
            self.hass,
            self.config_store,
            self._async_handle_intents,
        )

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
        """Laedt die Konfiguration, oeffnet die Datenbank, startet die Engine."""
        await self.config_store.async_load()
        await self.event_store.async_open()

        # Aufraeumen einmal beim Start: das Log kann waehrend eines langen
        # Stillstands ueber seine Grenzen gewachsen sein. Danach laeuft der
        # Cleanup ereignisgesteuert, nicht in einer Schleife.
        entfernt = await self.event_store.async_cleanup(
            retention_days=self.config.settings.retention_days,
            max_events=self.config.settings.max_events,
        )
        if entfernt:
            _LOGGER.debug("Beim Start %s alte Ereignisse entfernt", entfernt)

        await self.rule_engine.async_start()

    async def async_stop(self) -> None:
        """Haelt die Engine an, sichert und schliesst die Ablagen."""
        await self.rule_engine.async_stop()
        await self.config_store.async_shutdown()
        await self.event_store.async_close()

    # -- Konfigurationsaenderungen ---------------------------------------

    async def async_config_changed(self) -> None:
        """Nach jeder Aenderung an Entities oder Regeln aufzurufen."""
        self.config_store.schedule_save()
        self.rule_engine.async_refresh_tracking()

    async def async_set_paused(self, paused: bool) -> None:
        """Schaltet den globalen Pause-Modus (Spezifikation 42, 43).

        Beim Fortsetzen werden die aktuellen Zustaende neu bewertet, damit
        Notifications entstehen, die waehrend der Pause faellig geworden sind.
        """
        if self.config.settings.paused == paused:
            return

        self.config.settings.paused = paused
        self.config_store.schedule_save()

        if not paused:
            await self.rule_engine.async_evaluate_all()

    # -- Naht zur Notification-Engine ------------------------------------

    async def _async_handle_intents(self, intents: list[NotificationIntent]) -> None:
        """Nimmt die Absichten der Rule Engine entgegen.

        Ab Phase 3 erzeugt und beendet die Notification-Engine hier die
        Notifications und schreibt sie in den Event Store.
        """
        self.pending_intents.extend(intents)
        for intent in intents:
            _LOGGER.debug(
                "Absicht %s fuer Regel %s an Entity %s",
                intent.kind,
                intent.rule_id,
                intent.snapshot.entity_id,
            )
