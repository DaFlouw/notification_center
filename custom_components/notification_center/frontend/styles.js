/**
 * Gemeinsame Gestaltung des Panels.
 *
 * Leitgedanke: der Zustand soll an der Form ablesbar sein, nicht erst am
 * Text. Jede Dringlichkeit hat deshalb eine eigene, zurueckhaltende Toenung,
 * die sich durch Kacheln, Zeilen und Regeln zieht; alles Besondere --
 * Systemnachricht, Vorschlag, verknuepfte Regel -- traegt eine vierte.
 *
 * Die Farben stammen weiterhin aus den Home-Assistant-Variablen, damit das
 * Panel jedem Theme folgt. Die Toenungen werden daraus *gemischt* statt fest
 * hinterlegt: ``color-mix`` gegen die Kartenflaeche ergibt im hellen Theme
 * ein Pastell und im dunklen einen gedeckten Ton, ohne dass es zwei Paletten
 * braucht. Die Schriftfarbe einer Toenung entsteht gegen die Textfarbe, damit
 * sie auf beiden Gruenden lesbar bleibt.
 */

const sheet = new CSSStyleSheet();
sheet.replaceSync(`
  :host {
    --nc-accent: var(--primary-color, #03a9f4);
    /* Gefuellte Flaechen mit weisser Schrift: das Blau von Home Assistant ist
       dafuer zu hell (Kontrast rund 2,5 zu 1). Abgedunkelt traegt es den
       Text, bleibt aber erkennbar dieselbe Farbe -- und folgt weiter dem
       Theme. */
    --nc-accent-strong: color-mix(in srgb, var(--nc-accent) 70%, #000000);
    --nc-surface: var(--card-background-color, #ffffff);
    --nc-ground: var(--primary-background-color, #f2f5fa);
    --nc-text: var(--primary-text-color, #1b2430);
    --nc-muted: var(--secondary-text-color, #5a6778);
    --nc-border: var(--divider-color, rgba(127, 127, 127, 0.25));

    --nc-alarm: var(--error-color, #db4437);
    --nc-warning: var(--warning-color, #ffa600);
    --nc-info: var(--info-color, #039be5);
    --nc-ok: var(--success-color, #43a047);
    --nc-special: #6c5fd6;

    --nc-subtle: color-mix(in srgb, var(--nc-text) 5%, var(--nc-surface));
    --nc-subtle-strong: color-mix(in srgb, var(--nc-text) 10%, var(--nc-surface));

    --nc-alarm-soft: color-mix(in srgb, var(--nc-alarm) 9%, var(--nc-surface));
    --nc-alarm-chip: color-mix(in srgb, var(--nc-alarm) 22%, var(--nc-surface));
    --nc-alarm-ink: color-mix(in srgb, var(--nc-alarm) 70%, var(--nc-text));

    --nc-warning-soft: color-mix(in srgb, var(--nc-warning) 11%, var(--nc-surface));
    --nc-warning-chip: color-mix(in srgb, var(--nc-warning) 30%, var(--nc-surface));
    --nc-warning-ink: color-mix(in srgb, var(--nc-warning) 50%, var(--nc-text));

    --nc-info-soft: color-mix(in srgb, var(--nc-info) 12%, var(--nc-surface));
    --nc-info-chip: color-mix(in srgb, var(--nc-info) 24%, var(--nc-surface));
    --nc-info-ink: color-mix(in srgb, var(--nc-info) 50%, var(--nc-text));

    --nc-ok-chip: color-mix(in srgb, var(--nc-ok) 20%, var(--nc-surface));
    --nc-ok-ink: color-mix(in srgb, var(--nc-ok) 62%, var(--nc-text));

    --nc-special-soft: color-mix(in srgb, var(--nc-special) 8%, var(--nc-surface));
    --nc-special-chip: color-mix(in srgb, var(--nc-special) 20%, var(--nc-surface));
    --nc-special-ink: color-mix(in srgb, var(--nc-special) 72%, var(--nc-text));

    --nc-accent-chip: color-mix(in srgb, var(--nc-accent) 16%, var(--nc-surface));
    --nc-accent-ink: color-mix(in srgb, var(--nc-accent) 55%, var(--nc-text));

    --nc-radius: 20px;
    --nc-radius-row: 14px;

    display: block;
    min-height: 100%;
    background: var(--nc-ground);
    color: var(--nc-text);
    font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif);
    font-size: 15px;
    line-height: 1.4;
  }

  * { box-sizing: border-box; }

  /* -- Kopf und Navigation ------------------------------------------- */

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px 32px;
    max-width: 1168px;
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
    background: var(--nc-subtle-strong);
  }

  nav button {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 40px;
    padding: 0 18px;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--nc-muted);
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
    background: var(--nc-surface);
    color: var(--nc-muted);
    font-size: 12px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  nav button[aria-current="page"] .count { color: var(--nc-accent-ink); }

  main {
    display: flex;
    flex-direction: column;
    gap: 20px;
    max-width: 1168px;
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
    color: var(--nc-muted);
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

  .grid-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(340px, 100%), 1fr));
    gap: 16px;
    align-items: start;
  }

  /* -- Kacheln des Dashboards ---------------------------------------- */

  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(200px, 100%), 1fr));
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

  .tile.alarm { background: var(--nc-alarm-soft); color: var(--nc-alarm-ink); }
  .tile.warning { background: var(--nc-warning-soft); color: var(--nc-warning-ink); }
  .tile.info { background: var(--nc-info-soft); color: var(--nc-info-ink); }
  .tile.neutral { border: 1px solid var(--nc-border); padding: 21px; }
  .tile.neutral .tile-label { color: var(--nc-muted); }

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
    background: var(--nc-subtle-strong);
    color: var(--nc-muted);
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
  .row.deactivated { outline: 1px dashed var(--nc-border); outline-offset: -1px; }

  .row-body { display: flex; flex: 1 1 260px; flex-direction: column; min-width: 0; }
  .row-title { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-weight: 500; }
  .row-sub, .entity-meta { color: var(--nc-muted); font-size: 13px; overflow-wrap: anywhere; }

  .message { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .row-title .message { flex: 0 1 auto; }

  .time, .duration {
    color: var(--nc-muted);
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
    background: var(--nc-subtle-strong);
    color: var(--nc-muted);
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
  }

  .pill.alarm, .type-alarm { background: var(--nc-alarm-chip); color: var(--nc-alarm-ink); }
  .pill.warning, .type-warning { background: var(--nc-warning-chip); color: var(--nc-warning-ink); }
  .pill.info, .type-info { background: var(--nc-info-chip); color: var(--nc-info-ink); }
  .pill.ok, .badge.monitored { background: var(--nc-ok-chip); color: var(--nc-ok-ink); }
  .pill.special { background: var(--nc-special-chip); color: var(--nc-special-ink); }
  .badge.uncertain { background: var(--nc-warning-chip); color: var(--nc-warning-ink); }
  .pill.plain { background: var(--nc-surface); font-weight: 500; font-size: 13px; }

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

  .chip.on-surface { background: var(--nc-subtle); }

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
    color: var(--nc-accent-ink);
    background: none;
    border: none;
    cursor: pointer;
    font: inherit;
    font-size: 14px;
    font-weight: 500;
    padding: 0;
    text-decoration: none;
  }

  button.action, .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 40px;
    padding: 0 16px;
    border: 1px solid var(--nc-border);
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

  button.action[disabled], .btn[disabled] { opacity: 0.5; cursor: default; }

  .icon-btn {
    display: inline-flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--nc-muted);
    cursor: pointer;
  }

  .icon-btn:hover, .btn:hover, button.action.secondary:hover { background: var(--nc-subtle); }

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
    min-height: 34px;
    padding: 0 14px;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--nc-muted);
    cursor: pointer;
    font: inherit;
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
  }

  .segmented button[aria-pressed="true"] { background: var(--nc-text); color: var(--nc-surface); }

  /* -- Eingaben ------------------------------------------------------- */

  .filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
  .filters .spacer { flex: 1; }

  select, input[type="search"], input[type="text"], input[type="number"] {
    min-height: 40px;
    padding: 0 14px;
    border: 1px solid var(--nc-border);
    border-radius: 999px;
    background: var(--nc-surface);
    color: inherit;
    font: inherit;
    font-size: 14px;
  }

  select[multiple] { min-height: 0; padding: 6px; border-radius: 14px; }

  input[type="search"] {
    flex: 1 1 240px;
    min-width: 180px;
    border-color: transparent;
    background: var(--nc-subtle);
  }

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
  .entity-block + .entity-block { padding-top: 14px; border-top: 1px solid var(--nc-border); }
  .entity-name { font-weight: 500; overflow-wrap: anywhere; }

  .rule {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    border-radius: var(--nc-radius-row);
    background: var(--nc-subtle);
  }

  .rule.reporting.alarm { background: var(--nc-alarm-soft); }
  .rule.reporting.warning { background: var(--nc-warning-soft); }
  .rule.reporting.info { background: var(--nc-info-soft); }

  /* Die Regel, deren Formular gerade offen ist. */
  .rule.editing { outline: 2px solid var(--nc-accent); outline-offset: -2px; }

  .rule-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
  .rule-lines { display: flex; flex-direction: column; gap: 6px; }
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

  .dot { flex: none; width: 10px; height: 10px; border-radius: 50%; background: var(--nc-muted); }
  .dot.alarm { background: var(--nc-alarm); }
  .dot.warning { background: var(--nc-warning); }
  .dot.info { background: var(--nc-info); }

  .rule-lines.tight { gap: 2px; }
  .rule-line-name { flex: 0 1 220px; font-weight: 500; overflow-wrap: anywhere; }
  .rule-line-text { flex: 1 1 240px; color: var(--nc-muted); font-size: 13px; overflow-wrap: anywhere; }

  /* Ein Raum als eigenes Feld: die Klammer um seine Zeilen. */
  .room-cluster {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px;
    border-radius: 16px;
    background: var(--nc-subtle);
  }

  .room-cluster + .room-cluster { margin-top: 4px; }
  .btn.more { align-self: flex-start; margin: 4px 0 2px 6px; border-color: transparent; color: var(--nc-muted); }
  .room-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 6px 12px 4px; font-size: 14px; }
  .room-cluster .rule-line { background: var(--nc-surface); border-radius: 12px; }
  .room-cluster .rule-line.reporting.alarm { background: var(--nc-alarm-soft); }
  .room-cluster .rule-line.reporting.warning { background: var(--nc-warning-soft); }
  .room-cluster .rule-line.reporting.info { background: var(--nc-info-soft); }

  /* Filter als Pillen in der Farbe dessen, was sie zeigen. */
  .btn.filter { min-height: 36px; border-color: transparent; background: var(--nc-subtle); }
  .btn.filter.alarm { background: var(--nc-alarm-chip); color: var(--nc-alarm-ink); }
  .btn.filter.warning { background: var(--nc-warning-chip); color: var(--nc-warning-ink); }
  .btn.filter.info { background: var(--nc-info-chip); color: var(--nc-info-ink); }
  .btn.filter.combined { background: var(--nc-special-chip); color: var(--nc-special-ink); }
  .btn.filter[aria-pressed="true"] { outline: 2px solid currentColor; outline-offset: -2px; }
  .btn.filter.all[aria-pressed="true"] { background: var(--nc-text); color: var(--nc-surface); outline: none; }

  /* Auf- und zuklappbare Gliederung. */
  .toggle {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 12px;
    width: 100%;
    min-height: 40px;
    padding: 0 6px;
    border: none;
    background: none;
    color: var(--nc-muted);
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

  /* -- Discovery ------------------------------------------------------ */

  .suggestions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    border-radius: var(--nc-radius-row);
    background: var(--nc-special-soft);
  }

  .suggestion {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 14px;
    border-radius: 12px;
    background: var(--nc-surface);
  }

  .suggestion-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }

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
  .version { align-self: flex-end; padding: 0 6px; color: var(--nc-muted); font-size: 12px; }

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
