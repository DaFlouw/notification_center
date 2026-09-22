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
 *   show_history: false      (optional, Ereignisse des Tages darunter)
 *   history_max: 5           (optional, hoechstens so viele davon)
 *
 * Die Texte richten sich nach der Sprache des angemeldeten Anwenders; die
 * Meldungen selbst stehen so da, wie die Regel sie erzeugt hat.
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
import { categoryLabel, escapeHtml, eventDuration, formatTime, typeLabel } from "./format.js";
import { t, waehleSprache } from "./i18n.js";

const KATEGORIEN = ["alarm", "warning", "info"];

/** Wie viele Ereignisse des Tages die Karte hoechstens zeigt. */
const HISTORIE_VORGABE = 5;

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
  #config = { mode: "list", show_events_today: true, show_history: false };
  #state = { counts: {}, active: [], paused: false };
  #historie = { events: [], geladen: false, fehler: null };
  #historieLaeuft = false;
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
    this.#config = { mode: "list", show_events_today: true, show_history: false, ...config };
    this.#historie = { events: [], geladen: false, fehler: null };
    this.#render();
    if (this.#hass && this.#config.show_history) this.#ladeHistorie();
  }

  getCardSize() {
    const grund = this.#config.mode === "list" ? 3 : 1;
    return this.#config.show_history ? grund + 2 : grund;
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
        // Der Abonnementstrom meldet nur den aktiven Bestand. Was heute
        // schon vorbei ist, steht allein in der Historie -- die muss also
        // erneut geholt werden, sobald sich etwas geruehrt hat.
        if (this.#config.show_history) this.#ladeHistorie();
        this.#render();
      });
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
      this.#render();
    }
  }

  /**
   * Holt die Ereignisse des laufenden Tages.
   *
   * Beginn ist Mitternacht in der Zeitzone des Browsers, nicht die letzten
   * 24 Stunden: gefragt ist, was heute war.
   */
  async #ladeHistorie() {
    if (this.#historieLaeuft) return;
    this.#historieLaeuft = true;

    const beginn = new Date();
    beginn.setHours(0, 0, 0, 0);

    try {
      const antwort = await api.getHistory(this.#hass, {
        start: beginn.toISOString(),
        limit: this.#historieGrenze(),
        offset: 0,
      });
      this.#historie = { events: antwort.events || [], geladen: true, fehler: null };
    } catch (fehler) {
      this.#historie = { events: [], geladen: true, fehler: fehler.message || String(fehler) };
    } finally {
      this.#historieLaeuft = false;
      this.#render();
    }
  }

  #historieGrenze() {
    const wert = Number(this.#config.history_max);
    return Number.isFinite(wert) && wert > 0 ? Math.round(wert) : HISTORIE_VORGABE;
  }

  // -- Darstellung -------------------------------------------------------

  #render() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    const locale = this.#hass?.locale?.language || navigator.language;
    waehleSprache(this.#hass);

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
        ${this.#config.show_history ? this.#historieBlock(locale) : ""}
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
      return `<div class="fehler" part="error">${t("card.backendOutdated")}</div>`;
    }
    if (versionsKonflikt.erkannt) {
      return `<div class="fehler" part="error">${t("card.versionMismatch", {
        frontend: versionsKonflikt.frontend,
        backend: versionsKonflikt.backend,
      })}</div>`;
    }
    return this.#state.paused
      ? `<div class="pausiert" part="paused">${t("common.paused")}</div>`
      : "";
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
        .filter((event) => event.type === kategorie)
        .sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

      if (!eintraege.length) return "";

      const rest = grenze ? Math.max(0, eintraege.length - grenze) : 0;
      if (grenze) eintraege = eintraege.slice(0, grenze);

      return `
        <h2 part="heading">${categoryLabel(kategorie)}</h2>
        <ul part="list">
          ${eintraege.map((event) => this.#zeile(event, locale)).join("")}
          ${
            rest
              ? `<li class="zeile"><span class="meldung">${t("card.more", {
                  count: rest,
                })}</span></li>`
              : ""
          }
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
    const zeilen = KATEGORIEN.filter((kategorie) => (counts[kategorie] || 0) > 0).map(
      (kategorie) => {
        const anzahl = counts[kategorie];
        return `
        <li class="zeile" part="row row-${kategorie}">
          <span class="zahl ${kategorie}" part="count">${anzahl}</span>
          <span class="meldung" part="message">${
            anzahl === 1 ? typeLabel(kategorie) : categoryLabel(kategorie)
          }</span>
        </li>`;
      }
    );

    if (!zeilen.length) return this.#ruhig();
    return `<ul part="list">${zeilen.join("")}</ul>${this.#fuss()}`;
  }

  #ruhig() {
    return `
      <div class="ruhig" part="empty">
        <strong>${t("card.quiet")}</strong>
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
    return t("events.today", { count: this.#state.counts.events_today ?? 0 });
  }

  /**
   * Die Ereignisse des Tages, wie die Historie im Panel, nur kompakt.
   *
   * Gezeigt werden auch abgeschlossene Ereignisse -- genau darum geht es
   * hier: der Blick zurueck auf den Tag, nicht nur auf das, was gerade
   * anliegt.
   */
  #historieBlock(locale) {
    if (this.#historie.fehler) {
      return `<div class="fehler" part="error">${escapeHtml(this.#historie.fehler)}</div>`;
    }
    if (!this.#historie.geladen) return "";

    const eintraege = this.#historie.events.slice(0, this.#historieGrenze());

    return `
      <h2 part="heading">${t("card.historyTitle")}</h2>
      ${
        eintraege.length
          ? `<ul part="list">${eintraege
              .map((event) => this.#historieZeile(event, locale))
              .join("")}</ul>`
          : `<div class="fuss" part="empty">${t("card.historyEmpty")}</div>`
      }
    `;
  }

  #historieZeile(event, locale) {
    const klickbar = Boolean(event.entity_id);

    return `
      <li class="zeile ${klickbar ? "klickbar" : ""}" part="row row-${event.type}"
          ${klickbar ? `data-entity="${escapeHtml(event.entity_id)}"` : ""}>
        <span class="balken ${event.type}" part="bar"></span>
        <span class="meldung" part="message">${escapeHtml(event.message)}</span>
        <span class="zeit" part="time">${formatTime(event.start_time, locale)}</span>
        <span class="zeit" part="duration">${
          event.active ? t("card.historyActive") : eventDuration(event)
        }</span>
      </li>
    `;
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
    name: t("card.name"),
    description: t("card.description"),
    preview: true,
    documentationURL: "https://github.com/DaFlouw/notification_center#lovelace-card",
  });
}
