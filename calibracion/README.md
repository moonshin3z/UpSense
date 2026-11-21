# UpSense · núcleo científico

Convierte lo que miden un PMS5003, un MH-Z19C y un BME280 en una sola instrucción para la maestra: **abrir, cerrar o ventilar 5 minutos**. Se apoya en dos hallazgos recientes:

| Hallazgo | Qué tomamos | Dónde está en el código |
|---|---|---|
| **Sitarek, Emerling y Schmidt 2026**, *Sensors* 26(21):6718, doi:[10.3390/s26216718](https://doi.org/10.3390/s26216718) | Corregir por software el error que la humedad mete en sensores ópticos baratos, usando T, HR y presión y modelos livianos (en su caso, polinomio, SVR y DNN llegan a R² 0.94). Ellos usan SDS011; aquí se adapta al PMS5003. | `calibrar()` |
| **Vouriot et al. 2024**, *J R Soc Interface*, doi:[10.1098/rsif.2024.0270](https://doi.org/10.1098/rsif.2024.0270) | Con un sensor de CO2 en el aula se estima la fracción de aire reexhalado y, con Wells-Riley en la forma de Rudnick y Milton 2003, el riesgo relativo de contagio por aire. | `recomendar()`, `fraccionReexhalada()` |

> **Ojo con las citas.** El enlace que circulaba como "Tastan 2026" (Chemosensors 14(7):154) es en realidad de **Gökozan**; usa como referencia un modelo de Open-Meteo, no un instrumento, y no trata la humedad a fondo. No lo citamos como base. El Taştan real es *Sensors* 25:3183 (2025), doi:10.3390/s25103183 (no lo he leído). No pude abrir el artículo de Vouriot 2024 desde aquí: **verificar** el valor de CO2 del aliento (usamos 38 000 ppm, el de Rudnick y Milton) y qué afirma exactamente sobre un solo sensor.

## Estructura

```
python/ventana/      librería (sin dependencias)
  features.py        variables derivadas: punto de rocío, dpd, hgf = rh/(100-rh)
  calib.py           calibrar(lectura, modelo)
  nucleo.py          CO2 → aire reexhalado → riesgo; corrección EPA; recomendar()
python/generar_datos_sinteticos.py   co-ubicación SINTÉTICA (física κ-Köhler)
python/entrenar.py   entrena y compara 6 métodos, exporta modelos/*.json
python/exportar_c.py genera c/ventana_modelo.h desde modelos/modelo.json
python/demo_aula.py  modo demo: mañana de clases, sensor crudo vs UpSense
js/ventana-calib.js  lo mismo para el dashboard (ES module)
c/ventana_calib.h    lo mismo para el ESP32 (header-only, float32)
modelos/             modelo.json (recomendado), métricas y gráficos
datos/               CSV sintético, demo_aula.json/.csv, vectores de prueba
pruebas/             paridad Python = JS = C
docs/                pitch y protocolo para datos reales
```

Reproducir todo:

```bash
cd python
pip install numpy scikit-learn matplotlib     # solo para entrenar y graficar
python generar_datos_sinteticos.py
python entrenar.py                 # o: python entrenar.py mis_datos_reales.csv
python exportar_c.py
python demo_aula.py
cd .. && python pruebas/generar_vectores.py && node pruebas/probar_js.mjs && python pruebas/probar_c.py
```

## Resultados (datos SINTÉTICOS, no reales)

Prueba con el 25 % más reciente de 60 días simulados a 10 min. "Falsas alarmas" = momentos en que el método dice PM2.5 > 35.4 µg/m³ y la referencia no.

| Método | R² | MAE µg/m³ | MAE con HR > 75 % | Falsas alarmas | Alarmas perdidas | Tamaño |
|---|---|---|---|---|---|---|
| Sensor crudo | −6.0 | 29.9 | 45.1 | 45.8 % | 0 % | — |
| Corrección EPA (EE. UU.) | −2.3 | 15.1 | 26.7 | 24.8 % | 0 % | — |
| Física κ-Köhler (2 parámetros) | 0.93 | 2.8 | 4.5 | 3.6 % | 4.2 % | 0.5 KB |
| **Polinomio con términos físicos** ✅ | **0.96** | **2.1** | **3.0** | **1.7 %** | 4.6 % | **0.7 KB** |
| Random Forest 30×8 | 0.91 | 2.2 | 3.1 | 2.2 % | 3.8 % | 159 KB |
| Gradient Boosting 150×3 | 0.95 | 2.0 | 2.8 | 2.8 % | 3.1 % | 57 KB |

Elegimos el **polinomio**: rinde como el mejor, pesa menos de 1 KB, corre en el ESP32 en microsegundos y se puede explicar (cada término es física: `pm25_cf1·hgf` es el crecimiento de la partícula al mojarse). Coincide con Sitarek 2026, donde la regresión polinómica empata con redes neuronales.

**Por qué estas cifras no se pueden citar todavía:** los datos los generé yo con un modelo físico, así que es lógico que un modelo con esa misma física acierte. Lo que sí demuestran es que el pipeline funciona de punta a punta. Para cifras reales, ver `docs/protocolo_datos_reales.md`. Que la corrección EPA salga mal aquí refleja mis supuestos (factor del sensor y κ), no una debilidad probada de la EPA.

Demo de aula (`python demo_aula.py`, simulado, 32 alumnos, mañana lluviosa con una quema real a las 11:00):

| | Maestra con sensor crudo | Maestra con UpSense |
|---|---|---|
| Minutos con falsa alarma de "aire sucio" | 173 | 12 |
| CO2 medio en clase | 1 595 ppm | 1 198 ppm |
| Aire reexhalado medio | 3.1 % | 2.0 % |
| Riesgo relativo de contagio (vs aula a 800 ppm) | 3.1× | 2.1× |

Con la quema real de las 11:00 UpSense **sí** avisa ("ventile 5 min y cierre"): corrige la humedad pero no esconde el humo de verdad.

## Interfaz para el firmware y el dashboard

**Dashboard (JS)**: copiar `js/ventana-calib.js` y `modelos/modelo.json` a la carpeta del dashboard.

```js
import { calibrar, recomendar, crearEstado, COLOR_LED } from './ventana-calib.js';
const modelo = await (await fetch('modelo.json')).json();   // si falla, null → EPA
const estado = crearEstado();                                  // uno por aula

const c = calibrar({ pm25_cf1, rh, temp, pressure }, modelo);
// → { pm25, crudo, metodo, alerta_humedad: null | 'dudosa' (HR>85) | 'niebla' (HR>95) }

const r = recomendar({
  co2,                                   // promedio 5 min
  pm25: c.alerta_humedad === 'niebla' ? null : c.pm25,   // con niebla, decide el CO2
  fuentePm: 'interior',                  // o 'exterior' si hay segundo equipo afuera
  pm25Tendencia,                         // cambio en ~10 min o null
}, estado);
// → { accion: 'abrir'|'abrir_parcial'|'cerrar'|'ventilar_corto'|'nada'|'sin_datos',
//     titulo, texto, nivel: 0-3, f, riesgoRelativo, nivelCo2, nivelPm }
```

El formato de `modelo.json` es el que propuso el hilo del prototipo (`tipo: "lineal"` con `features`, `coef`, `intercepto`; o `tipo: "arboles"` con arrays de sklearn). Las `features` pueden ser términos como `pm25_cf1*hgf^2`: `ventana-calib.js` los calcula a partir de las 4 variables crudas.

**ESP32 (C)**: copiar `c/ventana_calib.h` y `c/ventana_modelo.h` a `include/`.

```c
#include "ventana_calib.h"            // incluye ventana_modelo.h si existe
VentanaEstado est = {0, 0};
float pm = ventana_calibrar(pm25_cf1, rh, temp, presion);
VentanaRec r = ventana_recomendar(co2_5min, pm, false, tendencia_o_NAN, &est);
tira.fill(tira.Color(r.r, r.g, r.b));  // r.accion, r.nivel, r.f, r.riesgo_relativo
```

**Tira LED** (sugerido, WS2812B de 8 LEDs): verde `nada`, ámbar `abrir_parcial`, rojo `abrir`, morado `cerrar`, naranja parpadeando `ventilar_corto`, gris `sin_datos`. Para `ventilar_corto` se puede usar la tira como cuenta regresiva de 5 minutos (un LED se apaga cada ~37 s).

**Campo del PMS5003**: usar **CF=1** (bytes 4-5 de la trama, `pm25_cf1`), no el "atmosférico". Toda la calibración asume CF=1.

## Umbrales y por qué

| Umbral | Valor | Justificación |
|---|---|---|
| Aire reexhalado verde | < 1 % (≈ 805 ppm) | 800 ppm: objetivo de muchas guías escolares durante COVID-19 [POR CONFIRMAR cita] |
| Aire reexhalado rojo | ≥ 2 % (≈ 1 185 ppm) | Avisar antes de 1 500 ppm, la media diaria máxima de la guía británica BB101 2018 para ventilación natural [POR CONFIRMAR] |
| PM2.5 alto | > 35.4 µg/m³ | Corte "dañino para grupos sensibles" del AQI de la EPA (revisión 2024) |
| PM2.5 muy alto | > 55.4 µg/m³ | Corte "dañino" del AQI de la EPA |
| Humedad dudosa / niebla | 85 % / 95 % | Sitarek 2026 ve el error crecer fuerte sobre 60-80 %; con niebla el sensor cuenta gotitas |
| Histéresis | 0.15 % de f (≈ 57 ppm), 3 µg/m³ | Ruido del MH-Z19C (±50 ppm ± 5 %) para que el semáforo no parpadee |

## Suposiciones que hay que confirmar

- CO2 del aliento 38 000 ppm y CO2 exterior 425 ppm (medir en el patio el primer día).
- κ efectivo del PMS5003 (0.12-0.28 urbano, ~0.06 humo) y factor 1.6 del CF=1: inventados para la simulación con base en la literatura general; reemplazar con datos reales.
- Clima de la simulación (HR 45-98 %, 850 hPa) aproximado para la temporada de lluvias en el valle de Guatemala.
- Generación de CO2 por niño 0.0038 L/s (Persily y de Jonge 2017, rango de 8-11 años) y renovaciones por hora del aula (0.6 cerrada, 5 abierta).
- La duración de "ventilar 5 minutos" se basa en la práctica alemana de Stoßlüften, no en un estudio específico.
