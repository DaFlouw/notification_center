# Systemtests

Testfaelle fuer den Durchlauf gegen eine **laufende** Home-Assistant-Instanz.

Sie ergaenzen die automatisierten Tests, decken aber etwas anderes ab: die
Domaenentests pruefen Logik ohne Home Assistant, die Integrationstests pruefen
sie gegen eine Testinstanz, und die Frontend-Tests pruefen Darstellungs-
funktionen ohne Browser. Was keiner von ihnen sieht, ist das Zusammenspiel im
Betrieb -- echte Entities, echte Zeit, echte Zustandswechsel.

## Durchfuehrung

Die WebSocket-Kommandos lassen sich direkt absetzen; die Services ueber
*Entwicklerwerkzeuge -> Aktionen*. Fuer den Nachweis genuegt jeweils ein
`get_history`-Aufruf mit `search` auf die Testkennung.

**Testentitaeten statt echter Geraete.** Alle Faelle arbeiten auf eigens
angelegten Helfern (`input_boolean`, `input_number`, `input_select`,
`input_text`, `counter`, `timer`) mit dem Namenspraefix `NC Test`. Regeln an
echten Geraeten zu erproben wuerde beim Ausloesen tatsaechlich Licht schalten
oder Heizungen verstellen.

**Aufraeumen.** Nach dem Durchlauf: Regeln und Gruppen loeschen, Entities aus
der Ueberwachung nehmen, Helfer loeschen, die `TC-`-Eintraege aus der Historie
entfernen. Anschliessend `get_config` gegen den Ausgangsstand vergleichen.

**Nicht ausfuehren:** `clear_history` loescht die gesamte Historie der
Installation, nicht nur die Testeintraege. `delete_event` nur auf selbst
erzeugte Ereignisse anwenden.

**Einstellungen** (`paused`, `retention_days`, `max_events`, `analysis_days`)
vor dem Lauf notieren und danach zuruecksetzen. Waehrend einer Pause entstehen
auch fuer die echten Geraete keine Eintraege.

---

## A -- Konfiguration und API-Grundlagen

| ID | Fall | Erwartung |
|----|------|-----------|
| A1 | `get_config` | Liefert `version` passend zum Manifest. Weicht sie ab, laeuft noch alter Python-Code und alle weiteren Ergebnisse sind wertlos. |
| A2 | `get_config` | Jede Entity traegt `name`, `area_name`, `floor_name` aus der Registry. |
| A3 | `get_active` | `counts` deckt sich mit der Liste in `active`, je Typ und in der Summe. |
| A4 | `get_counts` | Gleiche Werte wie `get_active`. |
| A5 | `get_device` mit einer Geraetekennung | Alle Entities des Geraets, je mit `monitored` und `rule_count`. |

## B -- Discovery

| ID | Fall | Erwartung |
|----|------|-----------|
| B1 | `discover` ohne Filter | Findet Geraete-Entities der unterstuetzten Domaenen. |
| B2 | `discover` mit `search` | Trifft ueber Anzeigename und Entity-ID. |
| B3 | `discover` mit `domain` | Nur Treffer dieser Domaene. |
| B4 | `discover` nach Anlegen der sechs Testhelfer | Alle sechs erscheinen (Issue 4). |
| B5 | `discover` bei vorhandenem `input_button` | Erscheint **nicht** -- sein Zustand ist der Zeitpunkt des letzten Drucks. |
| B6 | `get_suggestions` fuer `input_select` | `states` enthaelt genau die `options` der Entity. |
| B7 | `get_suggestions` fuer `input_text` | `states` ist **leer**, damit der Editor ein Textfeld zeigt. |
| B8 | `get_suggestions` fuer einen Binaersensor mit `device_class` | Vorschlag mit Begruendung und hoher Sicherheit. |

## C -- Regelauswertung

