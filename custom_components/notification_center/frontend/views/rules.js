/**
 * Regel-Editor einer ueberwachten Entity (Spezifikation 14 bis 18).
 *
 * Der einfache Teil steht oben, Hysterese und Zeitbedingung liegen im
 * erweiterten Bereich (Spezifikation 18). Zustandswerte kommen als Auswahl
 * aus der Entity, nicht als freies Textfeld (Spezifikation 14).
 */

import { escapeHtml, typeLabel } from "../format.js";
import { t } from "../i18n.js";

const BEDINGUNGEN = ["state_is", "state_is_not", "state_changed_to", "numeric"];

const OPERATOREN = ["gt", "gte", "lt", "lte", "eq"];

const TYPEN = ["info", "warning", "alarm"];

export function leereRegel(entityId) {
  return {
    entity_id: entityId,
    kind: "state_is",
    type: "warning",
    states: [],
    operator: "gt",
    threshold: null,
    release_threshold: null,
    duration_seconds: null,
    message_template: "",
    value_source: { kind: "state", attribute: null },
  };
}

/**
 * Baut den Zustand der Uebersicht aus der Antwort von get_config.
 *
 * Bewusst hier und nicht im Panel: eine Umformung im Panel liesse sich ohne
 * Browser nicht pruefen. Genau dort ging zuvor die Raumzuordnung verloren,
 * weil die Entities auf Kennung und Namen zusammengestrichen wurden, waehrend
 * das Backend laengst Raum und Geschoss mitlieferte.
 *
 * Die Eintraege werden deshalb unveraendert durchgereicht.
 */
export function uebersichtAusKonfiguration(konfiguration) {
  return {
    entities: konfiguration.entities || [],
    rules: konfiguration.rules || [],
    loading: false,
  };
}

/**
 * Uebersicht aller Regeln, nach Entity gruppiert.
 *
 * Regeln waren zuvor nur ueber die Discovery erreichbar und dort schwer
 * wiederzufinden. Diese Seite zeigt den gesamten Bestand auf einen Blick.
 */
export function renderRuleOverview(state) {
  const { entities = [], rules = [], loading } = state;

  if (loading) return `<div class="loading">${t("common.loading")}</div>`;

  if (!rules.length) {
    return `
      <div class="empty">
        <strong>${t("rules.overviewEmpty")}</strong>
        <span>
          ${t("rules.overviewEmptyHint", {
            link: `<button class="link" data-nav="discovery">${t("nav.discovery")}</button>`,
          })}
        </span>
      </div>
    `;
  }

  const platzierung = new Map(entities.map((eintrag) => [eintrag.entity_id, eintrag]));
  const baum = gruppiere(rules, platzierung);

  const abschnitte = [...baum.entries()]
    .sort(nachNamen)
    .map(([geschoss, raeume]) => {
      const inhalt = [...raeume.entries()]
        .sort(nachNamen)
        .map(
          ([raum, eintraege]) => `
            <div class="rule-room">
              <h3>${escapeHtml(raum)}</h3>
              ${eintraege.map((paar) => entityBlock(paar, platzierung)).join("")}
            </div>
          `
        )
        .join("");

      return `
        <section class="rule-floor">
          <h2>${escapeHtml(geschoss)}</h2>
          ${inhalt}
        </section>
      `;
    });

  return `
    <div class="entity-meta" style="margin-bottom: 12px">
      ${t("rules.count", { count: rules.length })}
    </div>
    ${abschnitte.join("")}
  `;
}

/** Ordnet die Regeln nach Geschoss, darin nach Raum, darin nach Entity. */
function gruppiere(rules, platzierung) {
  const baum = new Map();

  for (const regel of rules) {
    const ort = platzierung.get(regel.entity_id) || {};
    const geschoss = ort.floor_name || t("rules.noFloor");
    const raum = ort.area_name || t("rules.noArea");

    if (!baum.has(geschoss)) baum.set(geschoss, new Map());
    const raeume = baum.get(geschoss);

    if (!raeume.has(raum)) raeume.set(raum, new Map());
    const entities = raeume.get(raum);

    if (!entities.has(regel.entity_id)) entities.set(regel.entity_id, []);
    entities.get(regel.entity_id).push(regel);
  }

  // Aus der inneren Map je Raum eine sortierte Liste machen.
  for (const raeume of baum.values()) {
    for (const [raum, entities] of raeume.entries()) {
      raeume.set(raum, [...entities.entries()]);
    }
  }

  return baum;
}

function entityBlock([entityId, eintraege], platzierung) {
  const name = platzierung.get(entityId)?.name || entityId;

  // Kein eigener Bearbeiten-Knopf: jede Regelzeile hat bereits einen, und
  // zwei nebeneinander waren nur verwirrend.
  return `
    <div class="rule-entity">
      <div class="rule-entity-name">${escapeHtml(name)}</div>
      <ul>${eintraege.map((regel) => regelZeile(regel, entityId, name)).join("")}</ul>
    </div>
  `;
}

