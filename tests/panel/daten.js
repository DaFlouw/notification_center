/**
 * Antworten, wortgleich aus der laufenden Instanz vom 28.08.2026 (1.1.3)
 * uebernommen. Nichts davon ist erfunden -- nur die Historie ist auf neun
 * Eintraege gekuerzt, damit die Seite in einen Screenshot passt.
 */

export const GET_CONFIG = {
  api_version: 1,
  version: "1.1.3",
  entities: [
    { entity_id: "light.knx_interface_arbeiten_licht_fenster", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "buro", name: "Arbeiten Licht Fenster", area_name: "Arbeiten", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "flureg", name: "FlurEG Sensor Bewegung", area_name: "Flur EG", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "light.knx_interface_arbeiten_licht_mitte", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "buro", name: "Arbeiten Licht Mitte", area_name: "Arbeiten", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "climate.knx_interface_arbeiten_heizung_raum", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "buro", name: "Arbeiten Heizung Raum", area_name: "Arbeiten", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "person.florian_witt", device_id: null, area_id: null, name: "Florian Witt", area_name: null, floor_id: null, floor_name: null },
    { entity_id: "sensor.knx_interface_gastebad_temperatur_raum", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "gastebad", name: "Gästebad Temperatur Raum", area_name: "Gästebad", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "light.knx_interface_kuche_licht_kuchenzeile", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "kuche", name: "Küche Licht Küchenzeile", area_name: "Küche", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "switch.diskstation", device_id: null, area_id: null, name: "Diskstation", area_name: null, floor_id: null, floor_name: null },
    { entity_id: "binary_sensor.0x00158d0009f422e4_contact", device_id: "fb0defe75012de175ce702572109b5ca", area_id: "gastebad", name: "Aqara Fensterkontakt Tür", area_name: "Gästebad", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.knx_interface_wohn_ess_status_terrassentur", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "wohnzimmer", name: "Wohn-ess Status Terrassentür", area_name: "WohnEsszimmer", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "binary_sensor.knx_interface_wohn_ess_status_gartentur", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "wohnzimmer", name: "Wohn-ess Status Gartentür", area_name: "WohnEsszimmer", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
    { entity_id: "switch.knx_interface_gastebad_schalten_handtuchtrockner", device_id: "093d2a2d30f52032f1ae991a6e375000", area_id: "gastebad", name: "Gästebad Schalten Handtuchtrockner", area_name: "Gästebad", floor_id: "erdgeschoss", floor_name: "Erdgeschoss" },
  ],
  rules: [
    { rule_id: "rule_b07214cb5729", entity_id: "light.knx_interface_arbeiten_licht_fenster", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["off"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Licht aus im Arbeitszimmer", group_id: null, level: null },
    { rule_id: "rule_469851a9bd92", entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung", kind: "state_is", type: "alarm", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Bewegungs im Flur", group_id: null, level: null },
    { rule_id: "rule_0dd3a15421f8", entity_id: "light.knx_interface_arbeiten_licht_mitte", kind: "state_is", type: "warning", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Arbeitslicht an", group_id: null, level: null },
    { rule_id: "rule_0e1a62fe63d7", entity_id: "climate.knx_interface_arbeiten_heizung_raum", kind: "numeric", type: "warning", enabled: true, value_source: { kind: "attribute", attribute: "temperature" }, states: [], operator: "gt", threshold: 15, release_threshold: 3, duration_seconds: null, message_template: "Hot in here", group_id: null, level: null },
    { rule_id: "rule_67b741ae555f", entity_id: "person.florian_witt", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["home"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "{name}: {state}", group_id: null, level: null },
    { rule_id: "rule_0963d2881c46", entity_id: "climate.knx_interface_arbeiten_heizung_raum", kind: "state_is_not", type: "alarm", enabled: true, value_source: { kind: "attribute", attribute: "hvac_action" }, states: ["comfort"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Heizung außer Rand und aBand", group_id: null, level: null },
    { rule_id: "rule_428321a8ccc3", entity_id: "light.knx_interface_kuche_licht_kuchenzeile", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Licht in der Küche an", group_id: null, level: null },
    { rule_id: "rule_e460259a7cf6", entity_id: "switch.diskstation", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "{name}: an", group_id: null, level: null },
    { rule_id: "rule_aa88d8de0cd8", entity_id: "binary_sensor.0x00158d0009f422e4_contact", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Fenster im Gästebad ist geöffnet", group_id: null, level: null },
    { rule_id: "rule_ade621e3f228", entity_id: "binary_sensor.knx_interface_wohn_ess_status_terrassentur", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Terrassentür ist offen", group_id: null, level: null },
    { rule_id: "rule_448b216f8029", entity_id: "binary_sensor.knx_interface_wohn_ess_status_gartentur", kind: "state_is", type: "info", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: null, message_template: "Gartentür ist geöffnet", group_id: null, level: null },
    { rule_id: "rule_7bb2974e5a4a", entity_id: "switch.knx_interface_gastebad_schalten_handtuchtrockner", kind: "state_is", type: "warning", enabled: true, value_source: { kind: "state", attribute: null }, states: ["on"], operator: null, threshold: null, release_threshold: null, duration_seconds: 3600, message_template: "Handtuchtrocker im Gästebad ist länger als 60min an.", group_id: null, level: null },
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
    { event_id: "afb15bb645b243ac94244d7deda9dc93", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T20:24:41.544680+00:00", end_time: null, duration: 43.6, title: null, message: "Bewegungs im Flur", entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung", area_id: "flureg", rule_id: "rule_469851a9bd92" },
    { event_id: "f04ddb321d39458b8163a886e192456f", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:52:45.959410+00:00", end_time: null, duration: 1959.2, title: null, message: "Hot in here", entity_id: "climate.knx_interface_arbeiten_heizung_raum", area_id: "buro", rule_id: "rule_0e1a62fe63d7" },
    { event_id: "73f3b59b54534710b572de1af9e9e40d", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:49:39.930632+00:00", end_time: null, duration: 2145.2, title: null, message: "Arbeitslicht an", entity_id: "light.knx_interface_arbeiten_licht_mitte", area_id: "buro", rule_id: "rule_0dd3a15421f8" },
    { event_id: "5824ea61f5314840b4ecb7b275b9a100", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T19:49:29.307660+00:00", end_time: null, duration: 2155.8, title: null, message: "Heizung außer Rand und aBand", entity_id: "climate.knx_interface_arbeiten_heizung_raum", area_id: "buro", rule_id: "rule_0963d2881c46" },
    { event_id: "c215d285db644175871c004161949048", source: "entity_rule", type: "info", active: true, start_time: "2026-08-28T19:49:28.902660+00:00", end_time: null, duration: 2156.0, title: null, message: "Licht aus im Arbeitszimmer", entity_id: "light.knx_interface_arbeiten_licht_fenster", area_id: "buro", rule_id: "rule_b07214cb5729" },
    { event_id: "fb819d1b96544f8eb471248d558f0a23", source: "entity_rule", type: "info", active: true, start_time: "2026-08-26T11:11:05.096430+00:00", end_time: null, duration: 205526.9, title: null, message: "Diskstation: an", entity_id: "switch.diskstation", area_id: null, rule_id: "rule_e460259a7cf6" },
    { event_id: "7612d7b55036491ab8b0fdca287af433", source: "entity_rule", type: "info", active: true, start_time: "2026-08-26T04:50:20.093748+00:00", end_time: null, duration: 228371.9, title: null, message: "Florian Witt: home", entity_id: "person.florian_witt", area_id: null, rule_id: "rule_67b741ae555f" },
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
    { event_id: "afb15bb645b243ac94244d7deda9dc93", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T20:24:41.544680+00:00", end_time: null, duration: 43.6, message: "Bewegungs im Flur", entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung", area_id: "flureg" },
    { event_id: "292c2cda3ad64d7ea45ecbb4c9c1a550", source: "entity_rule", type: "info", active: false, start_time: "2026-08-28T20:17:11.462021+00:00", end_time: "2026-08-28T20:17:52.065074+00:00", duration: 40.6, message: "Licht in der Küche an", entity_id: "light.knx_interface_kuche_licht_kuchenzeile", area_id: "kuche" },
    { event_id: "f2a518ae02144f9aa20046ed6cf2e53f", source: "entity_rule", type: "alarm", active: false, start_time: "2026-08-28T20:15:09.302275+00:00", end_time: "2026-08-28T20:21:16.848860+00:00", duration: 367.5, message: "Bewegungs im Flur", entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung", area_id: "flureg" },
    { event_id: "3fb8591db6d74800bab759599a5fa00c", source: "entity_rule", type: "alarm", active: false, start_time: "2026-08-28T19:54:07.976246+00:00", end_time: "2026-08-28T20:01:12.885556+00:00", duration: 424.9, message: "Bewegungs im Flur", entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung", area_id: "flureg" },
    { event_id: "f04ddb321d39458b8163a886e192456f", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:52:45.959410+00:00", end_time: null, duration: 1959.2, message: "Hot in here", entity_id: "climate.knx_interface_arbeiten_heizung_raum", area_id: "buro" },
    { event_id: "d84900d443664f07aaaedac3c74c6813", source: "entity_rule", type: "info", active: false, start_time: "2026-08-28T19:50:02.636521+00:00", end_time: "2026-08-28T19:55:40.848203+00:00", duration: 338.2, message: "Licht in der Küche an", entity_id: "light.knx_interface_kuche_licht_kuchenzeile", area_id: "kuche" },
    { event_id: "73f3b59b54534710b572de1af9e9e40d", source: "entity_rule", type: "warning", active: true, start_time: "2026-08-28T19:49:39.930632+00:00", end_time: null, duration: 2145.2, message: "Arbeitslicht an", entity_id: "light.knx_interface_arbeiten_licht_mitte", area_id: "buro" },
    { event_id: "5824ea61f5314840b4ecb7b275b9a100", source: "entity_rule", type: "alarm", active: true, start_time: "2026-08-28T19:49:29.307660+00:00", end_time: null, duration: 2155.8, message: "Heizung außer Rand und aBand", entity_id: "climate.knx_interface_arbeiten_heizung_raum", area_id: "buro" },
    { event_id: "890610d1135f4cfab7954b5bfc6638d5", source: "entity_rule", type: "alarm", active: false, start_time: "2026-08-28T19:49:29.053625+00:00", end_time: "2026-08-28T19:53:50.904931+00:00", duration: 261.9, message: "Bewegungs im Flur", entity_id: "binary_sensor.knx_interface_flureg_sensor_bewegung", area_id: "flureg" },
  ],
};

export const DISCOVER = {
  api_version: 1,
  version: "1.1.3",
  entities: [
    { entity_id: "sensor.knx_interface_gastebad_temperatur_raum", name: "Gästebad Temperatur Raum", domain: "sensor", state: "22.74", device_class: "temperature", unit: "°C", device_id: "093d2a2d30f52032f1ae991a6e375000", device_name: "KNX Interface", area_id: "gastebad", area_name: "Gästebad", monitored: true, rule_count: 0, has_suggestions: false },
    { entity_id: "light.beleuchtung_gastebad", name: "Beleuchtung_Gästebad", domain: "light", state: "unavailable", device_class: null, unit: null, device_id: "69c4fb49bf4c2f733f875997108fbe82", device_name: "Beleuchtung_Gästebad", area_id: "gastebad", area_name: "Gästebad", monitored: false, rule_count: 0, has_suggestions: false },
    { entity_id: "sensor.knx_interface_gastebad_heizung_stellwert", name: "Gästebad Heizung Stellwert", domain: "sensor", state: "0", device_class: null, unit: "%", device_id: "093d2a2d30f52032f1ae991a6e375000", device_name: "KNX Interface", area_id: "gastebad", area_name: "Gästebad", monitored: false, rule_count: 0, has_suggestions: false },
    { entity_id: "light.knx_interface_gastebad_licht_spiegel", name: "Gästebad Licht Spiegel", domain: "light", state: "off", device_class: null, unit: null, device_id: "093d2a2d30f52032f1ae991a6e375000", device_name: "KNX Interface", area_id: "gastebad", area_name: "Gästebad", monitored: false, rule_count: 0, has_suggestions: true },
  ],
};

export const GET_SUGGESTIONS = {
  api_version: 1,
  version: "1.1.3",
  entity_id: "light.knx_interface_arbeiten_licht_fenster",
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
  buro: { area_id: "buro", name: "Arbeiten" },
  flureg: { area_id: "flureg", name: "Flur EG" },
  gastebad: { area_id: "gastebad", name: "Gästebad" },
  kuche: { area_id: "kuche", name: "Küche" },
  wohnzimmer: { area_id: "wohnzimmer", name: "WohnEsszimmer" },
};
