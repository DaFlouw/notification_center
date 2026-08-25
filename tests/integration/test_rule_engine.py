"""Tests des ereignisbasierten State-Listeners.

Deckt die Spezifikationsabschnitte 6 (ereignisbasierte Ueberwachung),
7 (explizite Uebernahme), 17 (Zeitbedingungen), 42/43 (Pause) und
82 (Fehlerisolierung) ab.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.notification_center.rules import engine
from custom_components.notification_center.rules.intents import IntentKind
from custom_components.notification_center.rules.models import ConditionKind, Rule
from custom_components.notification_center.storage.config_models import WatchedEntity

FENSTER = "binary_sensor.fenster_wz"
TEMPERATUR = "sensor.temperatur_wz"


def fensterregel(**kwargs: object) -> Rule:
    defaults: dict[str, object] = {
        "entity_id": FENSTER,
        "kind": ConditionKind.STATE_IS,
        "states": ("on",),
        "message_template": "{name} geoeffnet",
    }
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry):
    """Eingerichtete Integration mit einer ueberwachten Entity."""
    hass.states.async_set(FENSTER, "off")
    hass.states.async_set(TEMPERATUR, "21.0", {"unit_of_measurement": "°C"})

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    laufzeit = config_entry.runtime_data
    laufzeit.config.add_entity(WatchedEntity(entity_id=FENSTER))
    laufzeit.config.add_rule(fensterregel(rule_id="rule_fenster"))
    laufzeit.rule_engine.async_refresh_tracking()
    laufzeit.pending_intents.clear()
    return laufzeit


async def test_zustandsaenderung_erzeugt_absicht(hass: HomeAssistant, runtime) -> None:
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()

    assert len(runtime.pending_intents) == 1
    absicht = runtime.pending_intents[0]
    assert absicht.kind is IntentKind.START
    assert absicht.rule_id == "rule_fenster"


async def test_zustandsende_beendet_die_notification(hass: HomeAssistant, runtime) -> None:
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    runtime.pending_intents.clear()

    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()

    assert [a.kind for a in runtime.pending_intents] == [IntentKind.STOP]


async def test_nicht_ueberwachte_entity_wird_ignoriert(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 7: nur explizit uebernommene Entities werden beobachtet."""
    hass.states.async_set(TEMPERATUR, "35.0", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()

    assert runtime.pending_intents == []


async def test_unveraenderte_bedingung_erzeugt_keine_arbeit(hass: HomeAssistant, runtime) -> None:
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    runtime.pending_intents.clear()

    # Attributaenderung ohne Zustandswechsel.
    hass.states.async_set(FENSTER, "on", {"battery": 80})
    await hass.async_block_till_done()

    assert runtime.pending_intents == []


async def test_zeitbedingung_wird_ueber_einen_timer_ausgeloest(
    hass: HomeAssistant, config_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """Spezifikation 17: der Alarm entsteht erst nach Ablauf der Wartezeit."""
    hass.states.async_set(FENSTER, "off")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    laufzeit = config_entry.runtime_data
    laufzeit.config.add_entity(WatchedEntity(entity_id=FENSTER))
    laufzeit.config.add_rule(fensterregel(rule_id="rule_fenster", duration_seconds=900))
    laufzeit.rule_engine.async_refresh_tracking()
    laufzeit.pending_intents.clear()

    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    assert laufzeit.pending_intents == []

    # Die Uhr muss tatsaechlich weiterlaufen: der Timer-Callback fragt
    # dt_util.utcnow() erneut ab und vergleicht mit dem Beginn der Bedingung.
    freezer.move_to(dt_util.utcnow() + timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert [a.kind for a in laufzeit.pending_intents] == [IntentKind.START]


async def test_zeitbedingung_verfaellt_bei_vorzeitigem_ende(
    hass: HomeAssistant, config_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(FENSTER, "off")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    laufzeit = config_entry.runtime_data
    laufzeit.config.add_entity(WatchedEntity(entity_id=FENSTER))
    laufzeit.config.add_rule(fensterregel(rule_id="rule_fenster", duration_seconds=900))
    laufzeit.rule_engine.async_refresh_tracking()

    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    hass.states.async_set(FENSTER, "off")
    await hass.async_block_till_done()
    laufzeit.pending_intents.clear()

    # Die Uhr muss tatsaechlich weiterlaufen: der Timer-Callback fragt
    # dt_util.utcnow() erneut ab und vergleicht mit dem Beginn der Bedingung.
    freezer.move_to(dt_util.utcnow() + timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert laufzeit.pending_intents == []


async def test_pause_unterdrueckt_neue_notifications(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 42."""
    await runtime.async_set_paused(True)

    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()

    assert runtime.pending_intents == []


async def test_fortsetzen_bewertet_die_aktuellen_zustaende_neu(
    hass: HomeAssistant, runtime
) -> None:
    """Spezifikation 43: was waehrend der Pause entstand, wird nachgeholt."""
    await runtime.async_set_paused(True)
    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()
    assert runtime.pending_intents == []

    await runtime.async_set_paused(False)
    await hass.async_block_till_done()

    assert [a.kind for a in runtime.pending_intents] == [IntentKind.START]


async def test_entity_ohne_zustand_wird_uebersprungen(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Eine ueberwachte, aber nicht vorhandene Entity darf nicht stoeren."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    laufzeit = config_entry.runtime_data
    laufzeit.config.add_entity(WatchedEntity(entity_id="sensor.gibtsnicht"))
    laufzeit.rule_engine.async_refresh_tracking()

    await laufzeit.rule_engine.async_evaluate_all()
    await hass.async_block_till_done()

    assert laufzeit.pending_intents == []


async def test_fehlerhafte_regel_stoppt_die_uebrigen_nicht(
    hass: HomeAssistant, runtime, caplog: pytest.LogCaptureFixture
) -> None:
    """Spezifikation 82: Fehlerisolierung je Regel.

    Der Fehler wird in der Auswertung selbst ausgeloest. Ihn ueber
    beschaedigte Regeldaten zu erzwingen waere unzuverlaessig, weil die
    Auswertung solche Faelle meist schon als 'nicht erfuellt' abfaengt.
    """
    runtime.config.add_rule(fensterregel(rule_id="rule_kaputt"))
    echte_auswertung = engine.evaluate_rule

    def _auswerten(rule, snapshot, state, now):
        if rule.rule_id == "rule_kaputt":
            raise RuntimeError("absichtlicher Fehler")
        return echte_auswertung(rule, snapshot, state, now)

    with patch.object(engine, "evaluate_rule", _auswerten):
        hass.states.async_set(FENSTER, "on")
        await hass.async_block_till_done()

    assert [a.rule_id for a in runtime.pending_intents] == ["rule_fenster"]
    assert "rule_kaputt" in caplog.text
    assert "absichtlicher Fehler" in caplog.text


async def test_ueberwachung_folgt_der_konfiguration(hass: HomeAssistant, runtime) -> None:
    """Nach dem Entfernen wird die Entity nicht mehr beobachtet."""
    runtime.config.remove_entity(FENSTER)
    runtime.rule_engine.async_refresh_tracking()

    hass.states.async_set(FENSTER, "on")
    await hass.async_block_till_done()

    assert runtime.pending_intents == []
