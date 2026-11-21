#!/usr/bin/env python3
"""Simulador del monitor de aire: imita la API del ESP32 para desarrollar el
dashboard sin hardware. Solo usa la biblioteca estándar.

    python3 sim/simulador.py            # http://localhost:8000
    python3 sim/simulador.py --port 9000 --escenario humo

Escenarios (se repiten en un "día" de 24 h; el reloj avanza x60 si usas --rapido):
  aula   clase con CO2 subiendo, recreos con ventana abierta, mañana húmeda
         (el PMS5003 crudo exagera el PM2.5 por humedad: la falsa alarma)
  humo   igual, más un episodio de quema por la tarde (PM2.5 real alto afuera)
"""
import argparse, json, math, random, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DASH = Path(__file__).resolve().parent.parent / "dashboard"
INTERVAL = 60
HIST_LEN = 1440


class Aula:
    """Modelo muy simple del aula, en pasos de 1 minuto."""

    def __init__(self, escenario):
        self.escenario = escenario
        self.co2 = 450.0
        self.pm_in = 8.0

    def exterior(self, h):
        # PM2.5 exterior seco (µg/m³): base + horas pico de tráfico
        pm = 12 + 10 * math.exp(-((h - 7.5) ** 2) / 1.0) + 8 * math.exp(-((h - 18) ** 2) / 1.5)
        if self.escenario == "humo" and 14 <= h < 17:
            pm += 70 * math.sin(math.pi * (h - 14) / 3)
        rh = 70 + 22 * math.cos(2 * math.pi * (h - 5) / 24)  # húmedo de madrugada (~92 %)
        temp = 19 + 6 * math.cos(2 * math.pi * (h - 14) / 24)
        return pm, min(rh, 97), temp

    def step(self, h):
        pm_out, rh, temp = self.exterior(h)
        en_clase = 7 <= h < 13 and not (9.5 <= h < 10)  # recreo 9:30-10:00
        ventana = (not en_clase) or (self.escenario != "humo" and 11 <= h < 11.25)
        alumnos = 32 if en_clase else 0
        ach = 4.0 if ventana else 1.0  # renovaciones de aire por hora
        vol = 180.0  # m3
        # CO2: 0.005 L/s por alumno ~ 18 L/h -> ppm
        gen = alumnos * 15.0 / 1000 / vol * 1e6  # ppm/h (niño ~15 L/h de CO2)
        self.co2 += (gen - ach * (self.co2 - 420)) / 60
        self.pm_in += (ach * (0.8 * pm_out - self.pm_in) + (2.0 if en_clase else 0)) / 60
        rh_in = min(rh - 5, 95)
        return dict(co2=self.co2, pm=self.pm_in, rh=rh_in, temp=temp + 3)


def lectura_pms(pm_seco, rh):
    """Lo que reportaría un PMS5003: crece con la humedad y tiene ruido."""
    aw = min(rh, 95) / 100
    growth = 1 + (0.4 / 1.65) / (1 / aw - 1)  # κ-Köhler, κ=0.4
    cf1 = max(0, pm_seco * growth * 1.4 + random.gauss(0, 1.2))  # el PMS sobreestima ~40 %
    atm = cf1 if cf1 < 30 else 30 + (cf1 - 30) * 0.67  # forma aproximada CF1 -> atm
    return round(atm), round(cf1)


