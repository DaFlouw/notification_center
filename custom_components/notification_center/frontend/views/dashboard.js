/**
 * Dashboard: ausschliesslich aktive Notifications (Spezifikation 51 bis 57).
 *
 * Gezeigt werden nur Meldung und Zeitpunkt. Keine zweite Zeile mit Entity
 * oder Geraet, keine Icons vor den Kategorien, keine Animationen. Innerhalb
 * jeder Kategorie stehen die neuesten oben.
 */

import { categoryLabel, eventDuration, escapeHtml, formatTime } from "../format.js";
import { t } from "../i18n.js";

const KATEGORIEN = ["alarm", "warning", "info"];

export function renderDashboard(state, locale) {
  const { active = [], counts = {}, paused = false } = state;

  if (!active.length) {
    return leerZustand(counts, paused);
  }

  const abschnitte = KATEGORIEN.map((kategorie) => {
    const eintraege = active
      .filter((event) => event.type === kategorie)
      .sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

    if (!eintraege.length) return "";

    return `
      <h2>${categoryLabel(kategorie)}</h2>
      <ul>
        ${eintraege.map((event) => zeile(event, locale)).join("")}
      </ul>
    `;
  }).join("");

  return `
    ${paused ? `<div class="paused">${t("common.paused")}</div>` : ""}
    ${abschnitte}
    ${fusszeile(counts)}
  `;
}

function zeile(event, locale) {
  // Klickbar nur mit verknuepfter Entity (Spezifikation 30 und 71).
  const klickbar = Boolean(event.entity_id);

  return `
    <li class="row ${klickbar ? "clickable" : ""}"
        ${klickbar ? `data-entity="${escapeHtml(event.entity_id)}" tabindex="0" role="button"` : ""}>
      <span class="bar ${event.type}"></span>
      <span class="message">${escapeHtml(event.message)}</span>
      <span class="time">${formatTime(event.start_time, locale)}</span>
      <span class="duration">${eventDuration(event)}</span>
    </li>
  `;
}

function leerZustand(counts, paused) {
  return `
    ${paused ? `<div class="paused">${t("common.paused")}</div>` : ""}
    <div class="empty">
      <strong>${t("dashboard.quiet")}</strong>
      <span>${ereignisText(counts)} · <button class="link" data-nav="history">${t("dashboard.historyLink")}</button></span>
    </div>
  `;
}

function fusszeile(counts) {
  return `
    <div class="footer-link">
      ${ereignisText(counts)} · <button class="link" data-nav="history">${t("dashboard.historyLink")}</button>
    </div>
  `;
}

function ereignisText(counts) {
  return t("events.today", { count: counts.events_today ?? 0 });
}
