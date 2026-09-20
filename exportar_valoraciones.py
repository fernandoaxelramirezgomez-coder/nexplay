"""Exporta a CSV todas las valoraciones de la segunda opinión, para analizarlas.

Es local a propósito: la API nunca devuelve comentarios de otras personas, solo los
conteos. Este script lee datos/valoraciones.db (la base de contenido de usuarios) y le
pega el nombre del juego desde datos/nexplay.db.

Uso:
  python exportar_valoraciones.py                    # extracto/valoraciones-AAAA-MM-DD.csv
  python exportar_valoraciones.py --salida ruta.csv
"""

import argparse
import csv
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VALORACIONES_PATH = Path(os.environ.get("NEXPLAY_VALORACIONES_DB", RAIZ / "datos" / "valoraciones.db"))
CATALOGO_PATH = RAIZ / "datos" / "nexplay.db"
COLUMNAS = ["appid", "nombre", "usuario", "util", "comentario", "creado", "actualizado"]


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
        filas = con.execute(
            "SELECT appid, usuario, util, comentario, creado, actualizado "
            "FROM valoraciones ORDER BY appid, actualizado"
        ).fetchall()
    finally:
        con.close()

    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS)
        for appid, usuario, util, comentario, creado, actualizado in filas:
            escritor.writerow(
                [appid, nombres.get(appid, ""), usuario, "si" if util else "no", comentario or "", creado, actualizado]
            )

    con_comentario = sum(1 for fila in filas if fila[3])
    utiles = sum(1 for fila in filas if fila[2])
    print(
        f"{salida}: {len(filas)} valoraciones ({utiles} útiles, {len(filas) - utiles} no útiles), "
        f"{con_comentario} con comentario, {len({fila[1] for fila in filas})} usuarios."
    )
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
