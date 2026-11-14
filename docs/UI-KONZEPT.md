# Gestaltungskonzept des Panels

Stand: 1.5.0-rc2. Dieses Dokument beschreibt, wie das Panel aussieht und warum.
Es ist verbindlich: weicht die Umsetzung ab, ist die Umsetzung falsch oder
dieses Dokument wird geändert – nicht stillschweigend eines von beiden.

Dafür sorgen zwei Tests. `tests/frontend/konzept.test.js` vergleicht die
Palette hier mit `styles.js` und läuft bei jedem Push. Die Fälle H1 bis H71 des
Prüfstands (`tests/panel/index.html`) messen im Browser an den gezeichneten
Elementen nach, hell und dunkel. Beide lesen dieselbe Quelle,
`tests/panel/konzept.js`; die beiden Tabellen unten werden daraus erzeugt
(`node tests/panel/konzept-doku.js`).

## 1 Leitgedanken

1. **Der Zustand ist an der Form ablesbar, nicht erst am Text.** Jede
   Dringlichkeit hat eine eigene, zurückhaltende Tönung, die sich durch
   Kacheln, Zeilen, Pillen und Regeln zieht. Alles Besondere – Systemnachricht,
   Vorschlag, verknüpfte Regel – trägt eine vierte, violette.
2. **Farbe meldet, sie schmückt nicht.** Flächen sind weiß auf kühlem Grund.
   Getönt ist nur, was gerade etwas zu sagen hat: eine laufende Meldung, eine
   meldende Regel, ein offener Vorschlag.
3. **Die Farben stehen fest.** Sie werden nicht aus dem Theme von Home
   Assistant abgeleitet. Mit einem türkisen Theme wurde aus dem Blau Türkis
   und aus den kühlen Flächen Grau; die Tönungen der Dringlichkeiten
   verschoben sich mit. Vom Theme übernimmt das Panel nur eines: hell oder
   dunkel.
4. **Ein Weg je Aufgabe.** Keine zwei Bedienelemente für dasselbe
   nebeneinander, kein Knopf, der ins Leere führt.
5. **Sprache statt Technik.** »ist nicht«, »eine genügt«, »5 min lang« – der
   Editor fragt, was man will, nicht wie die Regel gespeichert wird.

## 2 Palette

Jede Farbe heißt im Stylesheet `--nc-<Name>`.

