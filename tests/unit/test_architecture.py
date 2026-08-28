"""Architekturtests.

Die Trennung zwischen Domaenenlogik und Home-Assistant-Anbindung ist eine
tragende Entscheidung: sie haelt Rule Engine, Notification-Lebenszyklus und
Event Store ohne HA-Runtime testbar. Damit sie nicht unbemerkt erodiert, wird
sie hier geprueft statt nur dokumentiert.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_PACKAGE = Path(__file__).resolve().parents[2] / "custom_components" / "notification_center"

#: Module, die keinerlei Home-Assistant-Importe enthalten duerfen.
PURE_MODULES = (
    "const.py",
    "notifications/models.py",
    "notifications/lifecycle.py",
    "rules/models.py",
    "rules/evaluator.py",
    "rules/intents.py",
    "storage/event_store.py",
    "storage/config_models.py",
    "discovery/analyzer.py",
    "discovery/states.py",
    "discovery/suggestions.py",
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


def _supported_domains() -> set[str]:
    """SUPPORTED_DOMAINS aus discovery/engine.py, ohne das Modul zu laden.

    Das Modul importiert Home Assistant und liesse sich hier nicht einfuehren.
    Der Wert steht aber als Literal im Quelltext und ist ueber den AST lesbar.
    """
    pfad = _PACKAGE / "discovery" / "engine.py"
    tree = ast.parse(pfad.read_text(encoding="utf-8"), filename=str(pfad))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        namen = [ziel.id for ziel in node.targets if isinstance(ziel, ast.Name)]
        if "SUPPORTED_DOMAINS" in namen:
            return set(ast.literal_eval(node.value))

    raise AssertionError("SUPPORTED_DOMAINS nicht in discovery/engine.py gefunden")


def _domains_der_typauswahl() -> set[str]:
    """Die Domaenen, die das Auswahlfeld der Discovery anbietet."""
    pfad = _PACKAGE / "frontend" / "views" / "discovery.js"
    quelle = pfad.read_text(encoding="utf-8")

    anfang = quelle.index("const TYP_GRUPPEN")
    ende = quelle.index("export function renderDiscovery")
    return set(re.findall(r'wert:\s*"([^"]+)"', quelle[anfang:ende]))


def test_typauswahl_deckt_alle_ueberwachbaren_domaenen_ab() -> None:
    """Backend und Auswahlfeld muessen dieselben Domaenen kennen.

    Die beiden Listen liegen in verschiedenen Sprachen und sind schon
    auseinandergelaufen: die Helferdomaenen fehlten im Auswahlfeld vollstaendig,
    mehrere Geraetetypen ebenfalls. Wer eine Domaene ergaenzt, muss beide
    Stellen anfassen -- dieser Test sagt es ihm.
    """
    backend = _supported_domains()
    auswahl = _domains_der_typauswahl()

    assert auswahl == backend, (
        f"Nur im Backend: {sorted(backend - auswahl)}; "
        f"nur im Auswahlfeld: {sorted(auswahl - backend)}"
    )
