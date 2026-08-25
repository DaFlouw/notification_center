"""Tests der Notification-Engine, des Event Stores und der Zaehler-Entities.

Deckt die Spezifikationsabschnitte 22, 31 bis 35, 37, 44, 45, 77 und 78 ab.
"""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.const import EVENT_NOTIFICATION
from custom_components.notification_center.notifications.models import (
    NotificationType,
)
from custom_components.notification_center.rules.models import (
    ConditionKind,
    NumericOperator,
    Rule,
    RuleGroup,
)
from custom_components.notification_center.storage.config_models import WatchedEntity
from custom_components.notification_center.storage.event_store import EventQuery

FENSTER = "binary_sensor.fenster_wz"
TEMPERATUR = "sensor.temperatur_wz"

SENSOR_WARNUNGEN = "sensor.notification_center_warning_count"
SENSOR_ALARME = "sensor.notification_center_alarm_count"
SENSOR_INFOS = "sensor.notification_center_info_count"
SENSOR_AKTIV = "sensor.notification_center_active_count"
SENSOR_HEUTE = "sensor.notification_center_events_today"


def fensterregel(**kwargs: object) -> Rule:
    defaults: dict[str, object] = {
        "entity_id": FENSTER,
        "kind": ConditionKind.STATE_IS,
        "states": ("on",),
        "type": NotificationType.WARNING,
        "message_template": "{name} geoeffnet",
        "rule_id": "rule_fenster",
    }
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry):
    hass.states.async_set(FENSTER, "off")
    hass.states.async_set(TEMPERATUR, "21.0", {"unit_of_measurement": "°C"})

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    laufzeit = config_entry.runtime_data
    laufzeit.config.add_entity(WatchedEntity(entity_id=FENSTER))
    laufzeit.config.add_entity(WatchedEntity(entity_id=TEMPERATUR))
    laufzeit.config.add_rule(fensterregel())
    laufzeit.rule_engine.async_refresh_tracking()
    return laufzeit


# -- Entstehen und Enden ----------------------------------------------------


async def test_notification_entsteht_und_wird_gespeichert(hass: HomeAssistant, runtime) -> None:
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()

    aktive = runtime.notification_engine.active_events()
    assert len(aktive) == 1
    assert aktive[0].message.endswith("geoeffnet")
    assert aktive[0].active is True
    assert aktive[0].entity_id == FENSTER

    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1
    assert seite.events[0].active is True


async def test_ende_aktualisiert_denselben_datensatz(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 31: kein zweiter Datensatz beim Beenden."""
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    event_id = runtime.notification_engine.active_events()[0].event_id

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()

    assert runtime.notification_engine.active_events() == []
    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1
    assert seite.events[0].event_id == event_id
    assert seite.events[0].active is False
    assert seite.events[0].end_time is not None


async def test_laufende_notification_wird_nicht_neu_geschrieben(
    hass: HomeAssistant, runtime
) -> None:
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    hass.states.async_set(FENSTER, "on", {"battery": 80})
    await hass.async_block_till_done()

    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1


# -- Zaehler-Entities -------------------------------------------------------


async def test_zaehler_entities_existieren_mit_englischen_ids(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 44."""
    for entity_id in (
        SENSOR_INFOS,
        SENSOR_WARNUNGEN,
        SENSOR_ALARME,
        SENSOR_AKTIV,
        SENSOR_HEUTE,
    ):
        assert hass.states.get(entity_id) is not None, entity_id


async def test_zaehler_folgen_den_notifications(hass: HomeAssistant, runtime) -> None:
    assert hass.states.get(SENSOR_WARNUNGEN).state == "0"

    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_WARNUNGEN).state == "1"
    assert hass.states.get(SENSOR_AKTIV).state == "1"
    assert hass.states.get(SENSOR_HEUTE).state == "1"

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_WARNUNGEN).state == "0"
    assert hass.states.get(SENSOR_AKTIV).state == "0"
    # Das Ereignis fand statt und bleibt im Tageszaehler.
    assert hass.states.get(SENSOR_HEUTE).state == "1"


# -- Eskalation -------------------------------------------------------------


async def test_jede_eskalationsstufe_wird_ein_eigenes_ereignis(
    hass: HomeAssistant, runtime
) -> None:
    """Spezifikation 20 und 35."""
    stufen = tuple(
        Rule(
            rule_id=f"rule_temp_{level}",
            entity_id=TEMPERATUR,
            kind=ConditionKind.NUMERIC,
            operator=NumericOperator.GT,
            threshold=schwelle,
            type=typ,
            group_id="group_temp",
            level=level,
            message_template="{name} {value} {unit}",
        )
        for level, schwelle, typ in (
            (1, 25.0, NotificationType.INFO),
            (2, 28.0, NotificationType.WARNING),
            (3, 32.0, NotificationType.ALARM),
        )
    )
    runtime.config.add_group(
        RuleGroup(
            group_id="group_temp",
            entity_id=TEMPERATUR,
            name="Temperatur",
            rules=stufen,
        )
    )
    runtime.rule_engine.async_refresh_tracking()

    for wert in ("26", "29", "33"):
        hass.states.async_set(TEMPERATUR, wert, {"unit_of_measurement": "°C"})
        await hass.async_block_till_done()

    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 3
    # Nicht nach Zeitstempel pruefen: bei eingefrorener Uhr koennen die drei
    # Ereignisse dieselbe Startzeit tragen.
    assert sorted(e.level for e in seite.events) == [1, 2, 3]
    assert [e.level for e in seite.events if e.active] == [3]
    assert hass.states.get(SENSOR_ALARME).state == "1"
    assert hass.states.get(SENSOR_INFOS).state == "0"


# -- Regel- und Entity-Aenderungen -----------------------------------------


async def test_deaktivierte_regel_beendet_ihre_notification(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 77."""
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_AKTIV).state == "1"

    await runtime.async_disable_rule("rule_fenster")
    await hass.async_block_till_done()

    assert runtime.notification_engine.active_events() == []
    assert hass.states.get(SENSOR_AKTIV).state == "0"


async def test_entfernte_entity_beendet_notification_und_behaelt_historie(
    hass: HomeAssistant, runtime
) -> None:
    """Spezifikation 78."""
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()

    await runtime.async_remove_entity(FENSTER)
    await hass.async_block_till_done()

    assert runtime.notification_engine.active_events() == []
    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1
    assert seite.events[0].active is False


# -- Eventbus ---------------------------------------------------------------


async def test_ereignisse_erscheinen_auf_dem_eventbus(hass: HomeAssistant, runtime) -> None:
    gesehen: list[dict] = []

    hass.bus.async_listen(EVENT_NOTIFICATION, lambda e: gesehen.append(dict(e.data)))

    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()

    assert [d["action"] for d in gesehen] == ["started", "ended"]
    assert gesehen[0]["entity_id"] == FENSTER


# -- Neustart ---------------------------------------------------------------


async def test_aktive_notification_ueberlebt_einen_neustart(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    """Spezifikation 37 und 45."""
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    event_id = runtime.notification_engine.active_events()[0].event_id

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    danach = config_entry.runtime_data
    aktive = danach.notification_engine.active_events()
    assert len(aktive) == 1
    assert aktive[0].event_id == event_id
    assert danach.notification_engine.counts.warning == 1
    assert hass.states.get(SENSOR_WARNUNGEN).state == "1"
    assert hass.states.get(SENSOR_HEUTE).state == "1"