<!-- PALETTE:ANFANG -->
| Name | Hell | Dunkel | Wofür |
| --- | --- | --- | --- |
| `ground` | `#f2f5fa` | `#111418` | Seitengrund |
| `surface` | `#ffffff` | `#1c2128` | Karten, Knöpfe, Bausteine |
| `text` | `#1b2430` | `#e6e9ee` | Text |
| `mid` | `#455468` | `#9aa4b2` | Reiter, Abschnittstitel, Dauer |
| `muted` | `#5a6778` | `#9aa4b2` | Nebentext, Kennungen, Platzhalter |
| `faint` | `#6b7686` | `#9aa4b2` | Versionszeile |
| `border` | `#e1e7ef` | `#2c333d` | Rahmen der Karten |
| `control` | `#d5dce6` | `#3a424e` | Rahmen der Knöpfe und Felder |
| `divider` | `#e9eef4` | `#2c333d` | Trennlinie zwischen Entities |
| `dashed` | `#c9d1dc` | `#3a424e` | gestrichelter Rahmen, unerfüllter Punkt |
| `nav` | `#e4eaf2` | `#232a33` | Grund der Navigation, neutrale Pille |
| `subtle` | `#f2f5fa` | `#111418` | Suchfeld, Umschalter, Wertbaustein |
| `quiet` | `#f6f8fb` | `#232a33` | ruhige Regel |
| `group` | `#f3f6fa` | `#171b21` | Raumfeld, Ablauf, Bedingungskarte |
| `selected` | `#1b2430` | `#e6e9ee` | gewählter Umschalter |
| `on-selected` | `#ffffff` | `#111418` | Schrift auf gewähltem Umschalter |
| `accent` | `#0277bd` | `#0277bd` | Hauptknopf, gewählter Reiter, Marke |
| `accent-hover` | `#01579b` | `#039be5` | Hauptknopf und Verweis unter dem Zeiger |
| `accent-chip` | `#e3f3fd` | `#1d4a63` | leiser Knopf, gewählte Pille |
| `accent-ink` | `#0b5580` | `#8fd3ff` | Schrift darauf |
| `link` | `#0277bd` | `#6cc4f5` | Verweis |
| `count-selected` | `#01579b` | `#8fd3ff` | Zahl am gewählten Reiter |
| `alarm` | `#db4437` | `#db4437` | Punkt |
| `alarm-tile` | `#fdeceb` | `#3a1f1e` | Kachel, Typwahl |
| `alarm-soft` | `#fef6f5` | `#2a1b1b` | Zeile, meldende Regel |
| `alarm-chip` | `#f9d2ce` | `#5a2a27` | Pille, Symbolfeld, Filter |
| `alarm-ink` | `#9f1f17` | `#ff9d94` | Schrift |
| `warning` | `#ffa600` | `#ffa600` | Punkt |
| `warning-tile` | `#fff3da` | `#3a2f17` | Kachel, Typwahl |
| `warning-soft` | `#fffaf0` | `#2a2416` | Zeile, meldende Regel |
| `warning-chip` | `#ffe2a8` | `#5a4516` | Pille, Symbolfeld, Filter |
| `warning-ink` | `#7a4a00` | `#ffcf70` | Schrift |
| `info` | `#039be5` | `#039be5` | Punkt |
| `info-tile` | `#e3f3fd` | `#16303f` | Kachel, Typwahl |
| `info-soft` | `#f3f9fe` | `#18242c` | Zeile, meldende Regel |
| `info-chip` | `#c4e5fa` | `#1d4a63` | Pille, Symbolfeld, Filter |
| `info-ink` | `#0b5580` | `#8fd3ff` | Schrift |
| `ok` | `#2e9e4f` | `#2e9e4f` | erfüllter Punkt |
| `ok-chip` | `#dff3e4` | `#1d3a27` | »überwacht«, »aktiv« |
| `ok-ink` | `#1d6b34` | `#8fdba5` | Schrift |
| `special` | `#4a3fa3` | `#c2b9ff` | gewählte Verknüpfung |
| `special-soft` | `#f6f4fe` | `#211f33` | offener Vorschlag, weitere Bedingung |
| `special-track` | `#f0eefc` | `#262341` | Grund des Verknüpfungs-Umschalters |
| `special-pill` | `#e9e6fb` | `#322c57` | »HA«, »3 Bedingungen« |
| `special-chip` | `#e0dbf9` | `#322c57` | »Vorschläge ansehen«, Filter »Verknüpft« |
| `special-line` | `#d9d5f3` | `#3d3768` | Rahmen des Entity-Felds |
| `special-dash` | `#b9b2ea` | `#5a519a` | gestrichelter Knopf |
| `special-ink` | `#4a3fa3` | `#c2b9ff` | Schrift |
<!-- PALETTE:ENDE -->

Die Tönungen folgen je Dringlichkeit demselben Muster: `-tile` für die große
Fläche (Kachel, Typwahl, Ergebnis im Ablauf), `-soft` für die Zeile, `-chip`
für die Pille und `-ink` für die Schrift darauf. Weiß auf einer Akzentfläche
bleibt in beiden Modi weiß.

## 3 Schrift und Maße

