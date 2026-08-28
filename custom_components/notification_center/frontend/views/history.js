/**
 * Historie: aktive und abgeschlossene Ereignisse (Spezifikation 58 bis 62).
 *
 * Filtern, Suchen und Blaettern passieren im Backend. Wie viele Eintraege eine
 * Seite umfasst, waehlt der Anwender; weitere kommen auf Anforderung. Die
 * Sortierung ist rein chronologisch: aktive Ereignisse werden nicht nach oben
 * geschoben (Spezifikation 34).
 */

import { escapeHtml, eventDuration, formatDateTime, typeLabel } from "../format.js";

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
  { wert: "heute", text: "Heute" },
  { wert: "7", text: "7 Tage" },
  { wert: "30", text: "30 Tage" },
  { wert: "alle", text: "Alle" },
];

export function renderHistory(state, locale) {
  const { events = [], total = 0, hasMore = false, filter = LEERER_FILTER, areas = [], loading } =
    state;

  return `
    <div class="filters">
      <select data-filter="typ" aria-label="Typ">
        <option value="">Alle Typen</option>
        <option value="info" ${filter.types[0] === "info" ? "selected" : ""}>Info</option>
        <option value="warning" ${filter.types[0] === "warning" ? "selected" : ""}>Warnung</option>
        <option value="alarm" ${filter.types[0] === "alarm" ? "selected" : ""}>Alarm</option>
      </select>

      <select data-filter="quelle" aria-label="Quelle">
        <option value="">Alle Quellen</option>
        <option value="entity_rule" ${filter.sources[0] === "entity_rule" ? "selected" : ""}>Entity-Regel</option>
        <option value="automation" ${filter.sources[0] === "automation" ? "selected" : ""}>Automation</option>
      </select>

      <select data-filter="zeitraum" aria-label="Zeitraum">
        ${ZEITRAEUME.map(
          (z) =>
            `<option value="${z.wert}" ${filter.zeitraum === z.wert ? "selected" : ""}>${z.text}</option>`
        ).join("")}
      </select>

      <select data-filter="bereich" aria-label="Bereich">
        <option value="">Alle Bereiche</option>
        ${areas
          .map(
            (bereich) =>
              `<option value="${escapeHtml(bereich.area_id)}" ${
                filter.area_ids[0] === bereich.area_id ? "selected" : ""
              }>${escapeHtml(bereich.name)}</option>`
          )
          .join("")}
      </select>

      <select data-filter="umfang" aria-label="Einträge pro Seite">
        ${SEITENGROESSEN.map(
          (groesse) =>
            `<option value="${groesse}" ${
              seitengroesse(filter) === groesse ? "selected" : ""
            }>${groesse} pro Seite</option>`
        ).join("")}
      </select>

      <input type="search" data-filter="suche" placeholder="Suchen"
             value="${escapeHtml(filter.search)}" aria-label="Suchen">

      <button class="action secondary" data-action="clear-history">Alle löschen</button>
    </div>

    ${loading ? '<div class="loading">Wird geladen …</div>' : ""}

    ${
      events.length
        ? `<ul>${events.map((event) => zeile(event, locale)).join("")}</ul>`
        : loading
          ? ""
          : '<div class="empty"><strong>Keine Ereignisse</strong><span>Für diese Auswahl gibt es keine Einträge.</span></div>'
    }

    ${
      hasMore
        ? `<div class="footer-link"><button class="action secondary" data-action="load-more">Weitere laden</button>
             <span class="badge">${events.length} von ${total}</span></div>`
        : events.length
          ? `<div class="footer-link"><span class="badge">${total} ${total === 1 ? "Eintrag" : "Einträge"}</span></div>`
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
      <span class="duration">${event.active ? "aktiv" : eventDuration(event)}</span>
      ${
        event.active
          ? ""
          : `<button class="link" data-action="delete-event" data-event="${escapeHtml(event.event_id)}"
                     title="Eintrag löschen" aria-label="Eintrag löschen">×</button>`
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
