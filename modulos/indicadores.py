"""
Módulo de indicadores: distancia desde la ubicación de la persona, litros que le cargan con su plata,
bencina que gasta en llegar a cada estación, litros que le quedan, comparación con la estación más
cercana, sensibilidad y tablas resumen por marca.

Notación (la misma del informe):
  M   = plata que la persona carga ($ por carga)  P = precio de la estación ($/L)
  r   = rendimiento del vehículo (km/L)           f = factor de ruta (calles / línea recta)
  d   = distancia en línea recta desde tu ubicación (km)
  K   = kilómetros recorridos al mes (km/mes)
  ref = la estación más cercana a tu ubicación (contra ella se compara todo)
"""
import numpy as np
import pandas as pd

RADIO_TIERRA_KM = 6371.0


def distancia_km(lat0, lon0, latitudes, longitudes):
    """Distancia en línea recta (fórmula del haversine) desde un punto a muchos puntos, con NumPy."""
    lat0, lon0 = np.radians(lat0), np.radians(lon0)
    lat, lon = np.radians(np.asarray(latitudes, dtype=float)), np.radians(np.asarray(longitudes, dtype=float))
    a = np.sin((lat - lat0) / 2) ** 2 + np.cos(lat0) * np.cos(lat) * np.sin((lon - lon0) / 2) ** 2
    return 2 * RADIO_TIERRA_KM * np.arcsin(np.sqrt(a))


def cargas_al_anio(km_mes, rendimiento, litros_por_carga):
    """Cargas al año = litros al año / litros por carga = (K × 12 / r) / litros por carga."""
    return (km_mes * 12 / rendimiento) / litros_por_carga


def costos_desde_ubicacion(estaciones, lat0, lon0, supuestos):
    """
    Agrega a cada estación lo que pasa si vas a cargar ahí con tu plata (M):
      distancia_km        = d (haversine)                          (km, línea recta)
      distancia_ruta_km   = f × d                                  (km por calles, solo ida)
      km_ida_vuelta       = 2 × f × d                              (km)
      litros_cargados     = M / P                                  (L: lo que te cargan con tu plata)
      litros_trayecto     = km_ida_vuelta / r                      (L: lo que gastas en ir y volver)
      litros_netos        = litros_cargados − litros_trayecto      (L: lo que de verdad te queda)
      gasto_llegar        = litros_trayecto × P                    ($: lo que cuesta ir y volver)
    Se recomienda la estación con MÁS litros_netos.
    """
    M = supuestos["monto_carga"]
    r = supuestos["rendimiento"]
    f = supuestos["factor_ruta"]

    df = estaciones.copy()
    df["distancia_km"] = distancia_km(lat0, lon0, df["latitud"], df["longitud"])
    df["distancia_ruta_km"] = f * df["distancia_km"]
    df["km_ida_vuelta"] = 2 * df["distancia_ruta_km"]
    df["litros_cargados"] = M / df["precio"]
    df["litros_trayecto"] = df["km_ida_vuelta"] / r
    df["litros_netos"] = df["litros_cargados"] - df["litros_trayecto"]
    df["gasto_llegar"] = df["litros_trayecto"] * df["precio"]
    return df


def comparar_con_referencia(df, referencia, supuestos):
    """
    Compara cada estación con la referencia (la más cercana a tu ubicación). Los litros de diferencia
    se pasan a pesos con el precio de la referencia (lo que costaría comprarlos ahí):
      litros_precio   = litros_cargados − litros_cargados_ref     (L que ganas o pierdes por el precio)
      litros_viaje    = litros_trayecto − litros_trayecto_ref     (L que gastas de más en llegar)
      litros_extra    = litros_netos − litros_netos_ref           (L que te quedan de más = las dos cosas)
      ganancia_precio = litros_precio × P_ref                     ($ por carga)
      gasto_extra     = litros_viaje × P_ref                      ($ por carga)
      ahorro_carga    = litros_extra × P_ref                      ($ por carga = ganancia − gasto extra)
      ahorro_anual    = ahorro_carga × cargas al año              ($ al año)
    """
    P_ref = referencia["precio"]
    litros_por_carga = referencia["litros_cargados"]
    df = df.copy()
    df["litros_precio"] = df["litros_cargados"] - referencia["litros_cargados"]
    df["litros_viaje"] = df["litros_trayecto"] - referencia["litros_trayecto"]
    df["litros_extra"] = df["litros_netos"] - referencia["litros_netos"]
    df["ganancia_precio"] = df["litros_precio"] * P_ref
    df["gasto_extra"] = df["litros_viaje"] * P_ref
    df["ahorro_carga"] = df["litros_extra"] * P_ref
    df["ahorro_anual"] = df["ahorro_carga"] * cargas_al_anio(supuestos["km_mes"], supuestos["rendimiento"],
                                                             litros_por_carga)
    df["conviene"] = df["litros_extra"] > 0
    return df


