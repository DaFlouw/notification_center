/**
 * Beispieldaten fuer den Pruefstand und die Bilder der Dokumentation.
 *
 * Frei erfunden. Die Struktur entspricht genau dem, was die WebSocket-API
 * liefert -- die Werte gehoeren zu keiner echten Anlage. Das ist Absicht:
 * Testdaten und Screenshots eines oeffentlichen Repositories sollen keine
 * Entity-Kennungen, Raumnamen oder Personennamen einer bewohnten Wohnung
 * enthalten.
 *
 * Die Zeitpunkte entstehen relativ zum Aufruf, damit Dauern und Uhrzeiten in
 * den Bildern plausibel bleiben statt zu veralten.
 */

const JETZT = Date.now();

/** ISO-Zeitpunkt, der so viele Minuten zurueckliegt. */
const vor = (minuten) => new Date(JETZT - minuten * 60_000).toISOString();

/** Dauer in Sekunden, passend zu einem noch laufenden Ereignis. */
const seit = (minuten) => minuten * 60;

export const GET_CONFIG = {
  api_version: 1,
  version: "1.1.4",
  entities: [
    { entity_id: "binary_sensor.wohnzimmer_terrassentuer", device_id: "dev_kontakt_1", area_id: "wohnzimmer", name: "Terrassentür", area_name: "Wohnzimmer", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.flur_haustuer", device_id: "dev_kontakt_2", area_id: "flur", name: "Haustür", area_name: "Flur", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.kueche_fenster", device_id: "dev_kontakt_3", area_id: "kueche", name: "Küchenfenster", area_name: "Küche", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "light.kueche_arbeitsplatte", device_id: "dev_licht_1", area_id: "kueche", name: "Licht Arbeitsplatte", area_name: "Küche", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "sensor.bad_luftfeuchte", device_id: "dev_klima_1", area_id: "bad", name: "Luftfeuchte Bad", area_name: "Bad", floor_id: "obergeschoss", floor_name: "Obergeschoss" },
    { entity_id: "climate.schlafzimmer_heizung", device_id: "dev_klima_2", area_id: "schlafzimmer", name: "Heizung Schlafzimmer", area_name: "Schlafzimmer", floor_id: "obergeschoss", floor_name: "Obergeschoss" },
    { entity_id: "binary_sensor.waschkueche_leckmelder", device_id: "dev_leck_1", area_id: "waschkueche", name: "Leckmelder Waschküche", area_name: "Waschküche", floor_id: "keller", floor_name: "Keller" },
    { entity_id: "switch.hobbyraum_loetstation", device_id: "dev_schalter_1", area_id: "hobbyraum", name: "Lötstation", area_name: "Hobbyraum", floor_id: "keller", floor_name: "Keller" },
    { entity_id: "switch.netzwerkspeicher", device_id: null, area_id: null, name: "Netzwerkspeicher", area_name: null, floor_id: null, floor_name: null },
    { entity_id: "person.alex", device_id: null, area_id: null, name: "Alex", area_name: null, floor_id: null, floor_name: null },
  ],
  rules: [
    { rule_id: "rule_terrasse", entity_id: "binary_sensor.wohnzimmer_terrassentuer", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Terrassentür ist offen", group_id: null, level: null },
    { rule_id: "rule_haustuer", entity_id: "binary_sensor.flur_haustuer", kind: "state_is", type: "alarm", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: 120, message_template: "Haustür steht seit zwei Minuten offen", group_id: null, level: null },
    { rule_id: "rule_kuechenfenster", entity_id: "binary_sensor.kueche_fenster", kind: "state_is", type: "warning", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: 900, message_template: "Küchenfenster länger als 15 min offen", group_id: null, level: null },
    { rule_id: "rule_arbeitsplatte", entity_id: "light.kueche_arbeitsplatte", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "{name} an", group_id: null, level: null },
    { rule_id: "rule_luftfeuchte", entity_id: "sensor.bad_luftfeuchte", kind: "numeric", type: "warning", enabled: true, value_source: { kind: "state", attribute: null }, states: [], operator: "gt", threshold: 70, release_threshold: 60, duration_seconds: null, message_template: "Luftfeuchte im Bad bei {value} {unit}", group_id: null, level: null },
    { rule_id: "rule_klima_temp", entity_id: "climate.schlafzimmer_heizung", kind: "numeric", type: "warning", enabled: true, value_source: { kind: "attribute", attribute: "temperature" }, states: [], operator: "gt", threshold: 23, release_threshold: 21, duration_seconds: null, message_template: "Schlafzimmer auf {value} °C gestellt", group_id: null, level: null },
    { rule_id: "rule_klima_modus", entity_id: "climate.schlafzimmer_heizung", kind: "state_is_not", type: "info", enabled: true, value_source: { kind: "attribute", attribute: "hvac_action" }, states: ["idle", "heating"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Heizung in ungewohntem Zustand", group_id: null, level: null },
    { rule_id: "rule_leck", entity_id: "binary_sensor.waschkueche_leckmelder", kind: "state_is", type: "alarm", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Wasser in der Waschküche", group_id: null, level: null },
    { rule_id: "rule_loetstation", entity_id: "switch.hobbyraum_loetstation", kind: "state_is", type: "warning", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: 3600, message_template: "Lötstation läuft seit über einer Stunde", group_id: null, level: null },
    { rule_id: "rule_nas", entity_id: "switch.netzwerkspeicher", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "{name}: an", group_id: null, level: null },
    { rule_id: "rule_alex", entity_id: "person.alex", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["home"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "{name} ist zu Hause", group_id: null, level: null },
  ],
  groups: [],
  settings: { paused: false, retention_days: 90, max_events: 5000, analysis_days: 7, setup_completed: true },
  options: { retention_days: [7, 30, 90, 365, 0], max_events: [1000, 5000, 10000, 50000] },
};

export const GET_ACTIVE = {
  api_version: 1,
  version: "1.1.4",
  counts: { info: 3, warning: 2, alarm: 2, active: 7, events_today: 23 },
  paused: false,
  active: [
    { event_id: "ev_leck", source: "entity_rule", type: "alarm", active: true, start_time: vor(4), end_time: null, duration: seit(4), title: null, message: "Wasser in der Waschküche", entity_id: "binary_sensor.waschkueche_leckmelder", area_id: "waschkueche", rule_id: "rule_leck" },
    { event_id: "ev_haustuer", source: "entity_rule", type: "alarm", active: true, start_time: vor(9), end_time: null, duration: seit(9), title: null, message: "Haustür steht seit zwei Minuten offen", entity_id: "binary_sensor.flur_haustuer", area_id: "flur", rule_id: "rule_haustuer" },
    { event_id: "ev_luftfeuchte", source: "entity_rule", type: "warning", active: true, start_time: vor(26), end_time: null, duration: seit(26), title: null, message: "Luftfeuchte im Bad bei 74 %", entity_id: "sensor.bad_luftfeuchte", area_id: "bad", rule_id: "rule_luftfeuchte" },
    { event_id: "ev_loetstation", source: "entity_rule", type: "warning", active: true, start_time: vor(83), end_time: null, duration: seit(83), title: null, message: "Lötstation läuft seit über einer Stunde", entity_id: "switch.hobbyraum_loetstation", area_id: "hobbyraum", rule_id: "rule_loetstation" },
    { event_id: "ev_terrasse", source: "entity_rule", type: "info", active: true, start_time: vor(41), end_time: null, duration: seit(41), title: null, message: "Terrassentür ist offen", entity_id: "binary_sensor.wohnzimmer_terrassentuer", area_id: "wohnzimmer", rule_id: "rule_terrasse" },
    { event_id: "ev_arbeitsplatte", source: "entity_rule", type: "info", active: true, start_time: vor(52), end_time: null, duration: seit(52), title: null, message: "Licht Arbeitsplatte an", entity_id: "light.kueche_arbeitsplatte", area_id: "kueche", rule_id: "rule_arbeitsplatte" },
    { event_id: "ev_alex", source: "entity_rule", type: "info", active: true, start_time: vor(447), end_time: null, duration: seit(447), title: null, message: "Alex ist zu Hause", entity_id: "person.alex", area_id: null, rule_id: "rule_alex" },
  ],
};

export const GET_COUNTS = {
  api_version: 1,
  version: "1.1.4",
  counts: { info: 3, warning: 2, alarm: 2, active: 7, events_today: 23 },
};

export const GET_HISTORY = {
  api_version: 1,
  version: "1.1.4",
  total: 214,
  offset: 0,
  has_more: true,
  events: [
    { event_id: "ev_leck", source: "entity_rule", type: "alarm", active: true, start_time: vor(4), end_time: null, duration: seit(4), message: "Wasser in der Waschküche", entity_id: "binary_sensor.waschkueche_leckmelder", area_id: "waschkueche" },
    { event_id: "ev_haustuer", source: "entity_rule", type: "alarm", active: true, start_time: vor(9), end_time: null, duration: seit(9), message: "Haustür steht seit zwei Minuten offen", entity_id: "binary_sensor.flur_haustuer", area_id: "flur" },
    { event_id: "ev_luftfeuchte", source: "entity_rule", type: "warning", active: true, start_time: vor(26), end_time: null, duration: seit(26), message: "Luftfeuchte im Bad bei 74 %", entity_id: "sensor.bad_luftfeuchte", area_id: "bad" },
    { event_id: "ev_fenster_zu", source: "entity_rule", type: "warning", active: false, start_time: vor(64), end_time: vor(38), duration: 1560, message: "Küchenfenster länger als 15 min offen", entity_id: "binary_sensor.kueche_fenster", area_id: "kueche" },
    { event_id: "ev_wartung", source: "automation", type: "info", active: false, start_time: vor(95), end_time: vor(92), duration: 180, message: "Sicherung abgeschlossen", entity_id: null, area_id: null },
    { event_id: "ev_terrasse_alt", source: "entity_rule", type: "info", active: false, start_time: vor(160), end_time: vor(151), duration: 540, message: "Terrassentür ist offen", entity_id: "binary_sensor.wohnzimmer_terrassentuer", area_id: "wohnzimmer" },
    { event_id: "ev_klima", source: "entity_rule", type: "warning", active: false, start_time: vor(220), end_time: vor(180), duration: 2400, message: "Schlafzimmer auf 24.0 °C gestellt", entity_id: "climate.schlafzimmer_heizung", area_id: "schlafzimmer" },
    { event_id: "ev_licht_alt", source: "entity_rule", type: "info", active: false, start_time: vor(300), end_time: vor(240), duration: 3600, message: "Licht Arbeitsplatte an", entity_id: "light.kueche_arbeitsplatte", area_id: "kueche" },
    { event_id: "ev_leck_alt", source: "entity_rule", type: "alarm", active: false, start_time: vor(1400), end_time: vor(1385), duration: 900, message: "Wasser in der Waschküche", entity_id: "binary_sensor.waschkueche_leckmelder", area_id: "waschkueche" },
  ],
};

export const DISCOVER = {
  api_version: 1,
  version: "1.1.4",
  entities: [
    { entity_id: "sensor.bad_luftfeuchte", name: "Luftfeuchte Bad", domain: "sensor", state: "74", device_class: "humidity", unit: "%", device_id: "dev_klima_1", device_name: "Klimasensor Bad", area_id: "bad", area_name: "Bad", monitored: true, rule_count: 1, has_suggestions: false },
    { entity_id: "binary_sensor.bad_fenster", name: "Badfenster", domain: "binary_sensor", state: "off", device_class: "window", unit: null, device_id: "dev_kontakt_4", device_name: "Fensterkontakt Bad", area_id: "bad", area_name: "Bad", monitored: false, rule_count: 0, has_suggestions: true },
    { entity_id: "sensor.bad_temperatur", name: "Temperatur Bad", domain: "sensor", state: "22.4", device_class: "temperature", unit: "°C", device_id: "dev_klima_1", device_name: "Klimasensor Bad", area_id: "bad", area_name: "Bad", monitored: false, rule_count: 0, has_suggestions: true },
    { entity_id: "light.bad_spiegel", name: "Spiegellicht", domain: "light", state: "off", device_class: null, unit: null, device_id: "dev_licht_2", device_name: "Spiegellicht", area_id: "bad", area_name: "Bad", monitored: false, rule_count: 0, has_suggestions: false },
  ],
};

export const GET_SUGGESTIONS = {
  api_version: 1,
  version: "1.1.4",
  entity_id: "binary_sensor.bad_fenster",
  suggestions: [
    {
      key: "window_open",
      title: "Warnung, wenn das Fenster länger als 15 min offen steht",
      confidence: "high",
      kind: "state_is",
      type: "warning",
      states: ["on"],
      operator: null,
      threshold: null,
      release_threshold: null,
      duration_seconds: 900,
      message_template: "{name} steht offen",
      reasons: [
        { label: "Geräteklasse", value: "window" },
        { label: "Grundlage", value: "allgemein übliche Schwelle" },
      ],
    },
  ],
  states: ["on", "off"],
  attributes: [{ name: "temperature", kind: "numeric", value: 22.4 }],
};

/** Bereiche, wie das Frontend sie aus `hass.areas` bekommt. */
export const AREAS = {
  wohnzimmer: { area_id: "wohnzimmer", name: "Wohnzimmer" },
  flur: { area_id: "flur", name: "Flur" },
  kueche: { area_id: "kueche", name: "Küche" },
  bad: { area_id: "bad", name: "Bad" },
  schlafzimmer: { area_id: "schlafzimmer", name: "Schlafzimmer" },
  waschkueche: { area_id: "waschkueche", name: "Waschküche" },
  hobbyraum: { area_id: "hobbyraum", name: "Hobbyraum" },
};
