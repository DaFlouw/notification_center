"""Laufzeitcontainer der Integration.

Haelt die gemeinsam genutzten Bausteine (Konfiguration, Event Store, Rule
Engine und Notification-Engine) zusammen und regelt deren Start und Stopp. Es
gibt genau eine Instanz pro Home-Assistant-Installation (Spezifikation 4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .discovery.engine import DiscoveryEngine
from .notifications.engine import NotificationEngine
from .notifications.models import CloseReason
from .rules.engine import RuleEngine
from .rules.intents import NotificationIntent
from .rules.models import Rule, RuleGroup
from .storage.config_models import ConfigDocument, WatchedEntity
from .storage.config_store import ConfigStore
from .storage.event_store_async import AsyncEventStore

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationCenterRuntime:
    """Alles, was zur Laufzeit gebraucht wird."""

    hass: HomeAssistant
    config_store: ConfigStore
    event_store: AsyncEventStore
    rule_engine: RuleEngine = field(init=False)
    notification_engine: NotificationEngine = field(init=False)
    discovery: DiscoveryEngine = field(init=False)

    def __post_init__(self) -> None:
        self.notification_engine = NotificationEngine(
            self.hass, self.event_store, self.config_store
        )
        self.rule_engine = RuleEngine(
            self.hass,
            self.config_store,
            self._async_handle_intents,
        )
        self.discovery = DiscoveryEngine(self.hass, self.config_store)

    @classmethod
    def create(cls, hass: HomeAssistant) -> NotificationCenterRuntime:
        return cls(
            hass=hass,
            config_store=ConfigStore(hass),
            event_store=AsyncEventStore(hass),
        )

    @property
    def config(self) -> ConfigDocument:
        return self.config_store.document

    # -- Lebenszyklus ----------------------------------------------------

    async def async_start(self) -> None:
        """Laedt die Ablagen und startet beide Engines."""
        await self.config_store.async_load()
        await self.event_store.async_open()

        # Aufraeumen einmal beim Start: das Log kann waehrend eines langen
        # Stillstands ueber seine Grenzen gewachsen sein. Danach geschieht es
        # beim Tageswechsel, nicht in einer Schleife.
        entfernt = await self.event_store.async_cleanup(
            retention_days=self.config.settings.retention_days,
            max_events=self.config.settings.max_events,
        )
        if entfernt:
            _LOGGER.debug("Beim Start %s alte Ereignisse entfernt", entfernt)

        await self.notification_engine.async_start()
        # Die Reihenfolge traegt: erst die offenen Meldungen wiederherstellen,
        # dann die Rule Engine damit gleichziehen lassen. Sonst weiss sie
        # nicht, welche Regeln bereits erfuellt sind, und beendet nichts mehr.
        await self.rule_engine.async_start(
            active_rules=self.notification_engine.active_rule_starts()
        )

    async def async_stop(self) -> None:
        """Haelt die Engines an, sichert und schliesst die Ablagen."""
        await self.rule_engine.async_stop()
        await self.notification_engine.async_stop()
        await self.config_store.async_shutdown()
        await self.event_store.async_close()

    # -- Konfigurationsaenderungen ---------------------------------------

    async def async_config_changed(self) -> None:
        """Nach jeder Aenderung an Entities oder Regeln aufzurufen."""
        self.config_store.schedule_save()
        self.rule_engine.async_refresh_tracking()
        # Muss ausserhalb von async_refresh_tracking geschehen: eine neue Regel
        # auf einer bereits ueberwachten Entity aendert die Menge der
        # beobachteten Entities nicht, und refresh_tracking kehrt dann sofort
        # zurueck.
        self.rule_engine.async_seed_rule_states()

    async def async_remove_entity(self, entity_id: str) -> None:
        """Entfernt eine Entity aus der Ueberwachung (Spezifikation 78)."""
        entfernte_regeln = self.config.remove_entity(entity_id)
        await self.notification_engine.async_close_rules(
            entfernte_regeln, CloseReason.ENTITY_REMOVED
        )
        await self.async_config_changed()

    async def async_replace_entity(self, old_entity_id: str, new_entity_id: str) -> None:
        """Ersetzt eine ueberwachte Entity (Spezifikation 66).

        Die Regeln wandern mit und behalten ihre IDs. Laufende Notifications
        der alten Entity werden abgeschlossen, ihre Historie bleibt der alten
        Entity zugeordnet.

        Eine unbekannte Kennung wird abgelehnt. Sonst nimmt ein Tippfehler die
        richtige Entity aus der Ueberwachung und haengt alle ihre Regeln an
        etwas, das nie einen Zustand meldet -- die Ueberwachung hoert
        stillschweigend auf zu arbeiten.
        """
        self._pruefe_entity(new_entity_id)

        metadata = self.discovery.metadata_for(new_entity_id)
        neu = WatchedEntity(
            entity_id=new_entity_id,
            device_id=metadata.device_id if metadata else None,
            area_id=metadata.area_id if metadata else None,
        )

        umgehaengt = self.config.replace_entity(old_entity_id, neu)
        await self.notification_engine.async_close_rules(umgehaengt, CloseReason.ENTITY_REPLACED)
        await self.async_config_changed()

    def _pruefe_entity(self, entity_id: str) -> None:
        """Stellt sicher, dass es die Entity ueberhaupt gibt.

        Gefragt wird nicht nur die Zustandsmaschine, sondern auch die
        Entity-Registry: eine Entity kann voruebergehend nicht geladen sein
        und traegt dann keinen Zustand, gehoert aber weiterhin zur Anlage.
        Nur was in beiden fehlt, ist ein Tippfehler.
        """
        if self.hass.states.get(entity_id) is not None:
            return
        if er.async_get(self.hass).async_get(entity_id) is not None:
            return
        raise ValueError(f"Die Entity {entity_id} gibt es nicht.")

    async def async_save_rule(self, rule: Rule) -> None:
        """Legt eine Regel an oder ersetzt sie.

        Beim Ersetzen wird eine laufende Notification beendet: sie beruht auf
        der alten Bedingung und waere sonst nicht mehr nachvollziehbar.
        """
        bestand = self.config.rules.get(rule.rule_id)
        self.config.add_rule(rule)

        if bestand is not None:
            await self.notification_engine.async_close_rules(
                [rule.rule_id], CloseReason.RULE_DISABLED
            )

        await self.async_config_changed()

    async def async_delete_rule(self, rule_id: str) -> None:
        """Entfernt eine Regel und beendet ihre Notification."""
        self.config.remove_rule(rule_id)
        await self.notification_engine.async_close_rules([rule_id], CloseReason.RULE_DISABLED)
        await self.async_config_changed()

    async def async_save_group(self, group: RuleGroup) -> None:
        """Legt eine Eskalationsgruppe an oder ersetzt sie."""
        vorher = self.config.groups.get(group.group_id)
        if vorher is not None:
            await self.notification_engine.async_close_rules(
                [regel.rule_id for regel in vorher.rules], CloseReason.RULE_DISABLED
            )
            self.rule_engine.async_forget_group(group.group_id)

        self.config.add_group(group)
        await self.async_config_changed()

    async def async_disable_rule(self, rule_id: str) -> None:
        """Deaktiviert eine Regel und beendet ihre Notification (Spez. 77)."""
        regel = self.config.rules.get(rule_id)
        if regel is None or not regel.enabled:
            return

        regel.enabled = False
        await self.notification_engine.async_close_rules([rule_id], CloseReason.RULE_DISABLED)
        await self.async_config_changed()

    async def async_set_paused(self, paused: bool) -> None:
        """Schaltet den globalen Pause-Modus (Spezifikation 42, 43).

        Beim Fortsetzen werden die aktuellen Zustaende neu bewertet, damit
        Notifications entstehen, die waehrend der Pause faellig geworden sind.
        Bestehende aktive Notifications bleiben waehrend der Pause unberuehrt.
        """
        if self.config.settings.paused == paused:
            return

        self.config.settings.paused = paused
        self.config_store.schedule_save()

        if not paused:
            await self.rule_engine.async_evaluate_all()

    # -- Verbindung der Engines ------------------------------------------

    async def _async_handle_intents(self, intents: list[NotificationIntent]) -> None:
        """Reicht die Absichten der Rule Engine an die Notification-Engine."""
        await self.notification_engine.async_apply(intents)
