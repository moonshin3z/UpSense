"""
Genera datos SINTÉTICOS de co-ubicación para demostrar la calibración.

  >>> NO son mediciones reales. Sirven para probar el pipeline de punta a
  >>> punta y para el demo. Antes de afirmar cifras en el pitch hay que
  >>> reentrenar con datos reales (ver docs/protocolo_datos_reales.md).

Modelo físico de lo que mide un PMS5003 en Ciudad de Guatemala:

  pm25_cf1 = a · PM_seco · g(RH, κ) · (1 + ruido) + b + niebla

  g(RH, κ) = 1 + (κ / 1.65) · aw / (1 − aw),  aw = RH/100
      Crecimiento higroscópico en masa (κ-Köhler, forma de Crilley et al.
      2018 para sensores ópticos; 1.65 g/cm³ = densidad seca supuesta).
  κ        Higroscopicidad EFECTIVA dentro del sensor (el ventilador y la
           electrónica calientan el aire y bajan la HR interna, así que es
           menor que el κ atmosférico): 0.12-0.28 aerosol urbano, ~0.06 humo
           de biomasa (leña, caña). Atmosférico típico 0.1-0.6. [SUPUESTO]
  a        Sobreestimación del CF=1 de Plantower frente a referencia en seco
           (~1.5-2×; coherente con la pendiente 0.524 de la EPA). [SUPUESTO]
  niebla   Con RH > 95 % el sensor cuenta gotitas: picos espurios.

Clima supuesto (temporada de lluvias, valle de Guatemala, ~1 500 m):
  T 14-26 °C con ciclo diario, RH 45-98 % (inversa a T, mañanas con niebla
  y tardes de lluvia), presión ~850 hPa. [SUPUESTO, ajustar con INSIVUMEH]

Salida: datos/coubicacion_sintetica.csv, una fila cada 10 min.
"""

import csv
import math
import os
import random

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "datos", "coubicacion_sintetica.csv")


def generar(dias=60, paso_min=10, semilla=7):
    rnd = random.Random(semilla)
    filas = []
    n = int(dias * 24 * 60 / paso_min)
    lluvia = 0.0
    evento_humo = 0.0       # µg/m³ extra de quema (caña, basura, leña)
    kappa_lento = 0.2
    deriva_p = 0.0
    for i in range(n):
        t_h = i * paso_min / 60.0
        hora = t_h % 24
        dia = int(t_h // 24)
        finde = dia % 7 in (5, 6)

        # --- clima ---
        ciclo = math.cos(2 * math.pi * (hora - 15) / 24)       # máx a las 15 h
        temp = 20 + 5.5 * ciclo + rnd.gauss(0, 0.6)
        if rnd.random() < 0.004 and 13 <= hora <= 19:
            lluvia = rnd.uniform(1.5, 4)                        # horas de lluvia
        lluvia = max(0.0, lluvia - paso_min / 60)
        rh_base = 72 - 20 * ciclo + (14 if lluvia > 0 else 0) + rnd.gauss(0, 3)
        if 4 <= hora <= 8 and rnd.random() < 0.35:
            rh_base += rnd.uniform(5, 15)                       # neblina matutina
        rh = min(99.0, max(35.0, rh_base))
        if lluvia > 0:
            temp -= 2.0
        deriva_p += rnd.gauss(0, 0.05)
        deriva_p *= 0.995
        pressure = 851 + 1.2 * math.cos(2 * math.pi * (hora - 10) / 12) + deriva_p * 10

        # --- PM2.5 real (seco) ---
        trafico = 0 if finde else (
            22 * math.exp(-((hora - 7.5) / 1.3) ** 2) + 16 * math.exp(-((hora - 18.5) / 1.6) ** 2))
        fondo = 11 + 4 * math.sin(2 * math.pi * dia / 23)
        if rnd.random() < 0.0025:
            evento_humo = rnd.uniform(25, 110)
        evento_humo *= 0.97
        lavado = 0.55 if lluvia > 0 else 1.0                    # la lluvia limpia
        pm_seco = max(1.0, (fondo + trafico + evento_humo) * lavado * (1 + rnd.gauss(0, 0.08)))

        # --- higroscopicidad según fuente ---
        kappa_lento += rnd.gauss(0, 0.01)
        kappa_lento = min(0.28, max(0.12, kappa_lento))
        frac_humo = evento_humo / (fondo + trafico + evento_humo + 1e-9)
        kappa = kappa_lento * (1 - frac_humo) + 0.06 * frac_humo

        # --- respuesta del PMS5003 ---
        aw = min(rh, 96.0) / 100
        g = 1 + (kappa / 1.65) * aw / (1 - aw)
        a = 1.6
        cf1 = a * pm_seco * g * (1 + rnd.gauss(0, 0.07)) + rnd.gauss(0, 0.8)
        if rh > 95:
            cf1 += rnd.uniform(0, 1) * (rh - 95) * 3                # gotitas de niebla
        cf1 = max(0.0, cf1)

        filas.append({
            "t_horas": round(t_h, 4),
            "hora": round(hora, 3),
            "pm25_cf1": round(cf1, 2),
            "rh": round(rh, 1),
            "temp": round(temp, 2),
            "pressure": round(pressure, 1),
            "pm25_referencia": round(pm_seco, 2),
        })
    return filas


if __name__ == "__main__":
    filas = generar()
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} filas → {os.path.normpath(SALIDA)}")
