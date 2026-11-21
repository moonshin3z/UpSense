// Pruebas en la PC de los parsers y del semáforo:  ./correr.sh
#include <cstdio>
#include "pms5003.h"
#include "mhz19c.h"
#include "semaforo.h"

uint32_t g_millis = 1;
static int fallos = 0;
#define CHECK(c) do { if (!(c)) { printf("FALLA %s:%d  %s\n", __FILE__, __LINE__, #c); fallos++; } } while (0)

static std::vector<uint8_t> tramaPms(uint16_t cf1_25, uint16_t atm_25) {
  std::vector<uint8_t> f = {0x42, 0x4D, 0x00, 28};
  uint16_t d[13] = {5, cf1_25, 20, 4, atm_25, 18, 1000, 300, 50, 5, 1, 0, 0};
  for (uint16_t v : d) { f.push_back(v >> 8); f.push_back(v & 0xFF); }
  uint16_t s = 0; for (uint8_t b : f) s += b;
  f.push_back(s >> 8); f.push_back(s & 0xFF);
  return f;
}

int main() {
  // ---- PMS5003 ----
  HardwareSerial sp; Pms5003 pms; pms.begin(sp, 0, 0);
  for (uint8_t b : {0x00, 0x42, 0x13, 0x42}) sp.rx.push_back(b);         // basura y cabecera falsa
  for (uint8_t b : tramaPms(37, 31)) sp.rx.push_back(b);
  CHECK(pms.update());
  CHECK(pms.data().pm25_cf1 == 37 && pms.data().pm25_atm == 31 && pms.data().n03 == 1000);
  auto mala = tramaPms(50, 40); mala[10] ^= 0xFF;                       // checksum roto
  for (uint8_t b : mala) sp.rx.push_back(b);
  CHECK(!pms.update()); CHECK(pms.badFrames() == 1); CHECK(pms.data().pm25_cf1 == 37);
  auto t = tramaPms(12, 12);                                              // llega en dos pedazos
  for (size_t i = 0; i < 10; i++) sp.rx.push_back(t[i]);
  CHECK(!pms.update());
  for (size_t i = 10; i < t.size(); i++) sp.rx.push_back(t[i]);
  CHECK(pms.update()); CHECK(pms.data().pm25_cf1 == 12);

  // ---- MH-Z19C ----
  HardwareSerial sm; MhZ19c mhz; mhz.begin(sm, 0, 0);
  mhz.update(5000);
  uint8_t q[9] = {0xFF, 0x01, 0x86, 0, 0, 0, 0, 0, 0x79};                 // consulta estándar del datasheet
  CHECK(sm.tx.size() == 9 && std::equal(q, q + 9, sm.tx.begin()));
  uint8_t r[9] = {0xFF, 0x86, 0x03, 0x20, 0x40, 0, 0, 0, 0};              // 0x0320 = 800 ppm
  uint8_t sum = 0; for (int i = 1; i < 8; i++) sum += r[i]; r[8] = 0xFF - sum + 1;
  for (uint8_t b : r) sm.rx.push_back(b);
  CHECK(mhz.update(5000)); CHECK(mhz.ppm() == 800);
  r[3] = 0x21; for (uint8_t b : r) sm.rx.push_back(b);                    // checksum ya no cuadra
  CHECK(!mhz.update(5000)); CHECK(mhz.ppm() == 800);

  // ---- Semáforo (sobre ventana_calib.h) ----
  auto correr = [](Semaforo& s, float cf1, float co2, float rh, int n) {
    for (int i = 0; i < n; i++) { g_millis += 5000; s.agregar(cf1, co2, rh, 22, 850); }
    return s.decidir();
  };
  { Semaforo s; CHECK(s.decidir().accion == V_SIN_DATOS); }
  { Semaforo s; auto d = correr(s, 8, 600, 55, 80); CHECK(d.accion == V_NADA); }
  { Semaforo s; auto d = correr(s, 8, 1400, 55, 80); CHECK(d.accion == V_ABRIR); }
  { Semaforo s; auto d = correr(s, 8, 950, 55, 80); CHECK(d.accion == V_ABRIR_PARCIAL); }
  { Semaforo s; auto d = correr(s, 150, 1400, 55, 80); CHECK(d.accion == V_VENTILAR_CORTO); }
  // Humo que entra (PM sube rápido con CO2 bajo): cerrar
  { Semaforo s; correr(s, 8, 600, 55, 150);
    auto d = correr(s, 150, 600, 55, 60);
    CHECK(!d.alertaHumedad); CHECK(d.accion == V_CERRAR); }
  // Prueba del vapor: PM crudo se dispara junto con la HR -> no se manda a cerrar
  { Semaforo s; correr(s, 8, 600, 55, 150);
    float antes = s.pm25Corregido();
    auto d = correr(s, 200, 600, 97, 12);
    CHECK(d.alertaHumedad); CHECK(d.accion == V_NADA);
    CHECK(fabsf(s.pm25Corregido() - antes) < 0.01f); }
  // Vapor que no llega a niebla pero sube de golpe (55 -> 80 %): también se detecta
  { Semaforo s; correr(s, 8, 600, 55, 150);
    auto d = correr(s, 120, 600, 80, 6);
    CHECK(d.alertaHumedad); CHECK(d.accion == V_NADA); }
  // Decisión remota del dashboard manda mientras dura su ttl
  { Semaforo s; correr(s, 8, 600, 55, 10);
    s.forzar(V_CERRAR, 60000); CHECK(s.decidir().accion == V_CERRAR && s.decidir().remota);
    g_millis += 61000; CHECK(s.decidir().accion == V_NADA); }
  CHECK(accionDesdeTexto("abrir_parcial") == V_ABRIR_PARCIAL);
  CHECK(accionDesdeTexto("xx") == V_SIN_DATOS);

  printf(fallos ? "%d pruebas fallaron\n" : "Todas las pruebas pasaron\n", fallos);
  return fallos ? 1 : 0;
}
