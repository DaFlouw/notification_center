"""Vorschlaege fuer Regeln einer Entity.

Ohne Home-Assistant-Importe: Metadaten und Historienprofil kommen fertig
herein, heraus kommen Vorschlaege mit Begruendung und Sicherheitsbewertung.

Leitgedanke aus Spezifikation 10: **Metadaten wiegen schwerer als Namen.**
``device_class=temperature`` mit Einheit Grad Celsius ist eine belastbare
Aussage; das Wort "Temperatur" im Namen ist nur ein Hinweis. Namensheuristik
kommt deshalb nur zum Zug, wenn Metadaten fehlen, und fuehrt dann zu einem
Vorschlag geringer Sicherheit.

Reicht die Grundlage nicht, entsteht bewusst *kein* Vorschlag
(Spezifikation 12). Eine eigene Regel bleibt trotzdem jederzeit moeglich
(Spezifikation 79).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..notifications.models import NotificationType
from ..rules.models import ConditionKind, NumericOperator
from .analyzer import (
    NumericProfile,
    StateProfile,
    suggest_hysteresis,
    suggest_lower_threshold,
    suggest_upper_threshold,
)
from .texte import GRUNDSPRACHE, text, zahl


class Confidence(StrEnum):
    """Wie belastbar ein Vorschlag ist (Spezifikation 12)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def is_uncertain(self) -> bool:
        """Vorschlaege geringer Sicherheit werden in der Oberflaeche markiert."""
        return self is Confidence.LOW


#: Domaenen, deren Zustand immer eine Zahl ist, auch ohne Einheit und ohne
#: ``state_class``. Ohne diese Liste bekaemen ein Zahlenhelfer und ein Zaehler
#: Zustandsvorschlaege angeboten -- "Zustand ist 42" statt einer Schwelle.
_NUMERIC_DOMAINS = frozenset({"input_number", "counter"})


@dataclass(frozen=True, slots=True)
class EntityMetadata:
    """Was ueber eine Entity bekannt ist, bevor die Historie befragt wird."""

    entity_id: str
    domain: str
    state: str | None = None
    name: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    unit: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)
    device_id: str | None = None
    area_id: str | None = None

    @property
    def display_name(self) -> str:
        return self.name or self.entity_id

    @property
    def is_numeric(self) -> bool:
        """Numerisch ist, was eine Einheit oder eine state_class traegt.

        Dazu die Domaenen, die von sich aus nur Zahlen kennen und deshalb
        beides nicht brauchen.
        """
        if self.domain in _NUMERIC_DOMAINS:
            return True
        return self.domain == "sensor" and bool(self.unit or self.state_class)


@dataclass(frozen=True, slots=True)
class Reason:
    """Ein Baustein der aufklappbaren Begruendung (Spezifikation 13)."""

    label: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "value": self.value}


@dataclass(frozen=True, slots=True)
class Suggestion:
    """Ein Regelvorschlag samt Begruendung.

    ``title`` ist die eigentliche Empfehlung und wird allein angezeigt; die
    ``reasons`` liegen darunter und werden erst auf Wunsch aufgeklappt.
    """

    key: str
    title: str
    confidence: Confidence
    kind: ConditionKind
    type: NotificationType
    reasons: tuple[Reason, ...] = ()

    states: tuple[str, ...] = ()
    operator: NumericOperator | None = None
    threshold: float | None = None
    release_threshold: float | None = None
    duration_seconds: float | None = None
    message_template: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "confidence": str(self.confidence),
            "uncertain": self.confidence.is_uncertain,
            "kind": str(self.kind),
            "type": str(self.type),
            "states": list(self.states),
            "operator": str(self.operator) if self.operator else None,
            "threshold": self.threshold,
            "release_threshold": self.release_threshold,
            "duration_seconds": self.duration_seconds,
            "message_template": self.message_template,
            "reasons": [reason.to_dict() for reason in self.reasons],
        }


# ---------------------------------------------------------------------------
# Katalog nach device_class
# ---------------------------------------------------------------------------

#: Binaersensoren, deren aktiver Zustand fuer sich genommen ein Alarm ist.
#: Die Beschriftung steht unter ``class.<kennung>`` in texte.py.
_ALARM_CLASSES = frozenset({"smoke", "gas", "carbon_monoxide", "moisture", "safety"})

#: Binaersensoren, deren aktiver Zustand eine Warnung wert ist.
_WARNING_CLASSES = frozenset({"problem", "battery", "tamper"})

#: Oeffnungen: erst nach einer Weile meldenswert, sonst nervt jede Tuer.
_OPENING_CLASSES = frozenset({"door", "window", "garage_door", "opening"})

