"""
Prueba rápida de la API para la ficha del Anexo A.
Ejecutar con:  python probar_api.py
Muestra el código de estado, cuántas estaciones llegaron (Chile y Los Lagos) y un ejemplo de Puerto Montt.
"""
import json

import requests

from modulos.api import ENCABEZADOS, URL_BASE, URL_ESTACIONES, URL_MARCAS, describir_codigo

REGION = "De los Lagos"
COMUNA = "Puerto Montt"

print("1) Consulta de estaciones:", URL_ESTACIONES)
respuesta = requests.get(URL_ESTACIONES, headers=ENCABEZADOS, timeout=30)
print("   Código de estado:", respuesta.status_code, "→", describir_codigo(respuesta.status_code))

if respuesta.status_code == 200:
    estaciones = respuesta.json()["data"]  # la API entrega todas las estaciones de Chile
    n_registros = sum(len(e.get("combustibles", [])) for e in estaciones)
    print("   Estaciones recibidas (todo Chile):", len(estaciones))
    print("   Registros estación × combustible (todo Chile):", n_registros)

    # Estaciones de la Región de Los Lagos y, dentro de ella, de Puerto Montt
    de_la_region = [e for e in estaciones if e.get("region") == REGION]
    print("   Estaciones en la Región de Los Lagos:", len(de_la_region))
    print("   Registros estación × combustible en Los Lagos:",
          sum(len(e.get("combustibles", [])) for e in de_la_region))
    de_la_comuna = [e for e in de_la_region if e.get("comuna") == COMUNA]
    registros_comuna = sum(len(e.get("combustibles", [])) for e in de_la_comuna)
    print(f"   Estaciones en {COMUNA}:", len(de_la_comuna))
    print(f"   Registros estación × combustible en {COMUNA}:", registros_comuna)

    if de_la_comuna:
        ejemplo = de_la_comuna[0]
        ejemplo_corto = {  # solo los campos que usa el proyecto, y el primer combustible
            "id": ejemplo.get("id"), "marca": ejemplo.get("marca"), "comuna": ejemplo.get("comuna"),
            "direccion": ejemplo.get("direccion"), "latitud": ejemplo.get("latitud"),
            "longitud": ejemplo.get("longitud"), "combustibles": ejemplo.get("combustibles", [])[:1],
        }
        print(f"   Ejemplo (primera estación de {COMUNA}):")
        print(json.dumps(ejemplo_corto, indent=2, ensure_ascii=False))

print("\n2) Consulta de marcas:", URL_MARCAS)
respuesta_marcas = requests.get(URL_MARCAS, headers=ENCABEZADOS, timeout=30)
print("   Código de estado:", respuesta_marcas.status_code, "→", describir_codigo(respuesta_marcas.status_code))

print("\n3) ¿Qué pasa si la consulta está mal escrita?")
mala = requests.get(URL_BASE + "/busqueda_estacion_filtroo", headers=ENCABEZADOS, timeout=30)
print("   Código de estado:", mala.status_code, "→", describir_codigo(mala.status_code))
