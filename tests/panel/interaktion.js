/**
 * Bedienungstests des Panels: Schaltflaechen, Filter, Eingabefelder.
 *
 * Geprueft wird beides -- was die Oberflaeche anzeigt und **welches Kommando
 * sie mit welchen Parametern abschickt**. Das zweite ist der eigentliche
 * Zweck: die Naht zwischen Bedienung und Backend hat sich als die Stelle
 * erwiesen, an der Fehler unbemerkt bleiben.
 *
 * Was das Backend aus den Kommandos macht, steht nicht hier. Das ist in
 * `SYSTEMTESTS.md`, Abschnitte A bis J, gegen eine laufende Instanz geprueft.
 */

const P = () => window.__panel;
const SR = () => window.__panel.shadowRoot;

const warte = (ms) => new Promise((r) => setTimeout(r, ms));

/** Laesst angestossene Aufrufe und das Neuzeichnen zur Ruhe kommen. */
const ruhe = async () => {
  await warte(40);
  await warte(40);
};

/** Wartezeit ueber die Entprellung der Eingabefelder hinaus (500 ms). */
const nachEntprellung = () => warte(750);

const marke = () => window.__protokoll.length;
const seither = (ab) => window.__protokoll.slice(ab);
const letztes = (ab, kommando) =>
  seither(ab)
    .filter((e) => e.kommando === kommando)
    .pop();
const anzahl = (ab, kommando) => seither(ab).filter((e) => e.kommando === kommando).length;

function pruefe(bedingung, meldung) {
  if (!bedingung) throw new Error(meldung);
}

function gleich(ist, soll, was) {
  const a = JSON.stringify(ist);
  const b = JSON.stringify(soll);
  if (a !== b) throw new Error(`${was}: ${a} statt ${b}`);
}

function element(auswahl, index = 0) {
  const treffer = SR().querySelectorAll(auswahl);
  if (!treffer[index]) throw new Error(`Element fehlt: ${auswahl} [${index}]`);
  return treffer[index];
}

/**
 * Wartet, bis ein Element da ist, statt auf eine feste Zeit zu setzen.
 *
 * Eine Aktion kann eine oder zwei Abfragen nach sich ziehen, je nachdem, was
 * schon geladen ist. Eine feste Wartezeit trifft mal zu, mal nicht, und der
 * Test wird launisch.
 */
async function bisSichtbar(auswahl, grenze = 2000) {
  const ende = Date.now() + grenze;
  for (;;) {
    const treffer = SR().querySelector(auswahl);
    if (treffer) return treffer;
    if (Date.now() > ende) throw new Error(`erschien nicht: ${auswahl}`);
    await warte(20);
  }
}

async function klick(auswahl, index = 0) {
  element(auswahl, index).click();
  await ruhe();
}

/** Setzt ein Auswahlfeld und meldet die Aenderung wie ein Anwender. */
async function waehle(auswahl, wert) {
  const feld = element(auswahl);
  feld.value = wert;
  feld.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
  await ruhe();
}

/** Tippt in ein Textfeld. */
async function tippe(auswahl, wert) {
  const feld = element(auswahl);
  feld.value = wert;
  feld.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
}

async function seite(id) {
  await klick(`nav button[data-page="${id}"]`);
  await bisSichtbar(`nav button[data-page="${id}"][aria-current="page"]`);
}

/** Oeffnet den Regel-Editor einer Entity mit zwei Regeln. */
const HEIZUNG = "climate.knx_interface_arbeiten_heizung_raum";
const REGEL_NUMERISCH = "rule_0e1a62fe63d7";
const REGEL_ZUSTAND = "rule_0963d2881c46";

async function oeffneEditor(regelId = REGEL_NUMERISCH) {
  await seite("rules");
  await bisSichtbar(`[data-action="edit-rule"][data-rule="${regelId}"]`);
  await klick(`[data-action="edit-rule"][data-rule="${regelId}"]`);
  await bisSichtbar('[data-rule-field="kind"]');
}

// ---------------------------------------------------------------------------

