"""
NexPlay - Prepara un entorno limpio de punta a punta
=====================================================

Para que el proyecto completo sea reproducible (no solo el notebook): baja
el asset de datos del release, reconstruye datos/nexplay.db, entrena el
modelo de produccion y verifica que la API levante con esos artefactos.

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

RAIZ = Path(__file__).resolve().parent
DB_PATH = RAIZ / "datos" / "nexplay.db"
MODELO_PATH = RAIZ / "modelo" / "nexplay.pkl"

# Mismo repo/tag que notebook/nexplay.ipynb: un release con tag fijo, nunca
# "latest", para que este script siga funcionando igual dentro de un año.
GITHUB_REPO = "fernandoaxelramirezgomez-coder/nexplay"
GITHUB_REF = "data-v2"
ASSET_NOMBRE = "nexplay_reproducible.db.xz"
ASSET_URL = f"https://github.com/{GITHUB_REPO}/releases/download/{GITHUB_REF}/{ASSET_NOMBRE}"
# sha256 real del asset publicado en ese release (ver salida de
# extracto_reproducible.py). Si se regenera el asset y se sube uno nuevo,
# este valor tiene que actualizarse junto con el.
ASSET_SHA256 = "9d5a54f6cbb5f361e397eb043989e592cbff1d553c57ef8a41aae41e2c763d72"

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


def _descargar_y_reconstruir_db(forzar: bool) -> None:
    if DB_PATH.exists() and not forzar:
        print(f"{DB_PATH} ya existe, no se reconstruye (usa --force para pisarla).")
        return

    print(f"descargando {ASSET_URL} ...")
    try:
        with urllib.request.urlopen(ASSET_URL, timeout=TIMEOUT_RED) as resp:
            comprimido = resp.read()
    except urllib.error.URLError as exc:
        print(f"no se pudo descargar el asset del release: {exc}")
        sys.exit(1)

    checksum = sha256(comprimido).hexdigest()
    if checksum != ASSET_SHA256:
        print(
            f"SHA-256 no coincide: esperado {ASSET_SHA256}, obtenido {checksum}. "
            "El asset del release pudo cambiar o la descarga se corrompió; no seguir sin verificarlo."
        )
        sys.exit(1)
    print(f"descarga verificada: {len(comprimido) / (1024 * 1024):.1f} MB, sha256 OK")

    DB_PATH.parent.mkdir(exist_ok=True)
    DB_PATH.write_bytes(lzma.decompress(comprimido))
    print(f"{DB_PATH} reconstruida ({DB_PATH.stat().st_size / (1024 * 1024):.1f} MB)")


def _entrenar_modelo(forzar: bool) -> None:
    if MODELO_PATH.exists() and not forzar:
        print(f"{MODELO_PATH} ya existe, no se reentrena (usa --force para pisarlo).")
        return

    print("entrenando el modelo de producción (entrenar_modelo.py) ...")
    resultado = subprocess.run([sys.executable, str(RAIZ / "entrenar_modelo.py")], cwd=RAIZ)
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
    _descargar_y_reconstruir_db(args.force)
    _entrenar_modelo(args.force)
    _verificar_api()

    print()
    print("Entorno listo. Para levantar el proyecto:")
    print("    uvicorn api.main:app --reload")
    print("    python ui/app.py   # en otra terminal, con requirements-ui.txt instalado")


if __name__ == "__main__":
    main()