| Was | Wert |
| --- | --- |
| Schrift | Roboto, ersatzweise die Systemschrift; Kennungen in Roboto Mono 12 px |
| Grundgröße | 15 px, Zeilenhöhe 1,4 |
| Seitentitel im Editor | 24 px, Gewicht 500 |
| Zahl der Kachel | 40 px, Gewicht 500, Tabellenziffern |
| Kartentitel, Raum | 16 px, Gewicht 500 |
| Abschnittstitel | 13 px, Gewicht 700, Versalien, Laufweite 0,04 em |
| Knopf, Verweis, Umschalter | 14 px, Gewicht 500 |
| Baustein, Nebentext | 13 px |
| Pille | 12 px, Gewicht 700 |
| Inhaltsbreite | höchstens 1120 px, Rand 24 px (schmal: 16 px) |
| Abstand zwischen Abschnitten | 24 px |
| Radius | Karte 20 px · Feld im Ablauf, Bedingung 16 px · Zeile, Regel 14 px · Vorschlag 12 px · Baustein 8 px · Knopf und Pille rund |
| Höhe | Knopf und Suchfeld 44 px · Auswahlknopf im Editor 40 px · Umschalter und Filter 36 px · Platzhalter 32 px |

## 4 Bausteine

- **Karte** – weiß, 1 px Rahmen (`border`), Radius 20 px. Ohne Schatten.
- **Zeile** – Radius 14 px; getönt (`-soft`) nur, solange die Meldung läuft.
- **Pille** – der Typ einer Meldung oder ein Kennzeichen; nie anklickbar.
- **Baustein** – ein Stück einer Bedingung, »Zustand ist **on**«; der Wert fett.
- **Knopf** – drei Stufen: gefüllt (`accent`) für die eine Hauptsache der
  Ansicht, leise (`accent-chip`) für eine naheliegende Nebensache, umrandet für
  alles Übrige. Violett (`special-chip`) nur für Vorschläge.
- **Verweis** – blau ohne Unterstreichung, für Wege zu einer anderen Ansicht
  (»Regeln«, »Bearbeiten«).
- **Umschalter** – zwei Spielarten. *Was* man sieht (Zeitraum, Status, Alle):
  die Wahl dunkel gefüllt. *Wie* man es sieht (Karten oder Liste, nach Raum
  oder Typ): die Wahl nur weiß angehoben.
- **Suchfeld** – Pille mit Lupe auf `subtle`, ohne Rahmen.
- **Symbole** – Leuchte für Alarm, Dreieck für Warnung, Kreis mit i für Info.

## 5 Ansichten

### 5.1 Kopf

Links Marke und Name, rechts die vier Reiter als Pillen in einer Schiene. Der
gewählte Reiter ist gefüllt. Dashboard und Regeln tragen ihre Zahl.

### 5.2 Dashboard

Vier Kacheln: Alarme, Warnungen, Infos, Ereignisse heute. Die ersten drei sind
zugleich Filter – ein Klick zeigt nur diese Dringlichkeit, ein zweiter hebt
ihn auf. Die vierte führt in die Historie von heute. Darunter je
Dringlichkeit eine Karte mit den laufenden Meldungen: Symbol, Text, Ort und
Beginn, Dauer, »Deaktivieren«.

Unten rechts, bewusst unauffällig und nur hier: die Version und der Verweis
»Einstellungen« zur Seite der Integration in Home Assistant.

### 5.3 Historie

Filterkarte mit Suchfeld, Zeitraum als Umschalter und den übrigen Filtern als
Auswahlfelder. Die Einträge sind nach Tagen gegliedert. Was noch läuft, ist
getönt und trägt »aktiv«; was von Hand deaktiviert wurde, hat einen
gestrichelten Rahmen, das Kennzeichen »deaktiviert« und den Knopf »Wieder
aktivieren«. Laufende Einträge lassen sich nicht löschen.

### 5.4 Regeln

Die Filterkarte der Umsetzung gilt, nicht die des ersten Entwurfs:

- Suchfeld über Regel, Entity und Raum;
- Darstellung »Karten | Liste« und Gliederung »Nach Raum | Nach Typ« als leise
  Umschalter, daneben »Alle einklappen«;
- darunter die Filter als Pillen in der Farbe dessen, was sie zeigen: Alle,
  Alarm, Warnung, Info, Verknüpft, Abgeschaltet – jeweils mit Anzahl, und nur,
  wenn es etwas zu zeigen gibt.

