/**
 * Discovery: Entities suchen, uebernehmen und ihre Regeln verwalten
 * (Spezifikation 63 bis 66).
 *
 * Die Vorschlaege selbst kommen aus dem Backend. Hier steht nur ihre
 * Darstellung: die Empfehlung sichtbar, die Begruendung aufklappbar
 * (Spezifikation 13).
 */

import { escapeHtml, typeLabel } from "../format.js";
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
      "valve",
      "lock",
      "climate",
      "water_heater",
      "switch",
      "light",
      "fan",
      "humidifier",
      "vacuum",
      "lawn_mower",
      "siren",
      "media_player",
      "remote",
      "device_tracker",
      "person",
      "alarm_control_panel",
      "update",
      "number",
      "select",
      "text",
      "date",
      "datetime",
      "time",
      "todo",
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

/** Wie viele Typen als Schnellwahl erscheinen. */
const SCHNELLWAHL = 6;

const STATUS = ["all", "monitored", "suggested"];

export function renderDiscovery(state) {
  const {
    entities = [],
    domain = "",
    search = "",
    loading,
    suggestions = {},
    status = "all",
    domainCounts = {},
  } = state;

  return `
    <section class="card pad" aria-label="${t("discovery.filterLabel")}">
      <div class="filters">
        <input type="search" data-discovery="search" placeholder="${t("discovery.searchPlaceholder")}"
               value="${escapeHtml(search)}" aria-label="${t("history.search")}">

        <div class="segmented" role="group" aria-label="${t("discovery.statusLabel")}">
          ${STATUS.map(
            (wert) =>
              `<button data-action="set-discovery-status" data-value="${wert}"
                       aria-pressed="${status === wert}">${t(`discovery.status.${wert}`)}</button>`
          ).join("")}
        </div>

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
      </div>

      ${schnellwahl(domainCounts, domain)}
    </section>

    ${loading ? `<div class="loading">${t("common.loading")}</div>` : ""}

    ${
      entities.length
        ? nachBereich(entities)
            .map(
              ([bereich, eintraege]) => `
                <section class="section">
                  <div class="section-title">${escapeHtml(bereich)} · ${t("discovery.entityCount", {
                    count: eintraege.length,
                  })}</div>
                  <ul class="card rows">
                    ${eintraege
                      .map((eintrag) => entityZeile(eintrag, suggestions[eintrag.entity_id]))
                      .join("")}
                  </ul>
                </section>
              `
            )
            .join("")
        : loading
          ? ""
          : `<div class="card empty"><strong>${t("discovery.empty")}</strong><span>${t("discovery.emptyHint")}</span></div>`
    }
  `;
}

/**
 * Die haeufigsten Typen dieser Anlage als Schnellwahl, mit ihrer Anzahl.
 *
 * Die vollstaendige Auswahl bleibt daneben bestehen: es gibt ueber dreissig
 * Typen, und als Pillen waeren sie eine Wand. Gezeigt wird, was hier
 * tatsaechlich vorkommt -- das ist zugleich die Auskunft, wo es sich lohnt
 * zu suchen.
 */
function schnellwahl(domainCounts, domain) {
  const haeufigste = Object.entries(domainCounts || {})
    .filter(([, anzahl]) => anzahl > 0)
    .sort(([, a], [, b]) => b - a)
    .slice(0, SCHNELLWAHL);
  if (!haeufigste.length) return "";

  return `
    <div class="filters" role="group" aria-label="${t("discovery.entityType")}">
      <button class="btn filter all" data-action="set-domain" data-domain=""
              aria-pressed="${domain === ""}">${t("discovery.allTypes")}</button>
      ${haeufigste
        .map(
          ([domaene, anzahl]) =>
            `<button class="btn filter" data-action="set-domain" data-domain="${escapeHtml(domaene)}"
                     aria-pressed="${domain === domaene}">${escapeHtml(
                       t(`discovery.domain.${domaene}`)
                     )} <span class="row-sub">${anzahl}</span></button>`
        )
        .join("")}
    </div>
  `;
}

/** Gruppiert nach Bereich; was keinem zugeordnet ist, steht am Ende. */
function nachBereich(entities) {
  const ohne = t("rules.noArea");
  const gruppen = new Map();

  for (const eintrag of entities) {
    const bereich = eintrag.area_name || ohne;
    if (!gruppen.has(bereich)) gruppen.set(bereich, []);
    gruppen.get(bereich).push(eintrag);
  }

  return [...gruppen.entries()].sort(
    ([a], [b]) => (a === ohne ? 1 : 0) - (b === ohne ? 1 : 0) || a.localeCompare(b)
  );
}

function entityZeile(eintrag, vorschlaege) {
  const wert = [eintrag.state, eintrag.unit].filter((teil) => teil != null && teil !== "").join(" ");

  return `
    <li class="entity-item">
      <div class="row entity-row${vorschlaege ? " tint special" : ""}">
        <span class="row-body">
          <span class="entity-name">${escapeHtml(eintrag.name)}</span>
          <span class="mono">${escapeHtml(eintrag.entity_id)}${
            eintrag.device_name ? ` · ${escapeHtml(eintrag.device_name)}` : ""
          }</span>
        </span>

        ${wert ? `<span class="chip on-surface">${escapeHtml(wert)}</span>` : ""}

        ${
          eintrag.monitored
            ? `<span class="badge monitored">${t("discovery.monitored")} · ${t("discovery.rules", {
                count: eintrag.rule_count,
              })}</span>
               <button class="btn soft" data-action="show-rules"
                       data-entity="${escapeHtml(eintrag.entity_id)}"
                       data-name="${escapeHtml(eintrag.name)}">${t("discovery.rulesButton")}</button>
               <button class="btn" data-action="remove-entity"
                       data-entity="${escapeHtml(eintrag.entity_id)}">${t("discovery.remove")}</button>`
            : `${
                 eintrag.has_suggestions
                   ? `<span class="pill special">${t("discovery.suggestionsAvailable")}</span>`
                   : ""
               }
               <button class="btn" data-action="show-suggestions"
                       data-entity="${escapeHtml(eintrag.entity_id)}" aria-expanded="${Boolean(vorschlaege)}">${
                         vorschlaege ? t("discovery.hideSuggestions") : t("discovery.suggestions")
                       }</button>
               <button class="btn primary" data-action="add-entity"
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
        ${vorschlag.type ? `<span class="pill ${escapeHtml(vorschlag.type)}">${escapeHtml(typeLabel(vorschlag.type))}</span>` : ""}
        <span class="message">${escapeHtml(vorschlag.title)}</span>
        ${vorschlag.uncertain ? `<span class="badge uncertain">${t("discovery.uncertain")}</span>` : ""}
      </div>
      ${begruendung(vorschlag)}
      <div class="footer-link">
        <button class="btn primary" data-action="accept-suggestion"
                data-entity="${escapeHtml(entityId)}"
                data-suggestion="${escapeHtml(vorschlag.key)}">${t("discovery.adoptWithRule")}</button>
      </div>
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