| ID | Fall | Erwartung |
|----|------|-----------|
| C1 | *Zustand ist* `on`, Schalter einschalten | Notification entsteht, `{state}` ist ersetzt. |
| C2 | Schalter ausschalten | Notification endet, `end_time` und `duration` gesetzt. |
| C3 | *Wert ueberschreitet* 25, Rueckkehr 20; Wert auf 30 | Notification entsteht, `{value}` und `{unit}` ersetzt. |
| C4 | Wert auf 22 (zwischen den Schwellen) | Notification bleibt bestehen -- Hysterese. |
| C5 | Wert auf 19 | Notification endet. |
| C6 | *Zustand aendert sich zu* `Urlaub`, erster Wechsel dorthin | Notification entsteht. |
| C7 | Zweiter und dritter Wechsel dorthin | Je eine neue Notification. |
| C8 | *Zustand ist nicht*, ueber ein Attribut als Wertquelle | Notification, solange das Attribut keinen der Werte hat. |
| C9 | *Zustand ist* mit `duration_seconds` 60, Schalter einschalten | Zunaechst **keine** Notification. |
| C10 | 60 Sekunden spaeter | Notification entsteht. |
| C11 | Zwei Regeln derselben Entity gleichzeitig erfuellt | Zwei parallele Notifications. |

## D -- Regelgruppen

Drei Stufen auf einem `input_number`, Operator `gt`: Stufe 1 ab 40 (Info),
Stufe 2 ab 50 (Warnung), Stufe 3 ab 60 (Alarm).

| ID | Fall | Erwartung |
|----|------|-----------|
| D1 | `save_group` | Gruppe wird angenommen, alle Stufen tragen `group_id` und `level`. |
| D2 | Wert auf 45 | Nur Stufe 1 aktiv. |
| D3 | Wert auf 65 | Stufe 1 endet, Stufe 3 beginnt, Stufe 2 bleibt unsichtbar. |
| D4 | Wert auf 55 | Stufe 3 endet, Stufe 2 wird sichtbar. |
| D5 | Zeitstempel nach D4 | Beginn von Stufe 2 liegt **nach** dem Ende von Stufe 3. |
| D6 | Wert auf 10 | Alle Stufen beendet. |
| D7 | `save_group` mit uneinheitlichem Operator oder doppelter Stufennummer | Wird abgelehnt. |

## E -- Notification-Lebenszyklus

| ID | Fall | Erwartung |
|----|------|-----------|
| E1 | `delete_rule` bei laufender Notification | Notification endet sofort. |
| E2 | `remove_entity` bei laufender Notification | Notification endet, Historie bleibt. |
| E3 | `remove_entity` | Auch Regeln und Gruppen dieser Entity verschwinden. |
| E4 | `replace_entity` | Neue Entity traegt `replaced_entity_id`, alte ist fort. |
| E5 | `replace_entity` auf eine Kennung, die es nicht gibt | Wird abgelehnt, nichts verschiebt sich. |
| E6 | `delete_event` auf ein beendetes Ereignis | `deleted: true`. |
| E7 | `delete_event` auf ein **laufendes** Ereignis | `deleted: false` -- aktive Meldungen sind geschuetzt. |

## F -- Automations-API

| ID | Fall | Erwartung |
|----|------|-----------|
| F1 | `create` mit `owner`, `type`, `title`, `entity_id` | Ereignis mit `source: automation`, alle Felder uebernommen. |
| F2 | `update` von Typ und Text | Aendert das bestehende Ereignis, **kein** zweiter Eintrag, `start_time` bleibt. |
| F3 | Zaehler nach F2 | Aufteilung nach Typ passt weiter zur Liste. |
| F4 | `create` mit gleicher `notification_id`, anderem `owner` | Zwei unabhaengige Notifications. |
| F5 | `dismiss` einer davon | Nur diese endet. |
| F6 | `create` mit `duration: "00:00:30"` | Endet nach 30 Sekunden von selbst. |
| F7 | `create` mit gleicher ID und gleichem Owner | Ueberschreibt, legt keine zweite an. |
| F8 | Ereignisbus | Bei Beginn, Aenderung und Ende feuert `notification_center_event`. |

