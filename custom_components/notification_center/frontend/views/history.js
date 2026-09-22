/**
 * Historie: aktive und abgeschlossene Ereignisse (Spezifikation 58 bis 62).
 *
 * Filtern, Suchen und Blaettern passieren im Backend. Wie viele Eintraege eine
 * Seite umfasst, waehlt der Anwender; weitere kommen auf Anforderung. Die
 * Sortierung ist rein chronologisch: aktive Ereignisse werden nicht nach oben
 * geschoben (Spezifikation 34).
 */

import { escapeHtml, eventDuration, formatDateTime, typeLabel } from "../format.js";
import { t } from "../i18n.js";

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

  return `
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
      </select>

      <select data-filter="zeitraum" aria-label="${t("history.period")}">
        ${ZEITRAEUME.map(
          (z) =>
            `<option value="${z.wert}" ${filter.zeitraum === z.wert ? "selected" : ""}>${t(z.schluessel)}</option>`
        ).join("")}
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

      <input type="search" data-filter="suche" placeholder="${t("history.search")}"
             value="${escapeHtml(filter.search)}" aria-label="${t("history.search")}">

      <button class="action secondary" data-action="clear-history">${t("history.clearAll")}</button>
    </div>

    ${loading ? `<div class="loading">${t("common.loading")}</div>` : ""}

    ${
      events.length
        ? `<ul>${events.map((event) => zeile(event, locale)).join("")}</ul>`
        : loading
          ? ""
          : `<div class="empty"><strong>${t("history.empty")}</strong><span>${t("history.emptyHint")}</span></div>`
    }

    ${
      hasMore
        ? `<div class="footer-link"><button class="action secondary" data-action="load-more">${t("history.loadMore")}</button>
             <span class="badge">${t("history.shownOfTotal", { shown: events.length, total })}</span></div>`
        : events.length
          ? `<div class="footer-link"><span class="badge">${t("history.entries", { count: total })}</span></div>`
          : ""
    }
  `;
}

function zeile(event, locale) {
  const klickbar = Boolean(event.entity_id);

  return `
    <li class="row ${klickbar ? "clickable" : ""}"
        ${klickbar ? `data-entity="${escapeHtml(event.entity_id)}" tabindex="0" role="button"` : ""}>
      <span class="bar ${event.type}"></span>
      <span class="time">${formatDateTime(event.start_time, locale)}</span>
      <span class="badge type-${event.type}">${typeLabel(event.type)}</span>
      <span class="message">${escapeHtml(event.message)}</span>
      <span class="duration">${event.active ? t("dashboard.active") : eventDuration(event)}</span>
      ${
        event.active
          ? ""
          : `<button class="link" data-action="delete-event" data-event="${escapeHtml(event.event_id)}"
                     title="${t("history.deleteEntry")}" aria-label="${t("history.deleteEntry")}">×</button>`
      }
    </li>
  `;
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
