"""Tests der Uebersetzung im Backend.

Titel, Begruendungen und Meldungsvorlagen der Vorschlaege entstehen im
Backend. Geprueft wird die Mechanik und die Vollstaendigkeit; die einzelnen
Formulierungen sind nicht Gegenstand der Tests.
"""

from __future__ import annotations

import pytest

from custom_components.notification_center.discovery.suggestions import (
    EntityMetadata,
    build_suggestions,
)
from custom_components.notification_center.discovery.texte import (
    GRUNDSPRACHE,
    TEXTE,
    passende_sprache,
    sprache_von,
    text,
    zahl,
)


def meta(**felder: object) -> EntityMetadata:
    grund: dict[str, object] = {
        "entity_id": "binary_sensor.pruefung",
        "name": "Pruefung",
        "domain": "binary_sensor",
        "device_class": None,
        "unit": None,
    }
    grund.update(felder)
    return EntityMetadata(**grund)  # type: ignore[arg-type]


# -- Mechanik ---------------------------------------------------------------


def test_unbekannte_sprache_faellt_auf_englisch_zurueck() -> None:
    assert passende_sprache("fr") == GRUNDSPRACHE
    assert passende_sprache(None) == GRUNDSPRACHE


def test_regionale_variante_faellt_auf_die_grundform() -> None:
    assert passende_sprache("de-CH") == "de"
    assert passende_sprache("EN-GB") == "en"


def test_luecke_in_einer_sprache_faellt_auf_englisch_zurueck() -> None:
    TEXTE["xx"] = {"state.on": "pa"}
    try:
        assert text("xx", "state.on") == "pa"
        assert text("xx", "state.off") == TEXTE["en"]["state.off"]
    finally:
        del TEXTE["xx"]


def test_unbekannter_schluessel_zeigt_sich_selbst() -> None:
    # Eine Luecke soll auffallen, nicht stillschweigend leer bleiben.
    assert text("de", "gibt.es.nicht") == "gibt.es.nicht"


def test_zahlen_folgen_der_sprache() -> None:
    assert zahl("de", 21.5) == "21,5"
    assert zahl("en", 21.5) == "21.5"
    # Ganze Zahlen ohne Nachkommastelle, in jeder Sprache.
    assert zahl("de", 20.0) == "20"
    assert zahl("en", 20.0) == "20"


def test_sprache_der_installation(monkeypatch: pytest.MonkeyPatch) -> None:
    class Konfiguration:
        language = "de"

    class Hass:
        config = Konfiguration()

    assert sprache_von(Hass()) == "de"
    assert sprache_von(None) == GRUNDSPRACHE


# -- Vollstaendigkeit --------------------------------------------------------


def test_keine_sprache_bringt_unbekannte_schluessel_mit() -> None:
    for sprache, woerterbuch in TEXTE.items():
        if sprache == GRUNDSPRACHE:
            continue
        unbekannt = set(woerterbuch) - set(TEXTE[GRUNDSPRACHE])
        assert not unbekannt, f"{sprache}: {sorted(unbekannt)}"


def test_jede_sprache_uebersetzt_alle_schluessel() -> None:
    for sprache, woerterbuch in TEXTE.items():
        fehlend = set(TEXTE[GRUNDSPRACHE]) - set(woerterbuch)
        assert not fehlend, f"{sprache}: {sorted(fehlend)}"


def test_platzhalter_stimmen_zwischen_den_sprachen_ueberein() -> None:
    """Ein fehlender Platzhalter wuerde die Ausgabe still verstuemmeln."""
    import re

    def platzhalter(wert: str) -> set[str]:
        return set(re.findall(r"\{(\w+)\}", wert))

    for sprache, woerterbuch in TEXTE.items():
        if sprache == GRUNDSPRACHE:
            continue
        for schluessel, wert in woerterbuch.items():
            assert platzhalter(wert) == platzhalter(TEXTE[GRUNDSPRACHE][schluessel]), (
                f"{sprache}: {schluessel}"
            )


# -- Vorschlaege -------------------------------------------------------------


def test_vorschlag_kommt_in_der_gewaehlten_sprache() -> None:
    englisch = build_suggestions(meta(device_class="smoke"), sprache="en")[0]
    deutsch = build_suggestions(meta(device_class="smoke"), sprache="de")[0]

    assert englisch.title == "Alarm on smoke detected"
    assert deutsch.title == "Alarm bei Rauch erkannt"
    # Der Schluessel des Vorschlags bleibt gleich: er ist keine Anzeige.
    assert englisch.key == deutsch.key


def test_begruendungen_folgen_der_sprache() -> None:
    englisch = build_suggestions(meta(device_class="window"), sprache="en")[0]
    deutsch = build_suggestions(meta(device_class="window"), sprache="de")[0]

    assert englisch.reasons[0].label == "Device class"
    assert deutsch.reasons[0].label == "Geraeteklasse"


def test_meldungsvorlage_von_an_und_aus_ist_uebersetzt() -> None:
    englisch = build_suggestions(meta(domain="switch", name="Pumpe"), sprache="en")
    deutsch = build_suggestions(meta(domain="switch", name="Pumpe"), sprache="de")

    an_englisch = next(v for v in englisch if v.key == "on_off_on")
    an_deutsch = next(v for v in deutsch if v.key == "on_off_on")

    assert an_englisch.title == "Information when Pumpe is on"
    assert an_englisch.message_template == "{name}: on"
    assert an_deutsch.title == "Information, wenn Pumpe an ist"
    assert an_deutsch.message_template == "{name}: an"


def test_ohne_angabe_gilt_englisch() -> None:
    assert build_suggestions(meta(device_class="smoke"))[0].title.startswith("Alarm on")
