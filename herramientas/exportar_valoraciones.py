"""Exporta a CSV los votos y los comentarios, para analizarlos.

Es local a propósito: la API devuelve los comentarios sin identidad, y aquí sí va el id
anónimo de quien los escribió. Lee datos/valoraciones.db (contenido de usuarios) y le
pega el nombre del juego desde datos/nexplay.db.

Genera dos archivos: uno de votos y otro de comentarios.

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

    promedio = sum(fila[2] for fila in votos) / len(votos) if votos else None
    usuarios = {fila[1] for fila in votos} | {fila[2] for fila in comentarios}
    print(f"{salida}: {len(votos)} calificaciones" + (f", promedio {promedio:.1f} de 5." if votos else "."))
    print(f"{salida_comentarios}: {len(comentarios)} comentarios. {len(usuarios)} usuarios distintos en total.")
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
