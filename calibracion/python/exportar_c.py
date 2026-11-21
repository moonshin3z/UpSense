"""
Genera c/ventana_modelo.h a partir de modelos/modelo.json (polinomio o κ-Köhler).

    python exportar_c.py [ruta/modelo.json]

Los modelos de árboles no se exportan a C a propósito: el polinomio pesa
<1 KB, corre en microsegundos en el ESP32 y en los datos de prueba rinde igual.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, ".."))


def termino_c(nombre):
    if nombre == "1":
        return "1.0f"
    partes = []
    for f in nombre.split("*"):
        if "^" in f:
            b, e = f.split("^")
            partes += [f"v->{b}"] * int(e)
        else:
            partes.append(f"v->{f}")
    return " * ".join(partes)


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "modelos", "modelo.json")
    m = json.load(open(ruta))
    lineas = ["/* GENERADO por python/exportar_c.py — no editar a mano */",
              f"/* modelo: {m['id']} · entrenado con: {m.get('entrenado_con')} */",
              f"/* métricas de prueba: {json.dumps(m.get('metricas_prueba'))} */",
              "/* Lo incluye ventana_calib.h automáticamente si está en la misma carpeta. */",
              "#ifndef VENTANA_MODELO_H", "#define VENTANA_MODELO_H", "",
              "static inline float ventana_modelo_eval(const VentanaVars *v) {"]
    if "kohler" in m:
        k = m["kohler"]
        lineas.append(f"  return v->pm25_cf1 / ({k['a']:.7g}f * (1.0f + {k['kappa']:.7g}f / 1.65f * v->hgf));")
    elif m["tipo"] == "lineal":
        lineas.append(f"  float y = {m.get('intercepto', 0):.9g}f;")
        for nombre, c in zip(m["features"], m["coef"]):
            lineas.append(f"  y += {c:.9g}f * ({termino_c(nombre)});")
        lineas.append("  return y;")
    else:
        sys.exit("Solo se exportan modelos 'lineal' o κ-Köhler a C.")
    lineas += ["}", "", "#endif", ""]
    out = os.path.join(RAIZ, "c", "ventana_modelo.h")
    open(out, "w").write("\n".join(lineas))
    print("→", out)


if __name__ == "__main__":
    main()
