"""
NexPlay - Prepara un entorno limpio de punta a punta
=====================================================

Para que el proyecto completo sea reproducible (no solo el notebook): baja
los assets de datos de los releases, reconstruye datos/nexplay.db, entrena el
modelo de produccion y verifica que la API levante con esos artefactos.

Son dos cortes de datos distintos, cada uno con su tag y su sha256:
- el que sirve la API (SERVIDO_*): el catalogo completo, data-v3 (los mismos
  123 juegos y reseñas de data-v2, mas los totales publicos de Steam);
- el de entrenamiento (ENTRENAMIENTO_*): siempre data-v1, los 83 juegos con
  los que se valido el modelo. Los titulos que llegaron despues son prueba
  externa y no entran al entrenamiento (ver entrenar_modelo.py).

No usa la API publica de Steam (ingesta_steam.py) ni credenciales: el asset
de datos ya paso por esa ingesta una vez y se publico en un GitHub Release
con tag fijo (nunca "latest"), con su SHA-256 verificado antes de tocarlo -
mismo patron que notebooks/01_modelo_riesgo.ipynb.

Ese asset es una copia sanitizada de datos/nexplay.db (ver
extracto_reproducible.py): mismas tablas 'juegos', 'resenas' y
'resumen_resenas' completas, salvo la columna steamid de 'resenas', que no
usa ni la API ni el entrenamiento y no hay razon para redistribuir.

Requiere que las dependencias ya esten instaladas (ver README.md):
    pip install -r requirements.txt -r requirements-modelo.txt

Uso:
    python preparar_entorno.py            # no pisa datos/ ni modelo/ si ya existen
    python preparar_entorno.py --force    # reconstruye aunque ya existan
    python preparar_entorno.py --solo-datos   # solo baja y verifica los releases (make data)

--force solo pisa una base que salio de un release: la reconoce por su sha256, contra
la marca que este script deja al escribirla (<base>.origen.json) o contra las bases
publicadas (BASES_DE_RELEASE). Cualquier otra, como la base original de la ingesta, la
deja como esta, se detiene y explica por que.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# Corre desde despliegue/, así que la raíz no está en sys.path y `despliegue.utilidades` no se encontraría.
sys.path.insert(0, str(RAIZ))

from despliegue.utilidades import ErrorDeRelease, descargar_verificado  # noqa: E402

DB_PATH = RAIZ / "datos" / "nexplay.db"
MODELO_PATH = RAIZ / "modelo" / "nexplay.pkl"

# Releases con tag fijo, nunca "latest", para que este script siga funcionando
# igual dentro de un año. Cada sha256 es el del asset publicado en ese release
# (ver salida de extracto_reproducible.py): si se sube uno nuevo, va con un tag
# nuevo y su sha256 se actualiza aqui.
SERVIDO_REF = "data-v3"
SERVIDO_SHA256 = "44f6704d469a8f59683be8e28429108b7a88a06ee01aecdb21da94d90077dfb8"

ENTRENAMIENTO_REF = "data-v1"
ENTRENAMIENTO_SHA256 = "2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7"
ENTRENAMIENTO_DB_PATH = RAIZ / "datos" / "entrenamiento" / f"nexplay_{ENTRENAMIENTO_REF}.db"

# sha256 de cada base ya descomprimida, tal como la deja descargar_verificado. Con esto
# --force reconoce una base de release que no tiene su marca (las de antes de la marca).
# Si se publica un release nuevo, su base entra aqui junto con su SERVIDO_SHA256.
BASES_DE_RELEASE = {
    "2f031cf37a2d6a2db9ad4701531e50dda8db0b7138bf5a8e0c544533e70cc65e": "data-v3",
    "6eff5dbc5c5d0a5bde03272146d74a3047a38ab6c07acfdb633e39a735097fb8": "data-v1",
}

PUERTO_PRUEBA_API = 8321


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


def _sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _marca(destino: Path) -> Path:
    return destino.with_name(f"{destino.name}.origen.json")


def origen_de_release(destino: Path) -> str | None:
    """El tag del release del que salió la base, o None si no se reconoce.

    La marca solo cuenta si su sha256 sigue siendo el de la base: una base de release que
    después se modificó ya no es la del release."""
    sha = _sha256_archivo(destino)
    marca = _marca(destino)
    if marca.exists():
        try:
            datos = json.loads(marca.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        if datos.get("sha256_base") == sha:
            return datos.get("ref")
    return BASES_DE_RELEASE.get(sha)


def _explicar_por_que_no_se_pisa(destino: Path) -> str:
    return (
        f"No piso {destino}: no la reconozco como una base que haya salido de un release.\n"
        f"Su sha256 ({_sha256_archivo(destino)[:12]}…) no coincide con ninguna base publicada"
        f" ni con su marca {_marca(destino).name}.\n"
        "Puede ser la base original de la ingesta, que guarda lo que los releases quitan a"
        " propósito (la columna steamid y la tabla progreso); eso no se recupera de un release.\n"
        f"Si de verdad quieres reemplazarla, respáldala o muévela primero (por ejemplo, a"
        f" {destino.name}.respaldo) y vuelve a correr con --force."
    )


def _descargar(ref: str, sha256_esperado: str, destino: Path, forzar: bool) -> None:
    """Baja el asset de un release, verifica su sha256 antes de tocar nada y lo
    descomprime en destino. Con --force solo pisa una base que salió de un release."""
    if destino.exists():
        if not forzar:
            print(f"{destino} ya existe, no se reconstruye (usa --force para pisarla).")
            return
        if origen_de_release(destino) is None:
            print(_explicar_por_que_no_se_pisa(destino))
            sys.exit(1)
    try:
        descargar_verificado(ref, sha256_esperado, destino)
    except ErrorDeRelease as exc:
        print(exc)
        sys.exit(1)
    _marca(destino).write_text(
        json.dumps({"ref": ref, "sha256_asset": sha256_esperado, "sha256_base": _sha256_archivo(destino)}, indent=1),
        encoding="utf-8",
    )


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
    parser.add_argument("--solo-datos", action="store_true",
                        help="solo baja y verifica los releases: no entrena ni levanta la API")
    args = parser.parse_args()

    _verificar_dependencias()
    _descargar(SERVIDO_REF, SERVIDO_SHA256, DB_PATH, args.force)
    base = _base_de_entrenamiento(args.force)
    if args.solo_datos:
        print()
        print(f"Datos listos: {DB_PATH.relative_to(RAIZ)} ({SERVIDO_REF}) y {base.relative_to(RAIZ)} ({ENTRENAMIENTO_REF}).")
        print("Para entrenar el modelo: make train, desde la raíz del repo.")
        return
    _entrenar_modelo(base, args.force)
    _verificar_api()

    print()
    print("Entorno listo. Para levantar el proyecto:")
    print("    uvicorn api.main:app --reload            # desde backend/")
    print("    cd ../frontend && npx ng serve   # en otra terminal")


if __name__ == "__main__":
    main()
