"""Tests der Historienanalyse und der Vorschlagsengine.

Deckt die Spezifikationsabschnitte 10 bis 13 und 79 ab.
"""

from __future__ import annotations

import pytest

from custom_components.notification_center.discovery.analyzer import (
    MIN_SAMPLES,
    analyze_numeric,
    analyze_states,
    percentile,
    suggest_hysteresis,
    suggest_lower_threshold,
    suggest_upper_threshold,
)
from custom_components.notification_center.discovery.suggestions import (
    Confidence,
    EntityMetadata,
    build_suggestions,
)
from custom_components.notification_center.notifications.models import NotificationType
from custom_components.notification_center.rules.models import (
    ConditionKind,
    NumericOperator,
)

# Ein ruhiger Wohnzimmerverlauf: ueblich 19 bis 24 Grad.
WOHNZIMMER = [
    19.0,
    19.5,
    20.0,
    20.5,
    21.0,
    21.5,
    22.0,
    22.5,
    23.0,
    23.5,
    24.0,
    21.0,
    20.0,
    22.0,
    21.5,
    20.5,
]


# -- Quantile ---------------------------------------------------------------


def test_quantil_einer_einzelnen_zahl() -> None:
    assert percentile([5.0], 0.95) == 5.0


def test_quantile_liegen_in_der_reihe() -> None:
    werte = list(range(1, 101))
    assert percentile(werte, 0.05) == 5
    assert percentile(werte, 0.50) == 50
    assert percentile(werte, 0.95) == 95


def test_quantil_einer_leeren_reihe_ist_ein_fehler() -> None:
    with pytest.raises(ValueError, match="leeren"):
        percentile([], 0.5)


# -- Numerische Analyse -----------------------------------------------------


def test_zu_wenige_messwerte_ergeben_kein_profil() -> None:
    """Spezifikation 12: ohne Grundlage kein Vorschlag."""
    assert analyze_numeric([20.0] * (MIN_SAMPLES - 1)) is None


def test_profil_beschreibt_den_ueblichen_bereich() -> None:
    profil = analyze_numeric(WOHNZIMMER)
    assert profil is not None
    assert profil.count == len(WOHNZIMMER)
    assert profil.minimum == 19.0
    assert profil.maximum == 24.0
    assert 19.0 <= profil.p05 <= 21.0
    assert 23.0 <= profil.p95 <= 24.0


def test_unbrauchbare_werte_werden_uebergangen() -> None:
    profil = analyze_numeric([*WOHNZIMMER, float("nan"), float("inf")])
    assert profil is not None
    assert profil.count == len(WOHNZIMMER)


def test_konstanter_wert_wird_erkannt() -> None:
    profil = analyze_numeric([21.0] * 20)
    assert profil is not None
    assert profil.is_constant is True
    assert suggest_upper_threshold(profil) is None


# -- Schwellenvorschlaege ---------------------------------------------------


def test_obere_schwelle_liegt_ueber_dem_ueblichen_bereich() -> None:
    profil = analyze_numeric(WOHNZIMMER)
    assert profil is not None
    schwelle = suggest_upper_threshold(profil)
    assert schwelle is not None
    assert schwelle > profil.p95


def test_untere_schwelle_liegt_unter_dem_ueblichen_bereich() -> None:
    profil = analyze_numeric(WOHNZIMMER)
    assert profil is not None
    schwelle = suggest_lower_threshold(profil)
    assert schwelle is not None
    assert schwelle < profil.p05


def test_ausreisser_verschiebt_die_schwelle_nicht_ins_unbrauchbare() -> None:
    """Quantile statt Maximum: ein Geraetefehler darf nicht dominieren."""
    ohne = analyze_numeric(WOHNZIMMER)
    mit = analyze_numeric([*WOHNZIMMER, 250.0])
    assert ohne is not None and mit is not None

    schwelle_ohne = suggest_upper_threshold(ohne)
    schwelle_mit = suggest_upper_threshold(mit)
    assert schwelle_ohne is not None and schwelle_mit is not None
    assert schwelle_mit < 60


def test_hysterese_liegt_auf_der_ruhigen_seite() -> None:
    profil = analyze_numeric(WOHNZIMMER)
    assert profil is not None

    obere = suggest_upper_threshold(profil)
    assert obere is not None
    assert suggest_hysteresis(obere, profil, upper=True) < obere

    untere = suggest_lower_threshold(profil)
    assert untere is not None
    assert suggest_hysteresis(untere, profil, upper=False) > untere


# -- Zustandsanalyse --------------------------------------------------------


def test_zustandsprofil_zaehlt_und_sortiert() -> None:
    profil = analyze_states(["idle"] * 10 + ["running"] * 4 + ["finished"])
    assert profil is not None
    assert profil.distinct_states[0] == "idle"
    assert profil.distinct_states[-1] == "finished"
    assert profil.share("idle") == pytest.approx(10 / 15)


