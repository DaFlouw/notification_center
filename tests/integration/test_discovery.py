"""Tests der Discovery-Engine.

Deckt die Spezifikationsabschnitte 7 bis 9, 11, 14, 16 und 64 bis 65 ab.
"""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.coordinator import NotificationCenterRuntime
from custom_components.notification_center.rules.models import (
    ConditionKind,
    NumericOperator,
    Rule,
)
from custom_components.notification_center.storage.config_models import WatchedEntity

FENSTER = "binary_sensor.fenster_wz"
TEMPERATUR = "sensor.temperatur_wz"
WASCHMASCHINE = "sensor.waschmaschine_status"


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry) -> NotificationCenterRuntime:
    hass.states.async_set(
        FENSTER, "off", {"device_class": "window", "friendly_name": "Fenster Wohnzimmer"}
    )
    hass.states.async_set(
        TEMPERATUR,
        "21.4",
        {
            "device_class": "temperature",
            "state_class": "measurement",
            "unit_of_measurement": "°C",
            "friendly_name": "Temperatur Wohnzimmer",
        },
    )
    hass.states.async_set(
        WASCHMASCHINE,
        "idle",
        {
            "options": ["idle", "running", "paused", "finished"],
            "remaining_time": 42,
            "friendly_name": "Waschmaschine Status",
            "programme": ["kochwaesche", "buntwaesche"],
        },
    )

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry.runtime_data


# -- Suche ------------------------------------------------------------------


async def test_discovery_findet_entities(hass: HomeAssistant, runtime) -> None:
    treffer = runtime.discovery.discover_entities()
    gefunden = {eintrag["entity_id"] for eintrag in treffer}

    assert FENSTER in gefunden
    assert TEMPERATUR in gefunden


async def test_discovery_filtert_nach_typ(hass: HomeAssistant, runtime) -> None:
    treffer = runtime.discovery.discover_entities(domain="binary_sensor")
    assert {e["domain"] for e in treffer} == {"binary_sensor"}


async def test_discovery_sucht_in_name_und_id(hass: HomeAssistant, runtime) -> None:
    ueber_namen = runtime.discovery.discover_entities(search="Wohnzimmer")
    assert len(ueber_namen) >= 2

    ueber_id = runtime.discovery.discover_entities(search="waschmaschine")
    assert [e["entity_id"] for e in ueber_id] == [WASCHMASCHINE]


async def test_discovery_uebergeht_ungeeignete_domains(hass: HomeAssistant, runtime) -> None:
    hass.states.async_set("automation.irgendwas", "on")
    await hass.async_block_till_done()

    treffer = runtime.discovery.discover_entities()
    assert all(not e["entity_id"].startswith("automation.") for e in treffer)


