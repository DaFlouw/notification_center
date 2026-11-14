/**
 * Der Regel-Editor (Spezifikation 14 bis 18).
 *
 * Gebaut wie ein Satz und nicht wie ein Formular: *wann* soll gemeldet
 * werden, *wie lange* muss es anhalten, *was* soll erscheinen. Oben steht die
 * Regel noch einmal als Ablauf -- Bedingungen, Wartezeit, Meldung -- und zu
 * jeder Bedingung der Wert, den die Entity in diesem Augenblick hat. So sieht
 * man beim Bauen, ob die Regel greifen wuerde, statt es nach dem Speichern
 * herauszufinden.
 *
 * Die Zustaende erscheinen so, wie Home Assistant sie dem Anwender zeigt
 * ("offen" statt ``on``). Gespeichert wird weiterhin der rohe Wert: nur er ist
 * von der Sprache unabhaengig.
 */

import { escapeHtml, typeLabel } from "../format.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";

const ARTEN = ["state_is", "state_is_not", "state_changed_to", "numeric"];
const OPERATOREN = ["gt", "gte", "lt", "lte", "eq"];
const TYPEN = ["info", "warning", "alarm"];
const PLATZHALTER = ["name", "state", "value", "unit"];

/** Die Wartezeiten der Schnellwahl, in Minuten. Null heisst sofort. */
export const WARTEZEITEN = [0, 1, 5, 15, 60];

/** Kennung der Entity-Liste des Formulars; im Shadow DOM eindeutig. */
const ENTITY_LISTE = "nc-entity-liste";

export function renderEditor(state) {
  const {
    entityId,
    entityName,
    entwurf,
    states = [],
    attributes = [],
    candidates = [],
    conditionOptions = {},
    names = {},
    current = {},
    labels = {},
  } = state;

  const name = entityName || entityId;
  const umfeld = {
    entityId,
    name,
    names,
    current,
    labels,
    // Die leere Kennung steht fuer die Entity der Regel.
    optionen: { "": { states, attributes, exists: true }, ...conditionOptions },
  };

  return `
    <div class="editor-head">
      <div>
        <button class="link" data-action="back-to-rules">${t("rules.backToAll")}</button>
        <h2>${t("editor.title", { name })}</h2>
        <div class="mono">${escapeHtml(entityId || "")}</div>
      </div>
      <div class="footer-link">
        <button class="action secondary" data-action="cancel-rule">${t("common.cancel")}</button>
        <button class="action" data-action="save-rule">${t("common.save")}</button>
      </div>
    </div>

    ${ablauf(entwurf, umfeld)}

    <section class="card pad">
      ${schritt(1, t("editor.stepWhen"))}
      ${bedingungsKarte(entwurf, null, umfeld)}
      ${weitereBedingungen(entwurf, umfeld)}
      ${entityListe(candidates)}
    </section>

    <section class="card pad">
      ${schritt(2, t("editor.stepHowLong"))}
      ${wartezeit(entwurf)}
    </section>

    <section class="card pad">
      ${schritt(3, t("editor.stepWhat"))}
      ${meldung(entwurf)}
    </section>

    <div class="editor-foot">
      ${
        entwurf.rule_id
          ? `<button class="btn ghost danger" data-action="delete-rule"
                     data-rule="${escapeHtml(entwurf.rule_id)}"
                     data-entity="${escapeHtml(entityId || "")}">${t("editor.deleteRule")}</button>`
          : "<span></span>"
      }
      <div class="footer-link">
        <button class="action secondary" data-action="cancel-rule">${t("common.cancel")}</button>
        <button class="action" data-action="save-rule">${t("common.save")}</button>
      </div>
    </div>
  `;
}

function schritt(nummer, titel) {
  return `<div class="step"><span class="step-no">${nummer}</span><h3>${titel}</h3></div>`;
}

// ---------------------------------------------------------------------------
// Der Ablauf: die Regel als Bild
// ---------------------------------------------------------------------------

/**
 * Bedingungen, Wartezeit und Meldung nebeneinander, von links nach rechts.
 *
 * Kein Diagramm um seiner selbst willen: es ist dieselbe Regel, die darunter
 * gebaut wird, nur in der Reihenfolge, in der sie arbeitet. Jede Bedingung
 * traegt einen Punkt -- gruen, wenn sie gerade zutrifft -- und den Wert, den
 * ihre Entity in diesem Augenblick hat.
 */
