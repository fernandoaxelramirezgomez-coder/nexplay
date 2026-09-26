"""Las herramientas con las que Nia consulta el catálogo.

El modelo no recibe los 123 juegos en el prompt: no caben con sus motivos, y meterlos
invita a inventar. Recibe estas funciones, que leen lo mismo que sirve la API y nada más.

Tres reglas que valen para todas:

- Solo leen, y solo de `api.catalogo`, `api.scoring` y `api.panorama`. Nunca de
  `datos/valoraciones.db`: los comentarios públicos y las valoraciones de la gente no son
  datos del catálogo y no entran en lo que Nia lee.
- Devuelven appids reales. Lo que no salga de aquí no puede acabar en una tarjeta: quien
  llama valida la respuesta contra estos appids (ver `nia.py`).
- El orden por omisión es alfabético. Ordenar por precio o por nota es una recomendación
  encubierta si nadie la pidió, así que hay que pedirla.
"""

import logging
from urllib.parse import urlencode

from . import catalogo, nia, panorama
from .schemas import JuegoCatalogo, NivelRiesgo

logger = logging.getLogger(__name__)

# Cuántos juegos devuelve una búsqueda. Con más, la respuesta se vuelve un catálogo
# recitado; el resto se resume con "hay N más" y un enlace a Explorar.
MAXIMO_RESULTADOS = 8

_ORDENES = ("nombre", "precio", "nota", "riesgo")


def _resumen_de_juego(juego: JuegoCatalogo) -> dict:
    """Lo justo para nombrarlo y compararlo. Sin descripción ni URLs: el frontend arma la
    tarjeta con el appid desde su propio catálogo."""
    return {
        "appid": juego.appid,
        "nombre": juego.nombre,
        "riesgo": juego.banda_riesgo.value,
        "precio": "gratis" if juego.es_gratis else juego.precio_final,
        "metacritic": juego.metacritic,
        "generos": juego.generos,
    }


def _clave_de_orden(orden: str):
    if orden == "precio":
        return lambda j: (0 if j.es_gratis else 1, j.precio_final if j.precio_final is not None else float("inf"))
    if orden == "nota":
        return lambda j: -(j.metacritic if j.metacritic is not None else -1)
    if orden == "riesgo":
        return lambda j: ({"bajo": 0, "medio": 1, "alto": 2}[j.banda_riesgo.value], j.nombre.lower())
    return lambda j: j.nombre.lower()


def buscar_juegos(
    texto: str = "",
    genero: str = "",
    riesgo: str = "",
    precio_max: float | None = None,
    solo_gratis: bool = False,
    con_nota: bool | None = None,
    orden: str = "nombre",
) -> dict:
    """Juegos del catálogo que cumplen los filtros, hasta MAXIMO_RESULTADOS."""
    nivel = NivelRiesgo(riesgo) if riesgo in ("bajo", "medio", "alto") else None
    juegos = catalogo.buscar(q=texto, genero=genero, riesgo=nivel)
    if solo_gratis:
        juegos = [j for j in juegos if j.es_gratis]
    if precio_max is not None:
        juegos = [j for j in juegos if j.es_gratis or (j.precio_final is not None and j.precio_final <= precio_max)]
    if con_nota is not None:
        juegos = [j for j in juegos if (j.metacritic is not None) == con_nota]

    if orden not in _ORDENES:
        orden = "nombre"
    juegos = sorted(juegos, key=_clave_de_orden(orden))
    mostrados = juegos[:MAXIMO_RESULTADOS]
    return {
        "juegos": [_resumen_de_juego(j) for j in mostrados],
        "total": len(juegos),
        "hay_mas": max(0, len(juegos) - len(mostrados)),
        "orden": orden,
        # La ruta que ve la misma lista completa, para que la respuesta pueda ofrecerla.
        "ver_todos": _enlace_a_explorar(texto, genero, riesgo),
    }


def _enlace_a_explorar(texto: str, genero: str, riesgo: str) -> str:
    filtros = {}
    if texto.strip():
        filtros["q"] = texto.strip()
    if genero.strip():
        filtros["genero"] = genero.strip()
    if riesgo in ("bajo", "medio", "alto"):
        filtros["riesgo"] = riesgo
    return "/explorar" + ("?" + urlencode(filtros) if filtros else "")


