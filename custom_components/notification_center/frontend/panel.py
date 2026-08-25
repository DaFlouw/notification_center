"""Registrierung des Notification-Center-Panels.

Das Panel ist die primaere Oberflaeche (Spezifikation 69). Es besteht aus
buildfreien ES-Modulen: keine Bundler-Abhaengigkeit, keine Build-Artefakte im
Repository, und die ausgelieferten Dateien sind genau die, die hier liegen.

Alle Benutzer duerfen es sehen; eine eigene Rechteverwaltung gibt es bewusst
nicht (Spezifikation 72).
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import (
    FRONTEND_URL_BASE,
    INTEGRATION_VERSION,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
)

_LOGGER = logging.getLogger(__name__)

PANEL_ELEMENT = "notification-center-panel"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Liefert die Frontend-Dateien aus und meldet das Panel an."""
    verzeichnis = Path(__file__).parent

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                FRONTEND_URL_BASE,
                str(verzeichnis),
                # Die Version steckt in der URL; ohne Cache-Header wuerde ein
                # Browser die alte Datei weiterverwenden.
                cache_headers=False,
            )
        ]
    )

    if PANEL_URL_PATH in hass.data.get("frontend_panels", {}):
        return

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        module_url=f"{FRONTEND_URL_BASE}/{PANEL_ELEMENT}.js?v={INTEGRATION_VERSION}",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        embed_iframe=False,
    )
    _LOGGER.debug("Panel unter /%s angemeldet", PANEL_URL_PATH)


def async_unregister_panel(hass: HomeAssistant) -> None:
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
