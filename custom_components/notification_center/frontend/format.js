/**
 * Darstellung von Zeiten und Dauern.
 *
 * Gespeichert wird in UTC, angezeigt in der Zeitzone des Browsers, die
 * Home Assistant an die Oberflaeche durchreicht (Spezifikation 36).
 */

const TYPE_LABELS = {
  info: "Info",
  warning: "Warnung",
  alarm: "Alarm",
};

const CATEGORY_LABELS = {
  alarm: "Alarme",
  warning: "Warnungen",
  info: "Infos",
};

export function typeLabel(type) {
  return TYPE_LABELS[type] || type;
}

export function categoryLabel(type) {
  return CATEGORY_LABELS[type] || type;
}

/** Uhrzeit eines Ereignisses, etwa "14:30". */
export function formatTime(iso, locale) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Zeitpunkt mit Datum, sobald er nicht von heute ist. */
export function formatDateTime(iso, locale) {
  if (!iso) return "";
  const date = new Date(iso);
  const heute = new Date();
  const gleicherTag =
    date.getFullYear() === heute.getFullYear() &&
    date.getMonth() === heute.getMonth() &&
    date.getDate() === heute.getDate();

  if (gleicherTag) return formatTime(iso, locale);

  return date.toLocaleString(locale, {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Dauer in Sekunden als lesbare Angabe.
 *
 * Aktive Ereignisse tragen keine feste Dauer; sie werden als "aktiv"
 * gekennzeichnet (Spezifikation 33).
 */
export function formatDuration(seconds) {
  const wert = Math.max(0, Math.round(seconds || 0));

  if (wert < 60) return `${wert} s`;
  if (wert < 3600) return `${Math.round(wert / 60)} min`;

  const stunden = Math.floor(wert / 3600);
  const minuten = Math.round((wert % 3600) / 60);
  if (stunden < 24) return minuten ? `${stunden} h ${minuten} min` : `${stunden} h`;

  const tage = Math.floor(stunden / 24);
  const rest = stunden % 24;
  return rest ? `${tage} d ${rest} h` : `${tage} d`;
}

/** Dauer eines Ereignisses, lebendig fuer aktive (Spezifikation 33). */
export function eventDuration(event) {
  if (event.active) {
    const laufend = (Date.now() - new Date(event.start_time).getTime()) / 1000;
    return formatDuration(laufend);
  }
  return formatDuration(event.duration);
}

/** Schuetzt vor HTML-Einschleusung aus Meldungstexten. */
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