## G -- Zaehler und Sensoren

| ID | Fall | Erwartung |
|----|------|-----------|
| G1 | Die fuenf Sensoren gegen `get_counts` | Gleiche Werte. |
| G2 | Nach jedem Beginn und Ende | Zaehler stimmen weiter mit der Liste ueberein. |
| G3 | `events_today` | Steigt mit jedem neuen Ereignis, nie beim Beenden. |
| G4 | Nach `update` mit Typwechsel | Aufteilung bleibt richtig. |

## H -- Historie

| ID | Fall | Erwartung |
|----|------|-----------|
| H1 | `get_history` ohne Filter | Neueste zuerst, `total` und `has_more` gesetzt. |
| H2 | Filter `types` | Nur dieser Typ. |
| H3 | Filter `sources` | Nur diese Quelle. |
| H4 | Filter `area_ids` | Nur dieser Bereich. |
| H5 | Alle drei zugleich | Schnittmenge. |
| H6 | `search` | Trifft im Meldungstext. |
| H7 | `limit` und `offset` | Zweite Seite setzt die erste ohne Luecke und ohne Ueberschneidung fort. |
| H8 | Filter `start` | Nur Ereignisse ab diesem Zeitpunkt. |

## I -- Einstellungen

| ID | Fall | Erwartung |
|----|------|-----------|
| I1 | `paused: true`, dann Zustandswechsel | Keine neue Notification, kein Eintrag. |
| I2 | Laufende Notification waehrend der Pause | Bleibt unberuehrt, auch wenn ihre Bedingung entfaellt. |
| I3 | `paused: false` | Aktuelle Zustaende werden neu bewertet. |
| I4 | `retention_days`, `max_events`, `analysis_days` | Werden uebernommen und ueberstehen einen Reload. |
| I5 | Unzulaessiger Wert | Wird abgelehnt. |

## J -- Wiederherstellung

| ID | Fall | Erwartung |
|----|------|-----------|
| J1 | `homeassistant.reload_config_entry` | Laufende Notifications bleiben, Zaehler werden aus der Datenbank aufgebaut. |
| J2 | Zaehler nach J1 | Stimmen wieder mit der Liste ueberein -- auch wenn sie vorher abgewichen sind. |
| J3 | Flankenregel nach J1 | Naechster Wechsel loest aus. |
| J4 | Zeitbedingung nach J1 | Wartezeit laeuft ab dem echten Beginn des Zustands weiter, nicht ab dem Neustart. |
| J5 | Protokoll nach dem gesamten Lauf | Keine Fehler oder Warnungen der Integration. |

## K -- Oberflaeche

| ID | Fall | Erwartung |
|----|------|-----------|
| K1 | Card auf einem Dashboard | Gruppierung nach Alarmen, Warnungen, Infos; je Meldung und Uhrzeit. |
| K2 | Card | Keine Dauer, kein Link in die Historie (Ticket 17). |
| K3 | Card | Fusszeile nennt die Ereignisse des Tages. |
| K4 | Card gegen `get_active` | Zeigt dieselben Meldungen. |
| K5 | Panel, Dashboard | Nur aktive Meldungen, nach Kategorien. |
| K6 | Panel, Regeln | Nach Geschoss und Raum gruppiert, Entities ohne Zuordnung am Ende. |
| K7 | Panel, Regel-Editor | An der gerade offenen Regel kein Bearbeiten-Knopf (Issue 3). |
| K8 | Panel, Historie | Auswahl 50 / 100 / 200 pro Seite, Vorgabe 100 (Issue 5). |
| K9 | Panel, Discovery | Typauswahl enthaelt die Gruppe *Helfer* (Issue 4). |

**K1 bis K4** lassen sich ueber einen Dashboard-Screenshot pruefen.

**K5 bis K9** betreffen das Panel. Es liegt unter `/notification-center` und
damit ausserhalb von Lovelace; die Screenshot-Werkzeuge fuer Dashboards
erreichen es nicht, und ein angemeldeter Browser steht nicht immer zur
Verfuegung.

