/**
 * Erzeugt die beiden Tabellen in ``docs/UI-KONZEPT.md`` aus ``konzept.js``.
 *
 *     node tests/panel/konzept-doku.js          schreibt sie neu
 *
 * ``tabellen()`` liefert denselben Text ohne zu schreiben; der Test
 * ``tests/frontend/konzept.test.js`` vergleicht damit, ob das Dokument auf
 * dem Stand ist.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { MASSE, PALETTE } from "./konzept.js";

export const DOKUMENT = fileURLToPath(new URL("../../docs/UI-KONZEPT.md", import.meta.url));

const SEITEN = {
  dashboard: "Dashboard",
  history: "Historie",
  rules: "Regeln",
  discovery: "Discovery",
  vorschlag: "Discovery, Vorschlag offen",
  editor: "Regel-Editor",
};

export function tabellen() {
  const palette = [
    "| Name | Hell | Dunkel | Wofür |",
    "| --- | --- | --- | --- |",
    ...Object.entries(PALETTE).map(
      ([name, [hell, dunkel, wofuer]]) => `| \`${name}\` | \`${hell}\` | \`${dunkel}\` | ${wofuer} |`
    ),
  ].join("\n");

  const masse = [
    "| Nr. | Ansicht | Was | Soll |",
    "| --- | --- | --- | --- |",
    ...MASSE.map(
      (punkt) =>
        `| ${punkt.id} | ${SEITEN[punkt.seite]} | ${punkt.was} | ${Object.entries(punkt.soll)
          .map(([eigenschaft, wert]) => `${eigenschaft}: \`${wert}\``)
          .join(" · ")} |`
    ),
  ].join("\n");

  return { PALETTE: palette, MASSE: masse };
}

/** Setzt die Tabellen zwischen ihre Marken. */
export function einsetzen(text) {
  let ergebnis = text;
  for (const [name, tabelle] of Object.entries(tabellen())) {
    const anfang = `<!-- ${name}:ANFANG -->`;
    const ende = `<!-- ${name}:ENDE -->`;
    const a = ergebnis.indexOf(anfang);
    const b = ergebnis.indexOf(ende);
    if (a < 0 || b < a) throw new Error(`Marken fuer ${name} fehlen im Konzept`);
    ergebnis = `${ergebnis.slice(0, a + anfang.length)}\n${tabelle}\n${ergebnis.slice(b)}`;
  }
  return ergebnis;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  writeFileSync(DOKUMENT, einsetzen(readFileSync(DOKUMENT, "utf-8")));
  console.log("docs/UI-KONZEPT.md aktualisiert");
}
