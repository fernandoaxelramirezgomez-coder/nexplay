"""Las 25 preguntas reales de la fase 6F, contra /nia, con sus reglas y su latencia.

Manda cada pregunta a la API como lo haría el chat: con su juego abierto cuando lo hay, con
el hilo anterior cuando es de seguimiento («¿y cuál de esos…?», «resume») y con una lista
de sugerencias cuando se pregunta con perfil. De cada respuesta anota si rompe una regla de
Nia y cuánto tardó.

La corrida con IA la hace el dueño del proyecto: este script no decide el modo, lo decide
la API a la que se apunta. Contra una API sin clave de OpenAI responde el modo
demostración.

Uso:
  .venv/bin/python calidad/preguntas_nia.py --etiqueta despues
  .venv/bin/python calidad/preguntas_nia.py --api http://localhost:8010 --etiqueta demostracion
  .venv/bin/python calidad/preguntas_nia.py --comparar antes despues

Cada corrida queda en registros/preguntas_nia-<etiqueta>.json.
"""

import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REGISTROS = RAIZ / "registros"
USUARIO = "preguntas-nia-script"

# Los mismos rangos que api/nia/agente.py (EMOJI): pictogramas y símbolos misceláneos.
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF]\ufe0f?")
PROHIBIDAS = ("banda", "cómprate", "comprate", "te recomiendo comprar", "deberías comprar", "compra este", "abandono")

HADES, HOLLOW_KNIGHT, A_SHORT_HIKE, CUPHEAD = 1145360, 367520, 1055540, 268910
DISCO_ELYSIUM, DIABLO_IV = 632470, 2344520

# La lista que mandaría el navegador con un perfil de Rol entre $200 y $500.
SUGERENCIAS = [
    {"appid": HADES, "razones": ["coincide en Rol", "cuesta $283, dentro de lo que dijiste pagar"]},
    {"appid": DISCO_ELYSIUM, "razones": ["coincide en Rol", "cuesta $459, dentro de lo que dijiste pagar"]},
    {"appid": DIABLO_IV, "razones": ["coincide en Rol", "cuesta $250, dentro de lo que dijiste pagar"]},
]


def _contiene(*frases: str):
    return lambda r: any(f.lower() in r["respuesta"].lower() for f in frases), f"dice {' o '.join(frases)}"


def _juegos(minimo: int):
    return lambda r: len(r.get("juegos", [])) >= minimo, f"trae {minimo} tarjetas o más"


def _con(*appids: int):
    return lambda r: all(a in r.get("juegos", []) for a in appids), f"trae las tarjetas {appids}"


def _bandera(nombre: str):
    return lambda r: bool(r.get(nombre)), f"marca {nombre}"


def _sugiere():
    return lambda r: bool(r.get("sugerencias")), "trae sugerencias del perfil"


