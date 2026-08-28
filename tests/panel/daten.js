/**
 * Antworten, wortgleich aus der laufenden Instanz vom 28.08.2026 (1.1.3)
 * uebernommen. Nichts davon ist erfunden -- nur die Historie ist auf neun
 * Eintraege gekuerzt, damit die Seite in einen Screenshot passt.
 */

export const GET_CONFIG = {
  api_version: 1,
  version: "1.1.3",
  entities: [
    { entity_id: "light.kueche_arbeitsplatte", device_id: "dev_knoten_1", area_id: "kueche", name: "Licht Arbeitsplatte", area_name: "Küche", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.flur_haustuer", device_id: "dev_knoten_1", area_id: "flur", name: "Haustür", area_name: "Flur", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "light.wohnzimmer_stehlampe", device_id: "dev_knoten_1", area_id: "kueche", name: "Stehlampe", area_name: "Küche", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "climate.schlafzimmer_heizung", device_id: "dev_knoten_1", area_id: "kueche", name: "Heizung Schlafzimmer", area_name: "Küche", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "person.alex", device_id: null, area_id: null, name: "Alex", area_name: null, floor_id: null, floor_name: null },
    { entity_id: "sensor.bad_temperatur", device_id: "dev_knoten_1", area_id: "bad", name: "Temperatur Bad", area_name: "Bad", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "light.kueche_decke", device_id: "dev_knoten_1", area_id: "kueche", name: "Deckenlicht Küche", area_name: "Küche", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "switch.netzwerkspeicher", device_id: null, area_id: null, name: "Netzwerkspeicher", area_name: null, floor_id: null, floor_name: null },
    { entity_id: "binary_sensor.bad_fenster", device_id: "dev_kontakt_1", area_id: "bad", name: "Fensterkontakt Bad", area_name: "Bad", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.wohnzimmer_terrassentuer", device_id: "dev_knoten_1", area_id: "wohnzimmer", name: "Terrassentür", area_name: "Wohnzimmer", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.wohnzimmer_gartentuer", device_id: "dev_knoten_1", area_id: "wohnzimmer", name: "Gartentür", area_name: "Wohnzimmer", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "switch.bad_handtuchtrockner", device_id: "dev_knoten_1", area_id: "bad", name: "Handtuchtrockner Bad", area_name: "Bad", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
  ],
  rules: [
    { rule_id: "rule_000000000011", entity_id: "light.kueche_arbeitsplatte", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["off"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Licht Arbeitsplatte aus", group_id: null, level: null },
    { rule_id: "rule_000000000006", entity_id: "binary_sensor.flur_haustuer", kind: "state_is", type: "alarm", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Haustür steht offen", group_id: null, level: null },
    { rule_id: "rule_000000000002", entity_id: "light.wohnzimmer_stehlampe", kind: "state_is", type: "warning", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Arbeitslicht an", group_id: null, level: null },
    { rule_id: "rule_000000000003", entity_id: "climate.schlafzimmer_heizung", kind: "numeric", type: "warning", enabled: true, value_source: { kind: "attribute", attribute: "temperature" }, states: [], operator: "gt", threshold: 15, release_threshold: 3, duration_seconds: null, message_template: "Schlafzimmer zu warm", group_id: null, level: null },
    { rule_id: "rule_000000000007", entity_id: "person.alex", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["home"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "{name}: {state}", group_id: null, level: null },
    { rule_id: "rule_000000000001", entity_id: "climate.schlafzimmer_heizung", kind: "state_is_not", type: "alarm", enabled: true, value_source: { kind: "attribute", attribute: "hvac_action" }, states: ["comfort"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Heizung in ungewohntem Zustand", group_id: null, level: null },
    { rule_id: "rule_000000000004", entity_id: "light.kueche_decke", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Deckenlicht Küche an", group_id: null, level: null },
    { rule_id: "rule_000000000012", entity_id: "switch.netzwerkspeicher", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "{name}: an", group_id: null, level: null },
    { rule_id: "rule_000000000009", entity_id: "binary_sensor.bad_fenster", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Badfenster ist geöffnet", group_id: null, level: null },
    { rule_id: "rule_000000000010", entity_id: "binary_sensor.wohnzimmer_terrassentuer", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Terrassentür ist offen", group_id: null, level: null },
    { rule_id: "rule_000000000005", entity_id: "binary_sensor.wohnzimmer_gartentuer", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Gartentür steht offen", group_id: null, level: null },
    { rule_id: "rule_000000000008", entity_id: "switch.bad_handtuchtrockner", kind: "state_is", type: "warning", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: 3600, message_template: "Handtuchtrockner laenger als 60 min an", group_id: null, level: null },
  ],
  groups: [],
  settings: { paused: false, retention_days: 90, max_events: 5000, analysis_days: 7, setup_completed: true },
  options: { retention_days: [7, 30, 90, 365, 0], max_events: [1000, 5000, 10000, 50000] },
};

export const GET_ACTIVE = {
  api_version: 1,
  version: "1.1.3",
  counts: { info: 3, warning: 2, alarm: 2, active: 7, events_today: 74 },
  paused: false,
  active: [
    { event_id: "00000000000000000000000000000007", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T20:24:41.544680+00:00", end_time: null, duration: 43.6, title: null, message: "Haustür steht offen", entity_id: "binary_sensor.flur_haustuer", area_id: "flur", rule_id: "rule_000000000006" },
    { event_id: "00000000000000000000000000000010", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:52:45.959410+00:00", end_time: null, duration: 1959.2, title: null, message: "Schlafzimmer zu warm", entity_id: "climate.schlafzimmer_heizung", area_id: "kueche", rule_id: "rule_000000000003" },
    { event_id: "00000000000000000000000000000004", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:49:39.930632+00:00", end_time: null, duration: 2145.2, title: null, message: "Arbeitslicht an", entity_id: "light.wohnzimmer_stehlampe", area_id: "kueche", rule_id: "rule_000000000002" },
    { event_id: "00000000000000000000000000000003", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T19:49:29.307660+00:00", end_time: null, duration: 2155.8, title: null, message: "Heizung in ungewohntem Zustand", entity_id: "climate.schlafzimmer_heizung", area_id: "kueche", rule_id: "rule_000000000001" },
    { event_id: "00000000000000000000000000000008", source: "entity_rule", type: "info", active: true, start_time: "2026-08-28T19:49:28.902660+00:00", end_time: null, duration: 2156.0, title: null, message: "Licht Arbeitsplatte aus", entity_id: "light.kueche_arbeitsplatte", area_id: "kueche", rule_id: "rule_000000000011" },
    { event_id: "00000000000000000000000000000012", source: "entity_rule", type: "info", active: true, start_time: "2026-08-26T11:11:05.096430+00:00", end_time: null, duration: 205526.9, title: null, message: "Netzwerkspeicher: an", entity_id: "switch.netzwerkspeicher", area_id: null, rule_id: "rule_000000000012" },
    { event_id: "00000000000000000000000000000005", source: "entity_rule", type: "info", active: true, start_time: "2026-08-26T04:50:20.093748+00:00", end_time: null, duration: 228371.9, title: null, message: "Alex ist zu Hause", entity_id: "person.alex", area_id: null, rule_id: "rule_000000000007" },
  ],
};

export const GET_COUNTS = {
  api_version: 1,
  version: "1.1.3",
  counts: { info: 3, warning: 2, alarm: 2, active: 7, events_today: 74 },
};

export const GET_HISTORY = {
  api_version: 1,
  version: "1.1.3",
  total: 119,
  offset: 0,
  has_more: true,
  events: [
    { event_id: "00000000000000000000000000000007", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T20:24:41.544680+00:00", end_time: null, duration: 43.6, message: "Haustür steht offen", entity_id: "binary_sensor.flur_haustuer", area_id: "flur" },
    { event_id: "00000000000000000000000000000001", source: "entity_rule", type: "info", active: false, start_time: "2026-08-28T20:17:11.462021+00:00", end_time: "2026-08-28T20:17:52.065074+00:00", duration: 40.6, message: "Deckenlicht Küche an", entity_id: "light.kueche_decke", area_id: "kueche" },
    { event_id: "00000000000000000000000000000011", source: "entity_rule", type: "alarm", active: false, start_time: "2026-08-28T20:15:09.302275+00:00", end_time: "2026-08-28T20:21:16.848860+00:00", duration: 367.5, message: "Haustür steht offen", entity_id: "binary_sensor.flur_haustuer", area_id: "flur" },
    { event_id: "00000000000000000000000000000002", source: "entity_rule", type: "alarm", active: false, start_time: "2026-08-28T19:54:07.976246+00:00", end_time: "2026-08-28T20:01:12.885556+00:00", duration: 424.9, message: "Haustür steht offen", entity_id: "binary_sensor.flur_haustuer", area_id: "flur" },
    { event_id: "00000000000000000000000000000010", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:52:45.959410+00:00", end_time: null, duration: 1959.2, message: "Schlafzimmer zu warm", entity_id: "climate.schlafzimmer_heizung", area_id: "kueche" },
    { event_id: "00000000000000000000000000000009", source: "entity_rule", type: "info", active: false, start_time: "2026-08-28T19:50:02.636521+00:00", end_time: "2026-08-28T19:55:40.848203+00:00", duration: 338.2, message: "Deckenlicht Küche an", entity_id: "light.kueche_decke", area_id: "kueche" },
    { event_id: "00000000000000000000000000000004", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:49:39.930632+00:00", end_time: null, duration: 2145.2, message: "Arbeitslicht an", entity_id: "light.wohnzimmer_stehlampe", area_id: "kueche" },
    { event_id: "00000000000000000000000000000003", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T19:49:29.307660+00:00", end_time: null, duration: 2155.8, message: "Heizung in ungewohntem Zustand", entity_id: "climate.schlafzimmer_heizung", area_id: "kueche" },
    { event_id: "00000000000000000000000000000006", source: "entity_rule", type: "alarm", active: false, start_time: "2026-08-28T19:49:29.053625+00:00", end_time: "2026-08-28T19:53:50.904931+00:00", duration: 261.9, message: "Haustür steht offen", entity_id: "binary_sensor.flur_haustuer", area_id: "flur" },
  ],
};

export const DISCOVER = {
  api_version: 1,
  version: "1.1.3",
  entities: [
    { entity_id: "sensor.bad_temperatur", name: "Temperatur Bad", domain: "sensor", state: "22.74", device_class: "temperature", unit: "°C", device_id: "dev_knoten_1", device_name: "KNX Interface", area_id: "bad", area_name: "Bad", monitored: true, rule_count: 0, has_suggestions: false },
    { entity_id: "light.beleuchtung_bad", name: "Beleuchtung_Bad", domain: "light", state: "unavailable", device_class: null, unit: null, device_id: "dev_licht_2", device_name: "Beleuchtung_Bad", area_id: "bad", area_name: "Bad", monitored: false, rule_count: 0, has_suggestions: false },
    { entity_id: "sensor.bad_heizung_stellwert", name: "Heizung Stellwert Bad", domain: "sensor", state: "0", device_class: null, unit: "%", device_id: "dev_knoten_1", device_name: "KNX Interface", area_id: "bad", area_name: "Bad", monitored: false, rule_count: 0, has_suggestions: false },
    { entity_id: "light.bad_spiegel", name: "Spiegellicht", domain: "light", state: "off", device_class: null, unit: null, device_id: "dev_knoten_1", device_name: "KNX Interface", area_id: "bad", area_name: "Bad", monitored: false, rule_count: 0, has_suggestions: true },
  ],
};

export const GET_SUGGESTIONS = {
  api_version: 1,
  version: "1.1.3",
  entity_id: "light.kueche_arbeitsplatte",
  suggestions: [
    {
      key: "window_open",
      title: "Warnung, wenn das Fenster laenger offen steht",
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
        { label: "Geraeteklasse", value: "window" },
        { label: "Grundlage", value: "allgemein uebliche Schwelle" },
      ],
    },
  ],
  states: ["on", "off"],
  attributes: [{ name: "temperature", kind: "numeric", value: 21.5 }],
};

/** Bereiche, wie das Frontend sie aus `hass.areas` bekommt. */
export const AREAS = {
  kueche_eg: { area_id: "kueche", name: "Küche" },
  flur_eg: { area_id: "flur", name: "Flur" },
  bad_eg: { area_id: "bad", name: "Bad" },
  kueche_og: { area_id: "kueche", name: "Küche" },
  wohnzimmer: { area_id: "wohnzimmer", name: "Wohnzimmer" },
};
