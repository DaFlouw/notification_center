/**
 * Das Gestaltungskonzept in pruefbarer Form.
 *
 * ``docs/UI-KONZEPT.md`` beschreibt, wie das Panel aussehen soll. Diese Datei
 * enthaelt dieselben Angaben so, dass ein Test sie lesen kann: die Palette
 * und, je Ansicht, was ein bestimmtes Element an Farbe und Mass zu tragen hat.
 *
 * Zwei Tests benutzen sie:
 *
 * - ``tests/frontend/konzept.test.js`` (Node) vergleicht die Palette mit
 *   ``styles.js`` und mit den Tabellen im Konzept. Laeuft in der CI.
 * - Die Faelle H1 ff. des Pruefstands (``interaktion.js``) messen im Browser
 *   am gezeichneten Element nach -- hell und dunkel.
 *
 * Wer eine Farbe aendert, aendert sie hier, im Konzept und in ``styles.js``.
 * Vergisst er eine der drei Stellen, sagt es ihm der Test.
 */

/** Jede Farbe mit ihrem Wert im hellen und im dunklen Modus. */
export const PALETTE = {
  ground: ["#f2f5fa", "#111418", "Seitengrund"],
  surface: ["#ffffff", "#1c2128", "Karten, Knöpfe, Bausteine"],
  text: ["#1b2430", "#e6e9ee", "Text"],
  mid: ["#455468", "#9aa4b2", "Reiter, Abschnittstitel, Dauer"],
  muted: ["#5a6778", "#9aa4b2", "Nebentext, Kennungen, Platzhalter"],
  faint: ["#6b7686", "#9aa4b2", "Versionszeile"],
  border: ["#e1e7ef", "#2c333d", "Rahmen der Karten"],
  control: ["#d5dce6", "#3a424e", "Rahmen der Knöpfe und Felder"],
  divider: ["#e9eef4", "#2c333d", "Trennlinie zwischen Entities"],
  dashed: ["#c9d1dc", "#3a424e", "gestrichelter Rahmen, unerfüllter Punkt"],
  nav: ["#e4eaf2", "#232a33", "Grund der Navigation, neutrale Pille"],
  subtle: ["#f2f5fa", "#111418", "Suchfeld, Umschalter, Wertbaustein"],
  quiet: ["#f6f8fb", "#232a33", "ruhige Regel"],
  group: ["#f3f6fa", "#171b21", "Raumfeld, Ablauf, Bedingungskarte"],
  selected: ["#1b2430", "#e6e9ee", "gewählter Umschalter"],
  "on-selected": ["#ffffff", "#111418", "Schrift auf gewähltem Umschalter"],

  accent: ["#0277bd", "#0277bd", "Hauptknopf, gewählter Reiter, Marke"],
  "accent-hover": ["#01579b", "#039be5", "Hauptknopf und Verweis unter dem Zeiger"],
  "accent-chip": ["#e3f3fd", "#1d4a63", "leiser Knopf, gewählte Pille"],
  "accent-ink": ["#0b5580", "#8fd3ff", "Schrift darauf"],
  link: ["#0277bd", "#6cc4f5", "Verweis"],
  "count-selected": ["#01579b", "#8fd3ff", "Zahl am gewählten Reiter"],

  alarm: ["#db4437", "#db4437", "Punkt"],
  "alarm-tile": ["#fdeceb", "#3a1f1e", "Kachel, Typwahl"],
  "alarm-soft": ["#fef6f5", "#2a1b1b", "Zeile, meldende Regel"],
  "alarm-chip": ["#f9d2ce", "#5a2a27", "Pille, Symbolfeld, Filter"],
  "alarm-ink": ["#9f1f17", "#ff9d94", "Schrift"],

  warning: ["#ffa600", "#ffa600", "Punkt"],
  "warning-tile": ["#fff3da", "#3a2f17", "Kachel, Typwahl"],
  "warning-soft": ["#fffaf0", "#2a2416", "Zeile, meldende Regel"],
  "warning-chip": ["#ffe2a8", "#5a4516", "Pille, Symbolfeld, Filter"],
  "warning-ink": ["#7a4a00", "#ffcf70", "Schrift"],

  info: ["#039be5", "#039be5", "Punkt"],
  "info-tile": ["#e3f3fd", "#16303f", "Kachel, Typwahl"],
  "info-soft": ["#f3f9fe", "#18242c", "Zeile, meldende Regel"],
  "info-chip": ["#c4e5fa", "#1d4a63", "Pille, Symbolfeld, Filter"],
  "info-ink": ["#0b5580", "#8fd3ff", "Schrift"],

  ok: ["#2e9e4f", "#2e9e4f", "erfüllter Punkt"],
  "ok-chip": ["#dff3e4", "#1d3a27", "»überwacht«, »aktiv«"],
  "ok-ink": ["#1d6b34", "#8fdba5", "Schrift"],

  special: ["#4a3fa3", "#c2b9ff", "gewählte Verknüpfung"],
  "special-soft": ["#f6f4fe", "#211f33", "offener Vorschlag, weitere Bedingung"],
  "special-track": ["#f0eefc", "#262341", "Grund des Verknüpfungs-Umschalters"],
  "special-pill": ["#e9e6fb", "#322c57", "»HA«, »3 Bedingungen«"],
  "special-chip": ["#e0dbf9", "#322c57", "»Vorschläge ansehen«, Filter »Verknüpft«"],
  "special-line": ["#d9d5f3", "#3d3768", "Rahmen des Entity-Felds"],
  "special-dash": ["#b9b2ea", "#5a519a", "gestrichelter Knopf"],
  "special-ink": ["#4a3fa3", "#c2b9ff", "Schrift"],
};

