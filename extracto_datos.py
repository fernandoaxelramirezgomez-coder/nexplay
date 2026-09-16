"""Genera un extracto minimo de datos/nexplay.db en Parquet, para publicar
como asset de un GitHub Release y que notebook/nexplay.ipynb lo consuma sin
tocar la base local ni el texto de las reseñas.

Columnas incluidas, y por que estan:
- appid, playtime_at_review, voted_up: reconstruyen la variable objetivo
  (Y=1 si playtime_at_review<120 y voted_up==0) y agrupan el GroupKFold.
- timestamp_created: fecha de la reseña, para el EDA temporal.
- num_games_owned: no es feature del modelo de produccion, pero sin ella no
  se puede reproducir la bandera privacidad_perfil (num_games_owned==0) ni
  el experimento de privacidad (comparar_variantes_privacidad).
- es_gratis, precio_final, descuento, metacritic: las cuatro variables del
  lado del juego del conjunto 'compra' (production). Junto con
  log_num_games_owned (derivada de num_games_owned) completan las seis
  variables del modelo productivo.
- nombre: para nombrar juegos concretos en el EDA (contraste novato vs
  veterano de la Capa A), no es feature.

Deliberadamente afuera: texto de la reseña, num_reviews/steam_purchase/
received_for_free/written_during_early_access (solo se usan en el
conjunto 'completo', que tiene fuga post-compra y no es parte de la
historia productiva), steamid, y cualquier otro campo no listado arriba.

Uso:
    python extracto_datos.py
"""

import hashlib
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "datos" / "nexplay.db"
SALIDA_PATH = Path(__file__).resolve().parent / "extracto" / "nexplay_extracto.parquet"

_COLUMNAS = [
    "appid",
    "nombre",
    "playtime_at_review",
    "voted_up",
    "timestamp_created",
    "num_games_owned",
    "es_gratis",
    "precio_final",
    "descuento",
    "metacritic",
]


def generar_extracto() -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT
                r.appid,
                j.nombre,
                r.playtime_at_review,
                r.voted_up,
                r.timestamp_created,
                r.num_games_owned,
                j.es_gratis,
                j.precio_final,
                j.descuento,
                j.metacritic
            FROM resenas r
            JOIN juegos j ON j.appid = r.appid
            ORDER BY r.appid, r.timestamp_created
            """,
            con,
        )
    finally:
        con.close()
    assert list(df.columns) == _COLUMNAS
    return df


def sha256_de(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def main():
    df = generar_extracto()

    SALIDA_PATH.parent.mkdir(exist_ok=True)
    df.to_parquet(SALIDA_PATH, index=False)

    checksum = sha256_de(SALIDA_PATH)
    tamanio_mb = SALIDA_PATH.stat().st_size / (1024 * 1024)

    print(f"extracto guardado en {SALIDA_PATH}")
    print(f"filas={len(df)}  juegos={df['appid'].nunique()}  tamaño={tamanio_mb:.2f} MB")
    print(f"sha256={checksum}")


if __name__ == "__main__":
    main()
