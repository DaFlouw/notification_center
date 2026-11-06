/**
 * Maskieren von Text, der in HTML landet.
 *
 * Eigenes Modul, damit sowohl die Darstellungshilfen (``format.js``) als auch
 * die Uebersetzungsschicht (``i18n.js``) darauf zugreifen koennen, ohne sich
 * gegenseitig zu importieren.
 *
 * Die Regel der Oberflaeche: alles, was nicht aus einem Woerterbuch stammt,
 * wird maskiert. Werte aus dem Backend, Entity-Kennungen, Fehlertexte und
 * Eingaben des Anwenders fallen darunter -- auch dann, wenn sie harmlos
 * aussehen. Markup entsteht ausschliesslich dort, wo es im Quelltext steht,
 * und wird mit :func:`raw` ausdruecklich als solches gekennzeichnet.
 */

/** Marke fuer Zeichenketten, die absichtlich Markup sind. */
const ROH = Symbol("notification-center-roh");

export function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (zeichen) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[zeichen]
  );
}

/**
 * Kennzeichnet fertiges Markup, das nicht maskiert werden soll.
 *
 * Gebraucht fuer die wenigen Faelle, in denen ein Platzhalter eines
 * Uebersetzungstexts eine Schaltflaeche oder einen Verweis aufnimmt. Nur fuer
 * Markup aus dem eigenen Quelltext -- niemals fuer etwas, das aus dem
 * Backend, aus Home Assistant oder aus einer Eingabe kommt.
 */
export function raw(html) {
  return { [ROH]: String(html) };
}

export function istRoh(wert) {
  return Boolean(wert) && typeof wert === "object" && ROH in wert;
}

/** Ein Wert, wie er in HTML eingesetzt werden darf. */
export function alsHtml(wert) {
  return istRoh(wert) ? wert[ROH] : escapeHtml(wert);
}