class Estado:
    def __init__(self, escenario, rapido):
        self.aula = Aula(escenario)
        self.rapido = rapido
        self.t0 = time.time()
        self.hist = []
        self.last = None
        # Pre-llenar 24 h de historial
        h_now = self.hora_sim()
        for i in range(HIST_LEN, 0, -1):
            h = (h_now - i / 60) % 24
            s = self.aula.step(h)
            atm, cf1 = lectura_pms(s["pm"], s["rh"])
            self.hist.append([-i * INTERVAL, round(atm * 0.7, 1), float(atm), float(cf1), round(atm * 1.3, 1),
                              round(s["co2"]), round(s["rh"], 1), round(s["temp"], 1)])
        self.last_min = int(self.uptime() // INTERVAL)
        self.vapor_t = None      # momento (real) en que se acercó vapor
        self.semaforo = None     # última decisión enviada por el dashboard

    def vapor(self):
        """Envolvente 0..1 de la prueba del vapor: sube en ~5 s, dura ~20 s, baja en ~40 s."""
        if self.vapor_t is None:
            return 0.0
        dt = time.time() - self.vapor_t
        if dt < 20:
            return 1 - math.exp(-dt / 5)
        v = (1 - math.exp(-4)) * math.exp(-(dt - 20) / 40)
        if v < 0.01:
            self.vapor_t = None
        return v

    def uptime(self):
        return (time.time() - self.t0) * (60 if self.rapido else 1)

    def hora_sim(self):
        lt = time.localtime()
        h = lt.tm_hour + lt.tm_min / 60 + lt.tm_sec / 3600
        return (h + (time.time() - getattr(self, "t0", time.time())) * (59 if self.rapido else 0) / 3600) % 24

    def ahora(self):
        h = self.hora_sim()
        m = int(self.uptime() // INTERVAL)
        while self.last_min < m:  # avanzar el modelo minuto a minuto
            self.last_min += 1
            s = self.aula.step(h)
            atm, cf1 = lectura_pms(s["pm"], s["rh"])
            self.hist.append([self.last_min * INTERVAL, round(atm * 0.7, 1), float(atm), float(cf1),
                              round(atm * 1.3, 1), round(s["co2"]), round(s["rh"], 1), round(s["temp"], 1)])
            self.hist = self.hist[-HIST_LEN:]
        a = self.aula
        _, rh, temp = a.exterior(h)
        v = self.vapor()
        rh_in = min(rh - 5 + v * (98 - (rh - 5)), 98)
        atm, cf1 = lectura_pms(a.pm_in, rh_in)
        if v:  # gotas de agua que el láser cuenta como partículas
            cf1 += round(140 * v)
            atm = cf1 if cf1 < 30 else round(30 + (cf1 - 30) * 0.67)
        warm = self.uptime() < 180 and not self.rapido
        return {
            "device": "aire-sim", "fw": "sim", "uptime": int(self.uptime()), "epoch": int(time.time()),
            "pms_ok": True, "co2_ok": True, "co2_warmup": warm,
            "pm1": round(atm * 0.7), "pm25": atm, "pm10": round(atm * 1.3),
            "pm1_cf1": round(cf1 * 0.7), "pm25_cf1": cf1, "pm10_cf1": round(cf1 * 1.3),
            "counts": [int(cf1 * 180), int(cf1 * 50), int(cf1 * 9), int(cf1), int(cf1 * .2), int(cf1 * .05)],
            "co2": None if warm else int(a.co2 + random.gauss(0, 8)),
            "temp": round(temp + 3 + random.gauss(0, .1), 1), "rh": round(rh_in + random.gauss(0, .5), 1),
            "pressure": 848.0,  # Ciudad de Guatemala ~1500 m
            "history_interval_s": INTERVAL,
            "semaforo": self.semaforo or {"accion": "local", "fuente": "local"},
            "_sim": {"hora": round(h, 2), "pm25_real_seco": round(a.pm_in, 1)},
        }

    def historial(self):
        return {"uptime": int(self.uptime()), "interval_s": INTERVAL,
                "fields": ["t", "pm1", "pm25", "pm25_cf1", "pm10", "co2", "rh", "temp"], "rows": self.hist}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--escenario", choices=["aula", "humo"], default="aula")
    ap.add_argument("--rapido", action="store_true", help="1 s real = 1 min simulado")
    args = ap.parse_args()
    st = Estado(args.escenario, args.rapido)

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(DASH), **k)

        def log_message(self, *a):
            pass

        def _json(self, obj):
            body = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n).decode() if n else ""
            if self.path.startswith("/api/sim/vapor"):
                st.vapor_t = time.time()
                return self._json({"vapor": True})
            if self.path.startswith("/api/semaforo"):
                from urllib.parse import parse_qs
                q = {k: v[0] for k, v in parse_qs(body).items()}
                st.semaforo = {"accion": q.get("accion", "?"), "nivel": q.get("nivel"), "fuente": "dashboard"}
                return self._json(st.semaforo)
            self.send_error(404)

        def do_GET(self):
            if self.path.startswith("/api/now"):
                return self._json(st.ahora())
            if self.path.startswith("/api/history"):
                st.ahora()
                return self._json(st.historial())
            return super().do_GET()

    print(f"Simulador ({args.escenario}) en http://localhost:{args.port}")
    ThreadingHTTPServer(("0.0.0.0", args.port), H).serve_forever()


if __name__ == "__main__":
    main()
