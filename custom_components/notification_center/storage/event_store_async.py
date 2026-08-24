"""Home-Assistant-Adapter fuer den synchronen Event Store.

SQLite-Zugriffe blockieren und duerfen den Event-Loop nicht anhalten. Dieser
Adapter fuehrt jede Operation im Executor aus. Der Store selbst bleibt dadurch
frei von Home-Assistant-Importen und ohne HA-Runtime testbar.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from homeassistant.core import HomeAssistant

from ..const import DATA_SUBDIR, EVENT_DB_FILENAME
from ..notifications.models import NotificationEvent
from .event_store import EventPage, EventQuery, EventStore


def default_database_path(hass: HomeAssistant) -> Path:
    """Pfad der Ereignisdatenbank im Konfigurationsverzeichnis.

    Liegt unterhalb von ``config``, damit die Datei vom Home-Assistant-Backup
    ohne Zutun mitgesichert wird.
    """
    return Path(hass.config.path(DATA_SUBDIR)) / EVENT_DB_FILENAME


class AsyncEventStore:
    """Asynchrone Huelle um :class:`EventStore`."""

    def __init__(self, hass: HomeAssistant, path: Path | str | None = None) -> None:
        self._hass = hass
        self._store = EventStore(path or default_database_path(hass))

    async def async_open(self) -> None:
        await self._hass.async_add_executor_job(self._store.open)

    async def async_close(self) -> None:
        await self._hass.async_add_executor_job(self._store.close)

    async def async_add(self, event: NotificationEvent) -> None:
        await self._hass.async_add_executor_job(self._store.add, event)

    async def async_update(self, event: NotificationEvent) -> None:
        await self._hass.async_add_executor_job(self._store.update, event)

    async def async_get(self, event_id: str) -> NotificationEvent | None:
        return await self._hass.async_add_executor_job(self._store.get, event_id)

    async def async_active_events(self) -> list[NotificationEvent]:
        return await self._hass.async_add_executor_job(self._store.active_events)

    async def async_find_automation_event(
        self, owner: str, notification_id: str
    ) -> NotificationEvent | None:
        return await self._hass.async_add_executor_job(
            self._store.find_automation_event, owner, notification_id
        )

    async def async_query(self, query: EventQuery) -> EventPage:
        return await self._hass.async_add_executor_job(self._store.query, query)

    async def async_count_since(self, since: datetime) -> int:
        return await self._hass.async_add_executor_job(self._store.count_since, since)

    async def async_delete(self, event_id: str) -> bool:
        return await self._hass.async_add_executor_job(self._store.delete, event_id)

    async def async_delete_all(self, *, keep_active: bool = True) -> int:
        def _delete() -> int:
            return self._store.delete_all(keep_active=keep_active)

        return await self._hass.async_add_executor_job(_delete)

    async def async_cleanup(self, *, retention_days: int, max_events: int) -> int:
        def _cleanup() -> int:
            return self._store.cleanup(retention_days=retention_days, max_events=max_events)

        return await self._hass.async_add_executor_job(_cleanup)
