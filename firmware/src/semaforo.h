#pragma once
#include <Arduino.h>
#include "ventana_calib.h"   // núcleo científico (copiado de calibracion/c/; ver README)

// Semáforo en el propio ESP32: funciona aunque nadie tenga el dashboard abierto.
//  - Calibra PM2.5 con el modelo de ventana_modelo.h (o EPA si no está).
//  - Promedia ~5 min y calcula la tendencia de PM en 10 min.
//  - Guardia de humedad: con niebla (HR > 95 %) o una subida brusca de HR
//    (vapor), las lecturas de PM no entran al promedio y se decide por CO2.
//  - Si el dashboard manda una decisión (POST /api/semaforo), manda durante su ttl.

const char* accionTexto(VentanaAccion a);
VentanaAccion accionDesdeTexto(const String& s);

struct Decision {
  VentanaAccion accion = V_SIN_DATOS;
  uint8_t nivel = 0;
  uint8_t r = 40, g = 40, b = 40;
  float riesgoRelativo = NAN;
  bool alertaHumedad = false;
  bool remota = false;   // true si vino del dashboard
};

class Semaforo {
 public:
  Semaforo() { for (auto& v : rhMin_) v = NAN; for (auto& v : pmHist_) v = NAN; }
  // Llamar cada ~5 s con la última lectura (NAN si falta).
  void agregar(float pm25cf1, float co2, float rh, float temp, float presion);
  Decision decidir();
  void forzar(VentanaAccion a, uint32_t ttlMs);
  float pm25Corregido() const { return pmEma_; }
  float co2Promedio() const { return co2Ema_; }
  bool alertaHumedad() const;

 private:
  float pmEma_ = NAN, co2Ema_ = NAN, rh_ = NAN;
  float rhMin_[12];            // mínimo de HR por ventanas de 10 s (2 min)
  uint8_t rhIdx_ = 0; uint32_t rhT_ = 0; bool rhLleno_ = false;
  float pmHist_[11];           // pmEma_ al cerrar cada minuto (tendencia 10 min)
  uint8_t pmIdx_ = 0; uint32_t pmT_ = 0;
  VentanaEstado est_ = {0, 0};
  Decision remota_; uint32_t remotaHasta_ = 0;
};

// Tira WS2812
void ledsBegin();
void ledsMostrar(const Decision& d);   // llamar seguido (anima parpadeo y cuenta regresiva)
