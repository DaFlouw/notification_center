"""Texte der Discovery-Vorschlaege, nach Sprache getrennt.

Titel, Begruendungen und Meldungsvorlagen entstehen im Backend und gehen als
fertiger Text an die Oberflaeche. Sie muessen deshalb hier uebersetzt werden
und nicht erst im Frontend -- zumal die Meldungsvorlage beim Uebernehmen zur
Regel wird und dann so stehen bleibt, wie sie war.

Grundsprache ist Englisch: sie haelt den vollstaendigen Satz Schluessel und
faengt jede Luecke auf.

Eine weitere Sprache hinzufuegen: einen Eintrag in ``TEXTE`` anlegen und die
Schluessel uebersetzen. Fehlende Schluessel sind erlaubt, sie fallen auf
Englisch zurueck. Die Tests pruefen, dass keine Sprache unbekannte Schluessel
mitbringt.
"""

from __future__ import annotations

from typing import Any

GRUNDSPRACHE = "en"

#: Sprachen, in denen die Kommastelle nicht mit einem Punkt geschrieben wird.
_KOMMA_SPRACHEN = frozenset({"de"})

TEXTE: dict[str, dict[str, str]] = {
    "en": {
        # -- Geraeteklassen, deren Zustand fuer sich spricht ---------------
        "class.smoke": "smoke detected",
        "class.gas": "gas detected",
        "class.carbon_monoxide": "carbon monoxide detected",
        "class.moisture": "moisture detected",
        "class.safety": "safety alert",
        "class.problem": "problem reported",
        "class.battery": "battery low",
        "class.tamper": "tampering detected",
        # -- Oeffnungen ----------------------------------------------------
        "opening.door": "door",
        "opening.window": "window",
        "opening.garage_door": "garage door",
        "opening.opening": "opening",
        # -- Allgemein anerkannte Schwellen --------------------------------
        "absolute.battery": "battery below 20 %",
        "absolute.carbon_dioxide": "CO2 above 1200 ppm",
        "absolute.humidity": "humidity above 65 %",
        # -- Titel ----------------------------------------------------------
        "title.alarm": "Alarm on {text}",
        "title.warning": "Warning on {text}",
        "title.openingOpen": "Warning when {thing} is open for more than {minutes} minutes",
        "title.onOff": "Information when {name} is {state}",
        "title.absolute": "Warning at {text}",
        "title.above": "Warning at {label} above {value}{unit}",
        "title.below": "Warning at {label} below {value}{unit}",
        "title.rareState": "Information when the state '{state}' occurs",
        # -- Zustaende und Bezeichnungen ------------------------------------
        "state.on": "on",
        "state.off": "off",
        "label.value": "Value",
        # -- Begruendungen ---------------------------------------------------
        "reason.deviceClass": "Device class",
        "reason.domain": "Domain",
        "reason.basis": "Basis",
        "reason.hint": "Hint",
        "reason.duration": "Time condition",
        "reason.history": "History",
        "reason.typicalRange": "typical range",
        "reason.suggestedThreshold": "suggested threshold",
        "reason.returnBelow": "returns below",
        "reason.observedStates": "observed states",
        "reason.share": "Share",
        "reason.unknown": "unknown",
        "reason.fixedStates": "the state space of this domain is fixed",
        "reason.commonThreshold": "commonly used threshold",
        "reason.fromName": "from the name '{name}'",
        "reason.minutes": "{minutes} minutes without interruption",
        "reason.lastDays": "last {days} days",
        "reason.range": "{low} to {high}{unit}",
        "reason.shareValue": "{state} in {percent} % of cases",
    },
    "de": {
        "class.smoke": "Rauch erkannt",
        "class.gas": "Gas erkannt",
        "class.carbon_monoxide": "Kohlenmonoxid erkannt",
        "class.moisture": "Feuchtigkeit erkannt",
        "class.safety": "Sicherheitsmeldung",
        "class.problem": "Stoerung gemeldet",
        "class.battery": "Batterie schwach",
        "class.tamper": "Manipulation erkannt",
        "opening.door": "Tuer",
        "opening.window": "Fenster",
        "opening.garage_door": "Garagentor",
        "opening.opening": "Oeffnung",
        "absolute.battery": "Batterie unter 20 %",
        "absolute.carbon_dioxide": "CO2 ueber 1200 ppm",
        "absolute.humidity": "Luftfeuchte ueber 65 %",
        "title.alarm": "Alarm bei {text}",
        "title.warning": "Warnung bei {text}",
        "title.openingOpen": "Warnung, wenn {thing} laenger als {minutes} Minuten offen ist",
        "title.onOff": "Information, wenn {name} {state} ist",
        "title.absolute": "Warnung bei {text}",
        "title.above": "Warnung bei {label} ueber {value}{unit}",
        "title.below": "Warnung bei {label} unter {value}{unit}",
        "title.rareState": "Information, wenn der Zustand '{state}' eintritt",
        "state.on": "an",
        "state.off": "aus",
        "label.value": "Wert",
        "reason.deviceClass": "Geraeteklasse",
        "reason.domain": "Domaene",
        "reason.basis": "Grundlage",
        "reason.hint": "Hinweis",
        "reason.duration": "Zeitbedingung",
        "reason.history": "Historie",
        "reason.typicalRange": "typischer Bereich",
        "reason.suggestedThreshold": "vorgeschlagene Schwelle",
        "reason.returnBelow": "Rueckkehr unter",
        "reason.observedStates": "beobachtete Zustaende",
        "reason.share": "Anteil",
        "reason.unknown": "unbekannt",
        "reason.fixedStates": "der Zustandsraum dieser Domaene steht fest",
        "reason.commonThreshold": "allgemein uebliche Schwelle",
        "reason.fromName": "aus dem Namen '{name}'",
        "reason.minutes": "{minutes} Minuten ununterbrochen",
        "reason.lastDays": "letzte {days} Tage",
        "reason.range": "{low} bis {high}{unit}",
        "reason.shareValue": "{state} in {percent} % der Faelle",
    },
}


def passende_sprache(code: str | None) -> str:
    """Die naechstliegende mitgelieferte Sprache zu einem Sprachcode.

    ``de-CH`` faellt auf ``de`` zurueck, alles Unbekannte auf Englisch.
    """
    wert = str(code or "").lower()
    if wert in TEXTE:
        return wert
    basis = wert.split("-")[0]
    return basis if basis in TEXTE else GRUNDSPRACHE


def sprache_von(hass: Any) -> str:
    """Die Sprache der Home-Assistant-Installation."""
    return passende_sprache(getattr(getattr(hass, "config", None), "language", None))


def text(sprache: str, key: str, **params: Any) -> str:
    """Der uebersetzte Text zu einem Schluessel.

    Fehlt er in der gewaehlten Sprache, greift Englisch; fehlt er auch dort,
    erscheint der Schluessel selbst -- eine Luecke soll auffallen.
    """
    vorlage = TEXTE.get(sprache, {}).get(key) or TEXTE[GRUNDSPRACHE].get(key) or key
    return vorlage.format(**params) if params else vorlage


def zahl(sprache: str, wert: float) -> str:
    """Eine Zahl so geschrieben, wie es die Sprache erwartet."""
    if float(wert).is_integer():
        return str(int(wert))
    geschrieben = f"{wert:g}"
    return geschrieben.replace(".", ",") if sprache in _KOMMA_SPRACHEN else geschrieben