/**
 * Unsortierte Sammelgruppen ans Ende, sonst alphabetisch.
 *
 * Erkannt werden sie am uebersetzten Text selbst und nicht an einem
 * Wortanfang: im Englischen beginnt "No area" mit einem anderen Wort.
 */
function nachNamen([a], [b]) {
  const sammel = (wert) => (wert === t("rules.noFloor") || wert === t("rules.noArea") ? 1 : 0);
  return sammel(a) - sammel(b) || a.localeCompare(b);
}

export function renderRules(state) {
  const { entityId, entityName, rules = [], entwurf, states = [], attributes = [] } = state;

  return `
    <div class="filters">
      <button class="link" data-action="back-to-rules">${t("rules.backToAll")}</button>
    </div>

    <h2>${t("rules.forEntity", { name: escapeHtml(entityName || entityId) })}</h2>

    <!--
      Die Entity-ID gehoert auf diese Seite: von hier aus laesst sich die
      Entity ersetzen, und dafuer muss man wissen, welche gerade gemeint ist.
      Zurueckhaltend gesetzt -- sie ist Beleg, nicht Ueberschrift.
    -->
    <div class="entity-meta" style="margin: -8px 0 12px">${escapeHtml(entityId || "")}</div>

    ${
      rules.length
        ? `<ul>${rules
            .map((regel) => regelZeile(regel, entityId, entityName, entwurf?.rule_id))
            .join("")}</ul>`
        : `<div class="entity-meta" style="padding: 8px 0">${t("rules.none")}</div>`
    }

    ${
      entwurf
        ? formular(entwurf, states, attributes)
        : `<div class="footer-link">
             <button class="action" data-action="new-rule">${t("rules.create")}</button>
             <button class="action secondary" data-action="replace-entity"
                     data-entity="${escapeHtml(entityId)}">${t("rules.replaceEntity")}</button>
           </div>`
    }
  `;
}

/**
 * Eine Regel als Listenzeile.
 *
 * ``offeneRegel`` ist die Regel, deren Formular gerade unter der Liste steht.
 * Sie bekommt keinen Bearbeiten-Knopf: er wuerde auf das verweisen, was
 * ohnehin schon offen ist. Bei einer einzigen Regel war die Schaltflaeche
 * damit durchgehend sinnlos, bei mehreren fuehrt sie weiterhin von einer
 * Regel zur naechsten.
 */
function regelZeile(regel, entityId = regel.entity_id, entityName = "", offeneRegel = null) {
  // Entity und Name wandern mit: nur so kann der Editor auch aus der
  // Uebersicht heraus die richtigen Regeln laden.
  const ziel =
    `data-rule="${escapeHtml(regel.rule_id)}" ` +
    `data-entity="${escapeHtml(entityId || "")}" ` +
    `data-name="${escapeHtml(entityName)}"`;

  const wirdBearbeitet = Boolean(offeneRegel) && regel.rule_id === offeneRegel;

  return `
    <li class="row${wirdBearbeitet ? " editing" : ""}">
      <span class="bar ${regel.type}"></span>
      <span class="message">${escapeHtml(beschreibung(regel))}</span>
      ${regel.enabled === false ? `<span class="badge">${t("rules.disabled")}</span>` : ""}
      ${
        wirdBearbeitet
          ? `<span class="badge">${t("rules.editing")}</span>`
          : `<button class="link" data-action="edit-rule" ${ziel}>${t("common.edit")}</button>`
      }
      <button class="link" data-action="delete-rule" ${ziel}>${t("common.delete")}</button>
    </li>
  `;
}

/** Kurzbeschreibung einer Regel fuer die Liste. */
export function beschreibung(regel) {
  const quelle =
    regel.value_source?.kind === "attribute"
      ? `${regel.value_source.attribute}`
      : t("common.state");

  if (regel.kind === "numeric") {
    const operator = OPERATOREN.includes(regel.operator)
      ? t(`rules.operator.${regel.operator}`)
      : regel.operator;
    const hysterese =
      regel.release_threshold != null
        ? t("rules.describe.back", { value: regel.release_threshold })
        : "";
    return `${quelle} ${operator} ${regel.threshold}${hysterese}${dauerText(regel)}`;
  }

  const zustaende = (regel.states || []).join(t("rules.describe.or"));
  const einleitung =
    regel.kind === "state_changed_to"
      ? t("rules.describe.changesTo")
      : regel.kind === "state_is_not"
        ? t("rules.describe.isNot")
        : t("rules.describe.is");
  return `${quelle} ${einleitung} ${zustaende}${dauerText(regel)}`;
}

function dauerText(regel) {
  if (!regel.duration_seconds) return "";
  return t("rules.describe.longerThan", { minutes: Math.round(regel.duration_seconds / 60) });
}