Dafuer gibt es `tests/panel/` -- einen Pruefstand, der das Panel ohne Home
Assistant betreibt:

```bash
python -m http.server 8792
```

Dann `http://localhost:8792/tests/panel/` oeffnen.

Die Seite laedt **das ausgelieferte Modul** aus
`custom_components/notification_center/frontend/` und prueft damit immer den
aktuellen Stand, keine Kopie. An die Stelle der WebSocket-Verbindung tritt ein
`hass`-Ersatz, der die Kommandos aus `daten.js` beantwortet -- Antworten, die
wortgleich aus einer laufenden Instanz stammen. Das Panel braucht von Home
Assistant nur `hass.areas`, `hass.locale` und `hass.connection` und bindet
keine HA-Elemente ein; deshalb laeuft es eigenstaendig.

Zum Bedienen aus der Konsole:

```js
__klick('nav button[data-page="rules"]')   // Seite wechseln
__wurzel()                                  // shadowRoot
__protokoll                                 // abgesetzte Kommandos samt Parametern
```

`__protokoll` ist der eigentliche Gewinn: damit laesst sich nicht nur pruefen,
was angezeigt wird, sondern auch, was das Panel dafuer **abgefragt** hat.

Was der Pruefstand **nicht** abdeckt: die echte WebSocket-Verbindung, das
Abonnement der Aktualisierungen, die Einbettung in die Seitenleiste und die
Themes des Anwenders.

## L -- Bedienelemente

Schaltflaechen, Filter und Eingabefelder. Geprueft wird beides: was die
Oberflaeche zeigt **und welches Kommando sie mit welchen Parametern
abschickt**. Das zweite ist der eigentliche Zweck -- die Naht zwischen
Bedienung und Backend hat sich als die Stelle erwiesen, an der Fehler
unbemerkt bleiben.

Die Faelle liegen als ausfuehrbare Suite in `tests/panel/interaktion.js`.
Server starten, `http://localhost:8792/tests/panel/` oeffnen, *Bedienungstests
starten*. Sie laufen gegen den Pruefstand, nicht gegen die Anlage: `Alle
loeschen` und `Entfernen` duerfen dabei folgenlos ausgeloest werden.

