/**
 * Gemeinsame Gestaltung des Panels.
 *
 * Leitgedanke: der Zustand soll an der Form ablesbar sein, nicht erst am
 * Text. Jede Dringlichkeit hat deshalb eine eigene, zurueckhaltende Toenung,
 * die sich durch Kacheln, Zeilen und Regeln zieht; alles Besondere --
 * Systemnachricht, Vorschlag, verknuepfte Regel -- traegt eine vierte.
 *
 * Die Farben sind *fest*, in einer hellen und einer dunklen Palette, und
 * stehen so auch in ``docs/UI-KONZEPT.md``. Frueher wurden sie aus den
 * Variablen des Home-Assistant-Themes gemischt. Das klang richtig und sah
 * falsch aus: mit einem tuerkisen Theme wurde aus dem Blau des Entwurfs
 * Tuerkis, aus den kuehlen Flaechen neutrales Grau, und die Toenungen der
 * Dringlichkeiten verschoben sich mit. Ein Panel, das Zustaende ueber Farbe
 * meldet, darf seine Farben nicht vom Zufall eines Themes abhaengen lassen.
 * Vom Theme uebernommen wird deshalb nur noch eines: hell oder dunkel.
 *
 * ``tests/frontend/konzept.test.js`` haelt die Werte hier und im Konzept
 * gleich.
 */

