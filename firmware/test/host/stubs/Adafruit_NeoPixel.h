#pragma once
#include <cstdint>
#define NEO_GRB 0
#define NEO_KHZ800 0
class Adafruit_NeoPixel {
 public:
  uint32_t px[64] = {0};
  Adafruit_NeoPixel(int, int, int) {}
  void begin() {} void setBrightness(uint8_t) {} void clear() {} void show() {}
  static uint32_t Color(uint8_t r, uint8_t g, uint8_t b) { return (uint32_t(r) << 16) | (uint32_t(g) << 8) | b; }
  void setPixelColor(uint16_t i, uint32_t c) { px[i] = c; }
  void setPixelColor(uint16_t i, uint8_t r, uint8_t g, uint8_t b) { px[i] = Color(r, g, b); }
};
