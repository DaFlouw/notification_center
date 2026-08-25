"""Oeffentliche Services fuer Home-Assistant-Automationen.

Drei Aufrufe (Spezifikation 23 bis 29):

``notification_center.create``
    Erzeugt eine Notification oder ueberschreibt eine bestehende mit
    derselben Kombination aus Owner und ID.
``notification_center.update``
    Aendert eine laufende Notification.
``notification_center.dismiss``
    Beendet eine laufende Notification.

Owner und ID bilden zusammen den eindeutigen Schluessel. Zwei Automationen
duerfen dieselbe ID verwenden, ohne sich zu beeinflussen (Spezifikation 25).
"""

from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from ..const import (
    DOMAIN,
    SERVICE_CREATE,
    SERVICE_DISMISS,
    SERVICE_UPDATE,
)
from ..coordinator import NotificationCenterRuntime
from ..notifications.models import NotificationType

_LOGGER = logging.getLogger(__name__)

ATTR_ID = "notification_id"
ATTR_OWNER = "owner"
ATTR_TYPE = "type"
ATTR_MESSAGE = "message"
ATTR_TITLE = "title"
ATTR_ENTITY_ID = "entity_id"
ATTR_DURATION = "duration"

#: Wird verwendet, wenn sich der Aufrufer nicht ermitteln laesst.
DEFAULT_OWNER = "manual"

#: Ohne eigene ID kann eine Automation nur eine Notification fuehren; das ist
#: fuer einfache Faelle gewollt und macht den Aufruf kurz.
DEFAULT_NOTIFICATION_ID = "default"

_TYPE = vol.All(vol.Lower, vol.Coerce(NotificationType))

CREATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_ID, default=DEFAULT_NOTIFICATION_ID): cv.string,
        vol.Optional(ATTR_OWNER): cv.string,
        vol.Optional(ATTR_TYPE, default=NotificationType.INFO.value): _TYPE,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_DURATION): cv.positive_time_period,
    }
)

UPDATE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ID, default=DEFAULT_NOTIFICATION_ID): cv.string,
        vol.Optional(ATTR_OWNER): cv.string,
        vol.Optional(ATTR_TYPE): _TYPE,
        vol.Optional(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    }
)

DISMISS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ID, default=DEFAULT_NOTIFICATION_ID): cv.string,
        vol.Optional(ATTR_OWNER): cv.string,
    }
)


@callback
def resolve_owner(hass: HomeAssistant, call: ServiceCall) -> str:
    """Ermittelt den Owner eines Aufrufs.

    Ein ausdrueckliches ``owner``-Feld gilt immer. Fehlt es, wird die
    aufrufende Automation ueber den Kontext gesucht: Home Assistant
    aktualisiert beim Ausloesen den Zustand der Automation mit demselben
    Kontext, dessen ID der Aufruf als ``parent_id`` traegt.

    Das ist eine Naeherung und bewusst keine Pflicht: wer sich darauf nicht
    verlassen will, gibt ``owner`` an. Ohne Treffer gilt ``manual``.
    """
    ausdruecklich = call.data.get(ATTR_OWNER)
    if ausdruecklich:
        return str(ausdruecklich)

    parent_id = call.context.parent_id
    if parent_id is None:
        return DEFAULT_OWNER

    for state in hass.states.async_all("automation"):
        if state.context.id == parent_id:
            return state.entity_id

    return DEFAULT_OWNER


@callback
def async_register_services(hass: HomeAssistant, runtime: NotificationCenterRuntime) -> None:
    """Meldet die drei Services an."""

    async def _create(call: ServiceCall) -> None:
        owner = resolve_owner(hass, call)
        dauer: timedelta | None = call.data.get(ATTR_DURATION)
        await runtime.notification_engine.async_create_automation(
            owner=owner,
            notification_id=call.data[ATTR_ID],
            type=call.data[ATTR_TYPE],
            message=call.data[ATTR_MESSAGE],
            title=call.data.get(ATTR_TITLE),
            entity_id=call.data.get(ATTR_ENTITY_ID),
            duration=dauer,
        )

    async def _update(call: ServiceCall) -> None:
        owner = resolve_owner(hass, call)
        await runtime.notification_engine.async_update_automation(
            owner=owner,
            notification_id=call.data[ATTR_ID],
            type=call.data.get(ATTR_TYPE),
            message=call.data.get(ATTR_MESSAGE),
            title=call.data.get(ATTR_TITLE),
            entity_id=call.data.get(ATTR_ENTITY_ID),
        )

    async def _dismiss(call: ServiceCall) -> None:
        owner = resolve_owner(hass, call)
        await runtime.notification_engine.async_dismiss_automation(
            owner=owner,
            notification_id=call.data[ATTR_ID],
        )

    hass.services.async_register(DOMAIN, SERVICE_CREATE, _create, schema=CREATE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE, _update, schema=UPDATE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DISMISS, _dismiss, schema=DISMISS_SCHEMA)
    _LOGGER.debug("Automations-Services angemeldet")


@callback
def async_unregister_services(hass: HomeAssistant) -> None:
    for service in (SERVICE_CREATE, SERVICE_UPDATE, SERVICE_DISMISS):
        hass.services.async_remove(DOMAIN, service)