| ID | Fall |
|----|------|
| L1 | Die vier Reiter wechseln die Seite und markieren den aktiven |
| L2 | Der Verweis *Historie* im Dashboard fuehrt zur Historie |
| L3 | *Alle Regeln* fuehrt aus dem Editor zurueck und laedt neu |
| L4 | Eine Meldung mit Entity oeffnet die Detailansicht |
| L5 | Jede aktive Meldung im Dashboard ist anklickbar |
| L6 | Filter Typ schickt `types` mit |
| L7 | Filter Quelle schickt `sources` mit |
| L8 | Filter Bereich schickt `area_ids` mit |
| L9 | Filter Zeitraum setzt `start`, *Alle* laesst es weg |
| L10 | Filter Seitengroesse setzt `limit` und beginnt von vorn |
| L11 | Das Suchfeld fragt entprellt und mit `search` ab |
| L12 | Mehrere Filter wirken gemeinsam |
| L13 | Die leere Auswahl eines Filters entfernt ihn wieder |
| L14 | *Weitere laden* blaettert mit dem Versatz der geladenen Menge |
| L15 | Das Kreuz an einer Zeile loescht genau dieses Ereignis |
| L16 | Aktive Ereignisse tragen kein Loeschkreuz |
| L17 | *Alle loeschen* fragt nach und bricht auf Abbruch folgenlos ab |
| L18 | *Alle loeschen* loescht nach Bestaetigung |
| L19 | *Bearbeiten* oeffnet den Editor mit genau dieser Regel |
| L20 | *Loeschen* fragt nach und bricht auf Abbruch folgenlos ab |
| L21 | *Loeschen* schickt nach Bestaetigung die richtige Regel |
| L22 | *Regel erstellen* oeffnet ein leeres Formular |
| L23 | Die Bedingung schaltet zwischen Zustands- und Wertfeldern um |
| L24 | Die Wertquelle laesst sich auf ein Attribut umstellen |
| L25 | Vergleich und Schwelle wandern als Zahl in die Regel |
| L26 | Die Mehrfachauswahl der Zustaende landet als Liste in der Regel |
| L27 | Der Meldungstext zeichnet nicht neu, damit der Fokus bleibt |
| L28 | Hysterese und Zeitbedingung; Minuten werden zu Sekunden |
| L29 | *Speichern* behaelt die Kennung einer bestehenden Regel |
| L30 | *Abbrechen* schliesst das Formular ohne Kommando |
| L31 | *Entity ersetzen* fragt nach und bricht ohne Eingabe ab |
| L32 | *Entity ersetzen* schickt beide Kennungen, ohne Leerzeichen |
| L33 | Die Typauswahl der Discovery schickt `domain` mit |
| L34 | Das Suchfeld der Discovery fragt entprellt ab |
| L35 | *Uebernehmen* meldet genau diese Entity zur Ueberwachung an |
| L36 | *Entfernen* fragt nach und schickt danach die Entity |
| L37 | *Vorschlaege* holt sie, derselbe Knopf klappt sie wieder ein |
| L38 | Ein Vorschlag uebernimmt Entity und Regel in einem Zug |
| L39 | Die Begruendung eines Vorschlags laesst sich aufklappen |
| L40 | *Regeln* fuehrt aus der Discovery in den Editor |
| L41 | Ein Fehler des Backends wird angezeigt, das Panel bleibt bedienbar |
| L42 | Ohne Einrichtung und ohne Entities erscheint der Assistent |
| L43 | *Ueberspringen* merkt sich das und fuehrt ins Dashboard (Ticket 9) |
| L44 | *Einrichtung starten* merkt sich das und fuehrt in die Discovery |
| L45 | Mit vorhandenen Entities bleibt der Assistent fort |
| L46 | Die Nutzlasten aus L24 bis L38 werden vom echten Backend angenommen |
| L47 | Der Ersetzen-Dialog nennt die aktuelle Entity |
| L48 | Die Seite des Editors zeigt die aktuelle Entity |
| L49 | Die unveraendert bestaetigte Entity loest kein Ersetzen aus |
| L50 | Die Ablehnung des Backends erscheint als Fehlermeldung |

**L46 gehoert an die Anlage.** Der Pruefstand zeigt, *was* die Oberflaeche
abschickt; ob das Backend es annimmt, zeigt nur die laufende Instanz. Die in
L24 bis L38 aufgezeichneten Nutzlasten werden dafuer unveraendert gegen eine
eigens angelegte Wegwerf-Entity gesendet.

`clear_history` wird dabei **nicht** gesendet: es loescht die Historie der
gesamten Installation.

---

## Durchlauf vom 28.08.2026, Version 1.1.3

Ausgefuehrt gegen die produktive Instanz.

| Bereich | Ergebnis |
|---------|----------|
| A Konfiguration und API | bestanden |
| B Discovery | bestanden |
| C Regelauswertung | C6 fehlgeschlagen (Issue 7), uebrige bestanden |
| D Regelgruppen | D5 fehlgeschlagen (Issue 8), uebrige bestanden |
| E Lebenszyklus | bestanden |
| F Automations-API | F3 fehlgeschlagen (Issue 6), uebrige bestanden |
| G Zaehler und Sensoren | G4 fehlgeschlagen (Issue 6), uebrige bestanden |
| H Historie | bestanden |
| I Einstellungen | bestanden |
| J Wiederherstellung | bestanden |
| K Oberflaeche | bestanden |
| L Bedienelemente | L46 (`replace_entity`) fehlgeschlagen (Issue 10), uebrige bestanden |

Zu K im Einzelnen:

