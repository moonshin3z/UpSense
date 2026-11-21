// UpSense: PMS5003 (partículas) + MH-Z19C (CO2) + BME280 (T, HR, presión) en ESP32.
// El propio equipo corrige el PM2.5 por humedad (ventana_calibrar, en semaforo.cpp),
// pausa las partículas si la humedad sube de golpe y decide qué mostrar en la tira LED,
// aunque no haya internet. Por HTTP publica las lecturas crudas y la decisión; el
// dashboard aplica el mismo modelo para mostrar crudo vs corregido.
//
// Endpoints:
//   GET /             dashboard (archivos de LittleFS, ver platformio.ini)
//   GET /api/now      última lectura
//   GET /api/history  promedios por minuto de las últimas 24 h (en RAM)
//   POST /api/co2/abc?on=0|1   activar/desactivar calibración automática del CO2

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <LittleFS.h>
#include <time.h>
#include "config.h"
#include "pms5003.h"
#include "mhz19c.h"
#include "semaforo.h"

#if defined(USE_BME280)
#include <Wire.h>
#include <Adafruit_BME280.h>
Adafruit_BME280 bme;
bool bmeOk = false;
#elif defined(USE_BME680)
#include <Wire.h>
#include <Adafruit_BME680.h>
Adafruit_BME680 bme;
bool bmeOk = false;
float gasKohm = NAN;  // resistencia del sensor de gas (más baja = más VOC); requiere ~30 min de estabilización
#endif

#ifdef PUSH_URL
#include <HTTPClient.h>
#endif

static const char* FW_VERSION = "0.1.0";

Pms5003 pms;
MhZ19c mhz;
Semaforo semaforo;
Decision decision;
WebServer server(80);
bool apMode = false;

float tempC = NAN, rh = NAN, pressHpa = NAN;

// ---------------- Historial (anillo en RAM) ----------------
// Valores guardados x10 en enteros para ocupar poco (≈20 bytes x 1440 = 29 KB).
struct Sample {
  uint32_t t;  // segundos desde el arranque (fin del intervalo)
  uint16_t pm1, pm25, pm25cf1, pm10;  // µg/m3 x10
  uint16_t co2;                        // ppm
  int16_t rh10, temp10;                // %, °C x10
};
static const uint16_t NA16 = 0xFFFF;
static const int16_t NAI16 = INT16_MIN;

Sample hist[HISTORY_LEN];
uint16_t histHead = 0, histCount = 0;

// Acumuladores del intervalo en curso
struct Acc {
  double pm1 = 0, pm25 = 0, pm25cf1 = 0, pm10 = 0; uint32_t nPm = 0;
  double co2 = 0; uint32_t nCo2 = 0;
  double rh = 0, temp = 0; uint32_t nEnv = 0;
} acc;
uint32_t lastHistMs = 0;

void closeInterval() {
  Sample s;
  s.t = millis() / 1000;
  s.pm1 = acc.nPm ? uint16_t(acc.pm1 / acc.nPm * 10 + .5) : NA16;
  s.pm25 = acc.nPm ? uint16_t(acc.pm25 / acc.nPm * 10 + .5) : NA16;
  s.pm25cf1 = acc.nPm ? uint16_t(acc.pm25cf1 / acc.nPm * 10 + .5) : NA16;
  s.pm10 = acc.nPm ? uint16_t(acc.pm10 / acc.nPm * 10 + .5) : NA16;
  s.co2 = acc.nCo2 ? uint16_t(acc.co2 / acc.nCo2 + .5) : NA16;
  s.rh10 = acc.nEnv ? int16_t(lround(acc.rh / acc.nEnv * 10)) : NAI16;
  s.temp10 = acc.nEnv ? int16_t(lround(acc.temp / acc.nEnv * 10)) : NAI16;
  hist[histHead] = s;
  histHead = (histHead + 1) % HISTORY_LEN;
  if (histCount < HISTORY_LEN) histCount++;
  acc = Acc();
}

// ---------------- JSON ----------------
static void appendNum(String& out, float v, int dec = 1) {
  if (isnan(v)) out += "null"; else out += String(v, dec);
}