def resolver_juego(nombre: str) -> dict:
    """De un nombre escrito por alguien al appid del catálogo, o a nada.

    Existe para que "compara Hades y Hollow Knight" no obligue a adivinar appids. Reusa el
    reconocedor de nombres que ya distingue "no está en el catálogo" de "está, pero no es
    el que tienes abierto"."""
    texto = (nombre or "").strip()
    if not texto:
        return {"encontrado": False, "nombre_buscado": nombre}

    exacto = next((j for j in catalogo.buscar() if j.nombre.lower() == texto.lower()), None)
    if exacto is None:
        # appid_abierto=0 para que no descarte ninguno: aquí no hay juego abierto.
        nombres = nia.juegos_del_catalogo_mencionados(texto, 0)
        if nombres:
            exacto = next((j for j in catalogo.buscar() if j.nombre == nombres[0]), None)
    if exacto is None:
        parciales = catalogo.buscar(q=texto)
        exacto = parciales[0] if len(parciales) == 1 else None

    if exacto is None:
        return {"encontrado": False, "nombre_buscado": texto}
    return {"encontrado": True, **_resumen_de_juego(exacto)}


def ficha_juego(appid: int) -> dict:
    """Lo mismo que Nia ve de un juego abierto: riesgo, factores del modelo, motivos con su
    n, crítica y precio."""
    try:
        datos = nia.contexto(int(appid))
    except ValueError:
        return {"encontrado": False, "appid": appid}
    return {
        "encontrado": True,
        "appid": int(appid),
        "nombre": datos["nombre"],
        "riesgo": datos["banda"],
        "factores": [f"{f['lectura']} → {f['efecto']} el riesgo estimado" for f in datos["factores"]],
        "generos": datos["generos"],
        "metacritic": datos["metacritic"],
        "precio": "gratis" if datos["es_gratis"] else datos["precio"],
        "lanzamiento": datos["lanzamiento"],
        "resenas_con_senal": datos["n_casos"],
        "resenas_clasificadas": datos["clasificadas"],
        "motivos": [f"{m.motivo} {m.frecuencia:.0%}" for m in datos["motivos"]],
    }


def panorama_del_catalogo() -> dict:
    """Las cifras de la muestra: de dónde salen los datos y qué tan grandes son."""
    p = panorama.resumen()
    return {
        "juegos": p.juegos,
        "resenas_descargadas": p.resenas_descargadas,
        "resenas_en_steam": p.resenas_en_steam,
        "cobertura": f"{p.cobertura:.1%}",
        "desde": p.ventana.desde,
        "hasta": p.ventana.hasta,
        "resenas_con_senal": p.casos_senal,
        "prevalencia": f"{p.prevalencia:.2%}",
        "motivos_del_catalogo": [f"{m.motivo} {m.frecuencia:.0%}" for m in p.motivos[:5]],
        "perfiles_privados": f"{p.muestra.perfiles_privados:.0%}",
    }


# Texto fijo: la metodología no la redacta el modelo. Si cambia, cambia aquí y en
# /como-funciona, que es donde está escrita para la gente.
_METODOLOGIA = """NexPlay estima el riesgo de arrepentimiento temprano antes de comprar.
Es una señal proxy: se marca Y=1 una reseña de Steam cuyo autor jugó menos de 120 minutos
—la ventana de reembolso— y calificó negativo. Steam nunca pregunta si alguien se
arrepintió, así que es un indicio, no un hecho.
El modelo es de título: solo usa datos del juego (gratuidad, precio, descuento, nota de
Metacritic y si tiene cobertura de crítica). El perfil declarado no mueve el riesgo; sirve
para ver qué tanto encaja un juego con quien lo declaró.
Se entrenó con el corte data-v1 (83 juegos, 123,972 reseñas), validado con GroupKFold
agrupando por appid para que generalice a juegos que no vio, y optimizado a PR-AUC porque
la clase está desbalanceada. En los 40 títulos que nunca vio sacó PR-AUC 0.0356 contra
0.0234 de un clasificador trivial: hay señal, y es modesta.
El riesgo de arrepentimiento (bajo, medio, alto) reparte el catálogo en tres niveles:
compara un juego con los demás y no es una probabilidad. Es del juego, no de quien pregunta."""