def test_zu_wenige_zustaende_ergeben_kein_profil() -> None:
    assert analyze_states(["on", "off"]) is None


# -- Vorschlaege fuer Binaersensoren ---------------------------------------


def meta(**kwargs: object) -> EntityMetadata:
    defaults: dict[str, object] = {
        "entity_id": "binary_sensor.fenster_wz",
        "domain": "binary_sensor",
        "name": "Fenster Wohnzimmer",
    }
    defaults.update(kwargs)
    return EntityMetadata(**defaults)  # type: ignore[arg-type]


def test_rauchmelder_wird_zum_alarm() -> None:
    vorschlaege = build_suggestions(meta(device_class="smoke", name="Rauchmelder Flur"))
    assert vorschlaege[0].type is NotificationType.ALARM
    assert vorschlaege[0].confidence is Confidence.HIGH
    assert vorschlaege[0].states == ("on",)


def test_fenster_bekommt_eine_zeitbedingung() -> None:
    """Spezifikation 17: nicht jede geoeffnete Tuer ist sofort meldenswert."""
    vorschlaege = build_suggestions(meta(device_class="window"))
    assert vorschlaege[0].duration_seconds == 900
    assert vorschlaege[0].type is NotificationType.WARNING
    assert "15 Minuten" in vorschlaege[0].title


def test_stoerung_wird_zur_warnung() -> None:
    vorschlaege = build_suggestions(meta(device_class="problem"))
    assert vorschlaege[0].type is NotificationType.WARNING


def test_unbekannter_binaersensor_bekommt_an_und_aus() -> None:
    """Issue 1: fuer Binaersensoren sind an und aus immer gueltige Regeln.

    Ohne sie stuende man vor einer leeren Liste, obwohl die beiden sinnvollen
    Regeln auf der Hand liegen.
    """
    vorschlaege = build_suggestions(meta(entity_id="binary_sensor.irgendwas", name="Irgendwas"))

    assert [v.states for v in vorschlaege] == [("on",), ("off",)]
    assert all(v.confidence is Confidence.MEDIUM for v in vorschlaege)


def test_schalter_bekommt_an_und_aus() -> None:
    """Issue 1: dasselbe gilt fuer Schalter."""
    vorschlaege = build_suggestions(
        EntityMetadata(entity_id="switch.pumpe", domain="switch", name="Pumpe")
    )
    assert len(vorschlaege) == 2
    assert vorschlaege[0].title == "Information, wenn Pumpe an ist"


def test_an_und_aus_stehen_hinter_den_klassenbezogenen() -> None:
    """Was die Geraeteklasse hergibt, wiegt schwerer als der blosse Zustand."""
    vorschlaege = build_suggestions(meta(device_class="smoke", name="Rauchmelder"))

    assert vorschlaege[0].key == "smoke_state"
    assert [v.key for v in vorschlaege[1:]] == ["on_off_on", "on_off_off"]


def test_sensoren_bekommen_keine_an_aus_vorschlaege() -> None:
    """Ein Messwert kennt kein an und aus."""
    vorschlaege = build_suggestions(
        EntityMetadata(entity_id="sensor.temperatur", domain="sensor", name="Temperatur")
    )
    assert vorschlaege == []


# -- Metadaten wiegen schwerer als Namen (Spezifikation 10) ----------------


def test_geraeteklasse_ergibt_hohe_sicherheit() -> None:
    vorschlaege = build_suggestions(meta(device_class="moisture", name="Melder 3"))
    assert vorschlaege[0].confidence is Confidence.HIGH


def test_nur_der_name_ergibt_geringe_sicherheit() -> None:
    vorschlaege = build_suggestions(
        meta(entity_id="binary_sensor.wasser_keller", name="Wasser Keller")
    )
    aus_dem_namen = next(v for v in vorschlaege if v.key == "moisture_state")

    assert aus_dem_namen.confidence is Confidence.LOW
    assert aus_dem_namen.confidence.is_uncertain is True


def test_geraeteklasse_schlaegt_irrefuehrenden_namen() -> None:
    """Ein Sensor namens 'Temperatur' mit device_class humidity ist Feuchte."""
    vorschlaege = build_suggestions(
        EntityMetadata(
            entity_id="sensor.temperatur_bad",
            domain="sensor",
            name="Temperatur Bad",
            device_class="humidity",
            unit="%",
        )
    )
    assert vorschlaege[0].threshold == 65.0
    assert vorschlaege[0].confidence is Confidence.HIGH


# -- Numerische Vorschlaege -------------------------------------------------


