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

import { categoryLabel, escapeHtml, eventDuration, typeLabel } from "../format.js";
import { raw } from "../html.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { renderEditor } from "./editor.js";

const OPERATOREN = ["gt", "gte", "lt", "lte", "eq"];

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

/** Die Filter der Uebersicht, in der Reihenfolge ihrer Schaltflaechen. */
const REGEL_FILTER = ["all", "alarm", "warning", "info", "combined", "disabled"];

const TYP_REIHENFOLGE = ["alarm", "warning", "info"];

/** Ab so vielen Regeln ist die dichte Liste die Vorgabe. */
export const LISTE_AB = 24;

/**
 * Wie viele Regeln ein Raum der dichten Liste zunaechst zeigt.
 *
 * Gekuerzt wird erst, wenn dadurch mindestens drei Zeilen wegfallen: fuer
 * eine oder zwei lohnt der Knopf nicht, er waere selbst eine Zeile. Was
 * gerade meldet, steht immer da -- eine Kuerzung darf nichts verbergen, das
 * Aufmerksamkeit braucht.
 */
export const ZEILEN_JE_RAUM = 6;
export const KUERZEN_AB = ZEILEN_JE_RAUM + 3;

/**
 * Uebersicht aller Regeln.
 *
 * Gebaut fuer zwei Groessenordnungen. Ein Dutzend Regeln steht als
 * Raumkarten da, jede Regel mit ihrer Bedingung in Bausteinen. Bei vielen
 * Regeln traegt das nicht mehr -- dann greifen drei Dinge zusammen:
 *
 * * Was gerade meldet, steht angeheftet ganz oben. Das ist die Frage, mit der
 *   man diese Seite meist oeffnet, und sie soll kein Aufklappen kosten.
 * * Die Abschnitte (Geschoss oder Typ) lassen sich einklappen und sagen
 *   zugeklappt, wie viele Regeln sie fuehren und ob eine davon meldet.
 * * Die dichte Liste zeigt eine Zeile je Regel, die Raeume als eigene Felder,
 *   damit die Zeilen nicht zu einer Wand verschwimmen.
 *
 * Suche und Filter arbeiten auf dem geladenen Bestand, nicht im Backend: es
 * sind Dutzende Regeln, nicht Tausende Ereignisse.
 */
export function renderRuleOverview(state) {
  const {
    entities = [],
    rules = [],
    loading,
    names = {},
    active = [],
    search = "",
    filter = "all",
    group = "room",
    density = null,
    collapsed = {},
    expandedRooms = [],
  } = state;

  if (loading) return `<div class="loading">${t("common.loading")}</div>`;

  if (!rules.length) {
    return `
      <div class="card empty">
        <strong>${t("rules.overviewEmpty")}</strong>
        <span>
          ${t("rules.overviewEmptyHint", {
            // Ausdruecklich Markup: die Schaltflaeche steht hier im
            // Quelltext und soll keine maskierten Klammern zeigen.
            link: raw(`<button class="link" data-nav="discovery">${t("nav.discovery")}</button>`),
          })}
        </span>
      </div>
    `;
  }

  const platzierung = new Map(entities.map((eintrag) => [eintrag.entity_id, eintrag]));
  const meldend = meldendeRegeln(active);
  const anzahl = zaehleFilter(rules);
  const dicht = (density || (rules.length > LISTE_AB ? "list" : "cards")) === "list";
  const sichtbar = rules.filter(
    (regel) => passtZumFilter(regel, filter) && passtZurSuche(regel, search, platzierung, names)
  );

  const abschnitte = gliedere(sichtbar, platzierung, group);
  const zustand = {
    collapsed,
    viele: rules.length > LISTE_AB,
    // Wer sucht oder filtert, will die Treffer sehen und nicht aufklappen.
    ungekuerzt: Boolean(String(search).trim()) || filter !== "all",
    offeneRaeume: new Set(expandedRooms),
  };
  const alleZu = abschnitte.length > 0 && abschnitte.every((a) => istZu(a, zustand, meldend));

  return `
    <section class="card pad" aria-label="${t("rules.filterLabel")}">
      <div class="filters">
        <label class="search">
          ${icon("search", 18)}
          <input type="search" data-rule-search placeholder="${t("rules.searchPlaceholder")}"
                 value="${escapeHtml(search)}" aria-label="${t("rules.searchPlaceholder")}">
        </label>

        <div class="segmented view" role="group" aria-label="${t("rules.densityLabel")}">
          <button data-action="set-rule-density" data-value="cards"
                  aria-pressed="${!dicht}">${t("rules.densityCards")}</button>
          <button data-action="set-rule-density" data-value="list"
                  aria-pressed="${dicht}">${t("rules.densityList")}</button>
        </div>

        <div class="segmented view" role="group" aria-label="${t("rules.groupLabel")}">
          <button data-action="set-rule-group" data-value="room"
                  aria-pressed="${group !== "type"}">${t("rules.groupRoom")}</button>
          <button data-action="set-rule-group" data-value="type"
                  aria-pressed="${group === "type"}">${t("rules.groupType")}</button>
        </div>

        <button class="btn" data-action="collapse-all-rules"
                data-value="${alleZu ? "open" : "close"}">${
                  alleZu ? t("rules.expandAll") : t("rules.collapseAll")
                }</button>
      </div>

      <div class="filters" role="group" aria-label="${t("rules.filterLabel")}">
        ${REGEL_FILTER.filter((wert) => wert === "all" || anzahl[wert] > 0)
          .map(
            (wert) =>
              `<button class="btn filter ${wert}" data-action="set-rule-filter" data-value="${wert}"
                       aria-pressed="${filter === wert}">${t(`rules.filter.${wert}`, {
                         count: anzahl[wert],
                       })}</button>`
          )
          .join("")}
      </div>
    </section>

    ${angeheftet(sichtbar, platzierung, names, meldend)}

    ${
      sichtbar.length
        ? abschnitte
            .map((abschnitt) => abschnittHtml(abschnitt, zustand, dicht, platzierung, names, meldend))
            .join("")
        : `<div class="card empty"><strong>${t("rules.noMatch")}</strong><span>${t(
            "rules.noMatchHint"
          )}</span></div>`
    }

    ${ohneRegel(entities, rules)}
  `;
}

