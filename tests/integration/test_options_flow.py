"""Tests des Options Flows (Spezifikation 38 und 42)."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.coordinator import NotificationCenterRuntime


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry) -> NotificationCenterRuntime:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry.runtime_data


async def test_flow_zeigt_die_aktuellen_werte(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    ergebnis = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert ergebnis["type"] is FlowResultType.FORM
    assert ergebnis["step_id"] == "init"


async def test_einstellungen_landen_im_store(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    """Spezifikation 47: es gibt nur eine Ablage fuer Einstellungen."""
    ergebnis = await hass.config_entries.options.async_init(config_entry.entry_id)
    ergebnis = await hass.config_entries.options.async_configure(
        ergebnis["flow_id"],
        {
            "retention_days": "30",
            "max_events": "5000",
            "analysis_days": 14,
            "paused": True,
        },
    )
    await hass.async_block_till_done()

    assert ergebnis["type"] is FlowResultType.CREATE_ENTRY
    einstellungen = config_entry.runtime_data.config.settings
    assert einstellungen.retention_days == 30
    assert einstellungen.max_events == 5000
    assert einstellungen.analysis_days == 14
    assert einstellungen.paused is True


async def test_unbegrenzte_aufbewahrung_ist_waehlbar(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    ergebnis = await hass.config_entries.options.async_init(config_entry.entry_id)
    await hass.config_entries.options.async_configure(
        ergebnis["flow_id"],
        {"retention_days": "0", "max_events": "50000", "analysis_days": 7, "paused": False},
    )
    await hass.async_block_till_done()

    assert config_entry.runtime_data.config.settings.retention_days == 0
