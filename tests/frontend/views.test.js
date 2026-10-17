/**
 * Tests der reinen Darstellungsfunktionen des Frontends.
 *
 * Sie laufen mit dem Testlaeufer von Node, ohne Browser und ohne
 * Abhaengigkeiten. Damit ist geprueft, was sich ohne Browser pruefen laesst:
 * dass aus gegebenen Daten die erwartete Ausgabe entsteht.
 *
 * Anlass war eine Reihe von Anzeigefehlern, die alle erst beim Anwender
 * auffielen, weil das Frontend keinerlei Tests hatte.
 *
 * Nicht abgedeckt sind Panel und Karte selbst: sie binden Browser-APIs ein,
 * die es in Node nicht gibt.
 */

import assert from "node:assert/strict";
import { before, describe, it } from "node:test";

import { setzeSprache } from "../../custom_components/notification_center/frontend/i18n.js";
import { escapeHtml, formatDuration, sourceBadge, typeLabel } from "../../custom_components/notification_center/frontend/format.js";
import { renderDashboard } from "../../custom_components/notification_center/frontend/views/dashboard.js";
import { renderDiscovery } from "../../custom_components/notification_center/frontend/views/discovery.js";
import {
  beschreibung,
  entwurfZuRegel,
  leereBedingung,
  leereRegel,
  renderRuleOverview,
  renderRules,
  uebersichtAusKonfiguration,
} from "../../custom_components/notification_center/frontend/views/rules.js";
import {
  LEERER_FILTER,
  buildQuery,
  renderHistory,
  seitengroesse,
} from "../../custom_components/notification_center/frontend/views/history.js";

// Die vorhandenen Erwartungen sind deutsch formuliert; die Grundsprache der
// Oberflaeche ist Englisch. Beides wird geprueft: hier Deutsch, in
// i18n.test.js zusaetzlich Englisch und der Rueckfall.
before(() => setzeSprache("de"));

/** Aufbau wie eine Antwort von get_config, Werte frei erfunden. */
const ENTITIES = [
  {
    entity_id: "light.kueche_arbeitsplatte",
    name: "Licht Arbeitsplatte",
    area_name: "Küche",
    floor_name: "Erdgeschoss",
  },
  {
    entity_id: "binary_sensor.flur_haustuer",
    name: "Haustür",
    area_name: "Flur",
    floor_name: "Erdgeschoss",
  },
  {
    entity_id: "person.alex",
    name: "Alex",
    area_name: null,
    floor_name: null,
  },
];

const RULES = [
  {
    rule_id: "rule_1",
    entity_id: "light.kueche_arbeitsplatte",
    kind: "state_is",
    type: "info",
    states: ["off"],
  },
  {
    rule_id: "rule_2",
    entity_id: "binary_sensor.flur_haustuer",
    kind: "state_is",
    type: "alarm",
    states: ["on"],
  },
  {
    rule_id: "rule_3",
    entity_id: "person.alex",
    kind: "state_is",
    type: "info",
    states: ["home"],
  },
];

describe("Regeluebersicht", () => {
  it("gruppiert nach Geschoss und Raum (Issue 2)", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });

    assert.match(html, /Erdgeschoss/);
    assert.match(html, /Küche/);
    assert.match(html, /Flur/);
  });

  it("ordnet jede Regel unter ihre Entity ein", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });

    assert.match(html, /Licht Arbeitsplatte/);
    assert.match(html, /Haustür/);
  });

  it("stellt Entities ohne Raum ans Ende, statt sie zu verlieren", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });

    assert.match(html, /Ohne Geschoss/);
    assert.ok(
      html.indexOf("Erdgeschoss") < html.indexOf("Ohne Geschoss"),
      "Zugeordnete Geschosse stehen vor der Sammelgruppe"
    );
  });

  it("verliert keine Regel", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });
    const zeilen = html.match(/data-action="edit-rule"/g) || [];
    assert.equal(zeilen.length, RULES.length);
  });

  it("gibt jeder Regelzeile ihre Entity mit (Ticket 16)", () => {
    // Ohne diese Angabe fand der Editor aus der Uebersicht heraus nichts.
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });
    assert.match(html, /data-action="edit-rule" data-rule="rule_1" data-entity="light\./);
  });

  it("bietet genau einen Bearbeiten-Knopf je Regel (Ticket 16)", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });
    const knoepfe = html.match(/>Bearbeiten/g) || [];
    assert.equal(knoepfe.length, RULES.length);
  });

  it("meldet einen leeren Bestand verstaendlich", () => {
    const html = renderRuleOverview({ entities: [], rules: [] });
    assert.match(html, /Noch keine Regeln/);
  });

  it("kommt mit fehlender Platzierung zurecht", () => {
    const html = renderRuleOverview({ entities: [], rules: RULES });
    assert.match(html, /Ohne Geschoss/);
  });
});

