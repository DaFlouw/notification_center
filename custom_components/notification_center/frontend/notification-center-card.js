/**
 * Kompakte Lovelace-Card (Spezifikation 70).
 *
 * Sie zeigt dasselbe wie das Dashboard im Panel: aktive Meldungen nach
 * Alarmen, Warnungen und Infos gruppiert, je mit Meldung und Ausloeseuhrzeit.
 * Keine Dauer, kein Link zur Historie; die Zahl der heutigen Ereignisse steht
 * darunter.
 *
 * Sie nutzt dieselbe Backend-API wie das Panel und enthaelt keine eigene
 * Notification-Logik: was aktiv ist, entscheidet ausschliesslich das Backend.
 *
 * Konfiguration:
 *
 *   type: custom:notification-center-card
 *   mode: list | counts      (Vorgabe: list)
 *   title: Meldungen         (optional)
 *   max: 10                  (optional, hoechstens so viele je Kategorie)
 *   show_events_today: true  (optional)
 *
 * Aussehen: die Karte ist ueber CSS-Variablen anpassbar, im Theme oder per
 * card_mod. Alle Bausteine tragen ausserdem einen ``part``-Namen, sodass sie
 * sich von aussen mit ``::part()`` ansprechen lassen.
 *
 *   --notification-center-alarm-color
 *   --notification-center-warning-color
 *   --notification-center-info-color
 *   --notification-center-heading-color
 *   --notification-center-heading-size
 *   --notification-center-message-size
 *   --notification-center-time-color
 *   --notification-center-time-size
 *   --notification-center-row-gap
 *   --notification-center-row-padding
 *   --notification-center-bar-width
 *   --notification-center-card-padding
 *   --notification-center-divider
 */

import { api, backendZuAlt, versionsKonflikt } from "./api.js";
import { escapeHtml, formatTime } from "./format.js";

const KATEGORIEN = [
  { schluessel: "alarm", titel: "Alarme", einzahl: "Alarm" },
  { schluessel: "warning", titel: "Warnungen", einzahl: "Warnung" },
  { schluessel: "info", titel: "Infos", einzahl: "Info" },
];

const STYLES = `
  :host {
    --nc-alarm: var(--notification-center-alarm-color, var(--error-color, #db4437));
    --nc-warning: var(--notification-center-warning-color, var(--warning-color, #ffa600));
    --nc-info: var(--notification-center-info-color, var(--secondary-text-color, #6b6b6b));
    --nc-heading: var(--notification-center-heading-color, var(--secondary-text-color));
    --nc-time: var(--notification-center-time-color, var(--secondary-text-color));
    --nc-divider: var(--notification-center-divider, var(--divider-color, rgba(127,127,127,.25)));
  }

  ha-card { padding: var(--notification-center-card-padding, 16px); }

  .titel {
    font-size: var(--notification-center-title-size, 16px);
    margin-bottom: 12px;
  }

  h2 {
    font-size: var(--notification-center-heading-size, 13px);
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--nc-heading);
    margin: 16px 0 4px;
  }

  h2:first-of-type { margin-top: 0; }

  ul { list-style: none; margin: 0; padding: 0; }

  .zeile {
    display: flex;
    align-items: baseline;
    gap: var(--notification-center-row-gap, 12px);
    padding: var(--notification-center-row-padding, 8px 0);
    border-bottom: 1px solid var(--nc-divider);
  }

  .zeile:last-child { border-bottom: none; }
  .zeile.klickbar { cursor: pointer; }

  .balken {
    align-self: stretch;
    border-radius: 2px;
    flex: 0 0 var(--notification-center-bar-width, 3px);
  }

  .balken.alarm { background: var(--nc-alarm); }
  .balken.warning { background: var(--nc-warning); }
  .balken.info { background: var(--nc-info); }

  .meldung {
    flex: 1;
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: var(--notification-center-message-size, inherit);
  }

  .zeit {
    color: var(--nc-time);
    font-size: var(--notification-center-time-size, 13px);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .zahl {
    font-variant-numeric: tabular-nums;
    min-width: 1.5em;
    text-align: right;
  }

  .zahl.alarm { color: var(--nc-alarm); }
  .zahl.warning { color: var(--nc-warning); }
  .zahl.info { color: var(--nc-info); }

  .ruhig { color: var(--nc-heading); }
  .ruhig strong { display: block; font-weight: 400; color: var(--primary-text-color); }

  .fuss {
    color: var(--nc-heading);
    font-size: var(--notification-center-footer-size, 13px);
    margin-top: 12px;
  }

  .pausiert { color: var(--nc-heading); font-size: 13px; padding-bottom: 8px; }
  .fehler { color: var(--nc-alarm); }
`;

class NotificationCenterCard extends HTMLElement {
  #hass = null;
  #config = { mode: "list", show_events_today: true };
  #state = { counts: {}, active: [], paused: false };
  #unsubscribe = null;
  #verbunden = false;
  #fehler = null;
  #backendZuAlt = false;

  static getStubConfig() {
    return { type: "custom:notification-center-card", mode: "list" };
  }

  setConfig(config) {
    if (config.mode && !["counts", "list"].includes(config.mode)) {
      throw new Error("mode muss 'list' oder 'counts' sein");
    }
    // Vorgabe ist die Liste: eine Meldungskarte, die nur zaehlt, beantwortet
    // die naheliegendste Frage nicht.
    this.#config = { mode: "list", show_events_today: true, ...config };
    this.#render();
  }

  getCardSize() {
    return this.#config.mode === "list" ? 3 : 1;
  }

  set hass(hass) {
    this.#hass = hass;
    if (!this.#verbunden) {
      this.#verbunden = true;
      this.#verbinden();
    }
  }

