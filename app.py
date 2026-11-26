"""
Benja Bencina: dashboard que calcula el mejor lugar para cargar bencina en Puerto Montt según dónde estás
Taller de Programación II · Solemne 3

Ejecutar con:  streamlit run app.py
"""
import folium
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from modulos import graficos
from modulos.api import COMUNA, obtener_datos
from modulos.graficos import miles
from modulos.indicadores import (cargas_al_anio, comparar_con_referencia, costos_desde_ubicacion,
                                 ganancia_y_gasto, resumen_por_marca, sensibilidad, tabla_dinamica_marcas)
from modulos.limpieza import estadistica_descriptiva, limpiar

st.set_page_config(page_title="Benja Bencina", layout="wide")

PREGUNTA = ("Según dónde estés en Puerto Montt, ¿en qué servicentro te conviene cargar, cuánto te cuesta llegar "
            "al más barato y cuánto ahorras frente al más cercano?")

# Punto de partida por defecto: centro de Puerto Montt (geodatos.net)
CENTRO = (-41.4693, -72.9424)
# Lugares conocidos para elegir rápido. Angelmó, Pelluco y Av. Presidente Ibáñez usan la ubicación
# de un servicentro de ese sector; Alerce (bamwor.com) y El Tepual (Wikipedia) usan coordenadas publicadas.
LUGARES = {
    "Centro de Puerto Montt": CENTRO,
    "Angelmó": (-41.4815, -72.9559),
    "Pelluco": (-41.4903, -72.8835),
    "Av. Presidente Ibáñez": (-41.4705, -72.9660),
    "Alerce": (-41.3969, -72.9148),
    "Aeropuerto El Tepual": (-41.4386, -73.0939),
}
CUALQUIERA = "Lo más barato (con o sin atención)"
SOLO_ASISTIDO = "Con atención (te atienden)"
SOLO_AUTOSERVICIO = "Autoservicio (cargas tú)"


@st.cache_data(ttl=1800, show_spinner="Consultando la API de Bencina en Línea…")
def cargar_datos_crudos():
    """API → JSON → tabla. Se guarda en caché 30 min para no repetir la consulta a la API."""
    return obtener_datos()


def cargar_datos():
    """Datos crudos (de la caché) + limpieza. La limpieza se hace siempre, así cualquier cambio se aplica al tiro."""
    crudo, origen, mensaje = cargar_datos_crudos()
    if crudo.empty:
        return crudo, pd.DataFrame(), origen, mensaje
    limpio, reporte = limpiar(crudo)
    return limpio, reporte, origen, mensaje


def filtrar_atencion(df, atencion):
    """
    Precio más bajo de cada servicentro (sea asistido o autoservicio), o solo un tipo de atención.
    Ojo: solo algunos servicentros tienen autoservicio; los demás no aparecen con esa opción.
    """
    if atencion == SOLO_ASISTIDO:
        return df[df["atencion"] == "Asistido"]
    if atencion == SOLO_AUTOSERVICIO:
        return df[df["atencion"] == "Autoservicio"]
    return df.sort_values("precio").drop_duplicates(subset=["estacion_id", "combustible"])


def mostrar(figura):
    """Muestra una figura de matplotlib y libera la memoria."""
    st.pyplot(figura)
    plt.close(figura)


def pesos(valor):
    """Formato de dinero: 1234.5 -> '$1.235'; -50 -> '-$50'."""
    return f"-${miles(-valor)}" if valor < 0 else f"${miles(valor)}"


def km(valor):
    """Formato de distancia con coma decimal: 2.345 -> '2,3 km'."""
    return f"{miles(valor, 1)} km"


def litros(valor):
    """Formato de litros con dos decimales: 12.4533 -> '12,45 L'."""
    return f"{miles(valor, 2)} L"


def elegir_lugar():
    """Cuando la persona elige un lugar conocido, ese lugar pasa a ser su ubicación."""
    lugar = st.session_state["lugar_conocido"]
    if lugar in LUGARES:
        st.session_state["ubicacion"] = LUGARES[lugar]
        st.session_state["descripcion_ubicacion"] = lugar


# Ubicación guardada entre clics (st.session_state recuerda valores mientras la página está abierta)
if "ubicacion" not in st.session_state:
    st.session_state["ubicacion"] = CENTRO
    st.session_state["descripcion_ubicacion"] = "Centro de Puerto Montt"
    st.session_state["ultimo_clic"] = None

