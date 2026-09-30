"""Bajar un asset de un release con tag fijo y verificar su sha256 antes de usarlo.

Lo usan preparar_entorno.py (el build de Render) y los notebooks. Aquí los errores
lanzan una excepción: el script la convierte en su código de salida y el notebook la muestra
tal cual, en vez de un SystemExit."""

import lzma
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path

GITHUB_REPO = "fernandoaxelramirezgomez-coder/nexplay"
ASSET_NOMBRE = "nexplay_reproducible.db.xz"
TIMEOUT_RED = 60


class ErrorDeRelease(Exception):
    """El asset no se pudo bajar o su sha256 no es el publicado."""


def descargar_verificado(ref: str, sha256_esperado: str, destino: Path, asset: str = ASSET_NOMBRE) -> Path:
    """Baja `asset` del release `ref`, verifica su sha256 antes de escribir nada y lo deja en
    `destino`, descomprimido si viene en .xz."""
    url = f"https://github.com/{GITHUB_REPO}/releases/download/{ref}/{asset}"
    print(f"descargando {url} ...")
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_RED) as resp:
            contenido = resp.read()
    except urllib.error.URLError as exc:
        raise ErrorDeRelease(f"no se pudo descargar el asset del release {ref}: {exc}") from exc

    checksum = sha256(contenido).hexdigest()
    if checksum != sha256_esperado:
        raise ErrorDeRelease(
            f"SHA-256 de {ref} no coincide: esperado {sha256_esperado}, obtenido {checksum}. "
            "El asset del release pudo cambiar o la descarga se corrompió; no seguir sin verificarlo."
        )
    print(f"descarga verificada ({ref}): {len(contenido) / (1024 * 1024):.1f} MB, sha256 OK")

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(lzma.decompress(contenido) if asset.endswith(".xz") else contenido)
    print(f"{destino} reconstruida ({destino.stat().st_size / (1024 * 1024):.1f} MB)")
    return destino
