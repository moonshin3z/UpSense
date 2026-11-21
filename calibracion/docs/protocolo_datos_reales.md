# Cómo conseguir datos reales para entrenar la calibración

El modelo actual está entrenado con datos **sintéticos**. Para poder decir una cifra en el pitch hace falta una etiqueta "verdadera" de PM2.5 seco al lado del PMS5003. Tres caminos, del más barato al más sólido.

## Opción A · Gemelo secado, como Sitarek 2026 (recomendada para el hackathon)

Sitarek et al. pusieron dos sensores iguales lado a lado: uno normal y otro con un calentador en la entrada de aire que se enciende cuando la HR pasa de 60 %. El calentado mide "seco" y sirve de etiqueta.

- Comprar un segundo PMS5003 (~$15-20) [POR CONFIRMAR precio local].
- Calentar la entrada de aire con una resistencia de potencia (p. ej. 10 Ω, 5 W a 5 V, ~2.5 W) pegada a un tubo corto de aluminio delante de la entrada, controlada con un MOSFET y el BME680 midiendo dentro del tubo. Objetivo: HR en la entrada < 50 %. [POR PROBAR: subir 8-10 °C suele bastar para pasar de 85 % a < 50 % de HR]
- Ambos en el mismo ESP32, registrando cada 60 s: `pm25_cf1` del normal, `pm25_cf1` del calentado, `rh`, `temp`, `pressure`.
- Antes de calentar, un día con ambos sin calefacción para comparar los dos sensores entre sí (factor de ajuste entre unidades).
- Etiqueta: `pm25_referencia` = PM del calentado, pasado por la corrección EPA con HR baja, o directamente su CF=1 si solo se quiere quitar el efecto de la humedad (en ese caso la salida queda en "unidades PMS5003 secas"; decirlo así).

Limitación (la misma que reconocen Sitarek et al.): la etiqueta es un sensor barato seco, no un instrumento oficial.

## Opción B · Co-ubicación con un monitor oficial

Poner el equipo durante 1 a 3 semanas junto a un monitor de referencia (beta-atenuación o gravimétrico). En Ciudad de Guatemala habría que preguntar a [POR CONFIRMAR] el Laboratorio de Monitoreo del Aire de la USAC, el MARN o la Municipalidad, si tienen una estación con PM2.5 y si permiten colocar un equipo al lado. Con 1 semana de datos horarios ya se puede reentrenar.

## Opción C · Datos públicos de co-ubicación

- El conjunto de Sitarek 2026 es público en RepOD: https://doi.org/10.18150/1QFISN (SDS011, Polonia; sirve para probar el pipeline, no para Guatemala).
- La EPA publica los datos de co-ubicación PurpleAir-referencia que usó para su corrección (Barkjohn et al. 2021) en catalog.data.gov.

Desde mi entorno no pude descargar ninguno de los dos (la red los bloquea). Se pueden bajar desde una computadora del equipo.

## Formato que espera `entrenar.py`

CSV con una fila por minuto (o cada 10 min) y estas columnas:

```
t_horas,pm25_cf1,rh,temp,pressure,pm25_referencia
0.0000,38.2,87.1,17.4,851.2,14.9
0.0167,37.9,87.0,17.4,851.2,14.6
```

Luego:

```bash
cd python
python entrenar.py ../datos/mis_datos.csv
python exportar_c.py
cp ../modelos/modelo.json <carpeta del dashboard>/modelo.json
cp ../c/ventana_modelo.h <firmware>/include/
```

`entrenar.py` separa el último 25 % del tiempo como prueba, imprime la tabla de métricas, elige el modelo y deja el gráfico `modelos/comparacion.png`.

## Cuántos datos hacen falta

Sitarek usó ~16 meses. Para un primer modelo útil basta con que el set cubra el rango de humedad del lugar (mañanas con neblina y tardes secas) y algún episodio de PM alto: en temporada de lluvias, unos 5-7 días suelen cubrir ese rango [SUPUESTO]. El polinomio tiene 10 coeficientes, así que no necesita muchos datos para no sobreajustar.
