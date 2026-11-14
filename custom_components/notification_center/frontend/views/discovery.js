/**
 * Discovery: Entities suchen, uebernehmen und ihre Regeln verwalten
 * (Spezifikation 63 bis 66).
 *
 * Die Vorschlaege selbst kommen aus dem Backend. Hier steht nur ihre
 * Darstellung: die Empfehlung in Bausteinen, die Begruendung als Satz
 * darunter (Spezifikation 13, Konzept Abschnitt Discovery).
 */

import { escapeHtml, typeLabel } from "../format.js";
import { raw } from "../html.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { bedingungsChips } from "./rules.js";

/** Wie viele Typen als Schnellwahl erscheinen. */
const SCHNELLWAHL = 6;

const STATUS = ["all", "monitored", "without_rule", "suggested"];

export function renderDiscovery(state) {
  const {
    entities = [],
    domain = "",
    search = "",
    loading,
    suggestions = {},
    status = "all",
    domainCounts = {},
    statusCounts = {},
    allDomains = false,
  } = state;

  return `
    <section class="card pad" aria-label="${t("discovery.filterLabel")}">
      <div class="filters">
<label class="search">
          ${icon("search", 18)}
          <input type="search" data-discovery="search" placeholder="${t("discovery.searchPlaceholder")}"
                 value="${escapeHtml(search)}" aria-label="${t("history.search")}">
        </label>

        <div class="segmented" role="group" aria-label="${t("discovery.statusLabel")}">
          ${STATUS.filter(
            // Ein Umschalter, hinter dem nichts steht, ist nur Laerm. Die
            // gewaehlte Ansicht bleibt stehen, auch wenn sie sich leert --
            // sonst verschwaende der Knopf, auf dem man gerade steht.
            (wert) => wert === "all" || wert === status || statusCounts[wert] !== 0
          )
            .map(
              (wert) =>
                `<button data-action="set-discovery-status" data-value="${wert}"
                         aria-pressed="${status === wert}">${t(`discovery.status.${wert}`)}${
                           // Ein aelteres Backend liefert die Zahlen nicht;
                           // dann steht nur das Wort da.
                           Number.isFinite(statusCounts[wert]) ? ` ${statusCounts[wert]}` : ""
                         }</button>`
            )
            .join("")}
        </div>
      </div>

      ${schnellwahl(domainCounts, domain, allDomains)}
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

    ${weitere(entities.length, statusCounts[status])}
  `;
}

/**
 * Der Knopf fuer die naechsten Treffer.
 *
 * Erscheint nur, wenn das Backend mehr kennt, als gezeigt wird -- abgelesen
 * an der Zahl des gewaehlten Umschalters. Ohne diese Zahl (aelteres Backend)
 * bleibt er weg, statt ins Leere zu fuehren.
 */
function weitere(gezeigt, gesamt) {
  if (!Number.isFinite(gesamt) || gesamt <= gezeigt) return "";
  return `
    <div class="footer-link center">
      <span class="row-sub">${t("history.shownOfTotal", { shown: gezeigt, total: gesamt })}</span>
      <button class="btn" data-action="discovery-more">${t("discovery.loadMore")}</button>
    </div>
  `;
}

/**
 * Die Typen dieser Anlage als Pillen, mit ihrer Anzahl.
 *
 * Das ist die *einzige* Typ-Auswahl. Frueher stand daneben noch ein
 * Auswahlfeld mit denselben Typen -- zweimal "Alle Typen" nebeneinander, und
 * keiner wusste, welches gilt. Gezeigt werden zuerst die haeufigsten; der
 * Rest klappt auf Wunsch dazu. Was es hier nicht gibt, wird nicht angeboten.
 */