/**
 * Uebernommene Entities, die keine Regel tragen.
 *
 * Sie werden beobachtet, melden aber nie etwas -- und tauchen in der
 * Uebersicht sonst nirgends auf. Wer in der Discovery "23 ueberwacht" liest
 * und hier 17 Regeln zaehlt, sucht die Differenz vergeblich. Hier steht sie,
 * mit den zwei Dingen, die man damit tun will: eine Regel anlegen oder die
 * Entity wieder entfernen.
 */
export function ohneRegel(entities, rules) {
  const mitRegel = new Set(rules.map((regel) => regel.entity_id));
  const leer = entities.filter((eintrag) => !mitRegel.has(eintrag.entity_id));
  if (!leer.length) return "";

  return `
    <section class="section">
      <div class="section-title">${t("rules.withoutRule")} · ${leer.length}</div>
      <ul class="card rows">
        ${leer
          .map(
            (eintrag) => `
              <li class="row">
                <span class="row-body">
                  <span class="entity-name">${escapeHtml(eintrag.name || eintrag.entity_id)}</span>
                  <span class="mono">${escapeHtml(eintrag.entity_id)}${
                    eintrag.area_name ? ` · ${escapeHtml(eintrag.area_name)}` : ""
                  }</span>
                </span>
                <button class="btn soft" data-action="show-rules"
                        data-entity="${escapeHtml(eintrag.entity_id)}"
                        data-name="${escapeHtml(eintrag.name || "")}">${t("rules.create")}</button>
                <button class="btn" data-action="remove-entity"
                        data-entity="${escapeHtml(eintrag.entity_id)}">${t("discovery.remove")}</button>
              </li>
            `
          )
          .join("")}
      </ul>
    </section>
  `;
}

/**
 * Was gerade meldet, angeheftet ueber allem.
 *
 * Die Regeln stehen darunter noch einmal an ihrem Platz. Die Dopplung ist
 * gewollt: oben die Lage, unten der Bestand.
 */
function angeheftet(rules, platzierung, namen, meldend) {
  const laufend = rules
    .filter((regel) => meldend.has(regel.rule_id))
    .sort(
      (a, b) =>
        TYP_REIHENFOLGE.indexOf(a.type) - TYP_REIHENFOLGE.indexOf(b.type) ||
        new Date(meldend.get(b.rule_id).start_time) - new Date(meldend.get(a.rule_id).start_time)
    );
  if (!laufend.length) return "";

  return `
    <section class="section">
      <div class="section-title">${t("rules.reportingNow")} · ${laufend.length}</div>
      <ul class="card rows">
        ${laufend
          .map((regel) => regelLinie(regel, platzierung, namen, meldend.get(regel.rule_id), true))
          .join("")}
      </ul>
    </section>
  `;
}

