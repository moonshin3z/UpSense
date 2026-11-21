#include "semaforo.h"
#include <Adafruit_NeoPixel.h>
#include "config.h"

const char* accionTexto(VentanaAccion a) { return ventana_accion_str(a); }
VentanaAccion accionDesdeTexto(const String& s) {
  for (int i = 0; i <= V_SIN_DATOS; i++) if (s == ventana_accion_str(VentanaAccion(i))) return VentanaAccion(i);
  return V_SIN_DATOS;
}

static const float ALFA = 2.0f / (60 + 1);  // EMA ~5 min con lecturas cada 5 s
static float ema(float prev, float x) { return isnan(x) ? prev : isnan(prev) ? x : prev + ALFA * (x - prev); }

void Semaforo::agregar(float pm25cf1, float co2, float rh, float temp, float presion) {
  uint32_t now = millis();
  rh_ = rh;
  if (!isnan(rh)) {
    if (rhT_ == 0 || now - rhT_ > 10000) {
      rhT_ = now; rhIdx_ = (rhIdx_ + 1) % 12; rhMin_[rhIdx_] = rh;
      if (rhIdx_ == 0) rhLleno_ = true;
    } else if (rh < rhMin_[rhIdx_]) rhMin_[rhIdx_] = rh;
  }
  if (!isnan(pm25cf1) && !alertaHumedad()) {
    // Sin BME280 no hay modelo posible: se usa el CF1 tal cual
    float pm = isnan(rh) ? pm25cf1 : ventana_calibrar(pm25cf1, rh, isnan(temp) ? 22.f : temp, isnan(presion) ? 850.f : presion);
    pmEma_ = ema(pmEma_, pm);
  }
  co2Ema_ = ema(co2Ema_, co2);
  if (pmT_ == 0 || now - pmT_ >= 60000) {
    pmT_ = now; pmIdx_ = (pmIdx_ + 1) % 11; pmHist_[pmIdx_] = pmEma_;
  }
}

bool Semaforo::alertaHumedad() const {
  if (isnan(rh_)) return false;
  if (rh_ > HR_NIEBLA) return true;
  float mn = rh_;
  uint8_t n = rhLleno_ ? 12 : rhIdx_ + 1;
  for (uint8_t i = 0; i < n; i++) if (!isnan(rhMin_[i])) mn = min(mn, rhMin_[i]);
  return rh_ - mn >= HR_SUBIDA_RAPIDA;
}

void Semaforo::forzar(VentanaAccion a, uint32_t ttlMs) {
  remota_ = Decision();
  remota_.accion = a; remota_.remota = true;
  static const uint8_t COL[6][3] = {{0,160,60},{255,170,0},{220,20,20},{130,40,200},{255,90,0},{40,40,40}};
  remota_.r = COL[a][0]; remota_.g = COL[a][1]; remota_.b = COL[a][2];
  remotaHasta_ = millis() + ttlMs;
}

Decision Semaforo::decidir() {
  Decision d;
  d.alertaHumedad = alertaHumedad();
  if (remotaHasta_ && (int32_t)(remotaHasta_ - millis()) > 0) { Decision r = remota_; r.alertaHumedad = d.alertaHumedad; return r; }
  float hace10 = pmHist_[(pmIdx_ + 1) % 11];  // el más viejo del anillo
  float tendencia = (!isnan(hace10) && !isnan(pmEma_)) ? pmEma_ - hace10 : NAN;
  // Con alerta de humedad se decide solo por CO2 (contrato de ventana_recomendar: pm < 0 = sin dato)
  float pm = (d.alertaHumedad || isnan(pmEma_)) ? -1.f : pmEma_;
  VentanaRec r = ventana_recomendar(co2Ema_, pm, false, d.alertaHumedad ? NAN : tendencia, &est_);
  d.accion = r.accion; d.nivel = r.nivel; d.r = r.r; d.g = r.g; d.b = r.b; d.riesgoRelativo = r.riesgo_relativo;
  return d;
}

// ---------------- LEDs ----------------
static Adafruit_NeoPixel tira(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void ledsBegin() {
  tira.begin();
  tira.setBrightness(LED_BRILLO);
  tira.clear();
  tira.show();
}

void ledsMostrar(const Decision& d) {
  static uint32_t ultimo = 0, inicioVentilar = 0;
  static VentanaAccion anterior = V_SIN_DATOS;
  uint32_t now = millis();
  if (now - ultimo < 40) return;  // ~25 fps
  ultimo = now;
  if (d.accion == V_VENTILAR_CORTO && anterior != V_VENTILAR_CORTO) inicioVentilar = now;
  anterior = d.accion;

  uint16_t encendidos = LED_COUNT;
  float k = 1.0f;
  switch (d.accion) {
    case V_ABRIR_PARCIAL: encendidos = (LED_COUNT + 1) / 2; break;   // media tira = "un poco"
    case V_VENTILAR_CORTO: {
      // Cuenta regresiva de 5 min: se apaga un LED cada 5 min / LED_COUNT, parpadeando
      uint32_t trans = now - inicioVentilar;
      uint32_t total = VENTILAR_MS;
      encendidos = trans >= total ? 0 : LED_COUNT - (uint32_t)((uint64_t)trans * LED_COUNT / total);
      k = (now / 500) % 2 ? 1.0f : 0.35f;
      break;
    }
    case V_SIN_DATOS: k = 0.25f + 0.75f * (0.5f + 0.5f * sinf(now / 600.0f)); break;  // respira
    default: break;
  }
  for (uint16_t i = 0; i < LED_COUNT; i++) {
    if (d.alertaHumedad && i == LED_COUNT - 1) { tira.setPixelColor(i, 50, 50, 50); continue; }  // aviso de humedad
    tira.setPixelColor(i, i < encendidos ? tira.Color(d.r * k, d.g * k, d.b * k) : 0);
  }
  tira.show();
}
