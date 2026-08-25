"""Tests der Rule Engine.

Deckt die Spezifikationsabschnitte 14 bis 21 sowie die Testfaelle A bis D ab.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.notification_center.notifications.models import NotificationType
from custom_components.notification_center.rules.evaluator import (
    GroupState,
    Phase,
    RuleState,
    coerce_number,
    evaluate_group,
    evaluate_rule,
    hold_met,
    trigger_met,
)
from custom_components.notification_center.rules.models import (
    ConditionKind,
    EntitySnapshot,
    NumericOperator,
    Rule,
    RuleGroup,
    ValueSource,
    ValueSourceKind,
)

from .conftest import T0


def snap(state: str, *, minutes: float = 0, **kwargs: object) -> EntitySnapshot:
    defaults: dict[str, object] = {
        "entity_id": "sensor.temperatur_wz",
        "state": state,
        "last_changed": T0 + timedelta(minutes=minutes),
        "name": "Temperatur Wohnzimmer",
        "unit": "°C",
    }
    defaults.update(kwargs)
    return EntitySnapshot(**defaults)  # type: ignore[arg-type]


def numeric(**kwargs: object) -> Rule:
    defaults: dict[str, object] = {
        "entity_id": "sensor.temperatur_wz",
        "kind": ConditionKind.NUMERIC,
        "operator": NumericOperator.GT,
        "threshold": 28.0,
    }
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


def fenster(**kwargs: object) -> Rule:
    defaults: dict[str, object] = {
        "entity_id": "binary_sensor.fenster_wz",
        "kind": ConditionKind.STATE_IS,
        "states": ("on",),
    }
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


# -- Wertaufbereitung -------------------------------------------------------


@pytest.mark.parametrize(
    ("roh", "erwartet"),
    [
        ("29.4", 29.4),
        ("29,4", 29.4),
        (29, 29.0),
        (29.4, 29.4),
        (" 30 ", 30.0),
        ("unknown", None),
        ("unavailable", None),
        ("", None),
        ("on", None),
        (None, None),
        (True, None),
    ],
)
def test_wertaufbereitung(roh: object, erwartet: float | None) -> None:
    assert coerce_number(roh) == erwartet


def test_nicht_verfuegbare_entity_erfuellt_keine_bedingung() -> None:
    """Ein alter Wert darf nicht weitergeschleppt werden."""
    rule = numeric()
    assert trigger_met(rule, snap("unavailable"), None) is False
    assert hold_met(rule, snap("unavailable")) is False


# -- Testfall A: Fenster offen ---------------------------------------------


def test_fenster_offen_erzeugt_und_beendet_notification() -> None:
    rule = fenster(type=NotificationType.WARNING)
    state = RuleState(rule_id=rule.rule_id)

    auf = evaluate_rule(rule, snap("on"), state, T0)
    assert auf.became_satisfied is True
    assert auf.phase is Phase.SATISFIED

    haelt = evaluate_rule(rule, snap("on", minutes=5), state, T0 + timedelta(minutes=5))
    assert haelt.became_satisfied is False
    assert haelt.phase is Phase.SATISFIED

    zu = evaluate_rule(rule, snap("off", minutes=9), state, T0 + timedelta(minutes=9))
    assert zu.became_unsatisfied is True
    assert zu.phase is Phase.IDLE


# -- Testfall B: Zeitbedingung ---------------------------------------------


def test_zeitbedingung_greift_erst_nach_ablauf() -> None:
    """Spezifikation 17: 10 Minuten keine Eskalation, 15 Minuten Alarm."""
    rule = fenster(duration_seconds=900, type=NotificationType.ALARM)
    state = RuleState(rule_id=rule.rule_id)

    start = evaluate_rule(rule, snap("on"), state, T0)
    assert start.phase is Phase.PENDING
    assert start.became_satisfied is False
    assert start.fire_at == T0 + timedelta(minutes=15)

    nach_zehn = evaluate_rule(rule, snap("on", minutes=10), state, T0 + timedelta(minutes=10))
    assert nach_zehn.phase is Phase.PENDING

    nach_fuenfzehn = evaluate_rule(rule, snap("on", minutes=15), state, T0 + timedelta(minutes=15))
    assert nach_fuenfzehn.phase is Phase.SATISFIED
    assert nach_fuenfzehn.became_satisfied is True
    assert nach_fuenfzehn.since == T0


def test_zeitbedingung_verfaellt_wenn_der_zustand_vorher_endet() -> None:
    rule = fenster(duration_seconds=900)
    state = RuleState(rule_id=rule.rule_id)

    evaluate_rule(rule, snap("on"), state, T0)
    evaluate_rule(rule, snap("off", minutes=5), state, T0 + timedelta(minutes=5))
    assert state.phase is Phase.IDLE
    assert state.condition_since is None

    # Erneutes Auftreten startet den Timer von vorn.
    neu = evaluate_rule(rule, snap("on", minutes=6), state, T0 + timedelta(minutes=6))
    assert neu.phase is Phase.PENDING
    assert neu.fire_at == T0 + timedelta(minutes=21)


def test_zeitbedingung_meldet_seit_wann_der_zustand_anliegt() -> None:
    """Die Startzeit ist der Beginn des Zustands, nicht der Timerablauf."""
    rule = fenster(duration_seconds=900)
    state = RuleState(rule_id=rule.rule_id)

    evaluate_rule(rule, snap("on"), state, T0)
    spaet = evaluate_rule(rule, snap("on", minutes=20), state, T0 + timedelta(minutes=20))

    assert spaet.became_satisfied is True
    assert spaet.since == T0


# -- Testfall D: Hysterese --------------------------------------------------


def test_hysterese_haelt_die_notification_zwischen_den_schwellen() -> None:
    """Spezifikation 18: 28.1 aus, 27.9 bleibt, 26.9 endet."""
    rule = numeric(threshold=28.0, release_threshold=27.0)
    state = RuleState(rule_id=rule.rule_id)

    aus = evaluate_rule(rule, snap("28.1"), state, T0)
    assert aus.became_satisfied is True

    bleibt = evaluate_rule(rule, snap("27.9", minutes=1), state, T0 + timedelta(minutes=1))
    assert bleibt.phase is Phase.SATISFIED
    assert bleibt.became_unsatisfied is False

    endet = evaluate_rule(rule, snap("26.9", minutes=2), state, T0 + timedelta(minutes=2))
    assert endet.phase is Phase.IDLE
    assert endet.became_unsatisfied is True


def test_ohne_hysterese_endet_direkt_an_der_schwelle() -> None:
    rule = numeric(threshold=28.0)
    state = RuleState(rule_id=rule.rule_id)

    evaluate_rule(rule, snap("28.1"), state, T0)
    endet = evaluate_rule(rule, snap("27.9", minutes=1), state, T0 + timedelta(minutes=1))
    assert endet.became_unsatisfied is True


def test_hysterese_bei_unterschreitung() -> None:
    rule = numeric(operator=NumericOperator.LT, threshold=5.0, release_threshold=6.0)
    state = RuleState(rule_id=rule.rule_id)

    assert evaluate_rule(rule, snap("4.9"), state, T0).became_satisfied is True
    assert evaluate_rule(rule, snap("5.5", minutes=1), state, T0 + timedelta(minutes=1)).phase is (
        Phase.SATISFIED
    )
    assert (
        evaluate_rule(
            rule, snap("6.1", minutes=2), state, T0 + timedelta(minutes=2)
        ).became_unsatisfied
        is True
    )


@pytest.mark.parametrize(
    ("operator", "schwelle", "wert", "erfuellt"),
    [
        (NumericOperator.GT, 28.0, "28.0", False),
        (NumericOperator.GTE, 28.0, "28.0", True),
        (NumericOperator.LT, 5.0, "5.0", False),
        (NumericOperator.LTE, 5.0, "5.0", True),
        (NumericOperator.EQ, 5.0, "5.0", True),
        (NumericOperator.EQ, 5.0, "5.1", False),
    ],
)
def test_vergleichsoperatoren(
    operator: NumericOperator, schwelle: float, wert: str, erfuellt: bool
) -> None:
    rule = numeric(operator=operator, threshold=schwelle)
    assert trigger_met(rule, snap(wert), None) is erfuellt


# -- Zustand aendert sich zu ------------------------------------------------


def test_zustandswechsel_loest_nur_bei_der_flanke_aus() -> None:
    rule = Rule(
        entity_id="sensor.waschmaschine",
        kind=ConditionKind.STATE_CHANGED_TO,
        states=("finished",),
    )
    state = RuleState(rule_id=rule.rule_id)

    # Erster Blick auf eine bereits fertige Maschine: kein neues Ereignis.
    erst = evaluate_rule(rule, snap("finished"), state, T0)
    assert erst.phase is Phase.IDLE

    evaluate_rule(rule, snap("running", minutes=1), state, T0 + timedelta(minutes=1))
    wechsel = evaluate_rule(rule, snap("finished", minutes=2), state, T0 + timedelta(minutes=2))
    assert wechsel.became_satisfied is True


def test_zustandswechsel_bleibt_aktiv_solange_der_zustand_anliegt() -> None:
    """Zustandsgebunden: die Notification endet beim Verlassen des Zustands."""
    rule = Rule(
        entity_id="sensor.waschmaschine",
        kind=ConditionKind.STATE_CHANGED_TO,
        states=("finished",),
    )
    state = RuleState(rule_id=rule.rule_id)

    evaluate_rule(rule, snap("running"), state, T0)
    evaluate_rule(rule, snap("finished", minutes=1), state, T0 + timedelta(minutes=1))

    haelt = evaluate_rule(rule, snap("finished", minutes=5), state, T0 + timedelta(minutes=5))
    assert haelt.phase is Phase.SATISFIED

    endet = evaluate_rule(rule, snap("idle", minutes=9), state, T0 + timedelta(minutes=9))
    assert endet.became_unsatisfied is True


def test_automatische_enddauer_beendet_trotz_anliegendem_zustand() -> None:
    rule = Rule(
        entity_id="sensor.waschmaschine",
        kind=ConditionKind.STATE_CHANGED_TO,
        states=("finished",),
        auto_end_seconds=300,
    )
    state = RuleState(rule_id=rule.rule_id)

    evaluate_rule(rule, snap("running"), state, T0)
    start = evaluate_rule(rule, snap("finished", minutes=1), state, T0 + timedelta(minutes=1))
    assert start.became_satisfied is True
    assert start.fire_at == T0 + timedelta(minutes=6)

    ablauf = evaluate_rule(rule, snap("finished", minutes=6), state, T0 + timedelta(minutes=6))
    assert ablauf.became_unsatisfied is True

    # Ohne echten Zustandswechsel entsteht sie nicht erneut.
    danach = evaluate_rule(rule, snap("finished", minutes=7), state, T0 + timedelta(minutes=7))
    assert danach.phase is Phase.IDLE


# -- Attribute --------------------------------------------------------------


def test_regel_auf_einem_attribut() -> None:
    """Spezifikation 16: remaining_time unter 5 Minuten."""
    rule = numeric(
        operator=NumericOperator.LT,
        threshold=5.0,
        value_source=ValueSource(kind=ValueSourceKind.ATTRIBUTE, attribute="remaining_time"),
    )
    state = RuleState(rule_id=rule.rule_id)

    viel = evaluate_rule(rule, snap("running", attributes={"remaining_time": 20}), state, T0)
    assert viel.phase is Phase.IDLE

    wenig = evaluate_rule(
        rule,
        snap("running", minutes=1, attributes={"remaining_time": 3}),
        state,
        T0 + timedelta(minutes=1),
    )
    assert wenig.became_satisfied is True
    assert wenig.value == 3


def test_fehlendes_attribut_erfuellt_nicht() -> None:
    rule = numeric(
        value_source=ValueSource(kind=ValueSourceKind.ATTRIBUTE, attribute="fehlt"),
    )
    state = RuleState(rule_id=rule.rule_id)
    assert evaluate_rule(rule, snap("29.0"), state, T0).phase is Phase.IDLE


# -- Deaktivierte Regeln ----------------------------------------------------


def test_deaktivierte_regel_beendet_ihre_notification() -> None:
    """Spezifikation 77."""
    rule = fenster()
    state = RuleState(rule_id=rule.rule_id)
    evaluate_rule(rule, snap("on"), state, T0)

    abgeschaltet = fenster(rule_id=rule.rule_id, enabled=False)
    ergebnis = evaluate_rule(abgeschaltet, snap("on", minutes=1), state, T0 + timedelta(minutes=1))

    assert ergebnis.became_unsatisfied is True
    assert ergebnis.phase is Phase.IDLE


# -- Testfall C: Eskalation -------------------------------------------------


@pytest.fixture
def temperaturgruppe() -> RuleGroup:
    stufen = tuple(
        numeric(
            rule_id=f"rule_{level}", threshold=schwelle, type=typ, group_id="group_1", level=level
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


def test_eskalation_und_deeskalation(temperaturgruppe: RuleGroup) -> None:
    """Testfall C: 26 Info, 29 Warnung, 33 Alarm, 29 Warnung, 24 beendet."""
    state = GroupState(group_id=temperaturgruppe.group_id)
    verlauf = []

    for minute, wert in enumerate(["26", "29", "33", "29", "24"]):
        ergebnis = evaluate_group(
            temperaturgruppe,
            snap(wert, minutes=minute),
            state,
            T0 + timedelta(minutes=minute),
        )
        verlauf.append(ergebnis.active_level)

    assert verlauf == [1, 2, 3, 2, None]


def test_eskalation_meldet_richtungswechsel(temperaturgruppe: RuleGroup) -> None:
    state = GroupState(group_id=temperaturgruppe.group_id)

    hoch = evaluate_group(temperaturgruppe, snap("29"), state, T0)
    assert hoch.escalated is True
    assert hoch.previous_level is None

    weiter = evaluate_group(
        temperaturgruppe, snap("33", minutes=1), state, T0 + timedelta(minutes=1)
    )
    assert weiter.escalated is True
    assert weiter.previous_level == 2

    runter = evaluate_group(
        temperaturgruppe, snap("29", minutes=2), state, T0 + timedelta(minutes=2)
    )
    assert runter.deescalated is True
    assert runter.changed is True

    ende = evaluate_group(temperaturgruppe, snap("20", minutes=3), state, T0 + timedelta(minutes=3))
    assert ende.cleared is True
    assert ende.active_level is None


def test_gleichbleibende_stufe_meldet_keine_aenderung(temperaturgruppe: RuleGroup) -> None:
    state = GroupState(group_id=temperaturgruppe.group_id)
    evaluate_group(temperaturgruppe, snap("29"), state, T0)

    unveraendert = evaluate_group(
        temperaturgruppe, snap("29.5", minutes=1), state, T0 + timedelta(minutes=1)
    )
    assert unveraendert.changed is False
    assert unveraendert.active_level == 2


def test_stufen_haben_unabhaengige_hysterese() -> None:
    """Spezifikation 21: keine Flattereffekte zwischen den Stufen."""
    stufen = (
        numeric(
            rule_id="rule_1",
            threshold=25.0,
            release_threshold=24.0,
            type=NotificationType.INFO,
            group_id="group_1",
            level=1,
        ),
        numeric(
            rule_id="rule_2",
            threshold=28.0,
            release_threshold=27.0,
            type=NotificationType.WARNING,
            group_id="group_1",
            level=2,
        ),
    )
    gruppe = RuleGroup(
        group_id="group_1",
        entity_id="sensor.temperatur_wz",
        name="Temperatur",
        rules=stufen,
    )
    state = GroupState(group_id="group_1")

    assert evaluate_group(gruppe, snap("28.5"), state, T0).active_level == 2

    # 27.5 liegt unter der Warnschwelle, aber ueber deren Rueckkehrschwelle.
    haelt = evaluate_group(gruppe, snap("27.5", minutes=1), state, T0 + timedelta(minutes=1))
    assert haelt.active_level == 2

    # 26.5 loest die Warnung, die Info haelt jedoch weiter.
    zurueck = evaluate_group(gruppe, snap("26.5", minutes=2), state, T0 + timedelta(minutes=2))
    assert zurueck.active_level == 1

    # 24.5 liegt unter der Infoschwelle, aber ueber deren Rueckkehrschwelle.
    info_haelt = evaluate_group(gruppe, snap("24.5", minutes=3), state, T0 + timedelta(minutes=3))
    assert info_haelt.active_level == 1

    ende = evaluate_group(gruppe, snap("23.5", minutes=4), state, T0 + timedelta(minutes=4))
    assert ende.active_level is None


def test_gruppe_mit_zeitbedingung_je_stufe() -> None:
    stufen = (
        numeric(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),
        numeric(
            rule_id="rule_2",
            threshold=28.0,
            duration_seconds=600,
            type=NotificationType.ALARM,
            group_id="group_1",
            level=2,
        ),
    )
    gruppe = RuleGroup(
        group_id="group_1", entity_id="sensor.temperatur_wz", name="Temperatur", rules=stufen
    )
    state = GroupState(group_id="group_1")

    # Die hoehere Stufe wartet noch, die niedrigere ist sofort sichtbar.
    sofort = evaluate_group(gruppe, snap("30"), state, T0)
    assert sofort.active_level == 1

    spaeter = evaluate_group(gruppe, snap("30", minutes=10), state, T0 + timedelta(minutes=10))
    assert spaeter.active_level == 2
    assert spaeter.escalated is True
