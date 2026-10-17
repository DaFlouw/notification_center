/**
 * Regel-Editor einer ueberwachten Entity (Spezifikation 14 bis 18).
 *
 * Der einfache Teil steht oben, Hysterese und Zeitbedingung liegen im
 * erweiterten Bereich (Spezifikation 18). Zustandswerte kommen als Auswahl
 * aus der Entity, nicht als freies Textfeld (Spezifikation 14).
 *
 * Eine Regel kann mehrere Bedingungen verknuepfen. Die erste steht oben und
 * gilt immer fuer die Entity der Regel; jede weitere ist ein eigener Block
 * und darf eine andere Entity betrachten. Verknuepft wird entweder mit "alle"
 * oder mit "eine genuegt", je Bedingung zusaetzlich verneinbar -- mehr
 * Logik waere ohne Klammern nicht darstellbar.
 */

import { escapeHtml, typeLabel } from "../format.js";
import { t } from "../i18n.js";

const BEDINGUNGEN = ["state_is", "state_is_not", "state_changed_to", "numeric"];

const OPERATOREN = ["gt", "gte", "lt", "lte", "eq"];

const TYPEN = ["info", "warning", "alarm"];

const LOGIK = ["all", "any"];

/** Kennung der Entity-Liste des Formulars; im Shadow DOM eindeutig. */
const ENTITY_LISTE = "nc-entity-liste";

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
    logic: "all",
    extra_conditions: [],
  };
}

/**
 * Eine neue, leere Teilbedingung.
 *
 * ``entity_id`` bleibt leer: ohne Angabe gilt die Bedingung fuer die Entity
 * der Regel, und das ist der haeufigere Fall -- etwa ein zweites Attribut
 * derselben Entity.
 */
