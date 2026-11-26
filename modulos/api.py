"""
Módulo API: consulta la API pública de Bencina en Línea (CNE), recorre el JSON,
lo convierte en una tabla (DataFrame) y deja solo las estaciones de la comuna de Puerto Montt.
Si la API no responde, usa el último CSV guardado en data/ (plan B).
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# --- Direcciones de la API (consultas GET, responden JSON, sin clave) ---
URL_BASE = "https://api.bencinaenlinea.cl/api"
URL_ESTACIONES = URL_BASE + "/busqueda_estacion_filtro"  # todas las estaciones con sus precios
URL_MARCAS = URL_BASE + "/marca_ciudadano"                # id de marca -> nombre de la marca

# Encabezados de la consulta: decimos quiénes somos y que esperamos JSON
ENCABEZADOS = {
    "User-Agent": "proyecto-academico-taller-programacion-II (uso no comercial)",
    "Accept": "application/json",
}
TIEMPO_MAXIMO = 30  # segundos que esperamos la respuesta antes de rendirnos

# El proyecto trabaja solo con esta comuna. La API no permite pedir una comuna,
# así que traemos todo Chile y filtramos apenas llegan los datos.
COMUNA = "Puerto Montt"

# Archivo donde se guardan los datos (respaldo para el plan B)
RUTA_CSV = Path(__file__).resolve().parent.parent / "data" / "estaciones.csv"


def ahora_chile():
    """
    Fecha y hora de Chile, aunque la app corra en un servidor de otro país (por ejemplo, Streamlit Cloud,
    que usa la hora UTC). Si el computador no tiene la base de zonas horarias (Windows sin el paquete
    tzdata), se usa la hora del computador, que en Chile ya es la correcta.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def describir_codigo(codigo):
    """Traduce el código de estado HTTP a una explicación en español."""
    explicaciones = {
        200: "OK: la API respondió correctamente",
        400: "Solicitud mal formada (parámetros incorrectos)",
        401: "No autorizado (la API pide credenciales)",
        403: "Acceso prohibido",
        404: "No encontrado: la dirección de la consulta está mal escrita",
        429: "Demasiadas consultas: se superó el límite de la API",
        500: "Error interno del servidor de la API",
        503: "Servicio no disponible (API caída o en mantención)",
    }
    return explicaciones.get(codigo, "Código no esperado")


def consultar(url):
    """Hace una consulta GET y devuelve la respuesta (sin revisar el código)."""
    return requests.get(url, headers=ENCABEZADOS, timeout=TIEMPO_MAXIMO)


def obtener_marcas():
    """Devuelve un diccionario {id_marca: nombre_marca}. Si falla, devuelve {}."""
    try:
        respuesta = consultar(URL_MARCAS)
    except requests.RequestException:
        return {}
    if respuesta.status_code != 200:
        return {}

    marcas = {}
    for marca in respuesta.json().get("data", []):
        marcas[marca.get("id")] = marca.get("nombre")
    return marcas


def json_a_tabla(datos_json, marcas, fecha_consulta):
    """
    Recorre el JSON y arma una fila por cada combinación estación x combustible.

    Estructura del JSON (resumida):
    {"data": [ {"id": .., "marca": .., "region": .., "comuna": .., "direccion": ..,
                "latitud": .., "longitud": ..,
                "combustibles": [ {"nombre_corto": "93", "nombre_largo": "Gasolina 93",
                                   "precio": "1650.000", "unidad_cobro": "$/L",
                                   "tipo_atencion_nombre": "AutoServicio",
                                   "precio_fecha": "2026-11-19 08:01:12"}, ... ]
              }, ... ]}
    """
    filas = []
    for estacion in datos_json.get("data", []):              # lista de estaciones
        id_marca = estacion.get("marca")
        nombre_marca = marcas.get(id_marca, f"Marca {id_marca}")
        for combustible in estacion.get("combustibles", []):  # lista de combustibles de esa estación
            filas.append({
                "estacion_id": estacion.get("id"),
                "marca": nombre_marca,
                "region": estacion.get("region"),
                "comuna": estacion.get("comuna"),
                "direccion": (estacion.get("direccion") or "").strip(),
                "latitud": estacion.get("latitud"),
                "longitud": estacion.get("longitud"),
                "combustible_codigo": combustible.get("nombre_corto"),
                "combustible_nombre": combustible.get("nombre_largo"),
                "precio": combustible.get("precio"),
                "unidad": combustible.get("unidad_cobro"),
                "atencion": combustible.get("tipo_atencion_nombre"),
                "fecha_precio": combustible.get("precio_fecha"),
                "fecha_consulta": fecha_consulta,
            })
    return pd.DataFrame(filas)


def filtrar_comuna(tabla):
    """Deja solo las filas de la comuna del proyecto (Puerto Montt)."""
    return tabla[tabla["comuna"] == COMUNA].reset_index(drop=True)


def cargar_respaldo():
    """Lee el último CSV guardado (plan B). Todo se lee como texto; la limpieza convierte los tipos."""
    return filtrar_comuna(pd.read_csv(RUTA_CSV, dtype=str))


def obtener_datos():
    """
    Intenta traer los datos desde la API. Devuelve (tabla, origen, mensaje):
      - origen = "api"      -> datos en vivo (y se guardan en data/estaciones.csv)
      - origen = "respaldo" -> la API falló y se usa el último CSV guardado
    """
    try:
        respuesta = consultar(URL_ESTACIONES)
        if respuesta.status_code != 200:
            raise ValueError(f"código {respuesta.status_code}: {describir_codigo(respuesta.status_code)}")

        datos_json = respuesta.json()  # puede fallar si la respuesta no es JSON
        if not datos_json.get("data"):
            raise ValueError("la respuesta no trae la lista 'data' de estaciones")

        ahora = ahora_chile()
        fecha_consulta = ahora.strftime("%Y-%m-%d %H:%M:%S")
        tabla = filtrar_comuna(json_a_tabla(datos_json, obtener_marcas(), fecha_consulta))
        if tabla.empty:
            raise ValueError(f"la respuesta no trae estaciones de {COMUNA}")

        RUTA_CSV.parent.mkdir(exist_ok=True)
        tabla.to_csv(RUTA_CSV, index=False)  # guardamos para el plan B (solo Puerto Montt)
        # Releemos el CSV para que ambos caminos (API y respaldo) entreguen exactamente el mismo formato
        tabla = cargar_respaldo()
        mensaje = (f"Precios en vivo del {ahora:%d-%m-%Y a las %H:%M} · "
                   f"{tabla['estacion_id'].nunique()} servicentros · la API respondió bien (código {respuesta.status_code}).")
        return tabla, "api", mensaje

    except (requests.RequestException, ValueError) as error:
        # requests.RequestException: sin internet, tiempo agotado, etc.
        # ValueError: código distinto de 200 o JSON inválido
        if not RUTA_CSV.exists():
            return pd.DataFrame(), "sin_datos", f"La API no respondió ({error}) y no hay datos guardados."
        tabla = cargar_respaldo()
        if tabla.empty:
            return tabla, "sin_datos", f"La API no respondió ({error}) y no hay datos guardados de {COMUNA}."
        fecha = pd.to_datetime(tabla["fecha_consulta"].iloc[0], errors="coerce") if len(tabla) else pd.NaT
        fecha_texto = f"{fecha:%d-%m-%Y a las %H:%M}" if pd.notna(fecha) else "una fecha desconocida"
        mensaje = (f"No hay conexión con la API ({error}). Te mostramos los últimos precios guardados, "
                   f"del {fecha_texto}.")
        return tabla, "respaldo", mensaje
