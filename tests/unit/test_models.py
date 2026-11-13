"""Tests der Notification-Datenmodelle."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from custom_components.notification_center.notifications.models import (
    CloseReason,
    NotificationEvent,
    NotificationSource,
    NotificationType,
    automation_key,
)

from .conftest import T0, make_event


def test_severity_ordnung() -> None:
    assert NotificationType.INFO.severity < NotificationType.WARNING.severity
    assert NotificationType.WARNING.severity < NotificationType.ALARM.severity


def test_start_time_muss_zeitzonenbewusst_sein() -> None:
    with pytest.raises(ValueError, match="zeitzonenbewusst"):
        NotificationEvent(
            message="x",
            type=NotificationType.INFO,
            source=NotificationSource.ENTITY_RULE,
            start_time=datetime(2026, 8, 23, 12, 0, 0),
        )


def test_dauer_eines_aktiven_ereignisses_waechst_mit_der_zeit() -> None:
    """Spezifikation 33: Dauer aktiver Ereignisse dynamisch berechnen."""
    event = make_event()
    assert event.duration(T0 + timedelta(minutes=12)) == pytest.approx(720.0)
    assert event.duration(T0 + timedelta(minutes=30)) == pytest.approx(1800.0)


def test_dauer_eines_abgeschlossenen_ereignisses_ist_fix() -> None:
    event = make_event()
    event.close(T0 + timedelta(minutes=12), CloseReason.CONDITION_CLEARED)
    assert event.duration(T0 + timedelta(hours=5)) == pytest.approx(720.0)


def test_close_ist_idempotent() -> None:
    event = make_event()
    event.close(T0 + timedelta(minutes=5), CloseReason.CONDITION_CLEARED)
    event.close(T0 + timedelta(minutes=99), CloseReason.DISMISSED)

    assert event.close_reason is CloseReason.CONDITION_CLEARED
    assert event.duration() == pytest.approx(300.0)


def test_close_vor_startzeit_wird_auf_startzeit_geklemmt() -> None:
    event = make_event()
    event.close(T0 - timedelta(minutes=5), CloseReason.CONDITION_CLEARED)
    assert event.end_time == T0
    assert event.duration() == 0.0


def test_to_dict_liefert_iso_zeiten_und_dauer() -> None:
    event = make_event(entity_id="binary_sensor.fenster")
    data = event.to_dict(now=T0 + timedelta(minutes=3))

    assert data["start_time"] == "2026-08-23T12:00:00+00:00"
    assert data["end_time"] is None
    assert data["duration"] == pytest.approx(180.0)
    assert data["active"] is True
    assert data["type"] == "warning"
    assert data["source"] == "entity_rule"
    assert data["entity_id"] == "binary_sensor.fenster"


def test_automation_key_trennt_gleiche_ids_verschiedener_owner() -> None:
    """Spezifikation 25 und Testfall J."""
    a = automation_key("automation.keller", "leck")
    b = automation_key("automation.dach", "leck")
    assert a != b

    # Der Trenner darf nicht durch Owner-Namen faelschbar sein.
    assert automation_key("a", "b_c") != automation_key("a_b", "c")


# -- Von Hand deaktivieren --------------------------------------------------


def test_von_hand_beendetes_ereignis_ist_als_solches_erkennbar() -> None:
    ereignis = make_event()
    ereignis.close(T0 + timedelta(minutes=5), CloseReason.DEACTIVATED)

    assert ereignis.active is False
    assert ereignis.deactivated is True
    assert ereignis.to_dict()["close_reason"] == "deactivated"


def test_anders_beendetes_ereignis_ist_nicht_wieder_aktivierbar() -> None:
    """Was wegen seiner Bedingung endete, behauptet sonst eine alte Lage."""
    ereignis = make_event()
    ereignis.close(T0 + timedelta(minutes=5), CloseReason.CONDITION_CLEARED)
    assert ereignis.deactivated is False


def test_fortsetzen_behaelt_den_beginn() -> None:
    ereignis = make_event()
    beginn = ereignis.start_time
    ereignis.close(T0 + timedelta(minutes=5), CloseReason.DEACTIVATED)

    ereignis.reopen()

    assert ereignis.active is True
    assert ereignis.end_time is None
    assert ereignis.close_reason is None
    # Derselbe Datensatz, derselbe Beginn (Spezifikation 31).
    assert ereignis.start_time == beginn
    assert ereignis.deactivated is False


def test_fortsetzen_eines_laufenden_ereignisses_ist_wirkungslos() -> None:
    ereignis = make_event()
    ereignis.reopen()
    assert ereignis.active is True
    assert ereignis.end_time is None


def test_laufendes_ereignis_hat_keinen_abschlussgrund() -> None:
    assert make_event().to_dict()["close_reason"] is None
