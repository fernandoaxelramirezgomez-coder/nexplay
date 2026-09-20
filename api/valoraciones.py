"""Valoraciones de la segunda opinión y su hilo de comentarios.

Viven en su propia base (datos/valoraciones.db, movible con NEXPLAY_VALORACIONES_DB),
separada de nexplay.db: es contenido de quien usa la app, no datos del proyecto, y
preparar_entorno.py no la reconstruye ni la pisa.

- El voto útil / no útil es uno por persona y juego, y se puede cambiar.
- Los comentarios son un hilo público: solo se insertan, nunca se editan ni se pisan, y
  se devuelven sin identidad (texto y fecha). El id de usuario se guarda para el límite
  de frecuencia y para poder ubicar una fila desde moderar_comentarios.py.

El id de usuario es anónimo y lo genera el navegador: identifica, no autentica.
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
                   creado      TEXT    NOT NULL,
                   actualizado TEXT    NOT NULL,
                   PRIMARY KEY (usuario, appid)
               )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_valoraciones_appid ON valoraciones (appid)")
        con.execute(
            """CREATE TABLE IF NOT EXISTS comentarios (
                   id      INTEGER PRIMARY KEY AUTOINCREMENT,
                   appid   INTEGER NOT NULL,
                   usuario TEXT    NOT NULL,
                   texto   TEXT    NOT NULL,
                   creado  TEXT    NOT NULL
               )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_appid ON comentarios (appid, id)")
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
                "SELECT util, actualizado FROM valoraciones WHERE appid = ? AND usuario = ?",
                (appid, usuario),
            ).fetchone()
            if fila is not None:
                mia = {"util": bool(fila[0]), "actualizado": fila[1]}
    finally:
        con.close()
    return {"appid": appid, "utiles": utiles, "no_utiles": no_utiles, "total": utiles + no_utiles, "mia": mia}


def guardar(appid: int, usuario: str, util: bool) -> dict:
    """Crea o actualiza el voto de ese usuario para ese juego."""
    ahora = _ahora()
    con = _conectar()
    try:
        con.execute(
            """INSERT INTO valoraciones (usuario, appid, util, creado, actualizado)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (usuario, appid) DO UPDATE SET
                   util = excluded.util,
                   actualizado = excluded.actualizado""",
            (usuario, appid, int(util), ahora, ahora),
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


MAXIMO_COMENTARIOS = 100


def comentarios(appid: int, limite: int = MAXIMO_COMENTARIOS) -> list[dict]:
    """Hilo público: los últimos `limite`, del más viejo al más nuevo y sin identidad."""
    con = _conectar()
    try:
        filas = con.execute(
            "SELECT texto, creado FROM comentarios WHERE appid = ? ORDER BY id DESC LIMIT ?",
            (appid, limite),
        ).fetchall()
    finally:
        con.close()
    return [{"texto": texto, "creado": creado} for texto, creado in reversed(filas)]


def agregar_comentario(appid: int, usuario: str, texto: str) -> list[dict]:
    """Solo inserta: los comentarios no se editan ni se pisan."""
    con = _conectar()
    try:
        con.execute(
            "INSERT INTO comentarios (appid, usuario, texto, creado) VALUES (?, ?, ?, ?)",
            (appid, usuario, texto, _ahora()),
        )
        con.commit()
    finally:
        con.close()
    return comentarios(appid)


def comentarios_para_moderar(appid: int | None = None) -> list[tuple]:
    """Con identidad y id: solo para moderar_comentarios.py, nunca para la API."""
    con = _conectar()
    try:
        if appid is None:
            return con.execute(
                "SELECT id, appid, usuario, texto, creado FROM comentarios ORDER BY id"
            ).fetchall()
        return con.execute(
            "SELECT id, appid, usuario, texto, creado FROM comentarios WHERE appid = ? ORDER BY id",
            (appid,),
        ).fetchall()
    finally:
        con.close()


def borrar_comentario(id_comentario: int) -> bool:
    con = _conectar()
    try:
        borradas = con.execute("DELETE FROM comentarios WHERE id = ?", (id_comentario,)).rowcount
        con.commit()
    finally:
        con.close()
    return borradas > 0
