/**
 * Zugriff auf die Backend-API.
 *
 * Hier steht keine Geschaeftslogik, nur der Aufruf der WebSocket-Kommandos
 * (Spezifikation 50). Auch das Filtern und Blaettern der Historie geschieht
 * im Backend; das Frontend reicht die Parameter nur durch.
 */

const PREFIX = "notification_center";

/** Version der API, gegen die dieses Frontend gebaut ist. */
export const EXPECTED_API_VERSION = 1;

/**
 * Die Version dieses Frontends, abgelesen am eigenen Pfad.
 *
 * Die Dateien werden unter `/notification_center_frontend/<version>/`
 * ausgeliefert. Damit kennt jedes Modul seine Version, ohne dass sie im Code
 * gepflegt werden muss und dort veralten koennte.
 */
export const FRONTEND_VERSION = (() => {
  const treffer = /notification_center_frontend\/([^/]+)\//.exec(import.meta.url);
  return treffer ? treffer[1] : null;
})();

/** Wird gesetzt, sobald Backend und Frontend auseinanderlaufen. */
export const versionsKonflikt = { erkannt: false, backend: null };

/** Ruft ein Kommando auf und prueft dabei die API-Version. */
async function call(hass, type, payload = {}) {
  const result = await hass.connection.sendMessagePromise({
    type: `${PREFIX}/${type}`,
    ...payload,
  });
  checkVersion(result);
  return result;
}

function checkVersion(result) {
  if (!result) return;

  if (result.api_version && result.api_version > EXPECTED_API_VERSION) {
    // Kein Abbruch: die Felder, die dieses Frontend kennt, bleiben gueltig.
    console.warn(
      `[notification-center] Backend spricht API-Version ${result.api_version}, ` +
        `dieses Frontend kennt ${EXPECTED_API_VERSION}. Bitte die Seite neu laden.`
    );
  }

  // Ein aus dem Zwischenspeicher geladenes Frontend wuerde sonst still
  // Falsches anzeigen. Sichtbar melden ist besser als leer bleiben.
  if (result.version && FRONTEND_VERSION && result.version !== FRONTEND_VERSION) {
    versionsKonflikt.erkannt = true;
    versionsKonflikt.backend = result.version;
  }
}

export const api = {
  getActive: (hass) => call(hass, "get_active"),
  getCounts: (hass) => call(hass, "get_counts"),
  getConfig: (hass) => call(hass, "get_config"),
  getHistory: (hass, query) => call(hass, "get_history", query),
  discover: (hass, query) => call(hass, "discover", query),
  getSuggestions: (hass, entityId) => call(hass, "get_suggestions", { entity_id: entityId }),
  getDevice: (hass, deviceId) => call(hass, "get_device", { device_id: deviceId }),
  addEntities: (hass, entityIds) => call(hass, "add_entities", { entity_ids: entityIds }),
  removeEntity: (hass, entityId) => call(hass, "remove_entity", { entity_id: entityId }),
  replaceEntity: (hass, oldId, newId) =>
    call(hass, "replace_entity", { old_entity_id: oldId, new_entity_id: newId }),
  saveRule: (hass, rule) => call(hass, "save_rule", { rule }),
  deleteRule: (hass, ruleId) => call(hass, "delete_rule", { rule_id: ruleId }),
  saveGroup: (hass, group) => call(hass, "save_group", { group }),
  setSettings: (hass, settings) => call(hass, "set_settings", settings),
  deleteEvent: (hass, eventId) => call(hass, "delete_event", { event_id: eventId }),
  clearHistory: (hass) => call(hass, "clear_history"),

  /**
   * Abonniert Aenderungen an aktiven Notifications und Zaehlern.
   *
   * Liefert eine Funktion zum Abbestellen. Das Panel fragt nichts periodisch
   * nach (Spezifikation 45).
   *
   * Wichtig: ``subscribeMessage`` reicht nur die *Folgeereignisse* durch, nicht
   * die erste Antwort des Abonnements. Ohne den zusaetzlichen Abruf bliebe die
   * Anzeige leer, bis sich zufaellig etwas aendert.
   */
  subscribeUpdates: async (hass, onUpdate) => {
    // Erst abonnieren, dann den Anfangszustand holen: andersherum koennte
    // eine Aenderung im Zeitraum dazwischen verlorengehen.
    const abbestellen = await hass.connection.subscribeMessage(
      (message) => {
        checkVersion(message);
        onUpdate(message);
      },
      { type: `${PREFIX}/subscribe_updates` }
    );

    onUpdate(await call(hass, "get_active"));
    return abbestellen;
  },
};
