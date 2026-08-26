"""Discovery: Entities finden, Metadaten sammeln, Historie befragen.

Diese Schicht beschafft Daten aus Home Assistant und reicht sie an die reinen
Module ``analyzer`` und ``suggestions`` weiter. Die Bewertung selbst findet
dort statt (Spezifikation 9: Discovery ist Backend-Logik, das Frontend zeigt
sie nur an).

Zur Historie (Spezifikation 11): analysiert werden standardmaessig die letzten
sieben Tage, und zwar **nur auf Anforderung**, nie im Hintergrund. Fuer
Sensoren mit ``state_class`` werden die Langzeitstatistiken von Home Assistant
verwendet: sie liegen stuendlich verdichtet vor und sind um Groessenordnungen
guenstiger als die Rohzustaende. Erst wenn es keine gibt, werden Rohzustaende
gelesen.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from ..const import DEFAULT_ANALYSIS_DAYS
from ..storage.config_models import ConfigDocument
from ..storage.config_store import ConfigStore
from .analyzer import (
    NumericProfile,
    StateProfile,
    analyze_numeric,
    analyze_states,
)
from .states import available_states
from .suggestions import Confidence, EntityMetadata, Suggestion, build_suggestions

_LOGGER = logging.getLogger(__name__)

#: Domains, die als Ueberwachungsgegenstand ueberhaupt sinnvoll sind.
SUPPORTED_DOMAINS = (
    "binary_sensor",
    "sensor",
    "cover",
    "lock",
    "climate",
    "water_heater",
    "vacuum",
    "device_tracker",
    "person",
    "alarm_control_panel",
    "switch",
    "light",
    "fan",
    "humidifier",
    "update",
)

#: Attribute, die keine auswertbare Groesse tragen (Spezifikation 16).
_UNUSABLE_ATTRIBUTES = frozenset(
    {
        "friendly_name",
        "icon",
        "entity_picture",
        "supported_features",
        "device_class",
        "state_class",
        "unit_of_measurement",
        "attribution",
        "assumed_state",
        "editable",
        "restored",
    }
)

#: Wie viele Werte eine Enum-artige Zeichenkette hoechstens tragen darf, damit
#: sie noch als Auswahlfeld taugt.
_MAX_ENUM_LENGTH = 32

#: Rueckblick fuer zusaetzlich beobachtete Zustaende. Grosszuegiger als der
#: Analysezeitraum: hier geht es nur um die Frage, welche Werte ueberhaupt
#: vorkommen, nicht um eine statistische Aussage.
STATE_LOOKBACK_DAYS = 30


class DiscoveryEngine:
    """Findet Entities und erzeugt Vorschlaege fuer sie."""

    def __init__(self, hass: HomeAssistant, config_store: ConfigStore) -> None:
        self._hass = hass
        self._config_store = config_store

    @property
    def _config(self) -> ConfigDocument:
        """Immer der aktuelle Stand; der Store ersetzt sein Dokument beim Laden."""
        return self._config_store.document

    # -- Entities finden -------------------------------------------------

    def discover_entities(
        self,
        *,
        domain: str | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Sucht Entities nach Typ, Name oder Entity-ID (Spezifikation 7).

        Die Vorschlagszahl beruht hier ausschliesslich auf Metadaten. Die
        Historie wird bewusst nicht angefasst: eine Suche darf nicht Dutzende
        Datenbankabfragen ausloesen.
        """
        begriff = (search or "").strip().lower()
        treffer: list[dict[str, Any]] = []

        for state in (
            self._hass.states.async_all(domain) if domain else self._hass.states.async_all()
        ):
            if state.domain not in SUPPORTED_DOMAINS:
                continue
            if begriff and begriff not in f"{state.entity_id} {state.name}".lower():
                continue

            treffer.append(self._describe(state))
            if len(treffer) >= limit:
                break

        treffer.sort(key=lambda eintrag: (not eintrag["monitored"], eintrag["name"].lower()))
        return treffer

    def _describe(self, state: State) -> dict[str, Any]:
        metadata = self.metadata_for(state.entity_id)
        ueberwacht = state.entity_id in self._config.entities
        regeln = len(self._config.rules_for(state.entity_id))

        eintrag: dict[str, Any] = {
            "entity_id": state.entity_id,
            "name": state.name,
            "domain": state.domain,
            "state": state.state,
            "device_class": metadata.device_class if metadata else None,
            "unit": metadata.unit if metadata else None,
            "device_id": metadata.device_id if metadata else None,
            "device_name": self._device_name(metadata.device_id if metadata else None),
            "area_id": metadata.area_id if metadata else None,
            "area_name": self._area_name(metadata.area_id if metadata else None),
            "monitored": ueberwacht,
            "rule_count": regeln,
        }

        # Bewusst *keine* Vorschlagszahl: sie liesse sich hier nur aus
        # Metadaten bilden, waehrend die tatsaechliche Liste zusaetzlich aus
        # der Historie entsteht. Eine Null neben zwei sichtbaren Vorschlaegen
        # ist schlechter als gar keine Angabe. Gemeldet wird nur, ob
        # ueberhaupt etwas zu erwarten ist.
        eintrag["has_suggestions"] = bool(
            not ueberwacht
            and metadata is not None
            and _ohne_unsichere(build_suggestions(metadata), False)
        )

        return eintrag

    # -- Metadaten -------------------------------------------------------

    def metadata_for(self, entity_id: str) -> EntityMetadata | None:
        """Sammelt alles, was ohne Datenbankzugriff bekannt ist."""
        state = self._hass.states.get(entity_id)
        if state is None:
            return None

        registry = er.async_get(self._hass)
        eintrag = registry.async_get(entity_id)
        device_id = eintrag.device_id if eintrag else None
        area_id = eintrag.area_id if eintrag else None

        if area_id is None and device_id is not None:
            geraet = dr.async_get(self._hass).async_get(device_id)
            area_id = geraet.area_id if geraet else None

        return EntityMetadata(
            entity_id=entity_id,
            domain=state.domain,
            state=state.state,
            name=state.name,
            device_class=state.attributes.get("device_class"),
            state_class=state.attributes.get("state_class"),
            unit=state.attributes.get("unit_of_measurement"),
            attributes=dict(state.attributes),
            device_id=device_id,
            area_id=area_id,
        )

    def usable_attributes(self, entity_id: str) -> list[dict[str, Any]]:
        """Attribute, die sich sinnvoll auswerten lassen (Spezifikation 16).

        Listen, Verschachtelungen und rein darstellende Angaben bleiben
        aussen vor: sie taugen nicht als Regelgrundlage und wuerden die
        Auswahl unbrauchbar lang machen.
        """
        state = self._hass.states.get(entity_id)
        if state is None:
            return []

        brauchbar: list[dict[str, Any]] = []
        for name, wert in state.attributes.items():
            if name in _UNUSABLE_ATTRIBUTES or name.startswith("_"):
                continue
            art = _attribute_kind(wert)
            if art is None:
                continue
            brauchbar.append({"name": name, "kind": art, "value": wert})

        return sorted(brauchbar, key=lambda eintrag: eintrag["name"])

    def available_states(self, entity_id: str) -> list[str]:
        """Auswaehlbare Zustandswerte einer Entity (Spezifikation 14).

        Der Regel-Editor bietet ein Auswahlfeld statt eines Textfelds. Die
        Werte stammen aus den Faehigkeiten der Entity und dem Katalog ihrer
        Domaene; beides ist unabhaengig davon, was die Entity bisher gezeigt
        hat. Beobachtetes ergaenzt die Liste nur.
        """
        state = self._hass.states.get(entity_id)
        if state is None:
            return []

        return available_states(
            domain=state.domain,
            current_state=state.state,
            attributes=state.attributes,
        )

    async def async_available_states(
        self, entity_id: str, *, days: int = STATE_LOOKBACK_DAYS
    ) -> list[str]:
        """Wie :meth:`available_states`, ergaenzt um beobachtete Werte.

        Die Historie wird nur zusaetzlich befragt. Liefert sie nichts, weil
        Home Assistant gerade erst gestartet ist, bleibt die Liste trotzdem
        vollstaendig.
        """
        state = self._hass.states.get(entity_id)
        if state is None:
            return []

        beobachtet: list[str] = []
        if "recorder" in self._hass.config.components:
            ende = dt_util.utcnow()
            beobachtet = await self._async_raw_states(entity_id, ende - timedelta(days=days), ende)

        return available_states(
            domain=state.domain,
            current_state=state.state,
            attributes=state.attributes,
            observed=beobachtet,
        )

    # -- Geraete ---------------------------------------------------------

    def get_device_suggestions(self, device_id: str) -> dict[str, Any]:
        """Alle Entities eines Geraets als Komfort-Gruppierung (Spez. 8).

        Geraete dienen nur der Uebersicht. Die Konfigurationseinheit bleibt
        die einzelne Entity; deshalb wird hier je Entity ausgewiesen, was
        moeglich ist.
        """
        registry = er.async_get(self._hass)
        geraet = dr.async_get(self._hass).async_get(device_id)

        eintraege = []
        for eintrag in er.async_entries_for_device(
            registry, device_id, include_disabled_entities=False
        ):
            state = self._hass.states.get(eintrag.entity_id)
            if state is None or state.domain not in SUPPORTED_DOMAINS:
                continue
            eintraege.append(self._describe(state))

        return {
            "device_id": device_id,
            "name": geraet.name_by_user or geraet.name if geraet else device_id,
            "area_id": geraet.area_id if geraet else None,
            "area_name": self._area_name(geraet.area_id if geraet else None),
            "entities": eintraege,
        }

    # -- Vorschlaege -----------------------------------------------------

    async def async_get_entity_suggestions(
        self,
        entity_id: str,
        *,
        analysis_days: int | None = None,
        include_uncertain: bool = False,
    ) -> list[Suggestion]:
        """Vorschlaege einer Entity, einschliesslich Historienanalyse.

        Wird beim Hinzufuegen einmal aufgerufen und spaeter nur auf
        ausdrueckliche Anforderung. Es gibt keine laufende
        Hintergrundanalyse (Spezifikation 11).

        Vorschlaege geringer Sicherheit bleiben aussen vor: ein Vorschlag, der
        bloss auf einem Wort im Namen beruht, kostet mehr Vertrauen als er
        einbringt. Ueber ``include_uncertain`` sind sie weiterhin erreichbar.
        """
        metadata = self.metadata_for(entity_id)
        if metadata is None:
            return []

        tage = analysis_days or self._config.settings.analysis_days or DEFAULT_ANALYSIS_DAYS
        numerisch, zustaende = await self.async_analyze_history(entity_id, days=tage)

        vorschlaege = build_suggestions(
            metadata,
            numeric_profile=numerisch,
            state_profile=zustaende,
            analysis_days=tage,
        )
        return _ohne_unsichere(vorschlaege, include_uncertain)

    async def async_analyze_history(
        self, entity_id: str, *, days: int = DEFAULT_ANALYSIS_DAYS
    ) -> tuple[NumericProfile | None, StateProfile | None]:
        """Liest und verdichtet die Historie einer einzelnen Entity."""
        if "recorder" not in self._hass.config.components:
            _LOGGER.debug("Kein Recorder verfuegbar, keine Historienanalyse")
            return (None, None)

        ende = dt_util.utcnow()
        beginn = ende - timedelta(days=days)
        metadata = self.metadata_for(entity_id)

        if metadata is not None and metadata.state_class:
            werte = await self._async_statistics(entity_id, beginn, ende)
            if werte:
                return (analyze_numeric(werte, span_days=days), None)

        zustaende = await self._async_raw_states(entity_id, beginn, ende)
        if not zustaende:
            return (None, None)

        zahlen = [wert for wert in (_als_zahl(z) for z in zustaende) if wert is not None]
        if len(zahlen) >= len(zustaende) / 2:
            return (analyze_numeric(zahlen, span_days=days), None)

        return (None, analyze_states(zustaende, span_days=days))

    async def _async_statistics(
        self, entity_id: str, start: datetime, end: datetime
    ) -> list[float]:
        """Stundenwerte aus den Langzeitstatistiken.

        Deutlich guenstiger als Rohzustaende: bei sieben Tagen sind es
        hoechstens 168 Zeilen statt womoeglich Zehntausender.
        """
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.statistics import statistics_during_period

        def _lesen() -> dict[str, list[dict[str, Any]]]:
            return statistics_during_period(
                self._hass,
                start,
                end,
                {entity_id},
                "hour",
                None,
                {"mean", "min", "max"},
            )

        try:
            ergebnis = await get_instance(self._hass).async_add_executor_job(_lesen)
        except Exception:
            _LOGGER.exception("Langzeitstatistik fuer %s nicht lesbar", entity_id)
            return []

        reihen = ergebnis.get(entity_id, [])
        werte: list[float] = []
        for zeile in reihen:
            mittel = zeile.get("mean")
            if mittel is not None:
                werte.append(float(mittel))
        return werte

    async def _async_raw_states(self, entity_id: str, start: datetime, end: datetime) -> list[str]:
        """Rohzustaende, ohne Attribute und nur bei erheblichen Aenderungen."""
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.history import state_changes_during_period

        def _lesen() -> dict[str, list[State]]:
            return state_changes_during_period(
                self._hass,
                start,
                end,
                entity_id,
                no_attributes=True,
                include_start_time_state=False,
            )

        try:
            ergebnis = await get_instance(self._hass).async_add_executor_job(_lesen)
        except Exception:
            _LOGGER.exception("Historie fuer %s nicht lesbar", entity_id)
            return []

        return [
            zustand.state
            for zustand in ergebnis.get(entity_id, [])
            if zustand.state not in ("unknown", "unavailable", "")
        ]

    # -- Hilfsmittel -----------------------------------------------------

    def _device_name(self, device_id: str | None) -> str | None:
        if device_id is None:
            return None
        geraet = dr.async_get(self._hass).async_get(device_id)
        if geraet is None:
            return None
        return geraet.name_by_user or geraet.name

    def _area_name(self, area_id: str | None) -> str | None:
        if area_id is None:
            return None
        bereich = ar.async_get(self._hass).async_get_area(area_id)
        return bereich.name if bereich else None


def _ohne_unsichere(suggestions: list[Suggestion], include_uncertain: bool) -> list[Suggestion]:
    if include_uncertain:
        return suggestions
    return [vorschlag for vorschlag in suggestions if vorschlag.confidence is not Confidence.LOW]


def _attribute_kind(value: Any) -> str | None:
    """Bestimmt, ob und wie ein Attribut auswertbar ist."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "numeric"
    if isinstance(value, str) and 0 < len(value) <= _MAX_ENUM_LENGTH:
        return "text"
    return None


def _als_zahl(wert: str) -> float | None:
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None
