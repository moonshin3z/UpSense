"""
calibrar(lectura, modelo) → PM2.5 corregido por humedad.

Misma lógica que js/ventana-calib.js (dashboard) y c/ventana_calib.h (ESP32).
Basado en Sitarek et al. 2026 (Sensors 26:6718, doi:10.3390/s26216718):
compensación de humedad por software con T, HR y presión, modelos livianos.
Ellos usan SDS011; aquí se adapta al PMS5003 (campo CF=1).
"""

import json

from .features import derivadas, valor_termino
from .nucleo import pm25_corregido_epa

RH_DUDOSA = 85.0   # por encima, la corrección es más incierta
RH_NIEBLA = 95.0   # por encima, el sensor cuenta gotitas: no fiable


def cargar_modelo(ruta):
    with open(ruta) as f:
        return json.load(f)


def _eval_arbol(t, x):
    nodo = 0
    while t["children_left"][nodo] != -1:
        if x[t["feature"][nodo]] <= t["threshold"][nodo]:
            nodo = t["children_left"][nodo]
        else:
            nodo = t["children_right"][nodo]
    return t["value"][nodo]


def evaluar(modelo, v):
    if "kohler" in modelo:
        k = modelo["kohler"]
        return v["pm25_cf1"] / (k["a"] * (1 + k["kappa"] / 1.65 * v["hgf"]))
    if modelo["tipo"] == "lineal":
        y = modelo.get("intercepto", 0.0)
        for nombre, c in zip(modelo["features"], modelo["coef"]):
            y += c * valor_termino(nombre, v)
        return y
    if modelo["tipo"] == "arboles":
        x = [valor_termino(n, v) for n in modelo["features"]]
        s = sum(_eval_arbol(t, x) for t in modelo["arboles"])
        if modelo.get("agregacion") == "media":
            return s / len(modelo["arboles"])
        return modelo.get("base", 0.0) + modelo.get("learning_rate", 1.0) * s
    raise ValueError("tipo de modelo desconocido")


def calibrar(lectura: dict, modelo: dict = None) -> dict:
    """lectura: {pm25_cf1, rh, temp, pressure, ...}  (crudas del firmware)

    Devuelve {pm25, crudo, metodo, alerta_humedad} donde alerta_humedad es
    None, "dudosa" (HR > 85 %) o "niebla" (HR > 95 %).
    """
    v = derivadas(lectura)
    rh = v.get("rh", 50.0)
    if modelo is not None:
        pm, metodo = evaluar(modelo, v), modelo.get("id", "modelo")
    else:
        pm, metodo = pm25_corregido_epa(v["pm25_cf1"], rh), "epa"
    pm = max(modelo.get("min", 0) if modelo else 0, pm)
    alerta = "niebla" if rh > RH_NIEBLA else ("dudosa" if rh > RH_DUDOSA else None)
    return {"pm25": round(pm, 2), "crudo": v["pm25_cf1"], "metodo": metodo, "alerta_humedad": alerta}
