<img src="icon.png" alt="" width="96" align="right">

# Notification Center

Zentrales, lokales Benachrichtigungs- und Ereignissystem fuer Home Assistant.

Das Notification Center ueberwacht ausgewaehlte Home-Assistant-Entities, erzeugt
daraus zustandsgebundene Notifications, fuehrt eine dauerhafte Historie und
stellt eine oeffentliche API bereit, ueber die Automationen Notifications
erzeugen, aktualisieren und beenden koennen.

Es arbeitet ausschliesslich mit Daten der lokalen Home-Assistant-Instanz:
keine externen Datenquellen, keine Cloud, keine externe Datenbank.

## Status

Aktuelle Version: `1.0.0`. Alle zehn Entwicklungsphasen sind abgeschlossen.

| Phase | Inhalt | Status |
|-------|--------|--------|
| 1 | Integration, Storage, Datenmodelle | abgeschlossen |
| 2 | Entity-Registrierung, State-Listener, Rule Engine | abgeschlossen |
| 3 | Notification-Lebenszyklus, Event Store, Counter | abgeschlossen |
| 4 | Automations-API (create/update/dismiss) | abgeschlossen |
| 5 | Discovery Engine, Vorschlaege, Confidence | abgeschlossen |
| 6 | Config Flow, Einstellungen | abgeschlossen |
| 7 | Lovelace-Panel (Dashboard, Historie, Discovery) | abgeschlossen |
| 8 | Kompakte Lovelace-Card | abgeschlossen |
| 9 | Restart-Recovery, Cleanup, Performance | abgeschlossen |
| 10 | Vollstaendige Tests, Dokumentation, Code-Qualitaet | abgeschlossen |

## Installation

Voraussetzung ist Home Assistant 2026.8 oder neuer.

**Ueber HACS**: Repository als benutzerdefiniertes Repository der Kategorie
*Integration* hinzufuegen, installieren, Home Assistant neu starten.

**Manuell**: den Ordner `custom_components/notification_center` nach
`<config>/custom_components/` kopieren und Home Assistant neu starten.

Danach unter *Einstellungen → Geräte & Dienste → Integration hinzufügen* das
Notification Center auswaehlen. Es gibt genau eine Instanz pro Installation.

## Bedienung

Das Panel erscheint in der Seitenleiste und hat vier Bereiche:

**Dashboard** zeigt ausschliesslich aktive Notifications, gruppiert nach
Alarmen, Warnungen und Infos, jeweils mit Meldung und Zeitpunkt. Eine
Notification mit verknuepfter Entity ist anklickbar und oeffnet deren
Detailansicht.

**Historie** zeigt aktive und abgeschlossene Ereignisse, neueste zuerst.
Filtern nach Typ, Quelle, Zeitraum und Bereich sowie die Volltextsuche laufen
im Backend; geladen werden 50 Eintraege, weitere auf Anforderung.

**Regeln** zeigt den gesamten Regelbestand, nach Entity gruppiert, und fuehrt
in den Regel-Editor: dort lassen sich Regeln von Hand anlegen, bearbeiten und
loeschen, und eine Entity laesst sich durch eine andere ersetzen.

**Discovery** findet Entities nach Typ, Name oder Entity-ID, zeigt zu jeder
Regelvorschlaege samt Begruendung und uebernimmt sie in die Ueberwachung.
Vorschlaege, die bloss auf einem Wort im Namen beruhen, werden nicht
angeboten: sie kosten mehr Vertrauen, als sie einbringen.

### Regeln

Eine Regel gehoert immer zu genau einer Entity. Vier Faelle stehen zur
Verfuegung:

* **Zustand ist** – gilt, solange der Zustand anliegt.
* **Zustand ist nicht** – gilt, solange der Zustand keiner der angegebenen ist.
* **Zustand aendert sich zu** – loest beim Wechsel in den Zielzustand aus und
  bleibt bestehen, solange dieser anliegt.
* **Wert ueber- oder unterschreitet** – numerischer Vergleich, optional mit
  Hysterese.
* **Zeitbedingung** – die Bedingung muss ununterbrochen eine Weile anliegen.

Mehrere Regeln derselben Entity duerfen gleichzeitig gelten und erzeugen dann
parallele Notifications. In einer **Regelgruppe** dagegen ist immer nur die
hoechste erfuellte Stufe sichtbar; jeder Stufenwechsel ist ein eigener
Eintrag in der Historie.

Entity-basierte Notifications lassen sich nicht von Hand beenden. Sie enden,
wenn ihre Bedingung nicht mehr gilt, ihre Regel deaktiviert oder ihre Entity
aus der Ueberwachung genommen wird.

## Automations-API

Drei Services stehen Automationen zur Verfuegung. Owner und ID bilden
zusammen den eindeutigen Schluessel; zwei Automationen duerfen dieselbe ID
verwenden, ohne sich zu beeinflussen.

```yaml
# Erzeugen. Ein erneuter Aufruf mit demselben Schluessel ueberschreibt die
# bestehende Notification, statt eine zweite anzulegen.
action: notification_center.create
data:
  notification_id: wasserleck
  type: alarm            # info | warning | alarm
  message: Wasserleck im Keller
  title: Keller          # optional
  entity_id: binary_sensor.leckmelder_keller   # optional, macht sie klickbar
  duration: "00:15:00"   # optional, beendet sie von selbst
```

```yaml
# Aendern. Erzeugt keinen eigenen Eintrag in der Historie.
action: notification_center.update
data:
  notification_id: wasserleck
  type: warning
  message: Wasserleck eingedaemmt
```