function ablauf(entwurf, umfeld) {
  const bedingungen = [{ ...entwurf, entity_id: "" }, ...(entwurf.extra_conditions || [])];
  const wort = entwurf.logic === "any" ? t("rules.logicWord.any") : t("rules.logicWord.all");
  const urteile = bedingungen.map((bedingung) => trifftZu(bedingung, umfeld));

  const zeilen = bedingungen
    .map((bedingung, stelle) => {
      const urteil = urteile[stelle];
      const vorsatz =
        stelle === 0
          ? ""
          : `<div class="flow-join"><span class="logic">${escapeHtml(
              bedingung.negate ? `${wort} ${t("rules.logicWord.not")}` : wort
            )}</span></div>`;
      const jetzt = aktuellerWert(bedingung, umfeld);
      return `
        ${vorsatz}
        <div class="flow-cond">
          <span class="dot ${urteil === true ? "met" : ""}"></span>
          <span class="row-body">
            <span class="entity-name">${escapeHtml(satz(bedingung, umfeld))}</span>
            ${
              jetzt === null
                ? ""
                : `<span class="row-sub${urteil === true ? " met" : ""}">${escapeHtml(
                    t("editor.now", { value: jetzt })
                  )}</span>`
            }
          </span>
        </div>
      `;
    })
    .join("");

  const minuten = entwurf.duration_seconds ? Math.round(entwurf.duration_seconds / 60) : 0;

  return `
    <section class="card pad" aria-label="${t("editor.flowTitle")}">
      <div class="flow-head">
        <h3>${t("editor.flowTitle")}</h3>
        <span class="row-sub">${escapeHtml(gesamturteil(entwurf, urteile))}</span>
      </div>
      <div class="flow">
        <div class="flow-box flow-conds">${zeilen}</div>
        ${
          minuten
            ? `<span class="flow-arrow">${icon("arrow", 28)}</span>
               <div class="flow-box flow-wait">
                 ${icon("timer", 26)}
                 <strong>${escapeHtml(t("editor.flowWait", { minutes: minuten }))}</strong>
                 <span class="row-sub">${t("editor.flowWaitHint")}</span>
               </div>`
            : ""
        }
        <span class="flow-arrow">${icon("arrow", 28)}</span>
        <div class="flow-box flow-result ${entwurf.type}">
          <div class="chips">
            <span class="icon-chip ${entwurf.type}">${icon(entwurf.type)}</span>
            <strong>${escapeHtml(typeLabel(entwurf.type))}</strong>
          </div>
          <span class="entity-name">${escapeHtml(
            entwurf.message_template || t("editor.flowNoText")
          )}</span>
          <span class="row-sub">${t("editor.flowEnds")}</span>
        </div>
      </div>
    </section>
  `;
}

/** Eine Bedingung als Satz: "Kuechenfenster ist offen". */
function satz(bedingung, umfeld) {
  const kennung = bedingung.entity_id || "";
  const wer = kennung ? umfeld.names[kennung] || kennung : umfeld.name;
  const attribut =
    bedingung.value_source?.kind === "attribute" ? ` · ${bedingung.value_source.attribute}` : "";

  if (bedingung.kind === "numeric") {
    const operator = OPERATOREN.includes(bedingung.operator)
      ? t(`rules.operator.${bedingung.operator}`)
      : "";
    const schwelle = bedingung.threshold ?? "…";
    return `${wer}${attribut} ${operator} ${schwelle}`;
  }

  const verb =
    bedingung.kind === "state_changed_to"
      ? t("rules.describe.changesTo")
      : bedingung.kind === "state_is_not"
        ? t("rules.describe.isNot")
        : t("rules.describe.is");
  const werte = (bedingung.states || []).map((wert) =>
    attribut ? wert : zustandsName(kennung, wert, umfeld)
  );
  return `${wer}${attribut} ${verb} ${werte.length ? werte.join(t("rules.describe.or")) : "…"}`;
}

/** Der Zustand, wie Home Assistant ihn dem Anwender zeigt. */
function zustandsName(kennung, wert, umfeld) {
  const eigene = umfeld.labels[kennung || umfeld.entityId] || {};
  return eigene[wert] ?? wert;
}