describe("Uebergabe der Konfiguration an die Uebersicht", () => {
  /**
   * Aufgebaut wie eine Antwort von get_config, mit erfundenen Werten.
   *
   * Hier lag der Fehler: das Panel strich die Eintraege auf Kennung und Namen
   * zusammen, sodass Raum und Geschoss verschwanden, bevor sie die
   * Gruppierung erreichten. Der Test der Darstellung allein hat das nicht
   * gefangen, weil er die vollstaendigen Objekte direkt eingespeist hat.
   */
  const ANTWORT = {
    api_version: 1,
    version: "1.1.1",
    entities: [
      {
        entity_id: "light.kueche_arbeitsplatte",
        added_at: "2026-01-15T09:00:00+00:00",
        device_id: "dev_licht_1",
        area_id: "kueche",
        name: "Licht Arbeitsplatte",
        area_name: "Küche",
        floor_id: "erdgeschoss",
        floor_name: "Erdgeschoss",
      },
      {
        entity_id: "switch.netzwerkspeicher",
        added_at: "2026-01-16T14:30:00+00:00",
        device_id: null,
        area_id: null,
        name: "Netzwerkspeicher",
        area_name: null,
        floor_id: null,
        floor_name: null,
      },
    ],
    rules: [
      { rule_id: "rule_1", entity_id: "light.kueche_arbeitsplatte", kind: "state_is", type: "info", states: ["off"] },
      { rule_id: "rule_2", entity_id: "switch.netzwerkspeicher", kind: "state_is", type: "info", states: ["on"] },
    ],
    settings: {},
  };

  it("behaelt Raum und Geschoss", () => {
    const zustand = uebersichtAusKonfiguration(ANTWORT);
    const erste = zustand.entities[0];

    assert.equal(erste.area_name, "Küche");
    assert.equal(erste.floor_name, "Erdgeschoss");
  });

  it("fuehrt bis zur fertigen Gruppierung", () => {
    const html = renderRuleOverview(uebersichtAusKonfiguration(ANTWORT));

    assert.match(html, /Erdgeschoss/);
    assert.match(html, /Küche/);
    assert.match(html, /Ohne Geschoss/);
  });

  it("kommt mit einer leeren Antwort zurecht", () => {
    const zustand = uebersichtAusKonfiguration({});
    assert.deepEqual(zustand.entities, []);
    assert.deepEqual(zustand.rules, []);
  });
});

