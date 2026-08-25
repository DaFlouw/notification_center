"""Tests der Entscheidungsschicht zwischen Auswertung und Notifications."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.notification_center.notifications.models import (
    CloseReason,
    NotificationType,
)
from custom_components.notification_center.rules.evaluator import (
    GroupState,
    RuleState,
    evaluate_group,
    evaluate_rule,
)
from custom_components.notification_center.rules.intents import (
    IntentKind,
    intents_for_group,
    intents_for_rule,
)
from custom_components.notification_center.rules.models import RuleGroup

from .conftest import T0
from .test_evaluator import fenster, numeric, snap

# -- Einzelne Regeln --------------------------------------------------------


def test_erfuellte_regel_startet_eine_notification() -> None:
    rule = fenster(message_template="{name} geoeffnet")
    state = RuleState(rule_id=rule.rule_id)
    ergebnis = evaluate_rule(rule, snap("on"), state, T0)

    absichten = intents_for_rule(rule, snap("on"), ergebnis)

    assert len(absichten) == 1
    assert absichten[0].kind is IntentKind.START
    assert absichten[0].since == T0
    assert absichten[0].message() == "Temperatur Wohnzimmer geoeffnet"


def test_beendete_regel_stoppt_mit_begruendung() -> None:
    rule = fenster()
    state = RuleState(rule_id=rule.rule_id)
    evaluate_rule(rule, snap("on"), state, T0)
    ergebnis = evaluate_rule(rule, snap("off", minutes=5), state, T0 + timedelta(minutes=5))

    absichten = intents_for_rule(rule, snap("off", minutes=5), ergebnis)

    assert len(absichten) == 1
    assert absichten[0].kind is IntentKind.STOP
    assert absichten[0].reason is CloseReason.CONDITION_CLEARED


def test_unveraenderte_regel_erzeugt_keine_absicht() -> None:
    """Eine laufende Notification wird nicht bei jedem Messwert neu geschrieben."""
    rule = fenster()
    state = RuleState(rule_id=rule.rule_id)
    evaluate_rule(rule, snap("on"), state, T0)
    ergebnis = evaluate_rule(rule, snap("on", minutes=1), state, T0 + timedelta(minutes=1))

    assert intents_for_rule(rule, snap("on", minutes=1), ergebnis) == []


def test_wartende_zeitbedingung_erzeugt_keine_absicht() -> None:
    rule = fenster(duration_seconds=900)
    state = RuleState(rule_id=rule.rule_id)
    ergebnis = evaluate_rule(rule, snap("on"), state, T0)

    assert intents_for_rule(rule, snap("on"), ergebnis) == []


def test_stopgrund_ist_ueberschreibbar() -> None:
    """Fuer Regeldeaktivierung und Entity-Entfernung (Spezifikation 77, 78)."""
    rule = fenster()
    state = RuleState(rule_id=rule.rule_id)
    evaluate_rule(rule, snap("on"), state, T0)
    ergebnis = evaluate_rule(rule, snap("off", minutes=1), state, T0 + timedelta(minutes=1))

    absichten = intents_for_rule(
        rule, snap("off", minutes=1), ergebnis, stop_reason=CloseReason.RULE_DISABLED
    )
    assert absichten[0].reason is CloseReason.RULE_DISABLED


# -- Meldungstexte ----------------------------------------------------------


def test_platzhalter_werden_mit_dem_ausgewerteten_wert_gefuellt() -> None:
    rule = numeric(message_template="{name}: {value} {unit}")
    state = RuleState(rule_id=rule.rule_id)
    ergebnis = evaluate_rule(rule, snap("29.4"), state, T0)

    absicht = intents_for_rule(rule, snap("29.4"), ergebnis)[0]
    assert absicht.message() == "Temperatur Wohnzimmer: 29.4 °C"


def test_regel_ohne_vorlage_faellt_auf_den_vorschlagstext_zurueck() -> None:
    """Eine Notification darf nie ohne Text entstehen."""
    rule = numeric(message_template="")
    state = RuleState(rule_id=rule.rule_id)
    ergebnis = evaluate_rule(rule, snap("29.4"), state, T0)

    absicht = intents_for_rule(rule, snap("29.4"), ergebnis)[0]
    assert absicht.message() == "Temperatur Wohnzimmer ueber 28"


# -- Eskalation -------------------------------------------------------------


@pytest.fixture
def gruppe() -> RuleGroup:
    stufen = tuple(
        numeric(
            rule_id=f"rule_{level}",
            threshold=schwelle,
            type=typ,
            group_id="group_1",
            level=level,
            message_template="{name} {value} {unit}",
        )
        for level, schwelle, typ in (
            (1, 25.0, NotificationType.INFO),
            (2, 28.0, NotificationType.WARNING),
            (3, 32.0, NotificationType.ALARM),
        )
    )
    return RuleGroup(
        group_id="group_1",
        entity_id="sensor.temperatur_wz",
        name="Temperatur Wohnzimmer",
        rules=stufen,
    )


def test_erste_stufe_startet_nur(gruppe: RuleGroup) -> None:
    state = GroupState(group_id="group_1")
    ergebnis = evaluate_group(gruppe, snap("26"), state, T0)

    absichten = intents_for_group(gruppe, snap("26"), ergebnis)

    assert [a.kind for a in absichten] == [IntentKind.START]
    assert absichten[0].level == 1
    assert absichten[0].rule.type is NotificationType.INFO


def test_eskalation_beendet_die_alte_und_startet_die_neue_stufe(gruppe: RuleGroup) -> None:
    """Spezifikation 20 und 35: jede Stufe ist ein eigenes Ereignis."""
    state = GroupState(group_id="group_1")
    evaluate_group(gruppe, snap("26"), state, T0)
    ergebnis = evaluate_group(gruppe, snap("29", minutes=1), state, T0 + timedelta(minutes=1))

    absichten = intents_for_group(gruppe, snap("29", minutes=1), ergebnis)

    assert [a.kind for a in absichten] == [IntentKind.STOP, IntentKind.START]
    assert absichten[0].level == 1
    assert absichten[0].reason is CloseReason.ESCALATED
    assert absichten[1].level == 2
    assert absichten[1].rule.type is NotificationType.WARNING


def test_deeskalation_wird_als_solche_begruendet(gruppe: RuleGroup) -> None:
    state = GroupState(group_id="group_1")
    evaluate_group(gruppe, snap("33"), state, T0)
    ergebnis = evaluate_group(gruppe, snap("29", minutes=1), state, T0 + timedelta(minutes=1))

    absichten = intents_for_group(gruppe, snap("29", minutes=1), ergebnis)

    assert absichten[0].reason is CloseReason.DEESCALATED
    assert absichten[0].level == 3
    assert absichten[1].level == 2


def test_ende_der_gruppe_stoppt_ohne_neustart(gruppe: RuleGroup) -> None:
    state = GroupState(group_id="group_1")
    evaluate_group(gruppe, snap("29"), state, T0)
    ergebnis = evaluate_group(gruppe, snap("20", minutes=1), state, T0 + timedelta(minutes=1))

    absichten = intents_for_group(gruppe, snap("20", minutes=1), ergebnis)

    assert [a.kind for a in absichten] == [IntentKind.STOP]
    assert absichten[0].reason is CloseReason.CONDITION_CLEARED


def test_gleichbleibende_stufe_erzeugt_keine_absicht(gruppe: RuleGroup) -> None:
    state = GroupState(group_id="group_1")
    evaluate_group(gruppe, snap("29"), state, T0)
    ergebnis = evaluate_group(gruppe, snap("29.5", minutes=1), state, T0 + timedelta(minutes=1))

    assert intents_for_group(gruppe, snap("29.5", minutes=1), ergebnis) == []


def test_vollstaendiger_eskalationsverlauf(gruppe: RuleGroup) -> None:
    """Testfall C als Folge von Absichten."""
    state = GroupState(group_id="group_1")
    verlauf: list[tuple[str, int | None]] = []

    for minute, wert in enumerate(["26", "29", "33", "29", "24"]):
        momentaufnahme = snap(wert, minutes=minute)
        ergebnis = evaluate_group(gruppe, momentaufnahme, state, T0 + timedelta(minutes=minute))
        for absicht in intents_for_group(gruppe, momentaufnahme, ergebnis):
            verlauf.append((str(absicht.kind), absicht.level))

    assert verlauf == [
        ("start", 1),
        ("stop", 1),
        ("start", 2),
        ("stop", 2),
        ("start", 3),
        ("stop", 3),
        ("start", 2),
        ("stop", 2),
    ]
