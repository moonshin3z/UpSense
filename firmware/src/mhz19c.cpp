#include "mhz19c.h"

void MhZ19c::begin(HardwareSerial& port, int rxPin, int txPin) {
  s_ = &port;
  s_->begin(9600, SERIAL_8N1, rxPin, txPin);
}

uint8_t MhZ19c::checksum(const uint8_t* p) {
  uint8_t sum = 0;
  for (int i = 1; i < 8; i++) sum += p[i];
  return 0xFF - sum + 1;
}

void MhZ19c::send(uint8_t cmd, uint8_t b3, uint8_t b4) {
  uint8_t f[9] = {0xFF, 0x01, cmd, b3, b4, 0, 0, 0, 0};
  f[8] = checksum(f);
  s_->write(f, 9);
}

void MhZ19c::setABC(bool on) { send(0x79, on ? 0xA0 : 0x00); }
void MhZ19c::calibrateZero() { send(0x87); }

bool MhZ19c::update(uint32_t periodMs) {
  if (!s_) return false;
  uint32_t now = millis();
  if (now - lastQuery_ >= periodMs || lastQuery_ == 0) {
    lastQuery_ = now ? now : 1;
    idx_ = 0;
    while (s_->available()) s_->read();  // descartar basura
    send(0x86);
  }
  bool got = false;
  while (s_->available()) {
    uint8_t c = s_->read();
    if (idx_ == 0 && c != 0xFF) continue;
    if (idx_ == 1 && c != 0x86) { idx_ = 0; continue; }
    buf_[idx_++] = c;
    if (idx_ == 9) {
      idx_ = 0;
      if (checksum(buf_) == buf_[8]) {
        ppm_ = (int(buf_[2]) << 8) | buf_[3];
        lastMs_ = millis();
        got = true;
      }
    }
  }
  return got;
}
