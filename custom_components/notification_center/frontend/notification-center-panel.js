/**
 * Das Notification-Center-Panel.
 *
 * Bewusst buildfrei: native Web Components, keine Bibliothek, kein Bundler.
 * Die ausgelieferten Dateien sind genau die im Repository.
 *
 * Hier steht ausschliesslich Darstellung und Bedienung. Jede Entscheidung
 * darueber, was eine Notification ist, wann sie entsteht und wann sie endet,
 * faellt im Backend (Spezifikation 50).
 */

import { api } from "./api.js";
import { adoptStyles } from "./styles.js";
import { renderDashboard } from "./views/dashboard.js";
import { LEERER_FILTER, buildQuery, renderHistory } from "./views/history.js";
import { renderDiscovery } from "./views/discovery.js";

const SEITEN = [
  { id: "dashboard", titel: "Dashboard" },
  { id: "history", titel: "Historie" },
  { id: "discovery", titel: "Discovery" },
];

const SEITENGROESSE = 50;

class NotificationCenterPanel extends HTMLElement {
  #hass = null;
  #unsubscribe = null;
  #tick = null;
  #seite = "dashboard";

  #dashboard = { active: [], counts: {}, paused: false };
  #history = { events: [], total: 0, hasMore: false, filter: { ...LEERER_FILTER }, areas: [] };
  #discovery = { entities: [], domain: "", search: "", suggestions: {} };
  #setupErledigt = true;
  #fehler = null;

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    adoptStyles(this.shadowRoot);
  }

  set hass(hass) {
    const ersteZuweisung = this.#hass === null;
    this.#hass = hass;
    if (ersteZuweisung) {
      this.#verbinden();
    }
  }

  get hass() {
    return this.#hass;
  }

  connectedCallback() {
    this.shadowRoot.addEventListener("click", this.#onClick);
    this.shadowRoot.addEventListener("change", this.#onChange);
    this.shadowRoot.addEventListener("input", this.#onInput);
    this.shadowRoot.addEventListener("keydown", this.#onKeydown);

    // Aktive Notifications tragen eine mitlaufende Dauer (Spezifikation 33).
    // Ein Takt pro Minute genuegt dafuer; Daten holt er keine.
    this.#tick = setInterval(() => {
      if (this.#seite === "dashboard" && this.#dashboard.active.length) this.#render();
    }, 60000);

    this.#render();
  }

  disconnectedCallback() {
    this.shadowRoot.removeEventListener("click", this.#onClick);
    this.shadowRoot.removeEventListener("change", this.#onChange);
    this.shadowRoot.removeEventListener("input", this.#onInput);
    this.shadowRoot.removeEventListener("keydown", this.#onKeydown);

    if (this.#tick) clearInterval(this.#tick);
    if (this.#unsubscribe) {
      this.#unsubscribe.then((ab) => ab()).catch(() => undefined);
      this.#unsubscribe = null;
    }
  }

  // -- Daten -------------------------------------------------------------

  async #verbinden() {
    try {
      // Der Einrichtungsassistent ist uebersprungbar und erscheint nur
      // einmal (Spezifikation 67).
      const konfiguration = await api.getConfig(this.#hass);
      this.#setupErledigt = Boolean(konfiguration.settings.setup_completed);
      if (!this.#setupErledigt) this.#seite = "welcome";

      // Aenderungen werden zugestellt, nicht abgefragt (Spezifikation 45).
      this.#unsubscribe = api.subscribeUpdates(this.#hass, (nachricht) => {
        this.#dashboard = {
          active: nachricht.active || [],
          counts: nachricht.counts || {},
          paused: Boolean(nachricht.paused),
        };
        if (this.#seite === "dashboard") this.#render();
      });
      await this.#unsubscribe;
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
      this.#render();
    }
  }

  async #ladeHistorie({ anhaengen = false } = {}) {
    this.#history.loading = true;
    this.#render();

    try {
      const offset = anhaengen ? this.#history.events.length : 0;
      const antwort = await api.getHistory(
        this.#hass,
        buildQuery(this.#history.filter, offset, SEITENGROESSE)
      );

      this.#history.events = anhaengen
        ? [...this.#history.events, ...antwort.events]
        : antwort.events;
      this.#history.total = antwort.total;
      this.#history.hasMore = antwort.has_more;
      this.#history.areas = this.#bereiche();
      this.#fehler = null;
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
    } finally {
      this.#history.loading = false;
      this.#render();
    }
  }

  async #ladeDiscovery() {
    this.#discovery.loading = true;
    this.#render();

    try {
      const antwort = await api.discover(this.#hass, {
        domain: this.#discovery.domain || null,
        search: this.#discovery.search || null,
      });
      this.#discovery.entities = antwort.entities;
      this.#fehler = null;
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
    } finally {
      this.#discovery.loading = false;
      this.#render();
    }
  }

  #bereiche() {
    const registry = this.#hass?.areas || {};
    return Object.values(registry)
      .map((bereich) => ({ area_id: bereich.area_id, name: bereich.name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  // -- Ereignisse --------------------------------------------------------

  #onClick = (ereignis) => {
    const ziel = ereignis.composedPath().find((el) => el instanceof HTMLElement && el.dataset);
    if (!ziel) return;

    const knopf = ereignis
      .composedPath()
      .find((el) => el instanceof HTMLElement && (el.dataset.action || el.dataset.nav));

    if (knopf?.dataset.nav) {
      this.#wechsle(knopf.dataset.nav);
      return;
    }

    if (knopf?.dataset.action) {
      ereignis.stopPropagation();
      this.#aktion(knopf.dataset.action, knopf.dataset);
      return;
    }

    const nav = ereignis.composedPath().find((el) => el instanceof HTMLElement && el.dataset.page);
    if (nav) {
      this.#wechsle(nav.dataset.page);
      return;
    }

    const zeile = ereignis
      .composedPath()
      .find((el) => el instanceof HTMLElement && el.dataset.entity && el.classList.contains("row"));
    if (zeile) this.#zeigeEntity(zeile.dataset.entity);
  };

  #onKeydown = (ereignis) => {
    if (ereignis.key !== "Enter" && ereignis.key !== " ") return;
    const zeile = ereignis
      .composedPath()
      .find((el) => el instanceof HTMLElement && el.dataset.entity && el.classList.contains("row"));
    if (zeile) {
      ereignis.preventDefault();
      this.#zeigeEntity(zeile.dataset.entity);
    }
  };

  #onChange = (ereignis) => {
    const feld = ereignis.target;
    if (!(feld instanceof HTMLElement)) return;

    if (feld.dataset.filter) {
      this.#filterGeaendert(feld.dataset.filter, feld.value);
      return;
    }
    if (feld.dataset.discovery === "domain") {
      this.#discovery.domain = feld.value;
      this.#ladeDiscovery();
    }
  };

  #onInput = (ereignis) => {
    const feld = ereignis.target;
    if (!(feld instanceof HTMLElement)) return;

    if (feld.dataset.filter === "suche") {
      this.#entprellt(() => {
        this.#history.filter.search = feld.value;
        this.#ladeHistorie();
      });
    }
    if (feld.dataset.discovery === "search") {
      this.#entprellt(() => {
        this.#discovery.search = feld.value;
        this.#ladeDiscovery();
      });
    }
  };

  #entprellTimer = null;

  #entprellt(fn) {
    if (this.#entprellTimer) clearTimeout(this.#entprellTimer);
    this.#entprellTimer = setTimeout(fn, 300);
  }

  #filterGeaendert(feld, wert) {
    const filter = this.#history.filter;
    if (feld === "typ") filter.types = wert ? [wert] : [];
    if (feld === "quelle") filter.sources = wert ? [wert] : [];
    if (feld === "bereich") filter.area_ids = wert ? [wert] : [];
    if (feld === "zeitraum") filter.zeitraum = wert;
    this.#ladeHistorie();
  }

  async #aktion(aktion, daten) {
    try {
      if (aktion === "start-setup" || aktion === "skip-setup") {
        await api.setSettings(this.#hass, { setup_completed: true });
        this.#setupErledigt = true;
        this.#seite = aktion === "start-setup" ? "discovery" : "dashboard";
        if (this.#seite === "discovery") await this.#ladeDiscovery();
        else this.#render();
        return;
      }

      if (aktion === "load-more") {
        await this.#ladeHistorie({ anhaengen: true });
        return;
      }

      if (aktion === "delete-event") {
        await api.deleteEvent(this.#hass, daten.event);
        await this.#ladeHistorie();
        return;
      }

      if (aktion === "clear-history") {
        // Ausdrueckliche Bestaetigung (Spezifikation 39).
        if (!confirm("Alle abgeschlossenen Einträge löschen? Aktive bleiben erhalten.")) return;
        await api.clearHistory(this.#hass);
        await this.#ladeHistorie();
        return;
      }

      if (aktion === "add-entity") {
        await api.addEntities(this.#hass, [daten.entity]);
        await this.#ladeDiscovery();
        return;
      }

      if (aktion === "remove-entity") {
        if (!confirm("Entity aus der Überwachung entfernen? Die Historie bleibt erhalten.")) return;
        await api.removeEntity(this.#hass, daten.entity);
        await this.#ladeDiscovery();
        return;
      }

      if (aktion === "show-suggestions") {
        const antwort = await api.getSuggestions(this.#hass, daten.entity);
        this.#discovery.suggestions[daten.entity] = antwort.suggestions;
        this.#render();
        return;
      }

      if (aktion === "accept-suggestion") {
        await this.#uebernehmeVorschlag(daten.entity, daten.suggestion);
      }
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
      this.#render();
    }
  }

  async #uebernehmeVorschlag(entityId, key) {
    const vorschlaege = this.#discovery.suggestions[entityId] || [];
    const vorschlag = vorschlaege.find((eintrag) => eintrag.key === key);
    if (!vorschlag) return;

    await api.addEntities(this.#hass, [entityId]);
    await api.saveRule(this.#hass, {
      entity_id: entityId,
      kind: vorschlag.kind,
      type: vorschlag.type,
      states: vorschlag.states,
      operator: vorschlag.operator,
      threshold: vorschlag.threshold,
      release_threshold: vorschlag.release_threshold,
      duration_seconds: vorschlag.duration_seconds,
      message_template: vorschlag.message_template,
    });

    delete this.#discovery.suggestions[entityId];
    await this.#ladeDiscovery();
  }

  #zeigeEntity(entityId) {
    // Klick oeffnet die Home-Assistant-Detailansicht (Spezifikation 71).
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      })
    );
  }

  #wechsle(seite) {
    if (this.#seite === seite) return;
    this.#seite = seite;
    this.#fehler = null;

    if (seite === "history") this.#ladeHistorie();
    else if (seite === "discovery") this.#ladeDiscovery();
    else this.#render();
  }

  // -- Darstellung -------------------------------------------------------

  #render() {
    const locale = this.#hass?.locale?.language || navigator.language;

    this.shadowRoot.innerHTML = `
      <header><h1>Notification Center</h1></header>
      <nav ${this.#seite === "welcome" ? 'hidden=""' : ""}>
        ${SEITEN.map(
          (seite) =>
            `<button data-page="${seite.id}" ${
              this.#seite === seite.id ? 'aria-current="page"' : ""
            }>${seite.titel}</button>`
        ).join("")}
      </nav>
      <main>
        ${this.#fehler ? `<div class="error">${this.#fehler}</div>` : ""}
        ${this.#inhalt(locale)}
      </main>
    `;
  }

  #inhalt(locale) {
    if (this.#seite === "welcome") return this.#willkommen();
    if (this.#seite === "history") return renderHistory(this.#history, locale);
    if (this.#seite === "discovery") return renderDiscovery(this.#discovery);
    return renderDashboard(this.#dashboard, locale);
  }

  #willkommen() {
    return `
      <div class="empty">
        <strong>Willkommen im Notification Center</strong>
        <span>
          Wähle aus, welche Entities überwacht werden sollen. Vorschläge für
          Regeln entstehen dabei automatisch.
        </span>
        <div style="margin-top: 24px; display: flex; gap: 8px; justify-content: center">
          <button class="action" data-action="start-setup">Einrichtung starten</button>
          <button class="action secondary" data-action="skip-setup">Überspringen</button>
        </div>
      </div>
    `;
  }
}

customElements.define("notification-center-panel", NotificationCenterPanel);
