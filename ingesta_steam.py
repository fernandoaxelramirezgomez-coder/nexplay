"""
PostPlay - Ingesta de datos desde las APIs publicas de Steam
===========================================================

Baja el catalogo de juegos y sus resenas, y los guarda en SQLite.

SQLite y no CSV porque la ingesta tarda horas y se interrumpe. Con SQLite
reanudas donde te quedaste en vez de volver a bajar todo.

Lo importante de este script: guarda el bloque "author" completo de cada
resena. Sin num_games_owned y playtime_at_review no puedes separar novatos
de veteranos, y ese es el corazon del proyecto.

Uso:
    python ingesta_steam.py --catalogo    # metadatos de los juegos
    python ingesta_steam.py --resenas     # resenas (esto es lo que tarda)
    python ingesta_steam.py --estado      # cuanto llevas

Fernando Barranco / Diplomado en Ciencia de Datos, FES Acatlan (UNAM)
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "datos" / "postplay.db"
APPIDS_PATH = BASE / "appids.txt"
LOCK_PATH = BASE / "ingesta.lock"

URL_DETALLES = "https://store.steampowered.com/api/appdetails"
URL_RESENAS = "https://store.steampowered.com/appreviews/{appid}"

# Steam limita appdetails a ~200 peticiones cada 5 minutos.
# Si empiezan a salir errores 429, sube estos numeros.
ESPERA_DETALLES = 1.6
ESPERA_RESENAS = 1.2

# Tope de resenas por juego. 2000 da buena cobertura temporal en juegos
# medianos sin que la ingesta se vuelva de dias.
MAX_RESENAS_POR_JUEGO = 1500

# "english" da volumen para el NLP. Puedes poner "all" o "spanish".
IDIOMA = "english"

# Steam bloquea peticiones sin User-Agent identificable.
HEADERS = {"User-Agent": "PostPlay-Academico/1.0 (proyecto FES Acatlan)"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE / "ingesta.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("postplay")


# ---------------------------------------------------------------------------
# Candado
# ---------------------------------------------------------------------------
# Dos ingestas sobre la misma base se pisan: se reparten los cursores, el
# contador de progreso queda mal y algunos juegos se marcan como terminados
# antes de tiempo. Este candado lo impide.

def tomar_candado():
    if LOCK_PATH.exists():
        try:
            pid = int(LOCK_PATH.read_text().strip())
        except (ValueError, OSError):
            pid = None
        if pid and Path(f"/proc/{pid}").exists():
            log.error("Ya hay una ingesta corriendo con PID %s.", pid)
            log.error("Para detenerla:  kill %s", pid)
            sys.exit(1)
        log.warning("Habia un candado viejo sin proceso vivo. Lo reemplazo.")
    LOCK_PATH.write_text(str(os.getpid()))


def soltar_candado():
    LOCK_PATH.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------

ESQUEMA = """
CREATE TABLE IF NOT EXISTS juegos (
    appid                INTEGER PRIMARY KEY,
    nombre               TEXT,
    tipo                 TEXT,
    fecha_lanzamiento    TEXT,
    proximamente         INTEGER,
    es_gratis            INTEGER,
    precio_inicial       INTEGER,
    precio_final         INTEGER,
    descuento            INTEGER,
    moneda               TEXT,
    generos              TEXT,
    categorias           TEXT,
    desarrolladores      TEXT,
    editores             TEXT,
    metacritic           INTEGER,
    soporta_windows      INTEGER,
    soporta_mac          INTEGER,
    soporta_linux        INTEGER,
    descripcion_corta    TEXT,
    descargado_en        TEXT
);

CREATE TABLE IF NOT EXISTS resenas (
    recommendationid            TEXT PRIMARY KEY,
    appid                       INTEGER,
    steamid                     TEXT,
    num_games_owned             INTEGER,
    num_reviews                 INTEGER,
    playtime_forever            INTEGER,
    playtime_last_two_weeks     INTEGER,
    playtime_at_review          INTEGER,
    last_played                 INTEGER,
    idioma                      TEXT,
    texto                       TEXT,
    timestamp_created           INTEGER,
    timestamp_updated           INTEGER,
    voted_up                    INTEGER,
    votes_up                    INTEGER,
    votes_funny                 INTEGER,
    weighted_vote_score         REAL,
    comment_count               INTEGER,
    steam_purchase              INTEGER,
    received_for_free           INTEGER,
    written_during_early_access INTEGER,
    descargado_en               TEXT
);

CREATE INDEX IF NOT EXISTS idx_resenas_appid ON resenas(appid);
CREATE INDEX IF NOT EXISTS idx_resenas_fecha ON resenas(timestamp_created);

CREATE TABLE IF NOT EXISTS resumen_resenas (
    appid             INTEGER PRIMARY KEY,
    total_resenas     INTEGER,
    total_positivas   INTEGER,
    total_negativas   INTEGER,
    descripcion_score TEXT,
    actualizado_en    TEXT
);

