/* GENERADO por python/exportar_c.py — no editar a mano */
/* modelo: ventana-polinomio · entrenado con: SINTETICO */
/* métricas de prueba: {"r2": 0.955, "rmse": 3.35, "mae": 2.09, "sesgo": 0.41, "falsas_alarmas_pct": 1.7, "alarmas_perdidas_pct": 4.6, "mae_rh_mayor_75": 2.97} */
/* Lo incluye ventana_calib.h automáticamente si está en la misma carpeta. */
#ifndef VENTANA_MODELO_H
#define VENTANA_MODELO_H

static inline float ventana_modelo_eval(const VentanaVars *v) {
  float y = -27.2550708f;
  y += 0.802784385f * (v->pm25_cf1);
  y += -0.0200985326f * (v->pm25_cf1 * v->hgf);
  y += 0.00029053581f * (v->pm25_cf1 * v->hgf * v->hgf);
  y += -0.020876014f * (v->pm25_cf1 * v->temp);
  y += 0.028158827f * (v->pm25_cf1 * v->dpd);
  y += 0.000296883882f * (v->pm25_cf1 * v->pm25_cf1);
  y += -0.115579155f * (v->hgf);
  y += 0.157164667f * (v->rh);
  y += 0.783300685f * (v->temp);
  return y;
}

#endif
