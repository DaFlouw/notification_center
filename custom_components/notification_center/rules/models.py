"""Datenmodelle der Rule Engine.

Dieses Modul enthaelt bewusst keine Home-Assistant-Importe: es beschreibt nur
Struktur, Gueltigkeit und Serialisierung von Regeln. Die eigentliche
Auswertung liegt in ``evaluator.py``.

Regeln gehoeren immer zu genau einer Entity (Spezifikation 8). Geraete sind
reine Komfort-Gruppierung in der Oberflaeche und tauchen hier nicht auf.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from itertools import pairwise
from typing import Any

from ..const import MODEL_SCHEMA_VERSION
from ..notifications.models import NotificationType

#: Platzhalter, die in Meldungstexten ersetzt werden.
PLACEHOLDERS = ("name", "state", "value", "unit", "entity_id")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Eingangsdaten der Auswertung
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EntitySnapshot:
    """Zustand einer Entity zu einem Zeitpunkt.

    Bewusst eine eigene, HA-freie Struktur: die Rule Engine soll ohne
    Home-Assistant-Runtime testbar bleiben. Die Integration erzeugt diese
    Objekte aus ``hass.states``.
    """

    entity_id: str
    state: str
    last_changed: datetime
    attributes: Mapping[str, Any] = field(default_factory=dict)
    name: str | None = None
    unit: str | None = None
    device_id: str | None = None
    area_id: str | None = None

    @property
    def display_name(self) -> str:
        return self.name or self.entity_id


# ---------------------------------------------------------------------------
# Wertquelle
# ---------------------------------------------------------------------------


class ValueSourceKind(StrEnum):
    """Woraus eine Regel ihren Wert bezieht."""

    STATE = "state"
    ATTRIBUTE = "attribute"


@dataclass(frozen=True, slots=True)
class ValueSource:
    """Zustand oder ein Attribut der Entity (Spezifikation 16)."""

    kind: ValueSourceKind = ValueSourceKind.STATE
    attribute: str | None = None

    def __post_init__(self) -> None:
        if self.kind is ValueSourceKind.ATTRIBUTE and not self.attribute:
            raise ValueError("Attribut-Wertquelle benoetigt einen Attributnamen")
        if self.kind is ValueSourceKind.STATE and self.attribute:
            raise ValueError("Zustands-Wertquelle darf keinen Attributnamen haben")

    def extract(self, snapshot: EntitySnapshot) -> Any:
        """Liest den Rohwert aus einem Snapshot."""
        if self.kind is ValueSourceKind.STATE:
            return snapshot.state
        return snapshot.attributes.get(self.attribute or "")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": str(self.kind), "attribute": self.attribute}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ValueSource:
        return cls(
            kind=ValueSourceKind(data.get("kind", ValueSourceKind.STATE)),
            attribute=data.get("attribute"),
        )


STATE_SOURCE = ValueSource()


# ---------------------------------------------------------------------------
# Bedingungsarten
# ---------------------------------------------------------------------------


class ConditionKind(StrEnum):
    """Die vier Faelle des einfachen Regel-Editors (Spezifikation 14)."""

    #: Zustand ist einer der angegebenen Werte, solange er anliegt.
    STATE_IS = "state_is"
    #: Zustand ist keiner der angegebenen Werte.
    STATE_IS_NOT = "state_is_not"
    #: Zustand wechselt in einen der angegebenen Werte.
    STATE_CHANGED_TO = "state_changed_to"
    #: Numerischer Vergleich gegen eine Schwelle.
    NUMERIC = "numeric"


class NumericOperator(StrEnum):
    """Vergleichsoperatoren numerischer Regeln (Spezifikation 15)."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"

    @property
    def is_upper_bound(self) -> bool:
        """True, wenn die Regel bei *steigendem* Wert ausloest."""
        return self in (NumericOperator.GT, NumericOperator.GTE)

    @property
    def is_lower_bound(self) -> bool:
        """True, wenn die Regel bei *fallendem* Wert ausloest."""
        return self in (NumericOperator.LT, NumericOperator.LTE)


