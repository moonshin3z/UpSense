"""
UpSense · núcleo científico
===========================

Convierte lecturas de sensores baratos (MH-Z19C, PMS5003, BME280/680) en:

1. Fracción de aire reexhalado  f  (Rudnick & Milton 2003; usada con un solo
   sensor de CO2 en aulas por Vouriot et al. 2024, doi:10.1098/rsif.2024.0270).
2. Riesgo relativo de contagio por aire (Wells-Riley en su forma con CO2).
3. PM2.5 corregido por humedad (corrección de la EPA de EE. UU. para sensores
   Plantower como el PMS5003, Barkjohn et al. 2021 + extensión 2022 para humo).
4. Una recomendación para la maestra: abrir / abrir_parcial / cerrar /
   ventilar_corto / nada.

Sin dependencias: solo la biblioteca estándar de Python. La misma lógica está
en ../../c/ventana_calib.h (ESP32) y ../../js/ventana-calib.js (dashboard), y las
tres pasan los mismos vectores de prueba (../../datos/vectores_prueba.json).

Las cifras marcadas [POR CONFIRMAR] son suposiciones razonables que hay que
verificar contra la fuente antes de citarlas en el pitch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Constantes científicas
# ---------------------------------------------------------------------------

#: CO2 que añade la respiración al aire exhalado, en ppm (≈3.8 %).
#: Rudnick & Milton 2003 usan 37 500 ppm; 38 000 es el valor redondo habitual.
#: [POR CONFIRMAR] el valor exacto que usa Vouriot et al. 2024. En niños el
#: CO2 del aliento es parecido al de adultos (lo que cambia es el volumen).
CO2_ALIENTO_PPM = 38_000.0

#: CO2 exterior de referencia si no se mide afuera (media global 2025 ≈ 425 ppm;
#: en ciudad con tráfico puede ser 450-500). [POR CONFIRMAR] medir en el patio.
CO2_EXTERIOR_PPM = 425.0

#: Aula "bien ventilada" contra la que se compara el riesgo: 800 ppm.
#: 800 ppm es el objetivo que usaron muchas guías escolares durante COVID-19
#: (p. ej. CDC, REHVA) y equivale a f ≈ 1 % de aire reexhalado.
CO2_REFERENCIA_PPM = 800.0

# Umbrales de fracción reexhalada (derivados de CO2 con exterior = 425 ppm):
#   f < 1.0 %  ≈ CO2 < 805 ppm   → verde
#   f < 2.0 %  ≈ CO2 < 1 185 ppm → amarillo (abrir pronto)
#   f ≥ 2.0 %                     → rojo (abrir ya)
# El corte de 2 % (~1 200 ppm) queda por debajo del límite de 1 500 ppm de
# media diaria de la guía escolar británica BB101 (2018) para ventilación
# natural, para avisar antes de llegar ahí. [POR CONFIRMAR] cita exacta BB101.
F_VERDE = 0.010
F_ROJO = 0.020

# PM2.5 exterior (µg/m³), cortes del AQI de la EPA revisado en 2024:
#   0-9.0 bueno · 9.1-35.4 moderado · 35.5-55.4 dañino para sensibles · >55.4 dañino
# La guía OMS 2021 (24 h) es 15 µg/m³; la usamos solo como dato para el pitch.
PM_MODERADO = 9.0
PM_SENSIBLES = 35.4  # por encima: abrir solo a ráfagas
PM_DANINO = 55.4     # por encima: mantener cerrado salvo CO2 rojo

# Histéresis para que el semáforo no parpadee con el ruido del MH-Z19C
# (±50 ppm ± 5 % según hoja de datos). 0.15 % de f ≈ 57 ppm de CO2.
HISTERESIS_F = 0.0015
HISTERESIS_PM = 3.0


# ---------------------------------------------------------------------------
# 1. Fracción de aire reexhalado
# ---------------------------------------------------------------------------

def fraccion_reexhalada(co2_ppm: float, co2_exterior_ppm: float = CO2_EXTERIOR_PPM,
                        co2_aliento_ppm: float = CO2_ALIENTO_PPM) -> float:
    """f = (C - C_ext) / C_a  (Rudnick & Milton 2003, ec. 7).

    Fracción del aire que se respira que ya pasó por los pulmones de otra
    persona del aula. 0.02 = "2 de cada 100 respiraciones son aire de otro".
    Se recorta a 0 si el sensor marca menos que el exterior (ruido/calibración).
    """
    return max(0.0, (co2_ppm - co2_exterior_ppm) / co2_aliento_ppm)


def co2_para_fraccion(f: float, co2_exterior_ppm: float = CO2_EXTERIOR_PPM,
                      co2_aliento_ppm: float = CO2_ALIENTO_PPM) -> float:
    """Inversa: qué CO2 corresponde a una fracción reexhalada f."""
    return co2_exterior_ppm + f * co2_aliento_ppm


# ---------------------------------------------------------------------------
# 2. Riesgo de contagio (Wells-Riley con CO2, Rudnick & Milton 2003, ec. 9)
# ---------------------------------------------------------------------------

#: Tasas de emisión de "quanta" por hora de un infectado en reposo/hablando.
#: SOLO ILUSTRATIVAS: varían órdenes de magnitud entre estudios y variantes.
#: El producto usa el riesgo RELATIVO, donde q se cancela. [POR CONFIRMAR]
QUANTA_POR_HORA = {
    "influenza": 15.0,      # Rudnick & Milton 2003 estiman ~15-128 q/h
    "covid19": 25.0,        # rango publicado ~10-100 q/h hablando
    "sarampion": 570.0,     # brote escolar de Riley et al. 1978
}


def prob_contagio(f_media: float, horas: float, personas: int,
                  infectados: int = 1, quanta_h: float = QUANTA_POR_HORA["influenza"]) -> float:
    """P = 1 - exp(-f · I · q · t / n)

    f_media: fracción reexhalada media en el periodo
    horas:   tiempo de exposición
    personas (n): ocupantes del aula, incluido el infectado
    Supone aire bien mezclado y que todos respiran a ritmo parecido.
    """
    if personas <= 0:
        return 0.0
    return 1.0 - math.exp(-f_media * infectados * quanta_h * horas / personas)


def riesgo_relativo(f: float, f_referencia: Optional[float] = None) -> float:
    """Cuántas veces más (o menos) riesgo que un aula a 800 ppm.

    Para riesgos pequeños, P ∝ f, así que RR = f / f_ref no depende del
    patógeno, ni del número de infectados, ni de q. Esa es la cifra que
    mostramos: "esta aula tiene 2.3× el riesgo de un aula bien ventilada".
    """
    if f_referencia is None:
        f_referencia = fraccion_reexhalada(CO2_REFERENCIA_PPM)
    if f_referencia <= 0:
        return float("nan")
    return f / f_referencia


# ---------------------------------------------------------------------------
# 3. Corrección por humedad del PMS5003 (EPA, Barkjohn et al. 2021/2022)
# ---------------------------------------------------------------------------

def pm25_corregido_epa(pm25_cf1: float, humedad_rel: float) -> float:
    """Corrección de la EPA de EE. UU. para sensores Plantower (PurpleAir).

    pm25_cf1:    PM2.5 del PMS5003 en el campo **CF=1** (bytes 4-5 de la trama),
                 NO el campo "atmosférico". µg/m³.
    humedad_rel: % de humedad relativa (BME280/680). Ojo: el BME dentro de la
                 caja mide más caliente y seco que afuera; ver README.

    Base (Barkjohn et al. 2021, AMT 14:4617):
        PM = 0.524·CF1 − 0.0862·HR + 5.75          (CF1 < 30)
    Extensión para concentraciones altas / humo (EPA 2022, ver
    Fire and Smoke Map): tramos 30-50, 50-210, 210-260 y >260.
    [POR CONFIRMAR] coeficientes de la extensión contra el documento EPA.

    El PMS5003 sobreestima con humedad alta porque las partículas absorben
    agua y crecen; en temporada de lluvias en Guatemala (HR 70-90 %) la
    lectura cruda puede ser ~1.5-2× la real.
    """
    x = max(0.0, pm25_cf1)
    rh = min(max(humedad_rel, 0.0), 100.0)
    if x < 30:
        y = 0.524 * x - 0.0862 * rh + 5.75
    elif x < 50:
        w = x / 20.0 - 1.5
        y = (0.786 * w + 0.524 * (1 - w)) * x - 0.0862 * rh + 5.75
    elif x < 210:
        y = 0.786 * x - 0.0862 * rh + 5.75
    elif x < 260:
        w = x / 50.0 - 4.2
        y = ((0.69 * w + 0.786 * (1 - w)) * x
             - 0.0862 * rh * (1 - w)
             + 2.966 * w + 5.75 * (1 - w)
             + 8.84e-4 * x * x * w)
    else:
        y = 2.966 + 0.69 * x + 8.84e-4 * x * x
    return max(0.0, y)


def categoria_pm(pm: float) -> str:
    if pm <= PM_MODERADO:
        return "bueno"
    if pm <= PM_SENSIBLES:
        return "moderado"
    if pm <= PM_DANINO:
        return "sensibles"
    return "danino"


# ---------------------------------------------------------------------------
# 4. Recomendación (misma interfaz que js/ventana-calib.js → recomendar)
# ---------------------------------------------------------------------------

ACCIONES = ("abrir", "abrir_parcial", "cerrar", "ventilar_corto", "nada", "sin_datos")

TEXTOS = {
    "nada": ("Aire en buen estado", "No hace falta hacer nada."),
    "abrir_parcial": ("Abra un poco la ventana", "El aire del aula se está cargando."),
    "abrir": ("Abra la ventana ya", "Mucho aire ya respirado por otros: ventile ahora."),
    "cerrar": ("Cierre la ventana", "Está entrando humo o polvo de afuera."),
    "ventilar_corto": ("Ventile 5 minutos y cierre",
                       "El aula necesita aire, pero afuera está sucio: abra del todo 5 min y vuelva a cerrar."),
    "sin_datos": ("Sin datos", "Revise el sensor de CO2."),
}

NIVEL = {"nada": 0, "abrir_parcial": 1, "cerrar": 2, "ventilar_corto": 2, "abrir": 3, "sin_datos": 0}

#: Subida de PM2.5 en ~10 min que interpretamos como "está entrando de afuera".
TENDENCIA_ENTRADA = 5.0


@dataclass
class Estado:
    """Memoria entre llamadas para la histéresis (evita que el semáforo parpadee)."""
    nivel_co2: int = 0      # 0 verde, 1 amarillo, 2 rojo
    nivel_pm: int = 0       # 0 ok, 1 > 35.4, 2 > 55.4


def _nivel_con_histeresis(valor: float, cortes: tuple, anterior: int, h: float) -> int:
    """Sube de nivel al cruzar el corte; baja solo al quedar h por debajo."""
    nivel = 0
    for i, c in enumerate(cortes, start=1):
        umbral = c - h if anterior >= i else c
        if valor >= umbral:
            nivel = i
    return nivel


def recomendar(co2: Optional[float], pm25: Optional[float] = None, fuente_pm: str = "interior",
               pm25_tendencia: Optional[float] = None, estado: Optional[Estado] = None,
               co2_exterior_ppm: float = CO2_EXTERIOR_PPM) -> dict:
    """Decide qué decirle a la maestra.

    co2:            ppm, promedio de ~5 min (MH-Z19C dentro del aula)
    pm25:           µg/m³ YA CALIBRADO (ver calibrar), promedio de ~5 min
    fuente_pm:      "interior" (un solo equipo en el aula) o "exterior"
    pm25_tendencia: cambio de PM2.5 en ~10 min (µg/m³) o None

    Matriz (nivel CO2 × PM2.5):

                    PM ok (≤35.4)   PM alto (35.4-55.4)      PM muy alto (>55.4)
        CO2 verde   nada            cerrar*                  cerrar*
        CO2 amar.   abrir_parcial   ventilar_corto           ventilar_corto
        CO2 rojo    abrir           ventilar_corto           ventilar_corto

    * Con PM interior alto que NO viene subiendo puede ser una fuente dentro
      del aula (tiza, barrer, cocina cercana): entonces abrir_parcial.
    "ventilar_corto" sigue la idea del Stoßlüften: abrir del todo poco tiempo
    renueva mucho aire con poca entrada acumulada de partículas. [POR CONFIRMAR]
    """
    if estado is None:
        estado = Estado()
    if co2 is None:
        t, x = TEXTOS["sin_datos"]
        return {"accion": "sin_datos", "titulo": t, "texto": x, "nivel": 0,
                "f": None, "riesgoRelativo": None}

    f = fraccion_reexhalada(co2, co2_exterior_ppm)
    rr = riesgo_relativo(f, fraccion_reexhalada(CO2_REFERENCIA_PPM, co2_exterior_ppm))
    nc = _nivel_con_histeresis(f, (F_VERDE, F_ROJO), estado.nivel_co2, HISTERESIS_F)
    npm = 0 if pm25 is None else _nivel_con_histeresis(pm25, (PM_SENSIBLES, PM_DANINO),
                                                        estado.nivel_pm, HISTERESIS_PM)
    estado.nivel_co2, estado.nivel_pm = nc, npm

    entrando = fuente_pm == "exterior" or (pm25_tendencia is not None and pm25_tendencia >= TENDENCIA_ENTRADA)
    if nc == 0:
        accion = "nada" if npm == 0 else ("cerrar" if entrando else "abrir_parcial")
    elif npm >= 1:
        accion = "ventilar_corto"
    else:
        accion = "abrir_parcial" if nc == 1 else "abrir"

    t, x = TEXTOS[accion]
    return {"accion": accion, "titulo": t, "texto": x, "nivel": NIVEL[accion],
            "f": round(f, 5), "riesgoRelativo": round(rr, 2),
            "nivelCo2": nc, "nivelPm": npm}


# ---------------------------------------------------------------------------
# Utilidades para series
# ---------------------------------------------------------------------------

class MediaMovil:
    """Media móvil simple para suavizar el MH-Z19C (lecturas cada ~5-10 s)."""

    def __init__(self, n: int = 12):
        self.n = n
        self.buf: list[float] = []

    def __call__(self, x: float) -> float:
        self.buf.append(x)
        if len(self.buf) > self.n:
            self.buf.pop(0)
        return sum(self.buf) / len(self.buf)


def riesgo_acumulado(serie_co2: list, dt_horas: float, personas: int,
                     co2_exterior_ppm: float = CO2_EXTERIOR_PPM,
                     quanta_h: float = QUANTA_POR_HORA["influenza"]) -> dict:
    """Integra f en la jornada: P = 1 - exp(-q/n · ∫f dt) (forma no estacionaria)."""
    integral = sum(fraccion_reexhalada(c, co2_exterior_ppm) for c in serie_co2) * dt_horas
    horas = len(serie_co2) * dt_horas
    f_media = integral / horas if horas else 0.0
    return {
        "horas": horas,
        "f_media": f_media,
        "riesgo_relativo": riesgo_relativo(f_media, fraccion_reexhalada(CO2_REFERENCIA_PPM, co2_exterior_ppm)),
        "prob_contagio_ilustrativa": prob_contagio(f_media, horas, personas, 1, quanta_h),
    }
