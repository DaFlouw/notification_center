"""Tests des Konfigurationsdokuments: Entities, Regeln, Ersetzen, Migration."""

from __future__ import annotations

import pytest

from custom_components.notification_center.notifications.models import NotificationType
from custom_components.notification_center.rules.models import (
    ConditionKind,
    NumericOperator,
    Rule,
    RuleGroup,
)
from custom_components.notification_center.storage.config_models import (
    ConfigDocument,
    ConfigError,
    Settings,
    WatchedEntity,
    entities_from_ids,
    migrate_config,
)


def make_rule(entity_id: str = "sensor.temperatur_wz", **kwargs: object) -> Rule:
    defaults: dict[str, object] = {
        "entity_id": entity_id,
        "kind": ConditionKind.NUMERIC,
        "operator": NumericOperator.GT,
        "threshold": 28.0,
    }
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def document() -> ConfigDocument:
    doc = ConfigDocument.empty()
    doc.add_entity(WatchedEntity(entity_id="sensor.temperatur_wz", area_id="wohnzimmer"))
    doc.add_entity(WatchedEntity(entity_id="binary_sensor.fenster_wz", area_id="wohnzimmer"))
    return doc


# -- Einstellungen ----------------------------------------------------------


def test_standardeinstellungen_sind_gueltig() -> None:
    settings = Settings()
    assert settings.paused is False
    assert settings.setup_completed is False


def test_unzulaessige_aufbewahrungsdauer_wird_abgelehnt() -> None:
    with pytest.raises(ConfigError, match="Aufbewahrungsdauer"):
        Settings(retention_days=42)


def test_unzulaessige_maximalmenge_wird_abgelehnt() -> None:
    with pytest.raises(ConfigError, match="Ereignisanzahl"):
        Settings(max_events=1234)


def test_unbegrenzte_aufbewahrung_ist_zulaessig() -> None:
    assert Settings(retention_days=0).retention_days == 0


# -- Entities ---------------------------------------------------------------


def test_entities_werden_explizit_uebernommen(document: ConfigDocument) -> None:
    """Spezifikation 7: nur ausgewaehlte Entities werden ueberwacht."""
    assert document.monitored_entity_ids == frozenset(
        {"sensor.temperatur_wz", "binary_sensor.fenster_wz"}
    )


def test_doppelte_uebernahme_ueberschreibt_nicht(document: ConfigDocument) -> None:
    zuvor = document.entities["sensor.temperatur_wz"].added_at
    document.add_entity(WatchedEntity(entity_id="sensor.temperatur_wz"))
    assert document.entities["sensor.temperatur_wz"].added_at == zuvor


def test_regel_fuer_nicht_ueberwachte_entity_wird_abgelehnt(document: ConfigDocument) -> None:
    with pytest.raises(ConfigError, match="nicht ueberwachte"):
        document.add_rule(make_rule("sensor.unbekannt"))


def test_entity_entfernen_loescht_ihre_regeln(document: ConfigDocument) -> None:
    """Spezifikation 78: Historie bleibt, Regeln verschwinden."""
    document.add_rule(make_rule(rule_id="rule_1"))
    document.add_rule(make_rule(rule_id="rule_2"))
    document.add_rule(
        make_rule(
            "binary_sensor.fenster_wz",
            rule_id="rule_3",
            kind=ConditionKind.STATE_IS,
            states=("on",),
            operator=None,
            threshold=None,
        )
    )

    entfernt = document.remove_entity("sensor.temperatur_wz")

    assert sorted(entfernt) == ["rule_1", "rule_2"]
    assert set(document.rules) == {"rule_3"}
    assert "sensor.temperatur_wz" not in document.entities


def test_entity_entfernen_loescht_ihre_gruppen(document: ConfigDocument) -> None:
    gruppe = RuleGroup(
        group_id="group_1",
        entity_id="sensor.temperatur_wz",
        name="Temperatur",
        rules=(
            make_rule(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),
            make_rule(rule_id="rule_2", threshold=30.0, group_id="group_1", level=2),
        ),
    )
    document.add_group(gruppe)

    document.remove_entity("sensor.temperatur_wz")

    assert document.groups == {}
    assert document.rules == {}


def test_unbekannte_entity_entfernen_schlaegt_fehl(document: ConfigDocument) -> None:
    with pytest.raises(ConfigError, match="nicht ueberwacht"):
        document.remove_entity("sensor.gibtsnicht")


# -- Regeln -----------------------------------------------------------------


def test_regel_entfernen_pflegt_die_gruppe(document: ConfigDocument) -> None:
    gruppe = RuleGroup(
        group_id="group_1",
        entity_id="sensor.temperatur_wz",
        name="Temperatur",
        rules=(
            make_rule(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),
            make_rule(rule_id="rule_2", threshold=30.0, group_id="group_1", level=2),
        ),
    )
    document.add_group(gruppe)

    document.remove_rule("rule_1")

    assert [rule.rule_id for rule in document.groups["group_1"].rules] == ["rule_2"]


