"""Valoraciones de la segunda opinión y su hilo de comentarios.

Viven en su propia base (datos/valoraciones.db, movible con NEXPLAY_VALORACIONES_DB),
separada de nexplay.db: es contenido de quien usa la app, no datos del proyecto, y
preparar_entorno.py no la reconstruye ni la pisa.

- El voto útil / no útil es uno por persona y juego, y se puede cambiar.
- Los comentarios son un hilo público. Se devuelven sin identidad: el id de quien
  escribió nunca sale de este módulo, solo se compara contra quien pregunta para marcar
  cuáles son suyos. Cada quien edita y borra los propios; ese mismo id sirve para el
  límite de frecuencia y para ubicar una fila desde moderar_comentarios.py.
- Las reacciones son un pulgar arriba por persona y comentario: una fila o ninguna.

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
                   id          INTEGER PRIMARY KEY AUTOINCREMENT,
                   appid       INTEGER NOT NULL,
                   usuario     TEXT    NOT NULL,
                   texto       TEXT    NOT NULL,
                   creado      TEXT    NOT NULL,
                   editado     INTEGER NOT NULL DEFAULT 0,
                   actualizado TEXT
               )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_appid ON comentarios (appid, id)")

        # Bases de antes de que el hilo se pudiera editar: se agregan las columnas nuevas
        # en vez de recrear la tabla, porque adentro hay comentarios de gente.
        columnas = {fila[1] for fila in con.execute("PRAGMA table_info(comentarios)")}
        if "editado" not in columnas:
            con.execute("ALTER TABLE comentarios ADD COLUMN editado INTEGER NOT NULL DEFAULT 0")
        if "actualizado" not in columnas:
            con.execute("ALTER TABLE comentarios ADD COLUMN actualizado TEXT")

        con.execute(
            """CREATE TABLE IF NOT EXISTS reacciones_comentario (
                   comentario_id INTEGER NOT NULL,
                   usuario       TEXT    NOT NULL,
                   PRIMARY KEY (comentario_id, usuario)
               )"""
        )
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


class ComentarioInexistente(Exception):
    """No hay comentario con ese id en ese juego."""


class ComentarioAjeno(Exception):
    """El comentario existe, pero lo escribió otra persona."""


def _exigir_duenio(con: sqlite3.Connection, appid: int, id_comentario: int, usuario: str) -> None:
    fila = con.execute(
        "SELECT usuario FROM comentarios WHERE id = ? AND appid = ?", (id_comentario, appid)
    ).fetchone()
    if fila is None:
        raise ComentarioInexistente(id_comentario)
    if fila[0] != usuario:
        raise ComentarioAjeno(id_comentario)


def comentarios(appid: int, usuario: str | None = None, limite: int = MAXIMO_COMENTARIOS) -> list[dict]:
    """Hilo público: los últimos `limite`, del más viejo al más nuevo. El id de quien
    escribió no sale de aquí; solo se compara con `usuario` para marcar `es_mio`."""
    quien = usuario or ""
    con = _conectar()
    try:
        filas = con.execute(
            """SELECT c.id, c.texto, c.creado, c.actualizado, c.editado,
                      (SELECT COUNT(*) FROM reacciones_comentario r WHERE r.comentario_id = c.id),
                      EXISTS (SELECT 1 FROM reacciones_comentario r
                              WHERE r.comentario_id = c.id AND r.usuario = ?),
                      c.usuario = ?
               FROM comentarios c
               WHERE c.appid = ?
               ORDER BY c.id DESC
               LIMIT ?""",
            (quien, quien, appid, limite),
        ).fetchall()
    finally:
        con.close()
    return [
        {
            "id": id_comentario,
            "texto": texto,
            "creado": creado,
            "actualizado": actualizado,
            "editado": bool(editado),
            "reacciones": reacciones,
            "reaccione_mia": bool(reaccione_mia),
            "es_mio": bool(quien) and bool(es_mio),
        }
        for id_comentario, texto, creado, actualizado, editado, reacciones, reaccione_mia, es_mio in reversed(filas)
    ]


def agregar_comentario(appid: int, usuario: str, texto: str) -> list[dict]:
    con = _conectar()
    try:
        con.execute(
            "INSERT INTO comentarios (appid, usuario, texto, creado) VALUES (?, ?, ?, ?)",
            (appid, usuario, texto, _ahora()),
        )
        con.commit()
    finally:
        con.close()
    return comentarios(appid, usuario)


def editar_comentario(appid: int, id_comentario: int, usuario: str, texto: str) -> list[dict]:
    """Solo el dueño edita el suyo. `creado` se conserva —es cuándo apareció en el hilo—
    y la fecha del cambio va en `actualizado`, que es la que se muestra."""
    con = _conectar()
    try:
        _exigir_duenio(con, appid, id_comentario, usuario)
        con.execute(
            "UPDATE comentarios SET texto = ?, editado = 1, actualizado = ? WHERE id = ?",
            (texto, _ahora(), id_comentario),
        )
        con.commit()
    finally:
        con.close()
    return comentarios(appid, usuario)


def borrar_comentario_propio(appid: int, id_comentario: int, usuario: str) -> list[dict]:
    """Se lleva también sus reacciones: sin fila de comentario no hay a qué apuntar."""
    con = _conectar()
    try:
        _exigir_duenio(con, appid, id_comentario, usuario)
        con.execute("DELETE FROM reacciones_comentario WHERE comentario_id = ?", (id_comentario,))
        con.execute("DELETE FROM comentarios WHERE id = ?", (id_comentario,))
        con.commit()
    finally:
        con.close()
    return comentarios(appid, usuario)


def alternar_reaccion(appid: int, id_comentario: int, usuario: str) -> dict:
    """Un pulgar arriba por persona y comentario: si ya estaba, se quita."""
    con = _conectar()
    try:
        existe = con.execute(
            "SELECT 1 FROM comentarios WHERE id = ? AND appid = ?", (id_comentario, appid)
        ).fetchone()
        if existe is None:
            raise ComentarioInexistente(id_comentario)

        quitadas = con.execute(
            "DELETE FROM reacciones_comentario WHERE comentario_id = ? AND usuario = ?",
            (id_comentario, usuario),
        ).rowcount
        if not quitadas:
            con.execute(
                "INSERT INTO reacciones_comentario (comentario_id, usuario) VALUES (?, ?)",
                (id_comentario, usuario),
            )
        total = con.execute(
            "SELECT COUNT(*) FROM reacciones_comentario WHERE comentario_id = ?", (id_comentario,)
        ).fetchone()[0]
        con.commit()
    finally:
        con.close()
    return {"comentario_id": id_comentario, "reacciones": total, "reaccione_mia": not quitadas}


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
    """Moderación: borra sin preguntar de quién es, con todo y reacciones."""
    con = _conectar()
    try:
        con.execute("DELETE FROM reacciones_comentario WHERE comentario_id = ?", (id_comentario,))
        borradas = con.execute("DELETE FROM comentarios WHERE id = ?", (id_comentario,)).rowcount
        con.commit()
    finally:
        con.close()
    return borradas > 0
