"""WebSocket-API des Notification Centers.

Die gesamte Geschaeftslogik liegt im Backend; das Frontend ruft ausschliesslich
diese Kommandos auf und stellt deren Antworten dar (Spezifikation 50).

Zwei Eigenschaften sind hier wichtig:

* **Serverseitige Historie.** Filtern, Suchen und Blaettern passieren in der
  Datenbank. Das Frontend erhaelt standardmaessig 50 Eintraege, nie das ganze
  Log (Spezifikation 49, 61).
* **Kein Polling.** Wer ``subscribe_updates`` abonniert, bekommt Aenderungen
  zugestellt; das Panel fragt nicht periodisch nach (Spezifikation 45).

Jede Antwort traegt ``api_version``. Ein veraltetes Frontend kann daran
erkennen, dass es neu geladen werden muss, statt an unerwarteten Feldern zu
scheitern.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

from ..const import (
    API_VERSION,
    DEFAULT_PAGE_SIZE,
    DOMAIN,
    MAX_EVENTS_OPTIONS,
    MAX_PAGE_SIZE,
    RETENTION_DAYS_OPTIONS,
    WS_PREFIX,
)
from ..coordinator import NotificationCenterRuntime
from ..notifications.engine import SIGNAL_COUNTS_UPDATED
from ..notifications.models import NotificationSource, NotificationType
from ..rules.models import Rule, RuleGroup, new_id
from ..storage.config_models import ConfigError, WatchedEntity
from ..storage.event_store import EventQuery

_LOGGER = logging.getLogger(__name__)


def _runtime(hass: HomeAssistant) -> NotificationCenterRuntime | None:
    eintraege = hass.config_entries.async_entries(DOMAIN)
    if not eintraege:
        return None
    return getattr(eintraege[0], "runtime_data", None)


def _requires_runtime(
    func: Callable[
        [HomeAssistant, websocket_api.ActiveConnection, dict[str, Any], NotificationCenterRuntime],
        Coroutine[Any, Any, None],
    ],
):
    """Sorgt dafuer, dass jedes Kommando eine geladene Instanz vorfindet."""

    async def wrapper(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        runtime = _runtime(hass)
        if runtime is None:
            connection.send_error(
                msg["id"], "not_loaded", "Das Notification Center ist nicht geladen."
            )
            return
        try:
            await func(hass, connection, msg, runtime)
        except ConfigError as err:
            connection.send_error(msg["id"], "invalid_config", str(err))
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_input", str(err))

    wrapper.__name__ = func.__name__
    return wrapper


def _envelope(payload: dict[str, Any]) -> dict[str, Any]:
    return {"api_version": API_VERSION, **payload}


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): f"{WS_PREFIX}/get_active"})
@websocket_api.async_response
@_requires_runtime
async def ws_get_active(hass, connection, msg, runtime) -> None:
    """Aktive Notifications und Zaehler fuer das Dashboard."""
    connection.send_result(msg["id"], _envelope(_dashboard_payload(runtime)))


@websocket_api.websocket_command({vol.Required("type"): f"{WS_PREFIX}/get_counts"})
@websocket_api.async_response
@_requires_runtime
async def ws_get_counts(hass, connection, msg, runtime) -> None:
    connection.send_result(
        msg["id"], _envelope({"counts": runtime.notification_engine.counts.to_dict()})
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/get_history",
        vol.Optional("types"): [vol.In([t.value for t in NotificationType])],
        vol.Optional("sources"): [vol.In([s.value for s in NotificationSource])],
        vol.Optional("entity_ids"): [str],
        vol.Optional("device_ids"): [str],
        vol.Optional("area_ids"): [str],
        vol.Optional("search"): vol.Any(str, None),
        vol.Optional("start"): vol.Any(str, None),
        vol.Optional("end"): vol.Any(str, None),
        vol.Optional("active_only"): bool,
        vol.Optional("limit"): vol.All(int, vol.Range(min=1, max=MAX_PAGE_SIZE)),
        vol.Optional("offset"): vol.All(int, vol.Range(min=0)),
    }
)
@websocket_api.async_response
@_requires_runtime
async def ws_get_history(hass, connection, msg, runtime) -> None:
    """Gefilterte, seitenweise Historie (Spezifikation 59 bis 61)."""
    query = EventQuery(
        types=[NotificationType(wert) for wert in msg.get("types", [])] or None,
        sources=[NotificationSource(wert) for wert in msg.get("sources", [])] or None,
        entity_ids=msg.get("entity_ids") or None,
        device_ids=msg.get("device_ids") or None,
        area_ids=msg.get("area_ids") or None,
        search=msg.get("search") or None,
        start=_zeitpunkt(msg.get("start")),
        end=_zeitpunkt(msg.get("end")),
        active_only=msg.get("active_only", False),
        limit=msg.get("limit", DEFAULT_PAGE_SIZE),
        offset=msg.get("offset", 0),
    )

    seite = await runtime.event_store.async_query(query)
    jetzt = dt_util.utcnow()

    connection.send_result(
        msg["id"],
        _envelope(
            {
                "events": [ereignis.to_dict(jetzt) for ereignis in seite.events],
                "total": seite.total,
                "offset": seite.offset,
                "has_more": seite.has_more,
            }
        ),
    )


@websocket_api.websocket_command({vol.Required("type"): f"{WS_PREFIX}/get_config"})
@websocket_api.async_response
@_requires_runtime
async def ws_get_config(hass, connection, msg, runtime) -> None:
    """Ueberwachte Entities, Regeln, Gruppen und Einstellungen."""
    config = runtime.config
    connection.send_result(
        msg["id"],
        _envelope(
            {
                "entities": [eintrag.to_dict() for eintrag in config.entities.values()],
                "rules": [regel.to_dict() for regel in config.rules.values()],
                "groups": [gruppe.to_dict() for gruppe in config.groups.values()],
                "settings": config.settings.to_dict(),
                "options": {
                    "retention_days": list(RETENTION_DAYS_OPTIONS),
                    "max_events": list(MAX_EVENTS_OPTIONS),
                },
            }
        ),
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/discover",
        vol.Optional("domain"): vol.Any(str, None),
        vol.Optional("search"): vol.Any(str, None),
        vol.Optional("limit"): vol.All(int, vol.Range(min=1, max=500)),
    }
)
@websocket_api.async_response
@_requires_runtime
async def ws_discover(hass, connection, msg, runtime) -> None:
    """Entitysuche. Fasst die Datenbank bewusst nicht an."""
    ergebnis = runtime.discovery.discover_entities(
        domain=msg.get("domain"),
        search=msg.get("search"),
        limit=msg.get("limit", 100),
    )
    connection.send_result(msg["id"], _envelope({"entities": ergebnis}))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/get_suggestions",
        vol.Required("entity_id"): str,
        vol.Optional("analysis_days"): vol.All(int, vol.Range(min=1, max=90)),
    }
)
@websocket_api.async_response
@_requires_runtime
async def ws_get_suggestions(hass, connection, msg, runtime) -> None:
    """Vorschlaege samt Historienanalyse. Laeuft nur auf Anforderung."""
    vorschlaege = await runtime.discovery.async_get_entity_suggestions(
        msg["entity_id"], analysis_days=msg.get("analysis_days")
    )
    connection.send_result(
        msg["id"],
        _envelope(
            {
                "entity_id": msg["entity_id"],
                "suggestions": [vorschlag.to_dict() for vorschlag in vorschlaege],
                "states": runtime.discovery.available_states(msg["entity_id"]),
                "attributes": runtime.discovery.usable_attributes(msg["entity_id"]),
            }
        ),
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{WS_PREFIX}/get_device", vol.Required("device_id"): str}
)
@websocket_api.async_response
@_requires_runtime
async def ws_get_device(hass, connection, msg, runtime) -> None:
    """Entities eines Geraets als Komfort-Gruppierung (Spezifikation 65)."""
    connection.send_result(
        msg["id"], _envelope(runtime.discovery.get_device_suggestions(msg["device_id"]))
    )


# ---------------------------------------------------------------------------
# Konfiguration aendern
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {vol.Required("type"): f"{WS_PREFIX}/add_entities", vol.Required("entity_ids"): [str]}
)
@websocket_api.async_response
@_requires_runtime
async def ws_add_entities(hass, connection, msg, runtime) -> None:
    """Uebernimmt Entities in die Ueberwachung (Spezifikation 7)."""
    for entity_id in msg["entity_ids"]:
        metadata = runtime.discovery.metadata_for(entity_id)
        runtime.config.add_entity(
            WatchedEntity(
                entity_id=entity_id,
                device_id=metadata.device_id if metadata else None,
                area_id=metadata.area_id if metadata else None,
            )
        )

    await runtime.async_config_changed()
    connection.send_result(msg["id"], _envelope({"added": msg["entity_ids"]}))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{WS_PREFIX}/remove_entity", vol.Required("entity_id"): str}
)
@websocket_api.async_response
@_requires_runtime
async def ws_remove_entity(hass, connection, msg, runtime) -> None:
    """Entfernt eine Entity; ihre Historie bleibt (Spezifikation 78)."""
    await runtime.async_remove_entity(msg["entity_id"])
    connection.send_result(msg["id"], _envelope({"removed": msg["entity_id"]}))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/replace_entity",
        vol.Required("old_entity_id"): str,
        vol.Required("new_entity_id"): str,
    }
)
@websocket_api.async_response
@_requires_runtime
async def ws_replace_entity(hass, connection, msg, runtime) -> None:
    """Ersetzt eine Entity und nimmt ihre Regeln mit (Spezifikation 66)."""
    await runtime.async_replace_entity(msg["old_entity_id"], msg["new_entity_id"])
    connection.send_result(msg["id"], _envelope({"replaced": msg["old_entity_id"]}))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{WS_PREFIX}/save_rule", vol.Required("rule"): dict}
)
@websocket_api.async_response
@_requires_runtime
async def ws_save_rule(hass, connection, msg, runtime) -> None:
    """Legt eine Regel an oder ersetzt sie.

    Ohne ``rule_id`` entsteht eine neue Regel; mit einer bekannten wird die
    bestehende ersetzt.
    """
    daten = dict(msg["rule"])
    daten.setdefault("rule_id", new_id("rule"))
    regel = Rule.from_dict(daten)
    await runtime.async_save_rule(regel)
    connection.send_result(msg["id"], _envelope({"rule": regel.to_dict()}))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{WS_PREFIX}/delete_rule", vol.Required("rule_id"): str}
)
@websocket_api.async_response
@_requires_runtime
async def ws_delete_rule(hass, connection, msg, runtime) -> None:
    await runtime.async_delete_rule(msg["rule_id"])
    connection.send_result(msg["id"], _envelope({"deleted": msg["rule_id"]}))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{WS_PREFIX}/save_group", vol.Required("group"): dict}
)
@websocket_api.async_response
@_requires_runtime
async def ws_save_group(hass, connection, msg, runtime) -> None:
    """Legt eine Eskalationsgruppe an oder ersetzt sie (Spezifikation 19)."""
    gruppe = RuleGroup.from_dict(msg["group"])
    await runtime.async_save_group(gruppe)
    connection.send_result(msg["id"], _envelope({"group": gruppe.to_dict()}))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/set_settings",
        vol.Optional("retention_days"): vol.In(RETENTION_DAYS_OPTIONS),
        vol.Optional("max_events"): vol.In(MAX_EVENTS_OPTIONS),
        vol.Optional("analysis_days"): vol.All(int, vol.Range(min=1, max=90)),
        vol.Optional("paused"): bool,
        vol.Optional("setup_completed"): bool,
    }
)
@websocket_api.async_response
@_requires_runtime
async def ws_set_settings(hass, connection, msg, runtime) -> None:
    """Aendert die globalen Einstellungen (Spezifikation 38, 42)."""
    settings = runtime.config.settings
    for feld in ("retention_days", "max_events", "analysis_days", "setup_completed"):
        if feld in msg:
            setattr(settings, feld, msg[feld])

    if "paused" in msg:
        await runtime.async_set_paused(msg["paused"])

    await runtime.config_store.async_save()
    connection.send_result(msg["id"], _envelope({"settings": settings.to_dict()}))


# ---------------------------------------------------------------------------
# Historie loeschen
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {vol.Required("type"): f"{WS_PREFIX}/delete_event", vol.Required("event_id"): str}
)
@websocket_api.async_response
@_requires_runtime
async def ws_delete_event(hass, connection, msg, runtime) -> None:
    """Loescht einen abgeschlossenen Eintrag (Spezifikation 39).

    Aktive Ereignisse bleiben: eine laufende Notification wuerde sonst ihren
    Datensatz verlieren.
    """
    geloescht = await runtime.event_store.async_delete(msg["event_id"])
    connection.send_result(msg["id"], _envelope({"deleted": geloescht}))


@websocket_api.websocket_command({vol.Required("type"): f"{WS_PREFIX}/clear_history"})
@websocket_api.async_response
@_requires_runtime
async def ws_clear_history(hass, connection, msg, runtime) -> None:
    """Leert das Log; aktive Ereignisse bleiben erhalten."""
    anzahl = await runtime.event_store.async_delete_all(keep_active=True)
    connection.send_result(msg["id"], _envelope({"deleted": anzahl}))


# ---------------------------------------------------------------------------
# Abonnement
# ---------------------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): f"{WS_PREFIX}/subscribe_updates"})
@callback
def ws_subscribe_updates(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Stellt Aenderungen zu, statt sie abfragen zu lassen.

    Das Dashboard bekommt damit den vollstaendigen Stand aktiver
    Notifications und Zaehler bei jeder Aenderung; es fragt nichts nach.
    """
    runtime = _runtime(hass)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Das Notification Center ist nicht geladen.")
        return

    @callback
    def _senden() -> None:
        aktuell = _runtime(hass)
        if aktuell is None:
            return
        connection.send_message(
            websocket_api.event_message(msg["id"], _envelope(_dashboard_payload(aktuell)))
        )

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_COUNTS_UPDATED, _senden
    )
    connection.send_result(msg["id"], _envelope(_dashboard_payload(runtime)))


