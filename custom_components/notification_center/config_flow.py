"""Config Flow und Options Flow des Notification Centers.

Der Config Flow ist bewusst leer: es gibt genau eine globale Instanz
(Spezifikation 4), und die eigentliche Einrichtung passiert im Panel
(Spezifikation 67).

Der Options Flow bietet die globalen Einstellungen auch ausserhalb des Panels
an. Die Werte liegen weiterhin ausschliesslich im Konfigurations-Store
(Spezifikation 47); dieser Flow liest und schreibt sie dort, statt eine zweite
Ablage aufzumachen.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONFIG_ENTRY_MINOR_VERSION,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    MAX_EVENTS_OPTIONS,
    RETENTION_DAYS_OPTIONS,
    RETENTION_DAYS_UNLIMITED,
    SINGLE_INSTANCE_TITLE,
)

CONF_RETENTION_DAYS = "retention_days"
CONF_MAX_EVENTS = "max_events"
CONF_ANALYSIS_DAYS = "analysis_days"
CONF_PAUSED = "paused"


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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NotificationCenterOptionsFlow:
        return NotificationCenterOptionsFlow()


class NotificationCenterOptionsFlow(OptionsFlow):
    """Globale Einstellungen (Spezifikation 38, 42)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        runtime = self.config_entry.runtime_data
        settings = runtime.config.settings

        if user_input is not None:
            settings.retention_days = int(user_input[CONF_RETENTION_DAYS])
            settings.max_events = int(user_input[CONF_MAX_EVENTS])
            settings.analysis_days = int(user_input[CONF_ANALYSIS_DAYS])
            await runtime.async_set_paused(bool(user_input[CONF_PAUSED]))
            await runtime.config_store.async_save()

            # Die Einstellungen liegen im Store, nicht in den Optionen des
            # Eintrags. Ein leeres Ergebnis vermeidet eine zweite Ablage.
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_RETENTION_DAYS, default=str(settings.retention_days)
                    ): _retention_selector(),
                    vol.Required(
                        CONF_MAX_EVENTS, default=str(settings.max_events)
                    ): _max_events_selector(),
                    vol.Required(
                        CONF_ANALYSIS_DAYS, default=settings.analysis_days
                    ): NumberSelector(
                        NumberSelectorConfig(min=1, max=90, mode=NumberSelectorMode.BOX)
                    ),
                    vol.Required(CONF_PAUSED, default=settings.paused): BooleanSelector(),
                }
            ),
        )


def _retention_selector() -> SelectSelector:
    """Aufbewahrungsdauer als Auswahl (Spezifikation 38)."""
    optionen = [
        SelectOptionDict(
            value=str(tage),
            label="unbegrenzt" if tage == RETENTION_DAYS_UNLIMITED else f"{tage} Tage",
        )
        for tage in RETENTION_DAYS_OPTIONS
    ]
    return SelectSelector(SelectSelectorConfig(options=optionen, mode=SelectSelectorMode.DROPDOWN))


def _max_events_selector() -> SelectSelector:
    """Maximale Ereignisanzahl als Auswahl (Spezifikation 38)."""
    optionen = [
        SelectOptionDict(value=str(anzahl), label=f"{anzahl:n}".replace(",", "."))
        for anzahl in MAX_EVENTS_OPTIONS
    ]
    return SelectSelector(SelectSelectorConfig(options=optionen, mode=SelectSelectorMode.DROPDOWN))
