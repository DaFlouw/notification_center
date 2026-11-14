/**
 * Historie: aktive und abgeschlossene Ereignisse (Spezifikation 58 bis 62).
 *
 * Filtern, Suchen und Blaettern passieren im Backend. Wie viele Eintraege eine
 * Seite umfasst, waehlt der Anwender; weitere kommen auf Anforderung. Die
 * Sortierung ist rein chronologisch: aktive Ereignisse werden nicht nach oben
 * geschoben (Spezifikation 34).
 */

import { escapeHtml, eventDuration, formatTime, sourceBadge, typeLabel } from "../format.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";

/** Waehlbare Seitengroessen. Das Backend laesst bis zu 500 Eintraege zu. */
export const SEITENGROESSEN = [50, 100, 200];

export const STANDARD_SEITENGROESSE = 100;

export const LEERER_FILTER = {
  types: [],
  sources: [],
  area_ids: [],
  search: "",
  zeitraum: "7",
  limit: STANDARD_SEITENGROESSE,
};

const ZEITRAEUME = [
  { wert: "heute", schluessel: "history.periodToday" },
  { wert: "7", schluessel: "history.periodWeek" },
  { wert: "30", schluessel: "history.periodMonth" },
  { wert: "alle", schluessel: "history.periodAll" },
];

export function renderHistory(state, locale) {
  const { events = [], total = 0, hasMore = false, filter = LEERER_FILTER, areas = [], loading } =
    state;

  const bereichsnamen = Object.fromEntries(areas.map((bereich) => [bereich.area_id, bereich.name]));

  return `
    <section class="card pad" aria-label="${t("history.filterLabel")}">
      <div class="filters">
        <label class="search">
          ${icon("search", 18)}
          <input type="search" data-filter="suche" placeholder="${t("history.search")}"
                 value="${escapeHtml(filter.search)}" aria-label="${t("history.search")}">
        </label>

        <div class="segmented" role="group" aria-label="${t("history.period")}">
          ${ZEITRAEUME.map(
            (z) =>
              `<button data-action="set-period" data-value="${z.wert}"
                       aria-pressed="${filter.zeitraum === z.wert}">${t(z.schluessel)}</button>`
          ).join("")}
        </div>
      </div>

      <div class="filters">
        <select data-filter="typ" aria-label="${t("history.type")}">
          <option value="">${t("history.allTypes")}</option>
          <option value="info" ${filter.types[0] === "info" ? "selected" : ""}>${t("type.info")}</option>
          <option value="warning" ${filter.types[0] === "warning" ? "selected" : ""}>${t("type.warning")}</option>
          <option value="alarm" ${filter.types[0] === "alarm" ? "selected" : ""}>${t("type.alarm")}</option>
        </select>

        <select data-filter="quelle" aria-label="${t("history.source")}">
          <option value="">${t("history.allSources")}</option>
          <option value="entity_rule" ${filter.sources[0] === "entity_rule" ? "selected" : ""}>${t("history.sourceEntityRule")}</option>
          <option value="automation" ${filter.sources[0] === "automation" ? "selected" : ""}>${t("history.sourceAutomation")}</option>
          <option value="ha_system" ${filter.sources[0] === "ha_system" ? "selected" : ""}>${t("history.sourceHaSystem")}</option>
        </select>

        <select data-filter="bereich" aria-label="${t("history.area")}">
          <option value="">${t("history.allAreas")}</option>
          ${areas
            .map(
              (bereich) =>
                `<option value="${escapeHtml(bereich.area_id)}" ${
                  filter.area_ids[0] === bereich.area_id ? "selected" : ""
                }>${escapeHtml(bereich.name)}</option>`
            )
            .join("")}
        </select>

        <select data-filter="umfang" aria-label="${t("history.perPageLabel")}">
          ${SEITENGROESSEN.map(
            (groesse) =>
              `<option value="${groesse}" ${
                seitengroesse(filter) === groesse ? "selected" : ""
              }>${t("history.perPage", { count: groesse })}</option>`
          ).join("")}
        </select>

        <span class="spacer"></span>
        <span class="row-sub">${t("history.shownOfTotal", { shown: events.length, total })}</span>
        <button class="btn danger" data-action="clear-history">${t("history.clearAll")}</button>
      </div>
    </section>

    ${loading ? `<div class="loading">${t("common.loading")}</div>` : ""}

    ${
      events.length
        ? nachTagen(events, locale)
            .map((tag) => tagesAbschnitt(tag, bereichsnamen, locale))
            .join("")
        : loading
          ? ""
          : `<div class="card empty"><strong>${t("history.empty")}</strong><span>${t("history.emptyHint")}</span></div>`
    }

    ${
      hasMore
        ? `<div class="footer-link center"><button class="btn" data-action="load-more">${t("history.loadMore")}</button></div>`
        : ""
    }
  `;
}

/**
 * Teilt die Ereignisse nach Kalendertagen, in der gelieferten Reihenfolge.
 *
 * Eine Uhrzeit ohne Tag sagt in einem Log ueber Wochen nichts; ein Datum an
 * jeder Zeile ist Rauschen. Die Tagesueberschrift traegt das Datum einmal.
 */