const FAELLE = [
  // -- Navigation ---------------------------------------------------------
  {
    id: "L1",
    titel: "Die vier Reiter wechseln die Seite und markieren den aktiven",
    async fn() {
      for (const [id, ueberschrift] of [
        ["history", "Alle Typen"],
        ["rules", "Regeln"],
        ["discovery", "Alle Typen"],
        ["dashboard", "Ereignisse heute"],
      ]) {
        await seite(id);
        const aktiv = SR().querySelector('nav button[aria-current="page"]');
        pruefe(aktiv, `${id}: kein Reiter markiert`);
        gleich(aktiv.dataset.page, id, `${id}: markierter Reiter`);
        pruefe(window.__text().includes(ueberschrift), `${id}: Inhalt fehlt`);
      }
    },
  },
  {
    id: "L2",
    titel: "Der Verweis 'Historie' im Dashboard fuehrt zur Historie",
    async fn() {
      await seite("dashboard");
      await klick('[data-nav="history"]');
      gleich(
        SR().querySelector('nav button[aria-current="page"]').dataset.page,
        "history",
        "Seite nach dem Verweis"
      );
    },
  },
  {
    id: "L3",
    titel: "'Alle Regeln' fuehrt aus dem Editor zurueck und laedt neu",
    async fn() {
      await oeffneEditor();
      const ab = marke();
      await klick('[data-action="back-to-rules"]');
      gleich(
        SR().querySelector('nav button[aria-current="page"]').dataset.page,
        "rules",
        "Seite nach dem Zurueck"
      );
      pruefe(letztes(ab, "get_config"), "Uebersicht wurde nicht neu geladen");
    },
  },

  // -- Dashboard ----------------------------------------------------------
  {
    id: "L4",
    titel: "Eine Meldung mit Entity oeffnet die Detailansicht",
    async fn() {
      await seite("dashboard");
      window.__ereignisse.length = 0;
      await klick(".row.clickable");
      const ereignis = window.__ereignisse.pop();
      pruefe(ereignis, "kein hass-more-info gemeldet");
      pruefe(ereignis.detail.entityId, "keine Entity im Ereignis");
    },
  },
  {
    id: "L5",
    titel: "Jede aktive Meldung im Dashboard ist anklickbar",
    async fn() {
      await seite("dashboard");
      const alle = SR().querySelectorAll("main .row").length;
      const klickbar = SR().querySelectorAll("main .row.clickable").length;
      gleich(klickbar, alle, "anklickbare Zeilen (alle sieben haben eine Entity)");
    },
  },

  // -- Filter der Historie ------------------------------------------------
  {
    id: "L6",
    titel: "Filter Typ schickt 'types' mit",
    async fn() {
      await seite("history");
      const ab = marke();
      await waehle('[data-filter="typ"]', "alarm");
      gleich(letztes(ab, "get_history").nachricht.types, ["alarm"], "types");
    },
  },
  {
    id: "L7",
    titel: "Filter Quelle schickt 'sources' mit",
    async fn() {
      await seite("history");
      const ab = marke();
      await waehle('[data-filter="quelle"]', "automation");
      gleich(letztes(ab, "get_history").nachricht.sources, ["automation"], "sources");
    },
  },
  {
    id: "L8",
    titel: "Filter Bereich schickt 'area_ids' mit",
    async fn() {
      await seite("history");
      const ab = marke();
      await waehle('[data-filter="bereich"]', "kuche");
      gleich(letztes(ab, "get_history").nachricht.area_ids, ["kuche"], "area_ids");
    },
  },
  {
    id: "L9",
    titel: "Filter Zeitraum setzt 'start', 'Alle' laesst es weg",
    async fn() {
      await seite("history");
      let ab = marke();
      await waehle('[data-filter="zeitraum"]', "heute");
      const heute = letztes(ab, "get_history").nachricht.start;
      pruefe(heute, "heute: kein start");
      pruefe(new Date(heute).getHours() === 0 || heute.includes("T"), "heute: kein Zeitpunkt");

      ab = marke();
      await waehle('[data-filter="zeitraum"]', "30");
      const dreissig = letztes(ab, "get_history").nachricht.start;
      pruefe(new Date(dreissig) < new Date(heute), "30 Tage liegt nicht vor heute");

      ab = marke();
      await waehle('[data-filter="zeitraum"]', "alle");
      pruefe(!("start" in letztes(ab, "get_history").nachricht), "Alle: start wurde mitgeschickt");
    },
  },
  {
    id: "L10",
    titel: "Filter Seitengroesse setzt 'limit' und beginnt von vorn",
    async fn() {
      await seite("history");
      const ab = marke();
      await waehle('[data-filter="umfang"]', "200");
      const nachricht = letztes(ab, "get_history").nachricht;
      gleich(nachricht.limit, 200, "limit");
      gleich(nachricht.offset, 0, "offset");
      gleich(element('[data-filter="umfang"]').value, "200", "Auswahl nach dem Neuzeichnen");
    },
  },
  {
    id: "L11",
    titel: "Das Suchfeld fragt entprellt und mit 'search' ab",
    async fn() {
      await seite("history");
      const ab = marke();
      await tippe('[data-filter="suche"]', "Kueche");
      gleich(anzahl(ab, "get_history"), 0, "Abfragen sofort nach dem Tippen");
      await nachEntprellung();
      gleich(letztes(ab, "get_history").nachricht.search, "Kueche", "search");
    },
  },
  {
    id: "L12",
    titel: "Mehrere Filter wirken gemeinsam",
    async fn() {
      await seite("history");
      await waehle('[data-filter="typ"]', "alarm");
      await waehle('[data-filter="bereich"]', "flureg");
      const ab = marke();
      await waehle('[data-filter="quelle"]', "entity_rule");
      const nachricht = letztes(ab, "get_history").nachricht;
      gleich(nachricht.types, ["alarm"], "types");
      gleich(nachricht.area_ids, ["flureg"], "area_ids");
      gleich(nachricht.sources, ["entity_rule"], "sources");
    },
  },
  {
    id: "L13",
    titel: "Die leere Auswahl eines Filters entfernt ihn wieder",
    async fn() {
      await seite("history");
      await waehle('[data-filter="typ"]', "alarm");
      const ab = marke();
      await waehle('[data-filter="typ"]', "");
      pruefe(!("types" in letztes(ab, "get_history").nachricht), "types blieb gesetzt");
    },
  },
  {
    id: "L14",
    titel: "'Weitere laden' blaettert mit dem Versatz der geladenen Menge",
    async fn() {
      await seite("history");
      const geladen = SR().querySelectorAll("main .row").length;
      const ab = marke();
      await klick('[data-action="load-more"]');
      gleich(letztes(ab, "get_history").nachricht.offset, geladen, "offset");
    },
  },
  {
    id: "L15",
    titel: "Das Kreuz an einer Zeile loescht genau dieses Ereignis",
    async fn() {
      await seite("history");
      const knopf = element('[data-action="delete-event"]');
      const kennung = knopf.dataset.event;
      const ab = marke();
      knopf.click();
      await ruhe();
      gleich(letztes(ab, "delete_event").nachricht.event_id, kennung, "event_id");
      pruefe(letztes(ab, "get_history"), "Liste wurde nicht neu geladen");
    },
  },
  {
    id: "L16",
    titel: "Aktive Ereignisse tragen kein Loeschkreuz",
    async fn() {
      await seite("history");
      const zeilen = [...SR().querySelectorAll("main .row")];
      const aktive = zeilen.filter((z) => z.textContent.includes("aktiv"));
      pruefe(aktive.length > 0, "keine aktiven Zeilen in den Testdaten");
      for (const zeile of aktive) {
        pruefe(
          !zeile.querySelector('[data-action="delete-event"]'),
          "aktive Zeile bietet ein Loeschkreuz an"
        );
      }
    },
  },
  {
    id: "L17",
    titel: "'Alle loeschen' fragt nach und bricht auf Abbruch folgenlos ab",
    async fn() {
      await seite("history");
      window.__dialoge.length = 0;
      window.__confirmAntwort = false;
      const ab = marke();
      await klick('[data-action="clear-history"]');
      window.__confirmAntwort = true;
      pruefe(window.__dialoge.some((d) => d.art === "confirm"), "es wurde nicht nachgefragt");
      gleich(anzahl(ab, "clear_history"), 0, "Aufrufe trotz Abbruch");
    },
  },
  {
    id: "L18",
    titel: "'Alle loeschen' loescht nach Bestaetigung",
    async fn() {
      await seite("history");
      window.__confirmAntwort = true;
      const ab = marke();
      await klick('[data-action="clear-history"]');
      gleich(anzahl(ab, "clear_history"), 1, "Aufrufe");
      pruefe(letztes(ab, "get_history"), "Liste wurde nicht neu geladen");
    },
  },

  // -- Regeluebersicht ----------------------------------------------------
  {
    id: "L19",
    titel: "'Bearbeiten' oeffnet den Editor mit genau dieser Regel",
    async fn() {
      await oeffneEditor(REGEL_ZUSTAND);
      pruefe(window.__text().includes("Arbeiten Heizung Raum"), "falsche Entity");
      const offen = SR().querySelector(".row.editing");
      pruefe(offen, "keine Zeile als in Bearbeitung markiert");
      pruefe(offen.textContent.includes("hvac_action"), "die falsche Zeile ist offen");
    },
  },
  {
    id: "L20",
    titel: "'Loeschen' fragt nach und bricht auf Abbruch folgenlos ab",
    async fn() {
      await seite("rules");
      window.__dialoge.length = 0;
      window.__confirmAntwort = false;
      const ab = marke();
      await klick('[data-action="delete-rule"]');
      window.__confirmAntwort = true;
      pruefe(window.__dialoge.some((d) => d.art === "confirm"), "es wurde nicht nachgefragt");
      gleich(anzahl(ab, "delete_rule"), 0, "Aufrufe trotz Abbruch");
    },
  },
  {
    id: "L21",
    titel: "'Loeschen' schickt nach Bestaetigung die richtige Regel",
    async fn() {
      await seite("rules");
      const knopf = element('[data-action="delete-rule"]');
      const kennung = knopf.dataset.rule;
      window.__confirmAntwort = true;
      const ab = marke();
      knopf.click();
      await ruhe();
      gleich(letztes(ab, "delete_rule").nachricht.rule_id, kennung, "rule_id");
    },
  },

  // -- Regel-Editor -------------------------------------------------------
  {
    id: "L22",
    titel: "'Regel erstellen' oeffnet ein leeres Formular",
    async fn() {
      await oeffneEditor();
      await klick('[data-action="cancel-rule"]');
      await klick('[data-action="new-rule"]');
      await bisSichtbar('[data-rule-field="kind"]');
      gleich(element('[data-rule-field="kind"]').value, "state_is", "Bedingung");
      gleich(element('[data-rule-field="type"]').value, "warning", "Typ");
      gleich(element('[data-rule-field="message"]').value, "", "Meldungstext");
      pruefe(!SR().querySelector(".row.editing"), "eine bestehende Zeile gilt als offen");
    },
  },
  {
    id: "L23",
    titel: "Die Bedingung schaltet zwischen Zustands- und Wertfeldern um",
    async fn() {
      await oeffneEditor();
      await klick('[data-action="cancel-rule"]');
      await klick('[data-action="new-rule"]');
      await bisSichtbar('[data-rule-field="kind"]');
      pruefe(SR().querySelector('[data-rule-field="states"]'), "Zustandsfeld fehlt");
      await waehle('[data-rule-field="kind"]', "numeric");
      pruefe(SR().querySelector('[data-rule-field="operator"]'), "Vergleichsfeld fehlt");
      pruefe(SR().querySelector('[data-rule-field="threshold"]'), "Schwellenfeld fehlt");
      pruefe(!SR().querySelector('[data-rule-field="states"]'), "Zustandsfeld blieb stehen");
      await waehle('[data-rule-field="kind"]', "state_is");
      pruefe(SR().querySelector('[data-rule-field="states"]'), "Zustandsfeld kam nicht zurueck");
    },
  },
  {
    id: "L24",
    titel: "Die Wertquelle laesst sich auf ein Attribut umstellen",
    async fn() {
      await oeffneEditor();
      const feld = element('[data-rule-field="source"]');
      const attribut = [...feld.options].find((o) => o.value === "temperature");
      pruefe(attribut, "das Attribut steht nicht zur Auswahl");
      await waehle('[data-rule-field="source"]', "temperature");
      const ab = marke();
      await klick('[data-action="save-rule"]');
      const regel = letztes(ab, "save_rule").nachricht.rule;
      gleich(regel.value_source, { kind: "attribute", attribute: "temperature" }, "value_source");
      // Kein Zuruecksetzen des Feldes: Speichern schliesst das Formular. Jeder
      // Fall oeffnet den Editor ohnehin neu.
      pruefe(!SR().querySelector('[data-rule-field="source"]'), "das Formular blieb nach dem Speichern offen");
    },
  },
  {
    id: "L25",
    titel: "Vergleich und Schwelle wandern als Zahl in die Regel",
    async fn() {
      await oeffneEditor();
      await waehle('[data-rule-field="operator"]', "lt");
      await tippe('[data-rule-field="threshold"]', "12.5");
      const ab = marke();
      await klick('[data-action="save-rule"]');
      const regel = letztes(ab, "save_rule").nachricht.rule;
      gleich(regel.operator, "lt", "operator");
      gleich(regel.threshold, 12.5, "threshold");
      pruefe(typeof regel.threshold === "number", "Schwelle ist keine Zahl");
    },
  },
  {
    id: "L26",
    titel: "Die Mehrfachauswahl der Zustaende landet als Liste in der Regel",
    async fn() {
      await oeffneEditor(REGEL_ZUSTAND);
      const feld = element('[data-rule-field="states"]');
      pruefe(feld.multiple, "das Zustandsfeld erlaubt keine Mehrfachauswahl");
      for (const option of feld.options) option.selected = true;
      feld.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
      await ruhe();
      const ab = marke();
      await klick('[data-action="save-rule"]');
      gleich(letztes(ab, "save_rule").nachricht.rule.states, ["on", "off"], "states");
    },
  },
  {
    id: "L27",
    titel: "Der Meldungstext zeichnet nicht neu, damit der Fokus bleibt",
    async fn() {
      await oeffneEditor();
      const feld = element('[data-rule-field="message"]');
      feld.focus();
      await tippe('[data-rule-field="message"]', "Neuer Text {value}");
      await ruhe();
      pruefe(
        SR().activeElement === element('[data-rule-field="message"]'),
        "der Fokus ist beim Tippen verlorengegangen"
      );
      const ab = marke();
      await klick('[data-action="save-rule"]');
      gleich(
        letztes(ab, "save_rule").nachricht.rule.message_template,
        "Neuer Text {value}",
        "message_template"
      );
    },
  },
  {
    id: "L28",
    titel: "Hysterese und Zeitbedingung im erweiterten Bereich",
    async fn() {
      await oeffneEditor();
      const erweitert = element("details");
      pruefe(erweitert.open, "der erweiterte Bereich ist bei gesetzten Werten nicht offen");
      await tippe('[data-rule-field="release"]', "7");
      await tippe('[data-rule-field="duration"]', "15");
      const ab = marke();
      await klick('[data-action="save-rule"]');
      const regel = letztes(ab, "save_rule").nachricht.rule;
      gleich(regel.release_threshold, 7, "release_threshold");
      gleich(regel.duration_seconds, 900, "duration_seconds (15 Minuten)");
    },
  },
  {
    id: "L29",
    titel: "'Speichern' behaelt die Kennung einer bestehenden Regel",
    async fn() {
      await oeffneEditor();
      const ab = marke();
      await klick('[data-action="save-rule"]');
      gleich(letztes(ab, "save_rule").nachricht.rule.rule_id, REGEL_NUMERISCH, "rule_id");
    },
  },
  {
    id: "L30",
    titel: "'Abbrechen' schliesst das Formular ohne Kommando",
    async fn() {
      await oeffneEditor();
      const ab = marke();
      await klick('[data-action="cancel-rule"]');
      gleich(anzahl(ab, "save_rule"), 0, "Speicheraufrufe");
      pruefe(!SR().querySelector('[data-rule-field="kind"]'), "das Formular steht noch");
      pruefe(!SR().querySelector(".row.editing"), "eine Zeile gilt weiter als offen");
    },
  },
  {
    id: "L31",
    titel: "'Entity ersetzen' fragt nach und bricht ohne Eingabe ab",
    async fn() {
      await oeffneEditor();
      await klick('[data-action="cancel-rule"]');
      await bisSichtbar('[data-action="replace-entity"]');
      window.__dialoge.length = 0;
      window.__promptAntwort = null;
      const ab = marke();
      await klick('[data-action="replace-entity"]');
      pruefe(window.__dialoge.some((d) => d.art === "prompt"), "es wurde nicht nachgefragt");
      gleich(anzahl(ab, "replace_entity"), 0, "Aufrufe trotz Abbruch");
    },
  },
  {
    id: "L32",
    titel: "'Entity ersetzen' schickt alte und neue Kennung, ohne Leerzeichen",
    async fn() {
      await oeffneEditor();
      await klick('[data-action="cancel-rule"]');
      await bisSichtbar('[data-action="replace-entity"]');
      window.__promptAntwort = "  switch.neue_entity  ";
      const ab = marke();
      await klick('[data-action="replace-entity"]');
      window.__promptAntwort = null;
      const nachricht = letztes(ab, "replace_entity").nachricht;
      gleich(nachricht.old_entity_id, HEIZUNG, "old_entity_id");
      gleich(nachricht.new_entity_id, "switch.neue_entity", "new_entity_id");
    },
  },

  // -- Discovery ----------------------------------------------------------
  {
    id: "L33",
    titel: "Die Typauswahl schickt 'domain' mit",
    async fn() {
      await seite("discovery");
      const ab = marke();
      await waehle('[data-discovery="domain"]', "input_boolean");
      gleich(letztes(ab, "discover").nachricht.domain, "input_boolean", "domain");
      await waehle('[data-discovery="domain"]', "");
    },
  },
  {
    id: "L34",
    titel: "Das Suchfeld der Discovery fragt entprellt ab",
    async fn() {
      await seite("discovery");
      const ab = marke();
      await tippe('[data-discovery="search"]', "fenster");
      gleich(anzahl(ab, "discover"), 0, "Abfragen sofort nach dem Tippen");
      await nachEntprellung();
      gleich(letztes(ab, "discover").nachricht.search, "fenster", "search");
      await tippe('[data-discovery="search"]', "");
      await nachEntprellung();
    },
  },
  {
    id: "L35",
    titel: "'Uebernehmen' meldet genau diese Entity zur Ueberwachung an",
    async fn() {
      await seite("discovery");
      const knopf = element('[data-action="add-entity"]');
      const kennung = knopf.dataset.entity;
      const ab = marke();
      knopf.click();
      await ruhe();
      gleich(letztes(ab, "add_entities").nachricht.entity_ids, [kennung], "entity_ids");
      pruefe(letztes(ab, "discover"), "die Liste wurde nicht neu geladen");
    },
  },
  {
    id: "L36",
    titel: "'Entfernen' fragt nach und schickt danach die Entity",
    async fn() {
      await seite("discovery");
      const knopf = element('[data-action="remove-entity"]');
      const kennung = knopf.dataset.entity;
      window.__dialoge.length = 0;
      window.__confirmAntwort = false;
      let ab = marke();
      knopf.click();
      await ruhe();
      pruefe(window.__dialoge.some((d) => d.art === "confirm"), "es wurde nicht nachgefragt");
      gleich(anzahl(ab, "remove_entity"), 0, "Aufrufe trotz Abbruch");

      window.__confirmAntwort = true;
      ab = marke();
      element('[data-action="remove-entity"]').click();
      await ruhe();
      gleich(letztes(ab, "remove_entity").nachricht.entity_id, kennung, "entity_id");
    },
  },
  {
    id: "L37",
    titel: "'Vorschlaege' holt sie, derselbe Knopf klappt sie wieder ein",
    async fn() {
      await seite("discovery");
      let ab = marke();
      await klick('[data-action="show-suggestions"]');
      gleich(anzahl(ab, "get_suggestions"), 1, "Abfragen beim Aufklappen");
      pruefe(SR().querySelector(".suggestions"), "die Vorschlaege sind nicht sichtbar");
      pruefe(
        element('[data-action="show-suggestions"]').textContent.includes("ausblenden"),
        "die Beschriftung wechselt nicht"
      );

      ab = marke();
      await klick('[data-action="show-suggestions"]');
      gleich(anzahl(ab, "get_suggestions"), 0, "Abfragen beim Einklappen");
      pruefe(!SR().querySelector(".suggestions"), "die Vorschlaege blieben stehen");
    },
  },
  {
    id: "L38",
    titel: "Ein Vorschlag uebernimmt Entity und Regel in einem Zug",
    async fn() {
      await seite("discovery");
      await klick('[data-action="show-suggestions"]');
      const knopf = element('[data-action="accept-suggestion"]');
      const kennung = knopf.dataset.entity;
      const ab = marke();
      knopf.click();
      await ruhe();
      gleich(letztes(ab, "add_entities").nachricht.entity_ids, [kennung], "entity_ids");
      const regel = letztes(ab, "save_rule").nachricht.rule;
      gleich(regel.entity_id, kennung, "entity_id der Regel");
      gleich(regel.kind, "state_is", "kind aus dem Vorschlag");
      gleich(regel.type, "warning", "type aus dem Vorschlag");
      gleich(regel.duration_seconds, 900, "duration_seconds aus dem Vorschlag");
      gleich(regel.message_template, "{name} steht offen", "message_template");
    },
  },
  {
    id: "L39",
    titel: "Die Begruendung eines Vorschlags laesst sich aufklappen",
    async fn() {
      await seite("discovery");
      await klick('[data-action="show-suggestions"]');
      const aufklappbar = SR().querySelector(".suggestions details");
      pruefe(aufklappbar, "keine aufklappbare Begruendung");
      pruefe(!aufklappbar.open, "die Begruendung ist von vornherein offen");
      aufklappbar.open = true;
      await ruhe();
      pruefe(
        aufklappbar.textContent.includes("window") || aufklappbar.textContent.includes("Geraeteklasse"),
        "die Begruendung nennt ihre Quelle nicht"
      );
    },
  },
  {
    id: "L40",
    titel: "'Regeln' fuehrt aus der Discovery in den Editor",
    async fn() {
      await seite("discovery");
      const knopf = element('[data-action="show-rules"]');
      const kennung = knopf.dataset.entity;
      knopf.click();
      await ruhe();
      pruefe(SR().querySelector('[data-action="back-to-rules"]'), "der Editor ist nicht offen");
      pruefe(
        window.__text().includes("Regeln für"),
        "die Ueberschrift des Editors fehlt"
      );
      pruefe(kennung, "am Knopf fehlt die Entity");
    },
  },

  // -- Fehlerbehandlung ---------------------------------------------------
  {
    id: "L41",
    titel: "Ein Fehler des Backends wird angezeigt, das Panel bleibt bedienbar",
    async fn() {
      await seite("history");
      window.__naechsterFehler = "Datenbank nicht erreichbar";
      await waehle('[data-filter="typ"]', "info");
      pruefe(
        window.__text().includes("Datenbank nicht erreichbar"),
        "die Fehlermeldung wird nicht angezeigt"
      );
      await seite("dashboard");
      pruefe(window.__text().includes("Ereignisse heute"), "das Panel reagiert nicht mehr");
    },
  },
];

