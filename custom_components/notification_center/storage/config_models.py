"""Struktur der persistierten Konfiguration.

Ohne Home-Assistant-Importe, damit Aenderungen an der Konfiguration und die
Schemamigrationen ohne HA-Runtime testbar bleiben. Das Laden und Speichern
uebernimmt ``config_store.py``.

Die Konfiguration ist klein und wird selten geschrieben; sie liegt deshalb im
Home-Assistant-Storage als JSON. Die Ereignisse liegen dagegen in SQLite
(siehe ``event_store.py``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..const import (
    CONFIG_STORE_MINOR_VERSION,
    DEFAULT_ANALYSIS_DAYS,
    DEFAULT_MAX_EVENTS,
    DEFAULT_RETENTION_DAYS,
    MAX_EVENTS_OPTIONS,
    RETENTION_DAYS_OPTIONS,
)
from ..notifications.models import utc_now
from ..rules.models import Rule, RuleGroup


class ConfigError(ValueError):
    """Ungueltige Aenderung an der Konfiguration."""


# ---------------------------------------------------------------------------
# Ueberwachte Entities
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WatchedEntity:
    """Eine explizit zur Ueberwachung uebernommene Entity (Spezifikation 7).

    Geraet und Bereich werden mitgefuehrt, damit Historieneintraege auch dann
    filterbar bleiben, wenn die Entity spaeter umgehaengt oder entfernt wird.
    """

    entity_id: str
    added_at: datetime = field(default_factory=utc_now)
    device_id: str | None = None
    area_id: str | None = None
    #: Zeitpunkt der letzten Vorschlagsanalyse; None bedeutet noch nie.
    analyzed_at: datetime | None = None
    #: Entity, die diese hier ersetzt hat beziehungsweise ersetzt wurde.
    replaced_entity_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "added_at": self.added_at.isoformat(),
            "device_id": self.device_id,
            "area_id": self.area_id,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "replaced_entity_id": self.replaced_entity_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WatchedEntity:
        analyzed = data.get("analyzed_at")
        return cls(
            entity_id=data["entity_id"],
            added_at=datetime.fromisoformat(data["added_at"]),
            device_id=data.get("device_id"),
            area_id=data.get("area_id"),
            analyzed_at=datetime.fromisoformat(analyzed) if analyzed else None,
            replaced_entity_id=data.get("replaced_entity_id"),
        )


# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Settings:
    """Globale Einstellungen des Notification Centers."""

    #: Globaler Pause-Modus (Spezifikation 42). Nur in den Einstellungen.
    paused: bool = False
    #: 0 bedeutet unbegrenzt.
    retention_days: int = DEFAULT_RETENTION_DAYS
    max_events: int = DEFAULT_MAX_EVENTS
    analysis_days: int = DEFAULT_ANALYSIS_DAYS
    #: Der Einrichtungsassistent ist uebersprungbar (Spezifikation 67).
    setup_completed: bool = False

    def __post_init__(self) -> None:
        if self.retention_days not in RETENTION_DAYS_OPTIONS:
            raise ConfigError(f"Unzulaessige Aufbewahrungsdauer: {self.retention_days}")
        if self.max_events not in MAX_EVENTS_OPTIONS:
            raise ConfigError(f"Unzulaessige maximale Ereignisanzahl: {self.max_events}")
        if self.analysis_days <= 0:
            raise ConfigError("Analysezeitraum muss positiv sein")

    def to_dict(self) -> dict[str, Any]:
        return {
            "paused": self.paused,
            "retention_days": self.retention_days,
            "max_events": self.max_events,
            "analysis_days": self.analysis_days,
            "setup_completed": self.setup_completed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Settings:
        return cls(
            paused=data.get("paused", False),
            retention_days=data.get("retention_days", DEFAULT_RETENTION_DAYS),
            max_events=data.get("max_events", DEFAULT_MAX_EVENTS),
            analysis_days=data.get("analysis_days", DEFAULT_ANALYSIS_DAYS),
            setup_completed=data.get("setup_completed", False),
        )


# ---------------------------------------------------------------------------
# Gesamtdokument
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ConfigDocument:
    """Die vollstaendige persistierte Konfiguration einer Installation.

    Es gibt genau ein solches Dokument pro Home-Assistant-Installation
    (Spezifikation 4).
    """

    entities: dict[str, WatchedEntity] = field(default_factory=dict)
    rules: dict[str, Rule] = field(default_factory=dict)
    groups: dict[str, RuleGroup] = field(default_factory=dict)
    settings: Settings = field(default_factory=Settings)
    minor_version: int = CONFIG_STORE_MINOR_VERSION

    # -- Entities --------------------------------------------------------

    def add_entity(self, entity: WatchedEntity) -> None:
        """Uebernimmt eine Entity in die Ueberwachung. Vorhandene bleiben."""
        self.entities.setdefault(entity.entity_id, entity)

    def remove_entity(self, entity_id: str) -> list[str]:
        """Entfernt eine Entity samt ihrer Regeln (Spezifikation 78).

        Gibt die IDs der entfernten Regeln zurueck, damit der Aufrufer die
        zugehoerigen aktiven Notifications beenden kann. Die Historie bleibt
        unangetastet.
        """
        if entity_id not in self.entities:
            raise ConfigError(f"Entity wird nicht ueberwacht: {entity_id}")

        entfernte = [rule.rule_id for rule in self.rules.values() if rule.entity_id == entity_id]
        for rule_id in entfernte:
            del self.rules[rule_id]

        for group_id in [
            group.group_id for group in self.groups.values() if group.entity_id == entity_id
        ]:
            del self.groups[group_id]

        del self.entities[entity_id]
        return entfernte

    def replace_entity(self, old_entity_id: str, new_entity: WatchedEntity) -> list[str]:
        """Ersetzt eine ueberwachte Entity durch eine andere.

        Die Regeln wandern auf die neue Entity, ihre Regel-IDs bleiben dabei
        erhalten. Die Historie der alten Entity bleibt unveraendert und
        weiterhin ihr zugeordnet, damit alt und neu im Log unterscheidbar
        bleiben (Spezifikation 66).

        Zurueckgegeben werden die IDs der umgehaengten Regeln, deren aktive
        Notifications der Aufrufer beenden muss.
        """
        if old_entity_id not in self.entities:
            raise ConfigError(f"Entity wird nicht ueberwacht: {old_entity_id}")
        if new_entity.entity_id in self.entities:
            raise ConfigError(f"Entity wird bereits ueberwacht: {new_entity.entity_id}")

        umgehaengt: list[str] = []
        for rule_id, rule in list(self.rules.items()):
            if rule.entity_id == old_entity_id:
                self.rules[rule_id] = rule.with_entity(new_entity.entity_id)
                umgehaengt.append(rule_id)

        for group_id, group in list(self.groups.items()):
            if group.entity_id == old_entity_id:
                self.groups[group_id] = RuleGroup(
                    group_id=group.group_id,
                    entity_id=new_entity.entity_id,
                    name=group.name,
                    rules=tuple(self.rules[rule.rule_id] for rule in group.rules),
                )

        alt = self.entities.pop(old_entity_id)
        new_entity.replaced_entity_id = alt.entity_id
        self.entities[new_entity.entity_id] = new_entity
        return umgehaengt

    # -- Regeln ----------------------------------------------------------

    def add_rule(self, rule: Rule) -> None:
        if rule.entity_id not in self.entities:
            raise ConfigError(f"Regel verweist auf eine nicht ueberwachte Entity: {rule.entity_id}")
        self.rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> Rule:
        if rule_id not in self.rules:
            raise ConfigError(f"Unbekannte Regel: {rule_id}")
        rule = self.rules.pop(rule_id)
        if rule.group_id and rule.group_id in self.groups:
            verbleibend = tuple(
                item for item in self.groups[rule.group_id].rules if item.rule_id != rule_id
            )
            if verbleibend:
                gruppe = self.groups[rule.group_id]
                self.groups[rule.group_id] = RuleGroup(
                    group_id=gruppe.group_id,
                    entity_id=gruppe.entity_id,
                    name=gruppe.name,
                    rules=verbleibend,
                )
            else:
                del self.groups[rule.group_id]
        return rule

    def add_group(self, group: RuleGroup) -> None:
        if group.entity_id not in self.entities:
            raise ConfigError(
                f"Regelgruppe verweist auf eine nicht ueberwachte Entity: {group.entity_id}"
            )
        self.groups[group.group_id] = group
        for rule in group.rules:
            self.rules[rule.rule_id] = rule

    def rules_for(self, entity_id: str) -> list[Rule]:
        return [rule for rule in self.rules.values() if rule.entity_id == entity_id]

    @property
    def monitored_entity_ids(self) -> frozenset[str]:
        """Nur diese Entities werden auf State-Changes beobachtet.

        Grundlage der ereignisbasierten Ueberwachung: es wird niemals ueber
        alle Entities von Home Assistant iteriert (Spezifikation 6).
        """
        return frozenset(self.entities)

    # -- Serialisierung --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "minor_version": self.minor_version,
            "entities": [entity.to_dict() for entity in self.entities.values()],
            "rules": [rule.to_dict() for rule in self.rules.values()],
            "groups": [group.to_dict() for group in self.groups.values()],
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ConfigDocument:
        rules = {item["rule_id"]: Rule.from_dict(item) for item in data.get("rules", ())}
        groups = {item["group_id"]: RuleGroup.from_dict(item) for item in data.get("groups", ())}
        return cls(
            minor_version=data.get("minor_version", CONFIG_STORE_MINOR_VERSION),
            entities={
                item["entity_id"]: WatchedEntity.from_dict(item)
                for item in data.get("entities", ())
            },
            rules=rules,
            groups=groups,
            settings=Settings.from_dict(data.get("settings", {})),
        )

    @classmethod
    def empty(cls) -> ConfigDocument:
        return cls()


def migrate_config(data: dict[str, Any], from_minor: int) -> dict[str, Any]:
    """Hebt ein gespeichertes Konfigurationsdokument auf die aktuelle Version.

    Migrationen werden aufsteigend angewendet. Solange nur Version 1 existiert,
    ist nichts zu tun; die Funktion legt aber die Struktur fest, damit spaetere
    Aenderungen keine Sonderbehandlung brauchen.
    """
    if from_minor > CONFIG_STORE_MINOR_VERSION:
        raise ConfigError(
            f"Konfiguration hat Version {from_minor}, unterstuetzt wird hoechstens "
            f"{CONFIG_STORE_MINOR_VERSION}. Vermutlich wurde die Integration "
            "heruntergestuft."
        )

    # Kuenftige Migrationen folgen hier aufsteigend, zum Beispiel:
    # if from_minor < 2:
    #     data = _migrate_1_to_2(data)

    data["minor_version"] = CONFIG_STORE_MINOR_VERSION
    return data


def entities_from_ids(
    entity_ids: Iterable[str],
    *,
    device_ids: Mapping[str, str] | None = None,
    area_ids: Mapping[str, str] | None = None,
) -> list[WatchedEntity]:
    """Hilfsfunktion fuer die Uebernahme mehrerer Entities auf einmal."""
    device_ids = device_ids or {}
    area_ids = area_ids or {}
    return [
        WatchedEntity(
            entity_id=entity_id,
            device_id=device_ids.get(entity_id),
            area_id=area_ids.get(entity_id),
        )
        for entity_id in entity_ids
    ]
