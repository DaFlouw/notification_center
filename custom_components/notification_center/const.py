"""Zentrale Konstanten des Notification Centers.

Dieses Modul darf keine Home-Assistant-Importe enthalten, damit es auch von
den reinen Domaenenmodulen (rules, notifications, storage) verwendet werden
kann, die ohne HA-Runtime testbar bleiben muessen.
"""

from __future__ import annotations

from typing import Final

# --------------------------------------------------------------------------
# Integration
# --------------------------------------------------------------------------

DOMAIN: Final = "notification_center"
INTEGRATION_VERSION: Final = "1.0.2"

#: Nur eine globale Instanz pro Home-Assistant-Installation (Spezifikation 4).
SINGLE_INSTANCE_TITLE: Final = "Notification Center"

# --------------------------------------------------------------------------
# Versionierung
# --------------------------------------------------------------------------
# Jede persistierte Struktur traegt eine eigene Schemaversion, damit
# Migrationen unabhaengig voneinander moeglich sind.

#: Version des ConfigEntry (async_migrate_entry).
CONFIG_ENTRY_VERSION: Final = 1
CONFIG_ENTRY_MINOR_VERSION: Final = 1

#: Version des Konfigurations-Stores (HA Store / JSON).
CONFIG_STORE_VERSION: Final = 1
CONFIG_STORE_MINOR_VERSION: Final = 1

#: Version des SQLite-Schemas (PRAGMA user_version).
EVENT_DB_SCHEMA_VERSION: Final = 1

#: Version der oeffentlichen WebSocket-API. Wird in jeder Antwort mitgeliefert,
#: damit ein veraltetes Frontend einen Hinweis statt eines Fehlers zeigt.
API_VERSION: Final = 1

#: Schemaversion der Datenmodelle (Rule, Event, Notification).
MODEL_SCHEMA_VERSION: Final = 1

# --------------------------------------------------------------------------
# Persistenz
# --------------------------------------------------------------------------

#: Unterverzeichnis im HA-Config-Ordner fuer eigene Daten.
DATA_SUBDIR: Final = "notification_center"

#: SQLite-Datei des Event Stores. Bewusst getrennt von der Recorder-Datenbank.
EVENT_DB_FILENAME: Final = "events.db"

#: Schluessel des HA-Storage-Stores (.storage/notification_center.config).
CONFIG_STORE_KEY: Final = f"{DOMAIN}.config"

#: Laufzeitzustand fuer die Wiederherstellung nach einem Neustart.
STATE_STORE_KEY: Final = f"{DOMAIN}.state"
STATE_STORE_VERSION: Final = 1

# --------------------------------------------------------------------------
# hass.data
# --------------------------------------------------------------------------

DATA_RUNTIME: Final = f"{DOMAIN}_runtime"

# --------------------------------------------------------------------------
# Services (oeffentliche Automations-API, Spezifikation 23-29)
# --------------------------------------------------------------------------

SERVICE_CREATE: Final = "create"
SERVICE_UPDATE: Final = "update"
SERVICE_DISMISS: Final = "dismiss"
SERVICE_GET_ACTIVE: Final = "get_active"
SERVICE_GET_HISTORY: Final = "get_history"
SERVICE_GET_COUNTS: Final = "get_counts"

# --------------------------------------------------------------------------
# Event-Bus
# --------------------------------------------------------------------------

#: Wird gefeuert, wenn eine Notification beginnt, sich aendert oder endet.
EVENT_NOTIFICATION: Final = f"{DOMAIN}_event"

# --------------------------------------------------------------------------
# WebSocket-API
# --------------------------------------------------------------------------

WS_PREFIX: Final = DOMAIN

# --------------------------------------------------------------------------
# Frontend
# --------------------------------------------------------------------------

PANEL_URL_PATH: Final = "notification-center"
PANEL_TITLE: Final = "Notification Center"
PANEL_ICON: Final = "mdi:bell-ring-outline"

#: Basis-URL, unter der die Frontend-Dateien ausgeliefert werden.
FRONTEND_URL_BASE: Final = f"/{DOMAIN}_frontend"

# --------------------------------------------------------------------------
# Log-Aufbewahrung (Spezifikation 38)
# --------------------------------------------------------------------------

RETENTION_DAYS_OPTIONS: Final = (7, 30, 90, 365, 0)  # 0 == unbegrenzt
RETENTION_DAYS_UNLIMITED: Final = 0
DEFAULT_RETENTION_DAYS: Final = 90

MAX_EVENTS_OPTIONS: Final = (1_000, 5_000, 10_000, 50_000)
DEFAULT_MAX_EVENTS: Final = 10_000

# --------------------------------------------------------------------------
# Historienanalyse (Spezifikation 11)
# --------------------------------------------------------------------------

#: Analysezeitraum in Tagen. Bewusst klein gehalten (Performance).
DEFAULT_ANALYSIS_DAYS: Final = 7

# --------------------------------------------------------------------------
# Abfragen (Spezifikation 61)
# --------------------------------------------------------------------------

DEFAULT_PAGE_SIZE: Final = 50
MAX_PAGE_SIZE: Final = 500
