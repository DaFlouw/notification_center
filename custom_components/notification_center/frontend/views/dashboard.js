/**
 * Dashboard: ausschliesslich aktive Notifications (Spezifikation 51 bis 57).
 *
 * Oben der Ueberblick in vier Kacheln, darunter die Meldungen je
 * Dringlichkeit, die neuesten oben. Die Kacheln sind zugleich der Filter: ein
 * Klick zeigt nur diese Dringlichkeit, ein zweiter hebt das wieder auf. Die
 * vierte fuehrt zu den Ereignissen von heute.
 *
 * Die Version steht hier und nur hier, klein am Fuss: wer sie sucht, findet
 * sie, und wer sie nicht sucht, wird nicht behelligt.
 */

import { categoryLabel, escapeHtml, eventDuration, formatTime, sourceBadge } from "../format.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";

const KATEGORIEN = ["alarm", "warning", "info"];

export function renderDashboard(state, locale) {
  const { active = [], counts = {}, paused = false, filter = null, areas = {}, version = "" } = state;
  const gewaehlt = KATEGORIEN.includes(filter) ? filter : null;

  const abschnitte = KATEGORIEN.filter((kategorie) => !gewaehlt || kategorie === gewaehlt)
    .map((kategorie) => abschnitt(kategorie, active, areas, locale, Boolean(gewaehlt)))
    .join("");

  return `
    ${paused ? `<div class="paused">${t("common.paused")}</div>` : ""}
    ${kacheln(active, counts, gewaehlt)}
    ${
      active.length || gewaehlt
        ? abschnitte
        : `<div class="card empty"><strong>${t("dashboard.quiet")}</strong></div>`
    }
    ${
      version
        ? `<div class="version">${escapeHtml(t("dashboard.version", { version }))} ·
             <button class="link quiet" data-action="open-integration">${t(
               "dashboard.settings"
             )}</button></div>`
        : ""
    }
  `;
}

/**
 * Die vier Kacheln.
 *
 * Gezaehlt wird aus den gezeigten Meldungen und nicht aus den Zaehlern des
 * Backends: beide stimmen ueberein, aber so kann die Zahl einer Kachel nie
 * von der Liste darunter abweichen.
 */
function kacheln(active, counts, gewaehlt) {
  const typen = KATEGORIEN.map((kategorie) => {
    const anzahl = active.filter((event) => event.type === kategorie).length;
    const gedrueckt = gewaehlt === kategorie;
    return `
      <button class="tile ${kategorie}${gewaehlt && !gedrueckt ? " dimmed" : ""}"
              data-action="filter-dashboard" data-type="${kategorie}"
              aria-pressed="${gedrueckt}">
        <span class="tile-top">
          <span class="tile-label">${categoryLabel(kategorie)}</span>
          <span class="icon-chip ${kategorie}">${icon(kategorie)}</span>
        </span>
        <span class="tile-value">${anzahl}</span>
      </button>
    `;
  }).join("");

  const heute = counts.events_today ?? 0;

  return `
    <div class="tiles">
      ${typen}
      <button class="tile neutral" data-action="show-today"
              aria-label="${escapeHtml(t("events.today", { count: heute }))}">
        <span class="tile-top">
          <span class="tile-label">${t("dashboard.eventsToday")}</span>
          <span class="link">${t("dashboard.historyLink")}</span>
        </span>
        <span class="tile-value">${heute}</span>
      </button>
    </div>
  `;
}

function abschnitt(kategorie, active, areas, locale, immerZeigen) {
  const eintraege = active
    .filter((event) => event.type === kategorie)
    .sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

  // Ohne Filter erscheint nur, was es gibt. Mit Filter wird auch die Leere
  // gezeigt: wer "Alarme" anklickt, soll lesen, dass es keine gibt.
  if (!eintraege.length && !immerZeigen) return "";

  return `
    <section class="card">
      <div class="card-head ${kategorie}">
        <h2>${categoryLabel(kategorie)}</h2>
        <span class="row-sub">${t("dashboard.activeCount", { count: eintraege.length })}</span>
      </div>
      ${
        eintraege.length
          ? `<ul class="rows">${eintraege.map((event) => zeile(event, areas, locale)).join("")}</ul>`
          : `<div class="rows"><div class="row-sub" style="padding: 4px 12px 12px">${t(
              "dashboard.noneOfType"
            )}</div></div>`
      }
    </section>
  `;
}

function zeile(event, areas, locale) {
  // Klickbar nur mit verknuepfter Entity (Spezifikation 30 und 71).
  const klickbar = Boolean(event.entity_id);
  const ort = event.source === "ha_system" ? "Home Assistant" : areas[event.area_id] || "";
  const seit = t("dashboard.since", { time: formatTime(event.start_time, locale) });

  return `
    <li class="row tint ${event.type} ${klickbar ? "clickable" : ""}"
        ${klickbar ? `data-entity="${escapeHtml(event.entity_id)}" tabindex="0" role="button"` : ""}>
      <span class="icon-chip ${event.type}">${icon(event.type, 18)}</span>
      <span class="row-body">
        <span class="row-title"><span class="message">${escapeHtml(event.message)}</span>${sourceBadge(event)}</span>
        <span class="row-sub">${ort ? `${escapeHtml(ort)} · ` : ""}${escapeHtml(seit)}</span>
      </span>
      <span class="pill plain duration">${eventDuration(event)}</span>
      <!--
        Abhaken, ohne auf die Bedingung zu warten. Der Eintrag bleibt im Log
        und ist dort wieder aktivierbar; deshalb steht hier kein Loeschen.
      -->
      <button class="btn" data-action="deactivate-event"
              data-event="${escapeHtml(event.event_id)}"
              title="${t("dashboard.deactivateHint")}">${t("dashboard.deactivate")}</button>
    </li>
  `;
}