/**
 * Ob ein Abschnitt zugeklappt ist.
 *
 * Was der Anwender selbst gesetzt hat, gilt. Ohne Vorgabe ist ein Abschnitt
 * offen -- ausser bei grossem Bestand: dann startet zugeklappt, was nichts
 * meldet, und die Seite beginnt mit dem, was Aufmerksamkeit braucht.
 */
function istZu(abschnitt, zustand, meldend) {
  const gesetzt = zustand.collapsed?.[abschnitt.schluessel];
  if (typeof gesetzt === "boolean") return gesetzt;
  // "Alle einklappen" setzt eine Vorgabe fuer jeden Abschnitt ohne eigene.
  if (typeof zustand.collapsed?.["*"] === "boolean") return zustand.collapsed["*"];
  return zustand.viele && meldetIn(abschnitt.regeln, meldend) === 0;
}

function meldetIn(regeln, meldend) {
  return regeln.filter((regel) => meldend.has(regel.rule_id)).length;
}

function abschnittHtml(abschnitt, zustand, dicht, platzierung, namen, meldend) {
  const zu = istZu(abschnitt, zustand, meldend);
  const melden = meldetIn(abschnitt.regeln, meldend);
  const dringlichster = TYP_REIHENFOLGE.find((typ) =>
    abschnitt.regeln.some((regel) => regel.type === typ && meldend.has(regel.rule_id))
  );

  return `
    <section class="section">
      <button class="toggle${zu ? " closed card" : ""}" data-action="toggle-rule-section"
              data-key="${escapeHtml(abschnitt.schluessel)}" aria-expanded="${!zu}">
        ${icon("chevron", 16)}
        <span>${escapeHtml(abschnitt.titel)}</span>
        <span class="summary">${t("rules.count", { count: abschnitt.regeln.length })} · ${t(
          "rules.roomCount",
          { count: abschnitt.karten.length }
        )}</span>
        ${
          melden
            ? `<span class="pill ${dringlichster}">${t("rules.reportingCount", { count: melden })}</span>`
            : zu
              ? `<span class="status">${t("rules.quiet")}</span>`
              : ""
        }
      </button>
      ${zu ? "" : dicht ? listenAnsicht(abschnitt, zustand, platzierung, namen, meldend) : kartenAnsicht(abschnitt, platzierung, namen, meldend)}
    </section>
  `;
}