describe("Dashboard", () => {
  const AKTIVE = [
    {
      event_id: "a",
      type: "alarm",
      message: "Wasserleck im Keller",
      start_time: "2026-08-26T06:13:37.000+00:00",
      active: true,
      entity_id: "binary_sensor.leck",
    },
    {
      event_id: "b",
      type: "warning",
      message: "Arbeitslicht an",
      start_time: "2026-08-26T06:08:00.000+00:00",
      active: true,
      entity_id: null,
    },
  ];

  it("zeigt die Meldungen nach Kategorien", () => {
    const html = renderDashboard(
      { active: AKTIVE, counts: { events_today: 18 } },
      "de-DE"
    );

    assert.match(html, /Alarme/);
    assert.match(html, /Warnungen/);
    assert.match(html, /Wasserleck im Keller/);
    assert.match(html, /Arbeitslicht an/);
  });

  it("macht nur Meldungen mit Entity anklickbar (Spezifikation 71)", () => {
    const html = renderDashboard({ active: AKTIVE, counts: {} }, "de-DE");
    const klickbar = html.match(/class="row clickable"/g) || [];
    assert.equal(klickbar.length, 1);
  });

  it("nennt die heutigen Ereignisse", () => {
    const html = renderDashboard({ active: AKTIVE, counts: { events_today: 18 } }, "de-DE");
    assert.match(html, /18 Ereignisse heute/);
  });

  it("meldet Ruhe, wenn nichts aktiv ist", () => {
    const html = renderDashboard({ active: [], counts: { events_today: 0 } }, "de-DE");
    assert.match(html, /Alles ruhig/);
    assert.match(html, /0 Ereignisse heute/);
  });

  it("weist auf eine Pause hin", () => {
    const html = renderDashboard({ active: [], counts: {}, paused: true }, "de-DE");
    assert.match(html, /Pausiert/);
  });

  it("maskiert Meldungstexte", () => {
    const html = renderDashboard(
      {
        active: [
          {
            event_id: "x",
            type: "info",
            message: "<img src=x onerror=alert(1)>",
            start_time: "2026-08-26T06:00:00.000+00:00",
            active: true,
          },
        ],
        counts: {},
      },
      "de-DE"
    );

    assert.doesNotMatch(html, /<img/);
    assert.match(html, /&lt;img/);
  });
});

describe("Discovery", () => {
  const TREFFER = [
    {
      entity_id: "binary_sensor.fenster",
      name: "Fenster",
      domain: "binary_sensor",
      monitored: false,
      rule_count: 0,
      has_suggestions: true,
    },
  ];

  it("setzt Vorschlaege sichtbar ab (Ticket 15)", () => {
    const html = renderDiscovery({
      entities: TREFFER,
      suggestions: {
        "binary_sensor.fenster": [
          { key: "window_state", title: "Warnung bei offenem Fenster", reasons: [] },
        ],
      },
    });

    assert.match(html, /class="suggestions"/);
    assert.match(html, /Warnung bei offenem Fenster/);
  });

  it("beschriftet den Knopf nach Zustand (Ticket 12)", () => {
    const zu = renderDiscovery({ entities: TREFFER, suggestions: {} });
    assert.match(zu, />Vorschläge</);

    const auf = renderDiscovery({
      entities: TREFFER,
      suggestions: { "binary_sensor.fenster": [] },
    });
    assert.match(auf, />Vorschläge ausblenden</);
  });

  it("nennt keine Vorschlagszahl vor dem Laden (Ticket 2)", () => {
    const html = renderDiscovery({ entities: TREFFER, suggestions: {} });
    assert.match(html, /Vorschläge verfügbar/);
    assert.doesNotMatch(html, /0 Vorschläge/);
  });
});

describe("Formatierung", () => {
  it("fasst Dauern lesbar zusammen", () => {
    assert.equal(formatDuration(30), "30 s");
    assert.equal(formatDuration(720), "12 min");
    assert.equal(formatDuration(3600), "1 h");
    assert.equal(formatDuration(5400), "1 h 30 min");
    assert.equal(formatDuration(90000), "1 d 1 h");
  });

  it("uebersetzt die Typen", () => {
    assert.equal(typeLabel("alarm"), "Alarm");
    assert.equal(typeLabel("warning"), "Warnung");
  });

  it("maskiert alle gefaehrlichen Zeichen", () => {
    assert.equal(escapeHtml('<a href="x">&\'</a>'), "&lt;a href=&quot;x&quot;&gt;&amp;&#39;&lt;/a&gt;");
  });

  it("vertraegt fehlende Werte", () => {
    assert.equal(escapeHtml(null), "");
    assert.equal(escapeHtml(undefined), "");
  });
});

