"""Tests der oeffentlichen Automations-API.

Deckt die Spezifikationsabschnitte 23 bis 30 sowie die Testfaelle H, I und J
ab.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
import voluptuous as vol
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.notification_center.api.services import (
    DEFAULT_NOTIFICATION_ID,
    DEFAULT_OWNER,
)
from custom_components.notification_center.const import (
    DOMAIN,
    SERVICE_CREATE,
    SERVICE_DISMISS,
    SERVICE_UPDATE,
)
from custom_components.notification_center.coordinator import NotificationCenterRuntime
from custom_components.notification_center.notifications.models import (
    CloseReason,
    NotificationSource,
    NotificationType,
)
from custom_components.notification_center.storage.event_store import EventQuery

SENSOR_ALARME = "sensor.notification_center_alarm_count"
SENSOR_HEUTE = "sensor.notification_center_events_today"


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry) -> NotificationCenterRuntime:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry.runtime_data


async def erzeugen(hass: HomeAssistant, **daten: object) -> None:
    await hass.services.async_call(DOMAIN, SERVICE_CREATE, daten, blocking=True)
    await hass.async_block_till_done()


async def aendern(hass: HomeAssistant, **daten: object) -> None:
    await hass.services.async_call(DOMAIN, SERVICE_UPDATE, daten, blocking=True)
    await hass.async_block_till_done()


async def beenden(hass: HomeAssistant, **daten: object) -> None:
    await hass.services.async_call(DOMAIN, SERVICE_DISMISS, daten, blocking=True)
    await hass.async_block_till_done()


# -- Anmeldung --------------------------------------------------------------


async def test_services_sind_angemeldet(hass: HomeAssistant, runtime) -> None:
    for service in (SERVICE_CREATE, SERVICE_UPDATE, SERVICE_DISMISS):
        assert hass.services.has_service(DOMAIN, service), service


async def test_services_verschwinden_beim_entladen(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, SERVICE_CREATE)


# -- create -----------------------------------------------------------------


async def test_create_erzeugt_eine_notification(hass: HomeAssistant, runtime) -> None:
    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        type="alarm",
        message="Wasserleck im Keller",
        title="Keller",
    )

    aktive = runtime.notification_engine.active_events()
    assert len(aktive) == 1
    assert aktive[0].message == "Wasserleck im Keller"
    assert aktive[0].title == "Keller"
    assert aktive[0].type is NotificationType.ALARM
    assert aktive[0].source is NotificationSource.AUTOMATION
    assert aktive[0].owner == "automation.keller"
    assert hass.states.get(SENSOR_ALARME).state == "1"


async def test_message_ist_pflicht(hass: HomeAssistant, runtime) -> None:
    with pytest.raises(vol.Invalid):
        await erzeugen(hass, notification_id="leck")


async def test_typ_ist_standardmaessig_info(hass: HomeAssistant, runtime) -> None:
    await erzeugen(hass, message="Hinweis")
    assert runtime.notification_engine.active_events()[0].type is NotificationType.INFO


async def test_ohne_id_gilt_die_standardkennung(hass: HomeAssistant, runtime) -> None:
    await erzeugen(hass, message="Hinweis")
    assert runtime.notification_engine.active_events()[0].notification_id == DEFAULT_NOTIFICATION_ID


async def test_create_ist_idempotent(hass: HomeAssistant, runtime) -> None:
    """Testfall I und Spezifikation 26: derselbe Schluessel ueberschreibt."""
    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        type="warning",
        message="Feuchtigkeit erkannt",
    )
    erste = runtime.notification_engine.active_events()[0].event_id

    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        type="alarm",
        message="Wasserleck bestaetigt",
    )

    aktive = runtime.notification_engine.active_events()
    assert len(aktive) == 1
    assert aktive[0].event_id == erste
    assert aktive[0].type is NotificationType.ALARM
    assert aktive[0].message == "Wasserleck bestaetigt"

    # Kein zweiter Log-Eintrag (Spezifikation 75).
    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1
    assert hass.states.get(SENSOR_HEUTE).state == "1"


async def test_zwei_owner_mit_gleicher_id_stoeren_sich_nicht(hass: HomeAssistant, runtime) -> None:
    """Testfall J."""
    await erzeugen(hass, owner="automation.keller", notification_id="leck", message="Keller")
    await erzeugen(hass, owner="automation.dach", notification_id="leck", message="Dach")

    assert runtime.notification_engine.counts.active == 2

    await beenden(hass, owner="automation.keller", notification_id="leck")

    verbleibend = runtime.notification_engine.active_events()
    assert len(verbleibend) == 1
    assert verbleibend[0].owner == "automation.dach"


# -- update -----------------------------------------------------------------


async def test_update_aendert_ohne_neuen_logeintrag(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 27 und 75."""
    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        type="warning",
        message="Feuchtigkeit",
    )
    event_id = runtime.notification_engine.active_events()[0].event_id

    await aendern(
        hass,
        owner="automation.keller",
        notification_id="leck",
        type="alarm",
        message="Wasserleck",
    )

    aktive = runtime.notification_engine.active_events()[0]
    assert aktive.event_id == event_id
    assert aktive.type is NotificationType.ALARM
    assert aktive.message == "Wasserleck"

    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1


async def test_update_ohne_bestehende_notification_ist_wirkungslos(
    hass: HomeAssistant, runtime, caplog: pytest.LogCaptureFixture
) -> None:
    await aendern(hass, owner="automation.keller", notification_id="gibtsnicht", message="x")

    assert runtime.notification_engine.counts.active == 0
    assert "gibtsnicht" in caplog.text