/** Der Wert einer Farbe; ``dunkel`` waehlt die zweite Spalte. */
export function farbe(name, dunkel = false) {
  const eintrag = PALETTE[name];
  if (!eintrag) throw new Error(`unbekannte Farbe: ${name}`);
  return eintrag[dunkel ? 1 : 0];
}

/** ``#rrggbb`` in der Schreibweise, die ``getComputedStyle`` liefert. */
export function alsRgb(hex) {
  const zahl = parseInt(hex.slice(1), 16);
  return `rgb(${(zahl >> 16) & 255}, ${(zahl >> 8) & 255}, ${zahl & 255})`;
}

/**
 * Was am gezeichneten Element nachgemessen wird.
 *
 * ``seite`` ist die Ansicht, ``auswahl`` das Element darin. In ``soll`` steht
 * je CSS-Eigenschaft der Name einer Farbe aus der Palette oder, mit Einheit
 * oder als Schluesselwort, ein fester Wert. Weiss auf einer Akzentflaeche ist
 * in beiden Modi weiss und steht deshalb als ``#ffffff`` da.
 */
export const MASSE = [
  // -- Rahmen: Kopf und Navigation ---------------------------------------
  { id: "H1", seite: "dashboard", was: "Seitengrund und Schrift", auswahl: ":host",
    soll: { "background-color": "ground", color: "text", "font-size": "15px" } },
  { id: "H2", seite: "dashboard", was: "Marke", auswahl: ".brand-mark",
    soll: { "background-color": "accent", width: "40px", height: "40px", "border-top-left-radius": "12px" } },
  { id: "H3", seite: "dashboard", was: "Navigation", auswahl: "header nav",
    soll: { "background-color": "nav", "border-top-left-radius": "999px" } },
  { id: "H4", seite: "dashboard", was: "gewählter Reiter", auswahl: 'nav button[aria-current="page"]',
    soll: { "background-color": "accent", color: "#ffffff", "min-height": "44px", "font-weight": "500" } },
  { id: "H5", seite: "dashboard", was: "übrige Reiter", auswahl: "nav button:not([aria-current])",
    soll: { color: "mid" } },
  { id: "H6", seite: "dashboard", was: "Zahl am gewählten Reiter", auswahl: 'nav button[aria-current="page"] .count',
    soll: { "background-color": "surface", color: "count-selected", "font-size": "12px" } },

  // -- Dashboard ----------------------------------------------------------
  { id: "H7", seite: "dashboard", was: "Kachel Alarm", auswahl: ".tile.alarm",
    soll: { "background-color": "alarm-tile", color: "alarm-ink", "border-top-left-radius": "20px" } },
  { id: "H8", seite: "dashboard", was: "Kachel Warnung", auswahl: ".tile.warning",
    soll: { "background-color": "warning-tile", color: "warning-ink" } },
  { id: "H9", seite: "dashboard", was: "Kachel Info", auswahl: ".tile.info",
    soll: { "background-color": "info-tile", color: "info-ink" } },
  { id: "H10", seite: "dashboard", was: "Kachel Ereignisse", auswahl: ".tile.neutral",
    soll: { "background-color": "surface", "border-top-color": "border" } },
  { id: "H11", seite: "dashboard", was: "Zahl der Kachel", auswahl: ".tile .tile-value",
    soll: { "font-size": "40px", "font-weight": "500" } },
  { id: "H12", seite: "dashboard", was: "Symbolfeld Alarm", auswahl: ".icon-chip.alarm",
    soll: { "background-color": "alarm-chip", width: "36px", "border-top-left-radius": "12px" } },
  { id: "H13", seite: "dashboard", was: "Karte", auswahl: "main section.card",
    soll: { "background-color": "surface", "border-top-color": "border", "border-top-left-radius": "20px" } },
  { id: "H14", seite: "dashboard", was: "Zeile Alarm", auswahl: ".row.tint.alarm",
    soll: { "background-color": "alarm-soft", "border-top-left-radius": "14px" } },
  { id: "H15", seite: "dashboard", was: "Zeile Warnung", auswahl: ".row.tint.warning",
    soll: { "background-color": "warning-soft" } },
  { id: "H16", seite: "dashboard", was: "Zeile Info", auswahl: ".row.tint.info",
    soll: { "background-color": "info-soft" } },
  { id: "H17", seite: "dashboard", was: "Knopf Deaktivieren", auswahl: '.row [data-action="deactivate-event"]',
    soll: { "background-color": "surface", "border-top-color": "control", "min-height": "44px", "font-size": "14px" } },
  { id: "H18", seite: "dashboard", was: "Versionszeile", auswahl: ".version",
    soll: { color: "faint", "font-size": "12px" } },

  // -- Historie -----------------------------------------------------------
  { id: "H19", seite: "history", was: "Suchfeld", auswahl: ".search",
    soll: { "background-color": "subtle", height: "44px", "border-top-left-radius": "999px" } },
  { id: "H20", seite: "history", was: "gewählter Zeitraum", auswahl: '.segmented button[aria-pressed="true"]',
    soll: { "background-color": "selected", color: "on-selected", "min-height": "36px" } },
  { id: "H21", seite: "history", was: "Pille Alarm", auswahl: ".pill.alarm",
    soll: { "background-color": "alarm-chip", color: "alarm-ink", "font-size": "12px", "font-weight": "700" } },
  { id: "H22", seite: "history", was: "Pille Warnung", auswahl: ".pill.warning",
    soll: { "background-color": "warning-chip", color: "warning-ink" } },
  { id: "H23", seite: "history", was: "Pille Info", auswahl: ".pill.info",
    soll: { "background-color": "info-chip", color: "info-ink" } },
  { id: "H24", seite: "history", was: "deaktivierter Eintrag", auswahl: ".row.deactivated",
    soll: { "outline-style": "dashed", "outline-color": "dashed" } },
  { id: "H25", seite: "history", was: "Knopf Wieder aktivieren", auswahl: '[data-action="reactivate-event"]',
    soll: { "background-color": "accent-chip", color: "accent-ink" } },

  // -- Regeln -------------------------------------------------------------
  { id: "H26", seite: "rules", was: "gewählte Darstellung", auswahl: '.segmented.view button[aria-pressed="true"]',
    soll: { "background-color": "surface", color: "text" } },
  { id: "H27", seite: "rules", was: "Filter Alle, gewählt", auswahl: '.btn.filter.all[aria-pressed="true"]',
    soll: { "background-color": "selected", color: "on-selected", "min-height": "36px" } },
  { id: "H28", seite: "rules", was: "Filter Alarm", auswahl: ".btn.filter.alarm",
    soll: { "background-color": "alarm-chip", color: "alarm-ink" } },
  { id: "H29", seite: "rules", was: "Filter Warnung", auswahl: ".btn.filter.warning",
    soll: { "background-color": "warning-chip", color: "warning-ink" } },
  { id: "H30", seite: "rules", was: "Filter Info", auswahl: ".btn.filter.info",
    soll: { "background-color": "info-chip", color: "info-ink" } },
  { id: "H31", seite: "rules", was: "Filter Verknüpft", auswahl: ".btn.filter.combined",
    soll: { "background-color": "special-chip", color: "special-ink" } },
  { id: "H32", seite: "rules", was: "ruhige Regel", auswahl: ".rule:not(.reporting)",
    soll: { "background-color": "quiet", "border-top-left-radius": "14px" } },
  { id: "H33", seite: "rules", was: "meldende Regel, Alarm", auswahl: ".rule.reporting.alarm",
    soll: { "background-color": "alarm-soft" } },
  { id: "H34", seite: "rules", was: "meldende Regel, Info", auswahl: ".rule.reporting.info",
    soll: { "background-color": "info-soft" } },
  { id: "H35", seite: "rules", was: "Baustein einer Bedingung", auswahl: ".rule .chip",
    soll: { "background-color": "surface", "font-size": "13px", "border-top-left-radius": "8px" } },
  { id: "H36", seite: "rules", was: "Verweis Bearbeiten", auswahl: '.rule [data-action="edit-rule"]',
    soll: { color: "link", "font-size": "14px", "font-weight": "500" } },
  { id: "H37", seite: "rules", was: "Pille Bedingungen", auswahl: ".rule .pill.special",
    soll: { "background-color": "special-pill", color: "special-ink" } },
  { id: "H38", seite: "rules", was: "Verknüpfungswort", auswahl: ".rule .logic",
    soll: { color: "special-ink", "font-size": "11px", "font-weight": "700" } },
  { id: "H39", seite: "rules", was: "Trennlinie zwischen Entities", auswahl: ".entity-block + .entity-block",
    soll: { "border-top-color": "divider" } },
  { id: "H40", seite: "rules", was: "angeheftete Zeile, Alarm", auswahl: ".rule-line.reporting.alarm",
    soll: { "background-color": "alarm-soft" } },
  { id: "H41", seite: "rules", was: "Punkt Alarm", auswahl: ".dot.alarm",
    soll: { "background-color": "alarm", width: "10px" } },

  // -- Discovery ----------------------------------------------------------
  { id: "H42", seite: "discovery", was: "gewählter Status", auswahl: '[data-action="set-discovery-status"][aria-pressed="true"]',
    soll: { "background-color": "selected", color: "on-selected" } },
  { id: "H43", seite: "discovery", was: "Typ, gewählt", auswahl: '.btn.filter.plain[aria-pressed="true"]',
    soll: { "background-color": "accent-chip", color: "accent-ink", "min-height": "36px" } },
  { id: "H44", seite: "discovery", was: "Typ, nicht gewählt", auswahl: '.btn.filter.plain[aria-pressed="false"]',
    soll: { "background-color": "surface", "border-top-color": "control", color: "text", "font-weight": "400" } },
  { id: "H45", seite: "discovery", was: "Kennzeichen überwacht", auswahl: ".badge.monitored",
    soll: { "background-color": "ok-chip", color: "ok-ink" } },
  { id: "H46", seite: "discovery", was: "Wert der Entity", auswahl: ".entity-item:not(.open) .chip.on-surface",
    soll: { "background-color": "subtle", "font-weight": "500" } },
  { id: "H47", seite: "discovery", was: "Knopf Vorschläge", auswahl: '[data-action="show-suggestions"]',
    soll: { "background-color": "special-chip", color: "special-ink", "min-height": "44px" } },
  { id: "H48", seite: "discovery", was: "Knopf Übernehmen", auswahl: '.entity-item .row > [data-action="add-entity"]',
    soll: { "background-color": "surface", "border-top-color": "control", color: "text" } },
  { id: "H49", seite: "vorschlag", was: "Entity mit offenem Vorschlag", auswahl: ".entity-item.open",
    soll: { "background-color": "special-soft", "border-top-left-radius": "14px" } },
  { id: "H50", seite: "vorschlag", was: "Vorschlag", auswahl: ".suggestion",
    soll: { "background-color": "surface", "border-top-left-radius": "12px" } },
  { id: "H51", seite: "vorschlag", was: "Knopf Mit dieser Regel übernehmen", auswahl: '[data-action="accept-suggestion"]',
    soll: { "background-color": "accent", color: "#ffffff", "min-height": "44px" } },
  { id: "H52", seite: "vorschlag", was: "Begründung", auswahl: ".why",
    soll: { color: "mid", "font-size": "13px" } },

  // -- Regel-Editor -------------------------------------------------------
  { id: "H53", seite: "editor", was: "Titel", auswahl: ".editor-head h2",
    soll: { "font-size": "24px", "font-weight": "500" } },
  { id: "H54", seite: "editor", was: "Knopf Speichern", auswahl: '.editor-head [data-action="save-rule"]',
    soll: { "background-color": "accent", color: "#ffffff", "min-height": "44px" } },
  { id: "H55", seite: "editor", was: "Feld der Bedingungen im Ablauf", auswahl: ".flow-box.flow-conds",
    soll: { "background-color": "group", "border-top-left-radius": "16px" } },
  { id: "H56", seite: "editor", was: "Bedingung im Ablauf", auswahl: ".flow-cond",
    soll: { "background-color": "surface", "border-top-left-radius": "12px" } },
  { id: "H57", seite: "editor", was: "Ergebnis im Ablauf", auswahl: ".flow-result.warning",
    soll: { "background-color": "warning-tile" } },
  { id: "H58", seite: "editor", was: "Schrittnummer", auswahl: ".step-no",
    soll: { "background-color": "accent-chip", color: "accent-ink", width: "28px" } },
  { id: "H59", seite: "editor", was: "erste Bedingung", auswahl: ".cond-card:not(.extra)",
    soll: { "background-color": "group", "border-top-left-radius": "16px" } },
  { id: "H60", seite: "editor", was: "weitere Bedingung", auswahl: ".cond-card.extra",
    soll: { "background-color": "special-soft" } },
  { id: "H61", seite: "editor", was: "gewählter Zustand", auswahl: '.btn.choice[aria-pressed="true"]',
    soll: { "background-color": "accent-chip", color: "accent-ink", "border-top-color": "accent", "border-top-width": "2px", "min-height": "40px" } },
  { id: "H62", seite: "editor", was: "nicht gewählter Zustand", auswahl: '.btn.choice[aria-pressed="false"]',
    soll: { "background-color": "surface", "border-top-color": "control", "border-top-width": "1px" } },
  { id: "H63", seite: "editor", was: "gewählte Verknüpfung", auswahl: '.segmented.special button[aria-pressed="true"]',
    soll: { "background-color": "special", color: "surface" } },
  { id: "H64", seite: "editor", was: "Grund des Verknüpfungs-Umschalters", auswahl: ".segmented.special",
    soll: { "background-color": "special-track" } },
  { id: "H65", seite: "editor", was: "Knopf Weitere Bedingung", auswahl: ".btn.dashed",
    soll: { "border-top-style": "dashed", "border-top-color": "special-dash", color: "special-ink" } },
  { id: "H66", seite: "editor", was: "gewählter Typ", auswahl: '.type-tile.warning[aria-pressed="true"]',
    soll: { "background-color": "warning-tile", color: "warning-ink", "border-top-color": "warning-ink", "border-top-width": "2px" } },
  { id: "H67", seite: "editor", was: "nicht gewählter Typ", auswahl: ".type-tile.alarm",
    soll: { "background-color": "alarm-tile", color: "alarm-ink" } },
  { id: "H68", seite: "editor", was: "Meldungstext", auswahl: '[data-rule-field="message"]',
    soll: { "min-height": "48px", "border-top-left-radius": "14px", "border-top-color": "control" } },
  { id: "H69", seite: "editor", was: "Platzhalter-Knopf", auswahl: ".btn.chip-btn",
    soll: { "background-color": "subtle", "min-height": "32px", "font-size": "13px" } },
  { id: "H70", seite: "editor", was: "Knopf Regel löschen", auswahl: '[data-action="delete-rule"]',
    soll: { color: "alarm-ink", "background-color": "rgba(0, 0, 0, 0)" } },

  // -- Nachtrag -------------------------------------------------------------
  { id: "H71", seite: "dashboard", was: "Kennzeichen Systemnachricht", auswahl: ".badge.source",
    soll: { "background-color": "special-pill", color: "special-ink", "font-size": "11px" } },
];
