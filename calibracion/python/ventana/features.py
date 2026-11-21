"""
Variables que usa la calibración. La misma lista está en js/ventana-calib.js
y c/ventana_calib.h: si cambias una fórmula aquí, cámbiala allá.

Variables crudas (las publica el firmware):
    pm25_cf1  PM2.5 del PMS5003, campo CF=1 (µg/m³)
    rh        humedad relativa del BME280 (%)
    temp      temperatura del BME280 (°C)
    pressure  presión del BME280 (hPa). Ciudad de Guatemala ≈ 850 hPa.

Variables derivadas (se calculan, no se miden):
    dewpoint  punto de rocío, Magnus (°C)
    dpd       depresión del punto de rocío = temp - dewpoint (°C): cerca de 0
              significa aire a punto de saturarse (niebla, partículas mojadas)
    hgf       término de crecimiento higroscópico rh/(100-rh), base de la
              teoría κ-Köhler (Petters & Kreidenweis 2007; Crilley et al. 2018):
              una partícula crece ∝ κ · rh/(100-rh). Con rh=60 → 1.5; 90 → 9.
"""

import math

CRUDAS = ("pm25_cf1", "rh", "temp", "pressure")
DERIVADAS = ("dewpoint", "dpd", "hgf")

RH_MAX = 98.0  # por encima el término hgf explota; el sensor ya no es fiable


def _rh(rh):
    return min(max(rh, 1.0), RH_MAX)


def dewpoint(temp, rh):
    a, b = 17.62, 243.12
    g = math.log(_rh(rh) / 100.0) + a * temp / (b + temp)
    return b * g / (a - g)


def derivadas(lect: dict) -> dict:
    """Devuelve un dict con crudas + derivadas a partir de una lectura."""
    v = {k: float(lect[k]) for k in CRUDAS if k in lect and lect[k] is not None}
    rh = _rh(v.get("rh", 50.0))
    t = v.get("temp", 20.0)
    v.setdefault("pressure", 850.0)
    v["dewpoint"] = dewpoint(t, rh)
    v["dpd"] = t - v["dewpoint"]
    v["hgf"] = rh / (100.0 - rh)
    return v


def valor_termino(nombre: str, v: dict) -> float:
    """Evalúa un término tipo 'pm25_cf1*hgf' o 'rh^2' o '1'."""
    if nombre == "1":
        return 1.0
    total = 1.0
    for factor in nombre.split("*"):
        if "^" in factor:
            base, exp = factor.split("^")
            total *= v[base] ** int(exp)
        else:
            total *= v[factor]
    return total
