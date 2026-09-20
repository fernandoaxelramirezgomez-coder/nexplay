"""Valoraciones de la segunda opinión: útil o no útil, más un comentario privado.

Vive en su propia base (datos/valoraciones.db, movible con NEXPLAY_VALORACIONES_DB),
separada de nexplay.db: es contenido de quien usa la app, no datos del proyecto, y
preparar_entorno.py no la reconstruye ni la pisa.

El id de usuario es anónimo y lo genera el navegador: identifica, no autentica. El
comentario es privado —solo se devuelve a quien lo escribió—, así que de un juego solo
salen los conteos. Para analizarlos está exportar_valoraciones.py, que es local.
"""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH = Path(
    os.environ.get("NEXPLAY_VALORACIONES_DB", Path(__file__).resolve().parent.parent / "datos" / "valoraciones.db")
)


def _conectar() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    # WAL: lecturas y escrituras a la vez sin bloquearse entre sí.
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _crear_esquema() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = _conectar()
    try:
        con.execute(
            """CREATE TABLE IF NOT EXISTS valoraciones (
                   usuario     TEXT    NOT NULL,
                   appid       INTEGER NOT NULL,
                   util        INTEGER NOT NULL,
                   comentario  TEXT,
                   creado      TEXT    NOT NULL,
                   actualizado TEXT    NOT NULL,
                   PRIMARY KEY (usuario, appid)
               )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_valoraciones_appid ON valoraciones (appid)")
        con.commit()
    finally:
        con.close()


_crear_esquema()
logger.info("valoraciones en %s", _DB_PATH)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resumen(appid: int, usuario: str | None = None) -> dict:
    """Conteos del juego y, si se pide, la valoración de ese usuario. Nunca devuelve
    comentarios de terceros."""
    con = _conectar()
    try:
        utiles, no_utiles = con.execute(
            "SELECT COALESCE(SUM(util), 0), COALESCE(SUM(1 - util), 0) FROM valoraciones WHERE appid = ?",
            (appid,),
        ).fetchone()
        mia = None
        if usuario:
            fila = con.execute(
                "SELECT util, comentario, actualizado FROM valoraciones WHERE appid = ? AND usuario = ?",
                (appid, usuario),
            ).fetchone()
            if fila is not None:
                mia = {"util": bool(fila[0]), "comentario": fila[1], "actualizado": fila[2]}
    finally:
        con.close()
    return {"appid": appid, "utiles": utiles, "no_utiles": no_utiles, "total": utiles + no_utiles, "mia": mia}


def guardar(appid: int, usuario: str, util: bool, comentario: str | None) -> dict:
    """Crea o actualiza la valoración de ese usuario para ese juego. Con comentario en
    None se borra solo el comentario y la valoración se conserva."""
    ahora = _ahora()
    con = _conectar()
    try:
        con.execute(
            """INSERT INTO valoraciones (usuario, appid, util, comentario, creado, actualizado)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (usuario, appid) DO UPDATE SET
                   util = excluded.util,
                   comentario = excluded.comentario,
                   actualizado = excluded.actualizado""",
            (usuario, appid, int(util), comentario, ahora, ahora),
        )
        con.commit()
    finally:
        con.close()
    return resumen(appid, usuario)


def borrar(appid: int, usuario: str) -> dict:
    con = _conectar()
    try:
        con.execute("DELETE FROM valoraciones WHERE appid = ? AND usuario = ?", (appid, usuario))
        con.commit()
    finally:
        con.close()
    return resumen(appid, usuario)
