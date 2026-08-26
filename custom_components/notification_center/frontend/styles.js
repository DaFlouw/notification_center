/**
 * Gemeinsame Gestaltung.
 *
 * Leitgedanke aus Spezifikation 74: Information vor Dekoration. Keine
 * Animationen, keine Kategorie-Icons, keine grossen Karten. Die Farben
 * folgen Spezifikation 54 und stammen aus den Home-Assistant-Variablen,
 * damit das Panel sich in jedes Theme einfuegt.
 */

const sheet = new CSSStyleSheet();
sheet.replaceSync(`
  :host {
    --nc-info: var(--secondary-text-color, #6b6b6b);
    --nc-warning: var(--warning-color, #ffa600);
    --nc-alarm: var(--error-color, #db4437);
    --nc-border: var(--divider-color, rgba(127, 127, 127, 0.25));
    --nc-muted: var(--secondary-text-color, #6b6b6b);

    display: block;
    height: 100%;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, inherit);
  }

  * { box-sizing: border-box; }

  header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 16px;
    height: var(--header-height, 56px);
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, #fff);
  }

  header h1 {
    font-size: 20px;
    font-weight: 400;
    margin: 0;
    flex: 1;
  }

  nav {
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--nc-border);
    padding: 0 16px;
    background: var(--card-background-color, #fff);
    overflow-x: auto;
  }

  nav button {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--nc-muted);
    cursor: pointer;
    font: inherit;
    padding: 12px 16px;
    white-space: nowrap;
  }

  nav button[aria-current="page"] {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }

  main { padding: 16px; max-width: 1100px; margin: 0 auto; }

  h2 {
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--nc-muted);
    margin: 24px 0 8px;
  }

  h2:first-of-type { margin-top: 0; }

  h3 {
    font-size: 14px;
    font-weight: 500;
    color: var(--primary-text-color);
    margin: 12px 0 6px;
  }

  ul { list-style: none; margin: 0; padding: 0; }

  .row {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid var(--nc-border);
  }

  .row:last-child { border-bottom: none; }

  .row.clickable { cursor: pointer; }

  .message { flex: 1; min-width: 0; overflow-wrap: anywhere; }

  .time, .duration {
    color: var(--nc-muted);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .bar {
    align-self: stretch;
    border-radius: 2px;
    flex: 0 0 3px;
  }

  .bar.info { background: var(--nc-info); }
  .bar.warning { background: var(--nc-warning); }
  .bar.alarm { background: var(--nc-alarm); }

  .type-info { color: var(--nc-info); }
  .type-warning { color: var(--nc-warning); }
  .type-alarm { color: var(--nc-alarm); }

  .empty { padding: 48px 0; text-align: center; color: var(--nc-muted); }
  .empty strong { display: block; font-size: 18px; font-weight: 400; color: var(--primary-text-color); }
  .empty span { font-size: 14px; }

  .paused {
    color: var(--nc-muted);
    font-size: 13px;
    padding: 4px 0 12px;
  }

  .footer-link {
    margin-top: 24px;
    color: var(--nc-muted);
    font-size: 14px;
  }

  a, .link {
    color: var(--primary-color);
    background: none;
    border: none;
    cursor: pointer;
    font: inherit;
    padding: 0;
    text-decoration: none;
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
  }

  select, input[type="search"], input[type="text"], input[type="number"] {
    background: var(--card-background-color, #fff);
    border: 1px solid var(--nc-border);
    border-radius: 4px;
    color: inherit;
    font: inherit;
    padding: 7px 9px;
  }

  input[type="search"] { flex: 1; min-width: 180px; }

  button.action {
    background: var(--primary-color);
    border: none;
    border-radius: 4px;
    color: var(--text-primary-color, #fff);
    cursor: pointer;
    font: inherit;
    padding: 8px 14px;
  }

  button.action.secondary {
    background: none;
    border: 1px solid var(--nc-border);
    color: var(--primary-color);
  }

  button.action[disabled] { opacity: 0.5; cursor: default; }

  .entity-row { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--nc-border); }
  .entity-main { flex: 1; min-width: 0; }
  .entity-name { overflow-wrap: anywhere; }
  .entity-meta { color: var(--nc-muted); font-size: 13px; overflow-wrap: anywhere; }

  .badge { font-size: 12px; color: var(--nc-muted); white-space: nowrap; }
  .badge.monitored { color: var(--primary-color); }
  .badge.uncertain { color: var(--nc-warning); }

  details { margin-top: 6px; }
  details summary { color: var(--nc-muted); cursor: pointer; font-size: 13px; }
  details dl { display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; margin: 8px 0 0; font-size: 13px; }
  details dt { color: var(--nc-muted); }
  details dd { margin: 0; }

  .suggestion { padding: 10px 0; border-bottom: 1px solid var(--nc-border); }
  .suggestion:last-child { border-bottom: none; }
  .suggestion-head { display: flex; align-items: baseline; gap: 12px; }

  .error { color: var(--nc-alarm); padding: 16px 0; }
  .loading { color: var(--nc-muted); padding: 16px 0; }

  @media (max-width: 600px) {
    main { padding: 12px; }
    .row { gap: 8px; }
  }
`);

/** Haengt die gemeinsame Gestaltung an eine Shadow-Root. */
export function adoptStyles(shadowRoot) {
  shadowRoot.adoptedStyleSheets = [sheet];
}
