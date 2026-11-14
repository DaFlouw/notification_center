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
| L2 | Die Kachel *Ereignisse heute* fuehrt zur Historie |
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
| L19 | *Bearbeiten* oeffnet den Editor mit genau dieser Regel, die Liste weicht |
| L20 | *Loeschen* fragt nach und bricht auf Abbruch folgenlos ab |
| L21 | *Loeschen* schickt nach Bestaetigung die richtige Regel |
| L22 | *Regel erstellen* oeffnet einen leeren Editor, ohne *Regel loeschen* |
| L23 | Die Bedingung schaltet zwischen Zustands- und Wertfeldern um |
| L24 | Die Wertquelle laesst sich auf ein Attribut umstellen |
| L25 | Vergleich und Schwelle wandern als Zahl in die Regel |
| L26 | Angeklickte Zustaende landen als Liste in der Regel |
| L27 | Der Meldungstext zeichnet nicht neu, damit der Fokus bleibt |
| L28 | Hysterese und Wartezeit; der Knopf *15 min* wird zu 900 Sekunden |
| L29 | *Speichern* behaelt die Kennung einer bestehenden Regel |
| L30 | *Abbrechen* schliesst den Editor ohne Kommando |
| L31 | *Entity ersetzen* fragt nach und bricht ohne Eingabe ab |
| L32 | *Entity ersetzen* schickt beide Kennungen, ohne Leerzeichen |
| L33 | Die Typ-Pille schickt `domain` mit, *Alle Typen* nimmt sie zurueck |
| L34 | Das Suchfeld der Discovery fragt entprellt ab |
| L35 | *Uebernehmen* meldet genau diese Entity zur Ueberwachung an |
| L36 | *Entity entfernen* steht bei ihren Regeln, fragt nach und schickt die Entity |
| L37 | *Vorschlaege ansehen* holt sie, derselbe Knopf klappt sie wieder ein |
| L38 | Ein Vorschlag uebernimmt Entity und Regel in einem Zug |
| L39 | Ein Vorschlag zeigt Bausteine und nennt seine Begruendung |
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
| L55 | Ein Fehlertext wird als Text gezeigt, nicht als Markup |
| L56 | Deaktivieren schickt die Kennung der gemeinten Meldung mit |
| L57 | Ein deaktivierter Eintrag der Historie laesst sich fortsetzen |
| L58 | Eine Kachel des Dashboards filtert, der zweite Klick hebt es auf |
| L59 | Ein Abschnitt der Regeln laesst sich zu- und wieder aufklappen |
| L60 | Der Knopf fuer Vorschlaege steht nur, wo welche zu erwarten sind |
| L61 | *Alle Typen* gibt es genau einmal; seltene Typen klappen dazu |
| L62 | *Weitere laden* holt die naechsten fuenfzig; ein Filterwechsel beginnt von vorn |
| L63 | Uebernommene Entities ohne Regel stehen eigens in der Regeluebersicht |
| L64 | Der Verweis *Einstellungen* fuehrt zur Integration, ohne neu zu laden |
| L65 | Im Editor: *eine genuegt* und der Typ wandern in die Regel |
| L66 | Im Editor: ein Platzhalter-Knopf haengt ihn an den Meldungstext |
| L67 | Das Panel folgt dem Theme nur in hell und dunkel |

**L46 gehoert an die Anlage.** Der Pruefstand zeigt, *was* die Oberflaeche
abschickt; ob das Backend es annimmt, zeigt nur die laufende Instanz. Die in
L24 bis L38 aufgezeichneten Nutzlasten werden dafuer unveraendert gegen eine
eigens angelegte Wegwerf-Entity gesendet.

`clear_history` wird dabei **nicht** gesendet: es loescht die Historie der
gesamten Installation.

## M -- Verknuepfte Bedingungen

Zwei Testhelfer als Partner: `input_boolean.nc_test_a` traegt die Regel,
`input_boolean.nc_test_b` und `input_select.nc_test_modus` sind Bedingungen.

| ID | Fall | Erwartung |
|----|------|-----------|
| M1 | Regel auf A mit zweiter Bedingung "B ist on", Verknuepfung *alle*; nur A einschalten | Keine Meldung. |
| M2 | Danach B einschalten | Meldung entsteht -- ausgeloest durch den Wechsel des Partners, nicht der eigenen Entity. |
| M3 | B wieder ausschalten, A bleibt an | Meldung endet. |
| M4 | Verknuepfung *eine genuegt*; nur B einschalten | Meldung entsteht. |
| M5 | Zweite Bedingung verneint ("nicht: B ist on"); A an, B aus | Meldung entsteht; mit B an endet sie. |
| M6 | Partner-Entity, die es nicht gibt (`input_boolean.nc_test_gibtsnicht`), verneint | Keine Meldung: unentscheidbar ist nicht wahr. |
| M7 | Bedingung ohne eigene Kennung auf ein Attribut von A | Wird gegen A ausgewertet. |
| M8 | `get_config` nach dem Speichern | `logic` und `extra_conditions` sind enthalten und unveraendert. |
| M9 | B ist nicht uebernommen | Erscheint nicht unter den ueberwachten Entities, die Regel reagiert trotzdem auf B. |