describe("Regel-Editor", () => {
  const EINE_REGEL = [{ rule_id: "rule_1", entity_id: "light.a", kind: "state_is", type: "info", states: ["off"] }];
  const ZWEI_REGELN = [
    ...EINE_REGEL,
    { rule_id: "rule_2", entity_id: "light.a", kind: "state_is", type: "alarm", states: ["on"] },
  ];

  const zustand = (rules, entwurf) => ({
    entityId: "light.a",
    entityName: "Licht A",
    rules,
    entwurf,
    states: ["on", "off"],
    attributes: [],
  });

  it("bietet ohne offenes Formular je Regel einen Bearbeiten-Knopf", () => {
    const html = renderRules(zustand(ZWEI_REGELN, null));
    assert.equal((html.match(/>Bearbeiten/g) || []).length, 2);
  });

  it("laesst den Knopf an der Regel weg, die gerade offen ist (Issue 3)", () => {
    // Der Anwender ist bereits in der Bearbeitung; der Knopf verwies auf
    // genau das, was schon vor ihm steht.
    const html = renderRules(zustand(EINE_REGEL, { ...EINE_REGEL[0] }));

    assert.doesNotMatch(html, />Bearbeiten/);
    assert.match(html, /wird bearbeitet/);
  });

  it("behaelt ihn an den uebrigen Regeln (Issue 3)", () => {
    const html = renderRules(zustand(ZWEI_REGELN, { ...ZWEI_REGELN[0] }));

    assert.equal((html.match(/>Bearbeiten/g) || []).length, 1);
    assert.match(html, /data-action="edit-rule" data-rule="rule_2"/);
  });

  it("laesst bei einer neuen Regel alle Knoepfe stehen", () => {
    // Ein Entwurf ohne rule_id gehoert zu keiner vorhandenen Zeile.
    const html = renderRules(zustand(ZWEI_REGELN, { entity_id: "light.a", kind: "state_is" }));
    assert.equal((html.match(/>Bearbeiten/g) || []).length, 2);
  });

  it("markiert in der Uebersicht nichts als in Bearbeitung", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });
    assert.doesNotMatch(html, /wird bearbeitet/);
  });
});

describe("Attribut als Wertquelle (Issue 14)", () => {
  // Ein Maehroboter mit einem Attribut, das ebenfalls "state" heisst: der
  // Zustand der Entity ist klein geschrieben, der Attributwert gross. Eine
  // Regel aus der Zustandsliste konnte deshalb nie zutreffen.
  const ATTRIBUTE = [
    { name: "state", kind: "text", value: "ERROR" },
    { name: "battery_level", kind: "numeric", value: 100 },
  ];

  const zustand = (entwurf) => ({
    entityId: "lawn_mower.rasen",
    entityName: "Rasen",
    rules: [],
    entwurf,
    states: ["mowing", "docked", "paused", "returning", "error"],
    attributes: ATTRIBUTE,
  });

  const entwurfMitAttribut = (states) => ({
    entity_id: "lawn_mower.rasen",
    kind: "state_is",
    type: "warning",
    states,
    value_source: { kind: "attribute", attribute: "state" },
  });

  it("bietet die Zustaende der Entity nicht an, wenn ein Attribut gewaehlt ist", () => {
    const html = renderRules(zustand(entwurfMitAttribut([])));

    assert.doesNotMatch(html, /<option value="mowing"/);
    assert.match(html, /data-rule-field="states"[^>]*type="text"|type="text"[^>]*data-rule-field="states"/);
  });

  it("zeigt den aktuellen Wert des Attributs", () => {
    const html = renderRules(zustand(entwurfMitAttribut([])));
    assert.match(html, /Aktueller Wert: ERROR/);
  });

  it("warnt, wenn sich der Wert nur in der Schreibweise unterscheidet", () => {
    const html = renderRules(zustand(entwurfMitAttribut(["error"])));
    assert.match(html, /Gross- und Kleinschreibung/);
  });

  it("schweigt, wenn die Schreibweise stimmt", () => {
    const html = renderRules(zustand(entwurfMitAttribut(["ERROR"])));

    assert.match(html, /Aktueller Wert: ERROR/);
    assert.doesNotMatch(html, /Gross- und Kleinschreibung/);
  });

  it("schweigt bei einem ganz anderen Wert", () => {
    // Ein Attribut kann Werte annehmen, die gerade nicht anliegen; davor
    // zu warnen waere falsch.
    const html = renderRules(zustand(entwurfMitAttribut(["OFFLINE"])));
    assert.doesNotMatch(html, /Gross- und Kleinschreibung/);
  });

  it("bietet die Zustandsliste weiterhin an, wenn der Zustand die Quelle ist", () => {
    const html = renderRules(
      zustand({
        entity_id: "lawn_mower.rasen",
        kind: "state_is",
        type: "warning",
        states: ["error"],
        value_source: { kind: "state", attribute: null },
      })
    );

    assert.match(html, /<option value="mowing"/);
    assert.doesNotMatch(html, /Aktueller Wert/);
  });
});