/** Der Rohwert, den eine Bedingung gerade betrachtet; ``null`` wenn unbekannt. */
function rohwert(bedingung, umfeld) {
  const stand = umfeld.current[bedingung.entity_id || umfeld.entityId];
  if (!stand) return null;
  if (bedingung.value_source?.kind === "attribute") {
    const wert = stand.attributes?.[bedingung.value_source.attribute];
    return wert === undefined || wert === null ? null : String(wert);
  }
  return stand.state ?? null;
}

function aktuellerWert(bedingung, umfeld) {
  const wert = rohwert(bedingung, umfeld);
  if (wert === null) return null;
  return bedingung.value_source?.kind === "attribute"
    ? wert
    : zustandsName(bedingung.entity_id || "", wert, umfeld);
}

/**
 * Ob eine Bedingung in diesem Augenblick zutrifft.
 *
 * Nur zur Anzeige. Die Entscheidung faellt im Backend; hier steht dieselbe
 * Regel noch einmal in klein, damit der Editor beim Bauen Auskunft geben
 * kann. ``null`` heisst: nicht entscheidbar -- Entity unbekannt, Wert nicht
 * verfuegbar, oder ein Wechsel, der nur im Augenblick des Wechsels gilt.
 */
export function trifftZu(bedingung, umfeld) {
  const wert = rohwert(bedingung, umfeld);
  if (wert === null || ["unknown", "unavailable", ""].includes(wert.toLowerCase())) return null;

  let ergebnis;
  if (bedingung.kind === "numeric") {
    const zahl = Number(String(wert).replace(",", "."));
    const schwelle = Number(bedingung.threshold);
    if (!Number.isFinite(zahl) || bedingung.threshold === null || bedingung.threshold === "" || !Number.isFinite(schwelle)) {
      return null;
    }
    ergebnis = { gt: zahl > schwelle, gte: zahl >= schwelle, lt: zahl < schwelle, lte: zahl <= schwelle, eq: zahl === schwelle }[bedingung.operator];
    if (ergebnis === undefined) return null;
  } else if (bedingung.kind === "state_changed_to") {
    return null;
  } else {
    if (!(bedingung.states || []).length) return null;
    const drin = bedingung.states.includes(wert);
    ergebnis = bedingung.kind === "state_is_not" ? !drin : drin;
  }

  return bedingung.negate ? !ergebnis : ergebnis;
}

function gesamturteil(entwurf, urteile) {
  if (urteile.some((urteil) => urteil === null)) return t("editor.statusUnknown");
  const erfuellt = entwurf.logic === "any" ? urteile.some(Boolean) : urteile.every(Boolean);
  return erfuellt ? t("editor.statusMet") : t("editor.statusNotMet");
}

// ---------------------------------------------------------------------------
// Schritt 1: die Bedingungen
// ---------------------------------------------------------------------------

/**
 * Eine Bedingung als Karte. ``index`` ist ``null`` fuer die erste Bedingung,
 * die immer der Entity der Regel gilt, sonst die Stelle in den weiteren.
 */
