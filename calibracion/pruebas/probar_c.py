"""Compila un programa C con ventana_calib.h y lo compara con los vectores de Python."""
import json, os, subprocess, sys, tempfile
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
V = json.load(open(os.path.join(RAIZ, "datos", "vectores_prueba.json")))
ACC = {"nada": 0, "abrir_parcial": 1, "abrir": 2, "cerrar": 3, "ventilar_corto": 4, "sin_datos": 5}
src = r'''
#include <stdio.h>
#include "ventana_calib.h"
int main(){ char t[16]; float a,b,c,d; VentanaEstado e={0,0};
 while(scanf("%15s",t)==1){
  if(t[0]=='C'){ scanf("%f %f %f %f",&a,&b,&c,&d);
    VentanaVars v=ventana_derivadas(a,b,c,d); float y=ventana_modelo_eval(&v); if(y<0)y=0;
    printf("%.4f %.4f\n", y, ventana_epa(a,b)); }
  else { int ext; scanf("%f %f %d %f",&a,&b,&ext,&c);
    VentanaRec r=ventana_recomendar(a,b,ext,c,&e); printf("%d %d\n", r.accion, r.nivel); } }
 return 0; }
'''
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "t.c"), "w").write(src)
    exe = os.path.join(d, "t")
    subprocess.run(["gcc", "-O2", "-Wall", "-I", os.path.join(RAIZ, "c"), os.path.join(d, "t.c"), "-o", exe, "-lm"], check=True)
    entrada = []
    for c in V["calibrar"]:
        l = c["lectura"]; entrada.append(f"C {l['pm25_cf1']} {l['rh']} {l['temp']} {l['pressure']}")
    for r in V["recomendar_secuencia"]:
        e = r["entrada"]; ten = "nan" if e["pm25Tendencia"] is None else e["pm25Tendencia"]
        entrada.append(f"R {e['co2']} {e['pm25']} {1 if e['fuentePm']=='exterior' else 0} {ten}")
    out = subprocess.run([exe], input="\n".join(entrada), capture_output=True, text=True, check=True).stdout.split("\n")
mal, peor = 0, 0.0
for i, c in enumerate(V["calibrar"]):
    y, epa = map(float, out[i].split())
    err = max(abs(y - c["modelo"]), abs(epa - c["epa"]))
    peor = max(peor, err)
    if err > 0.05: mal += 1
for j, r in enumerate(V["recomendar_secuencia"]):
    a, n = map(int, out[len(V["calibrar"]) + j].split())
    if a != ACC[r["accion"]] or n != r["nivel"]: mal += 1
print(f"C {'OK' if not mal else 'FALLA'}: {mal} diferencias; error máx. de PM2.5 en float32 = {peor:.4f} µg/m³")
sys.exit(1 if mal else 0)
