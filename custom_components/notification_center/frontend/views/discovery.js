/**
 * Discovery: Entities suchen, uebernehmen und ihre Regeln verwalten
 * (Spezifikation 63 bis 66).
 *
 * Die Vorschlaege selbst kommen aus dem Backend. Hier steht nur ihre
 * Darstellung: die Empfehlung sichtbar, die Begruendung aufklappbar
 * (Spezifikation 13).
 */

import { escapeHtml } from "../format.js";
import { t } from "../i18n.js";

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
    schluessel: "discovery.groupDevices",
    domains: [
      "binary_sensor",
      "sensor",
      "cover",
      "lock",
      "climate",
      "water_heater",
      "switch",
      "light",
      "fan",
      "humidifier",
      "vacuum",
      "device_tracker",
      "person",
      "alarm_control_panel",
      "update",
    ],
  },
  {
    schluessel: "discovery.groupHelpers",
    domains: [
      "input_boolean",
      "input_number",
      "input_select",
      "input_text",
      "input_datetime",
      "counter",
      "timer",
      "schedule",
    ],
  },
];

export function renderDiscovery(state) {
  const { entities = [], domain = "", search = "", loading, suggestions = {} } = state;

  return `
    <div class="filters">
      <select data-discovery="domain" aria-label="${t("discovery.entityType")}">
        <option value="" ${domain === "" ? "selected" : ""}>${t("discovery.allTypes")}</option>
        ${TYP_GRUPPEN.map(
          (gruppe) => `
            <optgroup label="${escapeHtml(t(gruppe.schluessel))}">
              ${gruppe.domains
                .map(
                  (domaene) =>
                    `<option value="${domaene}" ${
                      domain === domaene ? "selected" : ""
                    }>${escapeHtml(t(`discovery.domain.${domaene}`))}</option>`
                )
                .join("")}
            </optgroup>
          `
        ).join("")}
      </select>
      <input type="search" data-discovery="search" placeholder="${t("discovery.searchPlaceholder")}"
             value="${escapeHtml(search)}" aria-label="${t("history.search")}">
    </div>

    ${loading ? `<div class="loading">${t("common.loading")}</div>` : ""}

    ${
      entities.length
        ? `<ul>${entities.map((eintrag) => entityZeile(eintrag, suggestions[eintrag.entity_id])).join("")}</ul>`
        : loading
          ? ""
          : `<div class="empty"><strong>${t("discovery.empty")}</strong><span>${t("discovery.emptyHint")}</span></div>`
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
            ? `<span class="badge monitored">${t("discovery.monitored")} · ${t("discovery.rules", {
                count: eintrag.rule_count,
              })}</span>
               <button class="action secondary" data-action="show-rules"
                       data-entity="${escapeHtml(eintrag.entity_id)}"
                       data-name="${escapeHtml(eintrag.name)}">${t("discovery.rulesButton")}</button>
               <button class="action secondary" data-action="remove-entity"
                       data-entity="${escapeHtml(eintrag.entity_id)}">${t("discovery.remove")}</button>`
            : `${eintrag.has_suggestions ? `<span class="badge">${t("discovery.suggestionsAvailable")}</span>` : ""}
               <button class="action secondary" data-action="show-suggestions"
                       data-entity="${escapeHtml(eintrag.entity_id)}">${
                         vorschlaege ? t("discovery.hideSuggestions") : t("discovery.suggestions")
                       }</button>
               <button class="action" data-action="add-entity"
                       data-entity="${escapeHtml(eintrag.entity_id)}"
                       data-name="${escapeHtml(eintrag.name)}">${t("common.adopt")}</button>`
        }
      </div>

      ${vorschlaege ? vorschlagsBlock(eintrag.entity_id, vorschlaege) : ""}
    </li>
  `;
}

function vorschlagsBlock(entityId, vorschlaege) {
  if (!vorschlaege.length) {
    return `<div class="suggestions">
      <div class="entity-meta">${t("discovery.noSuggestions")}</div>
    </div>`;
  }

  return `
    <div class="suggestions">
      <div class="entity-meta">${t("discovery.suggestionCount", { count: vorschlaege.length })}</div>
      ${vorschlaege.map((vorschlag) => vorschlagZeile(entityId, vorschlag)).join("")}
    </div>
  `;
}

function vorschlagZeile(entityId, vorschlag) {
  return `
    <div class="suggestion">
      <div class="suggestion-head">
        <span class="message">${escapeHtml(vorschlag.title)}</span>
        ${vorschlag.uncertain ? `<span class="badge uncertain">${t("discovery.uncertain")}</span>` : ""}
        <button class="action secondary" data-action="accept-suggestion"
                data-entity="${escapeHtml(entityId)}"
                data-suggestion="${escapeHtml(vorschlag.key)}">${t("common.adopt")}</button>
      </div>
      ${begruendung(vorschlag)}
    </div>
  `;
}

function begruendung(vorschlag) {
  if (!vorschlag.reasons || !vorschlag.reasons.length) return "";

  return `
    <details>
      <summary>${t("discovery.why")}</summary>
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
