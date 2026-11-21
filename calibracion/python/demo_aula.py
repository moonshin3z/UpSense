"""
Modo demo: una mañana de clases en un aula de Ciudad de Guatemala, simulada
minuto a minuto, comparando dos maestras con el mismo equipo:

  A) "sensor crudo"  : el semáforo usa el PM2.5 tal cual sale del PMS5003
  B) "UpSense"       : el semáforo usa el PM2.5 corregido por humedad
                       (Sitarek 2026) y el CO2 → aire reexhalado (Vouriot 2024)

Ambas obedecen al semáforo (abren/cierran la ventana). La historia que se ve:
la mañana húmeda infla el sensor crudo → falsa alarma de "aire sucio" → la
maestra A cierra → el CO2 sube → los niños respiran más aire reexhalado.

  >>> DATOS SIMULADOS. Ver supuestos abajo. No son mediciones.

Salidas:
  datos/demo_aula.json   serie para que el dashboard la reproduzca
  datos/demo_aula.csv    lo mismo en CSV
  modelos/demo_aula.png  gráfico para la presentación
"""

import csv
import json
import math
import os
import random
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, ".."))
sys.path.insert(0, AQUI)
from ventana import calibrar, cargar_modelo, recomendar, Estado, fraccion_reexhalada  # noqa: E402
from ventana.nucleo import riesgo_relativo, prob_contagio, CO2_EXTERIOR_PPM  # noqa: E402

# ------------------------------------------------------------ supuestos [SUPUESTO]
VOLUMEN_M3 = 7.5 * 6.5 * 3.0        # aula típica ~146 m³
ALUMNOS = 32
CO2_NINO_LS = 0.0038                # L/s por niño de 8-11 años sentado (Persily & de Jonge 2017: ~0.0036-0.0041)
CO2_ADULTO_LS = 0.0052              # maestra de pie/hablando
ACH = {"cerrada": 0.6, "parcial": 2.5, "abierta": 5.0}   # renovaciones por hora
DEPOSICION_H = 0.2                  # PM2.5 que se deposita por hora
PENETRACION = 0.8                   # fracción del PM exterior que entra con la ventana cerrada
INICIO, FIN = 7 * 60, 12 * 60 + 30  # 07:00 a 12:30
RECREO = (10 * 60, 10 * 60 + 30)


def exterior(minuto, rnd):
    """Clima y PM2.5 exterior REAL (seco) en una mañana lluviosa con un evento de humo."""
    h = minuto / 60
    rh = max(55.0, 96 - 9 * (h - 7) + rnd.gauss(0, 1.0))        # neblina a las 7, se seca
    temp = 15 + 1.6 * (h - 7) + rnd.gauss(0, 0.2)
    pm = 14 + 22 * math.exp(-((h - 7.6) / 0.6) ** 2)           # hora pico de tráfico
    if 11.0 <= h < 11.5:
        pm += 70 * math.sin(math.pi * (h - 11.0) / 0.5)          # quema cercana (real)
    return rh, temp, max(2.0, pm * (1 + rnd.gauss(0, 0.04)))


def pms5003(pm_seco, rh, rnd, kappa=0.2, a=1.6):
    """Misma física que generar_datos_sinteticos.py (κ-Köhler efectivo)."""
    aw = min(rh, 96.0) / 100
    g = 1 + (kappa / 1.65) * aw / (1 - aw)
    cf1 = a * pm_seco * g * (1 + rnd.gauss(0, 0.05)) + rnd.gauss(0, 0.5)
    if rh > 95:
        cf1 += rnd.uniform(0, 1) * (rh - 95) * 3
    return max(0.0, cf1)


def ventana_por_accion(accion, actual, minuto):
    if accion == "abrir":
        return "abierta"
    if accion == "abrir_parcial":
        return "parcial"
    if accion == "cerrar":
        return "cerrada"
    if accion == "ventilar_corto":
        return "abierta" if minuto % 20 < 5 else "cerrada"     # 5 min de cada 20
    return actual                                               # "nada": no tocar


def simular(usar_calibracion, modelo, semilla=3):
    rnd = random.Random(semilla)
    co2, pm_in = 480.0, 15.0
    estado_ventana = "cerrada"
    est = Estado()
    hist_pm = []
    filas = []
    for minuto in range(INICIO, FIN + 1):
        rh_ext, t_ext, pm_ext = exterior(minuto, rnd)
        en_clase = not (RECREO[0] <= minuto < RECREO[1])
        n = ALUMNOS if en_clase else 0
        gen_m3h = (n * CO2_NINO_LS + (1 if en_clase else 0) * CO2_ADULTO_LS) * 3.6
        ach = ACH[estado_ventana] if en_clase else ACH["abierta"]   # en recreo se ventila
        dt = 1 / 60
        co2 += (gen_m3h * 1e6 / VOLUMEN_M3 + ach * (CO2_EXTERIOR_PPM - co2)) * dt
        pen = 1.0 if estado_ventana != "cerrada" else PENETRACION
        pm_in += (ach * (pen * pm_ext - pm_in) - DEPOSICION_H * pm_in) * dt
        rh_in = min(98.0, rh_ext - 4 + (3 if en_clase else 0))      # adentro un poco más seco
        t_in = t_ext + (3.0 if en_clase else 1.5)

        cf1 = pms5003(pm_in, rh_in, rnd)
        co2_med = co2 + rnd.gauss(0, 15)                             # ruido MH-Z19C
        lect = {"pm25_cf1": cf1, "rh": rh_in, "temp": t_in, "pressure": 851.0}
        cal = calibrar(lect, modelo)
        pm_usado = cal["pm25"] if usar_calibracion else cf1
        if usar_calibracion and cal["alerta_humedad"] == "niebla":
            pm_usado = None                                          # dato no fiable: decide CO2
        hist_pm.append(pm_usado if pm_usado is not None else (hist_pm[-1] if hist_pm else 0))
        tendencia = hist_pm[-1] - hist_pm[-11] if len(hist_pm) > 10 else None
        rec = recomendar(co2_med, pm_usado, "interior", tendencia, est)
        if en_clase and minuto % 5 == 0:                             # la maestra mira cada 5 min
            estado_ventana = ventana_por_accion(rec["accion"], estado_ventana, minuto)

        filas.append({
            "hora": f"{minuto // 60:02d}:{minuto % 60:02d}",
            "minuto": minuto,
            "en_clase": en_clase,
            "rh": round(rh_in, 1),
            "temp": round(t_in, 1),
            "co2": round(co2_med),
            "pm25_crudo": round(cf1, 1),
            "pm25_ventana": cal["pm25"],
            "pm25_real": round(pm_in, 1),
            "pm25_exterior_real": round(pm_ext, 1),
            "alerta_humedad": cal["alerta_humedad"],
            "f": rec["f"],
            "riesgo_relativo": rec["riesgoRelativo"],
            "accion": rec["accion"],
            "ventana": estado_ventana,
        })
    return filas