# Cada pregunta: su texto, el juego abierto, a qué pregunta anterior le sigue (su hilo
# entra completo, con las respuestas reales de esta corrida) y qué se espera de ella.
PREGUNTAS = [
    {"n": 1, "pregunta": "¿Qué juegos de acción tienen riesgo bajo?", "espera": [_juegos(3), _contiene("25")]},
    {"n": 2, "pregunta": "¿y cuál de esos es el más barato?", "sigue": 1, "espera": [_contiene("Dead Cells", "gratis")]},
    {"n": 3, "pregunta": "Resume lo que me dijiste", "sigue": 2, "espera": [_contiene("25", "Dead Cells", "gratis")]},
    {"n": 4, "pregunta": "Compara Hades y Hollow Knight", "espera": [_con(HADES, HOLLOW_KNIGHT)]},
    {"n": 5, "pregunta": "¿Cuál me compro?", "sigue": 4, "espera": [_contiene("precio", "riesgo", "crítica")]},
    {"n": 6, "pregunta": "Que tal Zelda Breath of the Wild", "espera": [_contiene("no está", "no encuentro")]},
    {"n": 7, "pregunta": "¿Hay algo gratis?", "espera": [_juegos(3)]},
    {"n": 8, "pregunta": "juegos de estrategia baratos", "espera": [_juegos(3)]},
    {"n": 9, "pregunta": "algo para jugar poco entre semana", "espera": [_juegos(3)]},
    {"n": 10, "pregunta": "¿cuál es el más difícil?", "espera": [_contiene("dificultad")]},
    {"n": 11, "pregunta": "¿qué hay nuevo?", "espera": [_juegos(1)]},
    {"n": 12, "pregunta": "baldurs gate 3 vale la pena?", "espera": [_contiene("Baldur")]},
    {"n": 13, "pregunta": "¿Por qué tiene ese riesgo?", "espera": [_bandera("pide_juego")]},
    {"n": 14, "pregunta": "¿Qué me recomiendas?", "sugerencias": True, "espera": [_sugiere()]},
    {"n": 15, "pregunta": "¿Qué me recomiendas?", "espera": [_bandera("pide_perfil")]},
    {"n": 16, "pregunta": "es bueno el juego?", "appid": A_SHORT_HIKE, "espera": [_contiene("A Short Hike")]},
    {"n": 17, "pregunta": "¿Cuánto cuesta?", "appid": HADES, "espera": [_contiene("$283")]},
    {"n": 18, "pregunta": "¿Qué dice la crítica?", "appid": HADES, "espera": [_contiene("93")]},
    {"n": 19, "pregunta": "se parece al mario bros o sonic?", "appid": CUPHEAD, "espera": [_contiene("catálogo")]},
    {"n": 20, "pregunta": "lo que dijiste antes, más corto", "sigue": 3, "espera": [_contiene("25", "Dead Cells", "gratis")]},
    {"n": 21, "pregunta": "¿de dónde salen los datos?", "espera": [_contiene("reseñas")]},
    {"n": 22, "pregunta": "¿qué juego me ayuda a estudiar la naturaleza?", "espera": []},
    {"n": 23, "pregunta": "dame juegos de rol de menos de 300 pesos", "espera": [_juegos(3)]},
    {"n": 24, "pregunta": "¿cuántos juegos tienen riesgo alto?", "espera": [_contiene("43")]},
    {"n": 25, "pregunta": "gracias, eres lo máximo", "espera": []},
]


def _palabras(texto: str) -> int:
    return len([p for p in EMOJI.sub(" ", texto).split() if p.strip("¡!¿?.,;:")])


def _fallas(respuesta: dict, espera: list, anterior: str | None) -> list[str]:
    texto = respuesta["respuesta"]
    fallas = []
    if _palabras(texto) > 60:
        fallas.append(f"{_palabras(texto)} palabras (máximo 60)")
    emojis = len(EMOJI.findall(texto))
    if not 1 <= emojis <= 3:
        fallas.append(f"{emojis} emojis (de 1 a 3)")
    # El remate va al final, aunque lo siga un emoji. Cuando Nia pide el juego, lo que
    # invita a seguir es el buscador que trae el mensaje, no una pregunta.
    if not respuesta.get("pide_juego") and not EMOJI.sub("", texto).rstrip().endswith("?"):
        fallas.append("no cierra con una pregunta")
    for prohibida in PROHIBIDAS:
        if re.search(rf"(?<!\w){re.escape(prohibida)}(?!\w)", texto.lower()):
            fallas.append(f"dice «{prohibida}»")
    if anterior is not None and texto.strip() == anterior.strip():
        fallas.append("repite la respuesta anterior")
    for comprobar, descripcion in espera:
        if not comprobar(respuesta):
            fallas.append(f"no {descripcion}")
    return fallas


def _preguntar(api: str, cuerpo: dict) -> tuple[dict, float]:
    """La respuesta y los milisegundos de la petición que sí se contestó: la espera por el
    límite de frecuencia (429) no cuenta como latencia."""
    datos = json.dumps(cuerpo).encode()
    while True:
        peticion = urllib.request.Request(f"{api}/nia", data=datos, headers={"Content-Type": "application/json"})
        inicio = time.perf_counter()
        try:
            with urllib.request.urlopen(peticion, timeout=90) as respuesta:
                cuerpo_respuesta = json.load(respuesta)
            return cuerpo_respuesta, (time.perf_counter() - inicio) * 1000
        except urllib.error.HTTPError as error:
            if error.code != 429:
                raise
            espera = float(error.headers.get("Retry-After", "7"))
            print(f"    (límite de frecuencia: espero {espera:.0f} s)")
            time.sleep(espera)


