"""Tests der Regelmodelle: Gueltigkeit, Serialisierung, Meldungstexte."""

from __future__ import annotations

import pytest

from custom_components.notification_center.notifications.models import NotificationType
from custom_components.notification_center.rules.models import (
    Condition,
    ConditionKind,
    EntitySnapshot,
    LogicOperator,
    NumericOperator,
    Rule,
    RuleGroup,
    ValueSource,
    ValueSourceKind,
    render_message,
    rules_for_entity,
    suggest_message,
)

from .conftest import T0


def make_numeric_rule(**kwargs: object) -> Rule:
    defaults: dict[str, object] = {
        "entity_id": "sensor.temperatur_wz",
        "kind": ConditionKind.NUMERIC,
        "operator": NumericOperator.GT,
        "threshold": 28.0,
    }
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


def make_snapshot(**kwargs: object) -> EntitySnapshot:
    defaults: dict[str, object] = {
        "entity_id": "sensor.temperatur_wz",
        "state": "29.4",
        "last_changed": T0,
        "name": "Temperatur Wohnzimmer",
        "unit": "°C",
    }
    defaults.update(kwargs)
    return EntitySnapshot(**defaults)  # type: ignore[arg-type]


# -- Wertquelle -------------------------------------------------------------


def test_zustandsquelle_liest_den_state() -> None:
    quelle = ValueSource()
    assert quelle.extract(make_snapshot()) == "29.4"


def test_attributquelle_liest_das_attribut() -> None:
    quelle = ValueSource(kind=ValueSourceKind.ATTRIBUTE, attribute="remaining_time")
    snapshot = make_snapshot(attributes={"remaining_time": 4})
    assert quelle.extract(snapshot) == 4


def test_attributquelle_ohne_namen_ist_ungueltig() -> None:
    with pytest.raises(ValueError, match="Attributnamen"):
        ValueSource(kind=ValueSourceKind.ATTRIBUTE)


def test_zustandsquelle_mit_attributnamen_ist_ungueltig() -> None:
    with pytest.raises(ValueError, match="kein"):
        ValueSource(kind=ValueSourceKind.STATE, attribute="remaining_time")


# -- Gueltigkeit numerischer Regeln ----------------------------------------


def test_numerische_regel_braucht_operator_und_schwelle() -> None:
    with pytest.raises(ValueError, match="Operator und Schwelle"):
        Rule(entity_id="sensor.x", kind=ConditionKind.NUMERIC)


def test_numerische_regel_darf_keine_zustaende_haben() -> None:
    with pytest.raises(ValueError, match="Zustandsliste"):
        make_numeric_rule(states=("on",))


@pytest.mark.parametrize(
    ("operator", "release"),
    [(NumericOperator.GT, 29.0), (NumericOperator.GTE, 28.0)],
)
def test_rueckkehrschwelle_muss_unter_der_ausloeseschwelle_liegen(
    operator: NumericOperator, release: float
) -> None:
    with pytest.raises(ValueError, match="kleiner"):
        make_numeric_rule(operator=operator, threshold=28.0, release_threshold=release)


def test_rueckkehrschwelle_bei_unterschreitung_muss_darueber_liegen() -> None:
    with pytest.raises(ValueError, match="groesser"):
        make_numeric_rule(operator=NumericOperator.LT, threshold=5.0, release_threshold=4.0)


def test_gueltige_hysterese_wird_akzeptiert() -> None:
    """Spezifikation 18: Warnung ab 28 Grad, Rueckkehr unter 27 Grad."""
    rule = make_numeric_rule(threshold=28.0, release_threshold=27.0)
    assert rule.release_threshold == 27.0


def test_gleichheitsregel_erlaubt_keine_hysterese() -> None:
    with pytest.raises(ValueError):
        make_numeric_rule(operator=NumericOperator.EQ, threshold=5.0, release_threshold=4.0)


# -- Gueltigkeit von Zustandsregeln ----------------------------------------


def test_zustandsregel_braucht_zustaende() -> None:
    with pytest.raises(ValueError, match="mindestens einen Zustand"):
        Rule(entity_id="binary_sensor.fenster", kind=ConditionKind.STATE_IS)


def test_zustandsregel_darf_keinen_numerischen_vergleich_haben() -> None:
    with pytest.raises(ValueError, match="numerischen Vergleich"):
        Rule(
            entity_id="binary_sensor.fenster",
            kind=ConditionKind.STATE_IS,
            states=("on",),
            operator=NumericOperator.GT,
            threshold=1.0,
        )


# -- Zeitverhalten ----------------------------------------------------------


def test_zeitbedingung_darf_nicht_negativ_sein() -> None:
    with pytest.raises(ValueError, match="negativ"):
        Rule(
            entity_id="binary_sensor.fenster",
            kind=ConditionKind.STATE_IS,
            states=("on",),
            duration_seconds=-1,
        )


