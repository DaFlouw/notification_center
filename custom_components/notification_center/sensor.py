"""Zaehler-Entities des Notification Centers (Spezifikation 44).

Die Werte kommen aus dem laufenden Zustand der Notification-Engine, nicht aus
einer Abfrage des Logs. Aktualisiert wird ereignisgesteuert ueber ein Signal;
die Entities werden nicht abgefragt (Spezifikation 45).

Die Entity-IDs sind bewusst englisch und werden festgelegt, damit sie von den
deutschen Anzeigenamen unabhaengig bleiben.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NotificationCenterEntry
from .const import DOMAIN, PANEL_TITLE
from .coordinator import NotificationCenterRuntime
from .notifications.engine import SIGNAL_COUNTS_UPDATED
from .notifications.lifecycle import Counts


@dataclass(frozen=True, kw_only=True)
class CountSensorDescription(SensorEntityDescription):
    """Beschreibt einen Zaehler und woher sein Wert kommt."""

    value_fn: Callable[[Counts], int]


SENSORS: tuple[CountSensorDescription, ...] = (
    CountSensorDescription(
        key="info_count",
        translation_key="info_count",
        value_fn=lambda counts: counts.info,
    ),
    CountSensorDescription(
        key="warning_count",
        translation_key="warning_count",
        value_fn=lambda counts: counts.warning,
    ),
    CountSensorDescription(
        key="alarm_count",
        translation_key="alarm_count",
        value_fn=lambda counts: counts.alarm,
    ),
    CountSensorDescription(
        key="active_count",
        translation_key="active_count",
        value_fn=lambda counts: counts.active,
    ),
    CountSensorDescription(
        key="events_today",
        translation_key="events_today",
        value_fn=lambda counts: counts.events_today,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NotificationCenterEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        NotificationCountSensor(hass, entry, entry.runtime_data, description)
        for description in SENSORS
    )


class NotificationCountSensor(SensorEntity):
    """Ein Zaehler aus dem laufenden Zustand der Notification-Engine."""

    entity_description: CountSensorDescription

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: NotificationCenterEntry,
        runtime: NotificationCenterRuntime,
        description: CountSensorDescription,
    ) -> None:
        self.entity_description = description
        self._runtime = runtime

        # Festgelegte, englische Entity-ID. Ohne das wuerde sie aus dem
        # deutschen Anzeigenamen abgeleitet.
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, f"{DOMAIN}_{description.key}", hass=hass
        )
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=PANEL_TITLE,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int:
        return self.entity_description.value_fn(self._runtime.notification_engine.counts)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_COUNTS_UPDATED, self._handle_counts_updated)
        )

    @callback
    def _handle_counts_updated(self) -> None:
        self.async_write_ha_state()