export function nachTagen(events, locale, jetzt = new Date()) {
  const tage = [];
  let aktuell = null;

  for (const event of events) {
    const tag = new Date(event.start_time);
    const schluessel = `${tag.getFullYear()}-${tag.getMonth()}-${tag.getDate()}`;
    if (!aktuell || aktuell.schluessel !== schluessel) {
      aktuell = { schluessel, titel: tagesTitel(tag, locale, jetzt), events: [] };
      tage.push(aktuell);
    }
    aktuell.events.push(event);
  }

  return tage;
}

function tagesTitel(tag, locale, jetzt) {
  const mitternacht = (datum) => new Date(datum.getFullYear(), datum.getMonth(), datum.getDate());
  const abstand = Math.round((mitternacht(jetzt) - mitternacht(tag)) / 86400000);

  if (abstand === 0) return t("history.today");
  if (abstand === 1) return t("history.yesterday");
  return tag.toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long" });
}

function tagesAbschnitt(tag, bereichsnamen, locale) {
  return `
    <section class="section">
      <div class="section-title">${escapeHtml(tag.titel)} · ${t("history.entries", {
        count: tag.events.length,
      })}</div>
      <ul class="card rows">
        ${tag.events.map((event) => zeile(event, bereichsnamen, locale)).join("")}
      </ul>
    </section>
  `;
}

function zeile(event, bereichsnamen, locale) {
  const klickbar = Boolean(event.entity_id);
  const ort = bereichsnamen[event.area_id];
  // Getoent wird, was laeuft: so faellt beim Ueberfliegen sofort auf, was
  // noch ansteht, ohne dass das ganze Log bunt wird.
  const klassen = ["row", event.active ? `tint ${event.type}` : "", klickbar ? "clickable" : ""];
  if (deaktiviert(event)) klassen.push("deactivated");

  return `
    <li class="${klassen.filter(Boolean).join(" ")}"
        ${klickbar ? `data-entity="${escapeHtml(event.entity_id)}" tabindex="0" role="button"` : ""}>
      <span class="time">${formatTime(event.start_time, locale)}</span>
      <span class="pill ${event.type}">${typeLabel(event.type)}</span>
      <span class="row-body">
        <span class="row-title">
          <span class="message">${escapeHtml(event.message)}</span>
          ${sourceBadge(event)}
          ${deaktiviert(event) ? `<span class="pill">${t("history.deactivated")}</span>` : ""}
        </span>
        ${ort ? `<span class="row-sub">${escapeHtml(ort)}</span>` : ""}
      </span>
      ${
        event.active
          ? `<span class="pill ok">${t("dashboard.active")}</span>`
          : `<span class="duration">${eventDuration(event)}</span>`
      }
      ${
        deaktiviert(event)
          ? `<button class="btn soft" data-action="reactivate-event"
                     data-event="${escapeHtml(event.event_id)}"
                     title="${t("history.reactivateHint")}">${t("history.reactivate")}</button>`
          : ""
      }
      ${
        event.active
          ? ""
          : `<button class="icon-btn" data-action="delete-event" data-event="${escapeHtml(event.event_id)}"
                     title="${t("history.deleteEntry")}" aria-label="${t("history.deleteEntry")}">${icon("close", 18)}</button>`
      }
    </li>
  `;
}

/**
 * Von Hand deaktiviert -- und damit wieder aktivierbar.
 *
 * Erkannt am Grund des Abschlusses, nicht daran, dass der Eintrag beendet
 * ist: alles andere endete, weil seine Bedingung entfiel, eine Stufe
 * wechselte oder eine Regel verschwand. Das wieder aufzuwecken wuerde eine
 * Lage behaupten, die es nicht mehr gibt.
 */
export function deaktiviert(event) {
  return event?.active === false && event?.close_reason === "deactivated";
}

/**
 * Die gewaehlte Seitengroesse, gegen unbekannte Werte abgesichert.
 *
 * Ein aus einer aelteren Fassung stammender Filter kennt das Feld noch nicht.
 */
export function seitengroesse(filter) {
  const wert = Number(filter?.limit);
  return SEITENGROESSEN.includes(wert) ? wert : STANDARD_SEITENGROESSE;
}

/** Uebersetzt die Filterauswahl in Parameter fuer die Backend-Abfrage. */
export function buildQuery(filter, offset = 0, limit = seitengroesse(filter)) {
  const query = { limit, offset };

  if (filter.types.length) query.types = filter.types;
  if (filter.sources.length) query.sources = filter.sources;
  if (filter.area_ids.length) query.area_ids = filter.area_ids;
  if (filter.search) query.search = filter.search;

  const start = zeitraumBeginn(filter.zeitraum);
  if (start) query.start = start;

  return query;
}

function zeitraumBeginn(zeitraum) {
  if (zeitraum === "alle") return null;

  const jetzt = new Date();
  if (zeitraum === "heute") {
    jetzt.setHours(0, 0, 0, 0);
    return jetzt.toISOString();
  }

  const tage = Number(zeitraum);
  if (!Number.isFinite(tage)) return null;

  jetzt.setDate(jetzt.getDate() - tage);
  return jetzt.toISOString();
}
