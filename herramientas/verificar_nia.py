"""Comprueba lo que Nia dice y cómo se guardan los votos a sus respuestas.

La banda la pone el modelo con datos del juego; las reseñas solo dicen de qué se queja la
gente. Nia confundía las dos cosas porque su contexto no traía los factores, así que este
script revisa lo que se le manda (api/nia.py, _contexto_para_prompt) y lo que responde el
modo demostración, que es el mismo camino sin gastar una llamada.

También revisa el almacén de los votos (fase 5b) contra una base temporal, sin tocar la
de verdad: registrar una respuesta, votarla, cambiar el voto, quitarlo, votar un id que no
existe y comprobar que la retención borra lo vencido y respeta lo reciente.

Uso:
  python verificar_nia.py            revisa contexto, respuestas por reglas y votos; sale 1 si algo falla
  python verificar_nia.py --openai   además manda las dos preguntas al modelo configurado
                                     e imprime la respuesta (eso sí consume cuota)
"""

import argparse
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Corre desde herramientas/, así que la raíz no está en sys.path y `api` no se encontraría.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Antes de importar la API: api.valoraciones fija la ruta de su base al importarse, y este
# script escribe votos de prueba. Con esto nunca toca la base de verdad.
_BASE_DE_PRUEBA = Path(tempfile.mkdtemp(prefix="nexplay-verificar-nia-")) / "valoraciones.db"
os.environ["NEXPLAY_VALORACIONES_DB"] = str(_BASE_DE_PRUEBA)

from api import catalogo, nia, valoraciones  # noqa: E402

# Las dos preguntas de la revisión, más una de motivos para ver que no se cruzan.
_PREGUNTAS = [
    "¿Por qué quedó en riesgo medio?",
    "¿El precio influye?",
    "¿Qué motivos aparecen en las reseñas?",
]

# Lo que Nia decía cuando explicaba la banda con las reseñas.
_PROHIBIDO_AL_EXPLICAR_LA_BANDA = (
    "reseñas negativas",
    "resenas negativas",
    "por la señal observada",
    "por la senal observada",
)

# Vocabulario del proyecto: nunca, en ninguna respuesta.
_PROHIBIDO_SIEMPRE = ("abandono", "insatisfacción general", "vale la pena", "te recomiendo")


_FACTORES_TS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "app" / "dominio" / "factores.ts"


def _mismas_frases_que_la_ficha() -> list[str]:
    """Las frases de _LECTURA_FACTORES tienen que estar tal cual en COMO_SE_LEE.

    Viven en dos idiomas porque la ficha las pinta y Nia las dice; si una se cambia sola,
    Nia contradice a la ficha sin que nada falle."""
    if not _FACTORES_TS.exists():
        return [f"no se encontró {_FACTORES_TS}"]
    ts = _FACTORES_TS.read_text(encoding="utf-8")
    faltan = [
        f"{etiqueta}: {frase!r} no está en dominio/factores.ts"
        for etiqueta, frases in nia._LECTURA_FACTORES.items()
        for frase in frases
        if frase not in ts
    ]
    if not faltan:
        print(f"frases:   las {sum(len(f) for f in nia._LECTURA_FACTORES.values())} lecturas son las mismas que en la ficha")
    return faltan


def _uno_por_banda() -> list:
    """Un juego de cada banda y, si existe, uno sin nota de Metacritic."""
    juegos = catalogo.buscar()
    elegidos = []
    for banda in ("bajo", "medio", "alto"):
        elegido = next((j for j in juegos if j.banda_riesgo.value == banda), None)
        if elegido:
            elegidos.append(elegido)
    sin_nota = next((j for j in juegos if j.metacritic is None), None)
    if sin_nota and sin_nota not in elegidos:
        elegidos.append(sin_nota)
    return elegidos