Darunter:

1. **Meldet gerade** – was jetzt meldet, angeheftet über allem, eine Zeile je
   Regel mit Punkt, Bedingung, Ort und Dauer.
2. **Die Gliederung** – je Etage ein auf- und zuklappbarer Abschnitt mit der
   Zahl der Regeln und Räume und dem Hinweis, wie viele melden.
3. **Karten** – eine Karte je Raum, **über die volle Breite**. Je Entity ihr
   Name und ihre Kennung, darunter je Regel ein Block: Typ, Zustand (»ruhig«
   oder »meldet seit …«), die Bedingungen als Bausteine in einer Zeile,
   rechts »Bearbeiten« und »Löschen«. Eine ruhige Regel liegt auf `quiet`,
   eine meldende auf der Tönung ihres Typs.
4. **Liste** – ab 24 Regeln die Voreinstellung: eine Zeile je Regel, die Räume
   als eigene Felder. Ein Raum mit mehr als neun Regeln zeigt sechs und den
   Knopf »n weitere in Raum zeigen«; wer sucht oder filtert, sieht alle.
5. **Übernommen, aber ohne Regel** – am Ende, nur wenn es solche Entities
   gibt. Sie werden beobachtet und melden nie; ohne diesen Abschnitt wäre die
   Differenz zwischen »überwacht« und den Regeln nirgends zu sehen. Je Zeile
   »Regel erstellen« und »Entfernen«.

Die Seite einer Entity zeigt ihre Regeln als Blöcke, darunter »Regel
erstellen«, »Entity ersetzen« und, abgesetzt rechts, »Entity entfernen«.

### 5.5 Regel-Editor

Eine eigene Seite, kein Formular unter der Liste. Oben »← Alle Regeln«, der
Titel »Regel für …« mit der Kennung, rechts »Abbrechen« und »Speichern«.

1. **So arbeitet die Regel** – der Ablauf als Bild, von links nach rechts:
   die Bedingungen (jede mit einem Punkt – grün, wenn sie jetzt gilt – und dem
   Wert in diesem Augenblick), verbunden durch UND oder ODER; die Wartezeit;
   das Ergebnis in der Farbe des Typs mit dem Meldungstext. Rechts oben, ob
   die Regel in diesem Moment zutrifft.
2. **Schritt 1, Wann soll gemeldet werden?** – je Bedingung eine Karte. Die Art
   als Umschalter: ist, ist nicht, wechselt zu, Zahlenwert. Die Zustände als
   Knöpfe zum Anklicken, benannt wie in Home Assistant; bei einem Attribut als
   Quelle ein Textfeld. Weitere Bedingungen liegen auf Violett, tragen ihr
   Entity-Feld und ein Kreuz zum Entfernen. Gibt es mehr als eine, steht
   darüber »alle zusammen | eine genügt«.
3. **Schritt 2, Wie lange muss das anhalten?** – sofort melden, 1, 5, 15 min,
   1 h als Knöpfe, daneben ein Minutenfeld; darunter ein Satz, was das
   bedeutet.
4. **Schritt 3, Was soll erscheinen?** – der Typ als drei Kacheln mit einem
   Halbsatz, wofür er gedacht ist; der Text; die Platzhalter als Knöpfe.

Unten links »Regel löschen« (nur bei einer vorhandenen Regel), rechts noch
einmal »Abbrechen« und »Speichern«.

### 5.6 Discovery

Die Filterkarte:

- Suchfeld über Name und Kennung;
- Status als Umschalter mit Anzahl: Alle, Überwacht, Ohne Regel, Mit
  Vorschlag. Ein Status, hinter dem nichts steht, entfällt;
- die Typen als Pillen mit Anzahl – die **einzige** Typ-Auswahl. Gezeigt
  werden »Alle Typen« und die sechs häufigsten; »n weitere Typen« klappt den
  Rest dazu.

