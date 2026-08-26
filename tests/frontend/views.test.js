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
import { describe, it } from "node:test";

import { escapeHtml, formatDuration, typeLabel } from "../../custom_components/notification_center/frontend/format.js";
import { renderDashboard } from "../../custom_components/notification_center/frontend/views/dashboard.js";
import { renderDiscovery } from "../../custom_components/notification_center/frontend/views/discovery.js";
import { renderRuleOverview } from "../../custom_components/notification_center/frontend/views/rules.js";

/** Nachgebildet aus einer echten Antwort von get_config. */
const ENTITIES = [
  {
    entity_id: "light.knx_interface_arbeiten_licht_fenster",
    name: "Arbeiten Licht Fenster",
    area_name: "Arbeiten",
    floor_name: "Erdgeschoss",
  },
  {
    entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung",
    name: "FlurEG Sensor Bewegung",
    area_name: "Flur EG",
    floor_name: "Erdgeschoss",
  },
  {
    entity_id: "person.florian_witt",
    name: "Florian Witt",
    area_name: null,
    floor_name: null,
  },
];

const RULES = [
  {
    rule_id: "rule_1",
    entity_id: "light.knx_interface_arbeiten_licht_fenster",
    kind: "state_is",
    type: "info",
    states: ["off"],
  },
  {
    rule_id: "rule_2",
    entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung",
    kind: "state_is",
    type: "alarm",
    states: ["on"],
  },
  {
    rule_id: "rule_3",
    entity_id: "person.florian_witt",
    kind: "state_is",
    type: "info",
    states: ["home"],
  },
];

describe("Regeluebersicht", () => {
  it("gruppiert nach Geschoss und Raum (Issue 2)", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });

    assert.match(html, /Erdgeschoss/);
    assert.match(html, /Arbeiten/);
    assert.match(html, /Flur EG/);
  });

  it("ordnet jede Regel unter ihre Entity ein", () => {
    const html = renderRuleOverview({ entities: ENTITIES, rules: RULES });

    assert.match(html, /Arbeiten Licht Fenster/);
    assert.match(html, /FlurEG Sensor Bewegung/);
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