describe("Seitengroesse der Historie (Issue 5)", () => {
  const ZUSTAND = { events: [], total: 0, filter: { ...LEERER_FILTER }, areas: [] };

  it("bietet 50, 100 und 200 an", () => {
    const html = renderHistory(ZUSTAND, "de-DE");

    assert.match(html, /<option value="50"[^>]*>50 pro Seite/);
    assert.match(html, /<option value="100"[^>]*>100 pro Seite/);
    assert.match(html, /<option value="200"[^>]*>200 pro Seite/);
  });

  it("waehlt 100 als Standard vor", () => {
    const html = renderHistory(ZUSTAND, "de-DE");
    assert.match(html, /<option value="100" selected>/);
  });

  it("zeigt die getroffene Wahl wieder an", () => {
    const html = renderHistory({ ...ZUSTAND, filter: { ...LEERER_FILTER, limit: 200 } }, "de-DE");

    assert.match(html, /<option value="200" selected>/);
    assert.doesNotMatch(html, /<option value="100" selected>/);
  });

  it("fragt genau die gewaehlte Menge ab", () => {
    assert.equal(buildQuery({ ...LEERER_FILTER, limit: 200 }).limit, 200);
    assert.equal(buildQuery({ ...LEERER_FILTER }).limit, 100);
  });

  it("faellt bei einem unbekannten Wert auf den Standard zurueck", () => {
    // Ein Filter aus einer aelteren Fassung kennt das Feld nicht.
    assert.equal(seitengroesse({}), 100);
    assert.equal(seitengroesse({ limit: 37 }), 100);
  });

  it("blaettert von der gewaehlten Menge aus weiter", () => {
    const query = buildQuery({ ...LEERER_FILTER, limit: 200 }, 200);
    assert.equal(query.offset, 200);
    assert.equal(query.limit, 200);
  });
});

describe("Typauswahl der Discovery (Issue 4)", () => {
  it("bietet die Helfer an", () => {
    const html = renderDiscovery({ entities: [], suggestions: {} });

    assert.match(html, /<optgroup label="Helfer">/);
    for (const domaene of [
      "input_boolean",
      "input_number",
      "input_select",
      "input_text",
      "input_datetime",
      "counter",
      "timer",
      "schedule",
    ]) {
      assert.match(html, new RegExp(`value="${domaene}"`), `${domaene} fehlt`);
    }
  });

  it("behaelt Alle Typen als Voreinstellung", () => {
    const html = renderDiscovery({ entities: [], suggestions: {} });
    assert.match(html, /<option value="" selected>Alle Typen/);
  });

  it("merkt sich die getroffene Wahl", () => {
    const html = renderDiscovery({ entities: [], suggestions: {}, domain: "counter" });
    assert.match(html, /<option value="counter" selected>/);
  });
});

