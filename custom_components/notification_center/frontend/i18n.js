/**
 * Uebersetzung der Oberflaeche.
 *
 * Grundsprache ist Englisch: sie liefert den vollstaendigen Satz Schluessel
 * und faengt jede Luecke einer Uebersetzung auf. Gewaehlt wird die Sprache,
 * die Home Assistant fuer den angemeldeten Anwender meldet.
 *
 * Eine weitere Sprache hinzufuegen:
 *
 *   1. ``translations/<code>.js`` anlegen, am besten als Kopie von ``en.js``,
 *      und die Werte uebersetzen. Fehlende Schluessel sind erlaubt.
 *   2. Die Datei hier importieren und in ``SPRACHEN`` eintragen.
 *
 * Mehr ist nicht noetig: die Tests pruefen selbst, dass keine Sprache
 * unbekannte Schluessel mitbringt.
 */

import de from "./translations/de.js";
import en from "./translations/en.js";
import es from "./translations/es.js";

/** Alle mitgelieferten Sprachen. Der Schluessel ist der ISO-Code. */
export const SPRACHEN = { en, de, es };

export const GRUNDSPRACHE = "en";

let aktuelleSprache = GRUNDSPRACHE;

/**
 * Bestimmt die Sprache aus dem, was Home Assistant durchreicht.
 *
 * ``hass.locale.language`` ist die Spracheinstellung des Anwenders, nicht die
 * des Servers; beide koennen sich unterscheiden. Regionale Varianten wie
 * ``de-CH`` fallen auf ``de`` zurueck, eine unbekannte Sprache auf Englisch.
 */
export function waehleSprache(hass) {
  const gemeldet = hass?.locale?.language || hass?.language || navigator?.language || "";
  aktuelleSprache = passendeSprache(gemeldet);
  return aktuelleSprache;
}

export function passendeSprache(code) {
  const wert = String(code || "").toLowerCase();
  if (SPRACHEN[wert]) return wert;

  const basis = wert.split("-")[0];
  return SPRACHEN[basis] ? basis : GRUNDSPRACHE;
}

export function sprache() {
  return aktuelleSprache;
}

/** Nur fuer Tests und die Vorschau ohne Home Assistant. */
export function setzeSprache(code) {
  aktuelleSprache = passendeSprache(code);
  return aktuelleSprache;
}

/**
 * Der uebersetzte Text zu einem Schluessel.
 *
 * ``params.count`` waehlt zusaetzlich die Zahlform: zu ``events`` gehoeren
 * dann ``events_one`` und ``events_other``. Platzhalter stehen in geschweiften
 * Klammern und werden aus ``params`` ersetzt.
 *
 * Fehlt ein Schluessel in der gewaehlten Sprache, greift Englisch; fehlt er
 * auch dort, erscheint der Schluessel selbst. Das ist haesslich und genau
 * deshalb richtig: eine Luecke soll auffallen, nicht stillschweigend leer
 * bleiben.
 */
export function t(key, params = {}) {
  const vorlage = suche(key, params) ?? key;
  return einsetzen(vorlage, params);
}

function suche(key, params) {
  const kandidaten =
    params.count === undefined
      ? [key]
      : [`${key}_${params.count === 1 ? "one" : "other"}`, key];

  for (const woerterbuch of [SPRACHEN[aktuelleSprache], SPRACHEN[GRUNDSPRACHE]]) {
    if (!woerterbuch) continue;
    for (const kandidat of kandidaten) {
      if (typeof woerterbuch[kandidat] === "string") return woerterbuch[kandidat];
    }
  }
  return null;
}

function einsetzen(vorlage, params) {
  return String(vorlage).replace(/\{(\w+)\}/g, (treffer, name) =>
    params[name] === undefined ? treffer : String(params[name])
  );
}
