"""Konfigurations-Store auf Basis des Home-Assistant-Storage.

Duenne Schicht ueber ``config_models.py``: dieses Modul kennt Home Assistant,
die Datenstruktur selbst nicht. Die Konfiguration ist klein und wird selten
geschrieben, deshalb ist JSON hier die passende Ablage. Ereignisse liegen
dagegen in SQLite (siehe ``event_store.py``).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from ..const import (
    CONFIG_STORE_KEY,
    CONFIG_STORE_MINOR_VERSION,
    CONFIG_STORE_VERSION,
)
from .config_models import ConfigDocument, migrate_config

_LOGGER = logging.getLogger(__name__)

#: Verzoegerung fuer gebuendelte Schreibvorgaenge. Mehrere Aenderungen kurz
#: hintereinander (etwa beim Uebernehmen eines ganzen Geraets) landen so in
#: einem einzigen Schreibvorgang.
SAVE_DELAY = 2.0


class _ConfigStorage(Store[dict[str, Any]]):
    """Store mit Migrationspfad fuer aeltere Konfigurationsstaende."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        if old_major_version > CONFIG_STORE_VERSION:
            raise ValueError(
                f"Konfiguration hat Hauptversion {old_major_version}, unterstuetzt "
                f"wird hoechstens {CONFIG_STORE_VERSION}"
            )
        _LOGGER.debug("Migriere Konfiguration von %s.%s", old_major_version, old_minor_version)
        return migrate_config(old_data, from_minor=old_minor_version)


class ConfigStore:
    """Laedt, haelt und speichert das Konfigurationsdokument."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store = _ConfigStorage(
            hass,
            CONFIG_STORE_VERSION,
            CONFIG_STORE_KEY,
            minor_version=CONFIG_STORE_MINOR_VERSION,
            atomic_writes=True,
        )
        self._document = ConfigDocument.empty()

    @property
    def document(self) -> ConfigDocument:
        """Das aktuelle Konfigurationsdokument.

        Aenderungen daran werden erst durch ``async_save`` beziehungsweise
        ``schedule_save`` dauerhaft.
        """
        return self._document

    async def async_load(self) -> ConfigDocument:
        raw = await self._store.async_load()
        if raw is None:
            self._document = ConfigDocument.empty()
            _LOGGER.debug("Keine gespeicherte Konfiguration gefunden, starte leer")
        else:
            self._document = ConfigDocument.from_dict(raw)
            _LOGGER.debug(
                "Konfiguration geladen: %s Entities, %s Regeln, %s Gruppen",
                len(self._document.entities),
                len(self._document.rules),
                len(self._document.groups),
            )
        return self._document

    async def async_save(self) -> None:
        """Schreibt sofort. Fuer Nutzeraktionen mit unmittelbarer Rueckmeldung."""
        await self._store.async_save(self._document.to_dict())

    @callback
    def schedule_save(self) -> None:
        """Schreibt verzoegert und gebuendelt."""
        self._store.async_delay_save(self._document.to_dict, SAVE_DELAY)

    async def async_shutdown(self) -> None:
        """Stellt sicher, dass eine ausstehende Speicherung noch erfolgt."""
        await self._store.async_save(self._document.to_dict())
