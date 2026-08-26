"""Auswertung von Regeln und Regelgruppen.

Ohne Home-Assistant-Importe: die Auswertung bekommt Zustaende als
:class:`EntitySnapshot` hereingereicht und liefert Entscheidungen zurueck. Was
mit diesen Entscheidungen geschieht, entscheidet ``engine.py``.

Zwei Begriffe sind hier zu trennen:

*Ausloesen* ist die Frage, ob eine Bedingung neu greift. *Halten* ist die
Frage, ob sie weiterhin greift. Bei numerischen Regeln fallen beide durch die
Hysterese auseinander (Ausloesen ab 28 Grad, Halten bis 27 Grad); bei
"Zustand aendert sich zu" ebenfalls, weil dort nur der Wechsel in den
Zielzustand ausloest, das Verweilen darin die Notification aber am Leben
haelt.

Eine Regel kann intern erfuellt sein, ohne dass daraus eine sichtbare
Notification wird: innerhalb einer Regelgruppe zeigt nur die hoechste erfuellte
Stufe eine Notification (Spezifikation 20). Die uebrigen Stufen fuehren
trotzdem ihren eigenen Zustand mit, damit ihre Hysterese unabhaengig wirkt
(Spezifikation 21).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from .models import (
    ConditionKind,
    EntitySnapshot,
    NumericOperator,
    Rule,
    RuleGroup,
)

#: Zustaende, die keinen auswertbaren Wert tragen.
UNAVAILABLE_STATES = frozenset({"unknown", "unavailable", "none", ""})


class Phase(StrEnum):
    """Interner Zustand einer einzelnen Regel."""

    #: Bedingung nicht erfuellt.
    IDLE = "idle"
    #: Bedingung erfuellt, die Zeitbedingung laeuft noch.
    PENDING = "pending"
    #: Bedingung erfuellt und Zeitbedingung abgelaufen.
    SATISFIED = "satisfied"


@dataclass(slots=True)
class RuleState:
    """Mitgefuehrter Zustand einer Regel zwischen zwei Auswertungen."""

    rule_id: str
    phase: Phase = Phase.IDLE
    #: Seit wann die Bedingung ununterbrochen erfuellt ist.
    condition_since: datetime | None = None
    #: Wann die Regel zuletzt in ``SATISFIED`` gewechselt ist.
    satisfied_at: datetime | None = None
    #: Letzter gesehener Zustandswert, fuer die Flankenerkennung.
    last_state: str | None = None

    @property
    def is_satisfied(self) -> bool:
        return self.phase is Phase.SATISFIED


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Ergebnis einer einzelnen Regelauswertung."""

    rule_id: str
    phase: Phase
    #: Die Regel ist neu erfuellt.
    became_satisfied: bool = False
    #: Die Regel ist nicht mehr erfuellt.
    became_unsatisfied: bool = False
    #: Zeitpunkt, zu dem erneut ausgewertet werden muss (Zeitbedingung oder
    #: automatische Enddauer). ``None`` bedeutet: nur bei Zustandsaenderungen.
    fire_at: datetime | None = None
    #: Der ausgewertete Wert, fuer den Meldungstext.
    value: Any = None
    #: Beginn der Bedingung. Bei Zeitbedingungen der Zeitpunkt, ab dem der
    #: Zustand anlag, nicht der Ablauf des Timers.
    since: datetime | None = None


# ---------------------------------------------------------------------------
# Wertaufbereitung
# ---------------------------------------------------------------------------


