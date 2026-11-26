"""
Módulo de limpieza: revisa la calidad de los datos (tipos, nulos, duplicados,
valores imposibles, precios desactualizados y atípicos) y deja una tabla lista
para calcular indicadores. Cada paso queda registrado en un reporte.
"""
import numpy as np
import pandas as pd

# Alcance del proyecto: combustibles para autos que se venden por litro
COMBUSTIBLES = {"93": "Gasolina 93", "95": "Gasolina 95", "97": "Gasolina 97", "DI": "Diésel"}

# Supuesto: un precio de bencina o diésel fuera de este rango es un error de digitación
# (por ejemplo 17.748 en vez de 1.774,8). El rango real del país está muy dentro de él.
PRECIO_MINIMO = 1000  # $/L
PRECIO_MAXIMO = 2500  # $/L

# Límites geográficos de Chile (incluye Isla de Pascua, longitud cercana a -109°)
LATITUD_MIN, LATITUD_MAX = -56.0, -17.0
LONGITUD_MIN, LONGITUD_MAX = -110.0, -66.0


def a_numero(serie):
    """Convierte texto a número. Acepta coma decimal ('-32,87' -> -32.87)."""
    texto = serie.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce")


def limpiar(crudo):
    """
    Recibe la tabla cruda (todo como texto) y devuelve (tabla_limpia, reporte).
    El reporte es una tabla con: problema revisado, cantidad encontrada y acción tomada.
    """
    df = crudo.copy()
    reporte = []

    def anotar(problema, cantidad, accion):
        reporte.append({"Problema revisado": problema, "Registros": int(cantidad), "Acción": accion})

    anotar("Registros recibidos (estación × combustible)", len(df), "—")

    # 1) Alcance: solo 93, 95, 97 y diésel. La API agrega una 'A' al código según el tipo de atención (A93, ADI...)
    df["combustible_codigo"] = df["combustible_codigo"].astype(str).str.strip()
    df["codigo_base"] = df["combustible_codigo"].str.removeprefix("A")
    fuera = ~df["codigo_base"].isin(COMBUSTIBLES.keys())
    anotar("Fuera de alcance (kerosene, GLP, GNC)", fuera.sum(), "Excluidos: no son bencina ni diésel por litro")
    df = df[~fuera].copy()
    df["combustible"] = df["codigo_base"].map(COMBUSTIBLES)

    # 1b) Tipo de atención: la API lo entrega invertido. El sitio oficial bencinaenlinea.cl muestra los
    #     precios con código "A..." (A93, ADI...) con el ícono de AUTOSERVICIO, y los demás como ASISTIDO.
    #     Por eso lo deducimos del código y no del campo de texto de la API.
    atencion_api = df["atencion"].astype(str).str.lower()
    df["atencion"] = df["combustible_codigo"].str.startswith("A").map({True: "Autoservicio", False: "Asistido"})
    invertidos = atencion_api != df["atencion"].str.lower()
    anotar("Tipo de atención invertido en la API", invertidos.sum(),
           "Corregido según el código (A93, ADI… = autoservicio), como lo muestra bencinaenlinea.cl")

    # 2) Tipos de dato: los precios y coordenadas llegan como texto
    coma = df["latitud"].astype(str).str.contains(",") | df["longitud"].astype(str).str.contains(",")
    anotar("Coordenadas escritas con coma decimal", coma.sum(), "Corregidas (coma → punto)")
    df["precio"] = a_numero(df["precio"])
    df["latitud"] = a_numero(df["latitud"])
    df["longitud"] = a_numero(df["longitud"])
    df["fecha_precio"] = pd.to_datetime(df["fecha_precio"], errors="coerce")
    df["fecha_consulta"] = pd.to_datetime(df["fecha_consulta"], errors="coerce")

    # 3) Valores nulos
    sin_precio = df["precio"].isna()
    anotar("Precio vacío o no numérico", sin_precio.sum(), "Eliminados")
    df = df[~sin_precio]
    sin_coord = df["latitud"].isna() | df["longitud"].isna()
    anotar("Coordenadas vacías o no numéricas", sin_coord.sum(), "Eliminados (no se puede medir distancia)")
    df = df[~sin_coord]

    textos = ["marca", "region", "comuna", "direccion"]
    sin_texto = df[textos].isna().any(axis=1)
    anotar("Marca, región, comuna o dirección vacías", sin_texto.sum(),
           "Rellenadas con 'Sin información'")
    df[textos] = df[textos].fillna("Sin información")

    # 4) Duplicados: misma estación, mismo combustible y mismo tipo de atención
    duplicados = df.duplicated(subset=["estacion_id", "combustible_codigo", "atencion"])
    anotar("Duplicados (estación + combustible + atención)", duplicados.sum(), "Eliminados (se deja uno)")
    df = df[~duplicados]

    # 5) Valores imposibles
    imposible = (df["precio"] < PRECIO_MINIMO) | (df["precio"] > PRECIO_MAXIMO)
    anotar(f"Precio imposible (fuera de {PRECIO_MINIMO}–{PRECIO_MAXIMO} $/L)", imposible.sum(),
           "Eliminados (error de digitación)")
    df = df[~imposible]
    fuera_chile = ~(df["latitud"].between(LATITUD_MIN, LATITUD_MAX)
                    & df["longitud"].between(LONGITUD_MIN, LONGITUD_MAX))
    anotar("Coordenadas fuera de Chile", fuera_chile.sum(), "Eliminados")
    df = df[~fuera_chile].copy()

    # 6) Precios desactualizados: no se eliminan, se marcan (el usuario decide con un filtro)
    df["dias_sin_actualizar"] = (df["fecha_consulta"] - df["fecha_precio"]).dt.days
    anotar("Fecha del precio vacía", df["dias_sin_actualizar"].isna().sum(),
           "Se mantienen, pero el filtro de días las deja fuera")
    viejos = df["dias_sin_actualizar"] > 30
    anotar("Precio sin actualizar hace más de 30 días", viejos.sum(), "Marcados (filtro en la barra lateral)")

    # 7) Atípicos extremos (regla de Tukey con 3 × rango intercuartílico).
    #    Se calcula por combustible Y tipo de atención, porque el asistido tiene otros precios.
    grupos = df.groupby(["combustible", "atencion"])["precio"]
    q1 = grupos.transform(lambda s: s.quantile(0.25))
    q3 = grupos.transform(lambda s: s.quantile(0.75))
    riq = (q3 - q1).clip(lower=5)  # mínimo 5 $/L: así no se marcan diferencias de pocos pesos
    df["atipico"] = (df["precio"] < q1 - 3 * riq) | (df["precio"] > q3 + 3 * riq)
    anotar("Precio atípico extremo (regla 3 × RIQ, por combustible y atención)", df["atipico"].sum(),
           "Marcados (se pueden excluir en la barra lateral)")

    # Columnas finales y una etiqueta legible para cada estación
    df["estacion"] = df["marca"] + " · " + df["direccion"].str.title()
    columnas = ["estacion_id", "estacion", "marca", "region", "comuna", "direccion", "latitud", "longitud",
                "combustible", "atencion", "precio", "fecha_precio", "dias_sin_actualizar", "atipico",
                "fecha_consulta"]
    anotar("Registros válidos después de la limpieza", len(df), "—")
    return df[columnas].reset_index(drop=True), pd.DataFrame(reporte)


def estadistica_descriptiva(df):
    """Promedio, mediana, desviación estándar, mínimo y máximo del precio por combustible (con NumPy)."""
    filas = []
    for combustible, grupo in df.groupby("combustible"):
        precios = grupo["precio"].to_numpy()
        filas.append({
            "Combustible": combustible,
            "N° registros": len(precios),
            "Promedio ($/L)": np.mean(precios),
            "Mediana ($/L)": np.median(precios),
            "Desv. estándar ($/L)": np.std(precios, ddof=1),
            "Mínimo ($/L)": np.min(precios),
            "Máximo ($/L)": np.max(precios),
        })
    return pd.DataFrame(filas).round(1)
