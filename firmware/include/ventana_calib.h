/*
 * ventana_calib.h · núcleo científico de UpSense para ESP32 (Arduino/PlatformIO)
 *
 * Header-only, sin dependencias (solo math.h). Misma lógica que
 * js/ventana-calib.js y python/ventana. Usa float de 32 bits (FPU del ESP32).
 *
 *   #include "ventana_calib.h"    // incluye solo ventana_modelo.h si existe
 *                                 // (generado por python/exportar_c.py)
 *
 *   VentanaEstado est = {0, 0};
 *   float pm = ventana_calibrar(pm25_cf1, rh, temp, presion);   // µg/m³ corregido
 *   VentanaRec r = ventana_recomendar(co2_5min, pm_5min, false, tendencia, &est);
 *   leds.fill(r.color);   // r.accion, r.nivel, r.f, r.riesgo_relativo
 *
 * Sin ventana_modelo.h (o con -DVENTANA_SIN_MODELO), ventana_calibrar usa la corrección EPA.
 */
#ifndef VENTANA_CALIB_H
#define VENTANA_CALIB_H

#include <math.h>
#include <stdint.h>
#include <stdbool.h>

#define V_CO2_ALIENTO   38000.0f  /* [POR CONFIRMAR] Vouriot 2024 */
#define V_CO2_EXTERIOR    425.0f  /* [POR CONFIRMAR] medir en el patio */
#define V_CO2_REFERENCIA  800.0f
#define V_F_VERDE   0.010f
#define V_F_ROJO    0.020f
#define V_PM_SENSIBLES 35.4f
#define V_PM_DANINO    55.4f
#define V_HIST_F   0.0015f
#define V_HIST_PM  3.0f
#define V_TENDENCIA_ENTRADA 5.0f
#define V_RH_MAX 98.0f

typedef enum { V_NADA = 0, V_ABRIR_PARCIAL, V_ABRIR, V_CERRAR, V_VENTILAR_CORTO, V_SIN_DATOS } VentanaAccion;

typedef struct { uint8_t nivel_co2; uint8_t nivel_pm; } VentanaEstado;

typedef struct {
  VentanaAccion accion;
  uint8_t nivel;            /* 0-3 */
  float f;                  /* fracción reexhalada */
  float riesgo_relativo;    /* vs aula a 800 ppm */
  uint8_t r, g, b;          /* color sugerido para la tira LED */
} VentanaRec;

typedef struct { float pm25_cf1, rh, temp, pressure, dewpoint, dpd, hgf; } VentanaVars;

static inline float v_clamp_rh(float rh) { return rh < 1.f ? 1.f : (rh > V_RH_MAX ? V_RH_MAX : rh); }

static inline VentanaVars ventana_derivadas(float pm25_cf1, float rh, float temp, float pressure) {
  VentanaVars v;
  float r = v_clamp_rh(rh);
  const float a = 17.62f, b = 243.12f;
  float g = logf(r / 100.f) + a * temp / (b + temp);
  v.pm25_cf1 = pm25_cf1; v.rh = rh; v.temp = temp; v.pressure = pressure;
  v.dewpoint = b * g / (a - g);
  v.dpd = temp - v.dewpoint;
  v.hgf = r / (100.f - r);
  return v;
}

#if !defined(VENTANA_SIN_MODELO) && defined(__has_include)
#  if __has_include("ventana_modelo.h")
#    include "ventana_modelo.h"
#  endif
#endif

static inline float ventana_epa(float cf1, float rh) {
  float x = cf1 < 0 ? 0 : cf1, y, w;
  if (rh < 0) rh = 0;
  if (rh > 100) rh = 100;
  if (x < 30)       y = 0.524f * x - 0.0862f * rh + 5.75f;
  else if (x < 50) { w = x / 20.f - 1.5f; y = (0.786f * w + 0.524f * (1 - w)) * x - 0.0862f * rh + 5.75f; }
  else if (x < 210) y = 0.786f * x - 0.0862f * rh + 5.75f;
  else if (x < 260) { w = x / 50.f - 4.2f;
    y = (0.69f * w + 0.786f * (1 - w)) * x - 0.0862f * rh * (1 - w) + 2.966f * w + 5.75f * (1 - w) + 8.84e-4f * x * x * w; }
  else y = 2.966f + 0.69f * x + 8.84e-4f * x * x;
  return y < 0 ? 0 : y;
}

static inline float ventana_calibrar(float pm25_cf1, float rh, float temp, float pressure) {
  VentanaVars v = ventana_derivadas(pm25_cf1, rh, temp, pressure);
#ifdef VENTANA_MODELO_H
  float y = ventana_modelo_eval(&v);
#else
  float y = ventana_epa(pm25_cf1, rh);
#endif
  return y < 0 ? 0 : y;
}

static inline float ventana_fraccion(float co2) {
  float f = (co2 - V_CO2_EXTERIOR) / V_CO2_ALIENTO;
  return f < 0 ? 0 : f;
}

static inline uint8_t v_nivel(float x, float c1, float c2, uint8_t ant, float h) {
  uint8_t n = 0;
  if (x >= (ant >= 1 ? c1 - h : c1)) n = 1;
  if (x >= (ant >= 2 ? c2 - h : c2)) n = 2;
  return n;
}

/* pm25 < 0 → sin dato de PM. tendencia: cambio en ~10 min, NAN si no hay. */
static inline VentanaRec ventana_recomendar(float co2, float pm25, bool pm_exterior,
                                            float tendencia, VentanaEstado *e) {
  static const uint8_t COL[6][3] = {{0,160,60},{255,170,0},{220,20,20},{130,40,200},{255,90,0},{40,40,40}};
  static const uint8_t NIV[6] = {0, 1, 3, 2, 2, 0};
  VentanaRec r;
  if (isnan(co2) || co2 <= 0) {
    r.accion = V_SIN_DATOS; r.f = NAN; r.riesgo_relativo = NAN;
  } else {
    r.f = ventana_fraccion(co2);
    r.riesgo_relativo = r.f / ventana_fraccion(V_CO2_REFERENCIA);
    uint8_t nc = v_nivel(r.f, V_F_VERDE, V_F_ROJO, e->nivel_co2, V_HIST_F);
    uint8_t npm = pm25 < 0 ? 0 : v_nivel(pm25, V_PM_SENSIBLES, V_PM_DANINO, e->nivel_pm, V_HIST_PM);
    e->nivel_co2 = nc; e->nivel_pm = npm;
    bool entrando = pm_exterior || (!isnan(tendencia) && tendencia >= V_TENDENCIA_ENTRADA);
    if (nc == 0)       r.accion = npm == 0 ? V_NADA : (entrando ? V_CERRAR : V_ABRIR_PARCIAL);
    else if (npm >= 1) r.accion = V_VENTILAR_CORTO;
    else               r.accion = nc == 1 ? V_ABRIR_PARCIAL : V_ABRIR;
  }
  r.nivel = NIV[r.accion];
  r.r = COL[r.accion][0]; r.g = COL[r.accion][1]; r.b = COL[r.accion][2];
  return r;
}

static inline const char *ventana_accion_str(VentanaAccion a) {
  static const char *S[] = {"nada", "abrir_parcial", "abrir", "cerrar", "ventilar_corto", "sin_datos"};
  return S[a];
}

#endif
