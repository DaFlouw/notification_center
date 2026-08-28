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
    INTEGRATION_VERSION,
    PANEL_URL_PATH,
)
from custom_components.notification_center.coordinator import NotificationCenterRuntime
from custom_components.notification_center.frontend.panel import card_resource
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
    assert vorschlaege
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


async def test_ersetzen_lehnt_eine_unbekannte_entity_ab(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Issue 10: sonst nimmt ein Tippfehler die Ueberwachung still ausser Betrieb.

    Die Oberflaeche fragt die neue Kennung als freien Text ab. Wird eine
    Entity angenommen, die es nicht gibt, faellt die richtige aus der
    Ueberwachung und ihre Regeln haengen an etwas, das nie einen Zustand
    meldet.
    """
    client = await hass_ws_client(hass)
    runtime.config.add_entity(WatchedEntity(entity_id=FENSTER))
    antwort = await sende(
        client,
        "save_rule",
        rule={"entity_id": FENSTER, "kind": str(ConditionKind.STATE_IS), "states": ["on"]},
    )
    rule_id = antwort["result"]["rule"]["rule_id"]

    antwort = await sende(
        client,
        "replace_entity",
        old_entity_id=FENSTER,
        new_entity_id="binary_sensor.gibt_es_nicht",
    )

    assert antwort["success"] is False
    assert "gibt_es_nicht" in antwort["error"]["message"]

    # Nichts darf sich verschoben haben.
    assert FENSTER in runtime.config.entities
    assert runtime.config.rules[rule_id].entity_id == FENSTER


async def test_ersetzen_erlaubt_eine_registrierte_entity_ohne_zustand(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Eine Entity kann voruebergehend nicht geladen sein.

    Sie traegt dann keinen Zustand, gehoert aber zur Anlage. Deshalb wird die
    Entity-Registry mitgefragt und nicht nur die Zustandsmaschine.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    eintrag = registry.async_get_or_create(
        "binary_sensor", "demo", "fenster_ohne_zustand", suggested_object_id="fenster_offline"
    )
    assert hass.states.get(eintrag.entity_id) is None

    client = await hass_ws_client(hass)
    runtime.config.add_entity(WatchedEntity(entity_id=FENSTER))

    antwort = await sende(
        client,
        "replace_entity",
        old_entity_id=FENSTER,
        new_entity_id=eintrag.entity_id,
    )

    assert antwort["success"] is True
    assert eintrag.entity_id in runtime.config.entities


# -- Einrichtungsassistent (Spezifikation 67) ------------------------------


async def test_einrichtung_ist_zunaechst_offen(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    client = await hass_ws_client(hass)
    antwort = await sende(client, "get_config")
    assert antwort["result"]["settings"]["setup_completed"] is False


async def test_einrichtung_laesst_sich_abschliessen(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Der Assistent muss uebersprungen werden koennen."""
    client = await hass_ws_client(hass)
    await sende(client, "set_settings", setup_completed=True)

    antwort = await sende(client, "get_config")
    assert antwort["result"]["settings"]["setup_completed"] is True


# -- Eskalationsgruppen ueber die API --------------------------------------


async def test_gruppe_speichern_und_eskalieren(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Spezifikation 19 und 20 durchgehend ueber die API."""
    client = await hass_ws_client(hass)
    await sende(client, "add_entities", entity_ids=[TEMPERATUR])

    stufen = [
        {
            "rule_id": f"rule_stufe_{level}",
            "entity_id": TEMPERATUR,
            "kind": "numeric",
            "operator": "gt",
            "threshold": schwelle,
            "type": typ,
            "group_id": "group_temp",
            "level": level,
            "message_template": "{name} {value}",
        }
        for level, schwelle, typ in ((1, 25.0, "info"), (2, 28.0, "warning"))
    ]

    antwort = await sende(
        client,
        "save_group",
        group={
            "group_id": "group_temp",
            "entity_id": TEMPERATUR,
            "name": "Temperatur",
            "rules": stufen,
        },
    )
    assert antwort["success"] is True

    hass.states.async_set(TEMPERATUR, "26", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    assert runtime.notification_engine.counts.info == 1

    hass.states.async_set(TEMPERATUR, "29", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    assert runtime.notification_engine.counts.info == 0
    assert runtime.notification_engine.counts.warning == 1

    verlauf = await sende(client, "get_history")
    assert verlauf["result"]["total"] == 2


async def test_ungueltige_gruppe_wird_abgelehnt(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Nicht monotone Schwellen haetten keine wohldefinierte Reihenfolge."""
    client = await hass_ws_client(hass)
    await sende(client, "add_entities", entity_ids=[TEMPERATUR])

    antwort = await sende(
        client,
        "save_group",
        group={
            "group_id": "group_temp",
            "entity_id": TEMPERATUR,
            "name": "Temperatur",
            "rules": [
                {
                    "rule_id": "rule_1",
                    "entity_id": TEMPERATUR,
                    "kind": "numeric",
                    "operator": "gt",
                    "threshold": 30.0,
                    "group_id": "group_temp",
                    "level": 1,
                },
                {
                    "rule_id": "rule_2",
                    "entity_id": TEMPERATUR,
                    "kind": "numeric",
                    "operator": "gt",
                    "threshold": 25.0,
                    "group_id": "group_temp",
                    "level": 2,
                },
            ],
        },
    )

    assert antwort["success"] is False
    assert antwort["error"]["code"] == "invalid_input"


# -- Fehlertickets ----------------------------------------------------------


async def test_abonnement_liefert_den_anfangszustand(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Fehlerticket 7.

    Das erste Ergebnis des Abonnements traegt bereits den vollstaendigen
    Stand. Das Frontend holt ihn zusaetzlich ueber get_active, weil
    subscribeMessage nur Folgeereignisse durchreicht; beide Wege muessen
    dasselbe liefern.
    """
    await hass.services.async_call(
        DOMAIN,
        "create",
        {"notification_id": "leck", "message": "Wasserleck", "type": "alarm"},
        blocking=True,
    )
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    abonnement = await sende(client, "subscribe_updates")
    abruf = await sende(client, "get_active")

    assert abonnement["result"]["counts"]["alarm"] == 1
    assert len(abonnement["result"]["active"]) == 1
    # Nicht die vollstaendigen Datensaetze vergleichen: die Dauer eines
    # aktiven Ereignisses wird bei jedem Abruf neu berechnet.
    assert [e["event_id"] for e in abruf["result"]["active"]] == [
        e["event_id"] for e in abonnement["result"]["active"]
    ]
    assert abruf["result"]["counts"] == abonnement["result"]["counts"]


async def test_regel_mit_zustand_ist_nicht(hass: HomeAssistant, runtime, hass_ws_client) -> None:
    """Fehlerticket 4 durchgehend ueber die API."""
    client = await hass_ws_client(hass)
    hass.states.async_set("sensor.waschmaschine", "idle", {"options": ["idle", "running"]})
    await hass.async_block_till_done()

    await sende(client, "add_entities", entity_ids=["sensor.waschmaschine"])
    antwort = await sende(
        client,
        "save_rule",
        rule={
            "entity_id": "sensor.waschmaschine",
            "kind": "state_is_not",
            "type": "info",
            "states": ["idle"],
            "message_template": "{name} läuft",
        },
    )
    assert antwort["success"] is True
    assert runtime.notification_engine.counts.active == 0

    hass.states.async_set("sensor.waschmaschine", "running", {"options": ["idle", "running"]})
    await hass.async_block_till_done()
    assert runtime.notification_engine.counts.info == 1

    hass.states.async_set("sensor.waschmaschine", "idle", {"options": ["idle", "running"]})
    await hass.async_block_till_done()
    assert runtime.notification_engine.counts.active == 0


async def test_zustandsauswahl_kommt_ueber_die_api(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Fehlerticket 5: vollstaendig auch ohne Historie."""
    client = await hass_ws_client(hass)
    antwort = await sende(client, "get_suggestions", entity_id=FENSTER)
    assert antwort["result"]["states"] == ["on", "off"]


async def test_unsichere_vorschlaege_kommen_nicht_ueber_die_api(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Fehlerticket 3."""
    hass.states.async_set("binary_sensor.wasser_keller", "off", {"friendly_name": "Wasser Keller"})
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    ohne = await sende(client, "get_suggestions", entity_id="binary_sensor.wasser_keller")
    assert all(not v["uncertain"] for v in ohne["result"]["suggestions"])

    mit = await sende(
        client,
        "get_suggestions",
        entity_id="binary_sensor.wasser_keller",
        include_uncertain=True,
    )
    assert any(v["uncertain"] for v in mit["result"]["suggestions"])


async def test_card_ist_als_lovelace_ressource_eingetragen(hass: HomeAssistant, runtime) -> None:
    """Fehlerticket 8.

    Ueber die Ressourcenliste findet die Kartenauswahl das Modul zuverlaessig
    wieder; als blosses Zusatzmodul war es nach einem Seitenwechsel weg.
    """
    eintrag = card_resource(hass)
    assert eintrag is not None
    # Home Assistant legt die Art je nach Version unter 'res_type' oder 'type' ab.
    assert (eintrag.get("res_type") or eintrag.get("type")) == "module"
    assert eintrag["url"].endswith("/notification-center-card.js")
    assert INTEGRATION_VERSION in eintrag["url"]


async def test_card_ressource_wird_nicht_doppelt_eingetragen(
    hass: HomeAssistant, runtime, config_entry: MockConfigEntry
) -> None:
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    resources = hass.data["lovelace"].resources
    treffer = [
        eintrag
        for eintrag in resources.async_items()
        if "notification-center-card.js" in str(eintrag.get("url", ""))
    ]
    assert len(treffer) == 1


# -- Versionierte Auslieferung (Fehlerticket 11) ---------------------------


async def test_frontend_liegt_unter_einem_versionierten_pfad(hass: HomeAssistant, runtime) -> None:
    """Fehlerticket 11.

    Steckt die Version nur in einer Abfragezeichenkette an der Einstiegsdatei,
    holt der Browser zwar diese neu, laedt ihre relativen Importe aber weiter
    aus dem Zwischenspeicher: neues Panel, alte Bausteine. Genau so blieb das
    Dashboard leer. Ueber einen versionierten Pfad erben alle Importe die
    Version.
    """
    from custom_components.notification_center.frontend.panel import (
        CARD_URL,
        PANEL_MODULE_URL,
        VERSIONED_BASE,
    )

    assert VERSIONED_BASE.endswith(f"/{INTEGRATION_VERSION}")
    assert PANEL_MODULE_URL.startswith(VERSIONED_BASE)
    assert CARD_URL.startswith(VERSIONED_BASE)
    assert "?" not in PANEL_MODULE_URL
    assert "?" not in CARD_URL


async def test_antworten_tragen_die_integrationsversion(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Damit ein zwischengespeichertes Frontend sich selbst erkennen kann."""
    client = await hass_ws_client(hass)
    antwort = await sende(client, "get_active")
    assert antwort["result"]["version"] == INTEGRATION_VERSION


# -- Einrichtungsassistent (Fehlerticket 9) --------------------------------


async def test_assistent_gilt_als_erledigt_wenn_entities_ueberwacht_werden(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Fehlerticket 9.

    Wer bereits Entities ueberwacht, hat die Einrichtung hinter sich, auch
    wenn der Assistent nie ausdruecklich bestaetigt wurde.
    """
    client = await hass_ws_client(hass)
    assert runtime.config.settings.setup_completed is False

    vorher = await sende(client, "get_config")
    assert vorher["result"]["settings"]["setup_completed"] is False

    await sende(client, "add_entities", entity_ids=[FENSTER])

    nachher = await sende(client, "get_config")
    assert nachher["result"]["settings"]["setup_completed"] is True


# -- Gruppierung nach Geschoss und Raum (Fehlerticket 10) ------------------


async def test_ueberwachte_entities_tragen_raum_und_geschoss(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    """Fehlerticket 10: ohne Ort waere die Regeluebersicht nur eine Liste."""
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import floor_registry as fr

    geschoss = fr.async_get(hass).async_create("Erdgeschoss")
    bereich = ar.async_get(hass).async_create("Wohnzimmer")
    ar.async_get(hass).async_update(bereich.id, floor_id=geschoss.floor_id)

    registry = er.async_get(hass)
    eintrag = registry.async_get_or_create("binary_sensor", "demo", "fenster")
    registry.async_update_entity(eintrag.entity_id, area_id=bereich.id)
    hass.states.async_set(eintrag.entity_id, "off", {"friendly_name": "Fenster"})
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await sende(client, "add_entities", entity_ids=[eintrag.entity_id])

    antwort = await sende(client, "get_config")
    platzierung = next(
        e for e in antwort["result"]["entities"] if e["entity_id"] == eintrag.entity_id
    )

    assert platzierung["area_name"] == "Wohnzimmer"
    assert platzierung["floor_name"] == "Erdgeschoss"
    assert platzierung["name"] == "Fenster"


async def test_entity_ohne_raum_bleibt_verwendbar(
    hass: HomeAssistant, runtime, hass_ws_client
) -> None:
    client = await hass_ws_client(hass)
    await sende(client, "add_entities", entity_ids=[FENSTER])

    antwort = await sende(client, "get_config")
    platzierung = antwort["result"]["entities"][0]

    assert platzierung["area_name"] is None
    assert platzierung["floor_name"] is None
    assert platzierung["name"]
