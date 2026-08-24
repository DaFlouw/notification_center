"""Notification Center: zentrales, lokales Benachrichtigungssystem.

Eine einzige Integration mit logisch getrennten Modulen. Die gesamte
Geschaeftslogik liegt hier im Backend; das Frontend stellt ausschliesslich dar.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONFIG_ENTRY_VERSION, DOMAIN
from .coordinator import NotificationCenterRuntime

_LOGGER = logging.getLogger(__name__)

#: Plattformen kommen ab Phase 3 dazu (Zaehler-Entities).
PLATFORMS: list[str] = []

type NotificationCenterEntry = ConfigEntry[NotificationCenterRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: NotificationCenterEntry) -> bool:
    """Startet die eine globale Instanz des Notification Centers."""
    runtime = NotificationCenterRuntime.create(hass)

    try:
        await runtime.async_start()
    except Exception as err:
        _LOGGER.exception("Notification Center konnte nicht gestartet werden")
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = runtime
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Notification Center gestartet")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NotificationCenterEntry) -> bool:
    """Beendet die Instanz und schliesst die Ereignisdatenbank."""
    unloaded = True
    if PLATFORMS:
        unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded:
        await entry.runtime_data.async_stop()

    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Hebt aeltere Konfigurationseintraege auf die aktuelle Version.

    Solange nur Version 1 existiert, ist nichts zu tun. Ein Eintrag aus einer
    *neueren* Version wird abgelehnt, statt seine Daten zu beschaedigen.
    """
    if entry.version > CONFIG_ENTRY_VERSION:
        _LOGGER.error(
            "Konfigurationseintrag hat Version %s, unterstuetzt wird hoechstens %s. "
            "Vermutlich wurde die Integration heruntergestuft",
            entry.version,
            CONFIG_ENTRY_VERSION,
        )
        return False
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Laedt die Integration nach geaenderten Optionen neu."""
    await hass.config_entries.async_reload(entry.entry_id)


__all__ = ["DOMAIN", "NotificationCenterEntry", "NotificationCenterRuntime"]
