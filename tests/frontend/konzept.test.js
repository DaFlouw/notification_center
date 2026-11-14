/**
 * Haelt Konzept und Umsetzung beieinander.
 *
 * Drei Stellen nennen die Farben des Panels: ``docs/UI-KONZEPT.md`` fuer den
 * Menschen, ``tests/panel/konzept.js`` fuer die Tests und ``styles.js`` fuer
 * den Browser. Dieser Test laeuft ohne Browser und stellt sicher, dass sie
 * dasselbe sagen. Was am gezeichneten Element ankommt, messen die Faelle H1
 * ff. des Pruefstands nach.
 *
 * Anlass: die Umsetzung von 1.5.0 wich sichtbar vom Entwurf ab -- anderes
 * Blau, graue statt kuehle Flaechen --, und kein Test hat es gemerkt.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { MASSE, PALETTE, alsRgb, farbe } from "../panel/konzept.js";
import { DOKUMENT, einsetzen } from "../panel/konzept-doku.js";

const lies = (pfad) => readFileSync(fileURLToPath(new URL(pfad, import.meta.url)), "utf-8");

const FRONTEND = "../../custom_components/notification_center/frontend/";
const STYLES = lies(`${FRONTEND}styles.js`);

/** Die Variablen eines Blocks, ``:host`` oder ``:host([dark])``. */
function variablen(kopf) {
  const anfang = STYLES.indexOf(`${kopf} {`);
  assert.ok(anfang >= 0, `Block ${kopf} fehlt in styles.js`);
  const block = STYLES.slice(anfang, STYLES.indexOf("\n  }", anfang));
  return Object.fromEntries(
    [...block.matchAll(/--nc-([a-z-]+):\s*([^;]+);/g)].map((treffer) => [treffer[1], treffer[2].trim()])
  );
}

const HELL = variablen("  :host");
const DUNKEL = variablen("  :host([dark])");

describe("Konzept: Palette", () => {
  it("steht hell genau so im Stylesheet", () => {
    for (const name of Object.keys(PALETTE)) {
      assert.equal(HELL[name], farbe(name), `--nc-${name} (hell)`);
    }
  });

  it("steht dunkel genau so im Stylesheet", () => {
    for (const name of Object.keys(PALETTE)) {
      // Was dunkel nicht eigens gesetzt ist, gilt wie hell.
      assert.equal(DUNKEL[name] ?? HELL[name], farbe(name, true), `--nc-${name} (dunkel)`);
    }
  });

  it("kennt jede Farbe, die das Stylesheet festlegt", () => {
    const farben = Object.entries(HELL).filter(([, wert]) => wert.startsWith("#"));
    for (const [name] of farben) {
      // ``accent-strong`` ist ein alter Name fuer ``accent``.
      if (name === "accent-strong") continue;
      assert.ok(PALETTE[name], `--nc-${name} steht im Stylesheet, aber nicht im Konzept`);
    }
  });

  it("setzt dunkel nichts, was es hell nicht gibt", () => {
    for (const name of Object.keys(DUNKEL)) {
      assert.ok(name in HELL, `--nc-${name} gibt es nur dunkel`);
    }
  });

  it("haengt an keiner Farbe des Themes", () => {
    // Nur hell oder dunkel kommt von Home Assistant. Eine Theme-Variable im
    // Stylesheet wuerde die Palette wieder dem Zufall ueberlassen.
    for (const variable of [
      "--primary-color",
      "--card-background-color",
      "--primary-background-color",
      "--primary-text-color",
      "--secondary-text-color",
      "--divider-color",
      "--error-color",
      "--warning-color",
      "--info-color",
      "--success-color",
    ]) {
      assert.ok(!STYLES.includes(`var(${variable}`), `${variable} wird noch verwendet`);
    }
    assert.ok(!STYLES.includes("color-mix("), "es wird noch gemischt statt festgelegt");
  });

  it("benutzt nur Variablen, die es gibt", () => {
    const erlaubt = new Set([...Object.keys(HELL), "radius", "radius-row"]);
    for (const [, name] of STYLES.matchAll(/var\(--nc-([a-z-]+)/g)) {
      assert.ok(erlaubt.has(name), `var(--nc-${name}) ist nirgends festgelegt`);
    }
  });

  it("setzt das Attribut fuer den Dunkelmodus aus dem Theme", () => {
    const panel = lies(`${FRONTEND}notification-center-panel.js`);
    assert.match(panel, /toggleAttribute\("dark", Boolean\(hass\?\.themes\?\.darkMode\)\)/);
  });
});

describe("Konzept: Messpunkte", () => {
  it("haben eindeutige, lueckenlose Nummern", () => {
    assert.deepEqual(
      MASSE.map((punkt) => punkt.id),
      MASSE.map((_, stelle) => `H${stelle + 1}`)
    );
  });

  it("nennen nur Farben aus der Palette", () => {
    for (const punkt of MASSE) {
      for (const [eigenschaft, wert] of Object.entries(punkt.soll)) {
        if (eigenschaft.endsWith("-style")) continue;
        if (!/^[a-z-]+$/.test(wert)) continue;
        assert.ok(PALETTE[wert], `${punkt.id}: ${eigenschaft} nennt die unbekannte Farbe ${wert}`);
      }
    }
  });

  it("zeigen auf Klassen, die das Stylesheet kennt", () => {
    for (const punkt of MASSE) {
      for (const [, klasse] of punkt.auswahl.matchAll(/\.([a-z][a-z-]*)/g)) {
        assert.ok(
          STYLES.includes(`.${klasse}`),
          `${punkt.id}: die Klasse .${klasse} kommt im Stylesheet nicht vor`
        );
      }
    }
  });

  it("rechnen Farben so um, wie der Browser sie nennt", () => {
    assert.equal(alsRgb("#0277bd"), "rgb(2, 119, 189)");
    assert.equal(alsRgb("#ffffff"), "rgb(255, 255, 255)");
  });
});

describe("Konzept: Dokument", () => {
  it("traegt die Tabellen auf dem Stand von konzept.js", () => {
    const text = readFileSync(DOKUMENT, "utf-8");
    assert.equal(
      text,
      einsetzen(text),
      "docs/UI-KONZEPT.md ist veraltet -- node tests/panel/konzept-doku.js"
    );
  });
});