const sheet = new CSSStyleSheet();
sheet.replaceSync(`
  :host {
    --nc-ground: #f2f5fa;
    --nc-surface: #ffffff;
    --nc-text: #1b2430;
    --nc-mid: #455468;
    --nc-muted: #5a6778;
    --nc-faint: #6b7686;
    --nc-border: #e1e7ef;
    --nc-control: #d5dce6;
    --nc-divider: #e9eef4;
    --nc-dashed: #c9d1dc;
    --nc-nav: #e4eaf2;
    --nc-subtle: #f2f5fa;
    --nc-quiet: #f6f8fb;
    --nc-group: #f3f6fa;
    --nc-selected: #1b2430;
    --nc-on-selected: #ffffff;

    --nc-accent: #0277bd;
    --nc-accent-strong: #0277bd;
    --nc-accent-hover: #01579b;
    --nc-accent-chip: #e3f3fd;
    --nc-accent-ink: #0b5580;
    --nc-link: #0277bd;
    --nc-count-selected: #01579b;

    --nc-alarm: #db4437;
    --nc-alarm-tile: #fdeceb;
    --nc-alarm-soft: #fef6f5;
    --nc-alarm-chip: #f9d2ce;
    --nc-alarm-ink: #9f1f17;

    --nc-warning: #ffa600;
    --nc-warning-tile: #fff3da;
    --nc-warning-soft: #fffaf0;
    --nc-warning-chip: #ffe2a8;
    --nc-warning-ink: #7a4a00;

    --nc-info: #039be5;
    --nc-info-tile: #e3f3fd;
    --nc-info-soft: #f3f9fe;
    --nc-info-chip: #c4e5fa;
    --nc-info-ink: #0b5580;

    --nc-ok: #2e9e4f;
    --nc-ok-chip: #dff3e4;
    --nc-ok-ink: #1d6b34;

    --nc-special: #4a3fa3;
    --nc-special-soft: #f6f4fe;
    --nc-special-track: #f0eefc;
    --nc-special-pill: #e9e6fb;
    --nc-special-chip: #e0dbf9;
    --nc-special-line: #d9d5f3;
    --nc-special-dash: #b9b2ea;
    --nc-special-ink: #4a3fa3;

    --nc-radius: 20px;
    --nc-radius-row: 14px;

    display: block;
    min-height: 100%;
    background: var(--nc-ground);
    color: var(--nc-text);
    font-family: Roboto, system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.4;
  }

  /* Die dunkle Palette. Das Panel setzt das Attribut, sobald Home Assistant
     ein dunkles Theme meldet. */
  :host([dark]) {
    --nc-ground: #111418;
    --nc-surface: #1c2128;
    --nc-text: #e6e9ee;
    --nc-mid: #9aa4b2;
    --nc-muted: #9aa4b2;
    --nc-faint: #9aa4b2;
    --nc-border: #2c333d;
    --nc-control: #3a424e;
    --nc-divider: #2c333d;
    --nc-dashed: #3a424e;
    --nc-nav: #232a33;
    --nc-subtle: #111418;
    --nc-quiet: #232a33;
    --nc-group: #171b21;
    --nc-selected: #e6e9ee;
    --nc-on-selected: #111418;

    --nc-accent-hover: #039be5;
    --nc-accent-chip: #1d4a63;
    --nc-accent-ink: #8fd3ff;
    --nc-link: #6cc4f5;
    --nc-count-selected: #8fd3ff;

    --nc-alarm-tile: #3a1f1e;
    --nc-alarm-soft: #2a1b1b;
    --nc-alarm-chip: #5a2a27;
    --nc-alarm-ink: #ff9d94;

    --nc-warning-tile: #3a2f17;
    --nc-warning-soft: #2a2416;
    --nc-warning-chip: #5a4516;
    --nc-warning-ink: #ffcf70;

    --nc-info-tile: #16303f;
    --nc-info-soft: #18242c;
    --nc-info-chip: #1d4a63;
    --nc-info-ink: #8fd3ff;

    --nc-ok-chip: #1d3a27;
    --nc-ok-ink: #8fdba5;

    --nc-special: #c2b9ff;
    --nc-special-soft: #211f33;
    --nc-special-track: #262341;
    --nc-special-pill: #322c57;
    --nc-special-chip: #322c57;
    --nc-special-line: #3d3768;
    --nc-special-dash: #5a519a;
    --nc-special-ink: #c2b9ff;
  }

  * { box-sizing: border-box; }

  /* -- Kopf und Navigation ------------------------------------------- */

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px 32px;
    max-width: 1120px;
    margin: 0 auto;
    padding: 20px 24px 0;
  }

  .brand { display: flex; align-items: center; gap: 12px; }

  .brand-mark {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: var(--nc-accent-strong);
    color: #ffffff;
  }

  header h1 { font-size: 20px; font-weight: 500; margin: 0; }

  nav {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: var(--nc-nav);
  }

  nav button {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 44px;
    padding: 0 18px;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--nc-mid);
    cursor: pointer;
    font: inherit;
    font-weight: 500;
    white-space: nowrap;
  }

  nav button[aria-current="page"] {
    background: var(--nc-accent-strong);
    color: #ffffff;
  }

  .count {
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--nc-ground);
    color: var(--nc-mid);
    font-size: 12px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  nav button[aria-current="page"] .count { background: var(--nc-surface); color: var(--nc-count-selected); }

  main {
    display: flex;
    flex-direction: column;
    gap: 24px;
    max-width: 1120px;
    margin: 0 auto;
    padding: 24px 24px 32px;
  }

  /* -- Ueberschriften ------------------------------------------------- */

  h2 { font-size: 18px; font-weight: 500; margin: 0; }
  h3 { font-size: 16px; font-weight: 500; margin: 0; }

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 6px;
    color: var(--nc-mid);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .section { display: flex; flex-direction: column; gap: 12px; }

  ul { list-style: none; margin: 0; padding: 0; }

  /* -- Karten --------------------------------------------------------- */

  .card {
    background: var(--nc-surface);
    border: 1px solid var(--nc-border);
    border-radius: var(--nc-radius);
  }

  .card.pad { padding: 16px; display: flex; flex-direction: column; gap: 14px; }

  .card-head {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 16px 20px 12px;
  }

  .card-head.alarm h2 { color: var(--nc-alarm-ink); }
  .card-head.warning h2 { color: var(--nc-warning-ink); }
  .card-head.info h2 { color: var(--nc-info-ink); }
  .card-head h2 { font-size: 16px; }

  /* Eine Karte je Raum, ueber die volle Breite: eine Regel mit mehreren
     Bedingungen braucht Platz in der Zeile, nicht drei schmale Spalten. */
  .grid-cards { display: flex; flex-direction: column; gap: 16px; }

  /* -- Kacheln des Dashboards ---------------------------------------- */

  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));
    gap: 16px;
  }

  .tile {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 20px;
    border: 2px solid transparent;
    border-radius: var(--nc-radius);
    background: var(--nc-surface);
    color: var(--nc-text);
    cursor: pointer;
    font: inherit;
    text-align: left;
  }

  .tile-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .tile-label { font-size: 14px; font-weight: 500; }
  .tile-value { font-size: 40px; font-weight: 500; line-height: 1; font-variant-numeric: tabular-nums; }

  .tile.alarm { background: var(--nc-alarm-tile); color: var(--nc-alarm-ink); }
  .tile.warning { background: var(--nc-warning-tile); color: var(--nc-warning-ink); }
  .tile.info { background: var(--nc-info-tile); color: var(--nc-info-ink); }
  .tile.neutral { border: 1px solid var(--nc-border); padding: 21px; }
  .tile.neutral .tile-label { color: var(--nc-mid); }

  /* Die gewaehlte Kachel ist der Filter: deutlich, aber ohne zu schreien. */
  .tile[aria-pressed="true"] { border-color: currentColor; }
  .tile.dimmed { opacity: 0.55; }

  .icon-chip {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 12px;
    background: var(--nc-subtle);
    color: var(--nc-mid);
  }

  .icon-chip.alarm { background: var(--nc-alarm-chip); color: var(--nc-alarm-ink); }
  .icon-chip.warning { background: var(--nc-warning-chip); color: var(--nc-warning-ink); }
  .icon-chip.info { background: var(--nc-info-chip); color: var(--nc-info-ink); }

  /* -- Zeilen --------------------------------------------------------- */

  .rows { display: flex; flex-direction: column; gap: 4px; padding: 8px; }
  .card-head + .rows { padding-top: 0; }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 14px;
    padding: 10px 12px;
    border-radius: var(--nc-radius-row);
  }

  .row.clickable { cursor: pointer; }
  .row.tint.alarm { background: var(--nc-alarm-soft); }
  .row.tint.warning { background: var(--nc-warning-soft); }
  .row.tint.info { background: var(--nc-info-soft); }
  .row.tint.special { background: var(--nc-special-soft); }

  /* Von Hand deaktiviert: sichtbar zurueckgenommen, aber nicht versteckt. */
  .row.deactivated { outline: 1px dashed var(--nc-dashed); outline-offset: -1px; }

  .row-body { display: flex; flex: 1 1 260px; flex-direction: column; min-width: 0; }
  .row-title { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-weight: 500; }
  .row-sub, .entity-meta { color: var(--nc-muted); font-size: 13px; overflow-wrap: anywhere; }

  .message { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .row-title .message { flex: 0 1 auto; }

  .time, .duration {
    color: var(--nc-mid);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .time { min-width: 44px; }

  .mono {
    font-family: "Roboto Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
    color: var(--nc-muted);
    overflow-wrap: anywhere;
  }

  /* -- Pillen und Bausteine ------------------------------------------- */

  .pill, .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--nc-nav);
    color: var(--nc-mid);
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
  }

  .pill.alarm, .type-alarm { background: var(--nc-alarm-chip); color: var(--nc-alarm-ink); }
  .pill.warning, .type-warning { background: var(--nc-warning-chip); color: var(--nc-warning-ink); }
  .pill.info, .type-info { background: var(--nc-info-chip); color: var(--nc-info-ink); }
  .pill.ok, .badge.monitored { background: var(--nc-ok-chip); color: var(--nc-ok-ink); }
  .pill.special { background: var(--nc-special-pill); color: var(--nc-special-ink); }
  .pill.special.strong { background: var(--nc-special-chip); }
  .badge.source { padding: 2px 8px; background: var(--nc-special-pill); color: var(--nc-special-ink); font-size: 11px; }
  .badge.uncertain { background: var(--nc-warning-chip); color: var(--nc-warning-ink); }
  .pill.plain { padding: 4px 10px; background: var(--nc-surface); color: var(--nc-mid); font-weight: 500; font-size: 13px; font-variant-numeric: tabular-nums; }

  /* In Listen gleich breit, damit die Texte dahinter buendig beginnen. */
  .row > .pill.alarm, .row > .pill.warning, .row > .pill.info { justify-content: center; min-width: 76px; }

  .condition input[data-cond-field="entity"] { flex: 1 1 260px; }

  /* Ein Baustein einer Bedingung: "Zustand ist on". */
  .chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }

  .chip {
    padding: 4px 10px;
    border-radius: 8px;
    background: var(--nc-surface);
    font-size: 13px;
    overflow-wrap: anywhere;
  }

  .chip.on-surface { background: var(--nc-subtle); font-weight: 500; font-variant-numeric: tabular-nums; }

  .logic {
    color: var(--nc-special-ink);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .status { font-size: 12px; color: var(--nc-muted); }
  .status.alarm { color: var(--nc-alarm-ink); font-weight: 700; }
  .status.warning { color: var(--nc-warning-ink); font-weight: 700; }
  .status.info { color: var(--nc-info-ink); font-weight: 700; }

  /* -- Schaltflaechen ------------------------------------------------- */

  a, .link {
    color: var(--nc-link);
    background: none;
    border: none;
    cursor: pointer;
    font: inherit;
    font-size: 14px;
    font-weight: 500;
    padding: 0;
    text-decoration: none;
  }

  a:hover, .link:hover { color: var(--nc-accent-hover); }
  .row > .link { padding: 12px 4px; }

  button.action, .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 44px;
    padding: 0 18px;
    border: 1px solid var(--nc-control);
    border-radius: 999px;
    background: var(--nc-surface);
    color: var(--nc-text);
    cursor: pointer;
    font: inherit;
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
  }

  button.action:not(.secondary), .btn.primary {
    border-color: transparent;
    background: var(--nc-accent-strong);
    color: #ffffff;
  }

  .btn.soft { border-color: transparent; background: var(--nc-accent-chip); color: var(--nc-accent-ink); }
  .btn.special { border-color: transparent; background: var(--nc-special-chip); color: var(--nc-special-ink); }
  .btn.danger { color: var(--nc-alarm-ink); }
  .btn.ghost { border-color: transparent; background: transparent; }

  button.action[disabled], .btn[disabled] { opacity: 0.5; cursor: default; }

  .icon-btn {
    display: inline-flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--nc-muted);
    cursor: pointer;
  }

  .icon-btn:hover, .btn:not(.primary):not(.soft):not(.special):not(.filter):not(.choice):hover,
  button.action.secondary:hover { background: var(--nc-subtle); }
  button.action:not(.secondary):hover, .btn.primary:hover { background: var(--nc-accent-hover); }

  button:focus-visible, select:focus-visible, input:focus-visible, a:focus-visible, summary:focus-visible {
    outline: 2px solid var(--nc-accent);
    outline-offset: 2px;
  }

  /* Umschalter aus zwei bis vier Moeglichkeiten. */
  .segmented {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: var(--nc-subtle);
  }

  .segmented button {
    min-height: 36px;
    padding: 0 14px;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--nc-mid);
    cursor: pointer;
    font: inherit;
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
  }

  .segmented button[aria-pressed="true"] { background: var(--nc-selected); color: var(--nc-on-selected); }

  /* Die leise Spielart fuer die Darstellung -- Karten oder Liste, nach Raum
     oder Typ. Sie aendert, wie man sieht, nicht was; deshalb hebt sie die
     Wahl nur an, statt sie zu schwaerzen. */
  .segmented.view button[aria-pressed="true"] { background: var(--nc-surface); color: var(--nc-text); }

  /* -- Eingaben ------------------------------------------------------- */

  .filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
  .filters .spacer { flex: 1; }
  .filters.tight { gap: 6px; }
  .footer-link .spacer { flex: 1; }

  select, input[type="search"], input[type="text"], input[type="number"] {
    min-height: 40px;
    padding: 0 14px;
    border: 1px solid var(--nc-control);
    border-radius: 999px;
    background: var(--nc-surface);
    color: var(--nc-text);
    font: inherit;
    font-size: 14px;
  }

  select[multiple] { min-height: 0; padding: 6px; border-radius: 14px; }

  /* Das Suchfeld: eine Pille mit Lupe, das Eingabefeld darin ohne Rahmen. */
  .search {
    display: flex;
    flex: 1 1 280px;
    align-items: center;
    gap: 10px;
    height: 44px;
    min-width: 180px;
    padding: 0 14px;
    border-radius: 999px;
    background: var(--nc-subtle);
    color: var(--nc-muted);
  }

  .search:focus-within { outline: 2px solid var(--nc-accent); outline-offset: 2px; }

  .search input[type="search"] {
    flex: 1;
    min-width: 0;
    min-height: 0;
    padding: 0;
    border: none;
    outline: none;
    background: transparent;
    font-size: 15px;
  }

  input::placeholder { color: var(--nc-muted); opacity: 1; }

  .field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .field > span { color: var(--nc-muted); font-size: 12px; font-weight: 700; }
  .field.grow { flex: 1 1 240px; }

  .form-section { display: flex; flex-direction: column; gap: 12px; }

  .form-label {
    color: var(--nc-muted);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  /* Eine weitere Bedingung der Regel als eigener Block. */
  .condition {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    border-radius: var(--nc-radius-row);
    background: var(--nc-special-soft);
  }

  .negate {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 40px;
    color: var(--nc-muted);
    font-size: 14px;
    white-space: nowrap;
  }

  details summary { color: var(--nc-muted); cursor: pointer; font-size: 13px; font-weight: 500; }
  details dl { display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; margin: 8px 0 0; font-size: 13px; }
  details dt { color: var(--nc-muted); }
  details dd { margin: 0; }

  /* -- Regeln --------------------------------------------------------- */

  .entity-block { display: flex; flex-direction: column; gap: 8px; }
  .entity-block + .entity-block { padding-top: 14px; border-top: 1px solid var(--nc-divider); }
  .entity-name { font-weight: 500; overflow-wrap: anywhere; }

  .rule {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
    padding: 12px;
    border-radius: var(--nc-radius-row);
    background: var(--nc-quiet);
  }

  .rule.reporting.alarm { background: var(--nc-alarm-soft); }
  .rule.reporting.warning { background: var(--nc-warning-soft); }
  .rule.reporting.info { background: var(--nc-info-soft); }

  /* Die Regel, deren Formular gerade offen ist. */
  .rule.editing { outline: 2px solid var(--nc-accent); outline-offset: -2px; }

  .rule-head { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: center; gap: 8px; min-width: 190px; }
  .rule-lines { display: flex; flex-direction: column; gap: 6px; }
  .rule > .rule-lines { flex: 1 1 320px; flex-direction: row; flex-wrap: wrap; align-items: center; gap: 6px 10px; }
  .rule-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 16px; }

  /* Dichte Liste fuer grosse Bestaende: eine Zeile je Regel. */
  .rule-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 12px;
    padding: 8px 12px;
    border-radius: var(--nc-radius-row);
  }

  .rule-line.reporting.alarm { background: var(--nc-alarm-soft); }
  .rule-line.reporting.warning { background: var(--nc-warning-soft); }
  .rule-line.reporting.info { background: var(--nc-info-soft); }

  .dot { flex: none; width: 10px; height: 10px; border-radius: 50%; background: var(--nc-dashed); }
  .dot.alarm { background: var(--nc-alarm); }
  .dot.warning { background: var(--nc-warning); }
  .dot.info { background: var(--nc-info); }

  .rule-lines.tight { gap: 2px; }
  .rule-line-name { flex: 0 1 220px; font-weight: 500; overflow-wrap: anywhere; }
  .rule-line-text { flex: 1 1 240px; color: var(--nc-mid); font-size: 13px; overflow-wrap: anywhere; }

  /* Ein Raum als eigenes Feld: die Klammer um seine Zeilen. */
  .room-cluster {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px;
    border-radius: 16px;
    background: var(--nc-group);
  }

  .room-cluster + .room-cluster { margin-top: 4px; }
  .btn.more { align-self: flex-start; min-height: 40px; margin: 4px 0 4px 6px; padding: 0 14px; border-color: transparent; color: var(--nc-mid); }
  .room-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 12px 4px; font-size: 14px; font-weight: 700; }
  .room-head .row-sub { font-weight: 400; }
  .room-cluster .rule-line { background: var(--nc-surface); border-radius: 12px; }
  .room-cluster .rule-line.reporting.alarm { background: var(--nc-alarm-soft); }
  .room-cluster .rule-line.reporting.warning { background: var(--nc-warning-soft); }
  .room-cluster .rule-line.reporting.info { background: var(--nc-info-soft); }

  /* Filter als Pillen in der Farbe dessen, was sie zeigen. */
  .btn.filter { min-height: 36px; padding: 0 14px; border-color: transparent; background: var(--nc-subtle); }
  /* Ohne eigene Farbe: weiss mit Rahmen, die Zahl dahinter zurueckgenommen. */
  .btn.filter.plain, .btn.filter.disabled { border-color: var(--nc-control); background: var(--nc-surface); font-weight: 400; }
  .btn.filter.plain[aria-pressed="true"] {
    border-color: transparent;
    background: var(--nc-accent-chip);
    color: var(--nc-accent-ink);
    font-weight: 500;
    outline: none;
  }
  .btn.filter.alarm { background: var(--nc-alarm-chip); color: var(--nc-alarm-ink); }
  .btn.filter.warning { background: var(--nc-warning-chip); color: var(--nc-warning-ink); }
  .btn.filter.info { background: var(--nc-info-chip); color: var(--nc-info-ink); }
  .btn.filter.combined { background: var(--nc-special-chip); color: var(--nc-special-ink); }
  .btn.filter[aria-pressed="true"] { outline: 2px solid currentColor; outline-offset: -2px; }
  .btn.filter.all[aria-pressed="true"] { background: var(--nc-selected); color: var(--nc-on-selected); outline: none; }

  /* Auf- und zuklappbare Gliederung. */
  .toggle {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 12px;
    width: 100%;
    min-height: 44px;
    padding: 0 6px;
    border: none;
    background: none;
    color: var(--nc-mid);
    cursor: pointer;
    font: inherit;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-align: left;
    text-transform: uppercase;
  }

  .toggle.closed { min-height: 52px; padding: 0 16px; border: 1px solid var(--nc-border); border-radius: 16px; background: var(--nc-surface); }
  .toggle .summary { flex: 1; }
  .toggle .pill, .toggle .status { letter-spacing: 0; text-transform: none; }
  .toggle .chevron { transition: transform 0.15s; }
  .toggle[aria-expanded="false"] .chevron { transform: rotate(-90deg); }
  .toggle .summary { font-weight: 500; letter-spacing: 0; text-transform: none; }

  /* -- Regel-Editor --------------------------------------------------- */

  .editor-head, .editor-foot {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
  }

  .editor-head h2 { font-size: 24px; }

  .step { display: flex; align-items: center; gap: 12px; }

  .step-no {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--nc-accent-chip);
    color: var(--nc-accent-ink);
    font-size: 14px;
    font-weight: 700;
  }

  /* Der Ablauf: Bedingungen, Wartezeit, Meldung von links nach rechts. */
  .flow-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px; }
  .flow { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
  .flow-box { padding: 12px; border-radius: 16px; background: var(--nc-group); }
  .flow-conds { display: flex; flex: 1 1 300px; flex-direction: column; gap: 8px; }
  .flow-cond { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: var(--nc-surface); }
  .flow-join { padding-left: 4px; }
  .flow-arrow { display: flex; color: var(--nc-muted); }
  .flow-wait { display: flex; flex: 0 1 180px; flex-direction: column; align-items: center; gap: 6px; padding: 16px 12px; color: var(--nc-muted); text-align: center; }
  .flow-wait strong { color: var(--nc-text); }
  .flow-result { display: flex; flex: 1 1 260px; flex-direction: column; gap: 8px; padding: 16px; }
  .flow-result.alarm { background: var(--nc-alarm-tile); }
  .flow-result.warning { background: var(--nc-warning-tile); }
  .flow-result.info { background: var(--nc-info-tile); }
  .flow-result.alarm strong, .flow-result.alarm .row-sub { color: var(--nc-alarm-ink); }
  .flow-result.warning strong, .flow-result.warning .row-sub { color: var(--nc-warning-ink); }
  .flow-result.info strong, .flow-result.info .row-sub { color: var(--nc-info-ink); }

  .dot.met { background: var(--nc-ok); }
  .row-sub.met { color: var(--nc-ok-ink); }

  .cond-card { display: flex; flex-direction: column; gap: 10px; padding: 14px; border-radius: 16px; background: var(--nc-group); }
  .cond-card .segmented { background: var(--nc-surface); }
  .cond-card.extra input[data-cond-field="entity"] { border-color: var(--nc-special-line); font-weight: 500; }
  .cond-card.extra { background: var(--nc-special-soft); }
  .cond-card input[data-cond-field="entity"] { flex: 0 1 260px; }

  .filters.small, label.inline { color: var(--nc-muted); font-size: 13px; }
  label.inline { display: inline-flex; align-items: center; gap: 8px; }
  label.inline input[type="number"] { width: 88px; }
  input[data-rule-field="message"] { min-height: 48px; padding: 0 16px; border-radius: 14px; font-size: 15px; }

  /* Ein Wert zum Anklicken statt zum Tippen. */
  .btn.choice { min-height: 40px; padding: 0 16px; font-weight: 400; }
  .btn.choice[aria-pressed="true"] {
    font-weight: 500;
    border: 2px solid var(--nc-accent-strong);
    background: var(--nc-accent-chip);
    color: var(--nc-accent-ink);
  }

  .btn.dashed { align-self: flex-start; border-style: dashed; border-color: var(--nc-special-dash); color: var(--nc-special-ink); }
  .btn.chip-btn { min-height: 32px; padding: 0 12px; border-color: transparent; background: var(--nc-subtle); font-size: 13px; font-weight: 400; }

  .segmented.special { background: var(--nc-special-track); }
  .segmented.special button { color: var(--nc-special-ink); }
  .segmented.special button[aria-pressed="true"] { background: var(--nc-special); color: var(--nc-surface); }

  .type-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(200px, 100%), 1fr)); gap: 12px; }

  .type-tile {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 64px;
    padding: 12px 16px;
    border: 2px solid transparent;
    border-radius: 16px;
    cursor: pointer;
    font: inherit;
    text-align: left;
  }

  .type-tile > span > span { display: block; font-size: 12px; }
  .type-tile.alarm { background: var(--nc-alarm-tile); color: var(--nc-alarm-ink); }
  .type-tile.warning { background: var(--nc-warning-tile); color: var(--nc-warning-ink); }
  .type-tile.info { background: var(--nc-info-tile); color: var(--nc-info-ink); }
  .type-tile[aria-pressed="true"] { border-color: currentColor; }

  .link.quiet { color: var(--nc-faint); font-size: 12px; font-weight: 400; text-decoration: underline; }

  /* -- Discovery ------------------------------------------------------ */

/* Eine Entity mit aufgeklapptem Vorschlag: die Toenung umfasst Zeile und
     Vorschlag, damit beides als eines gelesen wird. */
  .entity-item.open {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 10px 12px 12px;
    border-radius: var(--nc-radius-row);
    background: var(--nc-special-soft);
  }

  .entity-item.open > .row { padding: 0; }
  .entity-item.open .chip.on-surface { background: var(--nc-surface); }

  .suggestions { display: flex; flex-direction: column; gap: 8px; }

  .suggestion {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
    border-radius: 12px;
    background: var(--nc-surface);
  }

  .suggestion-head { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .suggestion .chip { background: var(--nc-subtle); }
  .why { max-width: 65ch; margin: 0; color: var(--nc-mid); font-size: 13px; }

  /* -- Uebriges ------------------------------------------------------- */

  .empty { padding: 48px 16px; text-align: center; color: var(--nc-muted); }
  .empty strong { display: block; font-size: 18px; font-weight: 500; color: var(--nc-text); }
  .empty span { font-size: 14px; }

  .paused {
    align-self: flex-start;
    padding: 4px 12px;
    border-radius: 999px;
    background: var(--nc-warning-chip);
    color: var(--nc-warning-ink);
    font-size: 13px;
    font-weight: 500;
  }

  .footer-link {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
    color: var(--nc-muted);
    font-size: 14px;
  }

  .footer-link.center { justify-content: center; }

  /* Bewusst unauffaellig, und nur auf dem Dashboard. */
  .version { align-self: flex-end; padding: 0 6px; color: var(--nc-faint); font-size: 12px; }

  .error {
    padding: 12px 16px;
    border-radius: var(--nc-radius-row);
    background: var(--nc-alarm-soft);
    color: var(--nc-alarm-ink);
  }

  .loading { color: var(--nc-muted); padding: 8px 6px; }

  @media (prefers-reduced-motion: reduce) {
    .toggle .chevron { transition: none; }
  }

  @media (max-width: 600px) {
    header { padding: 16px 16px 0; }
    main { padding: 16px 16px 24px; }
    nav button { padding: 0 12px; }
  }
`);

/** Haengt die gemeinsame Gestaltung an eine Shadow-Root. */
export function adoptStyles(shadowRoot) {
  shadowRoot.adoptedStyleSheets = [sheet];
}