function formular(entwurf, states, attributes) {
  const numerisch = entwurf.kind === "numeric";

  return `
    <div style="border-top: 1px solid var(--nc-border); margin-top: 16px; padding-top: 16px">
      <div class="filters">
        <select data-rule-field="kind" aria-label="${t("rules.condition")}">
          ${auswahl(BEDINGUNGEN, entwurf.kind, (wert) => t(`rules.kind.${wert}`))}
        </select>

        <select data-rule-field="source" aria-label="${t("rules.valueSource")}">
          <option value="">${t("common.state")}</option>
          ${attributes
            .map(
              (attribut) =>
                `<option value="${escapeHtml(attribut.name)}" ${
                  entwurf.value_source?.attribute === attribut.name ? "selected" : ""
                }>${escapeHtml(t("rules.attribute", { name: attribut.name }))}</option>`
            )
            .join("")}
        </select>

        <select data-rule-field="type" aria-label="${t("history.type")}">
          ${auswahl(TYPEN, entwurf.type, typeLabel)}
        </select>
      </div>

      <div class="filters">
        ${
          numerisch
            ? `<select data-rule-field="operator" aria-label="${t("rules.comparison")}">
                 ${auswahl(OPERATOREN, entwurf.operator, (wert) => t(`rules.operator.${wert}`))}
               </select>
               <input type="number" step="any" data-rule-field="threshold"
                      placeholder="${t("rules.threshold")}" aria-label="${t("rules.threshold")}"
                      value="${entwurf.threshold ?? ""}">`
            : zustandsauswahl(entwurf, states)
        }
      </div>

      <div class="filters">
        <input type="text" data-rule-field="message" style="flex: 1; min-width: 220px"
               placeholder="${escapeHtml(t("rules.messagePlaceholder"))}"
               aria-label="${t("rules.message")}"
               value="${escapeHtml(entwurf.message_template || "")}">
      </div>

      <details ${entwurf.release_threshold != null || entwurf.duration_seconds ? "open" : ""}>
        <summary>${t("rules.advanced")}</summary>
        <div class="filters" style="margin-top: 8px">
          ${
            numerisch
              ? `<input type="number" step="any" data-rule-field="release"
                        placeholder="${t("rules.releasePlaceholder")}"
                        aria-label="${t("rules.release")}"
                        value="${entwurf.release_threshold ?? ""}">`
              : ""
          }
          <input type="number" min="0" data-rule-field="duration"
                 placeholder="${t("rules.durationPlaceholder")}"
                 aria-label="${t("rules.duration")}"
                 value="${entwurf.duration_seconds ? Math.round(entwurf.duration_seconds / 60) : ""}">
        </div>
      </details>

      <div class="footer-link">
        <button class="action" data-action="save-rule">${t("common.save")}</button>
        <button class="action secondary" data-action="cancel-rule">${t("common.cancel")}</button>
      </div>
    </div>
  `;
}

function zustandsauswahl(entwurf, states) {
  if (!states.length) {
    return `<input type="text" data-rule-field="states"
                   placeholder="${t("rules.statePlaceholder")}" aria-label="${t("common.state")}"
                   value="${escapeHtml((entwurf.states || []).join(", "))}">`;
  }

  // Auswahlfeld statt Textfeld: die Werte stammen aus der Entity selbst.
  return `
    <select data-rule-field="states" aria-label="${t("common.state")}" multiple
            size="${Math.min(states.length, 4)}">
      ${states
        .map(
          (zustand) =>
            `<option value="${escapeHtml(zustand)}" ${
              (entwurf.states || []).includes(zustand) ? "selected" : ""
            }>${escapeHtml(zustand)}</option>`
        )
        .join("")}
    </select>
  `;
}

function auswahl(werte, aktiv, beschriftung) {
  return werte
    .map(
      (wert) =>
        `<option value="${wert}" ${aktiv === wert ? "selected" : ""}>${escapeHtml(
          beschriftung(wert)
        )}</option>`
    )
    .join("");
}

/** Uebersetzt den Formularzustand in das Format der Backend-API. */
export function entwurfZuRegel(entwurf) {
  const regel = {
    entity_id: entwurf.entity_id,
    kind: entwurf.kind,
    type: entwurf.type,
    message_template: entwurf.message_template || "",
    value_source: entwurf.value_source || { kind: "state", attribute: null },
    duration_seconds: entwurf.duration_seconds || null,
  };

  if (entwurf.rule_id) regel.rule_id = entwurf.rule_id;

  if (entwurf.kind === "numeric") {
    regel.operator = entwurf.operator;
    regel.threshold = Number(entwurf.threshold);
    regel.release_threshold =
      entwurf.release_threshold === null || entwurf.release_threshold === ""
        ? null
        : Number(entwurf.release_threshold);
    regel.states = [];
  } else {
    regel.states = entwurf.states || [];
    regel.operator = null;
    regel.threshold = null;
    regel.release_threshold = null;
  }

  return regel;
}
