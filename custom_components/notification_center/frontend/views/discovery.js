/**
 * Discovery: Entities suchen, uebernehmen und ihre Regeln verwalten
 * (Spezifikation 63 bis 66).
 *
 * Die Vorschlaege selbst kommen aus dem Backend. Hier steht nur ihre
 * Darstellung: die Empfehlung sichtbar, die Begruendung aufklappbar
 * (Spezifikation 13).
 */

import { escapeHtml } from "../format.js";

/**
 * Die auswaehlbaren Typen, nach Herkunft getrennt.
 *
 * Die Liste deckt genau die Domaenen ab, die das Backend zur Ueberwachung
 * anbietet. Fehlt hier eine, taucht sie zwar unter "Alle Typen" auf, laesst
 * sich aber nicht gezielt heraussuchen -- so waren die Helfer zuvor gar nicht
 * und mehrere Geraetetypen nur zufaellig zu finden.
 */
const TYP_GRUPPEN = [
  {
    titel: "Geräte",
    typen: [
      { wert: "binary_sensor", text: "Binärsensor" },
      { wert: "sensor", text: "Sensor" },
      { wert: "cover", text: "Abdeckung" },
      { wert: "lock", text: "Schloss" },
      { wert: "climate", text: "Klima" },
      { wert: "water_heater", text: "Warmwasser" },
      { wert: "switch", text: "Schalter" },
      { wert: "light", text: "Licht" },
      { wert: "fan", text: "Lüftung" },
      { wert: "humidifier", text: "Luftbefeuchter" },
      { wert: "vacuum", text: "Staubsauger" },
      { wert: "device_tracker", text: "Anwesenheit" },
      { wert: "person", text: "Person" },
      { wert: "alarm_control_panel", text: "Alarmanlage" },
      { wert: "update", text: "Aktualisierung" },
    ],
  },
  {
    titel: "Helfer",
    typen: [
      { wert: "input_boolean", text: "Schalter" },
      { wert: "input_number", text: "Zahl" },
      { wert: "input_select", text: "Auswahl" },
      { wert: "input_text", text: "Text" },
      { wert: "input_datetime", text: "Datum und Zeit" },
      { wert: "counter", text: "Zähler" },
      { wert: "timer", text: "Timer" },
      { wert: "schedule", text: "Zeitplan" },
    ],
  },
];

export function renderDiscovery(state) {
  const { entities = [], domain = "", search = "", loading, suggestions = {} } = state;

  return `
    <div class="filters">
      <select data-discovery="domain" aria-label="Entity-Typ">
        <option value="" ${domain === "" ? "selected" : ""}>Alle Typen</option>
        ${TYP_GRUPPEN.map(
          (gruppe) => `
            <optgroup label="${escapeHtml(gruppe.titel)}">
              ${gruppe.typen
                .map(
                  (typ) =>
                    `<option value="${typ.wert}" ${
                      domain === typ.wert ? "selected" : ""
                    }>${typ.text}</option>`
                )
                .join("")}
            </optgroup>
          `
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
                       data-entity="${escapeHtml(eintrag.entity_id)}">${
                         vorschlaege ? "Vorschläge ausblenden" : "Vorschläge"
                       }</button>
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
    return `<div class="suggestions">
      <div class="entity-meta">
        Keine belastbaren Vorschläge. Eine eigene Regel ist trotzdem möglich:
        Entity übernehmen und dann unter Regeln anlegen.
      </div>
    </div>`;
  }

  return `
    <div class="suggestions">
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
