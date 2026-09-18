"""Genera una copia sanitizada de datos/nexplay.db para publicar como asset
de un GitHub Release: preparar_entorno.py la descarga y reconstruye un
datos/nexplay.db funcional en una máquina limpia, sin tocar la base local.

A diferencia de extracto_datos.py (que genera un Parquet mínimo solo para
el notebook, sin texto de reseña), esto copia las tablas 'juegos' y
'resenas' completas -incluido el texto, que api/scoring.py::motivos_frecuentes
necesita para construir /explicacion- con una sola exclusión: la columna
steamid de 'resenas'. Es un identificador de cuenta de Steam real; nada en
el proyecto la usa (ni la API ni el entrenamiento), así que no hay razón
para redistribuirla.

'juegos' se copia entera: es metadata pública de la tienda de Steam (precio,
géneros, etc.), sin ningún campo sensible.

Las tablas resumen_resenas y progreso no se copian: son metadata de la
ingesta (agregados ya derivables de 'resenas', progreso de paginación), no
las usa ni la API ni el entrenamiento.

Uso:
    python extracto_reproducible.py
"""

import hashlib
import lzma
import sqlite3
from pathlib import Path

DB_ORIGEN = Path(__file__).resolve().parent / "datos" / "nexplay.db"
DB_SALIDA = Path(__file__).resolve().parent / "extracto" / "nexplay_reproducible.db"
COMPRIMIDO_SALIDA = DB_SALIDA.with_suffix(".db.xz")

# Todas las columnas de 'resenas' salvo steamid.
_COLUMNAS_RESENAS = [
    "recommendationid",
    "appid",
    "num_games_owned",
    "num_reviews",
    "playtime_forever",
    "playtime_last_two_weeks",
    "playtime_at_review",
    "last_played",
    "idioma",
    "texto",
    "timestamp_created",
    "timestamp_updated",
    "voted_up",
    "votes_up",
    "votes_funny",
    "weighted_vote_score",
    "comment_count",
    "steam_purchase",
    "received_for_free",
    "written_during_early_access",
    "descargado_en",
]


def sha256_de(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def generar_db_sanitizada() -> None:
    DB_SALIDA.parent.mkdir(exist_ok=True)
    if DB_SALIDA.exists():
        DB_SALIDA.unlink()

    con = sqlite3.connect(DB_SALIDA)
    try:
        con.execute("ATTACH DATABASE ? AS origen", (str(DB_ORIGEN),))
        con.execute("CREATE TABLE juegos AS SELECT * FROM origen.juegos")
        con.execute("CREATE UNIQUE INDEX idx_juegos_appid ON juegos(appid)")

        columnas = ", ".join(_COLUMNAS_RESENAS)
        con.execute(f"CREATE TABLE resenas AS SELECT {columnas} FROM origen.resenas")
        con.execute("CREATE INDEX idx_resenas_appid ON resenas(appid)")

        con.commit()
    finally:
        con.execute("DETACH DATABASE origen")
        con.close()


def comprimir() -> None:
    with open(DB_SALIDA, "rb") as f_in, lzma.open(COMPRIMIDO_SALIDA, "wb", preset=6) as f_out:
        f_out.write(f_in.read())


def main():
    generar_db_sanitizada()
    comprimir()

    tamanio_db_mb = DB_SALIDA.stat().st_size / (1024 * 1024)
    tamanio_xz_mb = COMPRIMIDO_SALIDA.stat().st_size / (1024 * 1024)
    checksum = sha256_de(COMPRIMIDO_SALIDA)

    print(f"db sanitizada: {DB_SALIDA} ({tamanio_db_mb:.1f} MB)")
    print(f"comprimida:    {COMPRIMIDO_SALIDA} ({tamanio_xz_mb:.1f} MB)")
    print(f"sha256={checksum}")
    print()
    print("Subir COMPRIMIDO_SALIDA como asset del release (mismo tag que el")
    print("extracto del notebook) y pegar ese sha256 en preparar_entorno.py.")


if __name__ == "__main__":
    main()
