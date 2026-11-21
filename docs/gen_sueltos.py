# Genera conexiones-sueltas.svg: armado SIN protoboard. ESP32 DevKit de 38 pines,
# cables dupont directo a sus pines y dos conectores de palanca (5 V y GND).
# Pines = firmware/include/config.h. Uso: python3 docs/gen_sueltos.py
from html import escape as e
import os

W = 1720
RED, BLK, ORG, BLU = "#d62828", "#222222", "#f08c00", "#1c64d8"
GRN, PUR, WHT, BRN, YEL, GRY = "#2b9348", "#8e44ad", "#ffffff", "#8b5a2b", "#f5c400", "#9aa0a6"
out = ["@@HEAD@@"]
def a(s): out.append(s)
def text(x, y, t, size=14, color="#222", weight=400, anchor="start"):
    a(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{e(t)}</text>')
def path(pts, color, w=5, dash=False, ends=True):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    a(f'<path d="{d}" fill="none" stroke="#111" stroke-width="{w+3}" stroke-linejoin="round" stroke-linecap="round" opacity="0.85"/>')
    da = ' stroke-dasharray="10 7"' if dash else ""
    a(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{da}/>')
    if ends:
        for (x, y) in (pts[0], pts[-1]):
            a(f'<circle cx="{x}" cy="{y}" r="5.5" fill="{color}" stroke="#111" stroke-width="2"/>')
def badge(x, y, n):
    a(f'<circle cx="{x}" cy="{y}" r="12" fill="#fff" stroke="#111" stroke-width="2.5"/>')
    text(x, y + 5, str(n), 13, "#111", 800, "middle")
def comp(x, y, w, h, title, sub, fill, stroke):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    text(x + w / 2, y + 30, title, 19, "#111", 800, "middle")
    text(x + w / 2, y + 50, sub, 12, "#555", 500, "middle")
def pin(x, y, label, side, color="#111"):
    a(f'<rect x="{x-6}" y="{y-6}" width="12" height="12" fill="#e9c46a" stroke="#7a5c12" stroke-width="1.5"/>')
    if side == "r": text(x - 12, y + 5, label, 13, color, 800, "end")
    else: text(x + 12, y + 5, label, 13, color, 800, "start")

text(40, 48, "Monitor de aire · conexiones con componentes sueltos (sin protoboard)", 30, "#111", 800)
text(40, 76, "ESP32 DevKit de 38 pines + PMS5003 + MH-Z19C + BME280 + tira WS2812B. Cables dupont directo a los pines del ESP32;", 15, "#555")
text(40, 98, "Todo se alimenta del USB de la laptop: el pin 5V del ESP32 reparte 5 V y GND con dos conectores de palanca. Pines según firmware/include/config.h.", 15, "#555")

# ---------------------------------------------------------------- ESP32 (vista de arriba, antena arriba, USB abajo)
left = ["3V3", "EN", "VP", "VN", "34", "35", "32", "33", "25", "26", "27", "14", "12", "GND", "13", "SD2", "SD3", "CMD", "5V"]
right = ["GND", "23", "22", "TX", "RX", "21", "GND", "19", "18", "5", "17", "16", "4", "0", "2", "15", "SD1", "SD0", "CLK"]
used_l = {0, 9, 10, 13, 18}
used_r = {0, 2, 5, 10, 11, 12}
EXL, EXR, EY0 = 700, 1000, 340
def PL(i): return (EXL, EY0 + 30 * i)
def PR(i): return (EXR, EY0 + 30 * i)
a(f'<rect x="{EXL-14}" y="{EY0-110}" width="{EXR-EXL+28}" height="{30*18+170}" rx="10" fill="#1d2b4f" stroke="#0d1530" stroke-width="2"/>')
a(f'<rect x="{EXL+50}" y="{EY0-98}" width="{EXR-EXL-100}" height="150" rx="6" fill="#b9c0c9" stroke="#6b7480" stroke-width="2"/>')
a(f'<path d="M{EXL+80},{EY0-84} h20 v14 h-20 v14 h20 v14 h-20" fill="none" stroke="#6b7480" stroke-width="2"/>')
text((EXL + EXR) / 2, EY0 - 18, "ESP32-WROOM-32", 14, "#2a2f36", 800, "middle")
text((EXL + EXR) / 2, EY0 + 2, "(antena arriba)", 11, "#2a2f36", 600, "middle")
text((EXL + EXR) / 2, EY0 + 300, "ESP32 DevKit", 16, "#cfd8ea", 800, "middle")
text((EXL + EXR) / 2, EY0 + 320, "38 pines · vista de arriba", 12, "#cfd8ea", 600, "middle")
a(f'<rect x="{(EXL+EXR)/2-24}" y="{EY0+30*18+40}" width="48" height="30" rx="4" fill="#c9ced6" stroke="#555" stroke-width="2"/>')
text((EXL + EXR) / 2, EY0 + 30 * 18 + 60, "USB", 11, "#222", 800, "middle")
for i, n in enumerate(left):
    x, y = PL(i); u = i in used_l
    a(f'<rect x="{x-6}" y="{y-6}" width="12" height="12" fill="#e9c46a" stroke="#7a5c12" stroke-width="1.5"/>')
    if u: a(f'<rect x="{x+12}" y="{y-10}" width="{len(n)*8+8}" height="18" rx="3" fill="#ffe066"/>')
    text(x + 16, y + 5, n, 12, "#111" if u else "#c9d3e8", 800 if u else 500)
for i, n in enumerate(right):
    x, y = PR(i); u = i in used_r
    a(f'<rect x="{x-6}" y="{y-6}" width="12" height="12" fill="#e9c46a" stroke="#7a5c12" stroke-width="1.5"/>')
    if u: a(f'<rect x="{x-20-len(n)*8}" y="{y-10}" width="{len(n)*8+8}" height="18" rx="3" fill="#ffe066"/>')
    text(x - 16, y + 5, n, 12, "#111" if u else "#c9d3e8", 800 if u else 500, "end")

# ---------------------------------------------------------------- conectores de palanca
WT = 1180
def wago(x0, label, color, slots_lbl):
    w = 230
    a(f'<rect x="{x0}" y="{WT}" width="{w}" height="62" rx="8" fill="#eef1f4" stroke="{color}" stroke-width="3"/>')
    xs = [x0 + 25 + 45 * k for k in range(5)]
    for x, l in zip(xs, slots_lbl):
        a(f'<rect x="{x-13}" y="{WT+6}" width="26" height="34" rx="4" fill="#f7a400" stroke="#8a5a00" stroke-width="1.5"/>')
        a(f'<circle cx="{x}" cy="{WT}" r="6" fill="#555"/>')
        text(x, WT + 56, l, 10, "#333", 700, "middle")
    text(x0 + w / 2, WT + 84, label, 15, color, 800, "middle")
    return xs
S5 = wago(475, "CONECTOR 5 V (rojo)", RED, ["libre", "MH", "ESP", "PMS", "tira"])
SG = wago(815, "CONECTOR GND (negro)", BLK, ["libre", "MH", "ESP", "PMS", "tira"])

# ---------------------------------------------------------------- MH-Z19C (izquierda)
MX0, MX1, MY0 = 200, 520, 560
comp(MX0, MY0, MX1 - MX0, 220, "MH-Z19C", "sensor de CO₂", "#eefbf0", "#2b8a3e")
pin(MX1, PL(9)[1], "TX", "r"); pin(MX1, PL(10)[1], "RX", "r")
pin(MX1, 690, "Vin", "r", RED); pin(MX1, 720, "GND", "r")
text((MX0 + MX1) / 2 - 40, MY0 + 120, "HD, PWM y Vo:", 12, "#777", 500, "middle")
text((MX0 + MX1) / 2 - 40, MY0 + 136, "sin conectar", 12, "#777", 500, "middle")
text((MX0 + MX1) / 2 - 40, MY0 + 180, "Calienta 3 min", 13, "#2b8a3e", 800, "middle")
path([(MX1, PL(9)[1]), PL(9)], BLU); badge(560, PL(9)[1] - 14, 5)
path([(MX1, PL(10)[1]), PL(10)], PUR); badge(610, PL(10)[1] + 15, 6)

# ---------------------------------------------------------------- BME280 (arriba derecha)
BX0, BX1 = 1180, 1480
comp(BX0, 220, BX1 - BX0, 300, "BME280 (o BME680)", "temperatura · humedad · presión", "#f3f0ff", "#6741d9")
pin(BX0, 290, "VCC 3.3V", "l", ORG); pin(BX0, PR(0)[1], "GND", "l"); pin(BX0, PR(2)[1], "SCL", "l"); pin(BX0, PR(5)[1], "SDA", "l")
text(BX0 + 190, 430, "¡SOLO 3.3 V!", 15, "#c92a2a", 800, "middle")
text(BX0 + 190, 452, "nunca al conector de 5 V", 12, "#c92a2a", 700, "middle")
text(BX0 + 190, 480, "ponlo junto a la entrada", 12, "#555", 500, "middle")
text(BX0 + 190, 496, "de aire del PMS5003", 12, "#555", 500, "middle")
x3, y3 = PL(0)
path([(x3, y3), (650, y3), (650, 200), (1120, 200), (1120, 290), (BX0, 290)], ORG); badge(880, 200, 13)
path([PR(0), (BX0, PR(0)[1])], BLK); badge(1090, PR(0)[1] - 15, 14)
path([PR(2), (BX0, PR(2)[1])], BRN); badge(1090, PR(2)[1] - 15, 16)
path([PR(5), (BX0, PR(5)[1])], WHT); badge(1090, PR(5)[1] - 15, 15)

# ---------------------------------------------------------------- PMS5003 (derecha)
PY0 = 560
comp(BX0, PY0, BX1 - BX0, 220, "PMS5003", "partículas · conector de 8 pines", "#fff8e6", "#e67700")
pin(BX0, PR(10)[1], "4 RX", "l"); pin(BX0, PR(11)[1], "5 TX", "l")
pin(BX0, 710, "1 VCC", "l", RED); pin(BX0, 740, "2 GND", "l")
text(BX0 + 200, PY0 + 150, "usa el número de pin,", 12, "#555", 600, "middle")
text(BX0 + 200, PY0 + 166, "no el color del cable", 12, "#555", 600, "middle")
text(BX0 + 200, PY0 + 190, "4 RX opcional (punteado)", 12, "#555", 500, "middle")
path([PR(10), (BX0, PR(10)[1])], GRY, dash=True); badge(1090, PR(10)[1] - 15, 10)
path([PR(11), (BX0, PR(11)[1])], GRN); badge(1140, PR(11)[1] - 15, 9)

# ---------------------------------------------------------------- Tira WS2812B (derecha abajo) + resistencia + capacitor
TX0, TY0 = 1240, 820
comp(TX0, TY0, 440, 150, "Tira WS2812B · 8 LEDs", "extremo de ENTRADA (DIN)", "#fff0f6", "#c2255c")
for k, col in enumerate(["#2b9348", "#2b9348", "#f59f00", "#f59f00", "#e03131", "#e03131", "#9c36b5", "#ced4da"]):
    a(f'<rect x="{TX0+90+k*40}" y="{TY0+70}" width="28" height="28" rx="5" fill="{col}" stroke="#333"/>')
a(f'<path d="M{TX0+90},{TY0+118} h310" stroke="#c2255c" stroke-width="2" marker-end="url(#fl2)"/>')
a('<defs><marker id="fl2" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#c2255c"/></marker></defs>')
text(TX0 + 245, TY0 + 138, "sentido de los datos (flechas impresas)", 11, "#c2255c", 600, "middle")
pin(TX0, 850, "DIN", "l"); pin(TX0, 890, "5V", "l", RED); pin(TX0, 930, "GND", "l")
# GPIO4 -> resistencia -> DIN
gx, gy = PR(12)
path([(gx, gy), (1040, gy), (1040, 850), (1168, 850)], YEL); badge(1062, 780, 11)
a(f'<line x1="1168" y1="850" x2="1236" y2="850" stroke="#888" stroke-width="3"/>')
a('<rect x="1176" y="840" width="54" height="20" rx="9" fill="#e8d3a6" stroke="#8a6d3b" stroke-width="1.5"/>')
for k, col in enumerate(["#f08c00", "#f08c00", "#8b5a2b", "#c9a227"]):
    a(f'<rect x="{1184+k*11}" y="840" width="5" height="20" fill="{col}"/>')
text(1203, 832, "330 Ω", 12, "#111", 800, "middle")
path([(1236, 850), (TX0, 850)], YEL, ends=False); badge(1150, 830, 12)
# capacitor en los pads de la tira (entre 5V y GND)
cxp = 1205
a(f'<rect x="{cxp-14}" y="{892}" width="28" height="36" rx="6" fill="#1f3a93" stroke="#0d1d55" stroke-width="2"/>')
a(f'<rect x="{cxp-14}" y="{918}" width="28" height="10" rx="3" fill="#c7d2fe"/>')
text(cxp, 912, "+", 13, "#fff", 900, "middle")
text(cxp + 34, 960, "1000 µF", 11, "#1f3a93", 800, "middle")

# ---------------------------------------------------------------- cables al reparto 5 V / GND
def lane_route(src, xturn, lane, slot, color):
    pts = [src, (xturn, src[-1]), (xturn, lane), (slot, lane), (slot, WT)]
    path(pts, color)
# MH-Z19C
lane_route((MX1, 690), 560, 960, S5[1], RED); badge(545, 990, 3)
lane_route((MX1, 720), 530, 1110, SG[1], BLK); badge(515, 1085, 4)
# ESP32 5V y GND (lado izquierdo)
lane_route(PL(18), 670, 980, S5[2], RED); badge(686, 935, 1)
lane_route(PL(13), 640, 1090, SG[2], BLK); badge(624, 810, 2)
# PMS5003
lane_route((BX0, 710), 1100, 1010, S5[3], RED); badge(1100, 980, 7)
lane_route((BX0, 740), 1120, 1030, SG[3], BLK); badge(1135, 990, 8)
# Tira
lane_route((TX0, 890), 1140, 1050, S5[4], RED); badge(1160, 1030, 17)
lane_route((TX0, 930), 1160, 1070, SG[4], BLK); badge(1180, 1080, 18)
# capacitor entre los cables de la tira
a(f'<line x1="{cxp}" y1="890" x2="{cxp}" y2="892" stroke="#999" stroke-width="3"/>')
a(f'<line x1="{cxp}" y1="928" x2="{cxp}" y2="930" stroke="#999" stroke-width="3"/>')
badge(cxp + 30, 905, 19)

# ---------------------------------------------------------------- compu (alimentación por USB)
ux = (EXL + EXR) / 2
uy = EY0 + 30 * 18 + 70
LX0, LY0 = 1120, 1170
a(f'<rect x="{LX0}" y="{LY0}" width="260" height="140" rx="10" fill="#e9ecef" stroke="#495057" stroke-width="2"/>')
a(f'<rect x="{LX0+20}" y="{LY0+16}" width="220" height="80" rx="4" fill="#343a40"/>')
text(LX0 + 130, LY0 + 62, "Laptop", 16, "#fff", 800, "middle")
text(LX0 + 130, LY0 + 124, "alimenta todo por USB", 12, "#333", 700, "middle")
path([(ux, uy), (ux, 1150), (1080, 1150), (1080, LY0 + 50), (LX0, LY0 + 50)], "#868e96", 7, ends=False)
text(1090, 1140, "cable USB de datos", 12, "#495057", 700)
# ---------------------------------------------------------------- leyenda
lx, ly = 80, 250
items = [(RED, "5 V"), (ORG, "3.3 V"), (BLK, "GND"), (GRN, "PMS TX → GPIO16"), (GRY, "PMS RX (opcional)"),
         (BLU, "MH TX → GPIO26"), (PUR, "MH RX → GPIO27"), (WHT, "SDA → GPIO21"), (BRN, "SCL → GPIO22"), (YEL, "datos LED (GPIO4)")]
a(f'<rect x="{lx-14}" y="{ly-26}" width="250" height="{len(items)*20+40}" rx="10" fill="#fafafa" stroke="#ddd"/>')
text(lx, ly - 6, "Colores sugeridos", 13, "#111", 800)
for i, (c, l) in enumerate(items):
    yy = ly + 16 + i * 20
    a(f'<line x1="{lx}" y1="{yy-4}" x2="{lx+30}" y2="{yy-4}" stroke="#111" stroke-width="8" stroke-linecap="round"/>')
    a(f'<line x1="{lx}" y1="{yy-4}" x2="{lx+30}" y2="{yy-4}" stroke="{c}" stroke-width="5" stroke-linecap="round"/>')
    text(lx + 42, yy, l, 12, "#222")

# ---------------------------------------------------------------- tabla de cables
TY = 1370
a(f'<line x1="40" y1="{TY-30}" x2="{W-40}" y2="{TY-30}" stroke="#ddd" stroke-width="2"/>')
text(40, TY, "Tabla de cables (el número es el del dibujo)", 20, "#111", 800)
rows = [
    ("1", "ESP32 5V (abajo izq.)", "conector 5 V", "rojo", "de aquí sale el 5 V del USB"),
    ("2", "ESP32 GND (izq., entre 12 y 13)", "conector GND", "negro", "hembra-macho"),
    ("3", "MH-Z19C Vin", "conector 5 V", "rojo", ""),
    ("4", "MH-Z19C GND", "conector GND", "negro", ""),
    ("5", "MH-Z19C TX", "ESP32 26", "azul", "hembra-hembra"),
    ("6", "MH-Z19C RX", "ESP32 27", "morado", "hembra-hembra"),
    ("7", "PMS5003 pin 1 VCC", "conector 5 V", "rojo", ""),
    ("8", "PMS5003 pin 2 GND", "conector GND", "negro", ""),
    ("9", "PMS5003 pin 5 TX", "ESP32 16", "verde", ""),
    ("10", "PMS5003 pin 4 RX", "ESP32 17", "gris", "opcional"),
    ("11", "ESP32 4", "resistencia 330 Ω", "amarillo", "aislar con cinta"),
    ("12", "resistencia 330 Ω", "tira DIN", "amarillo", ""),
    ("13", "BME280 VCC", "ESP32 3V3 (arriba izq.)", "naranja", "¡NUNCA a 5 V!"),
    ("14", "BME280 GND", "ESP32 GND (arriba der.)", "negro", ""),
    ("15", "BME280 SDA", "ESP32 21", "blanco", ""),
    ("16", "BME280 SCL", "ESP32 22", "café", ""),
    ("17", "Tira 5V", "conector 5 V", "rojo", ""),
    ("18", "Tira GND", "conector GND", "negro", ""),
    ("19", "Capacitor 1000 µF", "pads 5V (+) y GND (−) de la tira", "—", "pata larga = +"),
]
cols = [40, 90, 420, 760, 880]
hdr = ["#", "Desde", "Hasta", "Color", "Nota"]
half = 10
for blk in range(2):
    ox = blk * 840
    yy = TY + 34
    a(f'<rect x="{ox+30}" y="{yy-18}" width="820" height="26" fill="#f1f3f5"/>')
    cx = [ox + 40, ox + 75, ox + 330, ox + 600, ox + 690]
    for x, h in zip(cx, hdr): text(x, yy, h, 13, "#111", 800)
    for k, r in enumerate(rows[blk * half:(blk + 1) * half]):
        y = yy + 26 * (k + 1)
        if k % 2: a(f'<rect x="{ox+30}" y="{y-18}" width="820" height="26" fill="#fafafa"/>')
        for j, (x, v) in enumerate(zip(cx, r)):
            text(x, y, v, 13, "#c92a2a" if "NUNCA" in v or "FINAL" in v else "#222", 800 if j == 0 else 400)

# ---------------------------------------------------------------- pasos
SY = TY + 34 + 26 * (half + 1) + 40
text(40, SY, "Pasos (todo con el USB desconectado; la laptop se conecta al final)", 20, "#111", 800)
pasos = [
    ("Prepara los conectores:", "uno para 5 V y otro para GND, etiquetados con cinta roja y negra. La punta macho del dupont entra en el conector de palanca."),
    ("ESP32:", "[1] pin 5V → conector 5 V (de aquí sale la energía del USB) · [2] pin GND (lado izquierdo, entre 12 y 13) → conector GND."),
    ("MH-Z19C:", "[3] Vin → conector 5 V · [4] GND → conector GND · [5] TX → pin 26 · [6] RX → pin 27."),
    ("PMS5003:", "[7] pin 1 VCC → conector 5 V · [8] pin 2 GND → conector GND · [9] pin 5 TX → pin 16 · [10] pin 4 RX → pin 17 (opcional)."),
    ("BME280:", "[13] VCC → pin 3V3 del ESP32 · [14] GND → pin GND de arriba a la derecha · [15] SDA → pin 21 · [16] SCL → pin 22."),
    ("Resistencia:", "[11] pin 4 → una pata de la resistencia de 330 Ω · [12] la otra pata → DIN de la tira. Cubre la resistencia con cinta o termoencogible."),
    ("Tira y capacitor:", "[17] 5V → conector 5 V · [18] GND → conector GND · [19] capacitor en la entrada de la tira: pata larga al 5V, franja al GND (soldado o enroscado y aislado)."),
    ("Revisa antes de conectar el USB:", "con el multímetro en continuidad, los conectores de 5 V y GND NO deben pitar entre sí; el VCC del BME280 debe ir al 3V3."),
    ("Conecta el USB a la laptop:", "con eso se enciende todo y también sirve para programar. Espera 3 minutos antes de creer el CO₂."),
]
yy = SY + 36
for i, (b, t) in enumerate(pasos, 1):
    a(f'<circle cx="56" cy="{yy-5}" r="13" fill="#111"/>')
    text(56, yy, str(i), 13, "#fff", 800, "middle")
    a(f'<text x="80" y="{yy}" font-size="15" fill="#222"><tspan font-weight="800">{e(b)}</tspan> {e(t)}</text>')
    yy += 32

CY = yy + 24
text(40, CY, "Materiales", 20, "#111", 800)
mats = ["1 ESP32 DevKit de 38 pines", "1 PMS5003 con su cable (8 pines)", "1 MH-Z19C", "1 módulo BME280 (o BME680)",
        "1 tira WS2812B de 8 LEDs con cables en DIN", "2 conectores de palanca de 4 o 5 entradas (tipo Wago 221)",
        "1 resistencia 330 Ω (1/4 W)", "1 capacitor electrolítico 1000 µF, 10 V o más", "1 laptop con puerto USB (mejor USB 3, el azul)",
        "~8 cables hembra-hembra, ~12 hembra-macho", "Cinta aislante o termoencogible", "Cable USB de datos (no solo de carga) y multímetro"]
for i, m in enumerate(mats): text(60, CY + 32 + i * 24, "• " + m, 14, "#222")
AX = 640
adv = [
    ("BME280 solo a 3.3 V:", "va al pin 3V3 del ESP32, nunca al conector de 5 V."),
    ("Polaridad del capacitor:", "pata larga = +, franja = −. Al revés puede reventar."),
    ("MH-Z19C tarda 3 min en calentar:", "ignora el CO₂ de los primeros 3 minutos."),
    ("TX del sensor va a RX del ESP32", "(ya está así). Si no llegan datos, invierte TX y RX."),
    ("Tira:", "conecta el extremo DIN, no el DOUT. Cables de datos lo más cortos posible."),
    ("Consumo por USB (~0.5 A):", "deja el brillo de la tira en 60. Si el ESP32 se reinicia,"),
    ("", "usa un puerto USB 3 o un hub con fuente, y no pongas la tira en blanco total."),
    ("Aísla todo lo que quede al aire", "(resistencia, patas del capacitor) para evitar cortos."),
    ("Guíate por el nombre impreso del pin:", "si tu placa tiene otro orden, avisa antes."),
    ("Sin conectores de palanca:", "sirve una regleta de tornillos, o unir y soldar los cables."),
]
a(f'<rect x="{AX-20}" y="{CY-30}" width="{W-40-AX+20}" height="{32+len(adv)*28+16}" rx="12" fill="#fff5f5" stroke="#e03131" stroke-width="2"/>')
text(AX, CY, "⚠ Advertencias", 20, "#c92a2a", 800)
for i, (b, t) in enumerate(adv):
    a(f'<text x="{AX}" y="{CY+32+i*28}" font-size="14" fill="#222"><tspan font-weight="800">{e(b)}</tspan> {e(t)}</text>')

H = int(max(CY + 32 + len(mats) * 24, CY + 32 + len(adv) * 28) + 50)
out[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter, Segoe UI, Roboto, Arial, sans-serif">'
          f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
a("</svg>")
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "conexiones-sueltas.svg"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(W, H)
