#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <time.h>

#include "config.h"

constexpr size_t SAMPLE_COUNT = 128;
constexpr float SAMPLE_RATE_HZ = 1000.0f;
WiFiClient networkClient;
PubSubClient mqtt(networkClient);
uint32_t bootNonce;
uint32_t sequenceNumber = 0;

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(250);
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void connectMqtt() {
  while (!mqtt.connected()) {
    String clientId = "nexora-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    if (strlen(MQTT_USERNAME)) mqtt.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
    else mqtt.connect(clientId.c_str());
    if (!mqtt.connected()) delay(1000);
  }
}

String utcTimestamp() {
  struct tm timeInfo;
  if (!getLocalTime(&timeInfo, 2000)) return "1970-01-01T00:00:00Z";
  char value[25];
  strftime(value, sizeof(value), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(value);
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  bootNonce = esp_random();
  connectWiFi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(16384);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  StaticJsonDocument<12288> document;
  document["message_id"] = String((uint32_t)ESP.getEfuseMac(), HEX) + "-" + String(bootNonce, HEX) + "-" + String(sequenceNumber++);
  JsonObject window = document.createNestedObject("signal_window");
  window["recorded_at"] = utcTimestamp();
  window["sample_rate_hz"] = SAMPLE_RATE_HZ;
  window["channel"] = "vibration_x";
  window["unit"] = "adc_count";
  window["device_id"] = String((uint32_t)ESP.getEfuseMac(), HEX);
  window["smoothing_window"] = 1;
  JsonObject metadata = window.createNestedObject("metadata_json");
  metadata["adc_bits"] = 12;
  metadata["firmware"] = "nexora-esp32-v1";
  JsonArray samples = window.createNestedArray("samples");
  const uint32_t intervalMicros = (uint32_t)(1000000.0f / SAMPLE_RATE_HZ);
  uint32_t nextSample = micros();
  for (size_t index = 0; index < SAMPLE_COUNT; ++index) {
    while ((int32_t)(micros() - nextSample) < 0) {}
    samples.add(analogRead(VIBRATION_ADC_PIN));
    nextSample += intervalMicros;
  }
  String payload;
  serializeJson(document, payload);
  String topic = "nexora/machines/" NEXORA_MACHINE_ID "/signal-windows";
  mqtt.publish(topic.c_str(), payload.c_str(), false);
  delay(1000);
}
