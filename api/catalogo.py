"""Búsqueda de juegos. El catálogo se carga una sola vez, al importar este
módulo (o sea, al arrancar el proceso), desde datos/nexplay.db —nunca en
cada request.

Steam es la única fuente: no hay manera de afirmar disponibilidad en
PlayStation/Xbox/Nintendo desde esta ingesta, así que todo el catálogo se
declara solo en PC.

portada_url y tienda_url son campos derivados del appid (no hay columna de
imagen en 'juegos'): la portada de Steam siempre vive en
cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg y la ficha en
store.steampowered.com/app/{appid}, verificado contra appids reales del
catálogo (fase 0).

banda_riesgo usa un perfil neutro (ver _PERFIL_NEUTRO): en el catálogo
visual no hay un perfil declarado todavía, así que no hay riesgo
personalizado que mostrar. scoring.predecir() solo lee compras_al_anio del
perfil -el resto de PerfilJugador no mueve el score-, y el lado del
jugador aporta ~2% del PR-AUC del modelo (dentro del ruido entre folds,
ver notebook/nexplay.ipynb sección 6): la banda que sale de este perfil
neutro se parece mucho a la que saldría de cualquier perfil razonable."""

import logging
import re
import sqlite3
from pathlib import Path

from . import scoring
from .schemas import JuegoCatalogo, NivelFriccion, NivelRiesgo, PerfilJugador, Plataforma

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent / "datos" / "nexplay.db"

_PERFIL_NEUTRO = PerfilJugador(
    compras_al_anio=5,  # a medio camino entre 0 y el umbral de "veterano" (10)
    horas_por_semana=8,
    tolerancia_friccion=NivelFriccion.MEDIA,
    tags_preferidos=[],
    tags_rechazados=[],
    plataforma=Plataforma.PC,
    segmento="novato",
    disponibilidad="media",
)


def _url_portada(appid: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"


def _url_tienda(appid: int) -> str:
    return f"https://store.steampowered.com/app/{appid}"


def _generos_de(campo: str | None) -> list[str]:
    return [g for g in (campo or "").split("|") if g]


# La ingesta pide las descripciones con l=spanish, pero Steam cae al inglés cuando el
# juego no la tiene traducida: son 9 de los 83. Se cuentan palabras muy comunes de cada
# idioma y gana la mayoría. Basta comparar, no detectar: con una sola palabra inglesa
# bastaba para tirar ocho descripciones que sí estaban en español pero citaban un título
# ("The Elder Scrolls V: Skyrim", "Skull and Bones", "The Last of Us").
_PALABRAS_INGLESAS = re.compile(r"\b(the|and|your|you|with|of|in|is|as|to|from)\b", re.IGNORECASE)
_PALABRAS_ESPANOLAS = re.compile(r"\b(de|del|la|el|los|las|un|una|que|con|para|en|por)\b", re.IGNORECASE)


def _descripcion_en_espanol(texto: str | None) -> str | None:
    """La descripción de Steam, o None si Steam la devolvió en inglés."""
    limpio = (texto or "").strip()
    if not limpio:
        return None
    if len(_PALABRAS_INGLESAS.findall(limpio)) > len(_PALABRAS_ESPANOLAS.findall(limpio)):
        return None
    return limpio


def _cargar_catalogo() -> list[JuegoCatalogo]:
    if not _DB_PATH.exists():
        logger.warning("no existe %s; el catálogo queda vacío", _DB_PATH)
        return []

    con = sqlite3.connect(_DB_PATH)
    try:
        filas = con.execute(
            "SELECT appid, nombre, generos, metacritic, es_gratis, precio_final, moneda, fecha_lanzamiento, "
            "descripcion_corta FROM juegos WHERE nombre IS NOT NULL ORDER BY nombre"
        ).fetchall()
    finally:
        con.close()

    catalogo = []
    sin_espanol = 0
    for (
        appid,
        nombre,
        generos,
        metacritic,
        es_gratis,
        precio_final,
        moneda,
        fecha_lanzamiento,
        descripcion_corta,
    ) in filas:
        descripcion = _descripcion_en_espanol(descripcion_corta)
        sin_espanol += descripcion is None
        prediccion = scoring.predecir(_PERFIL_NEUTRO, appid)
        catalogo.append(
            JuegoCatalogo(
                appid=appid,
                nombre=nombre,
                plataformas=[Plataforma.PC],
                generos=_generos_de(generos),
                metacritic=metacritic,
                es_gratis=bool(es_gratis),
                # precio_final viene en centavos (misma convencion que la API de Steam).
                precio_final=precio_final / 100 if precio_final is not None else None,
                moneda=moneda,
                fecha_lanzamiento=fecha_lanzamiento,
                descripcion=descripcion,
                portada_url=_url_portada(appid),
                tienda_url=_url_tienda(appid),
                banda_riesgo=prediccion.nivel,
                riesgo=prediccion.riesgo,
            )
        )
    if sin_espanol:
        logger.info("descripciones sin versión en español: %s de %s", sin_espanol, len(catalogo))
    return catalogo


_CATALOGO = _cargar_catalogo()
logger.info("catálogo cargado: %s juegos", len(_CATALOGO))


def buscar(q: str = "", genero: str = "", riesgo: NivelRiesgo | None = None) -> list[JuegoCatalogo]:
    resultado = _CATALOGO
    if q.strip():
        q_normalizado = q.strip().lower()
        resultado = [j for j in resultado if q_normalizado in j.nombre.lower()]
    if genero.strip():
        resultado = [j for j in resultado if genero.strip() in j.generos]
    if riesgo is not None:
        resultado = [j for j in resultado if j.banda_riesgo == riesgo]
    return resultado


def obtener(appid: int) -> JuegoCatalogo | None:
    return next((j for j in _CATALOGO if j.appid == appid), None)
