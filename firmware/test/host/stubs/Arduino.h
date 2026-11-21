// Stub mínimo de Arduino para probar la lógica en la PC (no es el core real).
#pragma once
#include <cstdint>
#include <cstddef>
#include <cmath>
#include <string>
#include <deque>
#include <vector>
#include <algorithm>
using std::min; using std::max; using std::isnan;
#define SERIAL_8N1 0
extern uint32_t g_millis;
inline uint32_t millis() { return g_millis; }
template <class T, class L, class H> T constrain(T x, L a, H b) { return x < a ? a : (x > b ? b : x); }
class String : public std::string {
 public:
  String(const char* s = "") : std::string(s) {}
  String(const std::string& s) : std::string(s) {}
  int toInt() const { return std::atoi(c_str()); }
};
class HardwareSerial {
 public:
  std::deque<uint8_t> rx;            // lo que "envía" el sensor
  std::vector<uint8_t> tx;           // lo que escribe el firmware
  void begin(unsigned long, int, int, int) {}
  int available() { return (int)rx.size(); }
  int read() { if (rx.empty()) return -1; int c = rx.front(); rx.pop_front(); return c; }
  size_t write(const uint8_t* b, size_t n) { tx.insert(tx.end(), b, b + n); return n; }
};
