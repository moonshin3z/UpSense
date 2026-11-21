"""Genera datos/vectores_prueba.json con la versión Python (la de referencia)."""
import json, os, random, sys
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "python"))
from ventana import calibrar, cargar_modelo, recomendar, Estado

modelo = cargar_modelo(os.path.join(RAIZ, "modelos", "modelo.json"))
rnd = random.Random(1)
cal = []
for _ in range(300):
    l = {"pm25_cf1": round(rnd.uniform(0, 300), 1), "rh": round(rnd.uniform(20, 99), 1),
         "temp": round(rnd.uniform(8, 35), 1), "pressure": round(rnd.uniform(830, 1015), 1)}
    cal.append({"lectura": l, "modelo": calibrar(l, modelo)["pm25"], "epa": calibrar(l)["pm25"]})
rec, est = [], Estado()
co2, pm = 450.0, 10.0
for i in range(400):
    co2 = min(3000, max(400, co2 + rnd.gauss(0, 60)))
    pm = min(150, max(0, pm + rnd.gauss(0, 4)))
    ten = None if i % 7 == 0 else round(rnd.gauss(0, 5), 1)
    fuente = "exterior" if i % 5 == 0 else "interior"
    e = {"co2": round(co2), "pm25": round(pm, 1), "fuentePm": fuente, "pm25Tendencia": ten}
    r = recomendar(e["co2"], e["pm25"], fuente, ten, est)
    rec.append({"entrada": e, "accion": r["accion"], "nivel": r["nivel"], "f": r["f"]})
json.dump({"modelo": modelo["id"], "calibrar": cal, "recomendar_secuencia": rec},
          open(os.path.join(RAIZ, "datos", "vectores_prueba.json"), "w"))
print(len(cal), "vectores de calibración,", len(rec), "de recomendación")