def test_letzte_stufe_entfernen_loest_die_gruppe_auf(document: ConfigDocument) -> None:
    gruppe = RuleGroup(
        group_id="group_1",
        entity_id="sensor.temperatur_wz",
        name="Temperatur",
        rules=(make_rule(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),),
    )
    document.add_group(gruppe)

    document.remove_rule("rule_1")

    assert document.groups == {}


def test_unbekannte_regel_entfernen_schlaegt_fehl(document: ConfigDocument) -> None:
    with pytest.raises(ConfigError, match="Unbekannte Regel"):
        document.remove_rule("rule_gibtsnicht")


def test_rules_for_liefert_nur_die_passenden(document: ConfigDocument) -> None:
    document.add_rule(make_rule(rule_id="rule_1"))
    document.add_rule(
        make_rule(
            "binary_sensor.fenster_wz",
            rule_id="rule_2",
            kind=ConditionKind.STATE_IS,
            states=("on",),
            operator=None,
            threshold=None,
        )
    )
    assert [rule.rule_id for rule in document.rules_for("sensor.temperatur_wz")] == ["rule_1"]


# -- Entity ersetzen (Spezifikation 66) ------------------------------------


def test_ersetzen_haengt_regeln_um(document: ConfigDocument) -> None:
    document.add_rule(make_rule(rule_id="rule_1", type=NotificationType.ALARM))

    umgehaengt = document.replace_entity(
        "sensor.temperatur_wz", WatchedEntity(entity_id="sensor.temperatur_neu")
    )

    assert umgehaengt == ["rule_1"]
    assert document.rules["rule_1"].entity_id == "sensor.temperatur_neu"
    assert document.rules["rule_1"].type is NotificationType.ALARM
    assert "sensor.temperatur_wz" not in document.entities
    assert document.entities["sensor.temperatur_neu"].replaced_entity_id == ("sensor.temperatur_wz")


def test_ersetzen_haengt_auch_gruppen_um(document: ConfigDocument) -> None:
    gruppe = RuleGroup(
        group_id="group_1",
        entity_id="sensor.temperatur_wz",
        name="Temperatur",
        rules=(
            make_rule(rule_id="rule_1", threshold=25.0, group_id="group_1", level=1),
            make_rule(rule_id="rule_2", threshold=30.0, group_id="group_1", level=2),
        ),
    )
    document.add_group(gruppe)

    document.replace_entity(
        "sensor.temperatur_wz", WatchedEntity(entity_id="sensor.temperatur_neu")
    )

    umgehaengt = document.groups["group_1"]
    assert umgehaengt.entity_id == "sensor.temperatur_neu"
    assert all(rule.entity_id == "sensor.temperatur_neu" for rule in umgehaengt.rules)


def test_ersetzen_durch_bereits_ueberwachte_entity_wird_abgelehnt(
    document: ConfigDocument,
) -> None:
    with pytest.raises(ConfigError, match="bereits ueberwacht"):
        document.replace_entity(
            "sensor.temperatur_wz", WatchedEntity(entity_id="binary_sensor.fenster_wz")
        )


def test_ersetzen_einer_unbekannten_entity_wird_abgelehnt(document: ConfigDocument) -> None:
    with pytest.raises(ConfigError, match="nicht ueberwacht"):
        document.replace_entity("sensor.gibtsnicht", WatchedEntity(entity_id="sensor.neu"))


# -- Serialisierung und Migration ------------------------------------------


def test_dokument_rundreise(document: ConfigDocument) -> None:
    document.add_rule(make_rule(rule_id="rule_1", message_template="{name} zu warm"))
    document.settings.paused = True

    wieder = ConfigDocument.from_dict(document.to_dict())

    assert wieder.monitored_entity_ids == document.monitored_entity_ids
    assert wieder.rules["rule_1"].message_template == "{name} zu warm"
    assert wieder.settings.paused is True
    assert wieder.entities["sensor.temperatur_wz"].area_id == "wohnzimmer"


def test_leeres_dokument_ist_serialisierbar() -> None:
    wieder = ConfigDocument.from_dict(ConfigDocument.empty().to_dict())
    assert wieder.entities == {}
    assert wieder.rules == {}


def test_migration_setzt_die_aktuelle_version() -> None:
    data = migrate_config({"minor_version": 1}, from_minor=1)
    assert data["minor_version"] == 1


def test_migration_lehnt_neuere_version_ab() -> None:
    with pytest.raises(ConfigError, match="heruntergestuft"):
        migrate_config({"minor_version": 99}, from_minor=99)


# -- Hilfsfunktionen --------------------------------------------------------


def test_entities_from_ids_uebernimmt_geraet_und_bereich() -> None:
    entities = entities_from_ids(
        ["sensor.a", "sensor.b"],
        device_ids={"sensor.a": "dev-1"},
        area_ids={"sensor.a": "keller"},
    )
    assert entities[0].device_id == "dev-1"
    assert entities[0].area_id == "keller"
    assert entities[1].device_id is None
