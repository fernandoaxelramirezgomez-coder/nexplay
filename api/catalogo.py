"""Búsqueda de juegos. El catálogo se carga una sola vez, al importar este
módulo (o sea, al arrancar el proceso), desde datos/postplay.db —nunca en
cada request.

Steam es la única fuente: no hay manera de afirmar disponibilidad en
PlayStation/Xbox/Nintendo desde esta ingesta, así que todo el catálogo se
declara solo en PC."""

import logging
import sqlite3
from pathlib import Path

from .schemas import JuegoCatalogo, Plataforma

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent / "datos" / "postplay.db"


def _cargar_catalogo() -> list[JuegoCatalogo]:
    if not _DB_PATH.exists():
        logger.warning("no existe %s; el catálogo queda vacío", _DB_PATH)
        return []

    con = sqlite3.connect(_DB_PATH)
    try:
        filas = con.execute(
            "SELECT appid, nombre FROM juegos WHERE nombre IS NOT NULL ORDER BY nombre"
        ).fetchall()
    finally:
        con.close()

    return [
        JuegoCatalogo(appid=appid, nombre=nombre, plataformas=[Plataforma.PC])
        for appid, nombre in filas
    ]


_CATALOGO = _cargar_catalogo()
logger.info("catálogo cargado: %s juegos", len(_CATALOGO))


def buscar(q: str) -> list[JuegoCatalogo]:
    if not q.strip():
        return _CATALOGO
    q_normalizado = q.strip().lower()
    return [j for j in _CATALOGO if q_normalizado in j.nombre.lower()]


def obtener(appid: int) -> JuegoCatalogo | None:
    return next((j for j in _CATALOGO if j.appid == appid), None)
