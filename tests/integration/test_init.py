"""Einrichtung, Entladen und Persistenz der Integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.storage.config_models import WatchedEntity
from custom_components.notification_center.storage.event_store_async import (
    default_database_path,
)


async def test_einrichtung_und_entladen(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    runtime = config_entry.runtime_data
    assert runtime.config.entities == {}

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_datenbank_liegt_im_konfigurationsverzeichnis(hass: HomeAssistant) -> None:
    """Die Datei muss unter config liegen, damit das HA-Backup sie mitnimmt."""
    pfad = default_database_path(hass)
    assert pfad.name == "events.db"
    assert pfad.parent.name == "notification_center"
    assert str(pfad).startswith(hass.config.config_dir)


async def test_konfiguration_ueberlebt_einen_neustart(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    runtime = config_entry.runtime_data
    runtime.config.add_entity(WatchedEntity(entity_id="binary_sensor.fenster_wz"))
    await runtime.config_store.async_save()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    wieder = config_entry.runtime_data
    assert "binary_sensor.fenster_wz" in wieder.config.entities
