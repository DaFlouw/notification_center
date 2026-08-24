"""Fixtures der Home-Assistant-Integrationstests.

Diese Tests benoetigen ``pytest-homeassistant-custom-component`` und damit eine
Linux-nahe Python-Umgebung. Sie laufen in der CI, nicht auf einem
Windows-Entwicklungsrechner.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.notification_center.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Laesst Home Assistant die Integration aus custom_components laden."""
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, title="Notification Center", data={})