* **K5** Dashboard zeigt genau die sieben aktiven Meldungen, nach Alarmen,
  Warnungen und Infos getrennt, mit Uhrzeit und Dauer; Fusszeile
  *74 Ereignisse heute*.
* **K6** Regeln stehen unter *Erdgeschoss* mit den Raeumen Arbeiten, Flur EG,
  Gaestebad, Kueche, WohnEsszimmer, darunter eingerueckt die Entities.
  *Ohne Geschoss / Ohne Raum* steht am Ende. Alle zwoelf Regeln sind
  vorhanden, je mit genau einem Bearbeiten-Knopf.
* **K7** Beim Bearbeiten einer Regel von *Arbeiten Heizung Raum* traegt deren
  Zeile *wird bearbeitet* und keinen Knopf mehr, die zweite Regel derselben
  Entity behaelt ihren. Das Formular ist mit den echten Werten gefuellt.
* **K8** Auswahl 50 / 100 / 200, vorgewaehlt 100. Die Abfrage ging mit
  `limit: 100` hinaus; nach dem Umstellen auf 200 mit `limit: 200, offset: 0`.
* **K9** Die Typauswahl fuehrt *Alle Typen* sowie die Gruppen *Geraete* (15
  Domaenen) und *Helfer* (8 Domaenen) -- deckungsgleich mit
  `SUPPORTED_DOMAINS`.

Ueber den gesamten Durchlauf durch alle vier Seiten gab die Browserkonsole
nichts aus: keine Fehler, keine Warnungen, kein Versionskonflikt.

Zu L: **45 der 46 Faelle bestanden.** L1 bis L45 laufen im Pruefstand, L46
gegen die Anlage. Dabei nahm das Backend jede aufgezeichnete Nutzlast
unveraendert an:

* die Regel mit Attribut als Wertquelle, Hysterese und Zeitbedingung, wie sie
  aus dem Formular entsteht,
* die Regel aus einem uebernommenen Vorschlag -- sie enthaelt gar kein
  `value_source` und wird richtig auf den Zustand als Quelle ergaenzt,
* `set_settings` mit `setup_completed`, wie es der Assistent schickt, ohne die
  uebrigen Einstellungen anzutasten.

Durchgefallen ist **L46 fuer `replace_entity`**: eine Kennung, die es nicht
gibt, wird angenommen. Siehe
[Issue 10](https://github.com/DaFlouw/notification_center/issues/10).

Offene Punkte:
[Issue 6](https://github.com/DaFlouw/notification_center/issues/6),
[Issue 7](https://github.com/DaFlouw/notification_center/issues/7),
[Issue 8](https://github.com/DaFlouw/notification_center/issues/8),
[Issue 10](https://github.com/DaFlouw/notification_center/issues/10).

---

## Nachpruefung vom 29.08.2026, Version 1.1.4

Gegen dieselbe Instanz, nach Neustart auf 1.1.4. Geprueft wurden die vier
Faelle, die im ersten Durchlauf gescheitert waren, jeweils mit eigens
angelegten Wegwerf-Entities.

| Fall | Issue | Ergebnis |
|------|-------|----------|
| C6 -- erste Flanke einer neuen Regel | 7 | Meldung entsteht beim ersten Wechsel |
| F3 / G4 -- Zaehler nach Typwechsel | 6 | Info 2->1, Alarm 0->1; nach dem Beenden deckungsgleich mit der Liste |
| D5 -- Beginn der deeskalierten Stufe | 8 | Stufe 2 beginnt `00:26:09.189297`, exakt zum Ende von Stufe 3 -- keine Ueberlappung |
| E5 -- Ersetzen mit unbekannter Kennung | 10 | Abgelehnt: *Die Entity switch.gibt_es_wirklich_nicht gibt es nicht.* Nichts verschoben |

Die Bedienelemente (Abschnitt L) laufen im Pruefstand: **49 von 49
bestanden**, darunter die drei neuen Faelle zur Anzeige der aktuellen Entity
und der Fall, dass die Ablehnung des Backends dem Anwender gezeigt wird.