function bedingungsKarte(bedingung, index, umfeld) {
  const erste = index === null;
  const kennung = erste ? "" : bedingung.entity_id || "";
  const info = umfeld.optionen[kennung] || {};
  const feld = erste ? "data-rule-field" : "data-cond-field";
  const nr = erste ? "" : `data-cond-index="${index}"`;
  const stelle = erste ? "" : `data-index="${index}"`;
  const wort = umfeld.logikWort;

  return `
    <div class="cond-card${erste ? "" : " extra"}">
      <div class="filters">
        ${
          erste
            ? `<strong>${escapeHtml(umfeld.name)}</strong>`
            : `<span class="logic">${escapeHtml(wort)}</span>
               <input type="text" list="${ENTITY_LISTE}" ${feld}="entity" ${nr}
                      placeholder="${t("rules.thisEntity")}"
                      aria-label="${t("rules.conditionEntity")}"
                      value="${escapeHtml(bedingung.entity_id || "")}">`
        }

        <div class="segmented" role="group" aria-label="${t("rules.comparison")}">
          ${ARTEN.map(
            (art) =>
              `<button data-action="set-kind" data-value="${art}" ${stelle}
                       aria-pressed="${bedingung.kind === art}">${t(`editor.kind.${art}`)}</button>`
          ).join("")}
        </div>

        ${wertfeld(bedingung, info, umfeld, kennung, feld, nr, stelle)}

        ${
          erste
            ? ""
            : `<span class="spacer"></span>
               <button class="icon-btn" data-action="remove-condition" data-index="${index}"
                       title="${t("rules.removeCondition")}"
                       aria-label="${t("rules.removeCondition")}">${icon("close", 18)}</button>`
        }
      </div>

      ${
        !erste && kennung && umfeld.names[kennung]
          ? `<div class="row-sub">${escapeHtml(umfeld.names[kennung])}</div>`
          : ""
      }
      ${
        !erste && kennung && info.exists === false
          ? `<div class="row-sub">${t("rules.entityUnknown")}</div>`
          : ""
      }

      <div class="filters small">
        ${
          (info.attributes || []).length
            ? `<label class="inline">${t("editor.looksAt")}
                 <select ${feld}="source" ${nr} aria-label="${t("rules.valueSource")}">
                   <option value="">${t("common.state")}</option>
                   ${(info.attributes || [])
                     .map(
                       (attribut) =>
                         `<option value="${escapeHtml(attribut.name)}" ${
                           bedingung.value_source?.attribute === attribut.name ? "selected" : ""
                         }>${escapeHtml(t("rules.attribute", { name: attribut.name }))}</option>`
                     )
                     .join("")}
                 </select>
               </label>`
            : ""
        }
        ${
          bedingung.kind === "numeric" && erste
            ? `<label class="inline">${t("editor.release")}
                 <input type="number" step="any" ${feld}="release"
                        aria-label="${t("rules.release")}"
                        value="${bedingung.release_threshold ?? ""}">
               </label>`
            : ""
        }
        ${
          // Die Verneinung eines Zahlenvergleichs laesst sich nicht als
          // "ist nicht" schreiben; nur dort bleibt sie als eigener Schalter.
          !erste && bedingung.kind === "numeric"
            ? `<label class="negate">
                 <input type="checkbox" ${feld}="negate" ${nr} ${bedingung.negate ? "checked" : ""}>
                 ${t("rules.negate")}
               </label>`
            : ""
        }
      </div>

      ${wertHinweis(bedingung, info)}
    </div>
  `;
}

/**
 * Das Feld fuer den Zielwert.
 *
 * Zustaende, die die Entity selbst kennt, stehen als Schalter da: anklicken
 * statt tippen. Fuer ein Attribut passt das nicht -- welche Werte es annehmen
 * kann, weiss das Backend nicht (Issue 14) --, deshalb dort ein Textfeld.
 */
function wertfeld(bedingung, info, umfeld, kennung, feld, nr, stelle) {
  if (bedingung.kind === "numeric") {
    return `
      <select ${feld}="operator" ${nr} aria-label="${t("rules.comparison")}">
        ${OPERATOREN.map(
          (operator) =>
            `<option value="${operator}" ${bedingung.operator === operator ? "selected" : ""}>${t(
              `rules.operator.${operator}`
            )}</option>`
        ).join("")}
      </select>
      <input type="number" step="any" ${feld}="threshold" ${nr}
             placeholder="${t("rules.threshold")}" aria-label="${t("rules.threshold")}"
             value="${bedingung.threshold ?? ""}">
    `;
  }

  const zustaende = info.states || [];
  if (bedingung.value_source?.kind === "attribute" || !zustaende.length) {
    return `<input type="text" ${feld}="states" ${nr}
                   placeholder="${escapeHtml(attributWert(bedingung, info) ?? t("rules.statePlaceholder"))}"
                   aria-label="${t("common.state")}"
                   value="${escapeHtml((bedingung.states || []).join(", "))}">`;
  }

  return `
    <div class="chips" role="group" aria-label="${t("common.state")}">
      ${zustaende
        .map(
          (zustand) =>
            `<button class="btn choice" data-action="toggle-state" ${stelle}
                     data-value="${escapeHtml(zustand)}"
                     aria-pressed="${(bedingung.states || []).includes(zustand)}">${escapeHtml(
                       zustandsName(kennung, zustand, umfeld)
                     )}</button>`
        )
        .join("")}
    </div>
  `;
}

/** Der aktuelle Wert des gewaehlten Attributs, als Text. */
function attributWert(bedingung, info) {
  if (bedingung.value_source?.kind !== "attribute") return null;
  const attribut = (info.attributes || []).find(
    (eintrag) => eintrag.name === bedingung.value_source.attribute
  );
  return attribut && attribut.value != null ? String(attribut.value) : null;
}

