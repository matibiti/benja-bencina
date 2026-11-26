# Bitácora de uso de inteligencia artificial

> Completen las columnas "Qué verificamos" y "Qué cambiamos" con lo que **ustedes** revisaron.
> El profesor puede preguntar cualquiera de estos puntos en la presentación.

## Herramientas usadas

| Herramienta | Para qué |
|---|---|
| Claude (Anthropic) | Ideas de proyecto, primera versión del código, borrador del modelo de solución |
| _(agregar otras si las usan)_ | |

## Registro

| Fecha | Instrucción principal (resumida) | Qué generó la IA | Qué verificamos | Qué cambiamos |
|---|---|---|---|---|
| 23-11-2026 | "Dame ideas de proyectos (…) que realmente cumplan una utilidad", adjuntando el enunciado | 6 ideas con API, pregunta e indicador. Elegimos la de precios de combustibles | _completar_ | _completar_ |
| 23-11-2026 | "Desarrolla la idea 6", enfocada en Puerto Montt | `app.py`, `modulos/`, `probar_api.py`, README, borrador de la ficha y del modelo de solución | _completar_ | _completar_ |
| 24-11-2026 | "Que trabaje solo con la X Región, con el mejor servicentro de tu ciudad y de la región, y cuánto se gana y se gasta en llegar" | Filtro de región en `modulos/api.py`, selector de ciudad, tarjetas "mejor de tu ciudad" y "más barato de la región", apartado de ganancia vs. gasto, regla de atípicos por combustible y atención | _completar_ | _completar_ |
| 25-11-2026 | "Quítale los emojis, más ordenado, y un apartado de la ubicación de la persona para ver cuánto gasta en llegar al servicentro más económico" | Punto de partida = ubicación (centro de la ciudad o coordenadas), costo total de la carga (precio + viaje), comparación con la más cercana, página ordenada en secciones y sin emojis | _completar_ | _completar_ |
| 25-11-2026 | "Que sea solo para Puerto Montt y fácil para cualquier persona; que el mapa permita ubicarte con un clic; que el gráfico muestre también la estación recomendada" | Filtro de comuna, mapa con clic (folium + streamlit-folium), lugares conocidos, recomendación en palabras simples, opciones técnicas en "Opciones avanzadas", ranking de precios, gráfico de ganancia vs. gasto con todas las estaciones | _completar_ | _completar_ |
| 25-11-2026 | "La opción asistido/autoservicio está mal y desaparecen servicentros" | Se revisó el código de bencinaenlinea.cl: la API entrega el tipo de atención invertido. Se corrige según el código (A93 = autoservicio) y por defecto se usa el precio más bajo de cada servicentro | _completar_ | _completar_ |
| 25-11-2026 | "Cambia el título y haz los textos más simples de leer" | Título "Bencina barata en Puerto Montt" y textos más cortos en la página, la barra lateral, los mensajes de la API y los gráficos | _completar_ | _completar_ |
| 25-11-2026 | "Mándame lo que se solicita para el lunes: el informe, el proyecto y la presentación" | Borrador del informe (Word y PDF) con capturas, hallazgos y cifras calculadas desde `data/estaciones.csv`; este .zip; borrador de las diapositivas con notas para cada integrante | _completar_ | _completar_ |
| 25-11-2026 | "En vez de litros, que se elija la plata que se carga (por ejemplo 20 lucas) y que indique cuántos litros te cargan; cambia todo lo asociado" | Filtro "¿Cuánta plata vas a cargar?"; nuevos indicadores (litros que te cargan, bencina del viaje y litros que te quedan); la recomendación pasa a ser el que deja más litros; gráficos, sensibilidad, informe y diapositivas recalculados | _completar_ | _completar_ |
| 26-11-2026 | "Cambia el nombre de la página a Benja Bencina, con una descripción abajo; cámbialo en el informe y la presentación, y hazme un guion de la presentación" | Nombre "Benja Bencina" y descripción en la app, el informe y las diapositivas; guion de la presentación por integrante con tiempos según el enunciado | _completar_ | _completar_ |
| 26-11-2026 | "El trabajo pide una URL: ¿cómo hacer que la app tenga URL y funcione 24/7?" | Pasos para publicar en Streamlit Community Cloud (la publicamos nosotros en https://benja-bencina.streamlit.app); corrección para mostrar la hora de Chile en el servidor (función ahora_chile y paquete tzdata) | _completar_ | _completar_ |

## Lista de verificación sugerida (marcar lo que hicieron)

- [ ] Ejecutamos `probar_api.py` y comparamos el JSON real con la estructura que asume `json_a_tabla()`
- [ ] Calculamos a mano el ahorro de una estación (con calculadora) y coincide con la tabla de la pestaña 5
- [ ] Probamos el plan B desconectando internet y vimos el aviso amarillo
- [ ] Revisamos que cada gráfico tenga título, ejes con unidades y texto de lectura
- [ ] Revisamos en el CSV ejemplos reales de cada problema de calidad (coma decimal, precio imposible, etc.)
- [ ] Cada integrante explicó en voz alta qué hace cada función de `modulos/`
