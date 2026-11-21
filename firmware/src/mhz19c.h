#pragma once
#include <Arduino.h>

// Winsen MH-Z19C (CO2 por NDIR) por UART, 9600 baud.
// Se consulta con el comando 0x86 y responde 9 bytes. Sin librerías.
class MhZ19c {
 public:
  void begin(HardwareSerial& port, int rxPin, int txPin);
  // Envía la consulta si toca (cada periodMs) y procesa la respuesta.
  // Devuelve true si hay una lectura nueva.
  bool update(uint32_t periodMs);
  int ppm() const { return ppm_; }
  bool ok() const { return lastMs_ && millis() - lastMs_ < 20000; }
  bool warmingUp(uint32_t warmupMs) const { return millis() < warmupMs; }
  void setABC(bool on);
  void calibrateZero();  // SOLO con el sensor 20+ min en aire exterior (~420 ppm)

 private:
  HardwareSerial* s_ = nullptr;
  uint8_t buf_[9];
  uint8_t idx_ = 0;
  int ppm_ = -1;
  uint32_t lastMs_ = 0, lastQuery_ = 0;
  void send(uint8_t cmd, uint8_t b3 = 0, uint8_t b4 = 0);
  static uint8_t checksum(const uint8_t* p);
};
