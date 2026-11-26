"""
Módulo de gráficos (matplotlib). Cada función devuelve una figura con título y
ejes con unidades; la app la muestra con st.pyplot().
"""
import matplotlib

matplotlib.use("Agg")  # dibuja sin abrir ventanas (necesario dentro de Streamlit)
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from modulos.indicadores import precio_umbral

# Colores del dashboard
AZUL = "#1f4e79"
VERDE = "#2e8b57"
GRIS = "#a6a6a6"
NARANJO = "#e07b00"


def miles(valor, decimales=0):
    """Formato chileno: 1234567.8 -> '1.234.568'."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


FORMATO_MILES = FuncFormatter(lambda v, _: miles(v))


def _figura(alto=4.5):
    fig, ax = plt.subplots(figsize=(8, alto))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="both", alpha=0.25)
    return fig, ax


def dispersion_precio_distancia(estaciones, referencia, supuestos):
    """Dispersión: precio vs distancia desde tu ubicación, con la curva de 'conviene / no conviene'."""
    fig, ax = _figura(5)
    otras = estaciones[estaciones["estacion_id"] != referencia["estacion_id"]]
    convienen = otras[otras["conviene"]]
    no_convienen = otras[~otras["conviene"]]
    ax.scatter(no_convienen["distancia_ruta_km"], no_convienen["precio"], color=GRIS, s=45,
               label="Te conviene menos que el más cercano", zorder=3)
    ax.scatter(convienen["distancia_ruta_km"], convienen["precio"], color=VERDE, s=55,
               label="Te conviene más que el más cercano", zorder=3)
    ax.scatter([referencia["distancia_ruta_km"]], [referencia["precio"]], color=NARANJO, s=140, marker="*",
               label="El más cercano", zorder=4)

    x_max = max(estaciones["distancia_ruta_km"].max(), 1) * 1.05
    x = [i * x_max / 100 for i in range(101)]
    ax.plot(x, precio_umbral(referencia["litros_netos"], x, supuestos["monto_carga"],
                             supuestos["rendimiento"]),
            color=AZUL, linestyle="--", linewidth=1.5, label="Precio máximo para que convenga")

    ax.set_title("Precio y distancia de cada servicentro")
    ax.set_xlabel("Distancia desde donde estás (km por calles)")
    ax.set_ylabel("Precio ($/L)")
    ax.yaxis.set_major_formatter(FORMATO_MILES)
    ax.legend(loc="best", fontsize=8, frameon=False)
    fig.tight_layout()
    return fig


def barras_ganancia_vs_gasto(estaciones, id_mejor, id_cercana, precio_promedio, monto_carga, cantidad=10):
    """
    Barras agrupadas por servicentro, en litros: litros que ganas por el precio (frente al promedio)
    y litros que gastas en ir y volver. Se muestran los que más litros dejan, y SIEMPRE el recomendado
    y el más cercano.
    """
    orden = estaciones.sort_values("te_queda_litros", ascending=False)
    elegidos = orden.head(cantidad)
    obligados = orden[orden["estacion_id"].isin([id_mejor, id_cercana]) & ~orden.index.isin(elegidos.index)]
    datos = pd.concat([elegidos, obligados]).sort_values("te_queda_litros").reset_index(drop=True)

    etiquetas = []
    for _, fila in datos.iterrows():
        nombre = fila["estacion"] if len(fila["estacion"]) <= 34 else fila["estacion"][:33] + "…"
        if fila["estacion_id"] == id_mejor:
            nombre += " (tu mejor opción)"
        elif fila["estacion_id"] == id_cercana:
            nombre += " (el más cercano)"
        etiquetas.append(nombre)

    posiciones = list(range(len(datos)))
    fig, ax = _figura(max(3.5, 0.62 * len(datos) + 1.4))
    ax.barh([p + 0.2 for p in posiciones], datos["litros_vs_promedio"], height=0.4, color=VERDE,
            label="Litros que ganas por el precio")
    ax.barh([p - 0.2 for p in posiciones], datos["litros_trayecto"], height=0.4, color=NARANJO,
            label="Litros que gastas en el viaje")
    x_texto = max(datos["litros_vs_promedio"].max(), datos["litros_trayecto"].max(), 0.01) * 1.05
    for p, queda in zip(posiciones, datos["te_queda_litros"]):
        if abs(queda) < 0.005:
            texto = "quedas igual"
        elif queda > 0:
            texto = f"te quedan {miles(queda, 2)} L más"
        else:
            texto = f"pierdes {miles(-queda, 2)} L"
        ax.text(x_texto, p, texto, va="center", fontsize=8)
    ax.set_yticks(posiciones)
    ax.set_yticklabels(etiquetas)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlim(right=x_texto * 1.35)
    # "\\$" evita que matplotlib lea el texto entre dos signos $ como fórmula matemática
    fig.suptitle(f"Litros que ganas por el precio vs. litros del viaje, cargando \\${miles(monto_carga)} "
                 f"(precio promedio: \\${miles(precio_promedio)}/L)")
    ax.set_xlabel("Litros por carga (L)")
    ax.set_ylabel("Servicentro")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: miles(v, 2)))
    ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    ax.grid(axis="y", alpha=0)
    fig.tight_layout()
    return fig


def barras_ranking_precios(estaciones, id_mejor=None, id_mas_barata=None):
    """Barras horizontales: todas las estaciones ordenadas por precio (la más barata arriba)."""
    datos = estaciones.sort_values("precio", ascending=False)
    etiquetas = [e if len(e) <= 45 else e[:44] + "…" for e in datos["estacion"]]
    colores = []
    for estacion_id in datos["estacion_id"]:
        if estacion_id == id_mejor:
            colores.append(VERDE)
        elif estacion_id == id_mas_barata:
            colores.append(AZUL)
        else:
            colores.append(GRIS)
    fig, ax = _figura(max(3, 0.28 * len(datos) + 1.5))
    ax.barh(etiquetas, datos["precio"], color=colores)
    ax.set_xlim(datos["precio"].min() - 15, datos["precio"].max() + 5)  # eje recortado para ver diferencias
    fig.suptitle("Precio de cada servicentro (verde: tu mejor opción · azul: el más barato)")
    ax.set_xlabel("Precio ($/L) · el eje no parte en cero")
    ax.set_ylabel("Servicentro")
    ax.xaxis.set_major_formatter(FORMATO_MILES)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="y", alpha=0)
    fig.tight_layout()
    return fig


def barras_precio_por_marca(resumen, marca_destacada=None):
    """Barras horizontales: precio promedio por marca en Puerto Montt; destaca una marca."""
    datos = resumen.sort_values("Promedio ($/L)", ascending=False)
    etiquetas = [f"{marca} ({int(n)})" for marca, n in zip(datos.index, datos["N° estaciones"])]
    fig, ax = _figura(max(3, 0.5 * len(datos) + 1.2))
    colores = [NARANJO if m == marca_destacada else AZUL for m in datos.index]
    ax.barh(etiquetas, datos["Promedio ($/L)"], color=colores)
    minimo = datos["Promedio ($/L)"].min()
    ax.set_xlim(minimo - 20, datos["Promedio ($/L)"].max() + 10)  # eje recortado para ver diferencias
    fig.suptitle("Precio promedio por marca (naranjo: la de tu mejor opción)")
    ax.set_xlabel("Precio promedio ($/L) · el eje no parte en cero")
    ax.set_ylabel("Marca (n° de servicentros)")
    ax.xaxis.set_major_formatter(FORMATO_MILES)
    ax.grid(axis="y", alpha=0)
    fig.tight_layout()
    return fig


def lineas_sensibilidad(tabla, km_actual, rendimiento_actual):
    """Líneas: ahorro anual de la mejor alternativa según km al mes, para distintos rendimientos."""
    fig, ax = _figura(4.5)
    colores = [NARANJO, AZUL, VERDE, GRIS]
    for color, (r, grupo) in zip(colores, tabla.groupby("rendimiento")):
        ax.plot(grupo["km_mes"], grupo["ahorro_anual"], color=color, linewidth=2, label=f"Auto de {r} km/L")
    ax.axvline(km_actual, color="black", linestyle=":", linewidth=1)
    ax.text(km_actual, ax.get_ylim()[1], f"  tú: {miles(km_actual)} km al mes",
            va="top", fontsize=8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("¿Y si manejas más o menos?")
    ax.set_xlabel("Km que manejas al mes")
    ax.set_ylabel("Ahorro al año ($)")
    ax.yaxis.set_major_formatter(FORMATO_MILES)
    ax.xaxis.set_major_formatter(FORMATO_MILES)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    return fig