# ---------------------------------------------------------------------------
# Logische Verknuepfung
# ---------------------------------------------------------------------------


class LogicOperator(StrEnum):
    """Wie die Bedingungen einer Regel zusammenwirken.

    Bewusst nur zwei Operatoren und eine Ebene: eine Regel verknuepft ihre
    Bedingungen entweder alle oder beliebig eine. Gemischte Vorrang-Ketten
    (``A und (B oder C)``) sind nicht vorgesehen -- sie liessen sich im
    Regel-Editor nicht ohne Klammern darstellen, und wer sie braucht, ist mit
    einer Automation besser bedient. Die Verneinung einer einzelnen Bedingung
    ist dagegen moeglich (:attr:`Condition.negate`), womit die drei
    klassischen Operatoren UND, ODER und NICHT abgedeckt sind.
    """

    #: Jede Bedingung muss zutreffen (UND).
    ALL = "all"
    #: Eine zutreffende Bedingung genuegt (ODER).
    ANY = "any"


def _validate_numeric_parts(
    operator: NumericOperator | None,
    threshold: float | None,
    release_threshold: float | None,
    states: tuple[str, ...],
) -> None:
    """Pruefung einer numerischen Bedingung, fuer Regel und Teilbedingung."""
    if operator is None or threshold is None:
        raise ValueError("Numerische Regel benoetigt Operator und Schwelle")
    if states:
        raise ValueError("Numerische Regel darf keine Zustandsliste haben")
    if release_threshold is None:
        return

    # Die Rueckkehrschwelle muss auf der 'ruhigen' Seite der Schwelle
    # liegen, sonst entsteht kein Hysteresefenster, sondern eine Luecke.
    if operator.is_upper_bound and release_threshold >= threshold:
        raise ValueError("Rueckkehrschwelle muss kleiner als die Ausloeseschwelle sein")
    if operator.is_lower_bound and release_threshold <= threshold:
        raise ValueError("Rueckkehrschwelle muss groesser als die Ausloeseschwelle sein")
    if operator is NumericOperator.EQ:
        raise ValueError("Gleichheitsregeln unterstuetzen keine Hysterese")


def _validate_state_parts(
    states: tuple[str, ...],
    operator: NumericOperator | None,
    threshold: float | None,
    release_threshold: float | None,
) -> None:
    """Pruefung einer Zustandsbedingung, fuer Regel und Teilbedingung."""
    if not states:
        raise ValueError("Zustandsregel benoetigt mindestens einen Zustand")
    if operator is not None or threshold is not None:
        raise ValueError("Zustandsregel darf keinen numerischen Vergleich haben")
    if release_threshold is not None:
        raise ValueError("Zustandsregel unterstuetzt keine Hysterese")


