"""Laufzeitcontainer der Integration.

Haelt die gemeinsam genutzten Bausteine (Konfiguration, Event Store und
spaeter Rule- und Notification-Engine) zusammen und regelt deren Start und
Stopp. Es gibt genau eine Instanz pro Home-Assistant-Installation
(Spezifikation 4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.core import HomeAssistant

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

    async def async_start(self) -> None:
        """Laedt die Konfiguration und oeffnet die Ereignisdatenbank."""
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

    async def async_stop(self) -> None:
        """Sichert die Konfiguration und schliesst die Ereignisdatenbank."""
        await self.config_store.async_shutdown()
        await self.event_store.async_close()