export function leereBedingung() {
  return {
    entity_id: "",
    kind: "state_is",
    states: [],
    operator: "gt",
    threshold: null,
    negate: false,
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
  const { entities = [], rules = [], loading, names = {} } = state;

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
              ${eintraege.map((paar) => entityBlock(paar, platzierung, names)).join("")}
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

function entityBlock([entityId, eintraege], platzierung, namen = {}) {
  const name = platzierung.get(entityId)?.name || entityId;

  // Kein eigener Bearbeiten-Knopf: jede Regelzeile hat bereits einen, und
  // zwei nebeneinander waren nur verwirrend.
  return `
    <div class="rule-entity">
      <div class="rule-entity-name">${escapeHtml(name)}</div>
      <ul>${eintraege
        .map((regel) => regelZeile(regel, entityId, name, null, namen))
        .join("")}</ul>
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
  const {
    entityId,
    entityName,
    rules = [],
    entwurf,
    states = [],
    attributes = [],
    names = {},
    candidates = [],
    conditionOptions = {},
  } = state;

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
            .map((regel) => regelZeile(regel, entityId, entityName, entwurf?.rule_id, names))
            .join("")}</ul>`
        : `<div class="entity-meta" style="padding: 8px 0">${t("rules.none")}</div>`
    }

    ${
      entwurf
        ? formular(entwurf, states, attributes, candidates, conditionOptions)
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
function regelZeile(
  regel,
  entityId = regel.entity_id,
  entityName = "",
  offeneRegel = null,
  namen = {}
) {
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
      <span class="message">${escapeHtml(beschreibung(regel, namen))}</span>
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

/**
 * Kurzbeschreibung einer Regel fuer die Liste.
 *
 * ``namen`` ordnet Entity-Kennungen Anzeigenamen zu. Gebraucht wird das nur
 * fuer Teilbedingungen, die eine andere Entity betrachten: ohne Namen stuende
 * dort eine nackte Kennung, und die sagt beim Querlesen wenig. Fehlt der
 * Name, bleibt die Kennung -- besser als nichts.
 */
export function beschreibung(regel, namen = {}) {
  // Ohne Kennung: die erste Bedingung gehoert immer der Entity der Regel, und
  // die steht in der Uebersicht schon als Ueberschrift darueber.
  const teile = [bedingungText({ ...regel, entity_id: null })];
  for (const bedingung of regel.extra_conditions || []) {
    teile.push(bedingungText(bedingung, namen));
  }

  const trenner = regel.logic === "any" ? t("rules.logic.any") : t("rules.logic.all");
  return `${teile.join(trenner)}${dauerText(regel)}`;
}

/**
 * Eine einzelne Bedingung als Text.
 *
 * Nimmt die Regel selbst oder eine Teilbedingung: beide tragen dieselben
 * Felder, die Regel traegt ihre erste Bedingung direkt.
 */
function bedingungText(bedingung, namen = {}) {
  const quelle =
    bedingung.value_source?.kind === "attribute"
      ? `${bedingung.value_source.attribute}`
      : t("common.state");

  let text;
  if (bedingung.kind === "numeric") {
    const operator = OPERATOREN.includes(bedingung.operator)
      ? t(`rules.operator.${bedingung.operator}`)
      : bedingung.operator;
    const hysterese =
      bedingung.release_threshold != null
        ? t("rules.describe.back", { value: bedingung.release_threshold })
        : "";
    text = `${quelle} ${operator} ${bedingung.threshold}${hysterese}`;
  } else {
    const zustaende = (bedingung.states || []).join(t("rules.describe.or"));
    const einleitung =
      bedingung.kind === "state_changed_to"
        ? t("rules.describe.changesTo")
        : bedingung.kind === "state_is_not"
          ? t("rules.describe.isNot")
          : t("rules.describe.is");
    text = `${quelle} ${einleitung} ${zustaende}`;
  }

  // Die Klammer ist noetig: "nicht Zustand ist on" waere mehrdeutig, verneint
  // ist die ganze Bedingung.
  if (bedingung.negate) text = `${t("rules.describe.not")}(${text})`;

  const ort = bedingung.entity_id ? `${namen[bedingung.entity_id] || bedingung.entity_id}: ` : "";
  return `${ort}${text}`;
}

function dauerText(regel) {
  if (!regel.duration_seconds) return "";
  return t("rules.describe.longerThan", { minutes: Math.round(regel.duration_seconds / 60) });
}

function formular(entwurf, states, attributes, kandidaten = [], bedingungsOptionen = {}) {
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
            : zustandsauswahl(entwurf, states, attributes)
        }
      </div>

      ${numerisch ? "" : wertHinweis(entwurf, attributes)}

      ${bedingungsBlock(entwurf, kandidaten, {
        "": { states, attributes, exists: true },
        ...bedingungsOptionen,
      })}

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

/**
 * Das Feld fuer den Zielwert.
 *
 * Die Auswahlliste gilt nur fuer den Zustand der Entity. Ist ein Attribut
 * die Wertquelle, passt sie nicht: ihre Werte gehoeren zu einer anderen
 * Groesse. Genau daran scheiterte eine Regel auf ein Attribut ``state``,
 * dessen Werte gross geschrieben sind, waehrend die Liste die klein
 * geschriebenen Zustaende der Entity anbot (Issue 14). Welche Werte ein
 * Attribut annehmen kann, weiss das Backend nicht -- deshalb ein Textfeld.
 */
function zustandsauswahl(entwurf, states, attributes = []) {
  if (attributname(entwurf)) {
    return `<input type="text" data-rule-field="states"
                   placeholder="${escapeHtml(attributVorgabe(entwurf, attributes))}"
                   aria-label="${t("common.state")}"
                   value="${escapeHtml((entwurf.states || []).join(", "))}">`;
  }

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

/** Der Name des Attributs, das als Wertquelle dient -- sonst ``null``. */
function attributname(entwurf) {
  return entwurf.value_source?.kind === "attribute" ? entwurf.value_source.attribute : null;
}

/** Der aktuelle Wert des gewaehlten Attributs, als Text. */
function attributWert(entwurf, attributes) {
  const name = attributname(entwurf);
  if (!name) return null;
  const attribut = (attributes || []).find((eintrag) => eintrag.name === name);
  return attribut && attribut.value != null ? String(attribut.value) : null;
}

function attributVorgabe(entwurf, attributes) {
  return attributWert(entwurf, attributes) ?? t("rules.statePlaceholder");
}

/**
 * Hilfe unter dem Feld: der aktuelle Wert, und eine Warnung, wenn der
 * eingetragene sich davon nur in der Gross- und Kleinschreibung
 * unterscheidet.
 *
 * Der Vergleich im Backend bleibt zeichengenau -- Zustaende sind in Home
 * Assistant gross- und kleinschreibungsempfindlich. Eine stillschweigend
 * unscharfe Regel waere schlechter als eine, die man sieht.
 */
function wertHinweis(entwurf, attributes) {
  const aktuell = attributWert(entwurf, attributes);
  if (aktuell === null) return "";

  const eingetragen = (entwurf.states || []).map((wert) => String(wert).trim()).filter(Boolean);
  const schreibweise = eingetragen.some(
    (wert) => wert !== aktuell && wert.toLowerCase() === aktuell.toLowerCase()
  );

  return `
    <div class="entity-meta" style="margin: -4px 0 8px">
      ${escapeHtml(t("rules.currentValue", { value: aktuell }))}
      ${
        schreibweise
          ? `<span class="badge uncertain">${escapeHtml(
              t("rules.caseMismatch", { value: aktuell })
            )}</span>`
          : ""
      }
    </div>
  `;
}


/**
 * Die weiteren Bedingungen samt Verknuepfung.
 *
 * Die Auswahl der Verknuepfung erscheint erst, wenn es etwas zu verknuepfen
 * gibt: bei einer einzigen Bedingung waere sie eine Frage ohne Gegenstand.
 */
function bedingungsBlock(entwurf, kandidaten, optionen) {
  const extras = entwurf.extra_conditions || [];

  return `
    <div style="margin-top: 12px">
      ${
        extras.length
          ? `<div class="filters">
               <select data-rule-field="logic" aria-label="${t("rules.logicLabel")}">
                 ${auswahl(LOGIK, entwurf.logic || "all", (wert) =>
                   wert === "any" ? t("rules.logicAny") : t("rules.logicAll")
                 )}
               </select>
             </div>`
          : ""
      }

      ${extras
        .map((bedingung, index) => bedingungsZeile(bedingung, index, kandidaten, optionen))
        .join("")}

      <div class="filters">
        <button class="link" data-action="add-condition">+ ${t("rules.addCondition")}</button>
      </div>

      ${entityListe(kandidaten)}
    </div>
  `;
}

/**
 * Eine weitere Bedingung.
 *
 * Das Entity-Feld ist ein Textfeld mit Vorschlagsliste und nicht ein
 * Auswahlfeld: eine Anlage hat leicht tausend Entities, und eine Liste dieser
 * Laenge laesst sich nicht bedienen. Leer bedeutet "diese Entity".
 */
function bedingungsZeile(bedingung, index, kandidaten, optionen) {
  const numerisch = bedingung.kind === "numeric";
  // Die leere Kennung steht fuer die Entity der Regel; ihre Werte liegen
  // unter demselben Schluessel in der Mappe.
  const info = optionen[bedingung.entity_id || ""] || {};
  const attribute = info.attributes || [];
  const zustaende = info.states || [];
  const feld = `data-cond-field`;
  const nr = `data-cond-index="${index}"`;

  return `
    <div class="condition">
      <div class="filters">
        <input type="text" list="${ENTITY_LISTE}" ${feld}="entity" ${nr}
               placeholder="${t("rules.thisEntity")}"
               aria-label="${t("rules.conditionEntity")}"
               value="${escapeHtml(bedingung.entity_id || "")}">

        <select ${feld}="kind" ${nr} aria-label="${t("rules.condition")}">
          ${auswahl(BEDINGUNGEN, bedingung.kind, (wert) => t(`rules.kind.${wert}`))}
        </select>

        <select ${feld}="source" ${nr} aria-label="${t("rules.valueSource")}">
          <option value="">${t("common.state")}</option>
          ${attribute
            .map(
              (attribut) =>
                `<option value="${escapeHtml(attribut.name)}" ${
                  bedingung.value_source?.attribute === attribut.name ? "selected" : ""
                }>${escapeHtml(t("rules.attribute", { name: attribut.name }))}</option>`
            )
            .join("")}
        </select>
      </div>

      <div class="filters">
        ${
          numerisch
            ? `<select ${feld}="operator" ${nr} aria-label="${t("rules.comparison")}">
                 ${auswahl(OPERATOREN, bedingung.operator, (wert) => t(`rules.operator.${wert}`))}
               </select>
               <input type="number" step="any" ${feld}="threshold" ${nr}
                      placeholder="${t("rules.threshold")}" aria-label="${t("rules.threshold")}"
                      value="${bedingung.threshold ?? ""}">`
            : zustandsfeld(bedingung, zustaende, `${feld}="states" ${nr}`)
        }

        ${
          bedingung.kind === "state_changed_to"
            ? ""
            : `<label class="negate">
                 <input type="checkbox" ${feld}="negate" ${nr}
                        ${bedingung.negate ? "checked" : ""}>
                 ${t("rules.negate")}
               </label>`
        }

        <button class="link" data-action="remove-condition" data-index="${index}">
          ${t("rules.removeCondition")}
        </button>
      </div>

      ${
        bedingung.entity_id && info.exists === false
          ? `<div class="entity-meta">${t("rules.entityUnknown")}</div>`
          : ""
      }
    </div>
  `;
}

/** Die Vorschlagsliste der Entities, einmal je Formular. */
function entityListe(kandidaten) {
  if (!kandidaten.length) return "";
  return `
    <datalist id="${ENTITY_LISTE}">
      ${kandidaten
        .map(
          (eintrag) =>
            `<option value="${escapeHtml(eintrag.entity_id)}">${escapeHtml(
              eintrag.name || eintrag.entity_id
            )}</option>`
        )
        .join("")}
    </datalist>
  `;
}

/**
 * Das Wertfeld einer Teilbedingung.
 *
 * Wie bei der ersten Bedingung: Auswahl, solange die Werte aus der Entity
 * selbst stammen, sonst ein Textfeld (siehe ``zustandsauswahl``).
 */
function zustandsfeld(bedingung, zustaende, attribute) {
  const wert = escapeHtml((bedingung.states || []).join(", "));

  if (bedingung.value_source?.kind === "attribute" || !zustaende.length) {
    return `<input type="text" ${attribute}
                   placeholder="${t("rules.statePlaceholder")}"
                   aria-label="${t("common.state")}" value="${wert}">`;
  }

  return `
    <select ${attribute} aria-label="${t("common.state")}" multiple
            size="${Math.min(zustaende.length, 4)}">
      ${zustaende
        .map(
          (zustand) =>
            `<option value="${escapeHtml(zustand)}" ${
              (bedingung.states || []).includes(zustand) ? "selected" : ""
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
    logic: entwurf.logic === "any" ? "any" : "all",
    extra_conditions: (entwurf.extra_conditions || []).map(bedingungZuApi),
  };

  if (entwurf.rule_id) regel.rule_id = entwurf.rule_id;

  Object.assign(regel, wertfelder(entwurf));
  return regel;
}

/**
 * Die Wertfelder einer Bedingung, passend zu ihrer Art.
 *
 * Die jeweils andere Haelfte wird ausdruecklich geleert: das Backend weist
 * eine Zustandsregel mit Schwelle zurueck, und ein Rest aus einem vorherigen
 * Formularzustand wuerde die Speicherung ohne erkennbaren Grund scheitern
 * lassen.
 */
function wertfelder(bedingung) {
  if (bedingung.kind === "numeric") {
    return {
      operator: bedingung.operator,
      threshold: Number(bedingung.threshold),
      release_threshold:
        bedingung.release_threshold === null ||
        bedingung.release_threshold === undefined ||
        bedingung.release_threshold === ""
          ? null
          : Number(bedingung.release_threshold),
      states: [],
    };
  }

  return {
    states: bedingung.states || [],
    operator: null,
    threshold: null,
    release_threshold: null,
  };
}

/** Eine Teilbedingung fuer die API. Leere Kennung heisst "diese Entity". */
function bedingungZuApi(bedingung) {
  return {
    entity_id: (bedingung.entity_id || "").trim() || null,
    kind: bedingung.kind,
    value_source: bedingung.value_source || { kind: "state", attribute: null },
    // Eine Flanke laesst sich nicht verneinen; das Backend weist es ab.
    negate: bedingung.kind === "state_changed_to" ? false : Boolean(bedingung.negate),
    ...wertfelder(bedingung),
  };
}
