"""Tests der Zustandsauswahl (Fehlerticket 5).

Die Historie allein taugt nicht: kurz nach einem Neustart hat eine Entity
womoeglich erst einen Zustand gezeigt. Der Katalog je Domaene und die
Faehigkeiten der Entity liefern die Auswahl auch ohne jede Beobachtung.
"""

from __future__ import annotations

from custom_components.notification_center.discovery.states import (
    DOMAIN_STATES,
    available_states,
)


def test_binaersensor_ohne_historie_hat_beide_zustaende() -> None:
    assert available_states(domain="binary_sensor", current_state="off") == ["on", "off"]


def test_abdeckung_kennt_alle_vier_zustaende() -> None:
    zustaende = available_states(domain="cover", current_state="open")
    assert set(zustaende) == {"open", "opening", "closed", "closing"}


def test_schloss_kennt_auch_seltene_zustaende() -> None:
    """Genau der Fall: 'jammed' tritt selten auf und fehlt der Historie."""
    assert "jammed" in available_states(domain="lock", current_state="locked")


def test_optionen_der_entity_stehen_vorn() -> None:
    zustaende = available_states(
        domain="sensor",
        current_state="idle",
        attributes={"options": ["idle", "running", "finished"]},
    )
    assert zustaende == ["idle", "running", "finished"]


def test_faehigkeitsattribute_werden_beruecksichtigt() -> None:
    zustaende = available_states(
        domain="climate",
        current_state="heat",
        attributes={"hvac_modes": ["off", "heat", "cool"]},
    )
    assert zustaende[:3] == ["off", "heat", "cool"]


def test_beobachtetes_ergaenzt_die_liste() -> None:
    zustaende = available_states(domain="sensor", current_state="idle", observed=["idle", "error"])
    assert "error" in zustaende


def test_beobachtetes_steht_hinten() -> None:
    """Erwartetes zuerst, Ueberraschungen darunter."""
    zustaende = available_states(domain="binary_sensor", current_state="off", observed=["seltsam"])
    assert zustaende == ["on", "off", "seltsam"]


def test_unbrauchbare_zustaende_fallen_weg() -> None:
    zustaende = available_states(
        domain="sensor", current_state="unavailable", observed=["unknown", "", "gut"]
    )
    assert zustaende == ["gut"]


def test_doppelte_werte_erscheinen_einmal() -> None:
    zustaende = available_states(
        domain="binary_sensor", current_state="on", observed=["on", "on", "off"]
    )
    assert zustaende == ["on", "off"]


def test_unbekannte_domaene_faellt_auf_beobachtetes_zurueck() -> None:
    zustaende = available_states(domain="irgendwas", current_state="a", observed=["a", "b"])
    assert zustaende == ["a", "b"]


def test_katalog_enthaelt_die_wichtigen_domaenen() -> None:
    for domain in ("binary_sensor", "cover", "lock", "climate", "alarm_control_panel"):
        assert DOMAIN_STATES[domain]


def test_helfer_bekommen_ihre_zustaende() -> None:
    """Die Helferdomaenen sind seit Issue 4 ueberwachbar."""
    assert available_states(domain="input_boolean", current_state="on") == ["on", "off"]
    assert available_states(domain="timer", current_state="idle") == ["idle", "active", "paused"]
    assert available_states(domain="schedule", current_state="off") == ["on", "off"]


def test_auswahlhelfer_bietet_seine_optionen_an() -> None:
    zustaende = available_states(
        domain="input_select",
        current_state="Zuhause",
        attributes={"options": ["Zuhause", "Urlaub", "Gäste"]},
    )
    assert zustaende == ["Zuhause", "Urlaub", "Gäste"]


def test_freie_werte_ergeben_keine_auswahl() -> None:
    """Text- und Datumshelfer koennen jeden Wert tragen.

    Eine Liste waere hier immer unvollstaendig und wuerde den Anwender auf den
    einen Wert festnageln, der gerade eingetragen ist. Der Regel-Editor zeigt
    stattdessen ein Textfeld, sobald er keine Auswahl bekommt.
    """
    assert available_states(domain="input_text", current_state="Paketbote") == []
    assert available_states(domain="input_datetime", current_state="2026-08-28 07:00:00") == []
