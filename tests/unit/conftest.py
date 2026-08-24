"""Gemeinsame Fixtures der Domaenentests.

Diese Tests laufen bewusst ohne Home-Assistant-Runtime. Damit das moeglich
bleibt, wird das Paket ``custom_components.notification_center`` hier als
Namensraum registriert, *ohne* sein ``__init__.py`` auszufuehren: dieses
importiert Home Assistant und wuerde die reinen Domaenentests an eine
HA-Installation binden.

Der Nebeneffekt ist erwuenscht: sobald ein Modul unter ``rules``,
``notifications`` oder ``storage`` versehentlich einen Home-Assistant-Import
bekommt, schlagen diese Tests fehl. Die Trennung ist damit nicht nur
Konvention, sondern geprueft.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _register_namespace() -> None:
    """Meldet die Paketstruktur an, ohne das echte ``__init__.py`` zu laden."""
    for name, path in (
        ("custom_components", _ROOT / "custom_components"),
        (
            "custom_components.notification_center",
            _ROOT / "custom_components" / "notification_center",
        ),
    ):
        if name in sys.modules:
            continue
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module


_register_namespace()

from custom_components.notification_center.notifications.models import (  # noqa: E402
    NotificationEvent,
    NotificationSource,
    NotificationType,
)
from custom_components.notification_center.storage.event_store import (  # noqa: E402
    EventStore,
)

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
