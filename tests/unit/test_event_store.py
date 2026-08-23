"""Tests des SQLite-Event-Stores.

Deckt die Spezifikationsabschnitte 31 bis 34, 38, 39, 48, 59 bis 61 sowie die
Testfaelle L (Cleanup) und M (50.000 Ereignisse) ab.
"""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from custom_components.notification_center.notifications.models import (
    CloseReason,
    NotificationEvent,
    NotificationSource,
    NotificationType,
)
from custom_components.notification_center.storage.event_store import (
    EventQuery,
    EventStore,
)

from .conftest import T0, make_event

# -- Schema und Lebenszyklus ------------------------------------------------


def test_schema_wird_beim_oeffnen_angelegt(store: EventStore) -> None:
    assert store.total_count() == 0


def test_datenbank_wird_wiedergeoeffnet(tmp_path: Path) -> None:
    path = tmp_path / "events.db"
    first = EventStore(path)
    first.open()
    first.add(make_event(message="bleibt erhalten"))
    first.close()

    second = EventStore(path)
    second.open()
    try:
        assert second.total_count() == 1
        assert second.active_events()[0].message == "bleibt erhalten"
    finally:
        second.close()


def test_neuere_schemaversion_wird_abgelehnt(tmp_path: Path) -> None:
    """Ein Downgrade der Integration darf keine Daten beschaedigen."""
    path = tmp_path / "events.db"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version=99")
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="Schemaversion 99"):
        EventStore(path).open()


def test_zugriff_ohne_open_schlaegt_fehl(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="nicht geoeffnet"):
        EventStore(tmp_path / "events.db").total_count()


# -- Aktualisierung statt zweitem Datensatz (Spezifikation 31) --------------


def test_abschluss_aktualisiert_denselben_datensatz(store: EventStore) -> None:
    event = make_event()
    store.add(event)

    event.close(T0 + timedelta(minutes=12), CloseReason.CONDITION_CLEARED)
    store.update(event)

    assert store.total_count() == 1
    stored = store.get(event.event_id)
    assert stored is not None
    assert stored.active is False
    assert stored.duration() == pytest.approx(720.0)
    assert stored.close_reason is CloseReason.CONDITION_CLEARED


def test_aktive_ereignisse_sind_sofort_sichtbar(store: EventStore) -> None:
    """Spezifikation 33: aktive Ereignisse erscheinen unmittelbar im Log."""
    store.add(make_event())
    assert len(store.active_events()) == 1
    assert store.query(EventQuery()).total == 1


def test_rundreise_erhaelt_alle_felder(store: EventStore) -> None:
    event = make_event(
        title="Wohnzimmer",
        entity_id="sensor.temperatur",
        device_id="dev-1",
        area_id="wohnzimmer",
        rule_id="rule-1",
        rule_group_id="group-1",
        level=2,
    )
    store.add(event)

    stored = store.get(event.event_id)
    assert stored is not None
    assert stored.title == "Wohnzimmer"
    assert stored.entity_id == "sensor.temperatur"
    assert stored.device_id == "dev-1"
    assert stored.area_id == "wohnzimmer"
    assert stored.rule_id == "rule-1"
    assert stored.rule_group_id == "group-1"
    assert stored.level == 2
    assert stored.start_time == event.start_time


# -- Sortierung (Spezifikation 34) -----------------------------------------


def test_sortierung_neueste_zuerst_aktive_nicht_bevorzugt(store: EventStore) -> None:
    """Aktive Ereignisse werden nicht nach oben geschoben."""
    alt_aktiv = make_event(message="alt aktiv", offset_minutes=0)
    neu_beendet = make_event(message="neu beendet", offset_minutes=10)
    neu_beendet.close(T0 + timedelta(minutes=11), CloseReason.CONDITION_CLEARED)
    store.add(alt_aktiv)
    store.add(neu_beendet)

    reihenfolge = [event.message for event in store.query(EventQuery()).events]
    assert reihenfolge == ["neu beendet", "alt aktiv"]


# -- Filter und Suche (Spezifikation 59, 60) -------------------------------


@pytest.fixture
def gefuellter_store(store: EventStore) -> EventStore:
    store.add(
        make_event(
            message="Fenster Wohnzimmer geoeffnet",
            type=NotificationType.WARNING,
            entity_id="binary_sensor.fenster_wz",
            area_id="wohnzimmer",
            offset_minutes=0,
        )
    )
    store.add(
        make_event(
            message="Temperatur zu hoch",
            type=NotificationType.ALARM,
            entity_id="sensor.temperatur_wz",
            area_id="wohnzimmer",
            offset_minutes=10,
        )
    )
    store.add(
        make_event(
            message="Wasserleck im Keller",
            type=NotificationType.ALARM,
            source=NotificationSource.AUTOMATION,
            owner="automation.keller_wasserleck",
            notification_id="wasserleck",
            area_id="keller",
            offset_minutes=20,
        )
    )
    return store


