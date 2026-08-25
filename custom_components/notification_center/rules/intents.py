"""Uebersetzt Auswertungsergebnisse in Absichten fuer die Notification-Engine.

Zwischen "die Bedingung ist erfuellt" und "es entsteht eine Notification"
liegt eine Entscheidung, die nichts mit Home Assistant zu tun hat: welche
Notification beginnt, welche endet und mit welcher Begruendung. Diese Schicht
bleibt deshalb rein und testbar; ``engine.py`` fuehrt die Absichten nur aus.

Der wichtigste Fall ist die Eskalation: ein Stufenwechsel innerhalb einer
Regelgruppe erzeugt immer *beides*, das Ende der bisherigen und den Beginn der
neuen Stufe. Jede Stufe wird damit zu einem eigenen Ereignis im Log
(Spezifikation 20, 35).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from ..notifications.models import CloseReason
from .evaluator import Evaluation, GroupEvaluation
from .models import EntitySnapshot, Rule, RuleGroup, render_message, suggest_message


class IntentKind(StrEnum):
    """Was mit einer Notification geschehen soll."""

    START = "start"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class NotificationIntent:
    """Eine auszufuehrende Aenderung an einer Notification."""

    kind: IntentKind
    rule: Rule
    snapshot: EntitySnapshot
    #: Beginn der Bedingung. Bei Zeitbedingungen der Zeitpunkt, ab dem der
    #: Zustand anlag, nicht der Ablauf des Timers (Spezifikation 17).
    since: datetime | None = None
    value: Any = None
    reason: CloseReason | None = None
    level: int | None = None

    @property
    def rule_id(self) -> str:
        return self.rule.rule_id

    def message(self) -> str:
        """Der fertige Meldungstext.

        Faellt auf den Vorschlagstext zurueck, wenn die Regel keine eigene
        Vorlage traegt. So entsteht nie eine leere Notification, auch wenn eine
        Regel ueber die API ohne Text angelegt wurde.
        """
        vorlage = self.rule.message_template.strip()
        if not vorlage:
            return suggest_message(self.rule, self.snapshot)
        return render_message(vorlage, self.snapshot, self.value)


def intents_for_rule(
    rule: Rule,
    snapshot: EntitySnapshot,
    evaluation: Evaluation,
    *,
    stop_reason: CloseReason = CloseReason.CONDITION_CLEARED,
) -> list[NotificationIntent]:
    """Absichten einer einzelnen, gruppenlosen Regel."""
    if evaluation.became_satisfied:
        return [
            NotificationIntent(
                kind=IntentKind.START,
                rule=rule,
                snapshot=snapshot,
                since=evaluation.since,
                value=evaluation.value,
            )
        ]

    if evaluation.became_unsatisfied:
        return [
            NotificationIntent(
                kind=IntentKind.STOP,
                rule=rule,
                snapshot=snapshot,
                value=evaluation.value,
                reason=stop_reason,
            )
        ]

    return []


def intents_for_group(
    group: RuleGroup,
    snapshot: EntitySnapshot,
    evaluation: GroupEvaluation,
) -> list[NotificationIntent]:
    """Absichten einer Eskalationsgruppe.

    Bleibt die Stufe gleich, geschieht nichts: eine laufende Notification wird
    nicht bei jedem Messwert neu geschrieben.
    """
    if not evaluation.changed:
        return []

    absichten: list[NotificationIntent] = []

    if evaluation.previous_level is not None:
        alt = group.rule_for_level(evaluation.previous_level)
        if alt is not None:
            absichten.append(
                NotificationIntent(
                    kind=IntentKind.STOP,
                    rule=alt,
                    snapshot=snapshot,
                    level=evaluation.previous_level,
                    reason=_stop_reason(evaluation),
                    value=_value_for(evaluation, evaluation.previous_level),
                )
            )

    if evaluation.active_level is not None:
        neu = group.rule_for_level(evaluation.active_level)
        if neu is not None:
            stufe = evaluation.evaluations.get(evaluation.active_level)
            absichten.append(
                NotificationIntent(
                    kind=IntentKind.START,
                    rule=neu,
                    snapshot=snapshot,
                    level=evaluation.active_level,
                    since=stufe.since if stufe else None,
                    value=stufe.value if stufe else None,
                )
            )

    return absichten


def _stop_reason(evaluation: GroupEvaluation) -> CloseReason:
    if evaluation.escalated:
        return CloseReason.ESCALATED
    if evaluation.deescalated:
        return CloseReason.DEESCALATED
    return CloseReason.CONDITION_CLEARED


def _value_for(evaluation: GroupEvaluation, level: int) -> Any:
    stufe = evaluation.evaluations.get(level)
    return stufe.value if stufe else None
