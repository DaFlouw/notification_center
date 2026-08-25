/**
 * Kompakte Lovelace-Card (Spezifikation 70).
 *
 * Zeigt entweder die Zaehler oder die aktiven Notifications in Kurzform. Sie
 * nutzt dieselbe Backend-API wie das Panel und enthaelt keine eigene
 * Notification-Logik: was aktiv ist, entscheidet ausschliesslich das Backend.
 *
 * Konfiguration:
 *
 *   type: custom:notification-center-card
 *   mode: counts | list      (Vorgabe: counts)
 *   max: 5                   (nur bei mode: list)
 *   title: Meldungen         (optional)
 */

import { api } from "./api.js";
import { escapeHtml, formatTime } from "./format.js";

const KATEGORIEN = [
  { schluessel: "alarm", einzahl: "Alarm", mehrzahl: "Alarme" },
  { schluessel: "warning", einzahl: "Warnung", mehrzahl: "Warnungen" },
  { schluessel: "info", einzahl: "Info", mehrzahl: "Infos" },
];

class NotificationCenterCard extends HTMLElement {
  #hass = null;
  #config = { mode: "counts", max: 5 };
  #state = { counts: {}, active: [], paused: false };
  #unsubscribe = null;
  #verbunden = false;

  static getStubConfig() {
    return { type: "custom:notification-center-card", mode: "counts" };
  }

  setConfig(config) {
    if (config.mode && !["counts", "list"].includes(config.mode)) {
      throw new Error("mode muss 'counts' oder 'list' sein");
    }
    this.#config = { mode: "counts", max: 5, ...config };
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
      this.#unsubscribe.then((ab) => ab()).catch(() => undefined);
      this.#unsubscribe = null;
      this.#verbunden = false;
    }
  }

  async #verbinden() {
    try {
      this.#unsubscribe = api.subscribeUpdates(this.#hass, (nachricht) => {
        this.#state = {
          counts: nachricht.counts || {},
          active: nachricht.active || [],
          paused: Boolean(nachricht.paused),
        };
        this.#render();
      });
      await this.#unsubscribe;
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
      this.#render();
    }
  }

  #fehler = null;

  #render() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    const locale = this.#hass?.locale?.language || navigator.language;
    const titel = this.#config.title;

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .titel { font-size: 16px; margin-bottom: 12px; }
        .zeile { display: flex; align-items: baseline; gap: 10px; padding: 4px 0; }
        .zahl { font-variant-numeric: tabular-nums; min-width: 1.5em; text-align: right; }
        .meldung { flex: 1; min-width: 0; overflow-wrap: anywhere; }
        .zeit { color: var(--secondary-text-color); font-size: 13px; white-space: nowrap; }
        .balken { align-self: stretch; border-radius: 2px; flex: 0 0 3px; }
        .alarm { color: var(--error-color); }
        .warning { color: var(--warning-color); }
        .info { color: var(--secondary-text-color); }
        .balken.alarm { background: var(--error-color); }
        .balken.warning { background: var(--warning-color); }
        .balken.info { background: var(--secondary-text-color); }
        .ruhig, .pausiert, .fehler { color: var(--secondary-text-color); }
        .fehler { color: var(--error-color); }
        .klickbar { cursor: pointer; }
      </style>
      <ha-card>
        ${titel ? `<div class="titel">${escapeHtml(titel)}</div>` : ""}
        ${this.#fehler ? `<div class="fehler">${escapeHtml(this.#fehler)}</div>` : this.#inhalt(locale)}
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

  #inhalt(locale) {
    if (this.#config.mode === "list") return this.#liste(locale);
    return this.#zaehler();
  }

  #zaehler() {
    const counts = this.#state.counts;
    const zeilen = KATEGORIEN.filter((kategorie) => (counts[kategorie.schluessel] || 0) > 0).map(
      (kategorie) => {
        const anzahl = counts[kategorie.schluessel];
        const wort = anzahl === 1 ? kategorie.einzahl : kategorie.mehrzahl;
        return `
          <div class="zeile ${kategorie.schluessel}">
            <span class="zahl">${anzahl}</span><span class="meldung">${wort}</span>
          </div>`;
      }
    );

    if (!zeilen.length) return this.#ruhig();
    return `${this.#pausenhinweis()}${zeilen.join("")}`;
  }

  #liste(locale) {
    const eintraege = this.#state.active.slice(0, this.#config.max);
    if (!eintraege.length) return this.#ruhig();

    const zeilen = eintraege.map(
      (event) => `
        <div class="zeile ${event.entity_id ? "klickbar" : ""}"
             ${event.entity_id ? `data-entity="${escapeHtml(event.entity_id)}"` : ""}>
          <span class="balken ${event.type}"></span>
          <span class="meldung">${escapeHtml(event.message)}</span>
          <span class="zeit">${formatTime(event.start_time, locale)}</span>
        </div>`
    );

    const rest = this.#state.active.length - eintraege.length;
    const weitere = rest > 0 ? `<div class="zeile ruhig">und ${rest} weitere</div>` : "";

    return `${this.#pausenhinweis()}${zeilen.join("")}${weitere}`;
  }

  #ruhig() {
    return `${this.#pausenhinweis()}<div class="ruhig">Alles ruhig</div>`;
  }

  #pausenhinweis() {
    return this.#state.paused ? '<div class="pausiert">Pausiert</div>' : "";
  }
}

customElements.define("notification-center-card", NotificationCenterCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "notification-center-card",
  name: "Notification Center",
  description: "Aktive Meldungen des Notification Centers in Kurzform.",
});