#: Fuer diese Messgroessen gibt es allgemein anerkannte Schwellen, die
#: unabhaengig von der Historie gelten.
#: Die Beschreibung steht unter ``absolute.<kennung>`` in texte.py.
_ABSOLUTE_THRESHOLDS: dict[str, tuple[NumericOperator, float, NotificationType]] = {
    "battery": (NumericOperator.LT, 20.0, NotificationType.WARNING),
    "carbon_dioxide": (NumericOperator.GT, 1200.0, NotificationType.WARNING),
    "humidity": (NumericOperator.GT, 65.0, NotificationType.WARNING),
}

#: Nur als letzter Ausweg, wenn keine Metadaten vorliegen.
_NAME_HINTS = {
    "temperatur": "temperature",
    "temperature": "temperature",
    "feuchte": "humidity",
    "humidity": "humidity",
    "batterie": "battery",
    "battery": "battery",
    "fenster": "window",
    "window": "window",
    "tuer": "door",
    "tür": "door",
    "door": "door",
    "rauch": "smoke",
    "smoke": "smoke",
    "leck": "moisture",
    "wasser": "moisture",
}

#: Vorgabe fuer Oeffnungen: 15 Minuten, wie im Beispiel der Spezifikation.
DEFAULT_OPENING_DURATION = 900.0

#: Domaenen, deren Zustandsraum aus genau zwei Werten besteht.
#:
#: Fuer sie laesst sich immer eine gueltige Regel bilden, auch ohne
#: device_class: dass die Entity an oder aus sein kann, steht fest. Ob es
#: meldenswert ist, weiss nur der Anwender, deshalb mittlere Sicherheit.
_ON_OFF_DOMAINS = frozenset({"binary_sensor", "switch", "input_boolean"})


def build_suggestions(
    metadata: EntityMetadata,
    *,
    numeric_profile: NumericProfile | None = None,
    state_profile: StateProfile | None = None,
    analysis_days: int = 7,
    sprache: str = GRUNDSPRACHE,
) -> list[Suggestion]:
    """Erzeugt alle Vorschlaege fuer eine Entity, beste Sicherheit zuerst.

    ``sprache`` bestimmt Titel, Begruendung und Meldungsvorlage. Die Vorlage
    wird beim Uebernehmen zur Regel und bleibt dann stehen, wie sie war.
    """
    device_class = metadata.device_class
    aus_namen = False

    if device_class is None:
        device_class = _guess_from_name(metadata)
        aus_namen = device_class is not None

    vorschlaege: list[Suggestion] = []

    if metadata.domain in _ON_OFF_DOMAINS:
        vorschlaege.extend(_binary_suggestions(metadata, device_class, aus_namen, sprache))
        vorschlaege.extend(_on_off_suggestions(metadata, sprache))
    elif metadata.is_numeric or (aus_namen and device_class in _ABSOLUTE_THRESHOLDS):
        vorschlaege.extend(
            _numeric_suggestions(
                metadata, device_class, aus_namen, numeric_profile, analysis_days, sprache
            )
        )
    else:
        vorschlaege.extend(_state_suggestions(metadata, state_profile, analysis_days, sprache))

    return sorted(vorschlaege, key=lambda v: _RANG[v.confidence])


_RANG = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}


# ---------------------------------------------------------------------------
# Binaersensoren
# ---------------------------------------------------------------------------


def _binary_suggestions(
    metadata: EntityMetadata, device_class: str | None, aus_namen: bool, sprache: str
) -> list[Suggestion]:
    if device_class in _ALARM_CLASSES:
        return [
            _zustandsvorschlag(
                metadata,
                device_class,
                aus_namen,
                sprache,
                titel=text(sprache, "title.alarm", text=text(sprache, f"class.{device_class}")),
                typ=NotificationType.ALARM,
            )
        ]

    if device_class in _WARNING_CLASSES:
        return [
            _zustandsvorschlag(
                metadata,
                device_class,
                aus_namen,
                sprache,
                titel=text(sprache, "title.warning", text=text(sprache, f"class.{device_class}")),
                typ=NotificationType.WARNING,
            )
        ]

    if device_class in _OPENING_CLASSES:
        return [
            _zustandsvorschlag(
                metadata,
                device_class,
                aus_namen,
                sprache,
                titel=text(
                    sprache,
                    "title.openingOpen",
                    thing=text(sprache, f"opening.{device_class}"),
                    minutes=int(DEFAULT_OPENING_DURATION / 60),
                ),
                typ=NotificationType.WARNING,
                dauer=DEFAULT_OPENING_DURATION,
            )
        ]

    return []


