#pragma once
#include <Arduino.h>

// Lectura del Plantower PMS5003 por UART (modo activo: el sensor envía
// una trama de 32 bytes aprox. cada 1 s). Parser no bloqueante, sin librerías.
struct PmsData {
  uint16_t pm1_cf1, pm25_cf1, pm10_cf1;  // "CF=1" (factor de fábrica); las correcciones tipo EPA usan estos
  uint16_t pm1_atm, pm25_atm, pm10_atm;  // "ambiente atmosférico" (lo que el fabricante sugiere mostrar)
  uint16_t n03, n05, n10, n25, n50, n100; // partículas >0.3/0.5/1/2.5/5/10 µm por 0.1 L
  uint32_t lastMs;                        // millis() de la última trama válida
};

class Pms5003 {
 public:
  void begin(HardwareSerial& port, int rxPin, int txPin);
  // Llamar en cada loop(). Devuelve true si llegó una trama nueva válida.
  bool update();
  const PmsData& data() const { return d_; }
  bool ok() const { return d_.lastMs && millis() - d_.lastMs < 5000; }
  uint32_t badFrames() const { return bad_; }

 private:
  HardwareSerial* s_ = nullptr;
  uint8_t buf_[32];
  uint8_t idx_ = 0;
  PmsData d_{};
  uint32_t bad_ = 0;
  bool parse();
};