def metodologia() -> dict:
    return {"texto": _METODOLOGIA}


# Lo que se le describe al modelo. Los nombres y las descripciones son parte del contrato:
# si dicen de más, el modelo llama a la herramienta equivocada.
ESQUEMAS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_juegos",
            "description": (
                "Busca juegos del catálogo de NexPlay por nombre, género, riesgo de arrepentimiento y precio."
                " Devuelve como máximo 8, en orden alfabético salvo que se pida otro."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string", "description": "Parte del nombre"},
                    "genero": {"type": "string", "description": "Género de Steam exacto, por ejemplo 'Acción'"},
                    "riesgo": {"type": "string", "enum": ["bajo", "medio", "alto"], "description": "Riesgo de arrepentimiento"},
                    "precio_max": {"type": "number", "description": "Precio máximo en MXN"},
                    "solo_gratis": {"type": "boolean"},
                    "con_nota": {"type": "boolean", "description": "true: solo con nota de Metacritic; false: solo sin ella"},
                    "orden": {
                        "type": "string",
                        "enum": list(_ORDENES),
                        "description": "Solo si quien pregunta pidió un orden; por omisión, alfabético",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolver_juego",
            "description": "Del nombre de un juego a su appid en el catálogo. Úsala antes de ficha_juego.",
            "parameters": {
                "type": "object",
                "properties": {"nombre": {"type": "string"}},
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ficha_juego",
            "description": "Los datos de un juego: riesgo de arrepentimiento, factores del modelo, motivos de las reseñas, crítica y precio.",
            "parameters": {
                "type": "object",
                "properties": {"appid": {"type": "integer"}},
                "required": ["appid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "panorama_del_catalogo",
            "description": "Cifras de la muestra de reseñas: cuántas, de cuándo, qué proporción trae señal.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "metodologia",
            "description": "Cómo se define y se entrena la señal de arrepentimiento temprano. Texto fijo.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

_FUNCIONES = {
    "buscar_juegos": buscar_juegos,
    "resolver_juego": resolver_juego,
    "ficha_juego": ficha_juego,
    "panorama_del_catalogo": panorama_del_catalogo,
    "metodologia": metodologia,
}

# Qué decir mientras corre cada una, para que la espera no sea un "escribiendo" mudo.
PASOS = {
    "buscar_juegos": "Buscando en el catálogo…",
    "resolver_juego": "Buscando ese juego…",
    "ficha_juego": "Leyendo la ficha de {nombre}…",
    "panorama_del_catalogo": "Contando las reseñas de la muestra…",
    "metodologia": "Repasando la metodología…",
}


def ejecutar(nombre: str, argumentos: dict) -> dict:
    """Corre una herramienta por su nombre. Un nombre desconocido no revienta: se responde
    que no existe y el modelo sigue con lo que tenga."""
    funcion = _FUNCIONES.get(nombre)
    if funcion is None:
        logger.warning("Nia pidió una herramienta que no existe: %r", nombre)
        return {"error": f"no existe la herramienta {nombre}"}
    try:
        return funcion(**argumentos)
    except TypeError as exc:
        logger.warning("argumentos inválidos para %s: %s", nombre, exc)
        return {"error": f"argumentos inválidos para {nombre}"}


def paso_de(nombre: str, argumentos: dict, salida: dict) -> str:
    """La línea de progreso de una llamada, ya con el nombre del juego si lo hubo."""
    plantilla = PASOS.get(nombre, "Consultando los datos…")
    return plantilla.format(nombre=salida.get("nombre") or argumentos.get("nombre") or "ese juego")


def appids_de(salida: dict) -> set[int]:
    """Los appids que una herramienta devolvió: los únicos que pueden acabar en tarjeta."""
    appids = set()
    if isinstance(salida.get("appid"), int):
        appids.add(salida["appid"])
    for juego in salida.get("juegos", []):
        if isinstance(juego.get("appid"), int):
            appids.add(juego["appid"])
    return appids
