"""Auswertung der Historie einer Entity.

Ohne Home-Assistant-Importe: die Analyse bekommt fertige Messwerte
hereingereicht. Woher sie stammen, entscheidet ``engine.py``.

Ziel ist nicht Statistik um ihrer selbst willen, sondern eine belastbare
Antwort auf eine einzige Frage: welcher Wertebereich ist fuer diese Entity
normal, und ab wann lohnt eine Meldung (Spezifikation 11)?

Deshalb werden Quantile statt Minimum und Maximum verwendet. Ein einzelner
Ausreisser, etwa waehrend eines Geraetefehlers, wuerde eine aus dem Maximum
abgeleitete Schwelle sonst unbrauchbar hoch setzen.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

#: Weniger Messwerte tragen keine Aussage ueber einen typischen Bereich.
MIN_SAMPLES = 12

#: Unterhalb dieser Zahl von Zustandswechseln ist eine Zustandsverteilung
#: nicht aussagekraeftig.
MIN_STATE_SAMPLES = 5


@dataclass(frozen=True, slots=True)
class NumericProfile:
    """Verdichtete Beschreibung eines numerischen Verlaufs."""

    count: int
    span_days: float
    minimum: float
    maximum: float
    mean: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float

    @property
    def typical_range(self) -> tuple[float, float]:
        """Der Bereich, in dem sich der Wert ueblicherweise bewegt."""
        return (self.p05, self.p95)

    @property
    def spread(self) -> float:
        return self.p95 - self.p05

    @property
    def iqr(self) -> float:
        """Interquartilsabstand: die Streuung der mittleren Haelfte.

        Anders als der Abstand zwischen p05 und p95 bleibt er auch bei kleinen
        Stichproben von einzelnen Ausreissern unberuehrt.
        """
        return self.p75 - self.p25

    @property
    def is_constant(self) -> bool:
        """Ein unveraenderlicher Wert traegt keine Schwelle."""
        return math.isclose(self.minimum, self.maximum)


@dataclass(frozen=True, slots=True)
class StateProfile:
    """Verdichtete Beschreibung eines Zustandsverlaufs."""

    count: int
    span_days: float
    occurrences: dict[str, int]

    @property
    def distinct_states(self) -> tuple[str, ...]:
        """Zustaende, nach Haeufigkeit absteigend."""
        return tuple(
            zustand
            for zustand, _ in sorted(self.occurrences.items(), key=lambda paar: (-paar[1], paar[0]))
        )

    def share(self, state: str) -> float:
        """Anteil eines Zustands an allen beobachteten Werten."""
        if self.count == 0:
            return 0.0
        return self.occurrences.get(state, 0) / self.count


def percentile(values: Sequence[float], fraction: float) -> float:
    """Quantil nach der Methode des naechsten Rangs.

    Bewusst ohne Interpolation und ohne zusaetzliche Abhaengigkeit: fuer
    Schwellenvorschlaege ist die Genauigkeit voellig ausreichend.
    """
    if not values:
        raise ValueError("Quantil einer leeren Reihe")

    sortiert = sorted(values)
    if len(sortiert) == 1:
        return sortiert[0]

    rang = max(1, math.ceil(fraction * len(sortiert)))
    return sortiert[min(rang, len(sortiert)) - 1]


def analyze_numeric(values: Sequence[float], *, span_days: float = 7.0) -> NumericProfile | None:
    """Verdichtet Messwerte zu einem Profil.

    Gibt ``None`` zurueck, wenn zu wenige Werte vorliegen. Dann entsteht kein
    automatischer Vorschlag (Spezifikation 12); eine eigene Regel bleibt
    trotzdem moeglich (Spezifikation 79).
    """
    brauchbar = [float(wert) for wert in values if _ist_endlich(wert)]
    if len(brauchbar) < MIN_SAMPLES:
        return None

    return NumericProfile(
        count=len(brauchbar),
        span_days=span_days,
        minimum=min(brauchbar),
        maximum=max(brauchbar),
        mean=sum(brauchbar) / len(brauchbar),
        p05=percentile(brauchbar, 0.05),
        p25=percentile(brauchbar, 0.25),
        p50=percentile(brauchbar, 0.50),
        p75=percentile(brauchbar, 0.75),
        p95=percentile(brauchbar, 0.95),
    )


def analyze_states(states: Sequence[str], *, span_days: float = 7.0) -> StateProfile | None:
    """Verdichtet Zustandswerte zu einem Profil."""
    brauchbar = [zustand for zustand in states if zustand]
    if len(brauchbar) < MIN_STATE_SAMPLES:
        return None

    return StateProfile(
        count=len(brauchbar),
        span_days=span_days,
        occurrences=dict(Counter(brauchbar)),
    )


# ---------------------------------------------------------------------------
# Schwellenvorschlaege
# ---------------------------------------------------------------------------


def suggest_upper_threshold(profile: NumericProfile) -> float | None:
    """Schwelle oberhalb des ueblichen Bereichs.

    Der Abstand richtet sich nach der Streuung: bei einem ruhigen Verlauf
    genuegt ein kleiner Aufschlag, bei einem unruhigen braucht es mehr, damit
    die Meldung nicht bei jedem normalen Ausschlag kommt.

    Zusaetzlich begrenzt eine robuste Obergrenze das Ergebnis. Bei wenigen
    Messwerten faellt das 95-%-Quantil mit dem Maximum zusammen; ein einzelner
    Ausreisser, etwa waehrend eines Geraetefehlers, wuerde die Schwelle sonst
    unbrauchbar hoch setzen.
    """
    if profile.is_constant:
        return None
    return _runden(min(profile.p95 + _abstand(profile), _obergrenze(profile)))


def suggest_lower_threshold(profile: NumericProfile) -> float | None:
    """Schwelle unterhalb des ueblichen Bereichs.

    Nach unten gilt dieselbe Absicherung gegen einzelne Ausreisser.
    """
    if profile.is_constant:
        return None
    return _runden(max(profile.p05 - _abstand(profile), _untergrenze(profile)))


def _obergrenze(profile: NumericProfile) -> float:
    """Robuste Obergrenze: Median plus drei Interquartilsabstaende."""
    return profile.p50 + 3 * max(profile.iqr, _mindeststreuung(profile))


def _untergrenze(profile: NumericProfile) -> float:
    return profile.p50 - 3 * max(profile.iqr, _mindeststreuung(profile))


def _mindeststreuung(profile: NumericProfile) -> float:
    """Damit ein sehr ruhiger Verlauf keine hauchduenne Grenze ergibt."""
    return max(abs(profile.p50) * 0.02, 0.5)


def suggest_hysteresis(threshold: float, profile: NumericProfile, *, upper: bool) -> float:
    """Rueckkehrschwelle zu einer Ausloeseschwelle (Spezifikation 18).

    Sie liegt eine halbe Streuungsbreite auf der ruhigen Seite, mindestens
    aber merklich von der Ausloeseschwelle entfernt, damit ein Wert nicht
    zwischen beiden hin- und herspringt.
    """
    abstand = max(_abstand(profile) / 2, abs(threshold) * 0.01, 0.1)
    return _runden(threshold - abstand if upper else threshold + abstand)


def _abstand(profile: NumericProfile) -> float:
    """Sicherheitsabstand zum ueblichen Bereich.

    Bemessen am Interquartilsabstand, nicht an der Gesamtspanne: sonst wuerde
    ein einzelner Ausreisser den Abstand mit aufblaehen.
    """
    return max(profile.iqr, 1.0)


def _runden(wert: float) -> float:
    """Rundet auf eine Zahl, die in einer Oberflaeche lesbar ist."""
    if abs(wert) >= 100:
        return float(round(wert / 5) * 5)
    if abs(wert) >= 10:
        return float(round(wert))
    return round(wert, 1)


def _ist_endlich(wert: object) -> bool:
    try:
        zahl = float(wert)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return math.isfinite(zahl)
