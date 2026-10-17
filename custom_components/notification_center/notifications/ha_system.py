"""Uebernahme der persistenten Benachrichtigungen von Home Assistant.

Das sind die Meldungen, die in der Seitenleiste hinter der Glocke liegen:
fehlgeschlagene Anmeldeversuche, ungueltige Konfiguration, Integrationen, die
neu eingerichtet werden muessen, Sicherungen. Sie entstehen voellig
unabhaengig vom Notification Center -- hier werden sie nur mitgefuehrt, damit
Dashboard, Historie und Zaehler das vollstaendige Bild zeigen.

Die Richtung ist bewusst einseitig. Home Assistant meldet, wir zeigen; endet
die Meldung dort, endet sie hier. Umgekehrt verwirft das Notification Center
nichts im Namen von Home Assistant: die Glocke bleibt die Stelle, an der man
eine Systemnachricht abtut.

Reparaturen und Updates gehoeren nicht dazu. Sie sind eigene Mechanismen mit
eigenen Oberflaechen; Updates lassen sich ausserdem schon heute mit einer
gewoehnlichen Regel auf die ``update``-Entities ueberwachen.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.components import persistent_notification as pn
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback

from ..storage.config_store import ConfigStore
from .engine import NotificationEngine
from .models import CloseReason, NotificationType

_LOGGER = logging.getLogger(__name__)

#: Laenge, auf die ein Meldungstext gekuerzt wird.
#:
#: Eine persistente Benachrichtigung darf mehrere Absaetze Markdown
#: enthalten -- "ungueltige Konfiguration" listet schon mal ein halbes
#: Protokoll auf. Eine Zeile im Dashboard ist dafuer der falsche Ort. Der
#: vollstaendige Text bleibt in Home Assistant selbst stehen.
MAX_MESSAGE_LENGTH = 300


class HaSystemNotifications:
    """Verbindet die Glocke von Home Assistant mit der Notification-Engine."""

    def __init__(
        self,
        hass: HomeAssistant,
        engine: NotificationEngine,
        config_store: ConfigStore,
    ) -> None:
        self._hass = hass
        self._engine = engine
        self._config_store = config_store
        self._unsub: CALLBACK_TYPE | None = None

        # Die Rueckrufe von Home Assistant sind synchron, die Arbeit daran
        # nicht. Ohne Reihenfolge koennte ein unmittelbar folgendes "verworfen"
        # vor dem "entstanden" ausgefuehrt werden und die Meldung bliebe
        # stehen. Die Sperre haelt die Reihenfolge der Ereignisse ein.
        self._sperre = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self._config_store.document.settings.ha_system_notifications

    @property
    def _typ(self) -> NotificationType:
        return self._config_store.document.settings.ha_system_notification_type

    @property
    def running(self) -> bool:
        return self._unsub is not None

    # -- Lebenszyklus ----------------------------------------------------

    async def async_start(self) -> None:
        """Nimmt die Uebernahme auf, falls sie eingeschaltet ist."""
        if self.running or not self.enabled:
            return

        self._unsub = pn.async_register_callback(self._hass, self._handle_update)
        _LOGGER.debug("Uebernahme der HA-Systemnachrichten aufgenommen")

        # Der Rueckruf liefert nur kuenftige Aenderungen. Was bereits in der
        # Seitenleiste steht, muss eigens geholt werden -- sonst fehlte nach
        # jedem Neustart genau das, was Home Assistant beim Hochfahren
        # gemeldet hat.
        await self._async_adopt_existing()

    @callback
    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def async_apply_settings(self) -> None:
        """Richtet sich nach der Einstellung, nachdem diese geaendert wurde."""
        if self.enabled:
            await self.async_start()
            return

        self.async_stop()
        # Bereits uebernommene Meldungen muessen verschwinden. Sonst blieben
        # sie stehen, bis Home Assistant sie zufaellig verwirft -- und bis
        # dahin waere nicht zu erklaeren, woher sie kommen.
        beendet = await self._engine.async_close_all_system(CloseReason.SOURCE_DISABLED)
        if beendet:
            _LOGGER.debug("%s uebernommene Systemnachrichten beendet", beendet)

    # -- Ereignisse ------------------------------------------------------

    @callback
    def _handle_update(self, update_type: pn.UpdateType, notifications: Mapping[str, Any]) -> None:
        """Rueckruf von Home Assistant: etwas an der Glocke hat sich geaendert."""
        if update_type is pn.UpdateType.REMOVED:
            for notification_id in list(notifications):
                self._hass.async_create_task(self._async_beenden(notification_id))
            return

        for notification_id, meldung in list(notifications.items()):
            self._hass.async_create_task(self._async_uebernehmen(notification_id, meldung))

    async def _async_uebernehmen(self, notification_id: str, meldung: Mapping[str, Any]) -> None:
        async with self._sperre:
            text = kurzfassung(meldung.get("message"))
            if not text:
                # Ohne Text gibt es nichts zu zeigen. Home Assistant laesst
                # das zu, das Notification Center nicht.
                _LOGGER.debug("Systemnachricht %s ohne Text uebersprungen", notification_id)
                return

            await self._engine.async_create_system(
                notification_id=notification_id,
                type=self._typ,
                message=text,
                title=titel(meldung.get("title")),
                created_at=meldung.get("created_at"),
            )

    async def _async_beenden(self, notification_id: str) -> None:
        async with self._sperre:
            await self._engine.async_close_system(notification_id)

    async def _async_adopt_existing(self) -> None:
        for notification_id, meldung in self._bestand().items():
            await self._async_uebernehmen(notification_id, meldung)

    def _bestand(self) -> dict[str, Any]:
        """Die Meldungen, die gerade in der Seitenleiste stehen.

        Home Assistant veroeffentlicht dafuer keine Funktion; die Komponente
        exportiert aber die intern genutzte. Sie wird deshalb nachgesehen
        statt fest aufgerufen: faellt sie eines Tages weg, fehlt nur der
        Altbestand, und die Uebernahme laufender Meldungen arbeitet weiter.
        """
        leser = getattr(pn, "_async_get_or_create_notifications", None)
        if leser is None:
            _LOGGER.debug(
                "Home Assistant bietet keinen Zugriff auf die bestehenden "
                "Benachrichtigungen; es werden nur neue uebernommen"
            )
            return {}

        try:
            return dict(leser(self._hass))
        except Exception:
            _LOGGER.exception("Bestehende Systemnachrichten konnten nicht gelesen werden")
            return {}


def kurzfassung(message: Any) -> str:
    """Ein Meldungstext, der in eine Zeile passt.

    Zeilenumbrueche und Mehrfachleerzeichen werden zusammengezogen: ein
    Markdown-Absatz im Dashboard ergibt sonst eine Zeile von unabsehbarer
    Hoehe. Gekuerzt wird mit einem Auslassungszeichen, damit sichtbar bleibt,
    dass es weitergeht.
    """
    if message is None:
        return ""

    text = " ".join(str(message).split())
    if len(text) <= MAX_MESSAGE_LENGTH:
        return text
    return text[: MAX_MESSAGE_LENGTH - 1].rstrip() + "…"


def titel(title: Any) -> str | None:
    if title is None:
        return None
    text = " ".join(str(title).split())
    return text or None