def sensor_meta(**kwargs: object) -> EntityMetadata:
    defaults: dict[str, object] = {
        "entity_id": "sensor.temperatur_wz",
        "domain": "sensor",
        "name": "Temperatur Wohnzimmer",
        "device_class": "temperature",
        "state_class": "measurement",
        "unit": "°C",
    }
    defaults.update(kwargs)
    return EntityMetadata(**defaults)  # type: ignore[arg-type]


def test_batterie_bekommt_die_uebliche_schwelle() -> None:
    vorschlaege = build_suggestions(
        sensor_meta(entity_id="sensor.batterie_melder", device_class="battery", unit="%")
    )
    assert vorschlaege[0].operator is NumericOperator.LT
    assert vorschlaege[0].threshold == 20.0


def test_temperatur_ohne_historie_ergibt_keinen_schwellenvorschlag() -> None:
    """Spezifikation 12: ohne Grundlage kein automatischer Vorschlag."""
    assert build_suggestions(sensor_meta()) == []


def test_temperatur_mit_historie_schlaegt_schwellen_vor() -> None:
    profil = analyze_numeric(WOHNZIMMER)
    vorschlaege = build_suggestions(sensor_meta(), numeric_profile=profil)

    assert len(vorschlaege) == 2
    obere = next(v for v in vorschlaege if v.operator is NumericOperator.GT)
    assert obere.kind is ConditionKind.NUMERIC
    assert obere.threshold is not None and obere.threshold > 24
    assert obere.release_threshold is not None
    assert obere.release_threshold < obere.threshold
    assert obere.confidence is Confidence.HIGH


def test_begruendung_nennt_historie_und_bereich() -> None:
    """Spezifikation 13: die Empfehlung steht oben, die Gruende darunter."""
    profil = analyze_numeric(WOHNZIMMER)
    vorschlag = build_suggestions(sensor_meta(), numeric_profile=profil, analysis_days=7)[0]

    labels = {reason.label for reason in vorschlag.reasons}
    assert "Geraeteklasse" in labels
    assert "Historie" in labels
    assert "typischer Bereich" in labels
    assert "vorgeschlagene Schwelle" in labels

    historie = next(r for r in vorschlag.reasons if r.label == "Historie")
    assert historie.value == "letzte 7 Tage"


def test_fehlende_einheit_senkt_die_sicherheit() -> None:
    profil = analyze_numeric(WOHNZIMMER)
    vorschlaege = build_suggestions(
        sensor_meta(unit=None, state_class="measurement"), numeric_profile=profil
    )
    assert vorschlaege[0].confidence is Confidence.MEDIUM


def test_absolute_schwelle_steht_vor_der_historischen() -> None:
    """Anerkannte Grenzwerte haben Vorrang vor abgeleiteten."""
    profil = analyze_numeric([40.0, 45.0, 50.0, 55.0, 60.0] * 4)
    vorschlaege = build_suggestions(
        sensor_meta(device_class="humidity", unit="%"), numeric_profile=profil
    )
    assert vorschlaege[0].threshold == 65.0


# -- Sortierung und Serialisierung -----------------------------------------


def test_sicherste_vorschlaege_zuerst() -> None:
    profil = analyze_numeric(WOHNZIMMER)
    vorschlaege = build_suggestions(
        sensor_meta(device_class="humidity", unit="%"), numeric_profile=profil
    )
    rangfolge = [v.confidence for v in vorschlaege]
    assert rangfolge == sorted(rangfolge, key=lambda c: {"high": 0, "medium": 1, "low": 2}[c])


def test_vorschlag_als_dict() -> None:
    vorschlag = build_suggestions(meta(device_class="smoke"))[0]
    daten = vorschlag.to_dict()

    assert daten["type"] == "alarm"
    assert daten["confidence"] == "high"
    assert daten["uncertain"] is False
    assert isinstance(daten["reasons"], list)
    assert daten["reasons"][0]["label"] == "Geraeteklasse"


# -- Seltene Zustaende ------------------------------------------------------


def test_seltener_zustand_wird_vorgeschlagen() -> None:
    profil = analyze_states(["idle"] * 40 + ["running"] * 10 + ["error"] * 2)
    vorschlaege = build_suggestions(
        EntityMetadata(entity_id="sensor.waschmaschine", domain="sensor", name="Waschmaschine"),
        state_profile=profil,
    )
    assert len(vorschlaege) == 1
    assert vorschlaege[0].states == ("error",)
    assert vorschlaege[0].confidence is Confidence.LOW


def test_ausgeglichene_zustaende_ergeben_keinen_vorschlag() -> None:
    profil = analyze_states(["auf"] * 10 + ["zu"] * 10)
    vorschlaege = build_suggestions(
        EntityMetadata(entity_id="sensor.klappe", domain="sensor", name="Klappe"),
        state_profile=profil,
    )
    assert vorschlaege == []
