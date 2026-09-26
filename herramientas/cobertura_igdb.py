"""Cobertura de IGDB sobre los juegos del catálogo sin Metacritic (punto 26 de la fase 6).

IGDB publica `aggregated_rating`, el promedio de críticas externas de cada juego. Antes
de integrarlo como fuente secundaria se mide cuántos de los juegos sin Metacritic lo
tienen: si es la mitad o más, se integra, rotulado y fuera del modelo; si no, se queda
solo el sentimiento de Steam.

Las credenciales son las de una aplicación de Twitch (IGDB usa las de Twitch) y se leen
de `.env` o del entorno, igual que la clave de OpenAI en api/config.py. El script nunca
las imprime: si faltan, dice cuáles.

    TWITCH_CLIENT_ID=...
    TWITCH_CLIENT_SECRET=...

Uso:
  .venv/bin/python herramientas/cobertura_igdb.py            # mide y reporta
  .venv/bin/python herramientas/cobertura_igdb.py --guardar  # además escribe datos/critica_igdb.json,
                                                             # solo si pasa el umbral
"""

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parent.parent
REPORTE = RAIZ / "registros" / "cobertura_igdb.json"
DESTINO = RAIZ / "datos" / "critica_igdb.json"
UMBRAL = 0.5
# IGDB permite 4 consultas por segundo.
PAUSA = 0.3
STEAM = 1


class Credenciales(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", env_file_encoding="utf-8", extra="ignore")

    twitch_client_id: str = ""
    twitch_client_secret: str = ""


def _post(url: str, cuerpo: bytes, cabeceras: dict[str, str]) -> object:
    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method="POST")
    with urllib.request.urlopen(peticion, timeout=20) as respuesta:
        return json.load(respuesta)


def _token(credenciales: Credenciales) -> str:
    cuerpo = urllib.parse.urlencode({
        "client_id": credenciales.twitch_client_id,
        "client_secret": credenciales.twitch_client_secret,
        "grant_type": "client_credentials",
    }).encode()
    return _post("https://id.twitch.tv/oauth2/token", cuerpo, {})["access_token"]


def _igdb(endpoint: str, consulta: str, credenciales: Credenciales, token: str) -> list[dict]:
    time.sleep(PAUSA)
    return _post(
        f"https://api.igdb.com/v4/{endpoint}",
        consulta.encode(),
        {
            "Client-ID": credenciales.twitch_client_id,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )


def _sin_metacritic(api: str) -> list[dict]:
    with urllib.request.urlopen(f"{api}/catalogo", timeout=20) as respuesta:
        return [j for j in json.load(respuesta) if j["metacritic"] is None]


def _por_appid_de_steam(appids: list[int], credenciales: Credenciales, token: str) -> dict[int, int]:
    """appid de Steam → id de juego en IGDB. IGDB cambió el campo que dice de qué tienda
    es cada id externo (`category` pasó a `external_game_source`): se prueba el nuevo y,
    si lo rechaza, el viejo. En los dos, Steam es el 1."""
    uids = ",".join(f'"{a}"' for a in appids)
    for campo in ("external_game_source", "category"):
        try:
            filas = _igdb(
                "external_games", f"fields game,uid; where {campo} = {STEAM} & uid = ({uids}); limit 500;",
                credenciales, token,
            )
        except urllib.error.HTTPError as error:
            if error.code == 400:
                continue
            raise
        vinculos: dict[int, int] = {}
        for fila in filas:
            if str(fila.get("uid", "")).isdigit() and fila.get("game"):
                vinculos.setdefault(int(fila["uid"]), fila["game"])
        return vinculos
    raise SystemExit("IGDB rechazó la búsqueda por id de Steam con los dos nombres de campo conocidos.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cobertura de IGDB sobre los juegos sin Metacritic.")
    parser.add_argument("--api", default="http://localhost:8000", help="API de NexPlay (por defecto %(default)s)")
    parser.add_argument("--guardar", action="store_true", help="escribe datos/critica_igdb.json si pasa el umbral")
    args = parser.parse_args()

    credenciales = Credenciales()
    faltan = [n for n, v in (("TWITCH_CLIENT_ID", credenciales.twitch_client_id),
                             ("TWITCH_CLIENT_SECRET", credenciales.twitch_client_secret)) if not v.strip()]
    if faltan:
        print(f"Faltan en .env o en el entorno: {', '.join(faltan)}. No se consultó IGDB.")
        return 2

    juegos = _sin_metacritic(args.api)
    try:
        token = _token(credenciales)
        vinculos = _por_appid_de_steam([j["appid"] for j in juegos], credenciales, token)
        ids = sorted(set(vinculos.values()))
        datos = {
            fila["id"]: fila
            for fila in (_igdb(
                "games", f"fields name,aggregated_rating,aggregated_rating_count; where id = ({','.join(map(str, ids))}); limit 500;",
                credenciales, token,
            ) if ids else [])
        }
    except urllib.error.HTTPError as error:
        # El cuerpo de error de Twitch e IGDB no trae las credenciales.
        print(f"IGDB respondió {error.code}: {error.read()[:200].decode(errors='replace')}")
        return 1

    filas = []
    for juego in juegos:
        igdb = datos.get(vinculos.get(juego["appid"], -1), {})
        filas.append({
            "appid": juego["appid"],
            "nombre": juego["nombre"],
            "igdb": igdb.get("id"),
            "nota": round(igdb["aggregated_rating"], 1) if igdb.get("aggregated_rating") is not None else None,
            "criticas": igdb.get("aggregated_rating_count"),
        })
    cubiertos = [f for f in filas if f["nota"] is not None]
    umbral = math.ceil(len(filas) * UMBRAL)
    pasa = len(cubiertos) >= umbral

    for fila in filas:
        if fila["nota"] is not None:
            detalle = f"{fila['nota']} ({fila['criticas']} críticas)"
        else:
            detalle = "en IGDB, sin nota de crítica" if fila["igdb"] else "no está en IGDB"
        print(f"  {fila['nombre'][:40]:40} {detalle}")
    print(
        f"IGDB: {len(cubiertos)} de {len(filas)} juegos sin Metacritic tienen nota de crítica "
        f"({len(cubiertos) / len(filas):.0%}); umbral {umbral}: {'PASA' if pasa else 'NO PASA'}. "
        f"En IGDB están {sum(1 for f in filas if f['igdb'])}."
    )

    REPORTE.parent.mkdir(exist_ok=True)
    REPORTE.write_text(json.dumps({
        "fecha": date.today().isoformat(), "juegos": len(filas), "con_nota": len(cubiertos),
        "umbral": umbral, "pasa": pasa, "detalle": filas,
    }, ensure_ascii=False, indent=2))
    print(f"Detalle en {REPORTE.relative_to(RAIZ)}")

    if args.guardar:
        if not pasa:
            print("No se guarda nada: no pasa el umbral y se queda solo Steam.")
            return 1
        DESTINO.write_text(json.dumps({
            str(f["appid"]): {"nota": f["nota"], "criticas": f["criticas"], "igdb": f["igdb"]}
            for f in cubiertos
        }, ensure_ascii=False, indent=2))
        print(f"Guardado {DESTINO.relative_to(RAIZ)} con {len(cubiertos)} juegos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
