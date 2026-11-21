# Armado del monitor de aire con componentes sueltos (sin protoboard)

Diagrama: [conexiones-sueltas.png](conexiones-sueltas.png) (editable: `conexiones-sueltas.svg`, se regenera con `python3 docs/gen_sueltos.py`).
ESP32 DevKit de 38 pines. Cables dupont directo a los pines del ESP32. Todo se alimenta del USB de la laptop: el pin 5V del ESP32 alimenta un conector de palanca de 5 V y el GND va a otro conector de palanca. Pines según `firmware/include/config.h`.

## Materiales

- 1 ESP32 DevKit de 38 pines
- 1 PMS5003 con su cable (8 pines)
- 1 MH-Z19C
- 1 módulo BME280 (o BME680)
- 1 tira WS2812B de 8 LEDs con cables en la entrada (DIN)
- 2 conectores de palanca de 4 o 5 entradas (tipo Wago 221), o una regleta de tornillos
- 1 resistencia de 330 Ω, 1/4 W (naranja-naranja-café)
- 1 capacitor electrolítico de 1000 µF, 10 V o más
- 1 laptop con puerto USB (mejor USB 3, el azul) y un cable USB de datos (no solo de carga)
- ~8 cables hembra-hembra y ~12 hembra-macho
- Cinta aislante o termoencogible, multímetro

## Tabla de cables

| # | Desde | Hasta | Color | Nota |
|---|---|---|---|---|
| 1 | ESP32 5V (abajo a la izquierda) | conector 5 V | rojo | de aquí sale el 5 V del USB |
| 2 | ESP32 GND (izquierda, entre 12 y 13) | conector GND | negro | |
| 3 | MH-Z19C Vin | conector 5 V | rojo | |
| 4 | MH-Z19C GND | conector GND | negro | |
| 5 | MH-Z19C TX | ESP32 26 | azul | |
| 6 | MH-Z19C RX | ESP32 27 | morado | |
| 7 | PMS5003 pin 1 VCC | conector 5 V | rojo | |
| 8 | PMS5003 pin 2 GND | conector GND | negro | |
| 9 | PMS5003 pin 5 TX | ESP32 16 | verde | |
| 10 | PMS5003 pin 4 RX | ESP32 17 | gris | opcional |
| 11 | ESP32 4 | resistencia 330 Ω | amarillo | aislar con cinta |
| 12 | resistencia 330 Ω | tira DIN | amarillo | |
| 13 | BME280 VCC | ESP32 3V3 (arriba a la izquierda) | naranja | **nunca a 5 V** |
| 14 | BME280 GND | ESP32 GND (arriba a la derecha) | negro | |
| 15 | BME280 SDA | ESP32 21 | blanco | |
| 16 | BME280 SCL | ESP32 22 | café | |
| 17 | Tira 5V | conector 5 V | rojo | |
| 18 | Tira GND | conector GND | negro | |
| 19 | Capacitor 1000 µF | pads 5V (+) y GND (−) de la entrada de la tira | — | pata larga = + |

## Pasos (todo con el USB desconectado; la laptop se conecta al final)

1. Prepara los conectores: uno para 5 V y otro para GND, etiquetados con cinta roja y negra. La punta macho del dupont entra en el conector de palanca.
2. ESP32: [1] pin 5V → conector 5 V · [2] pin GND (lado izquierdo, entre 12 y 13) → conector GND.
3. MH-Z19C: [3] Vin → conector 5 V · [4] GND → conector GND · [5] TX → pin 26 · [6] RX → pin 27. HD, PWM y Vo sin conectar.
4. PMS5003 (usa el número de pin, no el color del cable): [7] pin 1 VCC → conector 5 V · [8] pin 2 GND → conector GND · [9] pin 5 TX → pin 16 · [10] pin 4 RX → pin 17 (opcional).
5. BME280: [13] VCC → pin 3V3 del ESP32 · [14] GND → pin GND de arriba a la derecha · [15] SDA → pin 21 · [16] SCL → pin 22.
6. Resistencia: [11] pin 4 → una pata de la resistencia de 330 Ω · [12] la otra pata → DIN de la tira. Cubre la resistencia con cinta o termoencogible.
7. Tira y capacitor: [17] 5V → conector 5 V · [18] GND → conector GND · [19] capacitor en la entrada de la tira, pata larga al 5V y franja al GND (soldado, o enroscado y aislado).
8. Revisa antes de conectar el USB: con el multímetro en continuidad, los conectores de 5 V y GND no deben pitar entre sí, y el VCC del BME280 debe ir al 3V3.
9. Conecta el USB a la laptop: con eso se enciende todo y también sirve para programar. Espera 3 minutos antes de creer el CO₂.

## Advertencias

- **BME280 solo a 3.3 V:** va al pin 3V3 del ESP32, nunca al conector de 5 V.
- **Polaridad del capacitor:** pata larga = +, franja = −. Al revés puede reventar.
- **MH-Z19C tarda 3 minutos en calentar:** ignora el CO₂ de los primeros 3 minutos.
- El TX de cada sensor va al RX del ESP32 (ya está así). Si no llegan datos, invierte TX y RX de ese sensor.
- Conecta la tira por el extremo DIN, no por DOUT. Cables de datos lo más cortos posible.
- **Consumo por USB (~0.5 A en el peor caso):** deja el brillo de la tira en 60 (`LED_BRILLO` en config.h). Si el ESP32 se reinicia, usa un puerto USB 3 o un hub con fuente, y no pongas la tira en blanco total.
- Aísla todo lo que quede al aire (resistencia, patas del capacitor) para evitar cortos.
- Guíate por el nombre impreso del pin. Si tu placa tiene otro orden, avisa antes de conectar.
- Sin conectores de palanca sirve una regleta de tornillos, o unir y soldar los cables.
