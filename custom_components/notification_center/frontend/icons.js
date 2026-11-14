/**
 * Die wenigen Symbole des Panels, als eingebettetes SVG.
 *
 * Bewusst keine Symbolschrift und keine Bibliothek: das Panel bleibt
 * buildfrei, und die Handvoll Zeichen, die es braucht, rechtfertigt keine
 * Abhaengigkeit. Alle folgen ``currentColor`` und sind fuer Vorleser
 * unsichtbar -- die Bedeutung steht immer zusaetzlich als Text daneben.
 */

const PFADE = {
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path>',
  // Jede Dringlichkeit hat ihre eigene Form, nicht nur ihre eigene Farbe:
  // Warnleuchte, Dreieck, Kreis. Wer Farben schlecht unterscheidet oder die
  // Kachel nur im Augenwinkel sieht, erkennt sie am Umriss.
  alarm: '<path d="M5 20h14"></path><path d="M7 20v-6a5 5 0 0 1 10 0v6"></path><path d="M12 3v2"></path><path d="M4.6 6.6 6 8"></path><path d="M19.4 6.6 18 8"></path>',
  warning: '<path d="M12 4 3 20h18L12 4z"></path><path d="M12 10v4"></path><path d="M12 17.4v.2"></path>',
  info: '<circle cx="12" cy="12" r="9"></circle><path d="M12 11v5.5"></path><path d="M12 7.4v.2"></path>',
  close: '<path d="M6 6l12 12"></path><path d="M18 6 6 18"></path>',
  chevron: '<path d="m6 9 6 6 6-6"></path>',
  search: '<circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path>',
  arrow: '<path d="M5 12h14"></path><path d="m13 6 6 6-6 6"></path>',
  timer: '<circle cx="12" cy="13" r="8"></circle><path d="M12 9v4l2.5 2"></path><path d="M9 2h6"></path>',
};

/** Ein Symbol als SVG-Text. Unbekannte Namen ergeben nichts. */
export function icon(name, size = 20) {
  const pfad = PFADE[name];
  if (!pfad) return "";
  return (
    `<svg class="${name === "chevron" ? "chevron" : "icon"}" aria-hidden="true" ` +
    `width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
    `stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${pfad}</svg>`
  );
}
