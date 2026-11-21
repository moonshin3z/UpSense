#include "pms5003.h"

void Pms5003::begin(HardwareSerial& port, int rxPin, int txPin) {
  s_ = &port;
  s_->begin(9600, SERIAL_8N1, rxPin, txPin);
}

bool Pms5003::update() {
  bool got = false;
  while (s_ && s_->available()) {
    uint8_t c = s_->read();
    // Sincronizar con la cabecera 0x42 0x4D
    if (idx_ == 0 && c != 0x42) continue;
    if (idx_ == 1 && c != 0x4D) { idx_ = (c == 0x42) ? 1 : 0; continue; }
    buf_[idx_++] = c;
    if (idx_ == 32) {
      idx_ = 0;
      if (parse()) got = true; else bad_++;
    }
  }
  return got;
}

static inline uint16_t be16(const uint8_t* p) { return (uint16_t(p[0]) << 8) | p[1]; }

bool Pms5003::parse() {
  if (be16(buf_ + 2) != 28) return false;            // longitud de trama
  uint16_t sum = 0;
  for (int i = 0; i < 30; i++) sum += buf_[i];
  if (sum != be16(buf_ + 30)) return false;          // checksum
  d_.pm1_cf1 = be16(buf_ + 4);
  d_.pm25_cf1 = be16(buf_ + 6);
  d_.pm10_cf1 = be16(buf_ + 8);
  d_.pm1_atm = be16(buf_ + 10);
  d_.pm25_atm = be16(buf_ + 12);
  d_.pm10_atm = be16(buf_ + 14);
  d_.n03 = be16(buf_ + 16);
  d_.n05 = be16(buf_ + 18);
  d_.n10 = be16(buf_ + 20);
  d_.n25 = be16(buf_ + 22);
  d_.n50 = be16(buf_ + 24);
  d_.n100 = be16(buf_ + 26);
  d_.lastMs = millis();
  return true;
}
