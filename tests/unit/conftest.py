"""Gemeinsame Fixtures der Domaenentests.

Diese Tests laufen bewusst ohne Home-Assistant-Runtime.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from custom_components.notification_center.notifications.models import (
    NotificationEvent,
    NotificationSource,
    NotificationType,
)
from custom_components.notification_center.storage.event_store import EventStore

#: Fester Bezugszeitpunkt, damit Dauerberechnungen reproduzierbar sind.
T0 = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[EventStore]:
    """Ein frisch angelegter Event Store in einem temporaeren Verzeichnis."""
    instance = EventStore(tmp_path / "notification_center" / "events.db")
    instance.open()
    yield instance
    instance.close()


def make_event(
    *,
    message: str = "Fenster geoeffnet",
    type: NotificationType = NotificationType.WARNING,
    source: NotificationSource = NotificationSource.ENTITY_RULE,
    offset_minutes: float = 0,
    **kwargs: object,
) -> NotificationEvent:
    """Baut ein Ereignis relativ zum Bezugszeitpunkt ``T0``."""
    return NotificationEvent(
        message=message,
        type=type,
        source=source,
        start_time=T0 + timedelta(minutes=offset_minutes),
        **kwargs,  # type: ignore[arg-type]
    )
