/**
 * Discovery: Entities suchen, uebernehmen und ihre Regeln verwalten
 * (Spezifikation 63 bis 66).
 *
 * Die Vorschlaege selbst kommen aus dem Backend. Hier steht nur ihre
 * Darstellung: die Empfehlung sichtbar, die Begruendung aufklappbar
 * (Spezifikation 13).
 */

import { escapeHtml } from "../format.js";

const TYPEN = [
  { wert: "", text: "Alle Typen" },
  { wert: "binary_sensor", text: "Binärsensor" },
  { wert: "sensor", text: "Sensor" },
  { wert: "cover", text: "Abdeckung" },
  { wert: "lock", text: "Schloss" },
  { wert: "climate", text: "Klima" },
  { wert: "switch", text: "Schalter" },
  { wert: "light", text: "Licht" },
  { wert: "device_tracker", text: "Anwesenheit" },
  { wert: "alarm_control_panel", text: "Alarmanlage" },
  { wert: "update", text: "Aktualisierung" },
];

export function renderDiscovery(state) {
  const { entities = [], domain = "", search = "", loading, suggestions = {} } = state;

  return `
    <div class="filters">
      <select data-discovery="domain" aria-label="Entity-Typ">
        ${TYPEN.map(
          (typ) =>
            `<option value="${typ.wert}" ${domain === typ.wert ? "selected" : ""}>${typ.text}</option>`
        ).join("")}
      </select>
      <input type="search" data-discovery="search" placeholder="Name oder Entity-ID"
             value="${escapeHtml(search)}" aria-label="Suchen">
    </div>

    ${loading ? '<div class="loading">Wird geladen …</div>' : ""}

    ${
      entities.length
        ? `<ul>${entities.map((eintrag) => entityZeile(eintrag, suggestions[eintrag.entity_id])).join("")}</ul>`
        : loading
          ? ""
          : '<div class="empty"><strong>Nichts gefunden</strong><span>Andere Suche oder anderen Typ probieren.</span></div>'
    }
  `;
}

function entityZeile(eintrag, vorschlaege) {
  return `
    <li>
      <div class="entity-row">
        <span class="entity-main">
          <div class="entity-name">${escapeHtml(eintrag.name)}</div>
          <div class="entity-meta">
            ${escapeHtml(eintrag.entity_id)}
            ${eintrag.device_name ? ` · ${escapeHtml(eintrag.device_name)}` : ""}
            ${eintrag.area_name ? ` · ${escapeHtml(eintrag.area_name)}` : ""}
          </div>
        </span>

        ${
          eintrag.monitored
            ? `<span class="badge monitored">überwacht · ${eintrag.rule_count} ${
                eintrag.rule_count === 1 ? "Regel" : "Regeln"
              }</span>
               <button class="action secondary" data-action="show-rules"
                       data-entity="${escapeHtml(eintrag.entity_id)}"
                       data-name="${escapeHtml(eintrag.name)}">Regeln</button>
               <button class="action secondary" data-action="remove-entity"
                       data-entity="${escapeHtml(eintrag.entity_id)}">Entfernen</button>`
            : `${eintrag.has_suggestions ? '<span class="badge">Vorschläge verfügbar</span>' : ""}
               <button class="action secondary" data-action="show-suggestions"
                       data-entity="${escapeHtml(eintrag.entity_id)}">Vorschläge</button>
               <button class="action" data-action="add-entity"
                       data-entity="${escapeHtml(eintrag.entity_id)}"
                       data-name="${escapeHtml(eintrag.name)}">Übernehmen</button>`
        }
      </div>

      ${vorschlaege ? vorschlagsBlock(eintrag.entity_id, vorschlaege) : ""}
    </li>
  `;
}

function vorschlagsBlock(entityId, vorschlaege) {
  if (!vorschlaege.length) {
    return `<div class="entity-meta" style="padding: 0 0 12px">
      Keine belastbaren Vorschläge. Eine eigene Regel ist trotzdem möglich:
      Entity übernehmen und dann unter Regeln anlegen.
    </div>`;
  }

  return `
    <div style="padding: 0 0 12px">
      <div class="entity-meta">${vorschlaege.length} ${
        vorschlaege.length === 1 ? "Vorschlag" : "Vorschläge"
      }</div>
      ${vorschlaege.map((vorschlag) => vorschlagZeile(entityId, vorschlag)).join("")}
    </div>
  `;
}

function vorschlagZeile(entityId, vorschlag) {
  return `
    <div class="suggestion">
      <div class="suggestion-head">
        <span class="message">${escapeHtml(vorschlag.title)}</span>
        ${vorschlag.uncertain ? '<span class="badge uncertain">unsicher</span>' : ""}
        <button class="action secondary" data-action="accept-suggestion"
                data-entity="${escapeHtml(entityId)}"
                data-suggestion="${escapeHtml(vorschlag.key)}">Übernehmen</button>
      </div>
      ${begruendung(vorschlag)}
    </div>
  `;
}

function begruendung(vorschlag) {
  if (!vorschlag.reasons || !vorschlag.reasons.length) return "";

  return `
    <details>
      <summary>Warum dieser Vorschlag?</summary>
      <dl>
        ${vorschlag.reasons
          .map(
            (grund) =>
              `<dt>${escapeHtml(grund.label)}</dt><dd>${escapeHtml(grund.value)}</dd>`
          )
          .join("")}
      </dl>
    </details>
  `;
}