# ======================= ENCABEZADO =======================
datos, reporte, origen, mensaje = cargar_datos()

st.title("Benja Bencina")
st.markdown("#### Calcula el mejor lugar para cargar bencina en Puerto Montt, según dónde estás ubicado.")
st.markdown("Marca en el mapa dónde estás y elige cuánta plata vas a cargar. Te decimos dónde te rinde más, "
            "contando también la bencina que gastas en llegar.")
st.caption(f"Pregunta del proyecto: {PREGUNTA} · Datos: Bencina en Línea (CNE).")

if origen == "api":
    st.success(mensaje)
elif origen == "respaldo":
    st.warning(mensaje)  # plan B visible
else:
    st.error(mensaje)
    st.stop()

# ======================= BARRA LATERAL =======================
st.sidebar.header("Tu combustible")
combustible = st.sidebar.selectbox("¿Qué cargas?", ["Gasolina 93", "Gasolina 95", "Gasolina 97", "Diésel"])
atencion = st.sidebar.selectbox("¿Cómo cargas?", [CUALQUIERA, SOLO_ASISTIDO, SOLO_AUTOSERVICIO],
                                help="El autoservicio es más barato, pero solo algunos servicentros lo tienen.")
monto_carga = st.sidebar.select_slider("¿Cuánta plata vas a cargar?", options=list(range(5000, 100001, 1000)),
                                       value=20000, format_func=lambda v: f"${miles(v)}",
                                       help="Con esta plata calculamos cuántos litros te cargan en cada servicentro.")

st.sidebar.header("Tu auto")
rendimiento = st.sidebar.slider("¿Cuántos km por litro hace tu auto?", 5, 25, 12,
                                help="Si no sabes, deja 12. Es lo normal en un auto mediano.")
km_mes = st.sidebar.slider("¿Cuántos km manejas al mes?", 200, 5000, 1000, step=100,
                           help="Sirve para calcular el ahorro del año.")

with st.sidebar.expander("Opciones avanzadas"):
    factor_ruta = st.slider("Factor de ruta", 1.0, 2.0, 1.3, step=0.05,
                            help="Las calles no son línea recta. 1,3 significa que manejas un 30% más que en "
                                 "línea recta. Si no sabes, deja 1,3.")
    max_dias = st.slider("No usar precios con más de… días sin actualizar", 1, 60, 30)
    excluir_atipicos = st.checkbox("Quitar precios raros", value=True,
                                   help="Precios muy distintos al resto (regla 3 × RIQ). Suelen ser errores.")
    marcas = st.multiselect("Solo estas marcas (vacío = todas)", sorted(datos["marca"].unique()))

if st.sidebar.button("Actualizar precios"):
    st.cache_data.clear()
    st.rerun()

supuestos = {"rendimiento": rendimiento, "km_mes": km_mes,
             "monto_carga": monto_carga, "factor_ruta": factor_ruta}

# Aplicamos los filtros con Pandas
filtrado = datos[(datos["combustible"] == combustible) & (datos["dias_sin_actualizar"] <= max_dias)]
if excluir_atipicos:
    filtrado = filtrado[~filtrado["atipico"]]
if marcas:
    filtrado = filtrado[filtrado["marca"].isin(marcas)]
filtrado = filtrar_atencion(filtrado, atencion)

if filtrado.empty:
    st.info("No hay servicentros con esas opciones. Prueba con otras.")
    st.stop()
if atencion == SOLO_AUTOSERVICIO:
    st.sidebar.caption(f"Solo {filtrado['estacion_id'].nunique()} servicentros tienen autoservicio.")

# ======================= INDICADORES =======================
lat0, lon0 = st.session_state["ubicacion"]
estaciones = costos_desde_ubicacion(filtrado, lat0, lon0, supuestos)    # litros que cargas, gastas y te quedan
cercana = estaciones.loc[estaciones["distancia_km"].idxmin()]           # referencia: la más cercana
estaciones = comparar_con_referencia(estaciones, cercana, supuestos)
cercana = estaciones.loc[cercana.name]
mejor = estaciones.loc[estaciones["litros_netos"].idxmax()]             # más litros te quedan (carga − viaje)
mas_barata = estaciones.sort_values(["precio", "distancia_km"]).iloc[0]  # menor precio por litro
ranking = estaciones.sort_values("litros_netos", ascending=False)

# ======================= PESTAÑAS =======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dónde cargar", "Precios", "Cómo se calcula", "Calidad de datos", "Datos"])

