/**
 * Regel-Editor einer ueberwachten Entity (Spezifikation 14 bis 18).
 *
 * Der einfache Teil steht oben, Hysterese und Zeitbedingung liegen im
 * erweiterten Bereich (Spezifikation 18). Zustandswerte kommen als Auswahl
 * aus der Entity, nicht als freies Textfeld (Spezifikation 14).
 */

import { escapeHtml } from "../format.js";

const BEDINGUNGEN = [
  { wert: "state_is", text: "Zustand ist" },
  { wert: "state_is_not", text: "Zustand ist nicht" },
  { wert: "state_changed_to", text: "Zustand ändert sich zu" },
  { wert: "numeric", text: "Wert überschreitet oder unterschreitet" },
];

const OPERATOREN = [
  { wert: "gt", text: "größer als" },
  { wert: "gte", text: "größer oder gleich" },
  { wert: "lt", text: "kleiner als" },
  { wert: "lte", text: "kleiner oder gleich" },
  { wert: "eq", text: "gleich" },
];

const TYPEN = [
  { wert: "info", text: "Info" },
  { wert: "warning", text: "Warnung" },
  { wert: "alarm", text: "Alarm" },
];

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

  if (loading) return '<div class="loading">Wird geladen …</div>';

  if (!rules.length) {
    return `
      <div class="empty">
        <strong>Noch keine Regeln</strong>
        <span>
          Unter <button class="link" data-nav="discovery">Discovery</button>
          eine Entity übernehmen und ihr eine Regel geben.
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
      ${rules.length} ${rules.length === 1 ? "Regel" : "Regeln"}
    </div>
    ${abschnitte.join("")}
  `;
}