def test_filter_nach_typ(gefuellter_store: EventStore) -> None:
    page = gefuellter_store.query(EventQuery(types=[NotificationType.ALARM]))
    assert page.total == 2
    assert all(event.type is NotificationType.ALARM for event in page.events)


def test_filter_nach_quelle(gefuellter_store: EventStore) -> None:
    page = gefuellter_store.query(EventQuery(sources=[NotificationSource.AUTOMATION]))
    assert page.total == 1
    assert page.events[0].owner == "automation.keller_wasserleck"


def test_filter_nach_bereich(gefuellter_store: EventStore) -> None:
    assert gefuellter_store.query(EventQuery(area_ids=["wohnzimmer"])).total == 2
    assert gefuellter_store.query(EventQuery(area_ids=["keller"])).total == 1


def test_filter_nach_entity(gefuellter_store: EventStore) -> None:
    page = gefuellter_store.query(EventQuery(entity_ids=["sensor.temperatur_wz"]))
    assert page.total == 1


def test_filter_nach_zeitraum(gefuellter_store: EventStore) -> None:
    page = gefuellter_store.query(EventQuery(start=T0 + timedelta(minutes=5)))
    assert page.total == 2


def test_filter_kombiniert(gefuellter_store: EventStore) -> None:
    page = gefuellter_store.query(
        EventQuery(types=[NotificationType.ALARM], area_ids=["wohnzimmer"])
    )
    assert page.total == 1
    assert page.events[0].message == "Temperatur zu hoch"


def test_suche_ist_gross_klein_unabhaengig(gefuellter_store: EventStore) -> None:
    assert gefuellter_store.query(EventQuery(search="KELLER")).total == 1
    assert gefuellter_store.query(EventQuery(search="keller")).total == 1


def test_suche_findet_umlaute_unabhaengig_von_der_schreibweise(store: EventStore) -> None:
    """SQLites LIKE kann keine Umlaute falten, darum das vorbereitete Suchfeld."""
    store.add(make_event(message="Tür Garage offen"))
    assert store.query(EventQuery(search="TÜR")).total == 1
    assert store.query(EventQuery(search="tür")).total == 1


def test_suche_beruecksichtigt_entity_und_owner(gefuellter_store: EventStore) -> None:
    assert gefuellter_store.query(EventQuery(search="binary_sensor.fenster_wz")).total == 1
    assert gefuellter_store.query(EventQuery(search="automation.keller")).total == 1


def test_platzhalter_in_der_suche_werden_maskiert(store: EventStore) -> None:
    store.add(make_event(message="100% Luftfeuchte"))
    store.add(make_event(message="Fenster offen", offset_minutes=1))

    assert store.query(EventQuery(search="%")).total == 1
    assert store.query(EventQuery(search="100%")).total == 1
    assert store.query(EventQuery(search="_")).total == 0


def test_active_only_filter(gefuellter_store: EventStore) -> None:
    events = gefuellter_store.query(EventQuery()).events
    events[0].close(T0 + timedelta(minutes=30), CloseReason.CONDITION_CLEARED)
    gefuellter_store.update(events[0])

    assert gefuellter_store.query(EventQuery(active_only=True)).total == 2


# -- Pagination (Spezifikation 61, Testfall M) -----------------------------


def test_pagination_liefert_gesamtzahl_und_weiter_flag(store: EventStore) -> None:
    for index in range(120):
        store.add(make_event(message=f"Ereignis {index}", offset_minutes=index))

    erste = store.query(EventQuery(limit=50))
    assert len(erste.events) == 50
    assert erste.total == 120
    assert erste.has_more is True
    assert erste.events[0].message == "Ereignis 119"

    letzte = store.query(EventQuery(limit=50, offset=100))
    assert len(letzte.events) == 20
    assert letzte.has_more is False


def test_limit_wird_gedeckelt(store: EventStore) -> None:
    for index in range(10):
        store.add(make_event(offset_minutes=index))
    assert len(store.query(EventQuery(limit=10_000)).events) == 10


def test_grosses_log_liefert_nur_eine_seite(store: EventStore) -> None:
    """Testfall M: 50.000 Ereignisse, das Frontend laedt trotzdem nur 50."""
    events = [
        NotificationEvent(
            message=f"Ereignis {index}",
            type=NotificationType.INFO,
            source=NotificationSource.ENTITY_RULE,
            start_time=T0 + timedelta(seconds=index),
            active=False,
            end_time=T0 + timedelta(seconds=index + 1),
        )
        for index in range(50_000)
    ]
    store.add_all(events)

    page = store.query(EventQuery())
    assert store.total_count() == 50_000
    assert len(page.events) == 50
    assert page.total == 50_000
    assert page.has_more is True


# -- Loeschen (Spezifikation 39) -------------------------------------------


def test_abgeschlossenes_ereignis_kann_geloescht_werden(store: EventStore) -> None:
    event = make_event()
    event.close(T0 + timedelta(minutes=1), CloseReason.CONDITION_CLEARED)
    store.add(event)

    assert store.delete(event.event_id) is True
    assert store.total_count() == 0