  connectedCallback() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this.#render();
  }

  disconnectedCallback() {
    if (this.#unsubscribe) {
      Promise.resolve(this.#unsubscribe)
        .then((ab) => ab())
        .catch(() => undefined);
      this.#unsubscribe = null;
      this.#verbunden = false;
    }
  }

  async #verbinden() {
    try {
      this.#unsubscribe = await api.subscribeUpdates(this.#hass, (nachricht) => {
        this.#backendZuAlt = backendZuAlt(nachricht);
        this.#state = {
          counts: nachricht.counts || {},
          active: nachricht.active || [],
          paused: Boolean(nachricht.paused),
        };
        this.#render();
      });
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
      this.#render();
    }
  }

  // -- Darstellung -------------------------------------------------------

  #render() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    const locale = this.#hass?.locale?.language || navigator.language;

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <ha-card part="card">
        ${
          this.#config.title
            ? `<div class="titel" part="title">${escapeHtml(this.#config.title)}</div>`
            : ""
        }
        ${this.#hinweis()}
        ${this.#inhalt(locale)}
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll("[data-entity]").forEach((element) => {
      element.addEventListener("click", () => {
        this.dispatchEvent(
          new CustomEvent("hass-more-info", {
            detail: { entityId: element.dataset.entity },
            bubbles: true,
            composed: true,
          })
        );
      });
    });
  }

  #hinweis() {
    if (this.#fehler) {
      return `<div class="fehler" part="error">${escapeHtml(this.#fehler)}</div>`;
    }
    if (this.#backendZuAlt) {
      return `<div class="fehler" part="error">
        Home Assistant führt einen älteren Stand aus. Bitte neu starten.
      </div>`;
    }
    if (versionsKonflikt.erkannt) {
      return `<div class="fehler" part="error">
        Version ${versionsKonflikt.frontend} gegen ${versionsKonflikt.backend}.
        Bitte Home Assistant neu starten und die Seite neu laden.
      </div>`;
    }
    return this.#state.paused ? '<div class="pausiert" part="paused">Pausiert</div>' : "";
  }

  #inhalt(locale) {
    if (this.#config.mode === "counts") return this.#zaehler();
    return this.#liste(locale);
  }

  /** Wie das Dashboard im Panel: nach Kategorien, neueste zuerst. */
  #liste(locale) {
    const aktive = this.#state.active;
    if (!aktive.length) return this.#ruhig();

    const grenze = this.#config.max;
    const abschnitte = KATEGORIEN.map((kategorie) => {
      let eintraege = aktive
        .filter((event) => event.type === kategorie.schluessel)
        .sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

      if (!eintraege.length) return "";

      const rest = grenze ? Math.max(0, eintraege.length - grenze) : 0;
      if (grenze) eintraege = eintraege.slice(0, grenze);

      return `
        <h2 part="heading">${kategorie.titel}</h2>
        <ul part="list">
          ${eintraege.map((event) => this.#zeile(event, locale)).join("")}
          ${rest ? `<li class="zeile"><span class="meldung">und ${rest} weitere</span></li>` : ""}
        </ul>
      `;
    }).join("");

    return `${abschnitte}${this.#fuss()}`;
  }

  #zeile(event, locale) {
    const klickbar = Boolean(event.entity_id);

    return `
      <li class="zeile ${klickbar ? "klickbar" : ""}" part="row row-${event.type}"
          ${klickbar ? `data-entity="${escapeHtml(event.entity_id)}"` : ""}>
        <span class="balken ${event.type}" part="bar"></span>
        <span class="meldung" part="message">${escapeHtml(event.message)}</span>
        <span class="zeit" part="time">${formatTime(event.start_time, locale)}</span>
      </li>
    `;
  }

  #zaehler() {
    const counts = this.#state.counts;
    const zeilen = KATEGORIEN.filter((k) => (counts[k.schluessel] || 0) > 0).map((k) => {
      const anzahl = counts[k.schluessel];
      return `
        <li class="zeile" part="row row-${k.schluessel}">
          <span class="zahl ${k.schluessel}" part="count">${anzahl}</span>
          <span class="meldung" part="message">${anzahl === 1 ? k.einzahl : k.titel}</span>
        </li>`;
    });

    if (!zeilen.length) return this.#ruhig();
    return `<ul part="list">${zeilen.join("")}</ul>${this.#fuss()}`;
  }

  #ruhig() {
    return `
      <div class="ruhig" part="empty">
        <strong>Alles ruhig</strong>
        ${this.#ereignisText()}
      </div>
    `;
  }

  #fuss() {
    const text = this.#ereignisText();
    return text ? `<div class="fuss" part="footer">${text}</div>` : "";
  }

  #ereignisText() {
    if (this.#config.show_events_today === false) return "";
    const anzahl = this.#state.counts.events_today ?? 0;
    return `${anzahl} ${anzahl === 1 ? "Ereignis" : "Ereignisse"} heute`;
  }
}

// Das Modul kann mehr als einmal geladen werden, etwa wenn es sowohl als
// Lovelace-Ressource als auch als zusaetzliches Frontend-Modul eingebunden
// ist. Ein zweiter define() wuerde werfen und die Registrierung in
// customCards nie erreichen: die Karte verschwaende dann aus der Auswahl.
if (!customElements.get("notification-center-card")) {
  customElements.define("notification-center-card", NotificationCenterCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((karte) => karte.type === "notification-center-card")) {
  window.customCards.push({
    type: "notification-center-card",
    name: "Notification Center",
    description: "Aktive Meldungen des Notification Centers.",
    preview: true,
    documentationURL: "https://github.com/DaFlouw/notification_center#lovelace-card",
  });
}