def ganancia_y_gasto(df, precio_promedio, monto_carga):
    """
    Para el gráfico de litros ganados vs. litros del viaje: cada servicentro (incluidos el más cercano
    y el recomendado) comparado con cargar la misma plata al precio promedio de Puerto Montt:
      litros_vs_promedio = M / P − M / precio promedio     (L que GANAS por el precio)
      te_queda_litros    = litros_vs_promedio − litros_trayecto (L: ganancia menos la bencina del viaje)
    El que deja más litros es el de más litros_netos (es la misma cuenta ordenada de otra forma).
    """
    df = df.copy()
    df["litros_vs_promedio"] = monto_carga / df["precio"] - monto_carga / precio_promedio
    df["te_queda_litros"] = df["litros_vs_promedio"] - df["litros_trayecto"]
    return df


def precio_umbral(litros_netos_ref, distancias_ruta, monto_carga, rendimiento):
    """
    Precio máximo que puede tener una estación a x km por calles para que te deje los mismos litros
    que la más cercana:  M / P* − 2x / r = litros_netos_ref  →  P* = M / (litros_netos_ref + 2x / r).
    Es la curva del gráfico de dispersión: las estaciones bajo la curva convienen.
    """
    x = np.asarray(distancias_ruta, dtype=float)
    return monto_carga / (litros_netos_ref + 2 * x / rendimiento)


def sensibilidad(referencia, alternativa, monto_carga, rendimientos=(8, 12, 16), km_mes_max=4000):
    """
    Ahorro anual de ir a la alternativa en vez de la referencia, al variar los km al mes,
    para varios rendimientos:
      litros que te quedan = M / P − 2x / r
      ahorro por carga     = (litros alternativa − litros referencia) × P_ref
      cargas al año        = (K × 12 / r) / (M / P_ref)
    """
    km = np.arange(250, km_mes_max + 1, 250)
    P_ref = referencia["precio"]
    filas = []
    for r in rendimientos:
        netos_ref = monto_carga / P_ref - 2 * referencia["distancia_ruta_km"] / r
        netos_alt = monto_carga / alternativa["precio"] - 2 * alternativa["distancia_ruta_km"] / r
        ahorro_carga = (netos_alt - netos_ref) * P_ref
        ahorro = ahorro_carga * cargas_al_anio(km, r, monto_carga / P_ref)
        for k, a in zip(km, ahorro):
            filas.append({"km_mes": k, "rendimiento": r, "ahorro_anual": a})
    return pd.DataFrame(filas)


def resumen_por_marca(df):
    """Precio por marca (agrupación con Pandas): n° de estaciones, promedio, mínimo, máximo y dispersión."""
    resumen = df.groupby("marca")["precio"].agg(["count", "mean", "min", "max", "std"])
    resumen["brecha"] = resumen["max"] - resumen["min"]
    resumen.columns = ["N° estaciones", "Promedio ($/L)", "Mínimo ($/L)", "Máximo ($/L)",
                       "Desv. estándar ($/L)", "Brecha máx−mín ($/L)"]
    return resumen.sort_values("Promedio ($/L)").round(1)


def tabla_dinamica_marcas(df):
    """Tabla dinámica: precio promedio por marca (filas) y combustible (columnas)."""
    tabla = pd.pivot_table(df, index="marca", columns="combustible", values="precio", aggfunc="mean")
    return tabla.round(0)
