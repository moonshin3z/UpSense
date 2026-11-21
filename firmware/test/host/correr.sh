#!/bin/sh
# Compila y corre las pruebas de lógica del firmware en la PC (g++ o clang++).
cd "$(dirname "$0")"
${CXX:-g++} -std=c++17 -Wall -Wextra -Wno-unused-parameter -Istubs -I../../src -I../../include -include cmath \
  test_main.cpp ../../src/pms5003.cpp ../../src/mhz19c.cpp ../../src/semaforo.cpp -o /tmp/test_firmware && /tmp/test_firmware
