"""Verbindet Home-Assistant-Zustandsaenderungen mit der Regelauswertung.

Diese Schicht ist bewusst duenn: sie beschafft Zustaende, ruft die reine
Auswertung auf und reicht deren Absichten weiter. Alle Entscheidungen liegen
in ``evaluator.py`` und ``intents.py``.

Die Ueberwachung ist vollstaendig ereignisbasiert (Spezifikation 6). Es wird
ausschliesslich auf die explizit uebernommenen Entities gehoert; es gibt keine
Schleife ueber alle Entities und kein Polling. Zeitgesteuerte Auswertungen
entstehen nur fuer Regeln, deren Bedingung bereits anliegt.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime

from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from ..notifications.models import CloseReason
from ..storage.config_models import ConfigDocument
from ..storage.config_store import ConfigStore
from .evaluator import (
    GroupState,
    Phase,
    RuleState,
    evaluate_group,
    evaluate_rule,
    hold_met,
)
from .intents import IntentKind, NotificationIntent, intents_for_group, intents_for_rule
from .models import EntitySnapshot, Rule, RuleGroup

_LOGGER = logging.getLogger(__name__)

#: Wird mit den anstehenden Aenderungen aufgerufen.
Dispatcher = Callable[[list[NotificationIntent]], Awaitable[None]]


class RuleEngine:
    """Wertet Regeln aus, sobald sich eine ueberwachte Entity aendert."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_store: ConfigStore,
        dispatch: Dispatcher,
    ) -> None:
        self._hass = hass
        self._config_store = config_store
        self._dispatch = dispatch

        self._rule_states: dict[str, RuleState] = {}
        self._group_states: dict[str, GroupState] = {}
        self._timers: dict[str, CALLBACK_TYPE] = {}

        self._unsub_states: CALLBACK_TYPE | None = None
        self._tracked: frozenset[str] = frozenset()

    @property
    def _config(self) -> ConfigDocument:
        """Immer der aktuelle Stand.

        Der Store ersetzt sein Dokument beim Laden; eine festgehaltene
        Referenz waere nach einem Neustart der Integration veraltet.
        """
        return self._config_store.document

    # -- Lebenszyklus ----------------------------------------------------

    async def async_start(self) -> None:
        self.async_refresh_tracking()
        self.async_restore_timing()
        await self.async_evaluate_all()

    async def async_stop(self) -> None:
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None
        self._tracked = frozenset()
        self._cancel_all_timers()

    @callback
    def async_refresh_tracking(self) -> None:
        """Abonniert genau die ueberwachten Entities.

        Wird nach jeder Konfigurationsaenderung aufgerufen. Bleibt die Menge
        gleich, passiert nichts: ein unnoetiges Neuabonnieren wuerde nur
        Arbeit erzeugen.
        """
        gewuenscht = self._config.monitored_entity_ids
        if gewuenscht == self._tracked:
            return

        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None

        if gewuenscht:
            self._unsub_states = async_track_state_change_event(
                self._hass, list(gewuenscht), self._handle_state_event
            )

        self._tracked = gewuenscht
        _LOGGER.debug("Ueberwache %s Entities", len(gewuenscht))

        # Timer verwaister Regeln aufraeumen.
        for key in list(self._timers):
            if key not in self._config.rules and key not in self._config.groups:
                self._cancel_timer(key)

    @callback
    def async_restore_timing(self) -> None:
        """Setzt Zeitbedingungen nach einem Neustart auf den echten Beginn.

        Ohne das begaenne jede Wartezeit beim Start von vorn: ein seit 10:00
        offenes Fenster mit einer 15-Minuten-Regel wuerde nach einem Neustart
        um 10:10 erst um 10:25 melden statt um 10:15.

        Grundlage ist ``last_changed`` der Entity. Liegt die Bedingung schon
        laenger an als die Wartezeit, entsteht die Notification sofort
        (Spezifikation 37).
        """
        for entity_id in self._config.monitored_entity_ids:
            snapshot = self._snapshot(entity_id)
            if snapshot is None:
                continue

            for rule in self._all_rules_for(entity_id):
                if not rule.enabled or not rule.duration_seconds:
                    continue
                if not hold_met(rule, snapshot):
                    continue

                zustand = self._state_for(rule)
                if zustand.condition_since is None:
                    zustand.condition_since = snapshot.last_changed
                    zustand.last_state = snapshot.state
                    zustand.phase = Phase.PENDING

    @callback
    def async_seed_rule_states(self) -> None:
        """Gibt neuen Regeln den aktuellen Zustand ihrer Entity als Ausgangspunkt.

        Eine Flankenregel (*Zustand aendert sich zu*) vergleicht den neuen mit
        dem zuletzt gesehenen Zustand. Ohne Ausgangspunkt gibt es keinen
        Vergleich: die erste Auswertung diente bisher nur dazu, ihn zu setzen,
        und die Flanke, die sie ausgeloest hat, ging dabei verloren. Wer eine
        Regel anlegte und sie gleich ausprobierte, sah nichts.

        Gesetzt wird ausschliesslich ``last_state``. Phase und Beginn bleiben
        unberuehrt, damit eine Regel, deren Bedingung schon anliegt,
        weiterhin sofort meldet.

        Liegt der Zustand bereits im Zielzustand, entsteht *keine* Meldung --
        richtig so: es hat kein Wechsel stattgefunden.
        """
        for entity_id in self._config.monitored_entity_ids:
            snapshot = None
            for rule in self._all_rules_for(entity_id):
                zustand = self._state_for(rule)
                if zustand.last_state is not None:
                    continue
                if snapshot is None:
                    snapshot = self._snapshot(entity_id)
                    if snapshot is None:
                        break
                zustand.last_state = snapshot.state

    def _all_rules_for(self, entity_id: str) -> list[Rule]:
        """Alle Regeln einer Entity, auch die aus Gruppen."""
        return [rule for rule in self._config.rules.values() if rule.entity_id == entity_id]

    def _state_for(self, rule: Rule) -> RuleState:
        """Der mitgefuehrte Zustand einer Regel, egal ob einzeln oder in Gruppe."""
        if rule.group_id is not None:
            gruppe = self._group_states.setdefault(
                rule.group_id, GroupState(group_id=rule.group_id)
            )
            return gruppe.rule_states.setdefault(rule.rule_id, RuleState(rule_id=rule.rule_id))
        return self._rule_states.setdefault(rule.rule_id, RuleState(rule_id=rule.rule_id))

    # -- Ereignisse ------------------------------------------------------

    @callback
    def _handle_state_event(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        if event.data["new_state"] is None:
            # Entity wurde entfernt; das behandelt die Konfigurationsebene.
            return
        self._evaluate_entity(entity_id, dt_util.utcnow())

    @callback
    def _handle_timer(self, key: str, entity_id: str) -> None:
        """Ausloeser einer Zeitbedingung oder einer automatischen Enddauer."""
        self._timers.pop(key, None)
        self._evaluate_entity(entity_id, dt_util.utcnow())

    # -- Auswertung ------------------------------------------------------

    async def async_evaluate_all(self) -> None:
        """Wertet alle ueberwachten Entities einmal aus.

        Wird beim Start und nach dem Ende einer Pause gebraucht
        (Spezifikation 43). Im laufenden Betrieb geschieht nichts dergleichen.
        """
        jetzt = dt_util.utcnow()
        for entity_id in self._config.monitored_entity_ids:
            self._evaluate_entity(entity_id, jetzt)

    @callback
    def _evaluate_entity(self, entity_id: str, now: datetime) -> None:
        """Wertet alle Regeln einer Entity aus und stoesst die Absichten an.

        Die Auswertung selbst ist synchron und guenstig. Nur wenn sich
        tatsaechlich etwas aendert, entsteht eine Aufgabe: bei einem
        Messwert ohne Folgen faellt keine Arbeit an.
        """
        if self._config.settings.paused:
            return

        snapshot = self._snapshot(entity_id)
        if snapshot is None:
            return

        absichten: list[NotificationIntent] = []
        absichten.extend(self._evaluate_groups(entity_id, snapshot, now))
        absichten.extend(self._evaluate_single_rules(entity_id, snapshot, now))

        if absichten:
            self._hass.async_create_task(self._dispatch(absichten))

    def _evaluate_groups(
        self, entity_id: str, snapshot: EntitySnapshot, now: datetime
    ) -> list[NotificationIntent]:
        absichten: list[NotificationIntent] = []

        for group in self._groups_for(entity_id):
            try:
                zustand = self._group_states.setdefault(
                    group.group_id, GroupState(group_id=group.group_id)
                )
                ergebnis = evaluate_group(group, snapshot, zustand, now)
                absichten.extend(intents_for_group(group, snapshot, ergebnis))

                faellig = [
                    auswertung.fire_at
                    for auswertung in ergebnis.evaluations.values()
                    if auswertung.fire_at is not None
                ]
                self._schedule(group.group_id, entity_id, min(faellig) if faellig else None)
            except Exception:
                # Ein Fehler in einer Gruppe darf die uebrigen Regeln nicht
                # anhalten (Spezifikation 82).
                _LOGGER.exception("Fehler beim Auswerten der Regelgruppe %s", group.group_id)

        return absichten

    def _evaluate_single_rules(
        self, entity_id: str, snapshot: EntitySnapshot, now: datetime
    ) -> list[NotificationIntent]:
        absichten: list[NotificationIntent] = []

        for rule in self._single_rules_for(entity_id):
            try:
                ergebnis = evaluate_rule(rule, snapshot, self._state_for(rule), now)
                absichten.extend(intents_for_rule(rule, snapshot, ergebnis))
                self._schedule(rule.rule_id, entity_id, ergebnis.fire_at)
            except Exception:
                _LOGGER.exception("Fehler beim Auswerten der Regel %s", rule.rule_id)

        return absichten

    # -- Konfigurationsaenderungen ---------------------------------------

    @callback
    def async_forget_rules(
        self, rule_ids: Iterable[str], reason: CloseReason
    ) -> list[NotificationIntent]:
        """Beendet die Notifications entfernter oder abgeschalteter Regeln.

        Wird beim Deaktivieren einer Regel und beim Entfernen oder Ersetzen
        einer Entity gebraucht (Spezifikation 66, 77, 78).
        """
        absichten: list[NotificationIntent] = []

        for rule_id in rule_ids:
            self._cancel_timer(rule_id)
            zustand = self._rule_states.pop(rule_id, None)
            if zustand is None or not zustand.is_satisfied:
                continue
            regel = self._config.rules.get(rule_id)
            if regel is None:
                continue
            snapshot = self._snapshot(regel.entity_id)
            if snapshot is None:
                continue
            absichten.append(
                NotificationIntent(
                    kind=IntentKind.STOP,
                    rule=regel,
                    snapshot=snapshot,
                    reason=reason,
                )
            )

        return absichten

    @callback
    def async_forget_group(self, group_id: str) -> None:
        self._cancel_timer(group_id)
        self._group_states.pop(group_id, None)

    # -- Hilfsmittel -----------------------------------------------------

    def _groups_for(self, entity_id: str) -> list[RuleGroup]:
        return [group for group in self._config.groups.values() if group.entity_id == entity_id]

    def _single_rules_for(self, entity_id: str) -> list[Rule]:
        """Alle Regeln der Entity, die zu keiner Gruppe gehoeren.

        Gruppenmitglieder werden ueber ihre Gruppe ausgewertet, damit die
        Eskalationslogik greift.
        """
        return [
            rule
            for rule in self._config.rules.values()
            if rule.entity_id == entity_id and rule.group_id is None
        ]

    def _snapshot(self, entity_id: str) -> EntitySnapshot | None:
        """Baut die HA-freie Momentaufnahme fuer die Auswertung."""
        state = self._hass.states.get(entity_id)
        if state is None:
            return None

        registry = er.async_get(self._hass)
        eintrag = registry.async_get(entity_id)
        device_id = eintrag.device_id if eintrag else None
        area_id = eintrag.area_id if eintrag else None

        # Faellt die Entity nicht selbst in einen Bereich, gilt der Bereich
        # ihres Geraets.
        if area_id is None and device_id is not None:
            geraet = dr.async_get(self._hass).async_get(device_id)
            area_id = geraet.area_id if geraet else None

        return EntitySnapshot(
            entity_id=entity_id,
            state=state.state,
            last_changed=state.last_changed,
            attributes=state.attributes,
            name=state.name,
            unit=state.attributes.get("unit_of_measurement"),
            device_id=device_id,
            area_id=area_id,
        )

    @callback
    def _schedule(self, key: str, entity_id: str, fire_at: datetime | None) -> None:
        """Setzt oder loescht den Timer einer Regel beziehungsweise Gruppe."""
        self._cancel_timer(key)
        if fire_at is None:
            return

        @callback
        def _ausloesen(_now: datetime) -> None:
            self._handle_timer(key, entity_id)

        self._timers[key] = async_track_point_in_utc_time(self._hass, _ausloesen, fire_at)

    @callback
    def _cancel_timer(self, key: str) -> None:
        unsub = self._timers.pop(key, None)
        if unsub is not None:
            unsub()

    @callback
    def _cancel_all_timers(self) -> None:
        for key in list(self._timers):
            self._cancel_timer(key)