describe("Die Entity im Regel-Editor (Issue 9)", () => {
  const zustand = {
    entityId: "light.kueche_arbeitsplatte",
    entityName: "Licht Arbeitsplatte",
    rules: [],
    entwurf: null,
    states: [],
    attributes: [],
  };

  it("nennt die Entity-ID auf der Seite", () => {
    // Von hier aus laesst sich die Entity ersetzen; dafuer muss sichtbar
    // sein, welche gerade gemeint ist.
    const html = renderRules(zustand);
    assert.match(html, /light\.kueche_arbeitsplatte/);
  });

  it("setzt sie zurueckhaltend, nicht als Ueberschrift", () => {
    const html = renderRules(zustand);
    assert.match(
      html,
      /<div class="entity-meta"[^>]*>light\.kueche_arbeitsplatte<\/div>/
    );
    assert.match(html, /<h2>Regeln für Licht Arbeitsplatte<\/h2>/);
  });

  it("kommt ohne Anzeigenamen zurecht", () => {
    const html = renderRules({ ...zustand, entityName: "" });
    assert.match(html, /<h2>Regeln für light\./);
  });

  it("maskiert die Kennung", () => {
    const html = renderRules({ ...zustand, entityId: '<img src=x onerror=alert(1)>' });
    assert.doesNotMatch(html, /<img/);
  });
});

describe("Verknuepfte Bedingungen", () => {
  /** Fenster offen, waehrend die Heizung laeuft. */
  const VERKNUEPFT = {
    rule_id: "rule_1",
    entity_id: "binary_sensor.flur_haustuer",
    kind: "state_is",
    type: "warning",
    states: ["on"],
    value_source: { kind: "state", attribute: null },
    logic: "all",
    extra_conditions: [
      {
        entity_id: "climate.wohnzimmer",
        kind: "state_is",
        states: ["heat"],
        negate: false,
        value_source: { kind: "state", attribute: null },
      },
    ],
  };

  const NAMEN = { "climate.wohnzimmer": "Heizung Wohnzimmer" };

  it("beschreibt beide Bedingungen mit dem Verknuepfungswort", () => {
    const text = beschreibung(VERKNUEPFT, NAMEN);
    assert.match(text, /Zustand ist on und Heizung Wohnzimmer: Zustand ist heat/);
  });

  it("verwendet bei 'eine genuegt' das andere Wort", () => {
    const text = beschreibung({ ...VERKNUEPFT, logic: "any" }, NAMEN);
    assert.match(text, / oder Heizung Wohnzimmer/);
  });

  it("zeigt die Kennung, wenn kein Name bekannt ist", () => {
    const text = beschreibung(VERKNUEPFT);
    assert.match(text, /climate\.wohnzimmer: Zustand ist heat/);
  });

  it("klammert eine verneinte Bedingung", () => {
    // Ohne Klammer waere "nicht Zustand ist home" nicht zu lesen.
    const text = beschreibung(
      {
        ...VERKNUEPFT,
        extra_conditions: [
          {
            entity_id: "person.alex",
            kind: "state_is",
            states: ["home"],
            negate: true,
            value_source: { kind: "state", attribute: null },
          },
        ],
      },
      { "person.alex": "Alex" }
    );
    assert.match(text, /Alex: nicht \(Zustand ist home\)/);
  });

  it("beschreibt eine einzelne Bedingung unveraendert", () => {
    // Die Erweiterung darf an der bisherigen Darstellung nichts aendern.
    const einfach = { ...VERKNUEPFT, extra_conditions: [] };
    assert.equal(beschreibung(einfach), "Zustand ist on");
  });

  it("haengt die Zeitbedingung an die ganze Verknuepfung", () => {
    const text = beschreibung({ ...VERKNUEPFT, duration_seconds: 900 }, NAMEN);
    assert.match(text, /Zustand ist heat · länger als 15 min$/);
  });
});

