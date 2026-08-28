"""Tests des Notification-Lebenszyklus und der Zaehler.

Deckt die Spezifikationsabschnitte 22, 26, 37, 44, 45 und 52 ab.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.notification_center.notifications.lifecycle import (
    ActiveNotifications,
    Counts,
    automation_notification_key,
    key_for,
    rule_key,
)
from custom_components.notification_center.notifications.models import (
    CloseReason,
    NotificationSource,
    NotificationType,
)

from .conftest import T0, make_event


def regelereignis(rule_id: str = "rule_1", **kwargs: object):
    return make_event(rule_id=rule_id, **kwargs)


def automationsereignis(
    owner: str = "automation.keller", notification_id: str = "leck", **kwargs: object
):
    return make_event(
        source=NotificationSource.AUTOMATION,
        owner=owner,
        notification_id=notification_id,
        **kwargs,
    )


@pytest.fixture
def aktive() -> ActiveNotifications:
    menge = ActiveNotifications()
    menge.roll_day(T0.replace(hour=0, minute=0, second=0, microsecond=0))
    return menge


# -- Schluessel -------------------------------------------------------------


def test_schluessel_einer_regelnotification() -> None:
    assert key_for(regelereignis("rule_7")) == rule_key("rule_7")


def test_schluessel_einer_automationsnotification() -> None:
    ereignis = automationsereignis("automation.dach", "leck")
    assert key_for(ereignis) == automation_notification_key("automation.dach", "leck")


def test_gleiche_id_verschiedener_owner_ergeben_verschiedene_schluessel() -> None:
    """Testfall J."""
    a = key_for(automationsereignis("automation.keller", "leck"))
    b = key_for(automationsereignis("automation.dach", "leck"))
    assert a != b


def test_unvollstaendiges_ereignis_hat_keinen_schluessel() -> None:
    with pytest.raises(ValueError, match="rule_id"):
        key_for(make_event())


# -- Zaehler ----------------------------------------------------------------


def test_leere_menge_zaehlt_null(aktive: ActiveNotifications) -> None:
    assert aktive.counts == Counts()
    assert aktive.counts.active == 0


def test_zaehler_folgen_den_typen(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1", type=NotificationType.INFO))
    aktive.put(regelereignis("rule_2", type=NotificationType.WARNING))
    aktive.put(regelereignis("rule_3", type=NotificationType.WARNING))
    aktive.put(regelereignis("rule_4", type=NotificationType.ALARM))

    zaehler = aktive.counts
    assert (zaehler.info, zaehler.warning, zaehler.alarm) == (1, 2, 1)
    assert zaehler.active == 4


def test_beenden_senkt_den_zaehler(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1", type=NotificationType.ALARM))
    aktive.close(rule_key("rule_1"), T0 + timedelta(minutes=5), CloseReason.CONDITION_CLEARED)

    assert aktive.counts.alarm == 0
    assert aktive.counts.active == 0


def test_beenden_eines_unbekannten_schluessels_ist_wirkungslos(
    aktive: ActiveNotifications,
) -> None:
    assert aktive.close("rule:gibtsnicht", T0, CloseReason.DISMISSED) is None
    assert aktive.counts.active == 0


def test_typwechsel_verschiebt_den_zaehler(aktive: ActiveNotifications) -> None:
    """Spezifikation 26: eine Automation darf warning zu alarm machen."""
    aktive.put(automationsereignis(type=NotificationType.WARNING))
    aktive.put(automationsereignis(type=NotificationType.ALARM))

    zaehler = aktive.counts
    assert (zaehler.warning, zaehler.alarm) == (0, 1)
    assert zaehler.active == 1


def test_ueberschreiben_erzeugt_kein_zweites_tagesereignis(
    aktive: ActiveNotifications,
) -> None:
    """Zwischenaktualisierungen sind keine neuen Ereignisse (Spezifikation 75)."""
    aktive.put(automationsereignis(message="Leck erkannt"))
    aktive.put(automationsereignis(message="Leck bestaetigt"))

    assert aktive.counts.events_today == 1
    assert aktive.counts.active == 1


def test_ueberschreiben_liefert_den_vorherigen_stand(aktive: ActiveNotifications) -> None:
    erst = automationsereignis(message="Leck erkannt")
    aktive.put(erst)
    vorher = aktive.put(automationsereignis(message="Leck bestaetigt"))

    assert vorher is erst
    assert aktive.get(key_for(erst)).message == "Leck bestaetigt"


def test_abgeschlossenes_ereignis_gehoert_nicht_in_die_aktive_menge(
    aktive: ActiveNotifications,
) -> None:
    ereignis = regelereignis()
    ereignis.close(T0 + timedelta(minutes=1), CloseReason.CONDITION_CLEARED)

    with pytest.raises(ValueError, match="aktive"):
        aktive.put(ereignis)


# -- Tageszaehler -----------------------------------------------------------


def test_tageszaehler_steigt_mit_jedem_neuen_ereignis(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1"))
    aktive.put(regelereignis("rule_2"))
    aktive.close(rule_key("rule_1"), T0 + timedelta(minutes=1), CloseReason.CONDITION_CLEARED)

    # Das Beenden aendert den Tageszaehler nicht: das Ereignis fand statt.
    assert aktive.counts.events_today == 2


def test_ereignis_von_gestern_zaehlt_nicht_fuer_heute(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1", offset_minutes=-60 * 24))
    assert aktive.counts.events_today == 0
    assert aktive.counts.active == 1


def test_tageswechsel_setzt_den_zaehler_zurueck(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1"))
    assert aktive.counts.events_today == 1

    aktive.roll_day(T0 + timedelta(days=1))

    assert aktive.counts.events_today == 0
    # Die laufende Notification bleibt bestehen.
    assert aktive.counts.active == 1


def test_sofort_beendetes_ereignis_wird_mitgezaehlt(aktive: ActiveNotifications) -> None:
    ereignis = regelereignis()
    ereignis.close(T0, CloseReason.EXPIRED)
    aktive.note_closed_event(ereignis)

    assert aktive.counts.events_today == 1
    assert aktive.counts.active == 0


# -- Sortierung -------------------------------------------------------------


def test_aktive_notifications_neueste_zuerst(aktive: ActiveNotifications) -> None:
    """Spezifikation 52."""
    aktive.put(regelereignis("rule_1", message="alt", offset_minutes=0))
    aktive.put(regelereignis("rule_2", message="neu", offset_minutes=10))
    aktive.put(regelereignis("rule_3", message="mittel", offset_minutes=5))

    assert [e.message for e in aktive.events()] == ["neu", "mittel", "alt"]


def test_nach_typ_gefiltert_bleibt_die_sortierung(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1", type=NotificationType.ALARM, offset_minutes=0))
    aktive.put(regelereignis("rule_2", type=NotificationType.INFO, offset_minutes=5))
    aktive.put(regelereignis("rule_3", type=NotificationType.ALARM, offset_minutes=10))

    alarme = aktive.by_type(NotificationType.ALARM)
    assert [e.rule_id for e in alarme] == ["rule_3", "rule_1"]


# -- Massenoperationen ------------------------------------------------------


def test_schluessel_zu_regeln_finden(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1"))
    aktive.put(regelereignis("rule_2"))
    aktive.put(automationsereignis())

    treffer = aktive.keys_for_rules(["rule_1", "rule_9"])
    assert treffer == [rule_key("rule_1")]


def test_alle_beenden(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1"))
    aktive.put(automationsereignis())

    geschlossen = aktive.close_all(T0 + timedelta(minutes=1), CloseReason.ENTITY_REMOVED)

    assert len(geschlossen) == 2
    assert all(not e.active for e in geschlossen)
    assert aktive.counts.active == 0
    # Die Ereignisse haben stattgefunden und bleiben im Tageszaehler.
    assert aktive.counts.events_today == 2


# -- Wiederherstellung nach Neustart ---------------------------------------


def test_wiederherstellung_rekonstruiert_die_zaehler() -> None:
    """Spezifikation 37 und 45: aus einer Abfrage, nicht aus dem Log."""
    menge = ActiveNotifications()
    menge.restore(
        [
            regelereignis("rule_1", type=NotificationType.ALARM),
            regelereignis("rule_2", type=NotificationType.WARNING),
            automationsereignis(type=NotificationType.INFO),
        ],
        day_start=T0.replace(hour=0, minute=0, second=0, microsecond=0),
        events_today=17,
    )

    zaehler = menge.counts
    assert (zaehler.info, zaehler.warning, zaehler.alarm) == (1, 1, 1)
    assert zaehler.active == 3
    assert zaehler.events_today == 17


def test_wiederherstellung_ersetzt_den_bisherigen_zustand(
    aktive: ActiveNotifications,
) -> None:
    aktive.put(regelereignis("rule_alt"))

    aktive.restore(
        [regelereignis("rule_neu")],
        day_start=T0.replace(hour=0, minute=0, second=0, microsecond=0),
        events_today=3,
    )

    assert rule_key("rule_alt") not in aktive
    assert rule_key("rule_neu") in aktive
    assert aktive.counts.active == 1


def test_unvollstaendiger_datensatz_blockiert_die_wiederherstellung_nicht() -> None:
    """Ein beschaedigter Eintrag darf die uebrigen nicht mitreissen."""
    menge = ActiveNotifications()
    menge.restore(
        [make_event(), regelereignis("rule_1")],
        day_start=T0.replace(hour=0, minute=0, second=0, microsecond=0),
        events_today=0,
    )

    assert menge.counts.active == 1
    assert rule_key("rule_1") in menge


def test_zustand_als_dict(aktive: ActiveNotifications) -> None:
    aktive.put(regelereignis("rule_1", type=NotificationType.ALARM))
    daten = aktive.to_dict()

    assert daten["counts"]["alarm"] == 1
    assert daten["counts"]["active"] == 1
    assert len(daten["active"]) == 1
    assert daten["active"][0]["type"] == "alarm"


# -- Typwechsel an einer laufenden Notification (Issue 6) -------------------


def test_typwechsel_am_selben_objekt_bucht_richtig_um() -> None:
    """Issue 6: die Automations-API aendert das Ereignis an Ort und Stelle.

    ``async_update_automation`` setzt ``ereignis.type`` und reicht *dasselbe*
    Objekt an ``put``. Wer beim Abbuchen ``event.type`` liest, liest dann
    schon den neuen Wert und zieht vom falschen Zaehler ab. Der alte Typ bleibt
    dauerhaft zu hoch, der neue zu niedrig.
    """
    aktive = ActiveNotifications()
    ereignis = automationsereignis(type=NotificationType.INFO)
    aktive.put(ereignis)
    assert aktive.counts.to_dict() == Counts(info=1).to_dict()

    # Genau das, was die Engine tut: am Objekt aendern, dann erneut ablegen.
    ereignis.type = NotificationType.ALARM
    aktive.put(ereignis)

    zaehler = aktive.counts
    assert zaehler.info == 0, "der alte Typ wurde nicht abgebucht"
    assert zaehler.alarm == 1
    assert zaehler.active == 1


def test_beenden_nach_typwechsel_leert_den_zaehler() -> None:
    """Nach dem Wechsel muss auch das Beenden den richtigen Zaehler treffen."""
    aktive = ActiveNotifications()
    ereignis = automationsereignis(type=NotificationType.INFO)
    aktive.put(ereignis)

    ereignis.type = NotificationType.ALARM
    aktive.put(ereignis)
    aktive.close(key_for(ereignis), T0 + timedelta(minutes=1), CloseReason.DISMISSED)

    assert aktive.counts.to_dict() == Counts().to_dict()


def test_typwechsel_zaehlt_kein_zweites_ereignis_fuer_heute() -> None:
    """Ein Aendern ist kein neues Ereignis (Spezifikation 75)."""
    aktive = ActiveNotifications()
    aktive.roll_day(T0, events_today=0)

    ereignis = automationsereignis(type=NotificationType.INFO)
    aktive.put(ereignis)
    ereignis.type = NotificationType.WARNING
    aktive.put(ereignis)

    assert aktive.counts.events_today == 1


def test_mehrfacher_typwechsel_laeuft_nicht_aus_dem_takt() -> None:
    aktive = ActiveNotifications()
    ereignis = automationsereignis(type=NotificationType.INFO)

    for typ in (
        NotificationType.INFO,
        NotificationType.ALARM,
        NotificationType.WARNING,
        NotificationType.ALARM,
        NotificationType.INFO,
    ):
        ereignis.type = typ
        aktive.put(ereignis)

    assert aktive.counts.to_dict() == Counts(info=1).to_dict()
