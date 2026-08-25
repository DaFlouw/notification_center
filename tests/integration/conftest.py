"""Fixtures der Home-Assistant-Integrationstests.

Diese Tests benoetigen ``pytest-homeassistant-custom-component`` und damit eine
Linux-nahe Python-Umgebung. Sie laufen in der CI, nicht auf einem
Windows-Entwicklungsrechner.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.const import DOMAIN
from custom_components.notification_center.storage import event_store_async


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Laesst Home Assistant die Integration aus custom_components laden."""
    yield


@pytest.fixture(autouse=True)
def isolierte_ereignisdatenbank(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path | None:
    """Gibt jedem Test eine eigene Ereignisdatenbank.

    Die Testumgebung teilt sich ein Konfigurationsverzeichnis. Ohne diese
    Umleitung wuerde die SQLite-Datei zwischen den Tests bestehen bleiben und
    Zaehler wie Historien verfaelschen.
    """
    if request.node.get_closest_marker("echter_datenbankpfad"):
        return None

    pfad = tmp_path / "notification_center" / "events.db"
    monkeypatch.setattr(event_store_async, "default_database_path", lambda hass: pfad)
    return pfad


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, title="Notification Center", data={})
