"""
Entrena y compara métodos de calibración del PMS5003 contra la humedad.

Uso:
    python entrenar.py                         # datos sintéticos
    python entrenar.py ruta/a/mis_datos.csv    # datos reales de co-ubicación

El CSV necesita columnas: pm25_cf1, rh, temp, pressure, pm25_referencia
(y opcionalmente t_horas para ordenar en el tiempo).

Métodos comparados (entrenamiento con el 75 % más antiguo, prueba con el
25 % más reciente, para no hacer trampa con autocorrelación):

  crudo       lo que marca el sensor (CF=1), sin tocar
  epa         corrección EPA de EE. UU. (Barkjohn et al. 2021 + ext. 2022)
  kohler      física pura: PM = cf1 / (a · (1 + κ/1.65 · hgf)), ajustando a y κ
  polinomio   regresión con términos físicos (cf1·hgf, cf1·hgf², ...), al
              estilo de la regresión polinómica de Sitarek et al. 2026
  bosque      Random Forest pequeño (30 árboles, prof. 8)
  gbm         Gradient Boosting (150 árboles, prof. 3)

Salidas:
  modelos/modelo_<metodo>.json   formato que carga el dashboard
  modelos/modelo.json            el recomendado (copiar a dashboard/modelo.json)
  modelos/metricas.json          tabla de métricas
  modelos/comparacion.png        gráfico para el pitch
"""

import csv
import json
import math
import os
import sys

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ventana.features import derivadas, valor_termino  # noqa: E402
from ventana.nucleo import pm25_corregido_epa, PM_SENSIBLES  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, ".."))
DIR_MODELOS = os.path.join(RAIZ, "modelos")

FEATS_ARBOL = ["pm25_cf1", "rh", "temp", "pressure", "dewpoint", "dpd", "hgf"]
TERMINOS_POLI = [
    "1", "pm25_cf1", "pm25_cf1*hgf", "pm25_cf1*hgf^2", "pm25_cf1*temp",
    "pm25_cf1*dpd", "pm25_cf1^2", "hgf", "rh", "temp",
]


# ---------------------------------------------------------------- datos
def cargar(ruta):
    with open(ruta) as f:
        filas = list(csv.DictReader(f))
    if "t_horas" in filas[0]:
        filas.sort(key=lambda r: float(r["t_horas"]))
    lect = [derivadas(r) for r in filas]
    y = np.array([float(r["pm25_referencia"]) for r in filas])
    return lect, y


def matriz(lect, nombres):
    return np.array([[valor_termino(n, v) for n in nombres] for v in lect])