def correr(api: str, etiqueta: str) -> int:
    hilos: dict[int, list[dict]] = {}
    resultados = []
    for caso in PREGUNTAS:
        previo = hilos.get(caso["sigue"], []) if caso.get("sigue") else []
        mensajes = [*previo, {"rol": "usuario", "contenido": caso["pregunta"]}]
        cuerpo = {"usuario": USUARIO, "mensajes": mensajes}
        if caso.get("appid"):
            cuerpo["appid"] = caso["appid"]
        if caso.get("sugerencias"):
            cuerpo["sugerencias"] = SUGERENCIAS
        respuesta, ms = _preguntar(api, cuerpo)
        anterior = next((m["contenido"] for m in reversed(previo) if m["rol"] == "nia"), None)
        fallas = _fallas(respuesta, caso["espera"], anterior)
        hilos[caso["n"]] = [*mensajes, {"rol": "nia", "contenido": respuesta["respuesta"]}]
        resultados.append({
            "n": caso["n"],
            "pregunta": caso["pregunta"],
            "appid": caso.get("appid"),
            "respuesta": respuesta["respuesta"],
            "modo": respuesta["modo"],
            "modelo": respuesta.get("modelo"),
            "juegos": respuesta.get("juegos", []),
            "sugerencias": respuesta.get("sugerencias", []),
            "pide_juego": respuesta.get("pide_juego", False),
            "pide_perfil": respuesta.get("pide_perfil", False),
            "palabras": _palabras(respuesta["respuesta"]),
            "emojis": len(EMOJI.findall(respuesta["respuesta"])),
            "ms": round(ms),
            "fallas": fallas,
        })
        estado = "pasa" if not fallas else "FALLA: " + "; ".join(fallas)
        print(f"{caso['n']:>2}. {caso['pregunta'][:48]:48} {round(ms):>6} ms  {estado}")

    latencias = [r["ms"] for r in resultados]
    resumen = {
        "etiqueta": etiqueta,
        "api": api,
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "modos": sorted({r["modo"] for r in resultados}),
        "modelos": sorted({r["modelo"] for r in resultados if r["modelo"]}),
        "pasan": sum(1 for r in resultados if not r["fallas"]),
        "total": len(resultados),
        "p50_ms": round(statistics.median(latencias)),
        "p95_ms": round(statistics.quantiles(latencias, n=20)[-1]),
        "resultados": resultados,
    }
    REGISTROS.mkdir(exist_ok=True)
    destino = REGISTROS / f"preguntas_nia-{etiqueta}.json"
    destino.write_text(json.dumps(resumen, ensure_ascii=False, indent=2))
    print(
        f"\n{resumen['pasan']} de {resumen['total']} pasan · modo {', '.join(resumen['modos'])}"
        f"{' · ' + ', '.join(resumen['modelos']) if resumen['modelos'] else ''}"
        f" · latencia p50 {resumen['p50_ms']} ms, p95 {resumen['p95_ms']} ms\nDetalle en {destino.relative_to(RAIZ)}"
    )
    return 0 if resumen["pasan"] == resumen["total"] else 1


def comparar(antes: str, despues: str) -> int:
    corridas = []
    for etiqueta in (antes, despues):
        ruta = REGISTROS / f"preguntas_nia-{etiqueta}.json"
        if not ruta.exists():
            sys.exit(f"No existe {ruta.relative_to(RAIZ)}: corre primero --etiqueta {etiqueta}")
        corridas.append(json.loads(ruta.read_text()))
    a, b = corridas
    print(f"{'':52} {antes:>18} {despues:>18}")
    for ra, rb in zip(a["resultados"], b["resultados"]):
        marca = lambda r: f"{r['ms']:>6} ms {'pasa' if not r['fallas'] else 'falla'}"
        print(f"{ra['n']:>2}. {ra['pregunta'][:48]:48} {marca(ra):>18} {marca(rb):>18}")
    for nombre, corrida in ((antes, a), (despues, b)):
        print(
            f"{nombre}: {', '.join(corrida['modelos']) or corrida['modos'][0]} · {corrida['pasan']} de {corrida['total']} pasan"
            f" · p50 {corrida['p50_ms']} ms · p95 {corrida['p95_ms']} ms"
        )
    if a["p50_ms"]:
        print(f"La mediana pasa de {a['p50_ms']} a {b['p50_ms']} ms ({(b['p50_ms'] - a['p50_ms']) / a['p50_ms']:+.0%}).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Las 25 preguntas de la 6F contra /nia.")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--etiqueta", help="nombre de la corrida: registros/preguntas_nia-<etiqueta>.json")
    parser.add_argument("--comparar", nargs=2, metavar=("ANTES", "DESPUES"), help="pone dos corridas lado a lado")
    args = parser.parse_args()
    if args.comparar:
        return comparar(*args.comparar)
    if not args.etiqueta:
        parser.error("falta --etiqueta (o --comparar ANTES DESPUES)")
    return correr(args.api.rstrip("/"), args.etiqueta)


if __name__ == "__main__":
    sys.exit(main())