with tab1:
    # ---- 1. Mapa: la persona marca su ubicación con un clic ----
    st.subheader("1. ¿Dónde estás?")
    izquierda, derecha = st.columns([3, 1])
    with derecha:
        st.markdown("Haz **clic en el mapa** donde estás. O elige un lugar:")
        st.selectbox("Lugar conocido", ["—"] + list(LUGARES), key="lugar_conocido", on_change=elegir_lugar,
                     label_visibility="collapsed")
        st.markdown(f"**Partes desde:** {st.session_state['descripcion_ubicacion']}.")
        st.markdown(
            "<span style='color:#e07b00'>●</span> Tú &nbsp; <span style='color:#2e8b57'>●</span> Tu mejor opción "
            "<br><span style='color:#1f4e79'>●</span> El más barato &nbsp; <span style='color:#7f7f7f'>●</span> "
            "Otros", unsafe_allow_html=True)
    with izquierda:
        mapa = folium.Map(location=[lat0, lon0], zoom_start=13)
        for _, fila in estaciones.iterrows():
            if fila["estacion_id"] == mejor["estacion_id"]:
                color = "#2e8b57"
            elif fila["estacion_id"] == mas_barata["estacion_id"]:
                color = "#1f4e79"
            else:
                color = "#7f7f7f"
            folium.CircleMarker(
                location=[fila["latitud"], fila["longitud"]], radius=8, color=color, fill=True, fill_opacity=0.9,
                tooltip=f"{fila['estacion']}: {pesos(fila['precio'])}/L ({fila['atencion'].lower()}), "
                        f"a {km(fila['distancia_ruta_km'])}",
            ).add_to(mapa)
        folium.Marker(location=[lat0, lon0], tooltip="Tú estás aquí",
                      icon=folium.Icon(color="orange", icon="user", prefix="fa")).add_to(mapa)
        salida = st_folium(mapa, height=430, use_container_width=True, returned_objects=["last_clicked"],
                           key="mapa")

    # Si hubo un clic nuevo, ese punto pasa a ser la ubicación y se recalcula todo
    clic = salida.get("last_clicked") if salida else None
    if clic and (clic["lat"], clic["lng"]) != st.session_state["ultimo_clic"]:
        st.session_state["ultimo_clic"] = (clic["lat"], clic["lng"])
        st.session_state["ubicacion"] = (clic["lat"], clic["lng"])
        st.session_state["descripcion_ubicacion"] = "el punto que marcaste"
        st.rerun()

    # ---- 2. Recomendación ----
    st.subheader("2. Dónde te conviene cargar")
    st.success(
        f"**{mejor['estacion']}** · {pesos(mejor['precio'])}/L ({mejor['atencion'].lower()}) · "
        f"a {km(mejor['distancia_ruta_km'])}.\n\n"
        f"Con {pesos(monto_carga)} te cargan **{litros(mejor['litros_cargados'])}**. Gastas "
        f"{litros(mejor['litros_trayecto'])} ({pesos(mejor['gasto_llegar'])}) en ir y volver, así que te quedan "
        f"**{litros(mejor['litros_netos'])}**."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Te cargan", litros(mejor["litros_cargados"]), help=f"{pesos(monto_carga)} ÷ {pesos(mejor['precio'])}/L")
    c2.metric("Bencina del viaje", pesos(mejor["gasto_llegar"]),
              help=f"{litros(mejor['litros_trayecto'])} para ir y volver.")
    if mejor["estacion_id"] == cercana["estacion_id"]:
        c3.metric("Ahorras vs. el más cercano", "$0", help="Tu mejor opción es el más cercano.")
    else:
        c3.metric("Ahorras vs. el más cercano", pesos(mejor["ahorro_carga"]),
                  delta=f"{pesos(mejor['ahorro_anual'])} al año", delta_color="normal",
                  help=f"Te quedan {litros(mejor['litros_extra'])} más que en el más cercano. Ahí costarían "
                       f"{pesos(mejor['ahorro_carga'])}.")

    st.markdown(f"**Tus 5 mejores opciones** (cargando {pesos(monto_carga)}; ordenadas por los litros que te quedan)")
    top5 = ranking.head(5)
    st.dataframe(pd.DataFrame({
        "Servicentro": top5["estacion"],
        "Precio": [f"{pesos(p)}/L" for p in top5["precio"]],
        "Distancia": [km(d) for d in top5["distancia_ruta_km"]],
        "Te cargan": [litros(x) for x in top5["litros_cargados"]],
        "Viaje": [pesos(g) for g in top5["gasto_llegar"]],
        "Te quedan": [litros(x) for x in top5["litros_netos"]],
    }), hide_index=True)

    # ---- 3. El más barato ----
    st.subheader("3. El más barato de Puerto Montt")
    a, b, c = st.columns(3)
    a.metric("Precio", f"{pesos(mas_barata['precio'])}/L", help=mas_barata["estacion"])
    b.metric("Distancia", km(mas_barata["distancia_ruta_km"]))
    c.metric("Te cuesta llegar", pesos(mas_barata["gasto_llegar"]),
             help=f"Ida y vuelta: {km(mas_barata['km_ida_vuelta'])}, o sea "
                  f"{miles(mas_barata['litros_trayecto'], 2)} L de bencina.")
    if mas_barata["estacion_id"] == mejor["estacion_id"]:
        st.success(f"**{mas_barata['estacion']}** es el más barato y también tu mejor opción.")
    else:
        diferencia = mejor["litros_netos"] - mas_barata["litros_netos"]
        st.warning(f"**{mas_barata['estacion']}** es el más barato, pero no te conviene: por la bencina del viaje, "
                   f"te quedarían {litros(diferencia)} menos que en tu mejor opción "
                   f"(unos {pesos(diferencia * mejor['precio'])}).")

with tab2:
    st.subheader("Del más barato al más caro")
    mostrar(graficos.barras_ranking_precios(estaciones, mejor["estacion_id"], mas_barata["estacion_id"]))
    st.caption(f"Precio de {combustible} en cada servicentro. El eje no parte en cero, por eso las diferencias "
               f"se ven más grandes.")

    st.subheader("Precio por marca")
    mostrar(graficos.barras_precio_por_marca(resumen_por_marca(filtrado), mejor["marca"]))
    st.caption("Ojo: si una marca tiene pocos servicentros, su promedio dice poco.")
    st.markdown("**Precio promedio por marca y combustible ($/L)**")
    todos = datos[datos["dias_sin_actualizar"] <= max_dias]
    if excluir_atipicos:
        todos = todos[~todos["atipico"]]
    st.dataframe(tabla_dinamica_marcas(filtrar_atencion(todos, atencion)))

with tab3:
    st.subheader("Cómo se calcula")
    st.markdown(
        f"- **Te cargan** = {pesos(monto_carga)} ÷ precio por litro.\n"
        f"- **Bencina del viaje** = km de ida y vuelta ÷ {rendimiento} km por litro (en pesos: × precio).\n"
        f"- **Te quedan** = te cargan − bencina del viaje. **Te recomendamos el que te deja más litros.**\n"
        f"- **Km por calles** = km en línea recta × {miles(factor_ruta, 2)} (factor de ruta).\n"
        f"- Todo se compara con el servicentro más cercano a ti: **{cercana['estacion']}**. "
        f"Los litros de diferencia se pasan a pesos con su precio ({pesos(cercana['precio'])}/L)."
    )
    orden_ids = list(ranking["estacion_id"])
    nombres = dict(zip(ranking["estacion_id"], ranking["estacion"]))
    id_detalle = st.selectbox("Elige un servicentro para ver su cuenta", orden_ids,
                              format_func=lambda i: nombres[i])
    elegida = ranking[ranking["estacion_id"] == id_detalle].iloc[0]
    d1, d2, d3 = st.columns(3)
    d1.metric("Ahorro en el precio", pesos(elegida["ganancia_precio"]),
              help=f"Te cargan {litros(elegida['litros_precio'])} más que en el más cercano")
    d2.metric("Bencina extra del viaje", pesos(elegida["gasto_extra"]),
              help=f"Gastas {litros(elegida['litros_viaje'])} más en ir y volver que al más cercano")
    d3.metric("Resultado", pesos(elegida["ahorro_carga"]),
              delta=f"{pesos(elegida['ahorro_anual'])} al año", delta_color="normal")
    st.markdown(
        f"**Cuenta:** te cargan {miles(monto_carga)} ÷ {miles(elegida['precio'])} = "
        f"**{litros(elegida['litros_cargados'])}**. Bencina del viaje = {miles(elegida['km_ida_vuelta'], 1)} km ÷ "
        f"{rendimiento} = **{litros(elegida['litros_trayecto'])}** ({pesos(elegida['gasto_llegar'])}). "
        f"Te quedan {miles(elegida['litros_cargados'], 2)} − {miles(elegida['litros_trayecto'], 2)} = "
        f"**{litros(elegida['litros_netos'])}**. En el más cercano te quedan **{litros(cercana['litros_netos'])}**: "
        f"la diferencia es {litros(elegida['litros_extra'])}, que a {pesos(cercana['precio'])}/L son "
        f"**{pesos(elegida['ahorro_carga'])}**."
    )

    precio_promedio = filtrado["precio"].mean()
    con_ganancia = ganancia_y_gasto(estaciones, precio_promedio, monto_carga)
    mostrar(graficos.barras_ganancia_vs_gasto(con_ganancia, mejor["estacion_id"], cercana["estacion_id"],
                                              precio_promedio, monto_carga))
    st.caption(f"Verde: los litros de más que te cargan por el precio, frente al promedio ({pesos(precio_promedio)}/L). "
               f"Naranja: los litros que gastas en el viaje. El que más litros te deja es tu mejor opción. "
               f"Verde hacia la izquierda: ese servicentro es más caro que el promedio.")

    if (estaciones["distancia_km"] <= 10).sum() >= 2:
        mostrar(graficos.dispersion_precio_distancia(estaciones[estaciones["distancia_km"] <= 10], cercana, supuestos))
        st.caption("Cada punto es un servicentro a menos de 10 km. Los que quedan bajo la línea punteada (verdes) "
                   "te convienen más que el más cercano.")

    st.subheader("¿Y si cambian los datos de tu auto?")
    objetivo = mejor if mejor["estacion_id"] != cercana["estacion_id"] else mas_barata
    if objetivo["estacion_id"] == cercana["estacion_id"]:
        st.info("El más cercano ya es el más barato. No hay nada que comparar.")
    else:
        mostrar(graficos.lineas_sensibilidad(sensibilidad(cercana, objetivo, monto_carga), km_mes, rendimiento))
        st.caption(f"Ahorro al año de cargar siempre en {objetivo['estacion']} en vez del más cercano. "
                   f"Bajo cero: pierdes plata.")
        dos = filtrado.loc[[cercana.name, objetivo.name]]
        filas = []
        for f in [1.0, 1.3, 1.6]:
            fila = {"Factor de ruta": f}
            for r in [8, 12, 16]:
                caso = costos_desde_ubicacion(dos, lat0, lon0, {**supuestos, "factor_ruta": f, "rendimiento": r})
                ref, alt = caso.iloc[0], caso.iloc[1]
                ahorro_carga = (alt["litros_netos"] - ref["litros_netos"]) * ref["precio"]
                fila[f"{r} km/L"] = pesos(ahorro_carga * cargas_al_anio(km_mes, r, ref["litros_cargados"]))
            filas.append(fila)
        st.markdown(f"**Ahorro al año en {objetivo['estacion']}, según el factor de ruta y los km por litro**")
        st.dataframe(pd.DataFrame(filas), hide_index=True)

with tab4:
    st.subheader("Revisión de los datos de la API")
    st.caption("Revisamos cada problema, aunque haya cero casos.")
    st.dataframe(reporte, hide_index=True)
    st.subheader("Resumen de precios")
    st.caption(f"{COMUNA}, datos ya revisados. Calculado con NumPy.")
    st.dataframe(estadistica_descriptiva(datos), hide_index=True)

with tab5:
    st.subheader("Todos los servicentros, desde donde estás")
    columnas = {"estacion": "Servicentro", "atencion": "Atención", "precio": "Precio ($/L)",
                "distancia_ruta_km": "Distancia (km)", "litros_cargados": f"Te cargan con {pesos(monto_carga)} (L)",
                "litros_trayecto": "Bencina del viaje (L)", "gasto_llegar": "Bencina del viaje ($)",
                "litros_netos": "Te quedan (L)", "ahorro_carga": "Ahorras vs. el más cercano ($)",
                "ahorro_anual": "Ahorro al año ($)", "dias_sin_actualizar": "Días sin actualizar"}
    tabla = ranking[list(columnas)].rename(columns=columnas).round(2)
    st.dataframe(tabla, hide_index=True)
    st.download_button("Descargar en CSV", data=tabla.to_csv(index=False).encode("utf-8-sig"),
                       file_name="servicentros_puerto_montt.csv", mime="text/csv")