def test_automatische_enddauer_nur_bei_zustandswechsel() -> None:
    """Zustandsgebundene Regeln enden ueber ihren Zustand, nicht ueber einen Timer."""
    with pytest.raises(ValueError, match="nur bei"):
        Rule(
            entity_id="binary_sensor.fenster",
            kind=ConditionKind.STATE_IS,
            states=("on",),
            auto_end_seconds=300,
        )


def test_automatische_enddauer_bei_zustandswechsel_ist_erlaubt() -> None:
    rule = Rule(
        entity_id="sensor.waschmaschine",
        kind=ConditionKind.STATE_CHANGED_TO,
        states=("finished",),
        auto_end_seconds=300,
    )
    assert rule.auto_end_seconds == 300


def test_gruppe_und_stufe_nur_gemeinsam() -> None:
    with pytest.raises(ValueError, match="gemeinsam"):
        make_numeric_rule(group_id="group_1")


# -- Serialisierung ---------------------------------------------------------


def test_regel_rundreise_erhaelt_alle_felder() -> None:
    rule = make_numeric_rule(
        type=NotificationType.ALARM,
        release_threshold=27.0,
        duration_seconds=900,
        message_template="{name} bei {value} {unit}",
        title="Wohnzimmer",
        value_source=ValueSource(kind=ValueSourceKind.ATTRIBUTE, attribute="current"),
        group_id="group_1",
        level=3,
    )

    wieder = Rule.from_dict(rule.to_dict())

    assert wieder == rule
    assert wieder.value_source.attribute == "current"
    assert wieder.type is NotificationType.ALARM


def test_with_entity_haengt_regel_um_und_behaelt_die_id() -> None:
    """Spezifikation 66: Regeln wandern beim Ersetzen mit."""
    rule = make_numeric_rule()
    neu = rule.with_entity("sensor.temperatur_neu")

    assert neu.rule_id == rule.rule_id
    assert neu.entity_id == "sensor.temperatur_neu"
    assert rule.entity_id == "sensor.temperatur_wz"


# -- Regelgruppen -----------------------------------------------------------


def make_group(**kwargs: object) -> RuleGroup:
    group_id = "group_1"
    stufen = tuple(
        make_numeric_rule(
            rule_id=f"rule_{level}",
            threshold=schwelle,
            type=typ,
            group_id=group_id,
            level=level,
        )
        for level, schwelle, typ in (
            (1, 25.0, NotificationType.INFO),
            (2, 28.0, NotificationType.WARNING),
            (3, 32.0, NotificationType.ALARM),
        )
    )
    defaults: dict[str, object] = {
        "group_id": group_id,
        "entity_id": "sensor.temperatur_wz",
        "name": "Temperatur Wohnzimmer",
        "rules": stufen,
    }
    defaults.update(kwargs)
    return RuleGroup(**defaults)  # type: ignore[arg-type]


def test_gruppe_ordnet_stufen_aufsteigend() -> None:
    gruppe = make_group()
    assert [rule.threshold for rule in gruppe.ordered_levels] == [25.0, 28.0, 32.0]
    assert [rule.type for rule in gruppe.ordered_levels] == [
        NotificationType.INFO,
        NotificationType.WARNING,
        NotificationType.ALARM,
    ]


def test_gruppe_braucht_monoton_steigende_schwellen() -> None:
    stufen = (
        make_numeric_rule(rule_id="rule_1", threshold=30.0, group_id="group_1", level=1),
        make_numeric_rule(rule_id="rule_2", threshold=28.0, group_id="group_1", level=2),
    )
    with pytest.raises(ValueError, match="groessere"):
        make_group(rules=stufen)


def test_gruppe_mit_fallenden_schwellen_ist_gueltig() -> None:
    stufen = tuple(
        make_numeric_rule(
            rule_id=f"rule_{level}",
            operator=NumericOperator.LT,
            threshold=schwelle,
            group_id="group_1",
            level=level,
        )
        for level, schwelle in ((1, 10.0), (2, 5.0), (3, 2.0))
    )
    gruppe = make_group(rules=stufen)
    assert [rule.threshold for rule in gruppe.ordered_levels] == [10.0, 5.0, 2.0]


def test_gruppe_lehnt_zustandsregeln_ab() -> None:
    """Ohne Ordnung zwischen Zustaenden gibt es keine Eskalation."""
    zustandsregel = Rule(
        entity_id="sensor.temperatur_wz",
        kind=ConditionKind.STATE_IS,
        states=("on",),
        group_id="group_1",
        level=1,
    )
    with pytest.raises(ValueError, match="numerische"):
        make_group(rules=(zustandsregel,))