```yaml
# Beenden.
action: notification_center.dismiss
data:
  notification_id: wasserleck
```

Ohne `owner` wird die aufrufende Automation ueber den Aufrufkontext ermittelt.
Das ist eine Naeherung; bei verschachtelten Skripten kann sie danebengehen.
Wer sich auf saubere Trennung verlassen will, gibt `owner` ausdruecklich an.

Zusaetzlich feuert die Integration bei jedem Beginn, jeder Aenderung und jedem
Ende ein Ereignis `notification_center_event` auf dem Home-Assistant-Eventbus.

## Entities

Fuenf Zaehler stehen als Sensoren bereit. Ihre Werte stammen aus dem laufenden
Zustand, nicht aus einer Abfrage des Logs, und werden ereignisgesteuert
aktualisiert.

| Entity | Bedeutung |
|--------|-----------|
| `sensor.notification_center_info_count` | aktive Infos |
| `sensor.notification_center_warning_count` | aktive Warnungen |
| `sensor.notification_center_alarm_count` | aktive Alarme |
| `sensor.notification_center_active_count` | aktive Meldungen gesamt |
| `sensor.notification_center_events_today` | Ereignisse seit Mitternacht |

## Lovelace-Card

```yaml
type: custom:notification-center-card
mode: counts     # counts | list
title: Meldungen # optional
max: 5           # nur bei mode: list
```

Die Card kommt mit der Integration. Sie traegt sich selbst in die
Lovelace-Ressourcen ein und bleibt dort auch, wenn die Integration neu
geladen wird: ein Entfernen wuerde jede bereits eingerichtete Karte auf den
Dashboards zerstoeren.

## Einstellungen

Ueber *Konfigurieren* an der Integration:

* **Aufbewahrung der Historie** – 7, 30, 90, 365 Tage oder unbegrenzt.
* **Maximale Anzahl Ereignisse** – 1.000, 5.000, 10.000 oder 50.000.
  Beide Grenzen gelten gleichzeitig; aeltestes wird zuerst entfernt.
* **Analysezeitraum** – wie weit die Historienanalyse zurueckblickt.
* **Pausiert** – waehrend der Pause entstehen keine neuen Notifications und
  keine Log-Eintraege. Laufende bleiben unberuehrt. Beim Fortsetzen werden
  die aktuellen Zustaende neu bewertet.

Gesichert wird alles vom Home-Assistant-Backup; eine eigene Sicherung gibt es
bewusst nicht.

## Architektur

Eine einzige Home-Assistant-Integration (`notification_center`) mit logisch
getrennten Modulen. Die gesamte Geschaeftslogik liegt im Backend; das Frontend
stellt ausschliesslich dar und ruft die Backend-API auf.

```
custom_components/notification_center/
  api/            WebSocket-Kommandos und Services
  discovery/      Entity-Suche, Vorschlaege, Historienanalyse
  rules/          Regelmodelle, Auswertung, State-Listener
  notifications/  Notification-Modelle, Lebenszyklus, Engine
  storage/        Konfigurations-Store (JSON) und Event Store (SQLite)
  frontend/       Panel und Card (buildfreie ES-Module)
```

### Persistenz

* **Konfiguration** (ueberwachte Entities, Regeln, Einstellungen) liegt im
  Home-Assistant-Storage als JSON. Klein, versioniert, migrierbar.
* **Ereignisse** liegen in einer eigenen lokalen SQLite-Datei unter
  `<config>/notification_center/events.db`. Kein Datenbankserver, kein
  externer Dienst; die Datei wird vom Home-Assistant-Backup mitgesichert.
  SQLite ist noetig, weil bis zu 50.000 Ereignisse mit serverseitigem Filtern,
  Suchen, Sortieren, Paginieren und Cleanup performant bleiben muessen.

### Leistung

Die Ueberwachung ist vollstaendig ereignisbasiert: beobachtet werden nur die
explizit uebernommenen Entities, es gibt keine Schleife ueber alle Entities
und kein Polling. Timer entstehen ausschliesslich fuer Regeln, deren Bedingung
bereits anliegt.

Die Zaehler werden bei jeder Aenderung fortgeschrieben und nie aus dem Log
berechnet. Nach einem Neustart kostet die Wiederherstellung zwei Abfragen: die
aktiven Ereignisse ueber einen Teilindex und eine Zaehlabfrage fuer den
heutigen Tag.

Die Historienanalyse nutzt bevorzugt die Langzeitstatistiken von Home
Assistant. Bei sieben Tagen sind das hoechstens 168 Zeilen statt womoeglich
Zehntausender Rohzustaende. Sie laeuft nur auf Anforderung, nie im
Hintergrund; die Entitysuche fasst die Datenbank gar nicht an.

### Testbarkeit

Die Module `models.py`, `evaluator.py`, `intents.py`, `lifecycle.py`,
`analyzer.py`, `suggestions.py`, `config_models.py` und `event_store.py`
enthalten bewusst **keine Home-Assistant-Importe**. Sie erhalten Zustaende als
einfache Snapshot-Objekte und sind damit ohne HA-Runtime testbar. Ein
Architekturtest prueft das per AST nach, damit die Trennung nicht unbemerkt
erodiert.

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

Schlaegt ein Testlauf in der CI fehl, meldet der Testschritt die
Zusammenfassung zusaetzlich als Annotationen. Job-Logs sind ueber die
GitHub-API nur mit Admin-Rechten abrufbar, Annotationen dagegen frei lesbar.

Das Frontend ist buildfrei; die CI prueft lediglich, ob die ausgelieferten
ES-Module parsen.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
