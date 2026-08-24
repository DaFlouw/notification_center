"""Config Flow des Notification Centers.

Bewusst ohne Eingabefelder: es gibt genau eine globale Instanz
(Spezifikation 4), und die eigentliche Einrichtung passiert im Panel
(Spezifikation 67). Der Flow legt nur den Eintrag an.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONFIG_ENTRY_MINOR_VERSION,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    SINGLE_INSTANCE_TITLE,
)


class NotificationCenterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Legt die einzige Instanz an."""

    VERSION = CONFIG_ENTRY_VERSION
    MINOR_VERSION = CONFIG_ENTRY_MINOR_VERSION

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # Die Einzelinstanz erzwingt Home Assistant bereits ueber
        # "single_config_entry" im Manifest; hier ist keine Pruefung noetig.
        if user_input is None:
            return self.async_show_form(step_id="user")

        return self.async_create_entry(title=SINGLE_INSTANCE_TITLE, data={})