Die Treffer sind nach Raum gegliedert. Je Zeile Name, Kennung und Gerät, der
aktuelle Wert, dann:

- **überwacht** – das Kennzeichen »überwacht · n Regeln« (oder, in Gelb,
  »überwacht · keine Regel«) und der Verweis »Regeln«. Entfernt wird eine
  Entity von der Seite ihrer Regeln aus, nicht hier.
- **nicht überwacht** – »Übernehmen«, umrandet. Davor, violett, »Vorschläge
  ansehen« – **nur, wenn es welche gibt.**

Ein geöffneter Vorschlag tönt die ganze Zeile violett. Darin je Vorschlag
eine weiße Karte: Typ, die Bedingung in Bausteinen, darunter als Satz »Warum
dieser Vorschlag: …« und die zwei Antworten »Mit dieser Regel übernehmen«
(gefüllt) und »Ohne Regel übernehmen«.

Geladen werden fünfzig Treffer. Kennt das Backend mehr, steht am Ende
»n von m« und »Weitere laden«; jeder Klick holt fünfzig dazu, jeder Wechsel
von Suche, Status oder Typ beginnt wieder bei fünfzig.

## 6 Dunkelmodus

Meldet Home Assistant ein dunkles Theme, gilt die rechte Spalte der Palette.
Der Aufbau bleibt derselbe; die Tönungen werden gedeckt statt pastell, die
Schrift darauf hell. Der gewählte Umschalter kehrt sich um – hell gefüllt mit
dunkler Schrift.

## 7 Messpunkte

Was der Prüfstand an den gezeichneten Elementen nachmisst. Eine Farbe steht
mit ihrem Namen aus der Palette da und wird hell und dunkel geprüft.

