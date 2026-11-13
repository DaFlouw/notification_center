"""Tests des Deaktivierens einer laufenden Meldung von Hand.

Geprueft wird am Ergebnis: verschwindet die Meldung aus der aktiven Menge,
bleibt sie als Eintrag im Log, laesst sie sich fortsetzen -- und was geschieht,
wenn ihre Bedingung inzwischen nicht mehr anliegt.

Der letzte Fall ist der Grund, warum diese Tests eine laufende
Home-Assistant-Instanz brauchen: er fuehrt durch die Rule Engine und haengt an
echten Zustaenden.
"""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.coordinator import NotificationCenterRuntime
from custom_components.notification_center.notifications.models import CloseReason
from custom_components.notification_center.rules.models import ConditionKind, Rule
from custom_components.notification_center.storage.config_models import WatchedEntity

FENSTER = "binary_sensor.fenster_wz"


def fensterregel(**kwargs: object) -> Rule:
    defaults: dict[str, object] = {
        "rule_id": "rule_fenster",
        "entity_id": FENSTER,
        "kind": ConditionKind.STATE_IS,
        "states": ("on",),
        "message_template": "{name} geoeffnet",
    }
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


def aktive(laufzeit: NotificationCenterRuntime) -> list:
    return laufzeit.notification_engine.active_events()


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry) -> NotificationCenterRuntime:
    """Eingerichtete Integration mit einer laufenden Meldung."""
    hass.states.async_set(FENSTER, "off")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    laufzeit = config_entry.runtime_data
    laufzeit.config.add_entity(WatchedEntity(entity_id=FENSTER))
    laufzeit.config.add_rule(fensterregel())
    laufzeit.rule_engine.async_refresh_tracking()

    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    assert len(aktive(laufzeit)) == 1
    return laufzeit


# -- Deaktivieren -----------------------------------------------------------


async def test_deaktivieren_beendet_die_meldung(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    ereignis = aktive(runtime)[0]

    assert await runtime.async_deactivate_event(ereignis.event_id) is True
    await hass.async_block_till_done()

    assert aktive(runtime) == []
    assert runtime.notification_engine.counts.active == 0


async def test_deaktivierte_meldung_bleibt_im_log(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Deaktivieren ist kein Loeschen: der Eintrag bleibt, gekennzeichnet."""
    ereignis = aktive(runtime)[0]
    await runtime.async_deactivate_event(ereignis.event_id)
    await hass.async_block_till_done()

    gespeichert = await runtime.event_store.async_get(ereignis.event_id)
    assert gespeichert is not None
    assert gespeichert.active is False
    assert gespeichert.close_reason is CloseReason.DEACTIVATED
    assert gespeichert.deactivated is True


async def test_deaktivierte_meldung_kehrt_nicht_von_allein_zurueck(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Abgehakt ist abgehakt, solange die Bedingung ununterbrochen anliegt."""
    ereignis = aktive(runtime)[0]
    await runtime.async_deactivate_event(ereignis.event_id)
    await hass.async_block_till_done()

    # Weitere Zustandsmeldungen derselben Lage.
    hass.states.async_set(FENSTER, "on", {"battery": 80})
    await hass.async_block_till_done()

    assert aktive(runtime) == []


async def test_erneutes_ausloesen_meldet_wieder(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Ein neues Ereignis ist ein neues Ereignis."""
    ereignis = aktive(runtime)[0]
    await runtime.async_deactivate_event(ereignis.event_id)
    await hass.async_block_till_done()

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()

    neu = aktive(runtime)
    assert len(neu) == 1
    assert neu[0].event_id != ereignis.event_id


async def test_unbekannte_kennung_laesst_sich_nicht_deaktivieren(
    runtime: NotificationCenterRuntime,
) -> None:
    assert await runtime.async_deactivate_event("gibt_es_nicht") is False


# -- Fortsetzen -------------------------------------------------------------


async def test_fortsetzen_zeigt_die_meldung_wieder(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    ereignis = aktive(runtime)[0]
    await runtime.async_deactivate_event(ereignis.event_id)
    await hass.async_block_till_done()

    assert await runtime.async_reactivate_event(ereignis.event_id) is True
    await hass.async_block_till_done()

    wieder = aktive(runtime)
    assert len(wieder) == 1
    # Derselbe Datensatz, derselbe Beginn.
    assert wieder[0].event_id == ereignis.event_id
    assert wieder[0].start_time == ereignis.start_time
    assert wieder[0].close_reason is None


async def test_fortsetzen_ohne_bedingung_endet_sofort_wieder(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Der Kern der Sache: keine Meldung ohne Bedingung.

    Wird eine deaktivierte Meldung fortgesetzt, deren Bedingung inzwischen
    entfallen ist, bringt die Rule Engine sie im selben Zug wieder zu Ende.
    Ohne diesen Abgleich stuende sie fuer immer da -- niemand wuerde sie mehr
    beenden, denn den Wegfall der Bedingung hat die Engine laengst gemeldet.
    """
    ereignis = aktive(runtime)[0]
    await runtime.async_deactivate_event(ereignis.event_id)
    await hass.async_block_till_done()

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()

    assert await runtime.async_reactivate_event(ereignis.event_id) is True
    await hass.async_block_till_done()

    assert aktive(runtime) == []
    gespeichert = await runtime.event_store.async_get(ereignis.event_id)
    assert gespeichert is not None
    assert gespeichert.active is False
    assert gespeichert.close_reason is CloseReason.CONDITION_CLEARED


async def test_nur_von_hand_deaktiviertes_laesst_sich_fortsetzen(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Eine Meldung, die wegen ihrer Bedingung endete, bleibt beendet."""
    ereignis = aktive(runtime)[0]

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()
    assert aktive(runtime) == []

    assert await runtime.async_reactivate_event(ereignis.event_id) is False
    assert aktive(runtime) == []


async def test_fortsetzen_weicht_einer_laufenden_meldung(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Zwei Meldungen derselben Regel gleichzeitig gibt es nicht."""
    alt = aktive(runtime)[0]
    await runtime.async_deactivate_event(alt.event_id)
    await hass.async_block_till_done()

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    neu = aktive(runtime)[0]

    assert await runtime.async_reactivate_event(alt.event_id) is False
    assert [ereignis.event_id for ereignis in aktive(runtime)] == [neu.event_id]


async def test_fortgesetzte_meldung_endet_wieder_mit_ihrer_bedingung(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Nach dem Fortsetzen fuehrt die Rule Engine die Regel wieder mit."""
    ereignis = aktive(runtime)[0]
    await runtime.async_deactivate_event(ereignis.event_id)
    await hass.async_block_till_done()
    await runtime.async_reactivate_event(ereignis.event_id)
    await hass.async_block_till_done()

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()

    assert aktive(runtime) == []
    gespeichert = await runtime.event_store.async_get(ereignis.event_id)
    assert gespeichert is not None
    assert gespeichert.close_reason is CloseReason.CONDITION_CLEARED
