"""Architekturtests.

Die Trennung zwischen Domaenenlogik und Home-Assistant-Anbindung ist eine
tragende Entscheidung: sie haelt Rule Engine, Notification-Lebenszyklus und
Event Store ohne HA-Runtime testbar. Damit sie nicht unbemerkt erodiert, wird
sie hier geprueft statt nur dokumentiert.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_PACKAGE = Path(__file__).resolve().parents[2] / "custom_components" / "notification_center"

#: Module, die keinerlei Home-Assistant-Importe enthalten duerfen.
PURE_MODULES = (
    "const.py",
    "notifications/models.py",
    "rules/models.py",
    "rules/evaluator.py",
    "storage/event_store.py",
    "storage/config_models.py",
)


def _imported_roots(path: Path) -> set[str]:
    """Alle Wurzelpakete, die ein Modul importiert."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])

    return roots


@pytest.mark.parametrize("relative", PURE_MODULES)
def test_domaenenmodul_ist_frei_von_home_assistant(relative: str) -> None:
    path = _PACKAGE / relative
    assert path.exists(), f"Modul fehlt: {relative}"
    assert "homeassistant" not in _imported_roots(path), (
        f"{relative} importiert Home Assistant. Die Domaenenlogik muss ohne "
        "HA-Runtime testbar bleiben; die Anbindung gehoert in engine.py, "
        "coordinator.py oder die api-Module."
    )


def test_alle_gelisteten_module_existieren() -> None:
    """Schuetzt davor, dass die Liste beim Umbenennen still veraltet."""
    fehlend = [name for name in PURE_MODULES if not (_PACKAGE / name).exists()]
    assert not fehlend, f"Nicht mehr vorhandene Module in PURE_MODULES: {fehlend}"