CREATE TABLE IF NOT EXISTS progreso (
    appid          INTEGER PRIMARY KEY,
    cursor         TEXT,
    bajadas        INTEGER DEFAULT 0,
    terminado      INTEGER DEFAULT 0,
    actualizado_en TEXT
);
"""


def conectar():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(ESQUEMA)
    con.commit()
    return con


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def pedir(url, params=None, intentos=4):
    """GET con reintentos. Devuelve el JSON o None si no se pudo."""
    for intento in range(1, intentos + 1):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                espera = 30 * intento
                log.warning("429 de Steam. Espero %ss", espera)
                time.sleep(espera)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            log.warning("Fallo intento %s/%s: %s", intento, intentos, e)
            time.sleep(3 * intento)
    return None


def leer_appids():
    if not APPIDS_PATH.exists():
        log.error("No existe %s", APPIDS_PATH)
        sys.exit(1)
    ids = []
    for linea in APPIDS_PATH.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#")[0].strip()
        if linea.isdigit():
            ids.append(int(linea))
    if not ids:
        log.error("appids.txt no tiene ningun appid activo. Descomenta algunos.")
        sys.exit(1)
    return ids


def lista_a_texto(valor, campo=None):
    """Aplana las listas que devuelve Steam a texto separado por |."""
    if not valor:
        return None
    if campo:
        return "|".join(str(x.get(campo, "")) for x in valor)
    return "|".join(str(x) for x in valor)


# ---------------------------------------------------------------------------
# Catalogo
# ---------------------------------------------------------------------------

def bajar_juego(con, appid):
    datos = pedir(URL_DETALLES, {"appids": appid, "cc": "mx", "l": "spanish"})
    if not datos:
        log.error("appid %s: sin respuesta", appid)
        return False

    bloque = datos.get(str(appid), {})
    if not bloque.get("success"):
        log.warning("appid %s: Steam responde success=false (puede no existir)", appid)
        return False

    d = bloque.get("data", {})
    precio = d.get("price_overview") or {}
    lanzamiento = d.get("release_date") or {}
    plataformas = d.get("platforms") or {}
    metacritic = (d.get("metacritic") or {}).get("score")

    con.execute(
        """INSERT OR REPLACE INTO juegos VALUES
           (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            appid,
            d.get("name"),
            d.get("type"),
            lanzamiento.get("date"),
            1 if lanzamiento.get("coming_soon") else 0,
            1 if d.get("is_free") else 0,
            precio.get("initial"),
            precio.get("final"),
            precio.get("discount_percent"),
            precio.get("currency"),
            lista_a_texto(d.get("genres"), "description"),
            lista_a_texto(d.get("categories"), "description"),
            lista_a_texto(d.get("developers")),
            lista_a_texto(d.get("publishers")),
            metacritic,
            1 if plataformas.get("windows") else 0,
            1 if plataformas.get("mac") else 0,
            1 if plataformas.get("linux") else 0,
            d.get("short_description"),
            ahora(),
        ),
    )
    con.commit()
    log.info("appid %-8s OK  %s", appid, d.get("name"))
    return True


def correr_catalogo(con, appids):
    log.info("Catalogo: %s juegos por bajar", len(appids))
    for i, appid in enumerate(appids, 1):
        bajar_juego(con, appid)
        if i < len(appids):
            time.sleep(ESPERA_DETALLES)


# ---------------------------------------------------------------------------
# Resenas
# ---------------------------------------------------------------------------

def guardar_resumen(con, appid, resumen):
    con.execute(
        "INSERT OR REPLACE INTO resumen_resenas VALUES (?,?,?,?,?,?)",
        (
            appid,
            resumen.get("total_reviews"),
            resumen.get("total_positive"),
            resumen.get("total_negative"),
            resumen.get("review_score_desc"),
            ahora(),
        ),
    )
    con.commit()


def guardar_resenas(con, appid, resenas):
    filas = []
    for r in resenas:
        a = r.get("author") or {}
        filas.append((
            r.get("recommendationid"),
            appid,
            a.get("steamid"),
            a.get("num_games_owned"),
            a.get("num_reviews"),
            a.get("playtime_forever"),
            a.get("playtime_last_two_weeks"),
            a.get("playtime_at_review"),
            a.get("last_played"),
            r.get("language"),
            r.get("review"),
            r.get("timestamp_created"),
            r.get("timestamp_updated"),
            1 if r.get("voted_up") else 0,
            r.get("votes_up"),
            r.get("votes_funny"),
            r.get("weighted_vote_score"),
            r.get("comment_count"),
            1 if r.get("steam_purchase") else 0,
            1 if r.get("received_for_free") else 0,
            1 if r.get("written_during_early_access") else 0,
            ahora(),
        ))
    con.executemany(
        "INSERT OR IGNORE INTO resenas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        filas,
    )
    con.commit()
    return len(filas)


