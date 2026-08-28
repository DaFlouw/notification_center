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
_ALARM_CLASSES = {
    "smoke": "Rauch erkannt",
    "gas": "Gas erkannt",
    "carbon_monoxide": "Kohlenmonoxid erkannt",
    "moisture": "Feuchtigkeit erkannt",
    "safety": "Sicherheitsmeldung",
}

#: Binaersensoren, deren aktiver Zustand eine Warnung wert ist.
_WARNING_CLASSES = {
    "problem": "Stoerung gemeldet",
    "battery": "Batterie schwach",
    "tamper": "Manipulation erkannt",
}

#: Oeffnungen: erst nach einer Weile meldenswert, sonst nervt jede Tuer.
_OPENING_CLASSES = {
    "door": "Tuer",
    "window": "Fenster",
    "garage_door": "Garagentor",
    "opening": "Oeffnung",
}

#: Fuer diese Messgroessen gibt es allgemein anerkannte Schwellen, die
#: unabhaengig von der Historie gelten.
_ABSOLUTE_THRESHOLDS: dict[str, tuple[NumericOperator, float, NotificationType, str]] = {
    "battery": (NumericOperator.LT, 20.0, NotificationType.WARNING, "Batterie unter 20 %"),
    "carbon_dioxide": (
        NumericOperator.GT,
        1200.0,
        NotificationType.WARNING,
        "CO2 ueber 1200 ppm",
    ),
    "humidity": (NumericOperator.GT, 65.0, NotificationType.WARNING, "Luftfeuchte ueber 65 %"),
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
) -> list[Suggestion]:
    """Erzeugt alle Vorschlaege fuer eine Entity, beste Sicherheit zuerst."""
    device_class = metadata.device_class
    aus_namen = False

    if device_class is None:
        device_class = _guess_from_name(metadata)
        aus_namen = device_class is not None

    vorschlaege: list[Suggestion] = []

    if metadata.domain in _ON_OFF_DOMAINS:
        vorschlaege.extend(_binary_suggestions(metadata, device_class, aus_namen))
        vorschlaege.extend(_on_off_suggestions(metadata))
    elif metadata.is_numeric or (aus_namen and device_class in _ABSOLUTE_THRESHOLDS):
        vorschlaege.extend(
            _numeric_suggestions(metadata, device_class, aus_namen, numeric_profile, analysis_days)
        )
    else:
        vorschlaege.extend(_state_suggestions(metadata, state_profile, analysis_days))

    return sorted(vorschlaege, key=lambda v: _RANG[v.confidence])


_RANG = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}


# ---------------------------------------------------------------------------
# Binaersensoren
# ---------------------------------------------------------------------------


def _binary_suggestions(
    metadata: EntityMetadata, device_class: str | None, aus_namen: bool
) -> list[Suggestion]:
    if device_class in _ALARM_CLASSES:
        return [
            _zustandsvorschlag(
                metadata,
                device_class,
                aus_namen,
                titel=f"Alarm bei {_ALARM_CLASSES[device_class]}",
                typ=NotificationType.ALARM,
            )
        ]

    if device_class in _WARNING_CLASSES:
        return [
            _zustandsvorschlag(
                metadata,
                device_class,
                aus_namen,
                titel=f"Warnung bei {_WARNING_CLASSES[device_class]}",
                typ=NotificationType.WARNING,
            )
        ]

    if device_class in _OPENING_CLASSES:
        bezeichnung = _OPENING_CLASSES[device_class]
        return [
            _zustandsvorschlag(
                metadata,
                device_class,
                aus_namen,
                titel=f"Warnung, wenn {bezeichnung} laenger als 15 Minuten offen ist",
                typ=NotificationType.WARNING,
                dauer=DEFAULT_OPENING_DURATION,
            )
        ]

    return []


def _on_off_suggestions(metadata: EntityMetadata) -> list[Suggestion]:
    """Die immer gueltigen Vorschlaege fuer an und aus.

    Ohne sie stehen Anwender bei einem Schalter oder einem Binaersensor ohne
    Geraeteklasse vor einer leeren Liste, obwohl die beiden sinnvollen Regeln
    auf der Hand liegen.
    """
    name = metadata.display_name

    return [
        Suggestion(
            key=f"on_off_{zustand}",
            title=f"Information, wenn {name} {beschriftung} ist",
            confidence=Confidence.MEDIUM,
            kind=ConditionKind.STATE_IS,
            type=NotificationType.INFO,
            states=(zustand,),
            message_template=f"{{name}}: {beschriftung}",
            reasons=(
                Reason("Domaene", metadata.domain),
                Reason("Grundlage", "der Zustandsraum dieser Domaene steht fest"),
            ),
        )
        for zustand, beschriftung in (("on", "an"), ("off", "aus"))
    ]