describe("Regel-Editor: weitere Bedingungen", () => {
  const BASIS = {
    entityId: "binary_sensor.flur_haustuer",
    entityName: "Haustür",
    rules: [],
    states: ["on", "off"],
    attributes: [],
    candidates: [
      { entity_id: "climate.wohnzimmer", name: "Heizung Wohnzimmer" },
      { entity_id: "person.alex", name: "Alex" },
    ],
  };

  it("bietet eine neue Bedingung an, auch wenn es noch keine gibt", () => {
    const html = renderRules({ ...BASIS, entwurf: leereRegel(BASIS.entityId) });
    assert.match(html, /data-action="add-condition"/);
    // Die Verknuepfung erscheint erst, wenn es etwas zu verknuepfen gibt.
    assert.ok(!html.includes('data-rule-field="logic"'));
  });

  it("zeichnet eine Bedingung samt Entity-Feld, Verneinung und Vorschlagsliste", () => {
    const entwurf = {
      ...leereRegel(BASIS.entityId),
      extra_conditions: [{ ...leereBedingung(), entity_id: "climate.wohnzimmer" }],
    };
    const html = renderRules({
      ...BASIS,
      entwurf,
      conditionOptions: {
        "climate.wohnzimmer": { states: ["heat", "off"], attributes: [], exists: true },
      },
    });

    assert.match(html, /data-rule-field="logic"/);
    assert.match(html, /Alle Bedingungen müssen zutreffen/);
    assert.match(html, /data-cond-field="entity" data-cond-index="0"/);
    assert.match(html, /value="climate\.wohnzimmer"/);
    assert.match(html, /data-cond-field="negate"/);
    assert.match(html, /data-action="remove-condition" data-index="0"/);
    // Vorschlagsliste der Entities, einmal je Formular.
    assert.match(html, /<datalist id="nc-entity-liste">/);
    assert.match(html, /Heizung Wohnzimmer/);
    // Die Zustaende der *Partner*-Entity, nicht die der eigenen.
    assert.match(html, /<option value="heat"/);
  });

  it("nimmt fuer eine Bedingung ohne Kennung die Werte der eigenen Entity", () => {
    const entwurf = {
      ...leereRegel(BASIS.entityId),
      extra_conditions: [leereBedingung()],
    };
    const html = renderRules({ ...BASIS, entwurf });

    assert.match(html, /Diese Entity/);
    assert.match(html, /<option value="on"/);
  });

  it("laesst eine Flanke nicht verneinen", () => {
    const entwurf = {
      ...leereRegel(BASIS.entityId),
      extra_conditions: [{ ...leereBedingung(), kind: "state_changed_to" }],
    };
    const html = renderRules({ ...BASIS, entwurf });
    assert.ok(!html.includes('data-cond-field="negate"'));
  });

  it("weist auf eine unbekannte Kennung hin", () => {
    const entwurf = {
      ...leereRegel(BASIS.entityId),
      extra_conditions: [{ ...leereBedingung(), entity_id: "climate.gibtsnicht" }],
    };
    const html = renderRules({
      ...BASIS,
      entwurf,
      conditionOptions: {
        "climate.gibtsnicht": { states: [], attributes: [], exists: false },
      },
    });
    assert.match(html, /Keine Entity mit dieser Kennung/);
  });
});

