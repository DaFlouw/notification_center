"""Tests der Uebernahme der persistenten Benachrichtigungen von Home Assistant.

Das sind die Meldungen hinter der Glocke in der Seitenleiste. Geprueft wird am
Ergebnis: erscheint die Meldung im Notification Center, endet sie dort wieder,
und bleibt sie weg, wenn die Uebernahme abgeschaltet ist.

Diese Tests brauchen eine laufende Home-Assistant-Instanz: die Komponente
``persistent_notification`` liefert ihre Aenderungen ueber einen eigenen
Rueckruf, und genau dessen Anbindung ist hier der Gegenstand.
"""

from __future__ import annotations

import pytest
from homeassistant.components import persistent_notification as pn
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.coordinator import NotificationCenterRuntime
from custom_components.notification_center.notifications.ha_system import (
    MAX_MESSAGE_LENGTH,
    kurzfassung,
    titel,
)
from custom_components.notification_center.notifications.models import (
    NotificationSource,
    NotificationType,
)


def systemmeldungen(laufzeit: NotificationCenterRuntime) -> list:
    return [
        ereignis
        for ereignis in laufzeit.notification_engine.active_events()
        if ereignis.source is NotificationSource.HA_SYSTEM
    ]


async def _einrichten(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    *,
    uebernehmen: bool = True,
    typ: NotificationType = NotificationType.WARNING,
) -> NotificationCenterRuntime:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    laufzeit = config_entry.runtime_data
    laufzeit.config.settings.ha_system_notifications = uebernehmen
    laufzeit.config.settings.ha_system_type = str(typ)
    await laufzeit.async_apply_system_notifications()
    await hass.async_block_till_done()
    return laufzeit


@pytest.fixture
async def runtime(hass: HomeAssistant, config_entry: MockConfigEntry) -> NotificationCenterRuntime:
    return await _einrichten(hass, config_entry)


# -- Uebernahme -------------------------------------------------------------


async def test_neue_benachrichtigung_erscheint(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    pn.async_create(hass, "Anmeldeversuch fehlgeschlagen", "Sicherheit", "login_attempt")
    await hass.async_block_till_done()

    meldungen = systemmeldungen(runtime)
    assert len(meldungen) == 1
    assert meldungen[0].message == "Anmeldeversuch fehlgeschlagen"
    assert meldungen[0].title == "Sicherheit"
    assert meldungen[0].notification_id == "login_attempt"
    assert meldungen[0].type is NotificationType.WARNING


async def test_verworfene_benachrichtigung_endet(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    pn.async_create(hass, "Ungueltige Konfiguration", notification_id="invalid_config")
    await hass.async_block_till_done()
    assert len(systemmeldungen(runtime)) == 1

    pn.async_dismiss(hass, "invalid_config")
    await hass.async_block_till_done()

    assert systemmeldungen(runtime) == []


async def test_dieselbe_kennung_erzeugt_keinen_zweiten_eintrag(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Home Assistant aktualisiert eine Meldung unter derselben Kennung."""
    pn.async_create(hass, "Erster Stand", notification_id="backup")
    await hass.async_block_till_done()
    erster = systemmeldungen(runtime)[0]

    pn.async_create(hass, "Zweiter Stand", notification_id="backup")
    await hass.async_block_till_done()

    meldungen = systemmeldungen(runtime)
    assert len(meldungen) == 1
    assert meldungen[0].event_id == erster.event_id
    assert meldungen[0].message == "Zweiter Stand"


async def test_der_typ_folgt_der_einstellung(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    laufzeit = await _einrichten(hass, config_entry, typ=NotificationType.INFO)

    pn.async_create(hass, "Sicherung abgeschlossen", notification_id="backup")
    await hass.async_block_till_done()

    assert systemmeldungen(laufzeit)[0].type is NotificationType.INFO


async def test_bestand_wird_beim_einschalten_uebernommen(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Was schon in der Seitenleiste steht, darf nicht fehlen.

    Der Rueckruf von Home Assistant liefert nur kuenftige Aenderungen. Ohne
    das Nachholen des Bestands waere nach jedem Neustart unsichtbar, was
    Home Assistant beim Hochfahren gemeldet hat.
    """
    pn.async_create(hass, "Schon vorher da", notification_id="vorher")
    await hass.async_block_till_done()

    laufzeit = await _einrichten(hass, config_entry)

    meldungen = systemmeldungen(laufzeit)
    assert [meldung.message for meldung in meldungen] == ["Schon vorher da"]


# -- Abgeschaltet -----------------------------------------------------------


async def test_abgeschaltet_erscheint_nichts(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Die Vorgabe ist aus; ohne Zustimmung erscheint keine Systemnachricht."""
    laufzeit = await _einrichten(hass, config_entry, uebernehmen=False)

    pn.async_create(hass, "Ungefragt", notification_id="ungefragt")
    await hass.async_block_till_done()

    assert systemmeldungen(laufzeit) == []
    assert laufzeit.system_notifications.running is False


async def test_abschalten_beendet_die_gezeigten_meldungen(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    pn.async_create(hass, "Laeuft noch", notification_id="laeuft")
    await hass.async_block_till_done()
    assert len(systemmeldungen(runtime)) == 1

    runtime.config.settings.ha_system_notifications = False
    await runtime.async_apply_system_notifications()
    await hass.async_block_till_done()

    assert systemmeldungen(runtime) == []
    # In Home Assistant bleibt die Benachrichtigung bestehen: das
    # Notification Center verwirft nichts in dessen Namen.
    assert pn._async_get_or_create_notifications(hass).get("laeuft") is not None


async def test_pause_unterdrueckt_systemnachrichten(
    hass: HomeAssistant, runtime: NotificationCenterRuntime
) -> None:
    """Spezifikation 42: waehrend der Pause entsteht nichts."""
    await runtime.async_set_paused(True)

    pn.async_create(hass, "Waehrend der Pause", notification_id="pause")
    await hass.async_block_till_done()

    assert systemmeldungen(runtime) == []


# -- Aufbereitung des Texts -------------------------------------------------


def test_mehrzeiliger_text_wird_zu_einer_zeile() -> None:
    assert kurzfassung("Zeile eins\n\nZeile   zwei") == "Zeile eins Zeile zwei"


def test_langer_text_wird_gekuerzt() -> None:
    gekuerzt = kurzfassung("x" * (MAX_MESSAGE_LENGTH + 50))
    assert len(gekuerzt) == MAX_MESSAGE_LENGTH
    assert gekuerzt.endswith("…")


def test_text_ohne_inhalt_bleibt_leer() -> None:
    assert kurzfassung(None) == ""
    assert kurzfassung("   \n  ") == ""
    assert titel("  ") is None