/**
 * Der Einrichtungsassistent laeuft in einer eigenen Instanz.
 *
 * Er zeigt sich nur, solange weder `setup_completed` gesetzt ist noch
 * Entities ueberwacht werden. Das laesst sich an der bestehenden Instanz
 * nicht mehr herstellen (Ticket 9).
 */
async function mitFrischemPanel(konfiguration) {
  const protokoll = [];
  const element = document.createElement("notification-center-panel");
  element.hass = {
    locale: { language: "de" },
    areas: {},
    states: {},
    connection: {
      async sendMessagePromise(nachricht) {
        const kommando = String(nachricht.type).replace("notification_center/", "");
        protokoll.push({ kommando, nachricht });
        if (kommando === "get_config") return konfiguration;
        if (kommando === "get_active") return { api_version: 1, version: "1.1.3", counts: {}, active: [] };
        if (kommando === "discover") return { api_version: 1, version: "1.1.3", entities: [] };
        return { api_version: 1, version: "1.1.3" };
      },
      async subscribeMessage() {
        return () => {};
      },
    },
  };
  document.body.appendChild(element);
  await warte(120);
  return { element, protokoll, aufraeumen: () => element.remove() };
}

const LEERE_KONFIGURATION = {
  api_version: 1,
  version: "1.1.3",
  entities: [],
  rules: [],
  groups: [],
  settings: { paused: false, retention_days: 90, max_events: 5000, analysis_days: 7, setup_completed: false },
  options: { retention_days: [7, 30, 90, 365, 0], max_events: [1000, 5000, 10000, 50000] },
};