def coerce_number(value: Any) -> float | None:
    """Wandelt einen Roh- oder Zustandswert in eine Zahl.

    Nicht auswertbare Werte (``unknown``, ``unavailable``, Texte, ``None``)
    ergeben ``None`` und lassen jede numerische Bedingung als nicht erfuellt
    gelten. Eine kurzzeitig nicht verfuegbare Entity beendet damit eine
    laufende Notification, statt einen alten Wert weiterzuschleppen.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in UNAVAILABLE_STATES:
            return None
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return None
    return None


def _compare(operator: NumericOperator, value: float, threshold: float) -> bool:
    match operator:
        case NumericOperator.GT:
            return value > threshold
        case NumericOperator.GTE:
            return value >= threshold
        case NumericOperator.LT:
            return value < threshold
        case NumericOperator.LTE:
            return value <= threshold
        case NumericOperator.EQ:
            return value == threshold


# ---------------------------------------------------------------------------
# Bedingungen
# ---------------------------------------------------------------------------


def evaluate_value(rule: Rule, snapshot: EntitySnapshot) -> Any:
    """Der Wert, den die Regel betrachtet: Zustand oder Attribut."""
    return rule.value_source.extract(snapshot)


def trigger_met(rule: Rule, snapshot: EntitySnapshot, previous_state: str | None) -> bool:
    """Greift die Bedingung neu?"""
    raw = evaluate_value(rule, snapshot)

    if rule.kind is ConditionKind.NUMERIC:
        number = coerce_number(raw)
        if number is None:
            return False
        assert rule.operator is not None and rule.threshold is not None
        return _compare(rule.operator, number, rule.threshold)

    if raw is None or str(raw).lower() in UNAVAILABLE_STATES:
        return False

    im_zielzustand = str(raw) in rule.states
    if rule.kind is ConditionKind.STATE_IS:
        return im_zielzustand
    if rule.kind is ConditionKind.STATE_IS_NOT:
        return not im_zielzustand

    # STATE_CHANGED_TO: nur der Wechsel *in* den Zielzustand loest aus. Lag der
    # Zustand schon vorher an, ist das kein neues Ereignis.
    if previous_state is None:
        return False
    return im_zielzustand and str(previous_state) not in rule.states


def hold_met(rule: Rule, snapshot: EntitySnapshot) -> bool:
    """Greift die Bedingung weiterhin?

    Bei numerischen Regeln mit Hysterese gilt hier die Rueckkehrschwelle: die
    Notification bleibt bestehen, bis der Wert sie wieder passiert
    (Spezifikation 18).
    """
    raw = evaluate_value(rule, snapshot)

    if rule.kind is ConditionKind.NUMERIC:
        number = coerce_number(raw)
        if number is None:
            return False
        assert rule.operator is not None and rule.threshold is not None
        schwelle = rule.release_threshold if rule.release_threshold is not None else rule.threshold
        return _compare(rule.operator, number, schwelle)

    if raw is None or str(raw).lower() in UNAVAILABLE_STATES:
        return False

    if rule.kind is ConditionKind.STATE_IS_NOT:
        return str(raw) not in rule.states

    # Auch "Zustand aendert sich zu" bleibt bestehen, solange der Zielzustand
    # anliegt, und endet beim Verlassen.
    return str(raw) in rule.states


# ---------------------------------------------------------------------------
# Einzelne Regel
# ---------------------------------------------------------------------------


def evaluate_rule(
    rule: Rule,
    snapshot: EntitySnapshot,
    state: RuleState,
    now: datetime,
) -> Evaluation:
    """Wertet eine Regel aus und schreibt ``state`` fort.

    ``state`` wird an Ort und Stelle veraendert; das Ergebnis beschreibt, was
    sich dadurch geaendert hat.
    """
    previous_state = state.last_state
    war_erfuellt = state.is_satisfied

    if not rule.enabled:
        state.last_state = snapshot.state
        return _reset(state, war_erfuellt, rule.rule_id)

    weiterhin = hold_met(rule, snapshot)
    neu = trigger_met(rule, snapshot, previous_state)
    state.last_state = snapshot.state

    aktiv_gueltig = weiterhin if state.phase is not Phase.IDLE else neu

    if not aktiv_gueltig:
        return _reset(state, war_erfuellt, rule.rule_id)

    if state.condition_since is None:
        state.condition_since = now

    wert = evaluate_value(rule, snapshot)

    # Zeitbedingung (Spezifikation 17): die Bedingung muss ununterbrochen
    # anliegen, bevor eine Notification entsteht.
    if rule.duration_seconds:
        faellig = state.condition_since + timedelta(seconds=rule.duration_seconds)
        if now < faellig:
            state.phase = Phase.PENDING
            state.satisfied_at = None
            return Evaluation(
                rule_id=rule.rule_id,
                phase=Phase.PENDING,
                became_unsatisfied=war_erfuellt,
                fire_at=faellig,
                value=wert,
                since=state.condition_since,
            )

    if not war_erfuellt:
        state.satisfied_at = now
    state.phase = Phase.SATISFIED

    # Automatische Enddauer (nur bei "Zustand aendert sich zu"): beendet die
    # Notification, obwohl der Zustand noch anliegt.
    fire_at = None
    if rule.auto_end_seconds and state.satisfied_at is not None:
        ablauf = state.satisfied_at + timedelta(seconds=rule.auto_end_seconds)
        if now >= ablauf:
            # Der Zustand liegt weiter an, die Notification endet trotzdem.
            # Ein erneutes Ausloesen setzt einen echten Zustandswechsel
            # voraus, weshalb sie nicht sofort wieder entsteht.
            return _reset(state, war_erfuellt, rule.rule_id)
        fire_at = ablauf

    return Evaluation(
        rule_id=rule.rule_id,
        phase=Phase.SATISFIED,
        became_satisfied=not war_erfuellt,
        fire_at=fire_at,
        value=wert,
        since=state.condition_since,
    )


def _reset(state: RuleState, war_erfuellt: bool, rule_id: str) -> Evaluation:
    """Setzt die Regel zurueck; ein laufender Timer verfaellt dabei.

    ``last_state`` bleibt erhalten: die Flankenerkennung von
    "Zustand aendert sich zu" braucht den zuletzt gesehenen Wert.
    """
    state.phase = Phase.IDLE
    state.condition_since = None
    state.satisfied_at = None
    return Evaluation(
        rule_id=rule_id,
        phase=Phase.IDLE,
        became_unsatisfied=war_erfuellt,
    )


# ---------------------------------------------------------------------------
# Regelgruppe
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GroupEvaluation:
    """Ergebnis der Auswertung einer Eskalationsgruppe."""

    group_id: str
    #: Stufe, die sichtbar sein soll. ``None`` bedeutet keine Notification.
    active_level: int | None
    #: Stufe, die zuvor sichtbar war.
    previous_level: int | None
    #: Auswertung je Stufe, nach Stufennummer.
    evaluations: dict[int, Evaluation] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.active_level != self.previous_level

    @property
    def escalated(self) -> bool:
        if self.active_level is None:
            return False
        return self.previous_level is None or self.active_level > self.previous_level

    @property
    def deescalated(self) -> bool:
        if self.previous_level is None:
            return False
        return self.active_level is not None and self.active_level < self.previous_level

    @property
    def cleared(self) -> bool:
        return self.previous_level is not None and self.active_level is None


@dataclass(slots=True)
class GroupState:
    """Mitgefuehrter Zustand einer Regelgruppe."""

    group_id: str
    active_level: int | None = None
    rule_states: dict[str, RuleState] = field(default_factory=dict)

    def state_for(self, rule: Rule) -> RuleState:
        return self.rule_states.setdefault(rule.rule_id, RuleState(rule_id=rule.rule_id))


def evaluate_group(
    group: RuleGroup,
    snapshot: EntitySnapshot,
    state: GroupState,
    now: datetime,
) -> GroupEvaluation:
    """Wertet alle Stufen aus und bestimmt die hoechste gueltige.

    Jede Stufe fuehrt ihren eigenen Zustand mit, auch wenn sie gerade nicht
    sichtbar ist. Nur so wirkt die Hysterese einer Stufe unabhaengig von den
    anderen (Spezifikation 21).
    """
    auswertungen: dict[int, Evaluation] = {}
    erfuellte: list[int] = []

    for rule in group.ordered_levels:
        assert rule.level is not None
        ergebnis = evaluate_rule(rule, snapshot, state.state_for(rule), now)
        auswertungen[rule.level] = ergebnis
        if ergebnis.phase is Phase.SATISFIED:
            erfuellte.append(rule.level)

    zuvor = state.active_level
    neu = max(erfuellte) if erfuellte else None
    state.active_level = neu

    return GroupEvaluation(
        group_id=group.group_id,
        active_level=neu,
        previous_level=zuvor,
        evaluations=auswertungen,
    )
