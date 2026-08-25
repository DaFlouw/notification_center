# Notification Center

Zentrales, lokales Benachrichtigungs- und Ereignissystem fuer Home Assistant.

Das Notification Center ueberwacht ausgewaehlte Home-Assistant-Entities, erzeugt
daraus zustandsgebundene Notifications, fuehrt eine dauerhafte Historie und
stellt eine oeffentliche API bereit, ueber die Automationen Notifications
erzeugen, aktualisieren und beenden koennen.

Es arbeitet ausschliesslich mit Daten der lokalen Home-Assistant-Instanz:
keine externen Datenquellen, keine Cloud, keine externe Datenbank.

## Status

In Entwicklung. Aktuelle Version: `0.2.0`.

| Phase | Inhalt | Status |
|-------|--------|--------|
| 1 | Integration, Storage, Datenmodelle | abgeschlossen |
| 2 | Entity-Registrierung, State-Listener, Rule Engine | abgeschlossen |
| 3 | Notification-Lebenszyklus, Event Store, Counter | als naechstes |
| 4 | Automations-API (create/update/dismiss) | offen |
| 5 | Discovery Engine, Vorschlaege, Confidence | offen |
| 6 | Config Flow, Ersteinrichtung | offen |
| 7 | Lovelace-Panel (Dashboard, Historie, Discovery) | offen |
| 8 | Kompakte Lovelace-Card | offen |
| 9 | Restart-Recovery, Cleanup, Performance | offen |
| 10 | Vollstaendige Tests, Dokumentation, Code-Qualitaet | offen |

## Architektur

Eine einzige Home-Assistant-Integration (`notification_center`) mit logisch
getrennten Modulen. Die gesamte Geschaeftslogik liegt im Backend; das Frontend
stellt ausschliesslich dar und ruft die Backend-API auf.

```
custom_components/notification_center/
  api/            oeffentliche WebSocket-API und Services
  discovery/      Entity-/Device-Discovery, Vorschlaege, Historienanalyse
  rules/          Regelmodelle und Auswertung
  notifications/  Notification-Modelle und Lebenszyklus
  storage/        Konfigurations-Store (JSON) und Event Store (SQLite)
  frontend/       Panel und Card (buildfreie ES-Module)
```

### Persistenz

* **Konfiguration** (ueberwachte Entities, Regeln, Einstellungen) liegt im
  Home-Assistant-Storage als JSON. Klein, versioniert, migrierbar.
* **Events** liegen in einer eigenen lokalen SQLite-Datei unter
  `<config>/notification_center/events.db`. Kein Datenbankserver, kein
  externer Dienst; die Datei wird vom Home-Assistant-Backup mitgesichert.
  SQLite ist noetig, weil bis zu 50.000 Events mit serverseitigem Filtern,
  Suchen, Sortieren, Paginieren und Cleanup performant bleiben muessen.

### Testbarkeit

Die Module `models.py`, `evaluator.py`, `lifecycle.py` und `analyzer.py`
enthalten bewusst **keine Home-Assistant-Importe**. Sie erhalten Zustaende als
einfache Snapshot-Objekte und sind damit ohne HA-Runtime testbar
(`tests/unit`). Home-Assistant-abhaengige Tests liegen in
`tests/integration` und laufen unter Linux/CI.

## Entwicklung

Die Domaenentests laufen ohne Home Assistant und damit auch unter Windows:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest tests/unit
```

Die Home-Assistant-Tests unter `tests/integration` laufen ausschliesslich in
der GitHub-Actions-CI unter Linux: Home Assistant importiert `fcntl` und
startet damit unter Windows grundsaetzlich nicht. Sie benoetigen Python 3.14,
`pytest-homeassistant-custom-component` und das Paket
`home-assistant-frontend`, weil die Integration ein eigenes Panel bereitstellt.

Schlaegt ein Testlauf in der CI fehl, meldet der Testschritt die letzten
Ausgabezeilen zusaetzlich als Annotationen. Job-Logs sind ueber die
GitHub-API nur mit Admin-Rechten abrufbar, Annotationen dagegen frei lesbar.

Ein Architekturtest prueft, dass die Domaenenmodule keine
Home-Assistant-Importe enthalten. Die Trennung ist damit nicht nur
Konvention, sondern abgesichert.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
