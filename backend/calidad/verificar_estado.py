"""GET /estado: el sistema de un vistazo, sin datos sensibles y sin consultas a la base.

Revisa:
1. Los valores: si Nia tiene OpenAI, el release servido (el de la marca de preparar_entorno),
   cuántos juegos hay y con qué modelo de riesgo, igual que lo que ya está en memoria.
2. Con una clave de OpenAI puesta, que la clave no salga ni en el JSON ni en los logs: solo el
   booleano y el nombre del modelo.
3. Sin la marca, el release es None, no un error.
4. Que no abra la base: en Render también sirve para saber si el servicio despertó.
5. Que el esquema no gane campos sin revisión: lo que se agregue aquí lo ve cualquiera.

Uso, desde backend/:
    python calidad/verificar_estado.py        # sale 1 si algún chequeo falla
"""

import io
import logging
import sqlite3
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# Corre desde calidad/, así que la raíz no está en sys.path y `api` no se encontraría.
sys.path.insert(0, str(RAIZ))

from api import catalogo, estado, main, scoring  # noqa: E402
from api.config import configuracion  # noqa: E402
from api.schemas import EstadoSistema  # noqa: E402

CAMPOS = {"nia_con_openai", "modelo_nia", "datos_release", "juegos_catalogo", "modelo_version", "modelo_datos",
          "modelo_juegos_entrenamiento"}
CLAVE_FALSA = "sk-prueba-esta-clave-no-debe-salir-0123456789"


def main_() -> int:
    problemas = []

    respuesta = main.ver_estado()
    modelo = scoring.ficha_del_modelo()
    esperado = {
        "nia_con_openai": configuracion.hay_openai,
        "datos_release": estado.release_servido(),
        "juegos_catalogo": len(catalogo.buscar()),
        "modelo_version": modelo["version"],
        "modelo_datos": modelo["datos"],
        "modelo_juegos_entrenamiento": modelo["juegos_entrenamiento"],
    }
    distintos = {k: (getattr(respuesta, k), v) for k, v in esperado.items() if getattr(respuesta, k) != v}
    if distintos:
        problemas.append(f"los valores no son los de memoria (dice, esperado): {distintos}")
    print(f"1 · valores: {respuesta.model_dump()}")

    # Con clave y modelo puestos: el booleano y el nombre del modelo sí; la clave, nunca.
    registro = io.StringIO()
    manejador = logging.StreamHandler(registro)
    raiz = logging.getLogger()
    nivel = raiz.level
    raiz.addHandler(manejador)
    raiz.setLevel(logging.DEBUG)
    antes = (configuracion.openai_api_key, configuracion.nexplay_modelo_nia)
    try:
        configuracion.openai_api_key, configuracion.nexplay_modelo_nia = CLAVE_FALSA, "gpt-prueba"
        con_clave = main.ver_estado()
        cuerpo = con_clave.model_dump_json()
    finally:
        configuracion.openai_api_key, configuracion.nexplay_modelo_nia = antes
        raiz.removeHandler(manejador)
        raiz.setLevel(nivel)
    if CLAVE_FALSA in cuerpo or CLAVE_FALSA[:12] in registro.getvalue():
        problemas.append("la clave de OpenAI sale en la respuesta o en los logs")
    if not con_clave.nia_con_openai or con_clave.modelo_nia != "gpt-prueba":
        problemas.append(f"con clave y modelo no dice que Nia usa OpenAI: {con_clave.model_dump()}")
    print("2 · con clave: dice que Nia usa OpenAI y qué modelo; la clave no sale en el JSON ni en los logs")

    if estado.release_servido(Path("/no/existe/nexplay.db.origen.json")) is not None:
        problemas.append("sin la marca, el release no es None")
    print("3 · sin la marca, el release es None")

    abiertas = []
    conectar = sqlite3.connect
    sqlite3.connect = lambda *a, **k: abiertas.append(a) or conectar(*a, **k)
    try:
        inicio = time.perf_counter()
        for _ in range(100):
            main.ver_estado()
        milisegundos = (time.perf_counter() - inicio) * 10
    finally:
        sqlite3.connect = conectar
    if abiertas:
        problemas.append(f"GET /estado abre la base ({len(abiertas)} veces)")
    print(f"4 · sin abrir la base; {milisegundos:.2f} ms por llamada")

    if set(EstadoSistema.model_fields) != CAMPOS:
        problemas.append(f"el esquema cambió sin revisión: {sorted(set(EstadoSistema.model_fields) ^ CAMPOS)}")
    print(f"5 · el esquema tiene solo los {len(CAMPOS)} campos revisados")

    print()
    for problema in problemas:
        print(f"PROBLEMA: {problema}")
    if problemas:
        return 1
    print("estado: GET /estado dice el sistema de un vistazo, sin la clave y sin abrir la base")
    return 0


if __name__ == "__main__":
    sys.exit(main_())