String nowJson() {
  const PmsData& p = pms.data();
  bool pOk = pms.ok(), cOk = mhz.ok() && mhz.ppm() >= 0;
  String j;
  j.reserve(512);
  j += "{\"device\":\"" DEVICE_ID "\",\"fw\":\""; j += FW_VERSION;
  j += "\",\"uptime\":"; j += millis() / 1000;
  time_t epoch = time(nullptr);
  j += ",\"epoch\":"; j += (epoch > 1700000000 ? String((uint32_t)epoch) : String("null"));
  j += ",\"pms_ok\":"; j += pOk ? "true" : "false";
  j += ",\"co2_ok\":"; j += cOk ? "true" : "false";
  j += ",\"co2_warmup\":"; j += mhz.warmingUp(CO2_WARMUP_MS) ? "true" : "false";
  if (pOk) {
    j += ",\"pm1\":"; j += p.pm1_atm;
    j += ",\"pm25\":"; j += p.pm25_atm;
    j += ",\"pm10\":"; j += p.pm10_atm;
    j += ",\"pm1_cf1\":"; j += p.pm1_cf1;
    j += ",\"pm25_cf1\":"; j += p.pm25_cf1;
    j += ",\"pm10_cf1\":"; j += p.pm10_cf1;
    j += ",\"counts\":["; j += p.n03; j += ","; j += p.n05; j += ","; j += p.n10; j += ",";
    j += p.n25; j += ","; j += p.n50; j += ","; j += p.n100; j += "]";
  } else {
    j += ",\"pm1\":null,\"pm25\":null,\"pm10\":null,\"pm1_cf1\":null,\"pm25_cf1\":null,\"pm10_cf1\":null,\"counts\":null";
  }
  j += ",\"co2\":"; j += cOk ? String(mhz.ppm()) : String("null");
  j += ",\"temp\":"; appendNum(j, tempC);
  j += ",\"rh\":"; appendNum(j, rh);
  j += ",\"pressure\":"; appendNum(j, pressHpa);
#ifdef USE_BME680
  j += ",\"gas_kohm\":"; appendNum(j, gasKohm);
#endif
  j += ",\"semaforo\":{\"accion\":\""; j += accionTexto(decision.accion);
  j += "\",\"nivel\":"; j += decision.nivel;
  j += ",\"fuente\":\""; j += decision.remota ? "dashboard" : "local";
  j += "\",\"alerta_humedad\":"; j += decision.alertaHumedad ? "true" : "false";
  j += ",\"pm25_calibrado_5min\":"; appendNum(j, semaforo.pm25Corregido());
  j += ",\"riesgo_relativo\":"; appendNum(j, decision.riesgoRelativo, 2);
  j += "}";
  j += ",\"history_interval_s\":"; j += HISTORY_INTERVAL_S;
  j += "}";
  return j;
}

static void cors() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Cache-Control", "no-store");
}

void handleNow() { cors(); server.send(200, "application/json", nowJson()); }

void handleHistory() {
  cors();
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "application/json", "");
  String head = "{\"uptime\":" + String(millis() / 1000) + ",\"interval_s\":" + String(HISTORY_INTERVAL_S) +
                ",\"fields\":[\"t\",\"pm1\",\"pm25\",\"pm25_cf1\",\"pm10\",\"co2\",\"rh\",\"temp\"],\"rows\":[";
  server.sendContent(head);
  String chunk;
  chunk.reserve(2200);
  uint16_t start = (histHead + HISTORY_LEN - histCount) % HISTORY_LEN;
  auto v10 = [](uint16_t v, String& o) { if (v == NA16) o += "null"; else o += String(v / 10.0f, 1); };
  auto i10 = [](int16_t v, String& o) { if (v == NAI16) o += "null"; else o += String(v / 10.0f, 1); };
  for (uint16_t i = 0; i < histCount; i++) {
    const Sample& s = hist[(start + i) % HISTORY_LEN];
    if (i) chunk += ",";
    chunk += "["; chunk += s.t; chunk += ",";
    v10(s.pm1, chunk); chunk += ","; v10(s.pm25, chunk); chunk += ","; v10(s.pm25cf1, chunk); chunk += ",";
    v10(s.pm10, chunk); chunk += ",";
    if (s.co2 == NA16) chunk += "null"; else chunk += s.co2;
    chunk += ","; i10(s.rh10, chunk); chunk += ","; i10(s.temp10, chunk); chunk += "]";
    if (chunk.length() > 2000) { server.sendContent(chunk); chunk = ""; }
  }
  chunk += "]}";
  server.sendContent(chunk);
  server.sendContent("");
}

// El dashboard manda su decisión (con el modelo ML) para que la tira LED la muestre.
void handleSemaforo() {
  cors();
  Accion a = accionDesdeTexto(server.arg("accion"));
  uint32_t ttl = server.hasArg("ttl") ? constrain(server.arg("ttl").toInt(), 5, 600) : 60;
  semaforo.forzar(a, ttl * 1000UL);
  server.send(200, "application/json", String("{\"ok\":true,\"accion\":\"") + accionTexto(a) + "\"}");
}

void handleAbc() {
  cors();
  bool on = server.arg("on") != "0";
  mhz.setABC(on);
  server.send(200, "application/json", String("{\"abc\":") + (on ? "true" : "false") + "}");
}

// ---------------- WiFi ----------------
void setupWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Conectando a %s", WIFI_SSID);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < WIFI_TIMEOUT_MS) { delay(300); Serial.print("."); }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nConectado. Abre http://%s o http://%s.local\n", WiFi.localIP().toString().c_str(), MDNS_NAME);
    configTime(-6 * 3600, 0, "pool.ntp.org", "time.google.com");  // Guatemala UTC-6
  } else {
    apMode = true;
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASSWORD);
    Serial.printf("\nSin WiFi. Red propia '%s' (clave %s). Abre http://%s\n", AP_SSID, AP_PASSWORD,
                  WiFi.softAPIP().toString().c_str());
  }
  if (MDNS.begin(MDNS_NAME)) MDNS.addService("http", "tcp", 80);
}

