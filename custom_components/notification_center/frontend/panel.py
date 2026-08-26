"""Registrierung des Notification-Center-Panels und der Lovelace-Card.

Das Panel ist die primaere Oberflaeche (Spezifikation 69). Es besteht aus
buildfreien ES-Modulen: keine Bundler-Abhaengigkeit, keine Build-Artefakte im
Repository, und die ausgelieferten Dateien sind genau die, die hier liegen.

Alle Benutzer duerfen es sehen; eine eigene Rechteverwaltung gibt es bewusst
nicht (Spezifikation 72).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import (
    DOMAIN,
    FRONTEND_URL_BASE,
    INTEGRATION_VERSION,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
)

_LOGGER = logging.getLogger(__name__)

PANEL_ELEMENT = "notification-center-panel"
CARD_MODULE = "notification-center-card"

#: Merker der bereits registrierten statischen Pfade. Home Assistant lehnt
#: eine zweite Registrierung desselben Pfads ab; ohne diesen Merker wuerde ein
#: Neuladen der Integration den Panel-Start abbrechen.
_STATIC_PATHS = f"{DOMAIN}_static_paths"

#: Die Version steckt im *Pfad*, nicht in einer Abfragezeichenkette.
#:
#: Ein Modul und seine relativen Importe muessen gemeinsam altern. Haengt die
#: Version nur an der Einstiegsdatei, holt der Browser zwar diese neu, laedt
#: aber ``./api.js`` und die Ansichten weiter aus dem Zwischenspeicher: neues
#: Panel, alte Bausteine. Ueber einen versionierten Pfad erben alle relativen
#: Importe die Version automatisch.
VERSIONED_BASE = f"{FRONTEND_URL_BASE}/{INTEGRATION_VERSION}"

PANEL_MODULE_URL = f"{VERSIONED_BASE}/{PANEL_ELEMENT}.js"
CARD_URL = f"{VERSIONED_BASE}/{CARD_MODULE}.js"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Liefert die Frontend-Dateien aus und meldet Panel und Card an."""
    await _async_register_static_path(hass)
    await _async_register_card(hass)

    if PANEL_URL_PATH in hass.data.get("frontend_panels", {}):
        return

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        module_url=PANEL_MODULE_URL,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        embed_iframe=False,
    )
    _LOGGER.debug("Panel unter /%s angemeldet", PANEL_URL_PATH)


async def _async_register_static_path(hass: HomeAssistant) -> None:
    """Liefert die Frontend-Dateien unter einem versionierten Pfad aus."""
    registriert: set[str] = hass.data.setdefault(_STATIC_PATHS, set())
    if VERSIONED_BASE in registriert:
        return

    verzeichnis = str(Path(__file__).parent)
    pfade = [
        # Unter der Version: jede Datei bekommt bei einer neuen Version eine
        # neue URL, auch die relativ importierten Bausteine.
        StaticPathConfig(VERSIONED_BASE, verzeichnis, cache_headers=True),
    ]

    # Der unversionierte Pfad bleibt fuer Kartenkonfigurationen erhalten, die
    # noch auf die alte URL zeigen.
    if FRONTEND_URL_BASE not in registriert:
        pfade.append(StaticPathConfig(FRONTEND_URL_BASE, verzeichnis, cache_headers=False))
        registriert.add(FRONTEND_URL_BASE)

    await hass.http.async_register_static_paths(pfade)
    registriert.add(VERSIONED_BASE)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Macht die kompakte Card in Lovelace verfuegbar (Spezifikation 70).

    Bevorzugt als Lovelace-Ressource: nur so findet die Kartenauswahl sie
    zuverlaessig wieder, auch nach einem Neuladen der Seite. Laeuft Lovelace
    im YAML-Modus, gibt es keine verwaltbare Ressourcenliste; dann wird das
    Modul als zusaetzliches Frontend-Modul geladen.
    """
    if await _async_register_lovelace_resource(hass):
        return

    frontend.add_extra_js_url(hass, CARD_URL)
    _LOGGER.debug("Card als zusaetzliches Frontend-Modul eingebunden")


async def _async_register_lovelace_resource(hass: HomeAssistant) -> bool:
    """Traegt die Card in die Lovelace-Ressourcen ein, falls moeglich."""
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None:
        return False

    # Im YAML-Modus ist die Liste nicht veraenderbar.
    if not hasattr(resources, "async_create_item"):
        return False

    try:
        if hasattr(resources, "async_get_info"):
            await resources.async_get_info()

        for eintrag in resources.async_items():
            if not _ist_unsere_card(str(eintrag.get("url", ""))):
                continue
            if eintrag["url"] != CARD_URL:
                # Version im Pfad nachziehen, damit der Browser die neue Datei
                # holt statt der zwischengespeicherten.
                await resources.async_update_item(eintrag["id"], {"url": CARD_URL})
            return True

        await resources.async_create_item({"res_type": "module", "url": CARD_URL})
    except Exception:
        _LOGGER.exception("Card konnte nicht als Lovelace-Ressource eingetragen werden")
        return False

    _LOGGER.debug("Card als Lovelace-Ressource eingetragen")
    return True


def async_unregister_panel(hass: HomeAssistant) -> None:
    """Entfernt das Panel.

    Der Ressourceneintrag der Card bleibt bestehen: er gehoert zur
    Dashboard-Konfiguration des Benutzers, und ein Neuladen der Integration
    wuerde sonst jede Karte auf seinen Dashboards zerstoeren.
    """
    frontend.async_remove_panel(hass, PANEL_URL_PATH)


def _ist_unsere_card(url: str) -> bool:
    """Erkennt den Ressourceneintrag der Card, egal unter welcher Version."""
    return url.split("?")[0].endswith(f"/{CARD_MODULE}.js") and url.startswith(FRONTEND_URL_BASE)


def card_resource(hass: HomeAssistant) -> dict[str, Any] | None:
    """Der Ressourceneintrag der Card, sofern vorhanden. Nur fuer Tests."""
    resources = getattr(hass.data.get("lovelace"), "resources", None)
    if resources is None or not hasattr(resources, "async_items"):
        return None
    for eintrag in resources.async_items():
        if _ist_unsere_card(str(eintrag.get("url", ""))):
            return dict(eintrag)
    return None