@dataclass(frozen=True, slots=True)
class Condition:
    """Eine weitere Bedingung einer Regel (Spezifikation 14).

    Eine Regel gehoert weiterhin zu genau einer Entity: sie ist der Gegenstand
    der Meldung, liefert die Platzhalter des Meldungstexts und bestimmt Raum
    und Geschoss in der Historie. Eine Teilbedingung darf aber eine *andere*
    Entity betrachten -- das ist der eigentliche Zweck der Verknuepfung:
    "Fenster offen, waehrend die Heizung laeuft" ist eine Aussage ueber zwei
    Entities, aber eine Meldung ueber das Fenster.

    ``entity_id`` bleibt ``None``, solange sich die Bedingung auf die Entity
    der Regel bezieht. So bleibt eine Regel beim Entitytausch
    (Spezifikation 66) in einem Stueck: die Teilbedingung wandert mit, ohne
    dass irgendwo eine alte Kennung stehen bleibt.

    ``negate`` verneint das Ergebnis dieser einen Bedingung. Nicht verwendbar
    bei "Zustand aendert sich zu": die Verneinung eines Augenblicks waere
    praktisch immer wahr und damit nie das, was gemeint ist.
    """

    kind: ConditionKind
    entity_id: str | None = None
    value_source: ValueSource = STATE_SOURCE
    negate: bool = False

    # Zustandsbedingungen
    states: tuple[str, ...] = ()

    # Numerische Bedingungen
    operator: NumericOperator | None = None
    threshold: float | None = None
    release_threshold: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "states", tuple(self.states))

        if self.kind is ConditionKind.NUMERIC:
            _validate_numeric_parts(
                self.operator, self.threshold, self.release_threshold, self.states
            )
        else:
            _validate_state_parts(
                self.states, self.operator, self.threshold, self.release_threshold
            )

        if self.negate and self.kind is ConditionKind.STATE_CHANGED_TO:
            raise ValueError(
                "'Zustand aendert sich zu' laesst sich nicht verneinen: der Wechsel "
                "ist ein Augenblick, seine Verneinung waere fast immer wahr. "
                "Gemeint ist meist 'Zustand ist nicht'"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": str(self.kind),
            "entity_id": self.entity_id,
            "value_source": self.value_source.to_dict(),
            "negate": self.negate,
            "states": list(self.states),
            "operator": str(self.operator) if self.operator else None,
            "threshold": self.threshold,
            "release_threshold": self.release_threshold,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Condition:
        operator = data.get("operator")
        return cls(
            kind=ConditionKind(data["kind"]),
            entity_id=data.get("entity_id"),
            value_source=ValueSource.from_dict(data.get("value_source", {})),
            negate=bool(data.get("negate", False)),
            states=tuple(data.get("states", ())),
            operator=NumericOperator(operator) if operator else None,
            threshold=data.get("threshold"),
            release_threshold=data.get("release_threshold"),
        )


# ---------------------------------------------------------------------------
# Regel
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Rule:
    """Eine einzelne Regel einer ueberwachten Entity.

    Zeitverhalten:

    * ``duration_seconds`` ist die optionale Zeitbedingung aus
      Spezifikation 17: die Bedingung muss ununterbrochen so lange anliegen,
      bevor eine Notification entsteht. Endet der Zustand vorher, verfaellt
      der Timer; tritt er erneut auf, beginnt er von vorn.
    * ``auto_end_seconds`` beendet eine bereits laufende Notification nach
      Ablauf. Nur fuer ``STATE_CHANGED_TO`` sinnvoll, wo ein echtes
      Momentereignis abgebildet werden soll.

    ``release_threshold`` ist die Hysterese-Rueckkehrschwelle aus
    Spezifikation 18: die Notification bleibt aktiv, bis der Wert diese
    Schwelle wieder ueberschreitet beziehungsweise unterschreitet.
    """

    entity_id: str
    kind: ConditionKind
    type: NotificationType = NotificationType.WARNING

    rule_id: str = field(default_factory=lambda: new_id("rule"))
    enabled: bool = True
    value_source: ValueSource = STATE_SOURCE

    # Zustandsbedingungen
    states: tuple[str, ...] = ()

    # Numerische Bedingungen
    operator: NumericOperator | None = None
    threshold: float | None = None
    release_threshold: float | None = None

    # Zeitverhalten
    duration_seconds: float | None = None
    auto_end_seconds: float | None = None

    # Darstellung
    message_template: str = ""
    title: str | None = None

    # Eskalation
    group_id: str | None = None
    level: int | None = None

    # Verknuepfung weiterer Bedingungen
    logic: LogicOperator = LogicOperator.ALL
    extra_conditions: tuple[Condition, ...] = ()

    schema_version: int = MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.states = tuple(self.states)
        self.extra_conditions = tuple(self.extra_conditions)
        self._validate()

    # -- Bedingungen -----------------------------------------------------

    @property
    def primary_condition(self) -> Condition:
        """Die erste Bedingung, aus den Feldern der Regel selbst.

        Die Regel traegt ihre erste Bedingung weiterhin direkt in ``kind``,
        ``states``, ``operator`` und ``threshold``; weitere Bedingungen
        kommen in ``extra_conditions`` hinzu. Das haelt jede bestehende
        Regel, jede gespeicherte Konfiguration und jeden Vorschlag der
        Discovery unveraendert gueltig -- eine einzelne Bedingung sieht nach
        wie vor genauso aus wie vorher.
        """
        return Condition(
            kind=self.kind,
            value_source=self.value_source,
            states=self.states,
            operator=self.operator,
            threshold=self.threshold,
            release_threshold=self.release_threshold,
        )

    @property
    def conditions(self) -> tuple[Condition, ...]:
        """Alle Bedingungen der Regel, die erste zuerst."""
        return (self.primary_condition, *self.extra_conditions)

    @property
    def is_combined(self) -> bool:
        return bool(self.extra_conditions)

    def entity_for(self, condition: Condition) -> str:
        """Die Entity, die eine Bedingung betrachtet."""
        return condition.entity_id or self.entity_id

    @property
    def referenced_entity_ids(self) -> frozenset[str]:
        """Alle Entities, von denen die Regel abhaengt.

        Grundlage der Ueberwachung: auch eine Entity, die nur in einer
        Teilbedingung vorkommt, muss beobachtet werden -- sonst bemerkt die
        Regel deren Wechsel nicht.
        """
        return frozenset({self.entity_id, *(self.entity_for(bed) for bed in self.extra_conditions)})

    # -- Gueltigkeit -----------------------------------------------------

    def _validate(self) -> None:
        if not self.entity_id:
            raise ValueError("Regel benoetigt eine entity_id")

        if self.kind is ConditionKind.NUMERIC:
            self._validate_numeric()
        else:
            self._validate_state()

        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("Zeitbedingung darf nicht negativ sein")
        if self.auto_end_seconds is not None:
            if self.auto_end_seconds <= 0:
                raise ValueError("Automatische Enddauer muss groesser als null sein")
            if self.kind is not ConditionKind.STATE_CHANGED_TO:
                raise ValueError(
                    "Automatische Enddauer ist nur bei 'Zustand aendert sich zu' "
                    "vorgesehen; andere Regeln enden zustandsgebunden"
                )
        if (self.group_id is None) != (self.level is None):
            raise ValueError("group_id und level muessen gemeinsam gesetzt sein")

        if self.extra_conditions and self.group_id is not None:
            # Eine Eskalationsgruppe ordnet ihre Stufen allein nach der
            # Schwelle (siehe RuleGroup). Eine Stufe mit zusaetzlichen
            # Bedingungen koennte erfuellt sein, waehrend die niedrigere es
            # nicht ist -- die Reihenfolge waere nicht mehr wohldefiniert.
            raise ValueError("Stufen einer Regelgruppe tragen keine weiteren Bedingungen")

    def _validate_numeric(self) -> None:
        _validate_numeric_parts(self.operator, self.threshold, self.release_threshold, self.states)

    def _validate_state(self) -> None:
        _validate_state_parts(self.states, self.operator, self.threshold, self.release_threshold)

    # -- Serialisierung --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "schema_version": self.schema_version,
            "entity_id": self.entity_id,
            "kind": str(self.kind),
            "type": str(self.type),
            "enabled": self.enabled,
            "value_source": self.value_source.to_dict(),
            "states": list(self.states),
            "operator": str(self.operator) if self.operator else None,
            "threshold": self.threshold,
            "release_threshold": self.release_threshold,
            "duration_seconds": self.duration_seconds,
            "auto_end_seconds": self.auto_end_seconds,
            "message_template": self.message_template,
            "title": self.title,
            "group_id": self.group_id,
            "level": self.level,
            "logic": str(self.logic),
            "extra_conditions": [bedingung.to_dict() for bedingung in self.extra_conditions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Rule:
        operator = data.get("operator")
        return cls(
            rule_id=data["rule_id"],
            schema_version=data.get("schema_version", MODEL_SCHEMA_VERSION),
            entity_id=data["entity_id"],
            kind=ConditionKind(data["kind"]),
            type=NotificationType(data.get("type", NotificationType.WARNING)),
            enabled=data.get("enabled", True),
            value_source=ValueSource.from_dict(data.get("value_source", {})),
            states=tuple(data.get("states", ())),
            operator=NumericOperator(operator) if operator else None,
            threshold=data.get("threshold"),
            release_threshold=data.get("release_threshold"),
            duration_seconds=data.get("duration_seconds"),
            auto_end_seconds=data.get("auto_end_seconds"),
            message_template=data.get("message_template", ""),
            title=data.get("title"),
            group_id=data.get("group_id"),
            level=data.get("level"),
            logic=LogicOperator(data.get("logic", LogicOperator.ALL)),
            extra_conditions=tuple(
                Condition.from_dict(item) for item in data.get("extra_conditions", ())
            ),
        )

    def with_entity(self, entity_id: str) -> Rule:
        """Kopie der Regel fuer eine andere Entity (Spezifikation 66).

        Teilbedingungen ohne eigene Kennung wandern dabei mit: sie beziehen
        sich auf die Entity der Regel.
        """
        return replace(self, entity_id=entity_id)

    def with_partner_replaced(self, old_entity_id: str, new_entity_id: str) -> Rule:
        """Haengt Teilbedingungen auf eine andere Entity um.

        Wird beim Entitytausch gebraucht: wer eine Entity ersetzt, erwartet,
        dass auch die Regeln *anderer* Entities, die sie als Bedingung
        heranziehen, weiterhin greifen. Ohne das zeigten sie stumm nie wieder
        etwas, weil die alte Kennung nirgends mehr existiert.
        """
        if not any(bed.entity_id == old_entity_id for bed in self.extra_conditions):
            return self
        return replace(
            self,
            extra_conditions=tuple(
                replace(bed, entity_id=new_entity_id) if bed.entity_id == old_entity_id else bed
                for bed in self.extra_conditions
            ),
        )


# ---------------------------------------------------------------------------
# Regelgruppe
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RuleGroup:
    """Eskalationsstufen einer Entity (Spezifikation 19 bis 21).

    Eine Gruppe buendelt mehrere numerische Regeln derselben Entity und
    derselben Wertquelle, die sich nur in Schwelle, Typ und Hysterese
    unterscheiden. Nur die hoechste gueltige Stufe ist aktiv.

    Zustandsregeln bilden keine Gruppen: ohne Ordnungsrelation zwischen
    Zustaenden laesst sich keine Eskalation definieren.
    """

    entity_id: str
    name: str
    group_id: str = field(default_factory=lambda: new_id("group"))
    rules: tuple[Rule, ...] = ()
    schema_version: int = MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.rules = tuple(self.rules)
        self._validate()

    def _validate(self) -> None:
        if not self.rules:
            raise ValueError("Regelgruppe benoetigt mindestens eine Stufe")

        for rule in self.rules:
            if rule.entity_id != self.entity_id:
                raise ValueError("Alle Stufen einer Gruppe gehoeren zur selben Entity")
            if rule.kind is not ConditionKind.NUMERIC:
                raise ValueError("Regelgruppen sind nur fuer numerische Regeln vorgesehen")
            if rule.group_id != self.group_id:
                raise ValueError("Stufe verweist auf eine andere Gruppe")

        sources = {rule.value_source for rule in self.rules}
        if len(sources) > 1:
            raise ValueError("Alle Stufen einer Gruppe nutzen dieselbe Wertquelle")

        operators = {rule.operator for rule in self.rules}
        if len(operators) > 1:
            raise ValueError("Alle Stufen einer Gruppe nutzen denselben Operator")

        levels = [rule.level for rule in self.rules]
        if len(set(levels)) != len(levels):
            raise ValueError("Stufennummern muessen eindeutig sein")

        self._validate_monotonic()

    def _validate_monotonic(self) -> None:
        """Hoehere Stufen muessen strenger sein als niedrigere.

        Sonst waere eine hoehere Stufe erfuellt, ohne dass die niedrigere es
        ist, und die Eskalationslogik haette keine wohldefinierte Reihenfolge.
        """
        ordered = self.ordered_levels
        operator = ordered[0].operator
        assert operator is not None

        for lower, higher in pairwise(ordered):
            assert lower.threshold is not None and higher.threshold is not None
            if operator.is_upper_bound and higher.threshold <= lower.threshold:
                raise ValueError(
                    "Bei steigenden Schwellen muss jede hoehere Stufe eine groessere Schwelle haben"
                )
            if operator.is_lower_bound and higher.threshold >= lower.threshold:
                raise ValueError(
                    "Bei fallenden Schwellen muss jede hoehere Stufe eine kleinere Schwelle haben"
                )

    # -- Zugriff ---------------------------------------------------------

    @property
    def ordered_levels(self) -> tuple[Rule, ...]:
        """Stufen aufsteigend nach Stufennummer."""
        return tuple(sorted(self.rules, key=lambda rule: rule.level or 0))

    @property
    def value_source(self) -> ValueSource:
        return self.rules[0].value_source

    def rule_for_level(self, level: int) -> Rule | None:
        for rule in self.rules:
            if rule.level == level:
                return rule
        return None

    # -- Serialisierung --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "schema_version": self.schema_version,
            "entity_id": self.entity_id,
            "name": self.name,
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RuleGroup:
        return cls(
            group_id=data["group_id"],
            schema_version=data.get("schema_version", MODEL_SCHEMA_VERSION),
            entity_id=data["entity_id"],
            name=data["name"],
            rules=tuple(Rule.from_dict(item) for item in data.get("rules", ())),
        )


# ---------------------------------------------------------------------------
# Meldungstexte
# ---------------------------------------------------------------------------


def render_message(template: str, snapshot: EntitySnapshot, value: Any = None) -> str:
    """Ersetzt die unterstuetzten Platzhalter in einem Meldungstext.

    Bewusst kein Jinja: eine zweite Regelsprache im Regel-Editor waere fuer
    Anwender schwer zu durchschauen und im Fehlerfall schwer zu diagnostizieren.
    Unbekannte Platzhalter bleiben unveraendert stehen, damit ein Tippfehler
    sichtbar wird statt still zu verschwinden.
    """
    values: dict[str, str] = {
        "name": snapshot.display_name,
        "state": snapshot.state,
        "value": "" if value is None else str(value),
        "unit": snapshot.unit or "",
        "entity_id": snapshot.entity_id,
    }

    result = template
    for key in PLACEHOLDERS:
        result = result.replace("{" + key + "}", values[key])
    return result.strip()


def suggest_message(rule: Rule, snapshot: EntitySnapshot) -> str:
    """Erzeugt den Vorschlagstext beim Anlegen einer Regel.

    Der Text wird einmal beim Anlegen in ``message_template`` uebernommen und
    ist danach frei editierbar. Er wird nie nachtraeglich automatisch
    ueberschrieben.
    """
    name = snapshot.display_name
    if rule.kind is ConditionKind.NUMERIC:
        assert rule.operator is not None
        return f"{name} {_OPERATOR_TEXT[rule.operator]} {_format_number(rule.threshold)}".strip()

    zustaende = " oder ".join(rule.states)
    if rule.kind is ConditionKind.STATE_IS_NOT:
        return f"{name}: nicht {zustaende}"
    return f"{name}: {zustaende}"


_OPERATOR_TEXT: dict[NumericOperator, str] = {
    NumericOperator.GT: "ueber",
    NumericOperator.GTE: "ab",
    NumericOperator.LT: "unter",
    NumericOperator.LTE: "hoechstens",
    NumericOperator.EQ: "gleich",
}


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def rules_for_entity(rules: Sequence[Rule], entity_id: str) -> list[Rule]:
    """Alle Regeln einer Entity.

    Mehrere Regeln derselben Entity duerfen gleichzeitig erfuellt sein und
    erzeugen dann parallele Notifications. Nur innerhalb einer Regelgruppe
    gilt die Eskalationsregel, dass ausschliesslich die hoechste Stufe aktiv
    ist.
    """
    return [rule for rule in rules if rule.entity_id == entity_id]
