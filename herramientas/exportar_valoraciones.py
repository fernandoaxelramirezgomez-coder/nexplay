"""Exporta a CSV los votos, los comentarios y los votos a las respuestas de Nia.

Es local a propósito: la API devuelve los comentarios sin identidad, y aquí sí va el id
anónimo de quien los escribió. Lee datos/valoraciones.db (contenido de usuarios) y le
pega el nombre del juego desde datos/nexplay.db.

Genera tres archivos: votos de la segunda opinión, comentarios y votos a Nia. El último
lleva la pregunta y la respuesta completas, porque un 👎 sin saber a qué se refería no
sirve de nada; esas filas se borran solas a los 180 días (api/valoraciones.py).

Uso:
  python exportar_valoraciones.py                    # extracto/valoraciones-AAAA-MM-DD.csv y -comentarios.csv
  python exportar_valoraciones.py --salida ruta.csv
"""

import argparse
import csv
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VALORACIONES_PATH = Path(os.environ.get("NEXPLAY_VALORACIONES_DB", RAIZ / "datos" / "valoraciones.db"))
CATALOGO_PATH = RAIZ / "datos" / "nexplay.db"
COLUMNAS_VOTOS = ["appid", "nombre", "usuario", "calificacion", "creado", "actualizado"]
COLUMNAS_COMENTARIOS = ["id", "appid", "nombre", "usuario", "texto", "creado"]
COLUMNAS_NIA = [
    "id_respuesta", "usuario", "voto", "motivo", "appid", "nombre",
    "pregunta", "respuesta", "modo", "modelo", "version_prompt", "creado", "votado",
]


def _nombres_por_appid() -> dict[int, str]:
    if not CATALOGO_PATH.exists():
        print(f"aviso: no está {CATALOGO_PATH}; el CSV saldrá sin la columna nombre.")
        return {}
    con = sqlite3.connect(f"file:{CATALOGO_PATH}?mode=ro", uri=True)
    try:
        return dict(con.execute("SELECT appid, nombre FROM juegos").fetchall())
    finally:
        con.close()


def exportar(salida: Path) -> int:
    if not VALORACIONES_PATH.exists():
        print(f"no existe {VALORACIONES_PATH}: todavía nadie valoró ninguna segunda opinión.")
        return 1

    nombres = _nombres_por_appid()
    con = sqlite3.connect(f"file:{VALORACIONES_PATH}?mode=ro", uri=True)
    try:
        votos = con.execute(
            "SELECT appid, usuario, calificacion, creado, actualizado FROM valoraciones ORDER BY appid, actualizado"
        ).fetchall()
        comentarios = con.execute(
            "SELECT id, appid, usuario, texto, creado FROM comentarios ORDER BY appid, id"
        ).fetchall()
        # Las tablas de Nia son de la fase 5b: una base de antes no las tiene.
        tablas = {fila[0] for fila in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        votos_nia = (
            con.execute(
                """SELECT v.id_respuesta, v.usuario, v.voto, v.motivo, r.appid, r.pregunta, r.respuesta,
                          r.modo, r.modelo, r.version_prompt, r.creado, v.actualizado
                   FROM valoraciones_nia v JOIN respuestas_nia r ON r.id = v.id_respuesta
                   ORDER BY r.creado"""
            ).fetchall()
            if {"respuestas_nia", "valoraciones_nia"} <= tablas
            else []
        )
    finally:
        con.close()

    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS_VOTOS)
        for appid, usuario, calificacion, creado, actualizado in votos:
            escritor.writerow([appid, nombres.get(appid, ""), usuario, calificacion, creado, actualizado])

    salida_comentarios = salida.with_name(f"{salida.stem}-comentarios{salida.suffix}")
    with open(salida_comentarios, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS_COMENTARIOS)
        for id_comentario, appid, usuario, texto, creado in comentarios:
            escritor.writerow([id_comentario, appid, nombres.get(appid, ""), usuario, texto, creado])

    salida_nia = salida.with_name(f"{salida.stem}-nia{salida.suffix}")
    with open(salida_nia, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS_NIA)
        for id_respuesta, usuario, voto, motivo, appid, pregunta, respuesta, modo, modelo, version, creado, votado in votos_nia:
            escritor.writerow([
                id_respuesta, usuario, voto, motivo or "", appid or "", nombres.get(appid, ""),
                pregunta, respuesta, modo, modelo or "", version, creado, votado,
            ])

    promedio = sum(fila[2] for fila in votos) / len(votos) if votos else None
    usuarios = {fila[1] for fila in votos} | {fila[2] for fila in comentarios}
    print(f"{salida}: {len(votos)} calificaciones" + (f", promedio {promedio:.1f} de 5." if votos else "."))
    print(f"{salida_comentarios}: {len(comentarios)} comentarios. {len(usuarios)} usuarios distintos en total.")
    arriba = sum(1 for fila in votos_nia if fila[2] == 1)
    print(f"{salida_nia}: {len(votos_nia)} votos a Nia" + (f", {arriba} de ellos 👍." if votos_nia else "."))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporta las valoraciones a CSV (uso local, no por la API).")
    parser.add_argument(
        "--salida",
        type=Path,
        default=RAIZ / "extracto" / f"valoraciones-{date.today().isoformat()}.csv",
        help="ruta del CSV (por defecto %(default)s)",
    )
    sys.exit(exportar(parser.parse_args().salida))