FAELLE.push(
  {
    id: "L42",
    titel: "Ohne Einrichtung und ohne Entities erscheint der Assistent",
    async fn() {
      const { element, aufraeumen } = await mitFrischemPanel(LEERE_KONFIGURATION);
      try {
        const text = element.shadowRoot.textContent;
        pruefe(
          element.shadowRoot.querySelector('[data-action="start-setup"]'),
          "der Assistent fehlt"
        );
        pruefe(text.includes("Überspringen"), "der Ueberspringen-Knopf fehlt");
      } finally {
        aufraeumen();
      }
    },
  },
  {
    id: "L43",
    titel: "'Ueberspringen' merkt sich das und fuehrt ins Dashboard (Ticket 9)",
    async fn() {
      const { element, protokoll, aufraeumen } = await mitFrischemPanel(LEERE_KONFIGURATION);
      try {
        element.shadowRoot.querySelector('[data-action="skip-setup"]').click();
        await warte(120);
        const gesetzt = protokoll.filter((e) => e.kommando === "set_settings").pop();
        pruefe(gesetzt, "die Einrichtung wurde nicht als erledigt gemeldet");
        gleich(gesetzt.nachricht.setup_completed, true, "setup_completed");
        pruefe(
          !element.shadowRoot.querySelector('[data-action="start-setup"]'),
          "der Assistent steht noch"
        );
      } finally {
        aufraeumen();
      }
    },
  },
  {
    id: "L44",
    titel: "'Einrichtung starten' merkt sich das und fuehrt in die Discovery",
    async fn() {
      const { element, protokoll, aufraeumen } = await mitFrischemPanel(LEERE_KONFIGURATION);
      try {
        element.shadowRoot.querySelector('[data-action="start-setup"]').click();
        await warte(150);
        const gesetzt = protokoll.filter((e) => e.kommando === "set_settings").pop();
        pruefe(gesetzt, "die Einrichtung wurde nicht als erledigt gemeldet");
        gleich(gesetzt.nachricht.setup_completed, true, "setup_completed");
        pruefe(
          protokoll.some((e) => e.kommando === "discover"),
          "die Discovery wurde nicht geladen"
        );
      } finally {
        aufraeumen();
      }
    },
  },
  {
    id: "L45",
    titel: "Mit vorhandenen Entities bleibt der Assistent fort",
    async fn() {
      const konfiguration = {
        ...LEERE_KONFIGURATION,
        entities: [{ entity_id: "switch.a", name: "A", area_name: null, floor_name: null }],
      };
      const { element, aufraeumen } = await mitFrischemPanel(konfiguration);
      try {
        pruefe(
          !element.shadowRoot.querySelector('[data-action="start-setup"]'),
          "der Assistent erscheint trotz vorhandener Entities"
        );
      } finally {
        aufraeumen();
      }
    },
  }
);

/** Fuehrt alle Faelle nacheinander aus. */
export async function lauf() {
  const ergebnis = [];
  for (const fall of FAELLE) {
    try {
      await fall.fn();
      ergebnis.push({ id: fall.id, titel: fall.titel, bestanden: true });
    } catch (fehler) {
      ergebnis.push({
        id: fall.id,
        titel: fall.titel,
        bestanden: false,
        fehler: fehler.message || String(fehler),
      });
    }
  }
  return ergebnis;
}