def resumen(filas):
    clase = [r for r in filas if r["en_clase"]]
    f_media = sum(r["f"] for r in clase) / len(clase)
    horas = len(clase) / 60
    falsas = sum(1 for r in clase if r["accion"] in ("cerrar", "ventilar_corto") and r["pm25_real"] <= 35.4)
    return {
        "co2_max": max(r["co2"] for r in clase),
        "co2_medio": round(sum(r["co2"] for r in clase) / len(clase)),
        "min_co2_sobre_1200": sum(1 for r in clase if r["co2"] > 1200),
        "f_media_pct": round(100 * f_media, 2),
        "riesgo_relativo_medio": round(riesgo_relativo(f_media), 2),
        "prob_contagio_influenza_ilustrativa_pct": round(100 * prob_contagio(f_media, horas, ALUMNOS + 1), 2),
        "min_falsa_alarma_pm": falsas,
        "pm25_real_medio": round(sum(r["pm25_real"] for r in clase) / len(clase), 1),
    }


def grafico(A, B):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    t = [r["minuto"] / 60 for r in B]
    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [3, 2.3, 1]})
    ax[0].plot(t, [r["pm25_crudo"] for r in B], color="#c0392b", lw=1, label="PM2.5 sensor crudo")
    ax[0].plot(t, [r["pm25_ventana"] for r in B], color="#1f6fb2", lw=1.6, label="PM2.5 UpSense (corregido)")
    ax[0].plot(t, [r["pm25_real"] for r in B], color="black", lw=1, ls="--", label="PM2.5 real")
    ax[0].axhline(35.4, color="#e67e22", ls=":", lw=1)
    ax[0].set_ylabel("µg/m³")
    ax[0].legend(fontsize=8, loc="upper right")
    ax[0].set_title("Mañana húmeda en un aula (SIMULADO): misma lectura, dos decisiones distintas")
    ax[1].plot(t, [r["co2"] for r in A], color="#c0392b", lw=1.2, label="CO2 · maestra con sensor crudo")
    ax[1].plot(t, [r["co2"] for r in B], color="#1f6fb2", lw=1.6, label="CO2 · maestra con UpSense")
    ax[1].axhline(1185, color="#e67e22", ls=":", lw=1)
    ax[1].text(7.05, 1210, "2 % de aire reexhalado", color="#e67e22", fontsize=8)
    ax[1].set_ylabel("CO2 ppm")
    ax[1].legend(fontsize=8, loc="upper left")
    ax[2].plot(t, [r["rh"] for r in B], color="#5dade2")
    ax[2].fill_between(t, [r["rh"] for r in B], 50, color="#5dade2", alpha=0.3)
    ax[2].set_ylabel("Humedad %")
    ax[2].set_ylim(50, 100)
    ax[2].set_xlabel("hora del día")
    for a in ax:
        a.axvspan(10, 10.5, color="#eeeeee", zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(RAIZ, "modelos", "demo_aula.png"), dpi=130)


def main():
    modelo = cargar_modelo(os.path.join(RAIZ, "modelos", "modelo.json"))
    A = simular(False, modelo)
    B = simular(True, modelo)
    res = {"sensor_crudo": resumen(A), "ventana": resumen(B)}
    salida = {
        "nota": "SIMULADO. Aula de 32 alumnos, Ciudad de Guatemala, mañana lluviosa con quema a las 11:00.",
        "supuestos": {"volumen_m3": VOLUMEN_M3, "alumnos": ALUMNOS, "ach": ACH, "recreo": "10:00-10:30"},
        "resumen": res,
        "serie_ventana": B,
        "serie_sensor_crudo": A,
    }
    json.dump(salida, open(os.path.join(RAIZ, "datos", "demo_aula.json"), "w"), ensure_ascii=False)
    with open(os.path.join(RAIZ, "datos", "demo_aula.csv"), "w", newline="") as f:
        campos = list(B[0])
        w = csv.writer(f)
        w.writerow(campos + ["co2_si_sensor_crudo", "accion_si_sensor_crudo", "ventana_si_sensor_crudo"])
        for a, b in zip(A, B):
            w.writerow([b[c] for c in campos] + [a["co2"], a["accion"], a["ventana"]])
    grafico(A, B)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
