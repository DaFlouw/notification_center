"""Tests der WebSocket-API und der Panel-Registrierung.

Deckt die Spezifikationsabschnitte 39, 45 bis 50, 59 bis 61 und 69 ab.
"""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.const import (
    API_VERSION,
    DOMAIN,
    PANEL_URL_PATH,
)
from custom_components.notification_center.coordinator import NotificationCenterRuntime
from custom_components.notification_center.notifications.models import NotificationType
from custom_components.notification_center.rules.models import ConditionKind
from custom_components.notification_center.storage.config_models import WatchedEntity

FENSTER = "binary_sensor.fenster_wz"
TEMPERATUR = "sensor.temperatur_wz"


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry) -> NotificationCenterRuntime:
    hass.states.async_set(
        FENSTER, "off", {"device_class": "window", "friendly_name": "Fenster Wohnzimmer"}
    )
    hass.states.async_set(
        TEMPERATUR,
        "21.0",
        {
            "device_class": "temperature",
            "unit_of_measurement": "°C",
            "friendly_name": "Temperatur Wohnzimmer",
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry.runtime_data


async def sende(client, typ: str, **daten):
    await client.send_json_auto_id({"type": f"{DOMAIN}/{typ}", **daten})
    return await client.receive_json()


# -- Panel ------------------------------------------------------------------


async def test_panel_ist_angemeldet(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 69."""
    assert PANEL_URL_PATH in hass.data["frontend_panels"]


async def test_panel_ist_fuer_alle_sichtbar(hass: HomeAssistant, runtime) -> None:
    """Spezifikation 72: keine eigene Rechteverwaltung."""
    panel = hass.data["frontend_panels"][PANEL_URL_PATH]
    assert panel.require_admin is False


async def test_panel_verschwindet_beim_entladen(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data["frontend_panels"]


# -- Lesen ------------------------------------------------------------------


async def test_get_active_liefert_zaehler_und_version(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    client = await hass_ws_client(hass)
    antwort = await sende(client, "get_active")

    assert antwort["success"] is True
    assert antwort["result"]["api_version"] == API_VERSION
    assert antwort["result"]["counts"]["active"] == 0
    assert antwort["result"]["active"] == []
    assert antwort["result"]["paused"] is False


async def test_get_config_liefert_die_konfiguration(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    client = await hass_ws_client(hass)
    antwort = await sende(client, "get_config")

    ergebnis = antwort["result"]
    assert ergebnis["entities"] == []
    assert ergebnis["settings"]["paused"] is False
    assert 0 in ergebnis["options"]["retention_days"]


# -- Konfiguration aendern --------------------------------------------------


async def test_entity_uebernehmen_und_entfernen(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    client = await hass_ws_client(hass)

    antwort = await sende(client, "add_entities", entity_ids=[FENSTER])
    assert antwort["success"] is True
    assert FENSTER in runtime.config.entities

    antwort = await sende(client, "remove_entity", entity_id=FENSTER)
    assert antwort["success"] is True
    assert FENSTER not in runtime.config.entities


async def test_regel_speichern_und_loeschen(hass: HomeAssistant, runtime, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await sende(client, "add_entities", entity_ids=[FENSTER])

    antwort = await sende(
        client,
        "save_rule",
        rule={
            "entity_id": FENSTER,
            "kind": str(ConditionKind.STATE_IS),
            "type": str(NotificationType.WARNING),
            "states": ["on"],
            "message_template": "{name} offen",
        },
    )
    assert antwort["success"] is True
    rule_id = antwort["result"]["rule"]["rule_id"]
    assert rule_id in runtime.config.rules

    antwort = await sende(client, "delete_rule", rule_id=rule_id)
    assert antwort["success"] is True
    assert rule_id not in runtime.config.rules


async def test_ungueltige_regel_wird_abgelehnt(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Die Validierung des Backends greift auch ueber die API."""
    client = await hass_ws_client(hass)
    await sende(client, "add_entities", entity_ids=[FENSTER])

    antwort = await sende(
        client,
        "save_rule",
        rule={"entity_id": FENSTER, "kind": str(ConditionKind.STATE_IS), "states": []},
    )

    assert antwort["success"] is False
    assert antwort["error"]["code"] == "invalid_input"


async def test_regel_fuer_nicht_ueberwachte_entity_wird_abgelehnt(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    client = await hass_ws_client(hass)
    antwort = await sende(
        client,
        "save_rule",
        rule={
            "entity_id": FENSTER,
            "kind": str(ConditionKind.STATE_IS),
            "states": ["on"],
        },
    )
    assert antwort["success"] is False
    assert antwort["error"]["code"] == "invalid_config"


async def test_einstellungen_aendern(hass: HomeAssistant, runtime, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    antwort = await sende(client, "set_settings", retention_days=30, paused=True)

    assert antwort["result"]["settings"]["retention_days"] == 30
    assert runtime.config.settings.paused is True


async def test_unzulaessige_einstellung_wird_abgelehnt(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    client = await hass_ws_client(hass)
    antwort = await sende(client, "set_settings", retention_days=42)
    assert antwort["success"] is False


# -- Discovery --------------------------------------------------------------


async def test_discover_findet_entities(hass: HomeAssistant, runtime, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    antwort = await sende(client, "discover", search="Fenster")

    gefunden = [e["entity_id"] for e in antwort["result"]["entities"]]
    assert FENSTER in gefunden


async def test_vorschlaege_enthalten_begruendungen(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Spezifikation 13."""
    client = await hass_ws_client(hass)
    antwort = await sende(client, "get_suggestions", entity_id=FENSTER)

    vorschlaege = antwort["result"]["suggestions"]
    assert len(vorschlaege) == 1
    assert vorschlaege[0]["reasons"]
    assert antwort["result"]["states"] == ["on", "off"]


# -- Historie ---------------------------------------------------------------


async def test_historie_wird_serverseitig_geblaettert(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Spezifikation 61: nie das ganze Log."""
    client = await hass_ws_client(hass)

    for index in range(60):
        await hass.services.async_call(
            DOMAIN,
            "create",
            {"notification_id": f"n{index}", "message": f"Meldung {index}"},
            blocking=True,
        )
        await hass.services.async_call(
            DOMAIN, "dismiss", {"notification_id": f"n{index}"}, blocking=True
        )
    await hass.async_block_till_done()

    antwort = await sende(client, "get_history")
    assert len(antwort["result"]["events"]) == 50
    assert antwort["result"]["total"] == 60
    assert antwort["result"]["has_more"] is True

    weiter = await sende(client, "get_history", offset=50)
    assert len(weiter["result"]["events"]) == 10
    assert weiter["result"]["has_more"] is False


async def test_historie_filtert_nach_typ(hass: HomeAssistant, runtime, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await hass.services.async_call(
        DOMAIN, "create", {"notification_id": "a", "message": "Info", "type": "info"}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN,
        "create",
        {"notification_id": "b", "message": "Alarm", "type": "alarm"},
        blocking=True,
    )
    await hass.async_block_till_done()

    antwort = await sende(client, "get_history", types=["alarm"])
    assert antwort["result"]["total"] == 1
    assert antwort["result"]["events"][0]["message"] == "Alarm"


async def test_historie_sucht_serverseitig(hass: HomeAssistant, runtime, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await hass.services.async_call(
        DOMAIN, "create", {"notification_id": "a", "message": "Wasserleck"}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, "create", {"notification_id": "b", "message": "Fenster offen"}, blocking=True
    )
    await hass.async_block_till_done()

    antwort = await sende(client, "get_history", search="wasser")
    assert antwort["result"]["total"] == 1


# -- Historie loeschen ------------------------------------------------------


async def test_aktiver_eintrag_wird_nicht_geloescht(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Spezifikation 39."""
    client = await hass_ws_client(hass)
    await hass.services.async_call(
        DOMAIN, "create", {"notification_id": "a", "message": "Laeuft"}, blocking=True
    )
    await hass.async_block_till_done()

    event_id = runtime.notification_engine.active_events()[0].event_id
    antwort = await sende(client, "delete_event", event_id=event_id)

    assert antwort["result"]["deleted"] is False


async def test_alle_loeschen_behaelt_aktive(hass: HomeAssistant, runtime, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await hass.services.async_call(
        DOMAIN, "create", {"notification_id": "a", "message": "Beendet"}, blocking=True
    )
    await hass.services.async_call(DOMAIN, "dismiss", {"notification_id": "a"}, blocking=True)
    await hass.services.async_call(
        DOMAIN, "create", {"notification_id": "b", "message": "Laeuft"}, blocking=True
    )
    await hass.async_block_till_done()

    antwort = await sende(client, "clear_history")
    assert antwort["result"]["deleted"] == 1
    assert runtime.notification_engine.counts.active == 1


# -- Abonnement -------------------------------------------------------------


async def test_abonnement_stellt_aenderungen_zu(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Spezifikation 45: kein Polling."""
    client = await hass_ws_client(hass)

    erst = await sende(client, "subscribe_updates")
    assert erst["success"] is True
    assert erst["result"]["counts"]["active"] == 0

    await hass.services.async_call(
        DOMAIN,
        "create",
        {"notification_id": "leck", "message": "Wasserleck", "type": "alarm"},
        blocking=True,
    )
    await hass.async_block_till_done()

    nachricht = await client.receive_json()
    assert nachricht["type"] == "event"
    assert nachricht["event"]["counts"]["alarm"] == 1
    assert nachricht["event"]["active"][0]["message"] == "Wasserleck"


# -- Entity ersetzen --------------------------------------------------------


async def test_entity_ersetzen_nimmt_regeln_mit(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Spezifikation 66."""
    client = await hass_ws_client(hass)
    runtime.config.add_entity(WatchedEntity(entity_id=FENSTER))
    antwort = await sende(
        client,
        "save_rule",
        rule={
            "entity_id": FENSTER,
            "kind": str(ConditionKind.STATE_IS),
            "states": ["on"],
        },
    )
    rule_id = antwort["result"]["rule"]["rule_id"]

    hass.states.async_set("binary_sensor.fenster_neu", "off")
    await hass.async_block_till_done()

    antwort = await sende(
        client,
        "replace_entity",
        old_entity_id=FENSTER,
        new_entity_id="binary_sensor.fenster_neu",
    )

    assert antwort["success"] is True
    assert runtime.config.rules[rule_id].entity_id == "binary_sensor.fenster_neu"
    assert FENSTER not in runtime.config.entities
