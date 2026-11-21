# UpSense: la ciencia en lenguaje simple (para el pitch)

## En una frase

Un sensor de $65 en el aula que corrige sus propios errores por humedad y le dice a la maestra una sola cosa: abra, cierre, o ventile 5 minutos.

## El problema, contado para la maestra

- **Los sensores baratos se confunden con la humedad.** Cuando el aire está húmedo, las partículas absorben agua, se hinchan y el sensor las cuenta como si fueran más contaminación. En una mañana lluviosa de Guatemala, un sensor barato puede marcar el doble o el triple de lo real. Resultado: falsas alarmas de "aire sucio".
- **Las falsas alarmas tienen un costo escondido.** Si el sensor dice "aire sucio afuera", la maestra cierra la ventana. Con 30 niños adentro, el aire se carga de aire ya respirado por otros. Eso trae cansancio y más contagio de gripes.

## Lo que hacemos con dos hallazgos recientes

1. **Corregimos la humedad por software (Sitarek et al., *Sensors*, 2026).** Ellos mostraron que con temperatura, humedad y presión, un modelo pequeño corrige el error de humedad de un sensor barato hasta explicar el 94 % de la variación de la referencia. Nosotros lo llevamos al sensor PMS5003 y a un modelo de menos de 1 KB que cabe en el microcontrolador.
2. **Convertimos el CO2 en "aire de segunda mano" (Vouriot et al., *J R Soc Interface*, 2024).** El CO2 no es tóxico a estos niveles, pero es una huella de cuánto aire ya pasó por los pulmones de otro. Con un solo sensor calculamos qué porcentaje del aire que respira cada niño es aire reexhalado, y cuánto más riesgo de contagio hay que en un aula bien ventilada.

**Frase para el jurado:** "1 200 ppm de CO2 significa que 2 de cada 100 respiraciones de cada niño son aire que salió de los pulmones de un compañero."

## Cifras para mostrar (todas SIMULADAS, hay que decirlo)

- En la simulación, la corrección baja las falsas alarmas de contaminación de **46 % a 2 %** del tiempo.
- En una mañana húmeda simulada, la maestra que confía en el sensor crudo pasa **173 minutos** con falsa alarma y mantiene el aula a **1 600 ppm** en promedio. Con UpSense: **12 minutos** y **1 200 ppm**. El riesgo relativo de contagio baja de **3.1× a 2.1×** (un tercio menos).
- Cuando hay humo de verdad (una quema a las 11:00), UpSense **sí** avisa. No esconde la contaminación real, solo la falsa.

> Para el pitch: decir "en simulación" y "estamos validando con datos reales" hasta tenerlos. Un jurado de DeepTech va a preguntar con qué se entrenó.

## Cómo hacer que la diferencia se note en vivo

1. **Dos pantallas lado a lado en el dashboard:** "lo que dice un sensor barato" (rojo, PM crudo) y "lo que dice UpSense" (azul, PM corregido), con el gráfico `modelos/demo_aula.png` o reproduciendo `datos/demo_aula.json`.
2. **El truco de la humedad, en el escenario:** acercar al equipo una taza de agua caliente o un trapo húmedo (sin mojar el sensor). La humedad sube, el número crudo se dispara y la luz de "sensor barato" se pone morada ("cierre"), mientras UpSense se queda en verde o pasa a "humedad muy alta, decido por CO2". Ojo: si la humedad pasa de 95 % el sensor cuenta gotitas de verdad; UpSense lo detecta y deja de usar el PM. Probar antes cuánta humedad hace falta.
3. **El truco del CO2:** dos o tres personas respiran cerca del equipo durante 30 segundos. El CO2 sube, el porcentaje de aire reexhalado sube y la tira LED pasa de verde a ámbar o rojo: "abra la ventana".

## La tira LED (lo que ve la maestra sin leer nada)

| Color | Significa | Texto |
|---|---|---|
| Verde | Todo bien | No hace falta hacer nada |
| Ámbar | El aire se está cargando | Abra un poco la ventana |
| Rojo | Mucho aire reexhalado | Abra la ventana ya |
| Morado | Afuera está sucio | Cierre la ventana |
| Naranja con cuenta regresiva | Hace falta aire pero afuera está sucio | Abra 5 minutos y cierre |

La maestra no necesita saber qué es PM2.5. Solo mira el color.

## Preguntas difíciles que pueden hacer

- **"¿Con qué datos entrenaron?"** Hoy con datos simulados a partir de la física del crecimiento de partículas con la humedad. El plan para datos reales está en `protocolo_datos_reales.md`: dos sensores, uno con el aire secado, igual que Sitarek 2026, o co-ubicación con un monitor de referencia.
- **"¿El CO2 es peligroso?"** A estos niveles no. Lo usamos como medidor de ventilación: dice cuánto aire de otros respira cada niño. Un estudio de 2024 (Flagner) no encontró efecto en el rendimiento cognitivo a 3 000 ppm de CO2 puro, por eso no prometemos "mejores notas", sino menos aire reexhalado.
- **"¿Por qué no usar la corrección de la EPA?"** La usamos como respaldo, pero se hizo con datos de Estados Unidos. Nuestro modelo se puede reentrenar con datos de Guatemala en una tarde.