/** Ordnet die Regeln nach Geschoss, darin nach Raum, darin nach Entity. */
function gruppiere(rules, platzierung) {
  const baum = new Map();

  for (const regel of rules) {
    const ort = platzierung.get(regel.entity_id) || {};
    const geschoss = ort.floor_name || "Ohne Geschoss";
    const raum = ort.area_name || "Ohne Raum";

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

/** Unsortierte Sammelgruppen ans Ende, sonst alphabetisch. */
function nachNamen([a], [b]) {
  const sammel = (wert) => (wert.startsWith("Ohne ") ? 1 : 0);
  return sammel(a) - sammel(b) || a.localeCompare(b);
}

export function renderRules(state) {
  const { entityId, entityName, rules = [], entwurf, states = [], attributes = [] } = state;

  return `
    <div class="filters">
      <button class="link" data-action="back-to-rules">← Alle Regeln</button>
    </div>

    <h2>Regeln für ${escapeHtml(entityName || entityId)}</h2>

    ${
      rules.length
        ? `<ul>${rules
            .map((regel) => regelZeile(regel, entityId, entityName, entwurf?.rule_id))
            .join("")}</ul>`
        : '<div class="entity-meta" style="padding: 8px 0">Noch keine Regeln.</div>'
    }

    ${
      entwurf
        ? formular(entwurf, states, attributes)
        : `<div class="footer-link">
             <button class="action" data-action="new-rule">Regel erstellen</button>
             <button class="action secondary" data-action="replace-entity"
                     data-entity="${escapeHtml(entityId)}">Entity ersetzen</button>
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
      ${regel.enabled === false ? '<span class="badge">deaktiviert</span>' : ""}
      ${
        wirdBearbeitet
          ? '<span class="badge">wird bearbeitet</span>'
          : `<button class="link" data-action="edit-rule" ${ziel}>Bearbeiten</button>`
      }
      <button class="link" data-action="delete-rule" ${ziel}>Löschen</button>
    </li>
  `;
}

/** Kurzbeschreibung einer Regel fuer die Liste. */
export function beschreibung(regel) {
  const quelle =
    regel.value_source?.kind === "attribute" ? `${regel.value_source.attribute}` : "Zustand";

  if (regel.kind === "numeric") {
    const operator = OPERATOREN.find((o) => o.wert === regel.operator)?.text || regel.operator;
    const hysterese =
      regel.release_threshold != null ? `, zurück bei ${regel.release_threshold}` : "";
    return `${quelle} ${operator} ${regel.threshold}${hysterese}${dauerText(regel)}`;
  }

  const zustaende = (regel.states || []).join(" oder ");
  const einleitung =
    regel.kind === "state_changed_to"
      ? "wechselt zu"
      : regel.kind === "state_is_not"
        ? "ist nicht"
        : "ist";
  return `${quelle} ${einleitung} ${zustaende}${dauerText(regel)}`;
}

function dauerText(regel) {
  if (!regel.duration_seconds) return "";
  return ` · länger als ${Math.round(regel.duration_seconds / 60)} min`;
}

function formular(entwurf, states, attributes) {
  const numerisch = entwurf.kind === "numeric";

  return `
    <div style="border-top: 1px solid var(--nc-border); margin-top: 16px; padding-top: 16px">
      <div class="filters">
        <select data-rule-field="kind" aria-label="Bedingung">
          ${auswahl(BEDINGUNGEN, entwurf.kind)}
        </select>

        <select data-rule-field="source" aria-label="Wertquelle">
          <option value="">Zustand</option>
          ${attributes
            .map(
              (attribut) =>
                `<option value="${escapeHtml(attribut.name)}" ${
                  entwurf.value_source?.attribute === attribut.name ? "selected" : ""
                }>Attribut: ${escapeHtml(attribut.name)}</option>`
            )
            .join("")}
        </select>

        <select data-rule-field="type" aria-label="Typ">
          ${auswahl(TYPEN, entwurf.type)}
        </select>
      </div>

      <div class="filters">
        ${
          numerisch
            ? `<select data-rule-field="operator" aria-label="Vergleich">
                 ${auswahl(OPERATOREN, entwurf.operator)}
               </select>
               <input type="number" step="any" data-rule-field="threshold"
                      placeholder="Schwelle" aria-label="Schwelle"
                      value="${entwurf.threshold ?? ""}">`
            : zustandsauswahl(entwurf, states)
        }
      </div>

      <div class="filters">
        <input type="text" data-rule-field="message" style="flex: 1; min-width: 220px"
               placeholder="Meldungstext, z. B. {name} zu warm ({value} {unit})"
               aria-label="Meldungstext"
               value="${escapeHtml(entwurf.message_template || "")}">
      </div>

      <details ${entwurf.release_threshold != null || entwurf.duration_seconds ? "open" : ""}>
        <summary>Erweitert</summary>
        <div class="filters" style="margin-top: 8px">
          ${
            numerisch
              ? `<input type="number" step="any" data-rule-field="release"
                        placeholder="Rückkehrschwelle (Hysterese)"
                        aria-label="Rückkehrschwelle"
                        value="${entwurf.release_threshold ?? ""}">`
              : ""
          }
          <input type="number" min="0" data-rule-field="duration"
                 placeholder="Erst nach … Minuten" aria-label="Zeitbedingung in Minuten"
                 value="${entwurf.duration_seconds ? Math.round(entwurf.duration_seconds / 60) : ""}">
        </div>
      </details>

      <div class="footer-link">
        <button class="action" data-action="save-rule">Speichern</button>
        <button class="action secondary" data-action="cancel-rule">Abbrechen</button>
      </div>
    </div>
  `;
}

function zustandsauswahl(entwurf, states) {
  if (!states.length) {
    return `<input type="text" data-rule-field="states" placeholder="Zustand"
                   aria-label="Zustand" value="${escapeHtml((entwurf.states || []).join(", "))}">`;
  }

  // Auswahlfeld statt Textfeld: die Werte stammen aus der Entity selbst.
  return `
    <select data-rule-field="states" aria-label="Zustand" multiple size="${Math.min(states.length, 4)}">
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

function auswahl(optionen, aktiv) {
  return optionen
    .map(
      (option) =>
        `<option value="${option.wert}" ${aktiv === option.wert ? "selected" : ""}>${option.text}</option>`
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