def test_gruppe_lehnt_gemischte_entities_ab() -> None:
    fremd = make_numeric_rule(
        rule_id="rule_9",
        entity_id="sensor.andere",
        threshold=40.0,
        group_id="group_1",
        level=4,
    )
    with pytest.raises(ValueError, match="selben Entity"):
        make_group(rules=(*make_group().rules, fremd))


def test_gruppe_lehnt_gemischte_wertquellen_ab() -> None:
    stufen = (
        make_numeric_rule(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),
        make_numeric_rule(
            rule_id="rule_2",
            threshold=28.0,
            group_id="group_1",
            level=2,
            value_source=ValueSource(kind=ValueSourceKind.ATTRIBUTE, attribute="current"),
        ),
    )
    with pytest.raises(ValueError, match="dieselbe Wertquelle"):
        make_group(rules=stufen)


def test_gruppe_lehnt_gemischte_operatoren_ab() -> None:
    stufen = (
        make_numeric_rule(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),
        make_numeric_rule(
            rule_id="rule_2",
            operator=NumericOperator.LT,
            threshold=5.0,
            group_id="group_1",
            level=2,
        ),
    )
    with pytest.raises(ValueError, match="denselben Operator"):
        make_group(rules=stufen)


def test_gruppe_lehnt_doppelte_stufennummern_ab() -> None:
    stufen = (
        make_numeric_rule(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),
        make_numeric_rule(rule_id="rule_2", threshold=28.0, group_id="group_1", level=1),
    )
    with pytest.raises(ValueError, match="eindeutig"):
        make_group(rules=stufen)


def test_gruppe_rundreise() -> None:
    gruppe = make_group()
    wieder = RuleGroup.from_dict(gruppe.to_dict())
    assert wieder.group_id == gruppe.group_id
    assert len(wieder.rules) == 3
    assert wieder.rule_for_level(2) is not None
    assert wieder.rule_for_level(9) is None


# -- Meldungstexte ----------------------------------------------------------


def test_platzhalter_werden_ersetzt() -> None:
    text = render_message("{name}: {value} {unit}", make_snapshot(), value=29.4)
    assert text == "Temperatur Wohnzimmer: 29.4 °C"


def test_unbekannter_platzhalter_bleibt_stehen() -> None:
    """Ein Tippfehler soll sichtbar sein, nicht still verschwinden."""
    text = render_message("{nmae} zu hoch", make_snapshot())
    assert text == "{nmae} zu hoch"


def test_fehlende_einheit_hinterlaesst_keine_luecke() -> None:
    snapshot = make_snapshot(unit=None)
    assert render_message("{name} {unit}", snapshot) == "Temperatur Wohnzimmer"


def test_name_faellt_auf_entity_id_zurueck() -> None:
    snapshot = make_snapshot(name=None)
    assert render_message("{name}", snapshot) == "sensor.temperatur_wz"


def test_vorschlagstext_numerisch() -> None:
    text = suggest_message(make_numeric_rule(threshold=28.0), make_snapshot())
    assert text == "Temperatur Wohnzimmer ueber 28"


def test_vorschlagstext_zustand() -> None:
    rule = Rule(
        entity_id="binary_sensor.fenster",
        kind=ConditionKind.STATE_IS,
        states=("offen",),
    )
    snapshot = make_snapshot(entity_id="binary_sensor.fenster", name="Fenster Wohnzimmer")
    assert suggest_message(rule, snapshot) == "Fenster Wohnzimmer: offen"


# -- Mehrere Regeln pro Entity ---------------------------------------------


def test_mehrere_regeln_derselben_entity_bleiben_nebeneinander() -> None:
    """Parallele Regeln erzeugen parallele Notifications."""
    regeln = [
        make_numeric_rule(rule_id="rule_1", threshold=28.0),
        make_numeric_rule(rule_id="rule_2", operator=NumericOperator.LT, threshold=5.0),
        make_numeric_rule(rule_id="rule_3", entity_id="sensor.andere", threshold=10.0),
    ]
    treffer = rules_for_entity(regeln, "sensor.temperatur_wz")
    assert [rule.rule_id for rule in treffer] == ["rule_1", "rule_2"]


# -- Verknuepfte Bedingungen ------------------------------------------------


def test_regel_ohne_weitere_bedingungen_bleibt_wie_sie_war() -> None:
    """Die Erweiterung darf an bestehenden Regeln nichts aendern."""
    rule = make_numeric_rule()
    assert rule.is_combined is False
    assert rule.logic is LogicOperator.ALL
    assert rule.conditions == (rule.primary_condition,)
    assert rule.referenced_entity_ids == frozenset({"sensor.temperatur_wz"})