def bajar_resenas_juego(con, appid):
    fila = con.execute(
        "SELECT cursor, bajadas, terminado FROM progreso WHERE appid=?", (appid,)
    ).fetchone()

    if fila and fila[2]:
        log.info("appid %-8s ya terminado (%s resenas)", appid, fila[1])
        return

    cursor = fila[0] if fila else "*"
    bajadas = fila[1] if fila else 0
    cursores_vistos = set()
    primera_vuelta = True

    while bajadas < MAX_RESENAS_POR_JUEGO:
        # El cursor trae caracteres que hay que codificar para la URL.
        url = URL_RESENAS.format(appid=appid) + "?" + "&".join([
            "json=1",
            "filter=recent",
            f"language={IDIOMA}",
            "purchase_type=all",
            "num_per_page=100",
            f"cursor={quote(cursor, safe='')}",
        ])
        datos = pedir(url)

        if not datos or datos.get("success") != 1:
            log.error("appid %s: respuesta invalida, lo dejo para despues", appid)
            return

        if primera_vuelta:
            guardar_resumen(con, appid, datos.get("query_summary") or {})
            primera_vuelta = False

        lote = datos.get("reviews") or []
        if not lote:
            break

        bajadas += guardar_resenas(con, appid, lote)

        siguiente = datos.get("cursor")
        # Bug conocido de Steam: el cursor se repite y el script entra en bucle.
        if not siguiente or siguiente in cursores_vistos:
            break
        cursores_vistos.add(siguiente)
        cursor = siguiente

        con.execute(
            "INSERT OR REPLACE INTO progreso VALUES (?,?,?,?,?)",
            (appid, cursor, bajadas, 0, ahora()),
        )
        con.commit()
        log.info("appid %-8s %s resenas", appid, bajadas)
        time.sleep(ESPERA_RESENAS)

    con.execute(
        "INSERT OR REPLACE INTO progreso VALUES (?,?,?,?,?)",
        (appid, cursor, bajadas, 1, ahora()),
    )
    con.commit()
    log.info("appid %-8s TERMINADO con %s resenas", appid, bajadas)


def correr_resenas(con):
    appids = [f[0] for f in con.execute("SELECT appid FROM juegos ORDER BY appid")]
    if not appids:
        log.error("No hay juegos en la base. Corre primero --catalogo")
        return
    log.info("Resenas: %s juegos en cola", len(appids))
    for appid in appids:
        bajar_resenas_juego(con, appid)


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------

def mostrar_estado(con):
    juegos = con.execute("SELECT COUNT(*) FROM juegos").fetchone()[0]
    resenas = con.execute("SELECT COUNT(*) FROM resenas").fetchone()[0]
    listos = con.execute("SELECT COUNT(*) FROM progreso WHERE terminado=1").fetchone()[0]

    print()
    print("  PostPlay / estado de la ingesta")
    print("  " + "-" * 44)
    print(f"  Juegos en catalogo      {juegos}")
    print(f"  Juegos con resenas OK   {listos}")
    print(f"  Resenas totales         {resenas:,}")

    if resenas:
        novatos = con.execute(
            "SELECT COUNT(*) FROM resenas WHERE num_games_owned < 20"
        ).fetchone()[0]
        print(f"  De novatos (<20 juegos) {novatos:,}  ({novatos/resenas:.1%})")
        print()
        print("  Resenas por juego:")
        for nombre, n in con.execute("""
            SELECT j.nombre, COUNT(r.recommendationid)
            FROM juegos j LEFT JOIN resenas r ON r.appid = j.appid
            GROUP BY j.appid ORDER BY 2 DESC
        """):
            print(f"    {n:>7,}  {nombre}")
    print()


# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Ingesta de Steam para PostPlay")
    p.add_argument("--catalogo", action="store_true", help="baja metadatos de juegos")
    p.add_argument("--resenas", action="store_true", help="baja resenas")
    p.add_argument("--estado", action="store_true", help="muestra el avance")
    args = p.parse_args()

    con = conectar()

    # --estado no toma candado: quiero poder consultarlo mientras baja.
    if args.estado:
        mostrar_estado(con)
        con.close()
        return

    if not (args.catalogo or args.resenas):
        p.print_help()
        con.close()
        return

    tomar_candado()
    try:
        if args.catalogo:
            correr_catalogo(con, leer_appids())
        if args.resenas:
            correr_resenas(con)
        mostrar_estado(con)
    except KeyboardInterrupt:
        log.warning("Interrumpido. El avance quedo guardado, puedes reanudar.")
    finally:
        soltar_candado()
        con.close()


if __name__ == "__main__":
    main()