<!-- MASSE:ANFANG -->
| Nr. | Ansicht | Was | Soll |
| --- | --- | --- | --- |
| H1 | Dashboard | Seitengrund und Schrift | background-color: `ground` · color: `text` · font-size: `15px` |
| H2 | Dashboard | Marke | background-color: `accent` · width: `40px` · height: `40px` · border-top-left-radius: `12px` |
| H3 | Dashboard | Navigation | background-color: `nav` · border-top-left-radius: `999px` |
| H4 | Dashboard | gewählter Reiter | background-color: `accent` · color: `#ffffff` · min-height: `44px` · font-weight: `500` |
| H5 | Dashboard | übrige Reiter | color: `mid` |
| H6 | Dashboard | Zahl am gewählten Reiter | background-color: `surface` · color: `count-selected` · font-size: `12px` |
| H7 | Dashboard | Kachel Alarm | background-color: `alarm-tile` · color: `alarm-ink` · border-top-left-radius: `20px` |
| H8 | Dashboard | Kachel Warnung | background-color: `warning-tile` · color: `warning-ink` |
| H9 | Dashboard | Kachel Info | background-color: `info-tile` · color: `info-ink` |
| H10 | Dashboard | Kachel Ereignisse | background-color: `surface` · border-top-color: `border` |
| H11 | Dashboard | Zahl der Kachel | font-size: `40px` · font-weight: `500` |
| H12 | Dashboard | Symbolfeld Alarm | background-color: `alarm-chip` · width: `36px` · border-top-left-radius: `12px` |
| H13 | Dashboard | Karte | background-color: `surface` · border-top-color: `border` · border-top-left-radius: `20px` |
| H14 | Dashboard | Zeile Alarm | background-color: `alarm-soft` · border-top-left-radius: `14px` |
| H15 | Dashboard | Zeile Warnung | background-color: `warning-soft` |
| H16 | Dashboard | Zeile Info | background-color: `info-soft` |
| H17 | Dashboard | Knopf Deaktivieren | background-color: `surface` · border-top-color: `control` · min-height: `44px` · font-size: `14px` |
| H18 | Dashboard | Versionszeile | color: `faint` · font-size: `12px` |
| H19 | Historie | Suchfeld | background-color: `subtle` · height: `44px` · border-top-left-radius: `999px` |
| H20 | Historie | gewählter Zeitraum | background-color: `selected` · color: `on-selected` · min-height: `36px` |
| H21 | Historie | Pille Alarm | background-color: `alarm-chip` · color: `alarm-ink` · font-size: `12px` · font-weight: `700` |
| H22 | Historie | Pille Warnung | background-color: `warning-chip` · color: `warning-ink` |
| H23 | Historie | Pille Info | background-color: `info-chip` · color: `info-ink` |
| H24 | Historie | deaktivierter Eintrag | outline-style: `dashed` · outline-color: `dashed` |
| H25 | Historie | Knopf Wieder aktivieren | background-color: `accent-chip` · color: `accent-ink` |
| H26 | Regeln | gewählte Darstellung | background-color: `surface` · color: `text` |
| H27 | Regeln | Filter Alle, gewählt | background-color: `selected` · color: `on-selected` · min-height: `36px` |
| H28 | Regeln | Filter Alarm | background-color: `alarm-chip` · color: `alarm-ink` |
| H29 | Regeln | Filter Warnung | background-color: `warning-chip` · color: `warning-ink` |
| H30 | Regeln | Filter Info | background-color: `info-chip` · color: `info-ink` |
| H31 | Regeln | Filter Verknüpft | background-color: `special-chip` · color: `special-ink` |
| H32 | Regeln | ruhige Regel | background-color: `quiet` · border-top-left-radius: `14px` |
| H33 | Regeln | meldende Regel, Alarm | background-color: `alarm-soft` |
| H34 | Regeln | meldende Regel, Info | background-color: `info-soft` |
| H35 | Regeln | Baustein einer Bedingung | background-color: `surface` · font-size: `13px` · border-top-left-radius: `8px` |
| H36 | Regeln | Verweis Bearbeiten | color: `link` · font-size: `14px` · font-weight: `500` |
| H37 | Regeln | Pille Bedingungen | background-color: `special-pill` · color: `special-ink` |
| H38 | Regeln | Verknüpfungswort | color: `special-ink` · font-size: `11px` · font-weight: `700` |
| H39 | Regeln | Trennlinie zwischen Entities | border-top-color: `divider` |
| H40 | Regeln | angeheftete Zeile, Alarm | background-color: `alarm-soft` |
| H41 | Regeln | Punkt Alarm | background-color: `alarm` · width: `10px` |
| H42 | Discovery | gewählter Status | background-color: `selected` · color: `on-selected` |
| H43 | Discovery | Typ, gewählt | background-color: `accent-chip` · color: `accent-ink` · min-height: `36px` |
| H44 | Discovery | Typ, nicht gewählt | background-color: `surface` · border-top-color: `control` · color: `text` · font-weight: `400` |
| H45 | Discovery | Kennzeichen überwacht | background-color: `ok-chip` · color: `ok-ink` |
| H46 | Discovery | Wert der Entity | background-color: `subtle` · font-weight: `500` |
| H47 | Discovery | Knopf Vorschläge | background-color: `special-chip` · color: `special-ink` · min-height: `44px` |
| H48 | Discovery | Knopf Übernehmen | background-color: `surface` · border-top-color: `control` · color: `text` |
| H49 | Discovery, Vorschlag offen | Entity mit offenem Vorschlag | background-color: `special-soft` · border-top-left-radius: `14px` |
| H50 | Discovery, Vorschlag offen | Vorschlag | background-color: `surface` · border-top-left-radius: `12px` |
| H51 | Discovery, Vorschlag offen | Knopf Mit dieser Regel übernehmen | background-color: `accent` · color: `#ffffff` · min-height: `44px` |
| H52 | Discovery, Vorschlag offen | Begründung | color: `mid` · font-size: `13px` |
| H53 | Regel-Editor | Titel | font-size: `24px` · font-weight: `500` |
| H54 | Regel-Editor | Knopf Speichern | background-color: `accent` · color: `#ffffff` · min-height: `44px` |
| H55 | Regel-Editor | Feld der Bedingungen im Ablauf | background-color: `group` · border-top-left-radius: `16px` |
| H56 | Regel-Editor | Bedingung im Ablauf | background-color: `surface` · border-top-left-radius: `12px` |
| H57 | Regel-Editor | Ergebnis im Ablauf | background-color: `warning-tile` |
| H58 | Regel-Editor | Schrittnummer | background-color: `accent-chip` · color: `accent-ink` · width: `28px` |
| H59 | Regel-Editor | erste Bedingung | background-color: `group` · border-top-left-radius: `16px` |
| H60 | Regel-Editor | weitere Bedingung | background-color: `special-soft` |
| H61 | Regel-Editor | gewählter Zustand | background-color: `accent-chip` · color: `accent-ink` · border-top-color: `accent` · border-top-width: `2px` · min-height: `40px` |
| H62 | Regel-Editor | nicht gewählter Zustand | background-color: `surface` · border-top-color: `control` · border-top-width: `1px` |
| H63 | Regel-Editor | gewählte Verknüpfung | background-color: `special` · color: `surface` |
| H64 | Regel-Editor | Grund des Verknüpfungs-Umschalters | background-color: `special-track` |
| H65 | Regel-Editor | Knopf Weitere Bedingung | border-top-style: `dashed` · border-top-color: `special-dash` · color: `special-ink` |
| H66 | Regel-Editor | gewählter Typ | background-color: `warning-tile` · color: `warning-ink` · border-top-color: `warning-ink` · border-top-width: `2px` |
| H67 | Regel-Editor | nicht gewählter Typ | background-color: `alarm-tile` · color: `alarm-ink` |
| H68 | Regel-Editor | Meldungstext | min-height: `48px` · border-top-left-radius: `14px` · border-top-color: `control` |
| H69 | Regel-Editor | Platzhalter-Knopf | background-color: `subtle` · min-height: `32px` · font-size: `13px` |
| H70 | Regel-Editor | Knopf Regel löschen | color: `alarm-ink` · background-color: `rgba(0, 0, 0, 0)` |
| H71 | Dashboard | Kennzeichen Systemnachricht | background-color: `special-pill` · color: `special-ink` · font-size: `11px` |
<!-- MASSE:ENDE -->