## N -- Systemnachrichten von Home Assistant

Voraussetzung: *Benachrichtigungen von Home Assistant uebernehmen* ist an.

| ID | Fall | Erwartung |
|----|------|-----------|
| N1 | `persistent_notification.create` mit `notification_id: nc_test_sys` | Erscheint in `get_active` mit `source: ha_system`, Typ laut Einstellung. |
| N2 | Dieselbe Kennung erneut mit anderem Text | Derselbe Eintrag, neuer Text, kein zweiter im Log. |
| N3 | `persistent_notification.dismiss` | Eintrag endet. |
| N4 | Sehr langer, mehrzeiliger Text | Auf eine Zeile zusammengezogen, nach 300 Zeichen gekuerzt. |
| N5 | Erzeugen, dann `reload_config_entry` | Eintrag bleibt genau einmal bestehen. |
| N6 | Erzeugen, Einstellung aus, wieder an | Aus: Eintrag endet. An: der Bestand wird neu uebernommen. |
| N7 | Erzeugen, Einstellung aus, in HA verwerfen, Einstellung an | Kein verwaister Eintrag (Issue 16). |
| N8 | `get_history` mit `sources: ["ha_system"]` | Liefert genau die uebernommenen Eintraege. |

## O -- Deaktivieren und Wiederaktivieren

| ID | Fall | Erwartung |
|----|------|-----------|
| O1 | Laufende Regelmeldung per `deactivate_event` | Verschwindet aus `get_active`, Zaehler sinken. |
| O2 | `get_history` danach | Eintrag vorhanden, `close_reason: deactivated`. |
| O3 | Zustand der Entity erneut melden, Bedingung liegt weiter an | Keine neue Meldung. |
| O4 | `reactivate_event` bei anliegender Bedingung | Derselbe Eintrag laeuft wieder, selber Beginn. |
| O5 | Deaktivieren, Bedingung entfaellt, `reactivate_event` | Eintrag endet sofort wieder mit `condition_cleared`; nichts bleibt haengen. |
| O6 | `reactivate_event` auf einen normal beendeten Eintrag | Abgelehnt (`reactivated: false`). |
| O7 | Deaktivieren, Bedingung entfaellt und tritt erneut auf | Neue Meldung mit neuer Kennung. |

## P -- Discovery-Filter und Zaehler

| ID | Fall | Erwartung |
|----|------|-----------|
| P1 | `discover` ohne Filter | Antwort traegt `domain_counts` und `status_counts`. |
| P2 | `discover` mit `status: monitored` | Nur ueberwachte Entities; Anzahl gleich `status_counts.monitored`. |
| P3 | `discover` mit `status: suggested` | Jede hat `has_suggestions: true`. |
| P4 | `discover` mit `search` | Beide Zaehler folgen der Suche. |
| P5 | `get_entity_options` fuer eine nicht uebernommene Entity | Zustaende und Attribute, ohne Vorschlagsanalyse. |

## Q -- Neue Oberflaeche

Im Browser an der laufenden Instanz, nicht im Pruefstand: es geht um das,
was der Pruefstand nicht sieht -- Theme, echte Daten, die Seitenleiste.

| ID | Fall | Erwartung |
|----|------|-----------|
| Q1 | Panel im hellen und im dunklen Theme | Toenungen lesbar, kein weisser Kasten, keine unlesbare Schrift. |
| Q2 | Kachel *Alarme* anklicken, erneut anklicken | Filtert, hebt wieder auf. |
| Q3 | Kachel *Ereignisse heute* | Oeffnet die Historie mit Zeitraum *Heute*. |
| Q4 | Regeln: Geschoss zuklappen, Seite neu laden | Bleibt zugeklappt. |
| Q5 | Regeln: Darstellung *Liste* | Je Raum ein eigenes Feld. |
| Q6 | Regeln: Suche nach einem Raumnamen | Nur dessen Regeln; der Fokus bleibt im Feld. |
| Q7 | Regel bearbeiten und speichern | Der Editor ist eine eigene Seite: Ablauf, dann drei Schritte. Die Regel ist danach unveraendert vorhanden. |
| Q8 | Dashboard: *Deaktivieren*, dann Historie: *Wieder aktivieren* | Beides wirkt ohne Neuladen. |
| Q9 | Schmales Fenster (Handybreite) | Nichts laeuft seitlich aus dem Bild; Reiter und Kacheln brechen um. |
| Q10 | Version | Steht nur auf dem Dashboard, klein am Fuss. |
| Q11 | Farben mit dem eigenen Theme | Blau, nicht die Akzentfarbe des Themes; kuehler Grund, weisse Karten -- wie in `docs/UI-KONZEPT.md`. |
| Q12 | Editor: Zustaende einer Entity | Als Knoepfe, benannt wie in Home Assistant (*offen* statt `on`); im Ablauf steht der Wert von jetzt. |
| Q13 | Dashboard: *Einstellungen* | Oeffnet die Seite der Integration, ohne die Oberflaeche neu zu laden. |
| Q14 | Discovery: Zahlen | *Ueberwacht* minus *Ohne Regel* ergibt die Zahl der Entities mit Regeln; *Weitere laden* zeigt fuenfzig mehr. |
| Q15 | Protokoll nach dem Laden des Panels | Kein Fehler *the name "notification-center-panel" has already been used*. |

