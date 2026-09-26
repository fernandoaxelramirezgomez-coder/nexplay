"""Valoraciones de la segunda opinión y su hilo de comentarios.

Viven en su propia base (datos/valoraciones.db, movible con NEXPLAY_VALORACIONES_DB),
separada de nexplay.db: es contenido de quien usa la app, no datos del proyecto, y
preparar_entorno.py no la reconstruye ni la pisa.

- La calificación (1 a 5 estrellas) es una por persona y juego, y se puede cambiar.
- Los comentarios son un hilo público. Se devuelven sin identidad: el id de quien
  escribió nunca sale de este módulo, solo se compara contra quien pregunta para marcar
  cuáles son suyos. Cada quien edita y borra los propios; ese mismo id sirve para el
  límite de frecuencia y para ubicar una fila desde moderar_comentarios.py.
- Las reacciones son un pulgar arriba por persona y comentario: una fila o ninguna.
- Los votos a Nia son 👍/👎 por persona y respuesta, con un motivo opcional cuando es 👎.
  La respuesta se guarda al producirla, con su modo, su modelo y la versión del prompt,
  porque un voto sin saber a qué se refería no sirve de nada; todo eso se borra a los
  DIAS_DE_RETENCION_NIA días.

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
        # El voto útil/no útil pasó a una calificación de 1 a 5. La tabla vieja tenía
        # votos de prueba y se recrea limpia en vez de traducirlos: "útil" no tiene un
        # número de estrellas equivalente honesto.
        columnas = {fila[1] for fila in con.execute("PRAGMA table_info(valoraciones)")}
        if columnas and "calificacion" not in columnas:
            con.execute("DROP TABLE valoraciones")
            logger.info("tabla valoraciones recreada con calificación 1-5 (los votos útil/no útil eran de prueba)")
        con.execute(
            """CREATE TABLE IF NOT EXISTS valoraciones (
                   usuario      TEXT    NOT NULL,
                   appid        INTEGER NOT NULL,
                   calificacion INTEGER NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
                   creado       TEXT    NOT NULL,
                   actualizado  TEXT    NOT NULL,
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

        # Las respuestas de Nia se guardan al producirlas y no al votarlas: así el voto
        # sigue sirviendo después de reiniciar la API —pasa en cada cambio de código— y se
        # puede saber qué proporción de respuestas recibe voto, que dice tanto como el
        # voto. A cambio se guarda también lo que nadie votó, y por eso hay retención.
        con.execute(
            """CREATE TABLE IF NOT EXISTS respuestas_nia (
                   id             TEXT    PRIMARY KEY,
                   usuario        TEXT    NOT NULL,
                   appid          INTEGER,
                   pregunta       TEXT    NOT NULL,
                   respuesta      TEXT    NOT NULL,
                   modo           TEXT    NOT NULL,
                   modelo         TEXT,
                   version_prompt TEXT    NOT NULL,
                   creado         TEXT    NOT NULL
               )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_respuestas_nia_creado ON respuestas_nia (creado)")
        con.execute(
            """CREATE TABLE IF NOT EXISTS valoraciones_nia (
                   usuario      TEXT    NOT NULL,
                   id_respuesta TEXT    NOT NULL REFERENCES respuestas_nia (id),
                   voto         INTEGER NOT NULL CHECK (voto IN (-1, 1)),
                   motivo       TEXT,
                   creado       TEXT    NOT NULL,
                   actualizado  TEXT    NOT NULL,
                   PRIMARY KEY (usuario, id_respuesta)
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
    """Promedio y total del juego y, si se pide, la calificación de ese usuario. El
    promedio es None cuando nadie ha calificado: un 0.0 se leería como "cero estrellas"."""
    con = _conectar()
    try:
        promedio, total = con.execute(
            "SELECT AVG(calificacion), COUNT(*) FROM valoraciones WHERE appid = ?", (appid,)
        ).fetchone()
        mia = None
        if usuario:
            fila = con.execute(
                "SELECT calificacion FROM valoraciones WHERE appid = ? AND usuario = ?", (appid, usuario)
            ).fetchone()
            mia = fila[0] if fila else None
    finally:
        con.close()
    return {"appid": appid, "promedio": promedio, "total": total, "mia": mia}


def guardar(appid: int, usuario: str, calificacion: int) -> dict:
    """Crea o cambia la calificación de ese usuario para ese juego."""
    ahora = _ahora()
    con = _conectar()
    try:
        con.execute(
            """INSERT INTO valoraciones (usuario, appid, calificacion, creado, actualizado)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (usuario, appid) DO UPDATE SET
                   calificacion = excluded.calificacion,
                   actualizado = excluded.actualizado""",
            (usuario, appid, calificacion, ahora, ahora),
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


# Cuánto se conservan la pregunta, la respuesta y su voto. Seis meses alcanzan para
# comparar dos o tres versiones del prompt, que es para lo que se guardan. El barrido corre
# en cada escritura: una retención que nadie ejecuta no es una retención.
DIAS_DE_RETENCION_NIA = 180

MOTIVOS_VOTO_NIA = (
    "no respondió lo que pregunté",
    "dato incorrecto",
    "muy larga",
    "me recomendó algo",
)


class RespuestaNiaInexistente(Exception):
    """No hay respuesta de Nia con ese id: o nunca existió o ya venció su retención."""


def _barrer_vencidas(con: sqlite3.Connection) -> int:
    """Borra lo que pasó de la retención, y con ello los votos que apuntaban ahí."""
    limite = f"-{DIAS_DE_RETENCION_NIA} days"
    con.execute(
        "DELETE FROM valoraciones_nia WHERE id_respuesta IN"
        " (SELECT id FROM respuestas_nia WHERE creado < date('now', ?))",
        (limite,),
    )
    return con.execute("DELETE FROM respuestas_nia WHERE creado < date('now', ?)", (limite,)).rowcount


def registrar_respuesta_nia(
    id_respuesta: str,
    usuario: str,
    appid: int | None,
    pregunta: str,
    respuesta: str,
    modo: str,
    modelo: str | None,
    version_prompt: str,
) -> None:
    """Deja constancia de lo que Nia contestó, para que su voto tenga a qué referirse."""
    con = _conectar()
    try:
        vencidas = _barrer_vencidas(con)
        con.execute(
            """INSERT OR REPLACE INTO respuestas_nia
                   (id, usuario, appid, pregunta, respuesta, modo, modelo, version_prompt, creado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (id_respuesta, usuario, appid, pregunta, respuesta, modo, modelo, version_prompt, _ahora()),
        )
        con.commit()
    finally:
        con.close()
    if vencidas:
        logger.info("retención de Nia: %s respuestas de más de %s días borradas", vencidas, DIAS_DE_RETENCION_NIA)


def _exigir_respuesta(con: sqlite3.Connection, id_respuesta: str) -> None:
    if con.execute("SELECT 1 FROM respuestas_nia WHERE id = ?", (id_respuesta,)).fetchone() is None:
        raise RespuestaNiaInexistente(id_respuesta)


def voto_nia(id_respuesta: str, usuario: str) -> dict:
    """El voto de esa persona para esa respuesta, o ninguno."""
    con = _conectar()
    try:
        fila = con.execute(
            "SELECT voto, motivo FROM valoraciones_nia WHERE id_respuesta = ? AND usuario = ?",
            (id_respuesta, usuario),
        ).fetchone()
    finally:
        con.close()
    return {
        "id_respuesta": id_respuesta,
        "voto": fila[0] if fila else None,
        "motivo": fila[1] if fila else None,
    }


def guardar_voto_nia(id_respuesta: str, usuario: str, voto: int, motivo: str | None = None) -> dict:
    """Crea o cambia el voto. El motivo solo acompaña al 👎: con 👍 no hay nada que
    explicar y guardarlo sería ruido."""
    if motivo is not None and (voto != -1 or motivo not in MOTIVOS_VOTO_NIA):
        motivo = None
    ahora = _ahora()
    con = _conectar()
    try:
        _exigir_respuesta(con, id_respuesta)
        con.execute(
            """INSERT INTO valoraciones_nia (usuario, id_respuesta, voto, motivo, creado, actualizado)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (usuario, id_respuesta) DO UPDATE SET
                   voto = excluded.voto,
                   motivo = excluded.motivo,
                   actualizado = excluded.actualizado""",
            (usuario, id_respuesta, voto, motivo, ahora, ahora),
        )
        con.commit()
    finally:
        con.close()
    return voto_nia(id_respuesta, usuario)


def borrar_voto_nia(id_respuesta: str, usuario: str) -> dict:
    con = _conectar()
    try:
        _exigir_respuesta(con, id_respuesta)
        con.execute(
            "DELETE FROM valoraciones_nia WHERE id_respuesta = ? AND usuario = ?", (id_respuesta, usuario)
        )
        con.commit()
    finally:
        con.close()
    return voto_nia(id_respuesta, usuario)


def votos_nia_para_exportar() -> list[tuple]:
    """Con identidad y con el texto: solo para exportar_valoraciones.py y para la consulta
    de docs/evidencia, nunca para la API."""
    con = _conectar()
    try:
        return con.execute(
            """SELECT v.id_respuesta, v.usuario, v.voto, v.motivo, r.appid, r.pregunta, r.respuesta,
                      r.modo, r.modelo, r.version_prompt, r.creado, v.actualizado
               FROM valoraciones_nia v JOIN respuestas_nia r ON r.id = v.id_respuesta
               ORDER BY r.creado"""
        ).fetchall()
    finally:
        con.close()


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