# ---------------------------------------------------------------- métricas
def metricas(y, p):
    e = p - y
    ss_res = float(np.sum(e ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    real_ok = y <= PM_SENSIBLES
    falsas = int(np.sum(real_ok & (p > PM_SENSIBLES)))
    perdidas = int(np.sum(~real_ok & (p <= PM_SENSIBLES)))
    return {
        "r2": round(1 - ss_res / ss_tot, 3),
        "rmse": round(math.sqrt(ss_res / len(y)), 2),
        "mae": round(float(np.mean(np.abs(e))), 2),
        "sesgo": round(float(np.mean(e)), 2),
        "falsas_alarmas_pct": round(100 * falsas / max(1, int(real_ok.sum())), 1),
        "alarmas_perdidas_pct": round(100 * perdidas / max(1, int((~real_ok).sum())), 1),
    }


# ---------------------------------------------------------------- modelos
def ajustar_kohler(lect, y):
    cf1 = np.array([v["pm25_cf1"] for v in lect])
    hgf = np.array([v["hgf"] for v in lect])
    mejor = None
    for kappa in np.linspace(0.0, 1.0, 101):
        g = 1 + kappa / 1.65 * hgf
        x = y * g                       # cf1 ≈ a · y · g  →  a por mínimos cuadrados
        a = float(np.dot(x, cf1) / np.dot(x, x))
        err = float(np.mean((cf1 / (a * g) - y) ** 2))
        if mejor is None or err < mejor[0]:
            mejor = (err, a, float(kappa))
    return {"a": mejor[1], "kappa": mejor[2]}


def pred_kohler(m, lect):
    return np.array([v["pm25_cf1"] / (m["a"] * (1 + m["kappa"] / 1.65 * v["hgf"])) for v in lect])


def ajustar_poli(lect, y, alpha=1e-3):
    X = matriz(lect, TERMINOS_POLI)
    esc = np.maximum(np.abs(X).max(axis=0), 1e-9)   # escalado solo para resolver
    Xs = X / esc
    A = Xs.T @ Xs + alpha * np.eye(Xs.shape[1])
    coef = np.linalg.solve(A, Xs.T @ y) / esc
    return coef


def arboles_json(estimadores, feats):
    out = []
    for est in estimadores:
        t = est.tree_
        out.append({
            "children_left": t.children_left.tolist(),
            "children_right": t.children_right.tolist(),
            "feature": t.feature.tolist(),
            "threshold": [round(float(x), 5) for x in t.threshold],
            "value": [round(float(x), 5) for x in t.value[:, 0, 0]],
        })
    return out


# ---------------------------------------------------------------- export
def exportar(nombre, modelo, metr, fuente):
    base = {
        "id": f"ventana-{nombre}",
        "salida": "pm25",
        "min": 0,
        "entrenado_con": fuente,
        "metricas_prueba": metr,
        "nota": "Requiere variables derivadas (dewpoint, dpd, hgf): usar js/ventana-calib.js",
    }
    base.update(modelo)
    ruta = os.path.join(DIR_MODELOS, f"modelo_{nombre}.json")
    with open(ruta, "w") as f:
        json.dump(base, f, separators=(",", ":"))
    return ruta, os.path.getsize(ruta)


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "datos", "coubicacion_sintetica.csv")
    fuente = "SINTETICO" if "sintetica" in os.path.basename(ruta) else os.path.basename(ruta)
    lect, y = cargar(ruta)
    n_tr = int(0.75 * len(y))
    Ltr, Lte, ytr, yte = lect[:n_tr], lect[n_tr:], y[:n_tr], y[n_tr:]
    os.makedirs(DIR_MODELOS, exist_ok=True)

    preds, res, tam = {}, {}, {}

    preds["crudo"] = np.array([v["pm25_cf1"] for v in Lte])
    preds["epa"] = np.array([pm25_corregido_epa(v["pm25_cf1"], v["rh"]) for v in Lte])

    mk = ajustar_kohler(Ltr, ytr)
    preds["kohler"] = pred_kohler(mk, Lte)

    coef = ajustar_poli(Ltr, ytr)
    preds["polinomio"] = matriz(Lte, TERMINOS_POLI) @ coef

    Xtr, Xte = matriz(Ltr, FEATS_ARBOL), matriz(Lte, FEATS_ARBOL)
    rf = RandomForestRegressor(n_estimators=30, max_depth=8, min_samples_leaf=20,
                               random_state=0, n_jobs=-1).fit(Xtr, ytr)
    preds["bosque"] = rf.predict(Xte)
    gb = GradientBoostingRegressor(n_estimators=150, max_depth=3, learning_rate=0.1,
                                   random_state=0).fit(Xtr, ytr)
    preds["gbm"] = gb.predict(Xte)

    for k, p in preds.items():
        p = np.maximum(p, 0)
        preds[k] = p
        res[k] = metricas(yte, p)
        humedo = np.array([v["rh"] > 75 for v in Lte])
        res[k]["mae_rh_mayor_75"] = round(float(np.mean(np.abs(p[humedo] - yte[humedo]))), 2)

    # export
    _, tam["kohler"] = exportar("kohler", {
        "nombre": "Física κ-Köhler (2 parámetros)", "tipo": "lineal",
        "features": ["pm25_cf1", "hgf"], "kohler": mk,
        "formula": "pm25 = pm25_cf1 / (a * (1 + kappa/1.65 * hgf))"}, res["kohler"], fuente)
    _, tam["polinomio"] = exportar("polinomio", {
        "nombre": "Regresión con términos físicos", "tipo": "lineal",
        "features": TERMINOS_POLI[1:], "coef": [float(c) for c in coef[1:]],
        "intercepto": float(coef[0])}, res["polinomio"], fuente)
    _, tam["bosque"] = exportar("bosque", {
        "nombre": "Random Forest 30×8", "tipo": "arboles", "features": FEATS_ARBOL,
        "agregacion": "media", "base": 0, "learning_rate": 1,
        "arboles": arboles_json(rf.estimators_, FEATS_ARBOL)}, res["bosque"], fuente)
    _, tam["gbm"] = exportar("gbm", {
        "nombre": "Gradient Boosting 150×3", "tipo": "arboles", "features": FEATS_ARBOL,
        "agregacion": "suma", "base": float(gb.init_.constant_.ravel()[0]),
        "learning_rate": gb.learning_rate,
        "arboles": arboles_json([e[0] for e in gb.estimators_], FEATS_ARBOL)}, res["gbm"], fuente)

    # recomendado: el polinomio (0.7 KB, corre en el ESP32 y se puede explicar)
    # salvo que un modelo de árboles le gane por más de 10 % en MAE.
    mejor = "polinomio"
    for k in ("gbm", "bosque"):
        if res[k]["mae"] < 0.9 * res[mejor]["mae"]:
            mejor = k
    with open(os.path.join(DIR_MODELOS, f"modelo_{mejor}.json")) as f:
        txt = f.read()
    with open(os.path.join(DIR_MODELOS, "modelo.json"), "w") as f:
        f.write(txt)

    for k in res:
        res[k]["tam_json_kb"] = round(tam[k] / 1024, 1) if k in tam else None
    resumen = {"fuente": fuente, "n_entrenamiento": n_tr, "n_prueba": len(yte),
               "umbral_alarma": PM_SENSIBLES, "recomendado": mejor, "metodos": res}
    with open(os.path.join(DIR_MODELOS, "metricas.json"), "w") as f:
        json.dump(resumen, f, indent=1, ensure_ascii=False)

    print(f"Fuente: {fuente}  · entrenamiento {n_tr} · prueba {len(yte)}")
    print(f"{'método':10s} {'R2':>6s} {'RMSE':>6s} {'MAE':>6s} {'sesgo':>6s} {'MAE>75%':>8s} {'falsas%':>8s} {'perd%':>6s} {'KB':>6s}")
    for k, m in res.items():
        print(f"{k:10s} {m['r2']:6.3f} {m['rmse']:6.2f} {m['mae']:6.2f} {m['sesgo']:6.2f} "
              f"{m['mae_rh_mayor_75']:8.2f} {m['falsas_alarmas_pct']:8.1f} {m['alarmas_perdidas_pct']:6.1f} "
              f"{(m['tam_json_kb'] or 0):6.1f}")
    print("Recomendado:", mejor)

    grafico(Lte, yte, preds, res)


def grafico(Lte, yte, preds, res):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    n = min(len(yte), 6 * 24 * 7)   # una semana a 10 min
    t = np.arange(n) / 6 / 24
    rh = np.array([v["rh"] for v in Lte[:n]])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1]})
    a1.plot(t, preds["crudo"][:n], color="#c0392b", lw=0.9, alpha=0.8, label="Sensor crudo (PMS5003)")
    a1.plot(t, preds["epa"][:n], color="#999999", lw=0.9, label="Corrección EPA")
    a1.plot(t, preds[res and min(["polinomio", "bosque", "gbm"], key=lambda k: res[k]["mae"])][:n],
            color="#1f6fb2", lw=1.3, label="UpSense (calibración ML)")
    a1.plot(t, yte[:n], color="black", lw=1.1, ls="--", label="Referencia")
    a1.axhline(PM_SENSIBLES, color="#e67e22", lw=1, ls=":")
    a1.text(0.02, PM_SENSIBLES + 2, "umbral de alerta 35.4 µg/m³", color="#e67e22", fontsize=8)
    a1.set_ylabel("PM2.5 (µg/m³)")
    a1.legend(loc="upper right", fontsize=8, ncol=2)
    a1.set_title("Una semana de prueba (datos SINTÉTICOS): la humedad infla el sensor, la calibración lo corrige")
    a2.fill_between(t, rh, color="#5dade2", alpha=0.5)
    a2.set_ylabel("Humedad %")
    a2.set_xlabel("días")
    a2.set_ylim(30, 100)
    fig.tight_layout()
    fig.savefig(os.path.join(DIR_MODELOS, "comparacion.png"), dpi=130)


if __name__ == "__main__":
    main()