## 8 Änderungen gegenüber dem ersten Entwurf

| Was | Entwurf | Jetzt | Grund |
| --- | --- | --- | --- |
| Farben | fest | fest, auch in der Umsetzung | Die Ableitung aus dem Theme hat sie verfälscht. |
| Regeln, Filter | »Alle · Meldet gerade · Verknüpft« | Darstellung, Gliederung, Filter nach Typ | Die Umsetzung hat sich als die bessere erwiesen. |
| Regeln, Karten | mehrere Spalten | eine Spalte, volle Breite | Eine Regel mit mehreren Bedingungen braucht die Zeile. |
| Regeln ohne Regel | – | eigener Abschnitt | Erklärt die Differenz zu »überwacht«. |
| Regel-Editor | Formular unter der Liste | eigene Seite mit Ablauf | Zu technisch; siehe Leitgedanke 5. |
| Discovery, Status | drei | vier, mit »Ohne Regel« | wie oben |
| Discovery, Typen | Pillen | Pillen, der Rest aufklappbar; kein Auswahlfeld | Zwei Auswahlen für dasselbe verwirren. |
| Discovery, Vorschläge | »1 Vorschlag ansehen« | »Vorschläge ansehen«, nur wo es welche gibt | Die Zahl kennt erst die Analyse; ein Knopf ohne Ergebnis ist Lärm. |
| Discovery, Nachladen | »Weitere Bereiche laden« | »n von m · Weitere laden«, je fünfzig | Bereiche sind keine Ladeeinheit; Treffer schon. |
| Discovery, Entfernen | – | auf der Seite der Regeln | Neben »Übernehmen« lag es zu nah. |
| Dashboard | Version | Version und »Einstellungen« | Weg zur Integration, unauffällig. |
