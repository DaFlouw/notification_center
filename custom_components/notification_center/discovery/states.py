"""Moegliche Zustandswerte einer Entity.

Ohne Home-Assistant-Importe: die Auswahl entsteht aus Domaene, Attributen und
beobachteten Werten, die der Aufrufer beschafft.

Der Regel-Editor soll ein Auswahlfeld statt eines Textfelds anbieten
(Spezifikation 14). Die Historie allein taugt dafuer nicht: kurz nach einem
Neustart hat eine Entity vielleicht erst einen einzigen Zustand gezeigt, und
gerade der seltene, meldenswerte fehlt dann. Deshalb kommen drei Quellen
zusammen:

1. **Die Entity selbst**: ``options`` bei Enum-Sensoren, ``hvac_modes`` bei
   Thermostaten und die uebrigen faehigkeitsbeschreibenden Attribute.
2. **Ein Katalog je Domaene**: was ein ``binary_sensor`` oder ein ``lock``
   annehmen kann, steht fest und braucht keine Beobachtung.
3. **Beobachtete Werte**: der aktuelle Zustand und, sofern verfuegbar, was
   die Historie zusaetzlich gezeigt hat.

Die ersten beiden Quellen liefern schon ohne jede Historie ein vollstaendiges
Bild.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

#: Zustaende, die keine sinnvolle Regelgrundlage sind.
UNUSABLE = frozenset({"unknown", "unavailable", "none", ""})

#: Domaenen mit freiem Wert.
#:
#: Ein Texthelfer kann jeden Text tragen, ein Datumshelfer jeden Zeitpunkt.
#: Eine Auswahlliste waere hier immer unvollstaendig und wuerde den Anwender
#: auf den einen Wert festnageln, der zufaellig gerade eingetragen ist. Fuer
#: sie bleibt die Auswahl leer, damit der Regel-Editor ein Textfeld zeigt.
FREEFORM_DOMAINS = frozenset({"input_text", "input_datetime"})

#: Was die gaengigen Domaenen annehmen koennen. Quelle: die Zustandsdefinition
#: von Home Assistant, nicht die Beobachtung einer einzelnen Anlage.
DOMAIN_STATES: dict[str, tuple[str, ...]] = {
    "binary_sensor": ("on", "off"),
    "switch": ("on", "off"),
    "light": ("on", "off"),
    "fan": ("on", "off"),
    "input_boolean": ("on", "off"),
    "automation": ("on", "off"),
    "schedule": ("on", "off"),
    "cover": ("open", "opening", "closed", "closing"),
    "valve": ("open", "opening", "closed", "closing"),
    "lock": ("locked", "unlocked", "locking", "unlocking", "jammed", "open", "opening"),
    "device_tracker": ("home", "not_home"),
    "person": ("home", "not_home"),
    "alarm_control_panel": (
        "disarmed",
        "armed_home",
        "armed_away",
        "armed_night",
        "armed_vacation",
        "armed_custom_bypass",
        "pending",
        "arming",
        "disarming",
        "triggered",
    ),
    "media_player": ("off", "on", "idle", "playing", "paused", "standby", "buffering"),
    "vacuum": ("cleaning", "docked", "idle", "paused", "returning", "error"),
    "water_heater": ("eco", "electric", "performance", "high_demand", "heat_pump", "gas", "off"),
    "humidifier": ("on", "off"),
    "update": ("on", "off"),
    "climate": ("off", "heat", "cool", "heat_cool", "auto", "dry", "fan_only"),
    "sun": ("above_horizon", "below_horizon"),
    "timer": ("idle", "active", "paused"),
    "remote": ("on", "off"),
    "siren": ("on", "off"),
    "lawn_mower": ("mowing", "docked", "paused", "returning", "error"),
}

#: Attribute, die eine Entity selbst als Auswahl mitbringt.
CAPABILITY_ATTRIBUTES = (
    "options",
    "hvac_modes",
    "preset_modes",
    "fan_modes",
    "swing_modes",
    "operation_list",
    "source_list",
    "sound_mode_list",
    "effect_list",
)


def available_states(
    *,
    domain: str,
    current_state: str | None = None,
    attributes: Mapping[str, Any] | None = None,
    observed: Iterable[str] = (),
) -> list[str]:
    """Alle sinnvoll auswaehlbaren Zustaende einer Entity.

    Die Reihenfolge ist stabil: erst was die Entity selbst angibt, dann der
    Katalog ihrer Domaene, dann zusaetzlich Beobachtetes. So stehen die
    erwarteten Werte oben und Ueberraschungen unten.
    """
    if domain in FREEFORM_DOMAINS:
        return []

    attributes = attributes or {}
    gesehen: set[str] = set()
    ergebnis: list[str] = []

    def hinzu(werte: Iterable[Any]) -> None:
        for wert in werte:
            if not isinstance(wert, str | int | float) or isinstance(wert, bool):
                continue
            text = str(wert)
            if text.lower() in UNUSABLE or text in gesehen:
                continue
            gesehen.add(text)
            ergebnis.append(text)

    # 1. Was die Entity selbst als Auswahl angibt.
    for name in CAPABILITY_ATTRIBUTES:
        wert = attributes.get(name)
        if isinstance(wert, list | tuple):
            hinzu(wert)

    # 2. Der Katalog der Domaene.
    hinzu(DOMAIN_STATES.get(domain, ()))

    # 3. Beobachtetes, das die ersten beiden Quellen nicht kennen.
    if current_state is not None:
        hinzu([current_state])
    hinzu(observed)

    return ergebnis