describe("Uebergabe verknuepfter Bedingungen an die API", () => {
  it("reicht Verknuepfung und Bedingungen weiter", () => {
    const regel = entwurfZuRegel({
      ...leereRegel("binary_sensor.flur_haustuer"),
      states: ["on"],
      logic: "any",
      extra_conditions: [
        {
          ...leereBedingung(),
          entity_id: "climate.wohnzimmer",
          states: ["heat"],
          negate: true,
        },
      ],
    });

    assert.equal(regel.logic, "any");
    assert.equal(regel.extra_conditions.length, 1);
    assert.equal(regel.extra_conditions[0].entity_id, "climate.wohnzimmer");
    assert.deepEqual(regel.extra_conditions[0].states, ["heat"]);
    assert.equal(regel.extra_conditions[0].negate, true);
    // Die numerische Haelfte wird geleert, sonst weist das Backend ab.
    assert.equal(regel.extra_conditions[0].threshold, null);
    assert.equal(regel.extra_conditions[0].operator, null);
  });

  it("macht aus einer leeren Kennung 'diese Entity'", () => {
    const regel = entwurfZuRegel({
      ...leereRegel("sensor.temperatur"),
      states: ["on"],
      extra_conditions: [{ ...leereBedingung(), entity_id: "  " }],
    });
    assert.equal(regel.extra_conditions[0].entity_id, null);
  });

  it("raeumt die Zustandsliste einer numerischen Bedingung weg", () => {
    const regel = entwurfZuRegel({
      ...leereRegel("sensor.temperatur"),
      states: ["on"],
      extra_conditions: [
        { ...leereBedingung(), kind: "numeric", operator: "gte", threshold: "70", states: ["alt"] },
      ],
    });

    const bedingung = regel.extra_conditions[0];
    assert.equal(bedingung.threshold, 70);
    assert.equal(bedingung.operator, "gte");
    assert.deepEqual(bedingung.states, []);
  });

  it("verneint eine Flanke nie, auch wenn der Entwurf es behauptet", () => {
    const regel = entwurfZuRegel({
      ...leereRegel("sensor.temperatur"),
      states: ["on"],
      extra_conditions: [
        { ...leereBedingung(), kind: "state_changed_to", states: ["on"], negate: true },
      ],
    });
    assert.equal(regel.extra_conditions[0].negate, false);
  });

  it("laesst eine Regel ohne weitere Bedingungen schlank", () => {
    const regel = entwurfZuRegel({ ...leereRegel("sensor.temperatur"), states: ["on"] });
    assert.equal(regel.logic, "all");
    assert.deepEqual(regel.extra_conditions, []);
  });
});

describe("HA-Systemnachrichten in den Uebersichten", () => {
  const JETZT = new Date().toISOString();

  /** Eine uebernommene Meldung von Home Assistant: ohne Entity, ohne Regel. */
  const SYSTEM = {
    event_id: "ev_system",
    source: "ha_system",
    type: "warning",
    active: true,
    start_time: JETZT,
    message: "Fehlgeschlagener Anmeldeversuch",
    entity_id: null,
    area_id: null,
  };

  const AUS_REGEL = {
    event_id: "ev_regel",
    source: "entity_rule",
    type: "info",
    active: true,
    start_time: JETZT,
    message: "Licht Arbeitsplatte an",
    entity_id: "light.kueche_arbeitsplatte",
    area_id: "kueche",
  };

  const abzeichen = (html) => (html.match(/>HA</g) || []).length;

  it("kennzeichnet die Meldung im Dashboard", () => {
    const html = renderDashboard(
      { active: [SYSTEM, AUS_REGEL], counts: { events_today: 2 } },
      "de"
    );
    assert.equal(abzeichen(html), 1);
    assert.match(html, /Fehlgeschlagener Anmeldeversuch/);
  });

  it("kennzeichnet sie in der Historie", () => {
    const html = renderHistory(
      { events: [SYSTEM, AUS_REGEL], total: 2, filter: { ...LEERER_FILTER }, areas: [] },
      "de"
    );
    assert.equal(abzeichen(html), 1);
  });

  it("laesst sich in der Historie als Herkunft auswaehlen", () => {
    const html = renderHistory(
      { events: [], total: 0, filter: { ...LEERER_FILTER }, areas: [] },
      "de"
    );
    assert.match(html, /<option value="ha_system"/);
    assert.match(html, /Systemnachricht/);
  });

  it("nennt die ganze Herkunft im Titel", () => {
    // "HA" allein erklaert nichts; der ausgeschriebene Text liegt im Titel.
    assert.match(sourceBadge(SYSTEM), /title="Systemnachricht von Home Assistant"/);
  });

  it("beschriftet nur, was der Erklaerung bedarf", () => {
    // Regeln und Automationen sind das Erwartbare und bleiben unbeschriftet.
    assert.equal(sourceBadge(AUS_REGEL), "");
    assert.equal(sourceBadge({ source: "automation" }), "");
    assert.equal(sourceBadge(undefined), "");
  });

  it("bietet keinen Klick an, wo keine Entity verknuepft ist", () => {
    const html = renderDashboard({ active: [SYSTEM], counts: {} }, "de");
    assert.ok(!html.includes("clickable"));
  });
});