# ---------------------------------------------------------------------------
# Gemeinsames
# ---------------------------------------------------------------------------


def _dashboard_payload(runtime: NotificationCenterRuntime) -> dict[str, Any]:
    jetzt = dt_util.utcnow()
    return {
        "counts": runtime.notification_engine.counts.to_dict(),
        "active": [
            ereignis.to_dict(jetzt) for ereignis in runtime.notification_engine.active_events()
        ],
        "paused": runtime.config.settings.paused,
    }


def _zeitpunkt(wert: str | None) -> datetime | None:
    if not wert:
        return None
    zeit = dt_util.parse_datetime(wert)
    if zeit is None:
        raise ValueError(f"Unlesbarer Zeitpunkt: {wert}")
    return dt_util.as_utc(zeit)


COMMANDS = (
    ws_get_active,
    ws_get_counts,
    ws_get_history,
    ws_get_config,
    ws_discover,
    ws_get_suggestions,
    ws_get_device,
    ws_add_entities,
    ws_remove_entity,
    ws_replace_entity,
    ws_save_rule,
    ws_delete_rule,
    ws_save_group,
    ws_set_settings,
    ws_delete_event,
    ws_clear_history,
    ws_subscribe_updates,
)


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Meldet alle Kommandos an."""
    for kommando in COMMANDS:
        websocket_api.async_register_command(hass, kommando)
    _LOGGER.debug("%s WebSocket-Kommandos angemeldet", len(COMMANDS))