async def test_update_laesst_nicht_genannte_felder_stehen(hass: HomeAssistant, runtime) -> None:
    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        message="Feuchtigkeit",
        title="Keller",
    )

    await aendern(hass, owner="automation.keller", notification_id="leck", type="alarm")

    aktive = runtime.notification_engine.active_events()[0]
    assert aktive.title == "Keller"
    assert aktive.message == "Feuchtigkeit"


# -- dismiss ----------------------------------------------------------------


async def test_dismiss_beendet_und_schliesst_den_logeintrag(hass: HomeAssistant, runtime) -> None:
    """Testfall H und Spezifikation 28."""
    await erzeugen(hass, owner="automation.keller", notification_id="leck", message="Leck")
    await aendern(hass, owner="automation.keller", notification_id="leck", type="alarm")
    await beenden(hass, owner="automation.keller", notification_id="leck")

    assert runtime.notification_engine.counts.active == 0
    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1
    assert seite.events[0].active is False
    assert seite.events[0].close_reason is CloseReason.DISMISSED
    # Der Datensatz traegt den letzten Stand (Spezifikation 75).
    assert seite.events[0].type is NotificationType.ALARM


async def test_dismiss_ohne_bestehende_notification_ist_wirkungslos(
    hass: HomeAssistant, runtime
) -> None:
    await beenden(hass, owner="automation.keller", notification_id="gibtsnicht")
    assert runtime.notification_engine.counts.active == 0


# -- Dauer ------------------------------------------------------------------


async def test_dauer_beendet_die_notification_von_selbst(
    hass: HomeAssistant, runtime, freezer: FrozenDateTimeFactory
) -> None:
    """Spezifikation 29."""
    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        message="Leck",
        duration={"minutes": 15},
    )
    assert runtime.notification_engine.counts.active == 1

    freezer.move_to(dt_util.utcnow() + timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert runtime.notification_engine.counts.active == 0
    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.events[0].close_reason is CloseReason.EXPIRED


async def test_dismiss_vor_ablauf_der_dauer(
    hass: HomeAssistant, runtime, freezer: FrozenDateTimeFactory
) -> None:
    """Die Dauer ist eine Obergrenze, kein Zwang."""
    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        message="Leck",
        duration={"minutes": 15},
    )
    await beenden(hass, owner="automation.keller", notification_id="leck")
    assert runtime.notification_engine.counts.active == 0

    freezer.move_to(dt_util.utcnow() + timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 1
    assert seite.events[0].close_reason is CloseReason.DISMISSED


# -- Entity-Verknuepfung ----------------------------------------------------


async def test_verknuepfte_entity_wird_uebernommen(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 30."""
    await erzeugen(hass, message="Leck", entity_id="binary_sensor.leckmelder_keller")
    assert (
        runtime.notification_engine.active_events()[0].entity_id
        == "binary_sensor.leckmelder_keller"
    )


# -- Owner-Ermittlung -------------------------------------------------------


async def test_ohne_owner_und_kontext_gilt_manual(hass: HomeAssistant, runtime) -> None:
    await erzeugen(hass, message="Hinweis")
    assert runtime.notification_engine.active_events()[0].owner == DEFAULT_OWNER


async def test_owner_wird_aus_dem_automationskontext_ermittelt(
    hass: HomeAssistant, runtime
) -> None:
    """Spezifikation 25: die aufrufende Automation wird erkannt."""
    lauf = Context()
    hass.states.async_set("automation.keller_wasserleck", "on", {}, context=lauf)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE,
        {"message": "Leck", "notification_id": "leck"},
        blocking=True,
        context=Context(parent_id=lauf.id),
    )
    await hass.async_block_till_done()

    assert runtime.notification_engine.active_events()[0].owner == "automation.keller_wasserleck"


# -- Pause ------------------------------------------------------------------


async def test_pause_unterdrueckt_automations_notifications(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 42."""
    await runtime.async_set_paused(True)

    await erzeugen(hass, owner="automation.keller", notification_id="leck", message="Leck")

    assert runtime.notification_engine.counts.active == 0
    seite = await runtime.event_store.async_query(EventQuery())
    assert seite.total == 0


async def test_waehrend_der_pause_verworfene_werden_nicht_nachgeholt(
    hass: HomeAssistant, runtime
) -> None:
    """Spezifikation 43."""
    await runtime.async_set_paused(True)
    await erzeugen(hass, owner="automation.keller", notification_id="leck", message="Leck")

    await runtime.async_set_paused(False)
    await hass.async_block_till_done()

    assert runtime.notification_engine.counts.active == 0


# -- Neustart ---------------------------------------------------------------


async def test_automations_notification_ueberlebt_einen_neustart(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    await erzeugen(
        hass,
        owner="automation.keller",
        notification_id="leck",
        type="alarm",
        message="Wasserleck",
    )
    event_id = runtime.notification_engine.active_events()[0].event_id

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    danach = config_entry.runtime_data
    aktive = danach.notification_engine.active_events()
    assert len(aktive) == 1
    assert aktive[0].event_id == event_id
    assert hass.states.get(SENSOR_ALARME).state == "1"

    # Nach dem Neustart bleibt sie ueber Owner und ID ansprechbar.
    await beenden(hass, owner="automation.keller", notification_id="leck")
    assert danach.notification_engine.counts.active == 0