def _revisar_contexto(juego) -> list[str]:
    problemas = []
    datos = nia.contexto(juego.appid)
    texto = nia._contexto_para_prompt(datos)

    if "Qué mueve esta estimación" not in texto:
        problemas.append(f"{juego.nombre}: el contexto no lleva las variables del modelo")
    if not datos["factores"]:
        problemas.append(f"{juego.nombre}: el contexto no trae ningún factor")
    for factor in datos["factores"]:
        if factor["lectura"] not in texto:
            problemas.append(f"{juego.nombre}: el factor {factor['etiqueta']!r} no sale con la frase de la ficha")

    # Las frases tienen que ser las de la ficha (dominio/factores.ts, COMO_SE_LEE), no una
    # traducción libre de la etiqueta nominal de la API.
    for factor in datos["factores"]:
        if factor["etiqueta"] in nia._LECTURA_FACTORES:
            esperadas = nia._LECTURA_FACTORES[factor["etiqueta"]]
            if factor["lectura"] not in esperadas:
                problemas.append(f"{juego.nombre}: {factor['etiqueta']!r} no usa la frase de la ficha")

    # Factores imputados: si el dato no está, el factor no se cita.
    etiquetas = [f["etiqueta"] for f in datos["factores"]]
    if juego.metacritic is None and "nota de Metacritic" in etiquetas:
        problemas.append(f"{juego.nombre}: sin nota de Metacritic, el factor de la nota no debería citarse")
    if juego.precio_final is None and not juego.es_gratis and "precio del juego" in etiquetas:
        problemas.append(f"{juego.nombre}: sin precio conocido, el factor del precio no debería citarse")

    # El promedio de la nota, con el mismo decimal que la ficha.
    promedio = nia._referencias_del_catalogo()["metacritic_promedio"]
    if f"Metacritic promedio {promedio}" not in texto:
        problemas.append(f"{juego.nombre}: el contexto no cita el promedio de Metacritic del catálogo")
    if isinstance(promedio, float) and promedio != round(promedio, 1):
        problemas.append(f"el promedio de Metacritic no viene con un decimal ({promedio})")

    # El n de los porcentajes.
    if datos["motivos"] and "clasificada" not in texto:
        problemas.append(f"{juego.nombre}: los motivos no dicen sobre cuántas reseñas clasificadas van")

    print(f"contexto: {juego.nombre} (banda {juego.banda_riesgo.value}) → {len(datos['factores'])} factores")
    for factor in datos["factores"]:
        print(f"          - {factor['lectura']} → {factor['efecto']} el riesgo estimado")
    return problemas


def _revisar_respuestas(juego) -> list[str]:
    problemas = []
    datos = nia.contexto(juego.appid)
    for pregunta in _PREGUNTAS:
        respuesta = nia._demostracion(datos, pregunta)
        print(f"reglas:   {juego.nombre} · {pregunta}\n          {respuesta}")

        bajo = respuesta.lower()
        for prohibido in _PROHIBIDO_SIEMPRE:
            if prohibido in bajo:
                problemas.append(f"{juego.nombre}: la respuesta dice {prohibido!r}")
        if "riesgo" in pregunta.lower() or "por qué" in pregunta.lower():
            if "la pone el modelo con datos del juego" not in respuesta:
                problemas.append(f"{juego.nombre}: al explicar la banda no dice que la pone el modelo")
            if "Las reseñas explican los motivos, no la banda" not in respuesta:
                problemas.append(f"{juego.nombre}: al explicar la banda no descarta que salga de las reseñas")
            for prohibido in _PROHIBIDO_AL_EXPLICAR_LA_BANDA:
                if prohibido in bajo:
                    problemas.append(f"{juego.nombre}: explica la banda con las reseñas ({prohibido!r})")
        if pregunta == "¿El precio influye?":
            esperado = nia._factor_de_precio(datos)
            if esperado and esperado not in respuesta:
                problemas.append(f"{juego.nombre}: la respuesta del precio no distingue la variable del modelo")
        if datos["motivos"] and "%" in respuesta and "clasificada" not in respuesta:
            problemas.append(f"{juego.nombre}: cita un porcentaje sin decir sobre cuántas clasificadas")
    return problemas


def _preguntar_de_verdad(juego) -> list[str]:
    """Las dos preguntas al modelo configurado. Consume cuota: solo con --openai."""
    from api.schemas import MensajeChat

    problemas = []
    for pregunta in _PREGUNTAS[:2]:
        salida = nia.responder(juego.appid, [MensajeChat(rol="usuario", contenido=pregunta)], None)
        print(f"{salida['modo']}: {juego.nombre} · {pregunta}\n          {salida['respuesta']}")
        if salida["modo"] != "openai":
            problemas.append(f"la pregunta {pregunta!r} no llegó al modelo (modo {salida['modo']})")
    return problemas


