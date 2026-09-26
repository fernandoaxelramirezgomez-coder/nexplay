"""Comprueba lo que Nia dice y cómo se guardan los votos a sus respuestas.

El riesgo lo pone el modelo con datos del juego; las reseñas solo dicen de qué se queja la
gente. Nia confundía las dos cosas porque su contexto no traía los factores, así que este
script revisa lo que se le manda (api/nia.py, _contexto_para_prompt) y lo que responde el
modo demostración, que es el mismo camino sin gastar una llamada.

También revisa el almacén de los votos (fase 5b) contra una base temporal, sin tocar la
de verdad: registrar una respuesta, votarla, cambiar el voto, quitarlo, votar un id que no
existe y comprobar que la retención borra lo vencido y respeta lo reciente.

Uso:
  python verificar_nia.py            revisa contexto, respuestas por reglas y votos; sale 1 si algo falla
  python verificar_nia.py --openai   manda las quince preguntas del recorrido al modelo
                                     configurado e imprime lo que responde (consume cuota)
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

from api import catalogo, nia, nia_herramientas, valoraciones  # noqa: E402
from api.schemas import MensajeChat  # noqa: E402

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
_PROHIBIDO_SIEMPRE = ("abandono", "insatisfacción general", "vale la pena", "te recomiendo", "banda")


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
            if "lo pone el modelo con datos del juego" not in respuesta:
                problemas.append(f"{juego.nombre}: al explicar el riesgo no dice que lo pone el modelo")
            if "Las reseñas explican los motivos, no el riesgo" not in respuesta:
                problemas.append(f"{juego.nombre}: al explicar el riesgo no descarta que salga de las reseñas")
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


# Las quince del recorrido de catálogo (fase 5a): filtros, un juego que no está, las dos
# formas de pedir que elija por uno, metodología, comparar, seguimiento y fuera de tema.
# El primer valor es el juego del que se habla; None es modo catálogo.
_RECORRIDO = [
    (None, "¿Qué juegos de acción tienen riesgo bajo?"),
    (None, "¿Hay algo gratis en el catálogo?"),
    (None, "Juegos de estrategia de menos de 300 pesos"),
    (None, "¿Tienen Elden Ring?"),
    (None, "¿Y Super Mario Odyssey?"),
    (None, "¿Cuál me compro?"),
    (None, "¿Cuál es el mejor juego del catálogo?"),
    (None, "¿De dónde salen estos datos?"),
    (None, "¿Cómo calculan el riesgo?"),
    (None, "Compara Hades y Hollow Knight"),
    (None, "¿Y el más barato de esos dos?"),
    (None, "¿Qué opina la gente en los comentarios?"),
    (None, "¿Quién ganó el mundial de 2022?"),
    (1145360, "¿Por qué quedó en esa banda?"),
    (1145360, "¿Cuánto cuesta?"),
]

# Nada de esto puede salir de Nia, conteste el modelo o las reglas.
# "banda" también: desde la revisión del usuario final el nivel se llama riesgo de
# arrepentimiento, y "banda" era la palabra que nadie entendía.
_NUNCA = ("abandono", "te lo recomiendo", "vale la pena", "cómpralo", "no lo compres", "deberías comprar", "banda")


def _revisar_recorrido(con_openai: bool) -> list[str]:
    """Las quince preguntas, en el modo que esté configurado.

    En demostración se comprueban las reglas que valen siempre; las semánticas —que diga
    que un juego no está, que no elija por nadie— solo se pueden afirmar con el modelo, y
    ahí además se imprimen para leerlas."""
    problemas = []
    del_catalogo = {j.appid for j in catalogo.buscar()}
    nombres = {j.nombre for j in catalogo.buscar()}

    for appid, pregunta in _RECORRIDO:
        salida = nia.responder(appid, [MensajeChat(rol="usuario", contenido=pregunta)], "verificador01")
        texto = salida["respuesta"]
        bajo = texto.lower()
        donde = f"[{'catálogo' if appid is None else appid}] {pregunta!r}"

        if not texto.strip():
            problemas.append(f"{donde}: respuesta vacía")
        for prohibido in _NUNCA:
            if prohibido in bajo:
                problemas.append(f"{donde}: dice {prohibido!r}")
        fuera = [a for a in salida["juegos"] if a not in del_catalogo]
        if fuera:
            problemas.append(f"{donde}: devuelve appids que no están en el catálogo ({fuera})")

        if con_openai:
            print(f"{salida['modo']}: {donde}\n          {texto}")
            if salida["pasos"]:
                print(f"          pasos: {' · '.join(salida['pasos'])}")
            if salida["modo"] != "openai":
                problemas.append(f"{donde}: no llegó al modelo (modo {salida['modo']})")
            if pregunta == "¿Y Super Mario Odyssey?" and "no está" not in bajo:
                problemas.append(f"{donde}: no dice que el juego no está en el catálogo")
            # Un juego nombrado sin haberlo consultado no se puede pintar ni citar.
            nombrados = {n for n in nombres if n.lower() in bajo}
            if nombrados and not salida["juegos"]:
                problemas.append(f"{donde}: nombra juegos sin haberlos consultado ({sorted(nombrados)[:3]})")

    if not problemas:
        print(f"catálogo: las {len(_RECORRIDO)} preguntas del recorrido pasan"
              f" {'con el modelo' if con_openai else 'en demostración'}")
    return problemas


def _revisar_herramientas() -> list[str]:
    """Las herramientas solo devuelven lo que hay, y en un orden que no recomienda."""
    problemas = []
    del_catalogo = {j.appid for j in catalogo.buscar()}

    busqueda = nia_herramientas.buscar_juegos(genero="Acción")
    if any(j["appid"] not in del_catalogo for j in busqueda["juegos"]):
        problemas.append("buscar_juegos devolvió un appid que no está en el catálogo")
    if len(busqueda["juegos"]) > nia_herramientas.MAXIMO_RESULTADOS:
        problemas.append(f"buscar_juegos devolvió más de {nia_herramientas.MAXIMO_RESULTADOS}")
    if busqueda["total"] > len(busqueda["juegos"]) and not busqueda["hay_mas"]:
        problemas.append("buscar_juegos recorta la lista sin decir cuántos faltan")

    # Orden neutro salvo que se pida otro: ordenar por precio sin que nadie lo pidiera es
    # recomendar con otro nombre.
    nombres = [j["nombre"] for j in busqueda["juegos"]]
    if nombres != sorted(nombres, key=str.lower):
        problemas.append(f"buscar_juegos no ordena alfabéticamente por omisión ({nombres[:3]})")
    por_precio = nia_herramientas.buscar_juegos(genero="Acción", orden="precio")
    if [j["nombre"] for j in por_precio["juegos"]] == nombres and len(nombres) > 1:
        problemas.append("pedir orden por precio no cambia nada")

    # La misma consulta hecha a mano tiene que dar lo mismo.
    a_mano = catalogo.buscar(genero="Acción")
    if busqueda["total"] != len(a_mano):
        problemas.append(f"buscar_juegos cuenta {busqueda['total']} y el catálogo {len(a_mano)}")

    if not nia_herramientas.resolver_juego("Hollow Knight")["encontrado"]:
        problemas.append("resolver_juego no encuentra un juego que sí está")
    if nia_herramientas.resolver_juego("Super Mario Odyssey")["encontrado"]:
        problemas.append("resolver_juego encuentra un juego que no está en el catálogo")
    if nia_herramientas.ficha_juego(999999)["encontrado"]:
        problemas.append("ficha_juego responde por un appid que no existe")

    if not problemas:
        print(f"herramientas: {len(nia_herramientas.ESQUEMAS)} declaradas, orden alfabético por"
              " omisión y sin appids inventados")
    return problemas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openai", action="store_true", help="manda el recorrido al modelo configurado")
    argumentos = parser.parse_args()

    juegos = _uno_por_banda()
    problemas = _mismas_frases_que_la_ficha()
    problemas += _revisar_votos()
    problemas += _revisar_herramientas()
    problemas += _revisar_recorrido(argumentos.openai)
    for juego in juegos:
        problemas += _revisar_contexto(juego)
        problemas += _revisar_respuestas(juego)
    print()
    if problemas:
        for problema in problemas:
            print(f"PROBLEMA: {problema}")
        return 1
    print(f"sin problemas: {len(juegos)} juegos × {len(_PREGUNTAS)} preguntas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