def _zustandsvorschlag(
    metadata: EntityMetadata,
    device_class: str | None,
    aus_namen: bool,
    *,
    titel: str,
    typ: NotificationType,
    dauer: float | None = None,
) -> Suggestion:
    begruendung = [Reason("Geraeteklasse", device_class or "unbekannt")]
    if aus_namen:
        begruendung.append(Reason("Hinweis", f"aus dem Namen '{metadata.display_name}'"))
    if dauer:
        begruendung.append(Reason("Zeitbedingung", f"{int(dauer / 60)} Minuten ununterbrochen"))

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
) -> list[Suggestion]:
    vorschlaege: list[Suggestion] = []
    einheit = f" {metadata.unit}" if metadata.unit else ""

    # 1. Anerkannte absolute Schwellen haben Vorrang: sie gelten unabhaengig
    #    davon, was die letzten Tage gezeigt haben.
    if device_class in _ABSOLUTE_THRESHOLDS:
        operator, schwelle, typ, beschreibung = _ABSOLUTE_THRESHOLDS[device_class]
        begruendung = [
            Reason("Geraeteklasse", device_class or "unbekannt"),
            Reason("Grundlage", "allgemein uebliche Schwelle"),
        ]
        if aus_namen:
            begruendung.append(Reason("Hinweis", f"aus dem Namen '{metadata.display_name}'"))
        vorschlaege.append(
            Suggestion(
                key=f"{device_class}_absolute",
                title=f"Warnung bei {beschreibung}",
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
                    title=(f"Warnung bei {_beschriftung(metadata)} ueber {_zahl(obere)}{einheit}"),
                    confidence=_history_confidence(metadata, device_class, aus_namen),
                    kind=ConditionKind.NUMERIC,
                    type=NotificationType.WARNING,
                    operator=NumericOperator.GT,
                    threshold=obere,
                    release_threshold=hysterese,
                    message_template="{name}: {value}" + einheit,
                    reasons=(
                        Reason("Geraeteklasse", device_class or "unbekannt"),
                        Reason("Historie", f"letzte {analysis_days} Tage"),
                        Reason(
                            "typischer Bereich",
                            f"{_zahl(profile.p05)} bis {_zahl(profile.p95)}{einheit}",
                        ),
                        Reason("vorgeschlagene Schwelle", f"{_zahl(obere)}{einheit}"),
                        Reason("Rueckkehr unter", f"{_zahl(hysterese)}{einheit}"),
                    ),
                )
            )

        untere = suggest_lower_threshold(profile)
        if untere is not None and device_class in {"temperature", "humidity"}:
            vorschlaege.append(
                Suggestion(
                    key=f"{device_class}_lower",
                    title=(f"Warnung bei {_beschriftung(metadata)} unter {_zahl(untere)}{einheit}"),
                    confidence=_history_confidence(metadata, device_class, aus_namen),
                    kind=ConditionKind.NUMERIC,
                    type=NotificationType.WARNING,
                    operator=NumericOperator.LT,
                    threshold=untere,
                    release_threshold=suggest_hysteresis(untere, profile, upper=False),
                    message_template="{name}: {value}" + einheit,
                    reasons=(
                        Reason("Geraeteklasse", device_class or "unbekannt"),
                        Reason("Historie", f"letzte {analysis_days} Tage"),
                        Reason(
                            "typischer Bereich",
                            f"{_zahl(profile.p05)} bis {_zahl(profile.p95)}{einheit}",
                        ),
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
    metadata: EntityMetadata, profile: StateProfile | None, analysis_days: int
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
            title=f"Information, wenn der Zustand '{seltenster}' eintritt",
            confidence=Confidence.LOW,
            kind=ConditionKind.STATE_IS,
            type=NotificationType.INFO,
            states=(seltenster,),
            message_template="{name}: {state}",
            reasons=(
                Reason("Historie", f"letzte {analysis_days} Tage"),
                Reason("beobachtete Zustaende", ", ".join(profile.distinct_states)),
                Reason("Anteil", f"{seltenster} in {anteil * 100:.0f} % der Faelle"),
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


def _beschriftung(metadata: EntityMetadata) -> str:
    return metadata.device_class or "Wert"


def _zahl(wert: float) -> str:
    if float(wert).is_integer():
        return str(int(wert))
    return f"{wert:g}".replace(".", ",")


def suggestions_to_list(suggestions: Sequence[Suggestion]) -> list[dict[str, Any]]:
    return [vorschlag.to_dict() for vorschlag in suggestions]
