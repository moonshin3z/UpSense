# Genera diagrama-conexiones.svg. Pines = firmware/include/config.h
from html import escape as e
W, H = 1500, 1505
C5, C33, CG = "#d62828", "#e67700", "#222"
out = []
def a(s): out.append(s)
def box(x, y, w, h, title, sub, fill):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="#333" stroke-width="2"/>')
    a(f'<text x="{x+w/2}" y="{y+28}" text-anchor="middle" font-size="20" font-weight="700">{e(title)}</text>')
    a(f'<text x="{x+w/2}" y="{y+48}" text-anchor="middle" font-size="13" fill="#444">{e(sub)}</text>')
def pin(x, y, label, side, color="#111"):
    a(f'<circle cx="{x}" cy="{y}" r="5" fill="#fff" stroke="#333" stroke-width="2"/>')
    anchor, dx = ("start", 12) if side == "l" else ("end", -12)
    a(f'<text x="{x+dx}" y="{y+5}" font-size="14" text-anchor="{anchor}" fill="{color}">{e(label)}</text>')
def wire(pts, color, dash=False, w=3):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    da = ' stroke-dasharray="8 6"' if dash else ""
    a(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round"{da}/>')
def dot(x, y, c): a(f'<circle cx="{x}" cy="{y}" r="5" fill="{c}"/>')
def text(x, y, t, size=13, color="#333", weight=400, anchor="start"):
    a(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{e(t)}</text>')

a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter, Segoe UI, Roboto, Arial, sans-serif">')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(40, 44, "UpSense · diagrama de conexiones", 26, "#111", 800)
text(40, 68, "ESP32 DevKit + PMS5003 + MH-Z19C + BME280 (o BME680) + tira WS2812B. Pines según firmware/include/config.h.", 14, "#555")
text(40, 86, "El orden de los pines del ESP32 es esquemático: guíate por la serigrafía (GPIO16, GPIO4…) de tu placa.", 14, "#555")

# Rieles
R5, RG = 130, 160
wire([(40, R5), (1485, R5)], C5, w=5); wire([(40, RG), (1485, RG)], CG, w=5)
text(1485, R5 - 8, "riel 5 V", 13, C5, 700, "end"); text(110, RG + 18, "riel GND (todas las tierras unidas)", 13, CG, 700)
a(f'<rect x="590" y="96" width="320" height="22" rx="6" fill="#fff4f4" stroke="{C5}"/>')
text(750, 112, "Fuente 5 V ≥ 2 A (cargador USB o adaptador)", 13, "#111", 700, "middle")
wire([(700, 118), (700, R5)], C5); dot(700, R5, C5)
wire([(800, 118), (800, RG)], CG); dot(800, RG, CG)

# ESP32
EX, EY, EW, EH = 600, 260, 300, 480
box(EX, EY, EW, EH, "ESP32 DevKit", "38 pines, WROOM-32", "#eef4ff")
a(f'<rect x="{EX+105}" y="{EY+95}" width="90" height="70" rx="6" fill="#cfd8e6" stroke="#556"/>')
text(EX+150, EY+135, "WROOM", 12, "#334", 400, "middle")
a(f'<rect x="{EX+125}" y="{EY+EH-24}" width="50" height="24" rx="4" fill="#bbb" stroke="#555"/>')
text(EX+150, EY+EH-7, "USB", 11, "#111", 400, "middle")
L = {"GND": 320, "3V3": 360, "GPIO22": 440, "GPIO21": 490, "GPIO4": 620}
R = {"VIN": 320, "GND": 360, "GPIO17": 440, "GPIO16": 490, "GPIO26": 580, "GPIO27": 630}
pin(EX, L["GND"], "GND", "l"); pin(EX, L["3V3"], "3V3", "l", C33)
pin(EX, L["GPIO22"], "GPIO22 · SCL", "l"); pin(EX, L["GPIO21"], "GPIO21 · SDA", "l"); pin(EX, L["GPIO4"], "GPIO4 · datos LED", "l")
pin(EX+EW, R["VIN"], "VIN / 5V", "r", C5); pin(EX+EW, R["GND"], "GND", "r")
pin(EX+EW, R["GPIO17"], "GPIO17 · TX2", "r"); pin(EX+EW, R["GPIO16"], "GPIO16 · RX2", "r")
pin(EX+EW, R["GPIO26"], "GPIO26 · RX1", "r"); pin(EX+EW, R["GPIO27"], "GPIO27 · TX1", "r")
wire([(EX+EW, R["VIN"]), (950, R["VIN"]), (950, R5)], C5); dot(950, R5, C5)
wire([(EX+EW, R["GND"]), (975, R["GND"]), (975, RG)], CG); dot(975, RG, CG)
wire([(EX, L["GND"]), (565, L["GND"]), (565, RG)], CG); dot(565, RG, CG)

# PMS5003
PX, PY, PW, PH = 1130, 210, 300, 300
box(PX, PY, PW, PH, "PMS5003", "partículas · conector de 8 pines", "#fff8e6")
P = {"VCC": 270, "GND": 300, "SET": 330, "RX": 360, "TX": 390, "RESET": 420, "NC": 450}
pin(PX, P["VCC"], "1 VCC (5 V)", "l", C5); pin(PX, P["GND"], "2 GND", "l"); pin(PX, P["SET"], "3 SET (libre)", "l", "#888")
pin(PX, P["RX"], "4 RX", "l"); pin(PX, P["TX"], "5 TX", "l"); pin(PX, P["RESET"], "6 RESET (libre)", "l", "#888"); pin(PX, P["NC"], "7, 8 NC", "l", "#888")
wire([(PX, P["VCC"]), (1090, P["VCC"]), (1090, R5)], C5); dot(1090, R5, C5)
wire([(PX, P["GND"]), (1110, P["GND"]), (1110, RG)], CG); dot(1110, RG, CG)
wire([(PX, P["RX"]), (1010, P["RX"]), (1010, R["GPIO17"]), (EX+EW, R["GPIO17"])], "#4dabf7", dash=True)
wire([(PX, P["TX"]), (1050, P["TX"]), (1050, R["GPIO16"]), (EX+EW, R["GPIO16"])], "#1c7ed6")
text(PX+150, PY+PH-30, "RX es opcional (punteado). Lógica 3.3 V:", 12, "#666", 400, "middle")
text(PX+150, PY+PH-14, "va directo al ESP32, sin convertidor.", 12, "#666", 400, "middle")

# MH-Z19C (alimentación por la derecha)
MX, MY, MW, MH = 1130, 555, 300, 210
box(MX, MY, MW, MH, "MH-Z19C", "CO₂ NDIR · UART 9600", "#eefbf0")
M = {"TX": 580 + 30, "RX": 640 + 30}
M = {"TX": 610, "RX": 660}
pin(MX, M["TX"], "TX", "l"); pin(MX, M["RX"], "RX", "l")
pin(MX+MW, 640, "Vin (5 V)", "r", C5); pin(MX+MW, 690, "GND", "r")
wire([(MX+MW, 640), (1455, 640), (1455, R5)], C5); dot(1455, R5, C5)
wire([(MX+MW, 690), (1475, 690), (1475, RG)], CG); dot(1475, RG, CG)
wire([(MX, M["TX"]), (1050, M["TX"]), (1050, R["GPIO26"]), (EX+EW, R["GPIO26"])], "#2b8a3e")
wire([(MX, M["RX"]), (1010, M["RX"]), (1010, R["GPIO27"]), (EX+EW, R["GPIO27"])], "#69db7c")
text(MX+150, MY+MH-30, "HD, PWM y Vo sin conectar.", 12, "#666", 400, "middle")
text(MX+150, MY+MH-14, "Necesita 5 V estables (4.9 a 5.1 V).", 12, "#666", 400, "middle")

# BME280
BX, BY, BW, BH = 110, 210, 270, 275
box(BX, BY, BW, BH, "BME280 (o BME680)", "temp · humedad · presión · I²C", "#f3f0ff")
pin(BX+BW, 290, "GND", "r"); pin(BX+BW, 330, "VIN / VCC (3.3 V)", "r", C33)
pin(BX+BW, 380, "SCL", "r"); pin(BX+BW, 420, "SDA", "r")
wire([(BX+BW, 290), (405, 290), (405, RG)], CG); dot(405, RG, CG)
wire([(BX+BW, 330), (450, 330), (450, L["3V3"]), (EX, L["3V3"])], C33)
wire([(BX+BW, 380), (510, 380), (510, L["GPIO22"]), (EX, L["GPIO22"])], "#7048e8")
wire([(BX+BW, 420), (480, 420), (480, L["GPIO21"]), (EX, L["GPIO21"])], "#9775fa")
text(BX+BW/2, BY+BH-48, "¡A 3.3 V, no a 5 V!", 13, C33, 700, "middle")
text(BX+BW/2, BY+BH-30, "Dirección 0x76 o 0x77.", 12, "#666", 400, "middle")
text(BX+BW/2, BY+BH-14, "Junto a la entrada de aire del PMS5003.", 12, "#666", 400, "middle")

# WS2812B (alimentación por la izquierda)
SX, SY, SW, SH = 110, 590, 270, 200
box(SX, SY, SW, SH, "Tira WS2812B", "8 LEDs", "#fff0f6")
cols = ["#2f9e44", "#2f9e44", "#f59f00", "#f59f00", "#e03131", "#e03131", "#9c36b5", "#ced4da"]
for i, c in enumerate(cols):
    a(f'<rect x="{SX+16+i*30}" y="{SY+60}" width="24" height="24" rx="4" fill="{c}" stroke="#555"/>')
pin(SX, 700, "5V", "l", C5); pin(SX, 750, "GND", "l"); pin(SX+SW, 725, "DIN", "r")
wire([(SX, 700), (75, 700), (75, R5)], C5); dot(75, R5, C5)
wire([(SX, 750), (50, 750), (50, RG)], CG); dot(50, RG, CG)
# condensador entre 5V y GND, junto a la tira
wire([(75, 700), (75, 835)], C5); wire([(50, 750), (50, 835)], CG)
dot(75, 700, C5); dot(50, 750, CG)
a(f'<rect x="30" y="835" width="160" height="40" rx="6" fill="#e7f5ff" stroke="#1971c2" stroke-width="2"/>')
text(110, 852, "Condensador 1000 µF", 12, "#111", 700, "middle")
text(110, 867, "≥ 6.3 V, + al 5V, − al GND", 11, "#333", 400, "middle")
# resistencia en DIN
wire([(SX+SW, 725), (425, 725)], "#c2255c")
a(f'<rect x="425" y="714" width="64" height="22" rx="4" fill="#fff" stroke="#c2255c" stroke-width="2"/>')
text(457, 730, "330 Ω", 12, "#111", 700, "middle")
wire([(489, 725), (540, 725), (540, L["GPIO4"]), (EX, L["GPIO4"])], "#c2255c")
text(457, 755, "resistencia en serie,", 11, "#666", 400, "middle"); text(457, 769, "cerca de la tira", 11, "#666", 400, "middle")

# Leyenda
ly = 910
items = [(C5, "5 V"), (C33, "3.3 V"), (CG, "GND"), ("#1c7ed6", "UART PMS5003"), ("#2b8a3e", "UART MH-Z19C"), ("#7048e8", "I²C BME280"), ("#c2255c", "datos tira LED")]
x = 40
for c, t in items:
    a(f'<line x1="{x}" y1="{ly}" x2="{x+30}" y2="{ly}" stroke="{c}" stroke-width="4"/>')
    text(x+38, ly+5, t, 13)
    x += 60 + len(t) * 7.5

# Tabla pin a pin
ty = 950
text(40, ty, "Tabla pin a pin", 18, "#111", 800)
cols_x = [40, 230, 420, 640]
hdr = ["Componente", "Pin del componente", "Va a", "Nota"]
rows = [
 ("PMS5003", "1 VCC", "riel 5 V", "5 V obligatorio (ventilador)"),
 ("PMS5003", "2 GND", "riel GND", ""),
 ("PMS5003", "5 TX", "GPIO16 (RX2)", "datos del sensor al ESP32"),
 ("PMS5003", "4 RX", "GPIO17 (TX2)", "opcional; 3 SET, 6 RESET, 7, 8 libres"),
 ("MH-Z19C", "Vin", "riel 5 V", "4.9 a 5.1 V"),
 ("MH-Z19C", "GND", "riel GND", ""),
 ("MH-Z19C", "TX", "GPIO26 (RX1)", "lógica 3.3 V, directo"),
 ("MH-Z19C", "RX", "GPIO27 (TX1)", "HD, PWM, Vo libres"),
 ("BME280 / BME680", "VIN o VCC", "3V3 del ESP32", "nunca a 5 V si el módulo no tiene regulador"),
 ("BME280 / BME680", "GND", "riel GND", ""),
 ("BME280 / BME680", "SCL", "GPIO22", "I²C, dirección 0x76 o 0x77"),
 ("BME280 / BME680", "SDA", "GPIO21", ""),
 ("WS2812B", "5V", "riel 5 V", "condensador 1000 µF entre 5V y GND de la tira"),
 ("WS2812B", "GND", "riel GND", ""),
 ("WS2812B", "DIN", "GPIO4", "a través de resistencia de 330 Ω"),
 ("ESP32", "VIN / 5V", "riel 5 V", "si alimentas por USB, el riel sale de aquí (~4.7 V)"),
 ("ESP32", "GND", "riel GND", ""),
]
y = ty + 28
a(f'<rect x="36" y="{y-17}" width="1428" height="24" fill="#f1f3f5"/>')
for cx, h in zip(cols_x, hdr): text(cx, y, h, 13, "#111", 700)
for i, r in enumerate(rows):
    y += 24
    if i % 2: a(f'<rect x="36" y="{y-17}" width="1428" height="24" fill="#fafafa"/>')
    color = C5 if "5 V" in r[2] else (C33 if "3V3" in r[2] else "#111")
    for j, (cx, v) in enumerate(zip(cols_x, r)): text(cx, y, v, 13, color if j == 2 else "#222", 600 if j == 2 else 400)

y += 40
text(40, y, "Alimentación: con todo enchufado al USB del ESP32 funciona, pero el pin VIN da ~4.7 V. Para la demo, mejor una fuente de 5 V al riel y del riel al VIN del ESP32.", 13)
text(40, y + 20, "No conectes la fuente externa y el USB a la vez (salvo que tu placa tenga diodo en VIN). 8 LEDs a brillo 60/255 consumen menos de 150 mA.", 13)
text(40, y + 40, "Si la tira parpadea o da colores raros con datos a 3.3 V: acorta el cable de DIN o usa un convertidor de nivel (74AHCT125).", 13)
a('</svg>')
open("diagrama-conexiones.svg", "w").write("\n".join(out))
print(y + 60)
