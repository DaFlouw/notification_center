/**
 * Tests der Uebersetzungsschicht.
 *
 * Geprueft wird die Mechanik -- Sprachwahl, Rueckfall, Zahlformen,
 * Platzhalter -- und die Vollstaendigkeit der Woerterbuecher. Die einzelnen
 * Formulierungen sind nicht Gegenstand der Tests: sie aendern sich, ohne dass
 * etwas kaputt ist.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  GRUNDSPRACHE,
  SPRACHEN,
  passendeSprache,
  setzeSprache,
  sprache,
  t,
  waehleSprache,
} from "../../custom_components/notification_center/frontend/i18n.js";
import { categoryLabel, typeLabel } from "../../custom_components/notification_center/frontend/format.js";
import { renderDashboard } from "../../custom_components/notification_center/frontend/views/dashboard.js";

describe("Sprachwahl", () => {
  it("nimmt die Sprache, die Home Assistant fuer den Anwender meldet", () => {
    assert.equal(waehleSprache({ locale: { language: "de" } }), "de");
    assert.equal(sprache(), "de");
  });

  it("faellt von einer regionalen Variante auf die Grundform zurueck", () => {
    assert.equal(passendeSprache("de-CH"), "de");
    assert.equal(passendeSprache("EN-GB"), "en");
  });

  it("faellt bei unbekannter Sprache auf Englisch zurueck", () => {
    assert.equal(passendeSprache("fr"), GRUNDSPRACHE);
    assert.equal(waehleSprache({ locale: { language: "sv" } }), "en");
  });

  it("kommt ohne hass aus", () => {
    assert.ok(SPRACHEN[waehleSprache(undefined)]);
  });
});

describe("Texte", () => {
  it("uebersetzt in die gewaehlte Sprache", () => {
    setzeSprache("de");
    assert.equal(t("common.save"), "Speichern");
    setzeSprache("en");
    assert.equal(t("common.save"), "Save");
  });

  it("setzt Platzhalter ein", () => {
    setzeSprache("en");
    assert.equal(t("history.shownOfTotal", { shown: 20, total: 80 }), "20 of 80");
  });

  it("laesst unbekannte Platzhalter stehen", () => {
    setzeSprache("en");
    // Der Meldungstext im Regeleditor zeigt die Platzhalter der Vorlage; sie
    // duerfen nicht als fehlende Parameter verschwinden.
    assert.match(t("rules.messagePlaceholder"), /\{name\}/);
  });

  it("waehlt die Zahlform nach count", () => {
    setzeSprache("en");
    assert.equal(t("events.today", { count: 1 }), "1 event today");
    assert.equal(t("events.today", { count: 4 }), "4 events today");
    setzeSprache("de");
    assert.equal(t("events.today", { count: 1 }), "1 Ereignis heute");
    assert.equal(t("events.today", { count: 4 }), "4 Ereignisse heute");
  });

  it("zeigt den Schluessel, wenn es ihn nirgends gibt", () => {
    setzeSprache("de");
    assert.equal(t("gibt.es.nicht"), "gibt.es.nicht");
  });

  it("faellt bei einer Luecke in der Uebersetzung auf Englisch zurueck", () => {
    // Eine Sprache darf unvollstaendig sein; leer bleiben darf nichts.
    SPRACHEN.xx = { "common.save": "Spara" };
    setzeSprache("xx");
    assert.equal(t("common.save"), "Spara");
    assert.equal(t("common.cancel"), SPRACHEN.en["common.cancel"]);
    delete SPRACHEN.xx;
    setzeSprache("en");
  });
});

describe("Woerterbuecher", () => {
  it("kennen keine Schluessel, die Englisch nicht hat", () => {
    for (const [code, woerterbuch] of Object.entries(SPRACHEN)) {
      if (code === GRUNDSPRACHE) continue;
      const unbekannt = Object.keys(woerterbuch).filter((key) => !(key in SPRACHEN[GRUNDSPRACHE]));
      assert.deepEqual(unbekannt, [], `${code}: unbekannte Schluessel`);
    }
  });

  it("uebersetzen jeden Schluessel der Grundsprache", () => {
    // Fehlende Schluessel sind zwar erlaubt -- sie fallen auf Englisch
    // zurueck -- aber fuer die mitgelieferten Sprachen soll nichts fehlen.
    for (const [code, woerterbuch] of Object.entries(SPRACHEN)) {
      const fehlend = Object.keys(SPRACHEN[GRUNDSPRACHE]).filter((key) => !(key in woerterbuch));
      assert.deepEqual(fehlend, [], `${code}: fehlende Schluessel`);
    }
  });

  it("haben zu jeder Zahlform beide Varianten", () => {
    for (const [code, woerterbuch] of Object.entries(SPRACHEN)) {
      for (const key of Object.keys(woerterbuch)) {
        if (!key.endsWith("_one")) continue;
        const andere = `${key.slice(0, -4)}_other`;
        assert.ok(andere in woerterbuch, `${code}: ${andere} fehlt`);
      }
    }
  });
});

describe("Ansichten folgen der Sprache", () => {
  const zustand = {
    active: [
      {
        event_id: "ev_1",
        type: "alarm",
        message: "Wasser in der Waschküche",
        start_time: new Date().toISOString(),
        active: true,
        entity_id: "binary_sensor.leck",
      },
    ],
    counts: { events_today: 3 },
  };

  it("zeichnet das Dashboard englisch", () => {
    setzeSprache("en");
    const html = renderDashboard(zustand, "en");
    assert.match(html, /Alarms/);
    assert.match(html, /3 events today/);
    assert.match(html, /History/);
    // Die Meldung selbst kommt aus der Regel und bleibt, wie sie ist.
    assert.match(html, /Wasser in der Waschküche/);
  });

  it("zeichnet dasselbe Dashboard deutsch", () => {
    setzeSprache("de");
    const html = renderDashboard(zustand, "de");
    assert.match(html, /Alarme/);
    assert.match(html, /3 Ereignisse heute/);
    assert.match(html, /Historie/);
  });

  it("uebersetzt Typ- und Kategoriebezeichnungen", () => {
    setzeSprache("en");
    assert.equal(typeLabel("warning"), "Warning");
    assert.equal(categoryLabel("warning"), "Warnings");
    setzeSprache("de");
    assert.equal(typeLabel("warning"), "Warnung");
    assert.equal(categoryLabel("warning"), "Warnungen");
    // Unbekanntes bleibt unveraendert.
    assert.equal(typeLabel("sonstiges"), "sonstiges");
  });
});
