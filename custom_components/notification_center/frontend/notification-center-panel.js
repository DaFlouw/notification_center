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

import { MODULE_VERSION, api, backendZuAlt, versionsKonflikt } from "./api.js";
import { adoptStyles } from "./styles.js";
import { renderDashboard } from "./views/dashboard.js";
import { LEERER_FILTER, buildQuery, renderHistory } from "./views/history.js";
import { renderDiscovery } from "./views/discovery.js";
import {
  entwurfZuRegel,
  leereRegel,
  renderRuleOverview,
  renderRules,
  uebersichtAusKonfiguration,
} from "./views/rules.js";

const SEITEN = [
  { id: "dashboard", titel: "Dashboard" },
  { id: "history", titel: "Historie" },
  { id: "rules", titel: "Regeln" },
  { id: "discovery", titel: "Discovery" },
];

const SEITENGROESSE = 50;

/** Wartezeit, bis eine Eingabe als fertig gilt. */
const ENTPRELLUNG = 500;

class NotificationCenterPanel extends HTMLElement {
  #hass = null;
  #unsubscribe = null;
  #tick = null;
  #seite = "dashboard";

  #dashboard = { active: [], counts: {}, paused: false };
  #history = { events: [], total: 0, hasMore: false, filter: { ...LEERER_FILTER }, areas: [] };
  #discovery = { entities: [], domain: "", search: "", suggestions: {} };
  #rules = { entityId: null, entityName: "", rules: [], entwurf: null, states: [], attributes: [] };
  #ruleOverview = { entities: [], rules: [], loading: false };
  #setupErledigt = true;
  #backendZuAlt = false;
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
      Promise.resolve(this.#unsubscribe)
        .then((ab) => ab())
        .catch(() => undefined);
      this.#unsubscribe = null;
    }
  }

  // -- Daten -------------------------------------------------------------

  async #verbinden() {
    try {
      // Der Einrichtungsassistent ist uebersprungbar und erscheint nur
      // einmal (Spezifikation 67).
      const konfiguration = await api.getConfig(this.#hass);
      this.#backendZuAlt = backendZuAlt(konfiguration);
      this.#setupErledigt =
        Boolean(konfiguration.settings.setup_completed) ||
        (konfiguration.entities || []).length > 0;
      if (!this.#setupErledigt) this.#seite = "welcome";

      // Aenderungen werden zugestellt, nicht abgefragt (Spezifikation 45).
      this.#unsubscribe = await api.subscribeUpdates(this.#hass, (nachricht) => {
        this.#dashboard = {
          active: nachricht.active || [],
          counts: nachricht.counts || {},
          paused: Boolean(nachricht.paused),
        };
        if (this.#seite === "dashboard") this.#render();
      });
      this.#render();
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

  async #ladeRegeluebersicht() {
    this.#ruleOverview.loading = true;
    this.#render();

    try {
      const konfiguration = await api.getConfig(this.#hass);
      this.#ruleOverview = uebersichtAusKonfiguration(konfiguration);
      this.#fehler = null;
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
    } finally {
      this.#ruleOverview.loading = false;
      this.#render();
    }
  }

  async #ladeRegeln(entityId, name) {
    try {
      const [konfiguration, optionen] = await Promise.all([
        api.getConfig(this.#hass),
        api.getSuggestions(this.#hass, entityId),
      ]);

      this.#rules = {
        entityId,
        entityName: name || this.#rules.entityName,
        rules: konfiguration.rules.filter((regel) => regel.entity_id === entityId),
        entwurf: null,
        states: optionen.states || [],
        attributes: optionen.attributes || [],
      };
      this.#seite = "rule-editor";
      this.#fehler = null;
    } catch (fehler) {
      this.#fehler = fehler.message || String(fehler);
    }
    this.#render();
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

    if (feld.dataset.ruleField) {
      this.#entwurfGeaendert(feld.dataset.ruleField, feld);
      return;
    }
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

    if (feld.dataset.ruleField) {
      // Ohne erneutes Zeichnen: der Fokus soll im Feld bleiben.
      this.#entwurfGeaendert(feld.dataset.ruleField, feld, { neuZeichnen: false });
      return;
    }
    if (feld.dataset.filter === "suche") {
      this.#history.filter.search = feld.value;
      this.#entprellt(() => this.#ladeHistorie());
    }
    if (feld.dataset.discovery === "search") {
      this.#discovery.search = feld.value;
      this.#entprellt(() => this.#ladeDiscovery());
    }
  };

  #entprellTimer = null;

  #entprellt(fn) {
    if (this.#entprellTimer) clearTimeout(this.#entprellTimer);
    this.#entprellTimer = setTimeout(fn, ENTPRELLUNG);
  }

  #filterGeaendert(feld, wert) {
    const filter = this.#history.filter;
    if (feld === "typ") filter.types = wert ? [wert] : [];
    if (feld === "quelle") filter.sources = wert ? [wert] : [];
    if (feld === "bereich") filter.area_ids = wert ? [wert] : [];
    if (feld === "zeitraum") filter.zeitraum = wert;
    this.#ladeHistorie();
  }

  #entwurfGeaendert(feld, element, { neuZeichnen = true } = {}) {
    const entwurf = this.#rules.entwurf;
    if (!entwurf) return;

    if (feld === "kind") entwurf.kind = element.value;
    else if (feld === "type") entwurf.type = element.value;
    else if (feld === "operator") entwurf.operator = element.value;
    else if (feld === "threshold") entwurf.threshold = element.value;
    else if (feld === "release") entwurf.release_threshold = element.value;
    else if (feld === "message") entwurf.message_template = element.value;
    else if (feld === "duration") {
      const minuten = Number(element.value);
      entwurf.duration_seconds = minuten > 0 ? minuten * 60 : null;
    } else if (feld === "source") {
      entwurf.value_source = element.value
        ? { kind: "attribute", attribute: element.value }
        : { kind: "state", attribute: null };
    } else if (feld === "states") {
      entwurf.states = element.multiple
        ? Array.from(element.selectedOptions).map((option) => option.value)
        : element.value
            .split(",")
            .map((wert) => wert.trim())
            .filter(Boolean);
    }

    if (neuZeichnen) this.#render();
  }

  async #aktion(aktion, daten) {
    try {
      if (aktion === "show-rules") {
        await this.#ladeRegeln(daten.entity, daten.name);
        return;
      }

      if (aktion === "new-rule") {
        this.#rules.entwurf = leereRegel(this.#rules.entityId);
        this.#render();
        return;
      }

      if (aktion === "edit-rule") {
        // Aus der Uebersicht heraus sind die Regeln der Entity noch nicht
        // geladen; ohne das faende der Editor nichts zu bearbeiten.
        if (daten.entity && this.#rules.entityId !== daten.entity) {
          await this.#ladeRegeln(daten.entity, daten.name);
        }
        const regel = this.#rules.rules.find((eintrag) => eintrag.rule_id === daten.rule);
        if (regel) {
          this.#rules.entwurf = { ...regel };
          this.#seite = "rule-editor";
          this.#render();
        }
        return;
      }

      if (aktion === "cancel-rule") {
        this.#rules.entwurf = null;
        this.#render();
        return;
      }

      if (aktion === "save-rule") {
        await api.saveRule(this.#hass, entwurfZuRegel(this.#rules.entwurf));
        await this.#ladeRegeln(this.#rules.entityId);
        return;
      }

      if (aktion === "back-to-rules") {
        await this.#ladeRegeluebersicht();
        this.#seite = "rules";
        this.#render();
        return;
      }

      if (aktion === "delete-rule") {
        if (!confirm("Regel löschen? Eine laufende Meldung dazu endet sofort.")) return;
        await api.deleteRule(this.#hass, daten.rule);
        if (this.#seite === "rules") await this.#ladeRegeluebersicht();
        else await this.#ladeRegeln(this.#rules.entityId);
        return;
      }

      if (aktion === "replace-entity") {
        const neu = prompt("Entity-ID der neuen Entity:");
        if (!neu) return;
        await api.replaceEntity(this.#hass, daten.entity, neu.trim());
        await this.#ladeRegeln(neu.trim());
        return;
      }

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
        // Derselbe Knopf klappt wieder ein.
        if (this.#discovery.suggestions[daten.entity]) {
          delete this.#discovery.suggestions[daten.entity];
          this.#render();
          return;
        }
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

    if (seite === "rule-editor") return;
    if (seite === "rules") this.#ladeRegeluebersicht();
    else if (seite === "history") this.#ladeHistorie();
    else if (seite === "discovery") this.#ladeDiscovery();
    else this.#render();
  }

  // -- Darstellung -------------------------------------------------------

  #render() {
    const locale = this.#hass?.locale?.language || navigator.language;
    const fokus = this.#merkeFokus();

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
        ${this.#versionshinweis()}
        ${this.#fehler ? `<div class="error">${this.#fehler}</div>` : ""}
        ${this.#inhalt(locale)}
      </main>
    `;

    this.#stelleFokusHer(fokus);
  }

  /**
   * Merkt sich das aktive Eingabefeld samt Schreibmarke.
   *
   * Das Panel zeichnet sich vollstaendig neu. Ohne diese Rettung verliert ein
   * Suchfeld bei jedem Tastendruck den Fokus, und man kann kein Wort tippen.
   */
  #merkeFokus() {
    const element = this.shadowRoot.activeElement;
    if (!(element instanceof HTMLElement)) return null;

    const kennung = element.dataset.filter
      ? `[data-filter="${element.dataset.filter}"]`
      : element.dataset.discovery
        ? `[data-discovery="${element.dataset.discovery}"]`
        : element.dataset.ruleField
          ? `[data-rule-field="${element.dataset.ruleField}"]`
          : null;

    if (!kennung) return null;
    return { kennung, position: element.selectionStart ?? null };
  }

  #stelleFokusHer(fokus) {
    if (!fokus) return;

    const element = this.shadowRoot.querySelector(fokus.kennung);
    if (!(element instanceof HTMLElement)) return;

    element.focus();
    if (fokus.position !== null && typeof element.setSelectionRange === "function") {
      try {
        element.setSelectionRange(fokus.position, fokus.position);
      } catch {
        // Nicht jedes Eingabefeld erlaubt eine Schreibmarke.
      }
    }
  }

  #versionshinweis() {
    if (this.#backendZuAlt) {
      return `<div class="error">
        Die Dateien stammen aus Version ${MODULE_VERSION}, Home Assistant führt
        aber noch einen älteren Stand aus. Bitte Home Assistant neu starten.
      </div>`;
    }
    if (versionsKonflikt.erkannt) {
      return `<div class="error">
        Diese Seite stammt aus Version ${versionsKonflikt.frontend}, das
        Notification Center läuft in Version ${versionsKonflikt.backend}.
        Bitte Home Assistant neu starten und die Seite neu laden.
      </div>`;
    }
    return "";
  }

  #inhalt(locale) {
    if (this.#seite === "welcome") return this.#willkommen();
    if (this.#seite === "rules") return renderRuleOverview(this.#ruleOverview);
    if (this.#seite === "rule-editor") return renderRules(this.#rules);
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