def _on_off_suggestions(metadata: EntityMetadata, sprache: str) -> list[Suggestion]:
    """Die immer gueltigen Vorschlaege fuer an und aus.

    Ohne sie stehen Anwender bei einem Schalter oder einem Binaersensor ohne
    Geraeteklasse vor einer leeren Liste, obwohl die beiden sinnvollen Regeln
    auf der Hand liegen.
    """
    name = metadata.display_name

    return [
        Suggestion(
            key=f"on_off_{zustand}",
            title=text(sprache, "title.onOff", name=name, state=beschriftung),
            confidence=Confidence.MEDIUM,
            kind=ConditionKind.STATE_IS,
            type=NotificationType.INFO,
            states=(zustand,),
            message_template=f"{{name}}: {beschriftung}",
            reasons=(
                Reason(text(sprache, "reason.domain"), metadata.domain),
                Reason(text(sprache, "reason.basis"), text(sprache, "reason.fixedStates")),
            ),
        )
        for zustand, beschriftung in (
            ("on", text(sprache, "state.on")),
            ("off", text(sprache, "state.off")),
        )
    ]


def _zustandsvorschlag(
    metadata: EntityMetadata,
    device_class: str | None,
    aus_namen: bool,
    sprache: str,
    *,
    titel: str,
    typ: NotificationType,
    dauer: float | None = None,
) -> Suggestion:
    begruendung = [_geraeteklasse(sprache, device_class)]
    if aus_namen:
        begruendung.append(_namenshinweis(sprache, metadata))
    if dauer:
        begruendung.append(
            Reason(
                text(sprache, "reason.duration"),
                text(sprache, "reason.minutes", minutes=int(dauer / 60)),
            )
        )

    return Suggestion(
        key=f"{device_class}_state",
        title=titel,
        confidence=Confidence.LOW if aus_namen else Confidence.HIGH,
        kind=ConditionKind.STATE_IS,
        type=typ,
        states=("on",),
        duration_seconds=dauer,
        message_template="{name}",
        reasons=tuple(begruendung),
    )


# ---------------------------------------------------------------------------
# Numerische Sensoren
# ---------------------------------------------------------------------------


def _numeric_suggestions(
    metadata: EntityMetadata,
    device_class: str | None,
    aus_namen: bool,
    profile: NumericProfile | None,
    analysis_days: int,
    sprache: str,
) -> list[Suggestion]:
    vorschlaege: list[Suggestion] = []
    einheit = f" {metadata.unit}" if metadata.unit else ""

    # 1. Anerkannte absolute Schwellen haben Vorrang: sie gelten unabhaengig
    #    davon, was die letzten Tage gezeigt haben.
    if device_class in _ABSOLUTE_THRESHOLDS:
        operator, schwelle, typ = _ABSOLUTE_THRESHOLDS[device_class]
        begruendung = [
            _geraeteklasse(sprache, device_class),
            Reason(text(sprache, "reason.basis"), text(sprache, "reason.commonThreshold")),
        ]
        if aus_namen:
            begruendung.append(_namenshinweis(sprache, metadata))
        vorschlaege.append(
            Suggestion(
                key=f"{device_class}_absolute",
                title=text(
                    sprache,
                    "title.absolute",
                    text=text(sprache, f"absolute.{device_class}"),
                ),
                confidence=Confidence.LOW if aus_namen else Confidence.HIGH,
                kind=ConditionKind.NUMERIC,
                type=typ,
                operator=operator,
                threshold=schwelle,
                message_template="{name}: {value}" + einheit,
                reasons=tuple(begruendung),
            )
        )

    # 2. Aus der Historie abgeleitete Schwelle.
    if profile is not None and not profile.is_constant:
        obere = suggest_upper_threshold(profile)
        if obere is not None:
            hysterese = suggest_hysteresis(obere, profile, upper=True)
            vorschlaege.append(
                Suggestion(
                    key=f"{device_class or 'wert'}_upper",
                    title=text(
                        sprache,
                        "title.above",
                        label=_beschriftung(metadata, sprache),
                        value=zahl(sprache, obere),
                        unit=einheit,
                    ),
                    confidence=_history_confidence(metadata, device_class, aus_namen),
                    kind=ConditionKind.NUMERIC,
                    type=NotificationType.WARNING,
                    operator=NumericOperator.GT,
                    threshold=obere,
                    release_threshold=hysterese,
                    message_template="{name}: {value}" + einheit,
                    reasons=(
                        _geraeteklasse(sprache, device_class),
                        _historie(sprache, analysis_days),
                        _bereich(sprache, profile, einheit),
                        Reason(
                            text(sprache, "reason.suggestedThreshold"),
                            f"{zahl(sprache, obere)}{einheit}",
                        ),
                        Reason(
                            text(sprache, "reason.returnBelow"),
                            f"{zahl(sprache, hysterese)}{einheit}",
                        ),
                    ),
                )
            )

        untere = suggest_lower_threshold(profile)
        if untere is not None and device_class in {"temperature", "humidity"}:
            vorschlaege.append(
                Suggestion(
                    key=f"{device_class}_lower",
                    title=text(
                        sprache,
                        "title.below",
                        label=_beschriftung(metadata, sprache),
                        value=zahl(sprache, untere),
                        unit=einheit,
                    ),
                    confidence=_history_confidence(metadata, device_class, aus_namen),
                    kind=ConditionKind.NUMERIC,
                    type=NotificationType.WARNING,
                    operator=NumericOperator.LT,
                    threshold=untere,
                    release_threshold=suggest_hysteresis(untere, profile, upper=False),
                    message_template="{name}: {value}" + einheit,
                    reasons=(
                        _geraeteklasse(sprache, device_class),
                        _historie(sprache, analysis_days),
                        _bereich(sprache, profile, einheit),
                    ),
                )
            )

    return vorschlaege


