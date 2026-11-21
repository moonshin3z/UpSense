#pragma once
// ============================================================
//  Configuración del monitor. Edita esto antes de compilar.
// ============================================================

// --- WiFi ---------------------------------------------------
// Si no logra conectarse en WIFI_TIMEOUT_MS, levanta su propia red
// (modo punto de acceso) para que el demo funcione sin internet.
#define WIFI_SSID        "TU_RED"
#define WIFI_PASSWORD    "TU_CLAVE"
#define WIFI_TIMEOUT_MS  15000
#define AP_SSID          "MonitorAire"
#define AP_PASSWORD      "aire1234"      // mínimo 8 caracteres
#define MDNS_NAME        "aire"          // http://aire.local
#define DEVICE_ID        "aire-01"

// --- Pines (ESP32 DevKit) ----------------------------------
// PMS5003: TX del sensor -> PMS_RX_PIN. El RX del sensor puede ir a PMS_TX_PIN
// (solo hace falta para modo pasivo/suspensión). Alimentación 5 V, lógica 3.3 V.
#define PMS_RX_PIN   16
#define PMS_TX_PIN   17
// MH-Z19C: TX del sensor -> MHZ_RX_PIN, RX del sensor -> MHZ_TX_PIN. Alimentación 5 V.
#define MHZ_RX_PIN   26
#define MHZ_TX_PIN   27
// BME280 (opcional, env esp32dev_bme280): SDA 21, SCL 22, dirección 0x76 o 0x77
#define I2C_SDA      21
#define I2C_SCL      22

// --- Tira LED WS2812 (semáforo físico) ---------------------
// DIN de la tira -> LED_PIN (pon una resistencia de ~330 Ω en serie y un
// condensador de 1000 µF entre 5 V y GND de la tira). Alimentar a 5 V.
#define LED_PIN     4
#define LED_COUNT   8
#define LED_BRILLO  60      // 0-255; ojo con el consumo (~60 mA por LED a blanco total)
// Colores: los define el núcleo (ventana_calib.h): verde nada, ámbar abrir un
// poco (media tira), rojo abrir ya, morado cerrar, naranja parpadeando =
// ventilar 5 min (cuenta regresiva), gris respirando = sin datos.
// Con posible falsa alarma por humedad, el último LED queda en blanco tenue.
#define VENTILAR_MS   300000UL   // duración de la cuenta regresiva de "ventilar 5 min"

// Guardia de humedad (PM no fiable): niebla o subida brusca (vapor, trapear, lluvia)
#define HR_NIEBLA          95.0f   // %, igual que RH_NIEBLA del núcleo
#define HR_SUBIDA_RAPIDA    6.0f   // puntos de % sobre el mínimo de los últimos 2 min

// --- Muestreo ----------------------------------------------
#define CO2_QUERY_MS        5000     // cada cuánto se consulta el MH-Z19C
#define CO2_WARMUP_MS       180000   // el MH-Z19C da lecturas poco fiables los primeros ~3 min
#define HISTORY_INTERVAL_S  60       // promedio guardado en el historial
#define HISTORY_LEN         1440     // 1440 x 60 s = 24 h en RAM (se pierde al reiniciar)

// Calibración automática (ABC) del MH-Z19C: asume que una vez al día ve
// aire exterior (~420 ppm). En interiores que nunca se ventilan, apágala.
#define MHZ_ABC_ON  true

// --- Envío opcional a un servidor ---------------------------
// Si defines PUSH_URL, cada HISTORY_INTERVAL_S hace POST del JSON de /api/now.
// #define PUSH_URL "http://192.168.1.50:8000/api/ingest"