def test_erste_bedingung_stammt_aus_den_feldern_der_regel() -> None:
    rule = make_numeric_rule(threshold=28.0, release_threshold=27.0)
    erste = rule.primary_condition

    assert erste.kind is ConditionKind.NUMERIC
    assert (erste.operator, erste.threshold, erste.release_threshold) == (
        NumericOperator.GT,
        28.0,
        27.0,
    )
    # Ohne eigene Kennung: die Bedingung betrachtet die Entity der Regel.
    assert erste.entity_id is None


def test_weitere_bedingung_darf_eine_andere_entity_betrachten() -> None:
    rule = make_numeric_rule(
        extra_conditions=(
            Condition(
                kind=ConditionKind.STATE_IS,
                entity_id="climate.wohnzimmer",
                states=("heat",),
            ),
        )
    )

    assert rule.is_combined is True
    assert len(rule.conditions) == 2
    assert rule.entity_for(rule.extra_conditions[0]) == "climate.wohnzimmer"
    assert rule.referenced_entity_ids == frozenset({"sensor.temperatur_wz", "climate.wohnzimmer"})


def test_bedingung_ohne_kennung_folgt_der_entity_der_regel() -> None:
    """Eine zweite Bedingung auf dieselbe Entity braucht keine Kennung."""
    rule = make_numeric_rule(
        extra_conditions=(
            Condition(
                kind=ConditionKind.STATE_IS_NOT,
                value_source=ValueSource(kind=ValueSourceKind.ATTRIBUTE, attribute="mode"),
                states=("off",),
            ),
        )
    )

    assert rule.entity_for(rule.extra_conditions[0]) == "sensor.temperatur_wz"
    assert rule.referenced_entity_ids == frozenset({"sensor.temperatur_wz"})


def test_bedingungen_werden_vollstaendig_serialisiert() -> None:
    rule = make_numeric_rule(
        logic=LogicOperator.ANY,
        extra_conditions=(
            Condition(kind=ConditionKind.STATE_IS, entity_id="person.alex", states=("home",)),
            Condition(
                kind=ConditionKind.NUMERIC,
                entity_id="sensor.luftfeuchte",
                operator=NumericOperator.GTE,
                threshold=70.0,
                release_threshold=65.0,
                negate=True,
            ),
        ),
    )

    wieder = Rule.from_dict(rule.to_dict())
    assert wieder == rule
    assert wieder.logic is LogicOperator.ANY
    assert wieder.extra_conditions[1].negate is True
    assert wieder.extra_conditions[1].release_threshold == 65.0


def test_alte_gespeicherte_regel_laedt_ohne_bedingungsfelder() -> None:
    """Eine Konfiguration von vor der Erweiterung bleibt lesbar."""
    daten = make_numeric_rule().to_dict()
    del daten["logic"]
    del daten["extra_conditions"]

    rule = Rule.from_dict(daten)
    assert rule.logic is LogicOperator.ALL
    assert rule.extra_conditions == ()


def test_teilbedingung_wird_wie_eine_regel_geprueft() -> None:
    with pytest.raises(ValueError, match="mindestens einen Zustand"):
        Condition(kind=ConditionKind.STATE_IS)

    with pytest.raises(ValueError, match="Operator und Schwelle"):
        Condition(kind=ConditionKind.NUMERIC)

    with pytest.raises(ValueError, match="kleiner"):
        Condition(
            kind=ConditionKind.NUMERIC,
            operator=NumericOperator.GT,
            threshold=20.0,
            release_threshold=25.0,
        )


def test_eine_flanke_laesst_sich_nicht_verneinen() -> None:
    """Die Verneinung eines Augenblicks waere fast immer wahr."""
    with pytest.raises(ValueError, match="verneinen"):
        Condition(kind=ConditionKind.STATE_CHANGED_TO, states=("on",), negate=True)


def test_stufen_einer_gruppe_tragen_keine_weiteren_bedingungen() -> None:
    with pytest.raises(ValueError, match="keine weiteren Bedingungen"):
        make_numeric_rule(
            group_id="group_1",
            level=1,
            extra_conditions=(Condition(kind=ConditionKind.STATE_IS, states=("on",)),),
        )


def test_entitytausch_haengt_auch_teilbedingungen_um() -> None:
    rule = make_numeric_rule(
        extra_conditions=(
            Condition(kind=ConditionKind.STATE_IS, entity_id="climate.alt", states=("heat",)),
            Condition(kind=ConditionKind.STATE_IS, entity_id="person.alex", states=("home",)),
        )
    )

    neu = rule.with_partner_replaced("climate.alt", "climate.neu")
    assert [bed.entity_id for bed in neu.extra_conditions] == ["climate.neu", "person.alex"]

    # Ohne Treffer bleibt die Regel dieselbe und wird nicht kopiert.
    assert rule.with_partner_replaced("light.irgendwas", "light.anders") is rule