def test_aktives_ereignis_wird_nicht_geloescht(store: EventStore) -> None:
    """Eine laufende Notification darf ihren Datensatz nicht verlieren."""
    event = make_event()
    store.add(event)

    assert store.delete(event.event_id) is False
    assert store.total_count() == 1


def test_alle_loeschen_behaelt_aktive_ereignisse(store: EventStore) -> None:
    aktiv = make_event(message="laeuft noch")
    beendet = make_event(message="vorbei", offset_minutes=1)
    beendet.close(T0 + timedelta(minutes=2), CloseReason.CONDITION_CLEARED)
    store.add(aktiv)
    store.add(beendet)

    assert store.delete_all() == 1
    assert store.total_count() == 1
    assert store.active_events()[0].message == "laeuft noch"


# -- Cleanup (Spezifikation 38, Testfall L) --------------------------------


def test_cleanup_entfernt_nach_aufbewahrungsdauer(store: EventStore) -> None:
    alt = make_event(message="alt", offset_minutes=-60 * 24 * 40)
    alt.close(T0 - timedelta(days=39), CloseReason.CONDITION_CLEARED)
    neu = make_event(message="neu", offset_minutes=-60 * 24 * 2)
    neu.close(T0 - timedelta(days=1), CloseReason.CONDITION_CLEARED)
    store.add(alt)
    store.add(neu)

    assert store.cleanup(retention_days=30, max_events=1000, now=T0) == 1
    assert store.query(EventQuery()).events[0].message == "neu"


def test_cleanup_entfernt_aelteste_bei_mengenueberschreitung(store: EventStore) -> None:
    for index in range(10):
        event = make_event(message=f"Ereignis {index}", offset_minutes=index)
        event.close(T0 + timedelta(minutes=index, seconds=30), CloseReason.CONDITION_CLEARED)
        store.add(event)

    assert store.cleanup(retention_days=0, max_events=4, now=T0) == 6
    verbleibend = [event.message for event in store.query(EventQuery()).events]
    assert verbleibend == ["Ereignis 9", "Ereignis 8", "Ereignis 7", "Ereignis 6"]


def test_cleanup_unbegrenzte_aufbewahrung_beachtet_weiterhin_die_menge(store: EventStore) -> None:
    """Spezifikation 38: beide Grenzen gelten."""
    for index in range(5):
        event = make_event(message=f"Ereignis {index}", offset_minutes=-60 * 24 * 400 + index)
        event.close(T0 - timedelta(days=399), CloseReason.CONDITION_CLEARED)
        store.add(event)

    assert store.cleanup(retention_days=0, max_events=3, now=T0) == 2
    assert store.total_count() == 3


def test_cleanup_entfernt_niemals_aktive_ereignisse(store: EventStore) -> None:
    aktiv = make_event(message="sehr alt aber aktiv", offset_minutes=-60 * 24 * 400)
    store.add(aktiv)

    assert store.cleanup(retention_days=7, max_events=1, now=T0) == 0
    assert store.total_count() == 1


# -- Automations-Notifications (Spezifikation 25, 26) ----------------------


def test_automation_ereignis_wird_ueber_owner_und_id_gefunden(store: EventStore) -> None:
    event = make_event(
        message="Wasserleck",
        source=NotificationSource.AUTOMATION,
        owner="automation.keller",
        notification_id="leck",
    )
    store.add(event)

    gefunden = store.find_automation_event("automation.keller", "leck")
    assert gefunden is not None
    assert gefunden.event_id == event.event_id


def test_gleiche_id_verschiedener_owner_beeinflussen_sich_nicht(store: EventStore) -> None:
    """Testfall J."""
    for owner in ("automation.keller", "automation.dach"):
        store.add(
            make_event(
                message=f"Leck bei {owner}",
                source=NotificationSource.AUTOMATION,
                owner=owner,
                notification_id="leck",
            )
        )

    keller = store.find_automation_event("automation.keller", "leck")
    dach = store.find_automation_event("automation.dach", "leck")
    assert keller is not None and dach is not None
    assert keller.event_id != dach.event_id
    assert keller.message == "Leck bei automation.keller"


def test_beendetes_automation_ereignis_wird_nicht_mehr_gefunden(store: EventStore) -> None:
    event = make_event(
        source=NotificationSource.AUTOMATION,
        owner="automation.keller",
        notification_id="leck",
    )
    store.add(event)
    event.close(T0 + timedelta(minutes=1), CloseReason.DISMISSED)
    store.update(event)

    assert store.find_automation_event("automation.keller", "leck") is None


# -- Zaehlergrundlage ------------------------------------------------------


def test_count_since_zaehlt_ab_zeitpunkt(store: EventStore) -> None:
    for index in range(5):
        store.add(make_event(offset_minutes=index * 10))

    assert store.count_since(T0) == 5
    assert store.count_since(T0 + timedelta(minutes=25)) == 2