## R -- Aussehen nach dem Konzept

Farben, Masse und Schrift, gemessen am gezeichneten Element. Die Sollwerte
stehen in `docs/UI-KONZEPT.md`, Abschnitt 7, und pruefbar in
`tests/panel/konzept.js`; der Pruefstand faehrt jede Ansicht an und vergleicht
`getComputedStyle` damit -- einmal hell, einmal dunkel.

| ID | Bereich | Messpunkte |
|----|---------|------------|
| H1 -- H6 | Kopf und Navigation | Grund, Marke, Schiene, Reiter, Zahl |
| H7 -- H18 | Dashboard | Kacheln, Symbolfelder, Karten, Zeilen, Knopf, Versionszeile |
| H19 -- H25 | Historie | Suchfeld, Zeitraum, Pillen, deaktivierter Eintrag |
| H26 -- H41 | Regeln | Umschalter, Filter, ruhige und meldende Regel, Bausteine, Verweise |
| H42 -- H52 | Discovery | Status, Typ-Pillen, Kennzeichen, Knoepfe, offener Vorschlag |
| H53 -- H70 | Regel-Editor | Ablauf, Schritte, Bedingungen, Auswahlknoepfe, Typwahl |
| H71 | Dashboard | Kennzeichen der Systemnachricht |

Dazu laeuft in der CI `tests/frontend/konzept.test.js`: die Palette im
Konzept, in `konzept.js` und im Stylesheet muss dieselbe sein, und das
Stylesheet darf an keiner Farbe des Themes haengen.

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
* **K6** Regeln stehen unter ihrem Geschoss und darin unter ihrem Raum,
  darunter eingerueckt die Entities. *Ohne Geschoss / Ohne Raum* steht am
  Ende. Keine Regel fehlt, jede traegt genau einen Bearbeiten-Knopf.
* **K7** Beim Bearbeiten einer Regel an einer Entity mit zwei Regeln traegt
  deren Zeile *wird bearbeitet* und keinen Knopf mehr, die zweite Regel
  derselben Entity behaelt ihren. Das Formular ist mit den echten Werten gefuellt.
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

---

## Durchlauf vom 14.11.2026, Version 1.5.0-rc1

Gegen die laufende Instanz, mit eigens angelegten Helfern (`NC Test …`) und
Testregeln; danach vollstaendig aufgeraeumt und `get_config` gegen den
Ausgangsstand verglichen.

| Abschnitt | Ausgefuehrt | Ergebnis |
|-----------|-------------|----------|
| A | A3 | bestanden |
| C | C3 -- C7, C11 | bestanden |
| D | D1 -- D6 | bestanden |
| E | E1 -- E3, E6, E7 | bestanden |
| F | F1 -- F5, F7 | bestanden |
| G | G1, G3, G4 | bestanden |
| H | H1 -- H3, H5, H6 | bestanden |
| I | I1, I3, I5 | bestanden |
| J | J1, J2 | bestanden |
| M | M1 -- M9 | bestanden |
| N | N1 -- N8 | bestanden |
| O | O1 -- O7 | bestanden |
| P | P1 -- P5 | bestanden |

Nicht ausgefuehrt: die zeitgebundenen Faelle (C9, C10, F6, J4), B5 -- B8, E4,
E5, F8, H4, H7, H8, I2, I4, J3 sowie K und Q, die den Browser an der Anlage
brauchen.

Ein Befund am Rand: im Protokoll stand *Failed to execute 'define' on
'CustomElementRegistry': the name "notification-center-panel" has already
been used*. Home Assistant hatte das Modul zweimal geladen. Behoben in rc2
(Fall Q15).

## Pruefstand vom 14.11.2026, Version 1.5.0-rc2

Abschnitte L und R im Pruefstand: **133 von 133 bestanden** -- 62
Bedienungsfaelle und 71 Messpunkte, jeder hell und dunkel gemessen.