#ifdef PUSH_URL
void pushNow() {
  if (apMode || WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(PUSH_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(nowJson());
  if (code != 200) Serial.printf("PUSH falló: %d\n", code);
  http.end();
}
#endif

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.printf("\nMonitor de aire %s (%s)\n", DEVICE_ID, FW_VERSION);

  pms.begin(Serial2, PMS_RX_PIN, PMS_TX_PIN);
  mhz.begin(Serial1, MHZ_RX_PIN, MHZ_TX_PIN);
  delay(100);
  mhz.setABC(MHZ_ABC_ON);

#if defined(USE_BME280) || defined(USE_BME680)
  Wire.begin(I2C_SDA, I2C_SCL);
  bmeOk = bme.begin(0x76) || bme.begin(0x77);
  Serial.println(bmeOk ? "BME OK" : "BME280/680 no encontrado (revisa SDA/SCL y dirección)");
#ifdef USE_BME680
  if (bmeOk) {
    bme.setTemperatureOversampling(BME680_OS_8X);
    bme.setHumidityOversampling(BME680_OS_2X);
    bme.setPressureOversampling(BME680_OS_4X);
    bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
    bme.setGasHeater(320, 150);
  }
#endif
#endif

  ledsBegin();
  if (!LittleFS.begin(true)) Serial.println("LittleFS no montado (¿hiciste uploadfs?)");
  setupWifi();

  server.on("/api/now", HTTP_GET, handleNow);
  server.on("/api/history", HTTP_GET, handleHistory);
  server.on("/api/co2/abc", HTTP_POST, handleAbc);
  server.on("/api/semaforo", HTTP_POST, handleSemaforo);
  server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");
  server.onNotFound([]() { cors(); server.send(404, "text/plain", "no encontrado"); });
  server.begin();
  lastHistMs = millis();
}

void loop() {
  server.handleClient();

  if (pms.update()) {
    const PmsData& p = pms.data();
    acc.pm1 += p.pm1_atm; acc.pm25 += p.pm25_atm; acc.pm25cf1 += p.pm25_cf1; acc.pm10 += p.pm10_atm;
    acc.nPm++;
  }
  if (mhz.update(CO2_QUERY_MS) && !mhz.warmingUp(CO2_WARMUP_MS)) {
    acc.co2 += mhz.ppm(); acc.nCo2++;
  }

#if defined(USE_BME280)
  static uint32_t lastEnv = 0;
  if (bmeOk && millis() - lastEnv > 2000) {
    lastEnv = millis();
    tempC = bme.readTemperature();
    rh = bme.readHumidity();
    pressHpa = bme.readPressure() / 100.0f;
    if (!isnan(rh)) { acc.rh += rh; acc.temp += tempC; acc.nEnv++; }
  }
#elif defined(USE_BME680)
  static uint32_t lastEnv = 0;
  if (bmeOk && millis() - lastEnv > 3000) {  // performReading bloquea ~150 ms por el calefactor
    lastEnv = millis();
    if (bme.performReading()) {
      tempC = bme.temperature;
      rh = bme.humidity;
      pressHpa = bme.pressure / 100.0f;
      gasKohm = bme.gas_resistance / 1000.0f;
      acc.rh += rh; acc.temp += tempC; acc.nEnv++;
    }
  }
#endif

  // Semáforo: alimentar con una lectura cada ~5 s y refrescar LEDs
  static uint32_t lastSem = 0;
  if (millis() - lastSem >= 5000) {
    lastSem = millis();
    const PmsData& p = pms.data();
    bool pOk = pms.ok();
    bool cOk = mhz.ok() && !mhz.warmingUp(CO2_WARMUP_MS);
    semaforo.agregar(pOk ? p.pm25_cf1 : NAN, cOk ? (float)mhz.ppm() : NAN, rh, tempC, pressHpa);
    decision = semaforo.decidir();
  }
  ledsMostrar(decision);

  if (millis() - lastHistMs >= HISTORY_INTERVAL_S * 1000UL) {
    lastHistMs += HISTORY_INTERVAL_S * 1000UL;
    closeInterval();
#ifdef PUSH_URL
    pushNow();
#endif
  }

  // Log por serie cada 5 s, útil para depurar cableado sin WiFi
  static uint32_t lastLog = 0;
  if (millis() - lastLog > 5000) {
    lastLog = millis();
    const PmsData& p = pms.data();
    Serial.printf("PM2.5=%u (cf1 %u) PM10=%u  CO2=%d%s  T=%.1f RH=%.0f  [pms %s, co2 %s, tramas malas %u]\n",
                  p.pm25_atm, p.pm25_cf1, p.pm10_atm, mhz.ppm(), mhz.warmingUp(CO2_WARMUP_MS) ? " (calentando)" : "",
                  tempC, rh, pms.ok() ? "ok" : "SIN DATOS", mhz.ok() ? "ok" : "SIN DATOS", pms.badFrames());
  }
}