/**
 * Hilfe unter dem Feld: der aktuelle Wert des Attributs, und eine Warnung,
 * wenn der eingetragene sich davon nur in der Gross- und Kleinschreibung
 * unterscheidet. Der Vergleich im Backend bleibt zeichengenau.
 */
function wertHinweis(bedingung, info) {
  if (bedingung.kind === "numeric") return "";
  const aktuell = attributWert(bedingung, info);
  if (aktuell === null) return "";

  const eingetragen = (bedingung.states || []).map((wert) => String(wert).trim()).filter(Boolean);
  const schreibweise = eingetragen.some(
    (wert) => wert !== aktuell && wert.toLowerCase() === aktuell.toLowerCase()
  );

  return `
    <div class="entity-meta">
      ${t("rules.currentValue", { value: aktuell })}
      ${
        schreibweise
          ? `<span class="badge uncertain">${t("rules.caseMismatch", { value: aktuell })}</span>`
          : ""
      }
    </div>
  `;
}

function weitereBedingungen(entwurf, umfeld) {
  const extras = entwurf.extra_conditions || [];
  const wort = entwurf.logic === "any" ? t("rules.logicWord.any") : t("rules.logicWord.all");

  return `
    ${
      extras.length
        ? `<div class="filters">
             <span class="row-sub">${t("editor.logicLead")}</span>
             <div class="segmented special" role="group" aria-label="${t("rules.logicLabel")}">
               <button data-action="set-logic" data-value="all"
                       aria-pressed="${entwurf.logic !== "any"}">${t("editor.logicAll")}</button>
               <button data-action="set-logic" data-value="any"
                       aria-pressed="${entwurf.logic === "any"}">${t("editor.logicAny")}</button>
             </div>
           </div>`
        : ""
    }
    ${extras
      .map((bedingung, index) => bedingungsKarte(bedingung, index, { ...umfeld, logikWort: wort }))
      .join("")}
    <div>
      <button class="btn dashed" data-action="add-condition">${t("editor.addCondition")}</button>
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

// ---------------------------------------------------------------------------
// Schritt 2 und 3
// ---------------------------------------------------------------------------

function wartezeit(entwurf) {
  const minuten = entwurf.duration_seconds ? Math.round(entwurf.duration_seconds / 60) : 0;

  return `
    <div class="filters" role="group" aria-label="${t("rules.duration")}">
      ${WARTEZEITEN.map(
        (wert) =>
          `<button class="btn choice" data-action="set-duration" data-value="${wert}"
                   aria-pressed="${minuten === wert}">${
                     wert === 0
                       ? t("editor.waitNone")
                       : wert === 60
                         ? t("editor.waitHour")
                         : t("editor.waitMinutes", { minutes: wert })
                   }</button>`
      ).join("")}
      <label class="inline">${t("editor.waitOr")}
        <input type="number" min="0" data-rule-field="duration" aria-label="${t("rules.duration")}"
               value="${minuten || ""}">
        ${t("editor.waitUnit")}
      </label>
    </div>
    <p class="row-sub">${minuten ? t("editor.waitExplain", { minutes: minuten }) : t("editor.waitExplainNone")}</p>
  `;
}

function meldung(entwurf) {
  return `
    <div class="type-tiles" role="group" aria-label="${t("history.type")}">
      ${TYPEN.map(
        (typ) => `
          <button class="type-tile ${typ}" data-action="set-type" data-value="${typ}"
                  aria-pressed="${entwurf.type === typ}">
            ${icon(typ, 22)}
            <span><strong>${escapeHtml(typeLabel(typ))}</strong><span>${t(
              `editor.typeHint.${typ}`
            )}</span></span>
          </button>`
      ).join("")}
    </div>

    <label class="field">
      <span>${t("editor.messageLabel")}</span>
      <input type="text" data-rule-field="message"
             placeholder="${escapeHtml(t("rules.messagePlaceholder"))}"
             aria-label="${t("rules.message")}"
             value="${escapeHtml(entwurf.message_template || "")}">
    </label>
    <div class="filters small">
      <span class="row-sub">${t("editor.insert")}</span>
      ${PLATZHALTER.map(
        (name) =>
          `<button class="btn chip-btn" data-action="insert-placeholder"
                   data-value="{${name}}">${t(`editor.placeholder.${name}`)}</button>`
      ).join("")}
    </div>
  `;
}