async def test_ueberwachte_entities_stehen_oben(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 64: der Status ist in der Trefferliste sichtbar."""
    runtime.config.add_entity(WatchedEntity(entity_id=TEMPERATUR))
    runtime.config.add_rule(
        Rule(
            rule_id="rule_temp",
            entity_id=TEMPERATUR,
            kind=ConditionKind.NUMERIC,
            operator=NumericOperator.GT,
            threshold=28.0,
        )
    )

    treffer = runtime.discovery.discover_entities()

    assert treffer[0]["entity_id"] == TEMPERATUR
    assert treffer[0]["monitored"] is True
    assert treffer[0]["rule_count"] == 1


async def test_nicht_ueberwachte_melden_ob_vorschlaege_zu_erwarten_sind(
    hass: HomeAssistant, runtime
) -> None:
    """Fehlerticket 2: keine Zahl, die spaeter nicht stimmt.

    Die Trefferliste kennt nur Metadaten, die Vorschlagsliste zusaetzlich die
    Historie. Eine hier gebildete Zahl waere regelmaessig zu niedrig.
    """
    treffer = runtime.discovery.discover_entities(search="Fenster")
    assert treffer[0]["monitored"] is False
    assert treffer[0]["has_suggestions"] is True
    assert "suggestion_count" not in treffer[0]


# -- Metadaten --------------------------------------------------------------


async def test_metadaten_kommen_aus_dem_zustand(hass: HomeAssistant, runtime) -> None:
    metadata = runtime.discovery.metadata_for(TEMPERATUR)
    assert metadata is not None
    assert metadata.device_class == "temperature"
    assert metadata.state_class == "measurement"
    assert metadata.unit == "°C"
    assert metadata.is_numeric is True


async def test_bereich_kommt_vom_geraet(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Faellt die Entity nicht selbst in einen Bereich, gilt der des Geraets."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    laufzeit = config_entry.runtime_data

    bereich = ar.async_get(hass).async_create("Keller")
    geraet = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("demo", "waschmaschine")},
        name="Waschmaschine",
    )
    dr.async_get(hass).async_update_device(geraet.id, area_id=bereich.id)

    registry = er.async_get(hass)
    eintrag = registry.async_get_or_create(
        "sensor", "demo", "wm_status", device_id=geraet.id, config_entry=config_entry
    )
    hass.states.async_set(eintrag.entity_id, "idle")
    await hass.async_block_till_done()

    metadata = laufzeit.discovery.metadata_for(eintrag.entity_id)
    assert metadata is not None
    assert metadata.device_id == geraet.id
    assert metadata.area_id == bereich.id


async def test_unbekannte_entity_hat_keine_metadaten(hass: HomeAssistant, runtime) -> None:
    assert runtime.discovery.metadata_for("sensor.gibtsnicht") is None


# -- Attribute (Spezifikation 16) ------------------------------------------


async def test_nur_auswertbare_attribute_werden_angeboten(hass: HomeAssistant, runtime) -> None:
    attribute = runtime.discovery.usable_attributes(WASCHMASCHINE)
    namen = {eintrag["name"] for eintrag in attribute}

    assert "remaining_time" in namen
    # Listen taugen nicht als Regelgrundlage.
    assert "programme" not in namen
    # Rein darstellende Angaben ebenfalls nicht.
    assert "friendly_name" not in namen
    assert "options" not in namen


async def test_attributarten_werden_erkannt(hass: HomeAssistant, runtime) -> None:
    attribute = {e["name"]: e["kind"] for e in runtime.discovery.usable_attributes(WASCHMASCHINE)}
    assert attribute["remaining_time"] == "numeric"


# -- Zustandsauswahl (Spezifikation 14) ------------------------------------


async def test_zustaende_kommen_aus_den_optionen(hass: HomeAssistant, runtime) -> None:
    """Kein freies Textfeld: der Editor bietet die echten Werte an."""
    assert runtime.discovery.available_states(WASCHMASCHINE) == [
        "idle",
        "running",
        "paused",
        "finished",
    ]


async def test_binaersensor_hat_zwei_zustaende(hass: HomeAssistant, runtime) -> None:
    assert runtime.discovery.available_states(FENSTER) == ["on", "off"]


# -- Geraete (Spezifikation 8 und 65) --------------------------------------


async def test_geraet_gruppiert_seine_entities(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    laufzeit = config_entry.runtime_data

    geraet = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("demo", "waschmaschine")},
        name="Waschmaschine",
    )
    registry = er.async_get(hass)
    for unique_id, domain in (("wm_status", "sensor"), ("wm_tuer", "binary_sensor")):
        eintrag = registry.async_get_or_create(
            domain, "demo", unique_id, device_id=geraet.id, config_entry=config_entry
        )
        hass.states.async_set(eintrag.entity_id, "off")
    await hass.async_block_till_done()

    gruppe = laufzeit.discovery.get_device_suggestions(geraet.id)

    assert gruppe["name"] == "Waschmaschine"
    assert len(gruppe["entities"]) == 2


# -- Historienanalyse (Spezifikation 11) -----------------------------------


async def test_ohne_recorder_gibt_es_keine_historienanalyse(hass: HomeAssistant, runtime) -> None:
    """Die Analyse darf ohne Recorder nicht scheitern, nur leer bleiben."""
    numerisch, zustaende = await runtime.discovery.async_analyze_history(TEMPERATUR)
    assert numerisch is None
    assert zustaende is None


async def test_vorschlaege_kommen_auch_ohne_historie(hass: HomeAssistant, runtime) -> None:
    """Metadaten allein tragen bereits einen Vorschlag."""
    vorschlaege = await runtime.discovery.async_get_entity_suggestions(FENSTER)

    assert vorschlaege[0].duration_seconds == 900


async def test_vorschlaege_einer_unbekannten_entity_sind_leer(hass: HomeAssistant, runtime) -> None:
    assert await runtime.discovery.async_get_entity_suggestions("sensor.gibtsnicht") == []


# -- Unsichere Vorschlaege (Fehlerticket 3) --------------------------------


async def test_unsichere_vorschlaege_werden_nicht_angeboten(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Ein Vorschlag allein aus einem Wort im Namen kostet mehr Vertrauen,
    als er einbringt."""
    hass.states.async_set("binary_sensor.wasser_keller", "off", {"friendly_name": "Wasser Keller"})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    laufzeit = config_entry.runtime_data

    vorschlaege = await laufzeit.discovery.async_get_entity_suggestions(
        "binary_sensor.wasser_keller"
    )

    # Der aus dem Namen geratene Vorschlag faellt weg; die immer gueltigen
    # Zustandsvorschlaege an und aus bleiben (Issue 1).
    assert all(not v.confidence.is_uncertain for v in vorschlaege)
    assert {v.key for v in vorschlaege} == {"on_off_on", "on_off_off"}


async def test_unsichere_vorschlaege_bleiben_erreichbar(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    hass.states.async_set("binary_sensor.wasser_keller", "off", {"friendly_name": "Wasser Keller"})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    laufzeit = config_entry.runtime_data

    vorschlaege = await laufzeit.discovery.async_get_entity_suggestions(
        "binary_sensor.wasser_keller", include_uncertain=True
    )
    assert any(v.confidence.is_uncertain for v in vorschlaege)


async def test_sichere_vorschlaege_bleiben(hass: HomeAssistant, runtime) -> None:
    vorschlaege = await runtime.discovery.async_get_entity_suggestions(FENSTER)
    assert vorschlaege[0].confidence.is_uncertain is False


# -- Zustandsauswahl (Fehlerticket 5) --------------------------------------


async def test_zustandsauswahl_ohne_historie_ist_vollstaendig(hass: HomeAssistant, runtime) -> None:
    """Auch kurz nach einem Neustart, ohne jede Beobachtung."""
    assert runtime.discovery.available_states(FENSTER) == ["on", "off"]


async def test_zustandsauswahl_nutzt_die_optionen_der_entity(hass: HomeAssistant, runtime) -> None:
    assert runtime.discovery.available_states(WASCHMASCHINE) == [
        "idle",
        "running",
        "paused",
        "finished",
    ]


async def test_zustandsauswahl_kennt_seltene_zustaende_einer_domaene(
    hass: HomeAssistant, runtime
) -> None:
    hass.states.async_set("lock.haustuer", "locked", {"friendly_name": "Haustür"})
    await hass.async_block_till_done()

    zustaende = runtime.discovery.available_states("lock.haustuer")
    assert "jammed" in zustaende
    assert "unlocked" in zustaende


async def test_zustandsauswahl_ohne_recorder_bleibt_brauchbar(hass: HomeAssistant, runtime) -> None:
    zustaende = await runtime.discovery.async_available_states(FENSTER)
    assert zustaende == ["on", "off"]