function kartenAnsicht(abschnitt, platzierung, namen, meldend) {
  return `
    <div class="grid-cards">
      ${abschnitt.karten
        .map(
          (karte) => `
            <article class="card pad">
              <h3>${escapeHtml(karte.titel)}</h3>
              ${karte.entities.map((paar) => entityBlock(paar, platzierung, namen, meldend)).join("")}
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

/**
 * Die dichte Liste: je Raum ein eigenes Feld, darin eine Zeile je Regel.
 *
 * Das Feld ist die Klammer. Ohne sie waeren dreissig Zeilen eine Wand, in
 * der man den Raumwechsel nur an einer Zwischenueberschrift erkennt.
 */
function listenAnsicht(abschnitt, zustand, platzierung, namen, meldend) {
  return `
    <div class="card rows">
      ${abschnitt.karten
        .map((karte) => {
          const regeln = karte.entities.flatMap(([, eintraege]) => eintraege);
          const melden = meldetIn(regeln, meldend);
          const raumSchluessel = `${abschnitt.schluessel}|${karte.titel}`;
          const { gezeigt, verborgen } = kuerzeRaum(
            regeln,
            meldend,
            zustand.ungekuerzt || zustand.offeneRaeume.has(raumSchluessel)
          );
          const dringlichster = TYP_REIHENFOLGE.find((typ) =>
            regeln.some((regel) => regel.type === typ && meldend.has(regel.rule_id))
          );
          return `
            <div class="room-cluster">
              <div class="room-head">
                <strong>${escapeHtml(karte.titel)}</strong>
                <span class="row-sub">${t("rules.count", { count: regeln.length })}</span>
                ${
                  melden
                    ? `<span class="pill ${dringlichster}">${t("rules.reportingCount", {
                        count: melden,
                      })}</span>`
                    : ""
                }
              </div>
              <ul class="rule-lines tight">
                ${gezeigt
                  .map((regel) => regelLinie(regel, platzierung, namen, meldend.get(regel.rule_id)))
                  .join("")}
              </ul>
              ${
                verborgen
                  ? `<button class="btn more" data-action="show-all-room"
                             data-key="${escapeHtml(raumSchluessel)}">${t("rules.showMore", {
                               count: verborgen,
                               room: karte.titel,
                             })}</button>`
                  : ""
              }
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

/**
 * Kuerzt die Regeln eines Raums auf die ersten Zeilen.
 *
 * Meldende Regeln bleiben in jedem Fall stehen, auch jenseits der Grenze;
 * die Reihenfolge wird dabei nicht veraendert.
 */
export function kuerzeRaum(regeln, meldend, ungekuerzt = false) {
  if (ungekuerzt || regeln.length < KUERZEN_AB) return { gezeigt: regeln, verborgen: 0 };

  const gezeigt = regeln.filter(
    (regel, stelle) => stelle < ZEILEN_JE_RAUM || meldend.has(regel.rule_id)
  );
  return { gezeigt, verborgen: regeln.length - gezeigt.length };
}

/** Eine Regel als einzelne Zeile, fuer die dichte Liste und die Anheftung. */
function regelLinie(regel, platzierung, namen, ereignis = null, mitOrt = false) {
  const ort = platzierung.get(regel.entity_id) || {};
  const name = ort.name || regel.entity_id;
  const ziel =
    `data-rule="${escapeHtml(regel.rule_id)}" ` +
    `data-entity="${escapeHtml(regel.entity_id || "")}" ` +
    `data-name="${escapeHtml(name)}"`;
  const wo = [ort.floor_name, ort.area_name].filter(Boolean).join(" · ");

  return `
    <li class="rule-line${ereignis ? ` reporting ${regel.type}` : ""}">
      <span class="dot ${regel.type}" title="${escapeHtml(typeLabel(regel.type))}"></span>
      <span class="rule-line-name">${escapeHtml(name)}</span>
      <span class="rule-line-text">${escapeHtml(beschreibung(regel, namen))}</span>
      ${mitOrt && wo ? `<span class="row-sub">${escapeHtml(wo)}</span>` : ""}
      ${regel.enabled === false ? `<span class="badge">${t("rules.disabled")}</span>` : ""}
      ${
        ereignis
          ? `<span class="status ${regel.type}">${t("rules.reportingSince", {
              duration: eventDuration(ereignis),
            })}</span>`
          : `<span class="status">${t("rules.quiet")}</span>`
      }
      <button class="link" data-action="edit-rule" ${ziel}>${t("common.edit")}</button>
    </li>
  `;
}

/** Die gerade meldenden Regeln: Regel-Kennung auf ihr laufendes Ereignis. */
function meldendeRegeln(active) {
  return new Map(
    (active || []).filter((event) => event.rule_id).map((event) => [event.rule_id, event])
  );
}

function zaehleFilter(rules) {
  return {
    all: rules.length,
    alarm: rules.filter((regel) => regel.type === "alarm").length,
    warning: rules.filter((regel) => regel.type === "warning").length,
    info: rules.filter((regel) => regel.type === "info").length,
    combined: rules.filter((regel) => (regel.extra_conditions || []).length > 0).length,
    disabled: rules.filter((regel) => regel.enabled === false).length,
  };
}

function passtZumFilter(regel, filter) {
  if (TYP_REIHENFOLGE.includes(filter)) return regel.type === filter;
  if (filter === "combined") return (regel.extra_conditions || []).length > 0;
  if (filter === "disabled") return regel.enabled === false;
  return true;
}

/**
 * Sucht ueber alles, woran man eine Regel erkennt: Entity, Raum, Geschoss,
 * Bedingung und Meldungstext. Mehrere Woerter muessen alle vorkommen.
 */
function passtZurSuche(regel, search, platzierung, namen) {
  const begriffe = String(search || "")
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (!begriffe.length) return true;

  const ort = platzierung.get(regel.entity_id) || {};
  const heuhaufen = [
    regel.entity_id,
    ort.name,
    ort.area_name,
    ort.floor_name,
    regel.message_template,
    beschreibung(regel, namen),
    typeLabel(regel.type),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return begriffe.every((begriff) => heuhaufen.includes(begriff));
}

/**
 * Ordnet die Regeln in Abschnitte, darin in Raumkarten, darin nach Entity.
 *
 * Der Abschnitt ist das Geschoss oder, wahlweise, der Typ. Die Raumkarte
 * bleibt in beiden Faellen: der Raum ist das, woran man eine Entity
 * wiederfindet.
 */
function gliedere(rules, platzierung, group) {
  const abschnitte = new Map();

  for (const regel of rules) {
    const ort = platzierung.get(regel.entity_id) || {};
    const schluessel =
      group === "type" ? regel.type : ort.floor_name || t("rules.noFloor");
    const raum = ort.area_name || t("rules.noArea");

    if (!abschnitte.has(schluessel)) abschnitte.set(schluessel, new Map());
    const raeume = abschnitte.get(schluessel);

    if (!raeume.has(raum)) raeume.set(raum, new Map());
    const entities = raeume.get(raum);

    if (!entities.has(regel.entity_id)) entities.set(regel.entity_id, []);
    entities.get(regel.entity_id).push(regel);
  }

  const sortiert =
    group === "type"
      ? [...abschnitte.entries()].sort(
          ([a], [b]) => TYP_REIHENFOLGE.indexOf(a) - TYP_REIHENFOLGE.indexOf(b)
        )
      : [...abschnitte.entries()].sort(nachNamen);

  return sortiert.map(([schluessel, raeume]) => {
    const karten = [...raeume.entries()].sort(nachNamen).map(([raum, entities]) => ({
      titel: raum,
      entities: [...entities.entries()],
    }));
    return {
      schluessel: `${group}:${schluessel}`,
      titel: group === "type" ? categoryLabel(schluessel) : schluessel,
      regeln: karten.flatMap((karte) => karte.entities.flatMap(([, eintraege]) => eintraege)),
      karten,
    };
  });
}

function entityBlock([entityId, eintraege], platzierung, namen = {}, meldend = new Map()) {
  const name = platzierung.get(entityId)?.name || entityId;

  return `
    <div class="entity-block">
      <div>
        <div class="entity-name">${escapeHtml(name)}</div>
        <div class="mono">${escapeHtml(entityId)}</div>
      </div>
      <ul class="rule-lines">
        ${eintraege
          .map((regel) => regelZeile(regel, entityId, name, null, namen, meldend.get(regel.rule_id)))
          .join("")}
      </ul>
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
    names = {},
    active = [],
  } = state;

  if (entwurf) return renderEditor(state);

  const meldend = meldendeRegeln(active);

  return `
    <div class="filters">
      <button class="link" data-action="back-to-rules">${t("rules.backToAll")}</button>
    </div>

    <section class="card pad">
      <div>
        <h2>${t("rules.forEntity", { name: entityName || entityId })}</h2>
        <!--
          Die Entity-ID gehoert auf diese Seite: von hier aus laesst sich die
          Entity ersetzen, und dafuer muss man wissen, welche gerade gemeint
          ist. Zurueckhaltend gesetzt -- sie ist Beleg, nicht Ueberschrift.
        -->
        <div class="mono">${escapeHtml(entityId || "")}</div>
      </div>

      ${
        rules.length
          ? `<ul class="rule-lines">${rules
              .map((regel) =>
                regelZeile(
                  regel,
                  entityId,
                  entityName,
                  entwurf?.rule_id,
                  names,
                  meldend.get(regel.rule_id)
                )
              )
              .join("")}</ul>`
          : `<div class="row-sub">${t("rules.none")}</div>`
      }

      <div class="footer-link">
        <button class="action" data-action="new-rule">${t("rules.create")}</button>
        <button class="action secondary" data-action="replace-entity"
                data-entity="${escapeHtml(entityId)}">${t("rules.replaceEntity")}</button>
        <span class="spacer"></span>
        <button class="btn ghost danger" data-action="remove-entity"
                data-entity="${escapeHtml(entityId)}">${t("rules.removeEntity")}</button>
      </div>
    </section>
  `;
}

/**
 * Eine Regel als Block: Typ, Zustand, Bedingung in Bausteinen, Aktionen.
 *
 * ``offeneRegel`` ist die Regel, deren Formular gerade darunter steht. Sie
 * bekommt keinen Bearbeiten-Knopf: er wuerde auf das verweisen, was ohnehin
 * schon offen ist.
 *
 * ``ereignis`` ist die laufende Meldung der Regel, sofern sie gerade meldet.
 */
function regelZeile(
  regel,
  entityId = regel.entity_id,
  entityName = "",
  offeneRegel = null,
  namen = {},
  ereignis = null
) {
  // Entity und Name wandern mit: nur so kann der Editor auch aus der
  // Uebersicht heraus die richtigen Regeln laden.
  const ziel =
    `data-rule="${escapeHtml(regel.rule_id)}" ` +
    `data-entity="${escapeHtml(entityId || "")}" ` +
    `data-name="${escapeHtml(entityName)}"`;

  const wirdBearbeitet = Boolean(offeneRegel) && regel.rule_id === offeneRegel;
  const klassen = ["rule"];
  if (ereignis) klassen.push("reporting", regel.type);
  if (wirdBearbeitet) klassen.push("editing");

  const zusaetze = (regel.extra_conditions || []).length;

  return `
    <li class="${klassen.join(" ")}" title="${escapeHtml(beschreibung(regel, namen))}">
      <div class="rule-head">
        <span class="pill ${regel.type}">${typeLabel(regel.type)}</span>
        ${
          zusaetze
            ? `<span class="pill special">${t("rules.conditionCount", { count: zusaetze + 1 })}</span>`
            : ""
        }
        ${regel.enabled === false ? `<span class="badge">${t("rules.disabled")}</span>` : ""}
        ${
          ereignis
            ? `<span class="status ${regel.type}">${t("rules.reportingSince", {
                duration: eventDuration(ereignis),
              })}</span>`
            : `<span class="status">${t("rules.quiet")}</span>`
        }
      </div>
      <div class="rule-lines">${bedingungsZeilen(regel, namen)}</div>
      <div class="rule-actions">
        ${
          wirdBearbeitet
            ? `<span class="badge">${t("rules.editing")}</span>`
            : `<button class="link" data-action="edit-rule" ${ziel}>${t("common.edit")}</button>`
        }
        <button class="link" data-action="delete-rule" ${ziel}>${t("common.delete")}</button>
      </div>
    </li>
  `;
}

/**
 * Die Bedingungen einer Regel als Bausteine, eine Zeile je Bedingung.
 *
 * Die Verknuepfung steht als Wort davor und nicht als Zeichen: "UND NICHT"
 * liest jeder, ein Ausrufezeichen vor einer Klammer nicht.
 */
function bedingungsZeilen(regel, namen) {
  const wort = regel.logic === "any" ? t("rules.logicWord.any") : t("rules.logicWord.all");
  const zeilen = [`<div class="chips">${bedingungsChips({ ...regel, entity_id: null }, namen)}</div>`];

  for (const bedingung of regel.extra_conditions || []) {
    const vorsatz = bedingung.negate ? `${wort} ${t("rules.logicWord.not")}` : wort;
    zeilen.push(
      `<div class="chips"><span class="logic">${escapeHtml(vorsatz)}</span>${bedingungsChips(
        bedingung,
        namen
      )}</div>`
    );
  }

  if (regel.duration_seconds) {
    zeilen.push(
      `<div class="chips"><span class="chip">${t("rules.chip.longer", {
        minutes: raw(`<strong>${Math.round(regel.duration_seconds / 60)} min</strong>`),
      })}</span></div>`
    );
  }

  return zeilen.join("");
}

/** Eine Bedingung als ein oder zwei Bausteine. Die Werte stehen fett. */
export function bedingungsChips(bedingung, namen = {}) {
  const ort = bedingung.entity_id
    ? `${escapeHtml(namen[bedingung.entity_id] || bedingung.entity_id)} · `
    : "";
  const quelle =
    bedingung.value_source?.kind === "attribute"
      ? escapeHtml(bedingung.value_source.attribute)
      : t("common.state");

  if (bedingung.kind === "numeric") {
    const operator = OPERATOREN.includes(bedingung.operator)
      ? t(`rules.operator.${bedingung.operator}`)
      : escapeHtml(bedingung.operator);
    const schwelle = `<span class="chip">${ort}${quelle} ${operator} <strong>${escapeHtml(
      bedingung.threshold
    )}</strong></span>`;
    const zurueck =
      bedingung.release_threshold != null
        ? `<span class="chip">${t("rules.chip.back", {
            value: raw(`<strong>${escapeHtml(bedingung.release_threshold)}</strong>`),
          })}</span>`
        : "";
    return schwelle + zurueck;
  }

  const einleitung =
    bedingung.kind === "state_changed_to"
      ? t("rules.describe.changesTo")
      : bedingung.kind === "state_is_not"
        ? t("rules.describe.isNot")
        : t("rules.describe.is");
  const werte = (bedingung.states || [])
    .map((wert) => `<strong>${escapeHtml(wert)}</strong>`)
    .join(escapeHtml(t("rules.describe.or")));

  return `<span class="chip">${ort}${quelle} ${einleitung} ${werte}</span>`;
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
