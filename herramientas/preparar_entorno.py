"""
NexPlay - Prepara un entorno limpio de punta a punta
=====================================================

Para que el proyecto completo sea reproducible (no solo el notebook): baja
los assets de datos de los releases, reconstruye datos/nexplay.db, entrena el
modelo de produccion y verifica que la API levante con esos artefactos.

Son dos cortes de datos distintos, cada uno con su tag y su sha256:
- el que sirve la API (SERVIDO_*): el catalogo completo, data-v2;
- el de entrenamiento (ENTRENAMIENTO_*): siempre data-v1, los 83 juegos con
  los que se valido el modelo. Los titulos que llegaron despues son prueba
  externa y no entran al entrenamiento (ver entrenar_modelo.py).

No usa la API publica de Steam (ingesta_steam.py) ni credenciales: el asset
de datos ya paso por esa ingesta una vez y se publico en un GitHub Release
con tag fijo (nunca "latest"), con su SHA-256 verificado antes de tocarlo -
mismo patron que notebook/nexplay.ipynb.

Ese asset es una copia sanitizada de datos/nexplay.db (ver
extracto_reproducible.py): mismas tablas 'juegos' y 'resenas' completas,
salvo la columna steamid de 'resenas', que no usa ni la API ni el
entrenamiento y no hay razon para redistribuir.

Requiere que las dependencias ya esten instaladas (ver README.md):
    pip install -r requirements.txt -r requirements-modelo.txt

Uso:
    python preparar_entorno.py            # no pisa datos/ ni modelo/ si ya existen
    python preparar_entorno.py --force    # reconstruye aunque ya existan
"""

import argparse
import json
import lzma
import subprocess
import sys
import time
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DB_PATH = RAIZ / "datos" / "nexplay.db"
MODELO_PATH = RAIZ / "modelo" / "nexplay.pkl"

# Releases con tag fijo, nunca "latest", para que este script siga funcionando
# igual dentro de un año. Cada sha256 es el del asset publicado en ese release
# (ver salida de extracto_reproducible.py): si se sube uno nuevo, va con un tag
# nuevo y su sha256 se actualiza aqui.
GITHUB_REPO = "fernandoaxelramirezgomez-coder/nexplay"
ASSET_NOMBRE = "nexplay_reproducible.db.xz"

SERVIDO_REF = "data-v2"
SERVIDO_SHA256 = "9d5a54f6cbb5f361e397eb043989e592cbff1d553c57ef8a41aae41e2c763d72"

ENTRENAMIENTO_REF = "data-v1"
ENTRENAMIENTO_SHA256 = "2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7"
ENTRENAMIENTO_DB_PATH = RAIZ / "datos" / "entrenamiento" / f"nexplay_{ENTRENAMIENTO_REF}.db"

PUERTO_PRUEBA_API = 8321
TIMEOUT_RED = 60


def _verificar_dependencias() -> None:
    faltantes = []
    for paquete in ("fastapi", "uvicorn", "pydantic", "numpy", "pandas", "sklearn"):
        try:
            __import__(paquete)
        except ImportError:
            faltantes.append(paquete)
    if faltantes:
        print(f"Faltan dependencias: {', '.join(faltantes)}")
        print("Instala primero:")
        print("    pip install -r requirements.txt -r requirements-modelo.txt")
        sys.exit(1)


def _descargar(ref: str, sha256_esperado: str, destino: Path, forzar: bool) -> None:
    """Baja el asset de un release, verifica su sha256 antes de tocar nada y lo
    descomprime en destino."""
    if destino.exists() and not forzar:
        print(f"{destino} ya existe, no se reconstruye (usa --force para pisarla).")
        return

    url = f"https://github.com/{GITHUB_REPO}/releases/download/{ref}/{ASSET_NOMBRE}"
    print(f"descargando {url} ...")
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_RED) as resp:
            comprimido = resp.read()
    except urllib.error.URLError as exc:
        print(f"no se pudo descargar el asset del release {ref}: {exc}")
        sys.exit(1)

    checksum = sha256(comprimido).hexdigest()
    if checksum != sha256_esperado:
        print(
            f"SHA-256 de {ref} no coincide: esperado {sha256_esperado}, obtenido {checksum}. "
            "El asset del release pudo cambiar o la descarga se corrompió; no seguir sin verificarlo."
        )
        sys.exit(1)
    print(f"descarga verificada ({ref}): {len(comprimido) / (1024 * 1024):.1f} MB, sha256 OK")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(lzma.decompress(comprimido))
    print(f"{destino} reconstruida ({destino.stat().st_size / (1024 * 1024):.1f} MB)")


def _base_de_entrenamiento(forzar: bool) -> Path:
    """Si el corte que se sirve es el mismo que el de entrenamiento, se entrena
    sobre datos/nexplay.db y no se descarga dos veces."""
    if ENTRENAMIENTO_REF == SERVIDO_REF:
        return DB_PATH
    _descargar(ENTRENAMIENTO_REF, ENTRENAMIENTO_SHA256, ENTRENAMIENTO_DB_PATH, forzar)
    return ENTRENAMIENTO_DB_PATH


def _entrenar_modelo(base: Path, forzar: bool) -> None:
    if MODELO_PATH.exists() and not forzar:
        print(f"{MODELO_PATH} ya existe, no se reentrena (usa --force para pisarlo).")
        return

    print(f"entrenando el modelo de producción con {ENTRENAMIENTO_REF} (entrenar_modelo.py) ...")
    resultado = subprocess.run(
        [
            sys.executable, str(RAIZ / "modelado" / "entrenar_modelo.py"),
            "--db", str(base),
            "--tag-datos", ENTRENAMIENTO_REF,
            "--sha256-asset", ENTRENAMIENTO_SHA256,
        ],
        cwd=RAIZ,
    )
    if resultado.returncode != 0:
        print("entrenar_modelo.py falló; revisa el traceback arriba.")
        sys.exit(1)


def _verificar_api() -> None:
    print(f"levantando la API en el puerto {PUERTO_PRUEBA_API} para verificarla ...")
    proceso = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "api.main:app",
            "--port", str(PUERTO_PRUEBA_API), "--log-level", "warning",
        ],
        cwd=RAIZ,
    )
    try:
        url = f"http://127.0.0.1:{PUERTO_PRUEBA_API}/catalogo"
        ultimo_error = None
        for _ in range(30):
            if proceso.poll() is not None:
                print("la API se cayó al arrancar; revisa el traceback arriba.")
                sys.exit(1)
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        juegos = json.loads(resp.read())
                        print(f"API responde OK: {len(juegos)} juegos en el catálogo.")
                        return
            except (urllib.error.URLError, ConnectionError) as exc:
                ultimo_error = exc
                time.sleep(1)
        print(f"la API no respondió a tiempo en {url}: {ultimo_error}")
        sys.exit(1)
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description="Prepara un entorno NexPlay limpio de punta a punta")
    parser.add_argument("--force", action="store_true", help="reconstruye datos/ y modelo/ aunque ya existan")
    args = parser.parse_args()

    _verificar_dependencias()
    _descargar(SERVIDO_REF, SERVIDO_SHA256, DB_PATH, args.force)
    base = _base_de_entrenamiento(args.force)
    _entrenar_modelo(base, args.force)
    _verificar_api()

    print()
    print("Entorno listo. Para levantar el proyecto:")
    print("    uvicorn api.main:app --reload")
    print("    cd frontend && npx ng serve   # en otra terminal")


if __name__ == "__main__":
    main()