def _history_confidence(
    metadata: EntityMetadata, device_class: str | None, aus_namen: bool
) -> Confidence:
    """Eine Schwelle aus der Historie ist nur so gut wie ihre Metadaten."""
    if aus_namen or device_class is None:
        return Confidence.LOW
    if metadata.unit:
        return Confidence.HIGH
    return Confidence.MEDIUM


# ---------------------------------------------------------------------------
# Uebrige Entities
# ---------------------------------------------------------------------------


def _state_suggestions(
    metadata: EntityMetadata, profile: StateProfile | None, analysis_days: int, sprache: str
) -> list[Suggestion]:
    """Vorschlag aus beobachteten Zustaenden, etwa fuer Geraetestatus.

    Ohne Metadaten laesst sich nicht sagen, welcher Zustand meldenswert ist.
    Angeboten wird deshalb nur der seltenste beobachtete Zustand, und das mit
    geringer Sicherheit: das Ungewoehnliche ist eher meldenswert als das
    Uebliche.
    """
    if profile is None or len(profile.distinct_states) < 2:
        return []

    seltenster = profile.distinct_states[-1]
    anteil = profile.share(seltenster)
    if anteil > 0.25:
        # Kein Zustand sticht heraus.
        return []

    return [
        Suggestion(
            key="rare_state",
            title=text(sprache, "title.rareState", state=seltenster),
            confidence=Confidence.LOW,
            kind=ConditionKind.STATE_IS,
            type=NotificationType.INFO,
            states=(seltenster,),
            message_template="{name}: {state}",
            reasons=(
                _historie(sprache, analysis_days),
                Reason(text(sprache, "reason.observedStates"), ", ".join(profile.distinct_states)),
                Reason(
                    text(sprache, "reason.share"),
                    text(
                        sprache,
                        "reason.shareValue",
                        state=seltenster,
                        percent=f"{anteil * 100:.0f}",
                    ),
                ),
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Hilfsmittel
# ---------------------------------------------------------------------------


def _guess_from_name(metadata: EntityMetadata) -> str | None:
    """Letzter Ausweg, wenn keine Metadaten vorliegen."""
    text = f"{metadata.entity_id} {metadata.name or ''}".lower()
    for hinweis, device_class in _NAME_HINTS.items():
        if hinweis in text:
            return device_class
    return None


def _beschriftung(metadata: EntityMetadata, sprache: str) -> str:
    return metadata.device_class or text(sprache, "label.value")


def _geraeteklasse(sprache: str, device_class: str | None) -> Reason:
    return Reason(
        text(sprache, "reason.deviceClass"), device_class or text(sprache, "reason.unknown")
    )


def _namenshinweis(sprache: str, metadata: EntityMetadata) -> Reason:
    return Reason(
        text(sprache, "reason.hint"),
        text(sprache, "reason.fromName", name=metadata.display_name),
    )


def _historie(sprache: str, analysis_days: int) -> Reason:
    return Reason(
        text(sprache, "reason.history"), text(sprache, "reason.lastDays", days=analysis_days)
    )


def _bereich(sprache: str, profile: NumericProfile, einheit: str) -> Reason:
    return Reason(
        text(sprache, "reason.typicalRange"),
        text(
            sprache,
            "reason.range",
            low=zahl(sprache, profile.p05),
            high=zahl(sprache, profile.p95),
            unit=einheit,
        ),
    )


def suggestions_to_list(suggestions: Sequence[Suggestion]) -> list[dict[str, Any]]:
    return [vorschlag.to_dict() for vorschlag in suggestions]