def _revisar_votos() -> list[str]:
    """El almacén de los votos, contra la base temporal que se fijó al importar."""
    temporal = _BASE_DE_PRUEBA
    if valoraciones._DB_PATH != temporal:
        return [f"la prueba escribiría en {valoraciones._DB_PATH} en vez de la base temporal"]

    problemas = []
    usuario, otro = "pruebalocal01", "pruebalocal02"
    valoraciones.registrar_respuesta_nia("r1", usuario, 1145360, "¿por qué?", "porque sí", "demostracion", None, "reglas")

    voto = valoraciones.guardar_voto_nia("r1", usuario, -1, "muy larga")
    if (voto["voto"], voto["motivo"]) != (-1, "muy larga"):
        problemas.append(f"el 👎 con motivo no se guardó como se mandó ({voto})")

    # El motivo acompaña al 👎: con 👍 no hay nada que explicar.
    voto = valoraciones.guardar_voto_nia("r1", usuario, 1, "muy larga")
    if (voto["voto"], voto["motivo"]) != (1, None):
        problemas.append(f"cambiar a 👍 no limpia el motivo ({voto})")

    # Un motivo que no está en la lista no entra.
    voto = valoraciones.guardar_voto_nia("r1", usuario, -1, "porque no me gusta su tono")
    if voto["motivo"] is not None:
        problemas.append(f"se guardó un motivo fuera de la lista ({voto})")

    # Un voto por persona y respuesta: el de otra no pisa el propio.
    valoraciones.guardar_voto_nia("r1", otro, 1)
    if valoraciones.voto_nia("r1", usuario)["voto"] != -1:
        problemas.append("el voto de otra persona pisó el propio")

    if valoraciones.borrar_voto_nia("r1", usuario)["voto"] is not None:
        problemas.append("quitar el voto no lo quita")

    try:
        valoraciones.guardar_voto_nia("no-existe", usuario, 1)
        problemas.append("votar una respuesta inexistente no falla")
    except valoraciones.RespuestaNiaInexistente:
        pass

    # Retención: lo vencido se va con sus votos, lo reciente se queda.
    vieja = (datetime.now(timezone.utc) - timedelta(days=valoraciones.DIAS_DE_RETENCION_NIA + 1)).isoformat(timespec="seconds")
    valoraciones.registrar_respuesta_nia("r2", usuario, None, "vieja", "vieja", "demostracion", None, "reglas")
    valoraciones.guardar_voto_nia("r2", usuario, 1)
    con = sqlite3.connect(temporal)
    con.execute("UPDATE respuestas_nia SET creado = ? WHERE id = 'r2'", (vieja,))
    con.commit()
    con.close()

    valoraciones.registrar_respuesta_nia("r3", usuario, None, "nueva", "nueva", "demostracion", None, "reglas")
    con = sqlite3.connect(temporal)
    quedan = {fila[0] for fila in con.execute("SELECT id FROM respuestas_nia")}
    votos = con.execute("SELECT COUNT(*) FROM valoraciones_nia WHERE id_respuesta = 'r2'").fetchone()[0]
    con.close()
    if "r2" in quedan:
        problemas.append(f"la retención de {valoraciones.DIAS_DE_RETENCION_NIA} días no borró la respuesta vencida")
    if votos:
        problemas.append("la retención dejó votos huérfanos de una respuesta borrada")
    if {"r1", "r3"} - quedan:
        problemas.append(f"la retención se llevó respuestas recientes ({sorted(quedan)})")

    if not problemas:
        print(
            f"votos:    un voto por persona y respuesta, el motivo solo con 👎, y la retención de"
            f" {valoraciones.DIAS_DE_RETENCION_NIA} días borra lo vencido con sus votos"
        )
    return problemas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openai", action="store_true", help="manda las dos preguntas al modelo configurado")
    argumentos = parser.parse_args()

    juegos = _uno_por_banda()
    problemas = _mismas_frases_que_la_ficha()
    problemas += _revisar_votos()
    for juego in juegos:
        problemas += _revisar_contexto(juego)
        problemas += _revisar_respuestas(juego)
    if argumentos.openai:
        problemas += _preguntar_de_verdad(juegos[0])

    print()
    if problemas:
        for problema in problemas:
            print(f"PROBLEMA: {problema}")
        return 1
    print(f"sin problemas: {len(juegos)} juegos × {len(_PREGUNTAS)} preguntas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
