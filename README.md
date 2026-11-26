# Benja Bencina · Dashboard de datos públicos

Calcula el mejor lugar para cargar bencina en Puerto Montt, según dónde estás ubicado.

Proyecto final (Solemne 3) del Taller de Programación II.

**Pregunta:** Según dónde estés en Puerto Montt, ¿en qué servicentro te conviene cargar, cuánto te cuesta llegar
al más barato y cuánto ahorras frente al más cercano?

## Cómo ejecutar

Requiere Python 3.10 o más nuevo. Desde la carpeta del proyecto:

```bash
python -m pip install -r requirements.txt
python probar_api.py                 # prueba la API: código de estado y ejemplo del JSON
python -m streamlit run app.py       # abre el dashboard en el navegador
```

## Cómo se usa

1. Elige tu combustible, **cuánta plata vas a cargar** (por defecto $20.000) y, si quieres, los datos de tu auto en la barra lateral.
2. Haz clic en el mapa donde estás (o elige un lugar conocido).
3. La app muestra cuántos litros te cargan en cada servicentro, tu mejor opción, las 5 mejores y si te conviene ir al más barato.

La mejor opción es la que te deja **más litros**: litros que te cargan (plata ÷ precio) − litros que gastas en ir y volver.

## API utilizada

| Dato | Valor |
|---|---|
| Nombre | API pública de Bencina en Línea (Comisión Nacional de Energía, CNE) |
| Sitio oficial | https://bencinaenlinea.cl |
| Endpoint de estaciones | `GET https://api.bencinaenlinea.cl/api/busqueda_estacion_filtro` (trae todo el país; la app deja solo Puerto Montt) |
| Endpoint de marcas | `GET https://api.bencinaenlinea.cl/api/marca_ciudadano` (id de marca → nombre) |
| Formato | JSON. La lista de estaciones viene en la clave `data`; cada estación trae una lista `combustibles` |
| Clave (API key) | No necesita. Es gratuita |
| Límite conocido | Aprox. 500 consultas por hora por IP. La app guarda los datos en caché 30 minutos |
| Ojo | El campo `tipo_atencion_nombre` viene invertido. La app deduce la atención desde el código del combustible (A93, ADI… = autoservicio), como lo muestra bencinaenlinea.cl |

## Qué hace la app según el código de respuesta

- **200**: deja solo las estaciones de Puerto Montt, las usa en vivo y las guarda en `data/estaciones.csv`.
- **Cualquier otro código**, sin internet o respuesta que no es JSON: usa el último `data/estaciones.csv`
  guardado y muestra un aviso amarillo (plan B).

## Estructura

```
app.py                 Dashboard en Streamlit (mapa con clic, recomendación, pestañas y gráficos)
probar_api.py          Prueba rápida de la API (para la ficha del Anexo A)
modulos/
  api.py               Consulta GET, status_code, recorrido del JSON, filtro de Puerto Montt, CSV y plan B
  limpieza.py          Revisión de calidad y limpieza; estadística descriptiva con NumPy
  indicadores.py       Distancia (haversine con NumPy), gasto en llegar, costo total, comparaciones, sensibilidad
  graficos.py          Gráficos con matplotlib (título, ejes con unidades)
data/estaciones.csv    Últimos datos guardados (respaldo para el plan B)
.streamlit/config.toml La app se actualiza sola al guardar un archivo
requirements.txt       Librerías necesarias (incluye folium y streamlit-folium para el mapa con clic)
BITACORA_IA.md         Declaración de uso de inteligencia artificial
```

## Dónde está cada cálculo

| Qué | Archivo y función |
|---|---|
| Consulta GET y `status_code` | `modulos/api.py` → `obtener_datos()` |
| Recorrido del JSON con ciclos `for` | `modulos/api.py` → `json_a_tabla()` |
| Dejar solo Puerto Montt | `modulos/api.py` → `filtrar_comuna()` (constante `COMUNA`) |
| Guardar CSV y plan B | `modulos/api.py` → `obtener_datos()` (bloques `try` / `except`) |
| Nulos, duplicados, tipos y valores imposibles | `modulos/limpieza.py` → `limpiar()` |
| Estadística descriptiva (NumPy) | `modulos/limpieza.py` → `estadistica_descriptiva()` |
| Distancia desde tu ubicación (NumPy) | `modulos/indicadores.py` → `distancia_km()` |
| Litros que te cargan, bencina del viaje y litros que te quedan | `modulos/indicadores.py` → `costos_desde_ubicacion()` |
| Ahorro frente al servicentro más cercano | `modulos/indicadores.py` → `comparar_con_referencia()` |
| Litros ganados por el precio vs. litros del viaje (gráfico) | `modulos/indicadores.py` → `ganancia_y_gasto()` |
| Análisis de sensibilidad | `modulos/indicadores.py` → `sensibilidad()` y pestaña "Cómo se calcula" |
| Mapa con clic y ubicación | `app.py`, pestaña "Dónde cargar" (`st_folium` y `st.session_state`) |
| Mejor opción, más cercana y más barata | `app.py`, sección "INDICADORES" |
| Precio por marca y tabla dinámica | `modulos/indicadores.py` → `resumen_por_marca()`, `tabla_dinamica_marcas()` |

## Sobre el CSV de respaldo incluido

`data/estaciones.csv` trae la consulta del 25-11-2026 a las 17:35 (32 servicentros de Puerto Montt, 193 registros).
Cada vez que la app consulta la API con éxito, el archivo se reemplaza por los datos nuevos.
Para probar el plan B, desconecta internet y presiona "Actualizar precios": aparece el aviso amarillo.