function schnellwahl(domainCounts, domain, alle) {
  const vorhanden = Object.entries(domainCounts || {})
    .filter(([, anzahl]) => anzahl > 0)
    .sort(([, a], [, b]) => b - a);
  if (!vorhanden.length) return "";

  const sichtbar = alle ? vorhanden : vorhanden.slice(0, SCHNELLWAHL);
  // Der gewaehlte Typ bleibt sichtbar, auch wenn er zu den seltenen gehoert.
  const gewaehlt = vorhanden.find(([domaene]) => domaene === domain);
  if (gewaehlt && !sichtbar.includes(gewaehlt)) sichtbar.push(gewaehlt);
  const uebrig = vorhanden.length - sichtbar.length;

  return `
    <div class="filters tight" role="group" aria-label="${t("discovery.entityType")}">
      <button class="btn filter plain" data-action="set-domain" data-domain=""
              aria-pressed="${domain === ""}">${t("discovery.allTypes")}</button>
      ${sichtbar
        .map(
          ([domaene, anzahl]) =>
            `<button class="btn filter plain" data-action="set-domain" data-domain="${escapeHtml(domaene)}"
                     aria-pressed="${domain === domaene}">${escapeHtml(
                       t(`discovery.domain.${domaene}`)
                     )} <span class="row-sub">${anzahl}</span></button>`
        )
        .join("")}
      ${
        uebrig > 0 || alle
          ? `<button class="link" data-action="toggle-domains" aria-expanded="${Boolean(alle)}">${
              alle ? t("discovery.fewerTypes") : t("discovery.moreTypes", { count: uebrig })
            }</button>`
          : ""
      }
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
  const offen = Boolean(vorschlaege);
  const ziel = `data-entity="${escapeHtml(eintrag.entity_id)}" data-name="${escapeHtml(eintrag.name)}"`;

  return `
    <li class="entity-item${offen ? " open" : ""}">
      <div class="row entity-row">
        <span class="row-body">
          <span class="entity-name">${escapeHtml(eintrag.name)}</span>
          <span class="mono">${escapeHtml(eintrag.entity_id)}${
            eintrag.device_name ? ` · ${escapeHtml(eintrag.device_name)}` : ""
          }</span>
        </span>

        ${wert ? `<span class="chip on-surface">${escapeHtml(wert)}</span>` : ""}

        ${eintrag.monitored ? ueberwacht(eintrag, ziel) : unbeobachtet(eintrag, vorschlaege, ziel)}
      </div>

      ${offen ? vorschlagsBlock(eintrag, vorschlaege) : ""}
    </li>
  `;
}

/** Schon uebernommen: Stand der Regeln und der Weg dorthin. */
function ueberwacht(eintrag, ziel) {
  // Entfernen steht bewusst nicht hier, sondern auf der Seite der Regeln:
  // neben "Uebernehmen" der Nachbarzeile war es der Knopf, den man trifft,
  // wenn man den anderen meint.
  return `
    <span class="badge ${eintrag.rule_count ? "monitored" : "uncertain"}">${
      eintrag.rule_count
        ? `${t("discovery.monitored")} · ${t("discovery.rules", { count: eintrag.rule_count })}`
        : t("discovery.monitoredNoRule")
    }</span>
    <button class="link" data-action="show-rules" ${ziel}>${t("discovery.rulesButton")}</button>
  `;
}

/**
 * Noch nicht uebernommen.
 *
 * Der Knopf fuer die Vorschlaege erscheint nur, wo das Backend welche
 * erwartet. Vorher stand er an jeder Zeile und fuehrte meist zu "keine
 * Vorschlaege" -- ein Klick, der nichts bringt, an tausend Entities.
 */
function unbeobachtet(eintrag, vorschlaege, ziel) {
  const offen = Boolean(vorschlaege);
  const knopf =
    eintrag.has_suggestions || offen
      ? `<button class="btn special" data-action="show-suggestions"
                 data-entity="${escapeHtml(eintrag.entity_id)}" aria-expanded="${offen}">${
                   offen ? t("discovery.hideSuggestions") : t("discovery.viewSuggestions")
                 }</button>`
      : "";

  // Ist der Vorschlag offen, stehen beide Antworten darunter; die Zeile
  // wiederholt sie nicht.
  const uebernehmen =
    offen && vorschlaege.length
      ? ""
      : `<button class="btn" data-action="add-entity" ${ziel}>${t("common.adopt")}</button>`;

  return knopf + uebernehmen;
}

function vorschlagsBlock(eintrag, vorschlaege) {
  if (!vorschlaege.length) {
    return `<div class="suggestions">
      <div class="entity-meta">${t("discovery.noSuggestions")}</div>
    </div>`;
  }

  return `
    <div class="suggestions">
      ${vorschlaege.map((vorschlag) => vorschlagZeile(eintrag, vorschlag)).join("")}
    </div>
  `;
}

function vorschlagZeile(eintrag, vorschlag) {
  const entityId = eintrag.entity_id;
  const dauer = vorschlag.duration_seconds
    ? `<span class="chip">${t("rules.chip.longer", {
        minutes: raw(`<strong>${Math.round(vorschlag.duration_seconds / 60)} min</strong>`),
      })}</span>`
    : "";

  return `
    <div class="suggestion" title="${escapeHtml(vorschlag.title || "")}">
      <div class="suggestion-head">
        ${vorschlag.type ? `<span class="pill ${escapeHtml(vorschlag.type)}">${escapeHtml(typeLabel(vorschlag.type))}</span>` : ""}
        ${bedingungsChips({ ...vorschlag, entity_id: null })}${dauer}
        ${vorschlag.uncertain ? `<span class="badge uncertain">${t("discovery.uncertain")}</span>` : ""}
      </div>
      ${begruendung(vorschlag)}
      <div class="footer-link">
        <button class="btn primary" data-action="accept-suggestion"
                data-entity="${escapeHtml(entityId)}"
                data-suggestion="${escapeHtml(vorschlag.key)}">${t("discovery.adoptWithRule")}</button>
        <!--
          Die zweite Antwort auf einen Vorschlag: die Entity will ich, die
          Regel nicht. Sie steht hier, wo die Entscheidung faellt.
        -->
        <button class="btn" data-action="add-entity"
                data-entity="${escapeHtml(entityId)}"
                data-name="${escapeHtml(eintrag.name)}">${t("discovery.adoptWithoutRule")}</button>
      </div>
    </div>
  `;
}

/** Die Begruendung als ein Satz unter den Bausteinen. */
function begruendung(vorschlag) {
  if (!vorschlag.reasons || !vorschlag.reasons.length) return "";

  return `<p class="why">${t("discovery.whyLead")} ${vorschlag.reasons
    .map((grund) => `${escapeHtml(grund.label)}: ${escapeHtml(grund.value)}`)
    .join(" · ")}</p>`;
}
