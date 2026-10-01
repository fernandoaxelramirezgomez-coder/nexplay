"""Comprueba que `preparar_entorno.py --force` solo pise bases que salieron de un release.

El 2026-09-30, un --force en la raíz reemplazó la base original de la ingesta por data-v3 y
se perdieron la columna steamid y la tabla progreso. Desde entonces el script reconoce la
base por su sha256 (contra su marca .origen.json o contra BASES_DE_RELEASE) y, si no la
reconoce, se detiene sin tocarla.

Todo corre en un directorio temporal y sin red: la descarga se sustituye por una que
escribe bytes fijos. Al final revisa, solo leyendo, que las bases locales de datos/ se
reconozcan como lo que son.

Uso:
  python calidad/verificar_preparar_entorno.py      sale 1 si algo falla
"""

import contextlib
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from despliegue import preparar_entorno as pe  # noqa: E402

CONTENIDO_DEL_RELEASE = b"base de release de prueba"


class _Descarga:
    """Sustituye a descargar_verificado: cuenta las llamadas y escribe bytes fijos."""

    def __init__(self) -> None:
        self.llamadas = 0

    def __call__(self, ref: str, sha256_esperado: str, destino: Path) -> Path:
        self.llamadas += 1
        Path(destino).write_bytes(CONTENIDO_DEL_RELEASE)
        return Path(destino)


def _sha(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _base_de_ingesta(ruta: Path) -> None:
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE resenas (recommendationid TEXT, steamid TEXT)")
    con.execute("CREATE TABLE progreso (appid INTEGER, cursor TEXT)")
    con.execute("INSERT INTO resenas VALUES ('1', '76561198000000000')")
    con.commit()
    con.close()


def _correr(destino: Path, forzar: bool) -> tuple[int | None, str, int]:
    """Llama a _descargar y devuelve (código de salida o None, lo impreso, descargas)."""
    descarga = _Descarga()
    pe.descargar_verificado = descarga
    salida = io.StringIO()
    codigo = None
    with contextlib.redirect_stdout(salida):
        try:
            pe._descargar("data-prueba", "0" * 64, destino, forzar)
        except SystemExit as exc:
            codigo = exc.code
    return codigo, salida.getvalue(), descarga.llamadas


def _casos(carpeta: Path) -> list[str]:
    problemas = []
    marca_de = pe._marca

    # 1. La base de la ingesta no se pisa: sale con 1, explica por qué y no descarga.
    base = carpeta / "ingesta.db"
    _base_de_ingesta(base)
    antes = _sha(base)
    codigo, texto, descargas = _correr(base, forzar=True)
    if codigo != 1 or descargas or _sha(base) != antes:
        problemas.append(f"1 · la base de la ingesta se tocó (salida {codigo}, descargas {descargas})")
    if "No piso" not in texto or "steamid" not in texto or "respáldala" not in texto:
        problemas.append(f"1 · no explica por qué no la pisa: {texto!r}")

    # 2. Sin --force nada se pisa, aunque no se reconozca.
    antes = _sha(base)
    codigo, texto, descargas = _correr(base, forzar=False)
    if codigo is not None or descargas or _sha(base) != antes:
        problemas.append("2 · sin --force tocó una base existente")

    # 3. Una base publicada (sha en BASES_DE_RELEASE) sí se pisa y queda con su marca.
    publicada = carpeta / "publicada.db"
    publicada.write_bytes(b"base publicada, sin marca")
    pe.BASES_DE_RELEASE[_sha(publicada)] = "data-prueba-anterior"
    codigo, _, descargas = _correr(publicada, forzar=True)
    marca = marca_de(publicada)
    if codigo is not None or descargas != 1 or publicada.read_bytes() != CONTENIDO_DEL_RELEASE:
        problemas.append(f"3 · no pisó una base publicada (salida {codigo}, descargas {descargas})")
    elif not marca.exists() or json.loads(marca.read_text())["sha256_base"] != _sha(publicada):
        problemas.append("3 · después de escribir, la base no quedó con su marca")

    # 4. Con su marca vigente se vuelve a pisar (así se reconocen los releases futuros).
    codigo, _, descargas = _correr(publicada, forzar=True)
    if codigo is not None or descargas != 1:
        problemas.append(f"4 · no reconoció la base por su marca (salida {codigo})")

    # 5. Si la base cambió después de su marca, ya no es la del release: no se pisa.
    publicada.write_bytes(CONTENIDO_DEL_RELEASE + b" y algo agregado a mano")
    antes = _sha(publicada)
    codigo, texto, descargas = _correr(publicada, forzar=True)
    if codigo != 1 or descargas or _sha(publicada) != antes:
        problemas.append(f"5 · pisó una base modificada después de su marca (salida {codigo})")

    # 6. Una marca ilegible no vale como marca.
    marca.write_text("{no es json", encoding="utf-8")
    codigo, _, descargas = _correr(publicada, forzar=True)
    if codigo != 1 or descargas:
        problemas.append("6 · una marca ilegible dejó pisar la base")

    # 7. Si la base no existe, se baja y queda marcada.
    nueva = carpeta / "sub" / "nueva.db"
    nueva.parent.mkdir()
    codigo, _, descargas = _correr(nueva, forzar=True)
    if codigo is not None or descargas != 1 or not marca_de(nueva).exists():
        problemas.append("7 · no bajó ni marcó una base que no existía")
    return problemas


def _bases_locales() -> list[str]:
    """Solo lectura: las bases de datos/ se reconocen como lo que son."""
    problemas = []
    esperados = {
        RAIZ / "datos" / "nexplay.db": "data-v3",
        pe.ENTRENAMIENTO_DB_PATH: "data-v1",
        RAIZ / "datos" / "nexplay.db.respaldo-20260920-1914": None,
    }
    for ruta, esperado in esperados.items():
        if not ruta.exists():
            print(f"local:    {ruta.relative_to(RAIZ)} no existe aquí; no se revisa")
            continue
        origen = pe.origen_de_release(ruta)
        if origen != esperado:
            problemas.append(f"local · {ruta.relative_to(RAIZ)} se reconoce como {origen!r}, se esperaba {esperado!r}")
        else:
            como = f"release {origen}" if origen else "no reconocida: --force no la pisaría"
            print(f"local:    {ruta.relative_to(RAIZ)} → {como}")
    return problemas


def main() -> int:
    bases_originales = dict(pe.BASES_DE_RELEASE)
    descarga_original = pe.descargar_verificado
    try:
        with tempfile.TemporaryDirectory(prefix="nexplay-preparar-") as carpeta:
            problemas = _casos(Path(carpeta))
    finally:
        pe.BASES_DE_RELEASE.clear()
        pe.BASES_DE_RELEASE.update(bases_originales)
        pe.descargar_verificado = descarga_original
    if not problemas:
        print("casos:    la base de la ingesta y una modificada no se pisan; una publicada o con su marca sí,"
              " y queda marcada; sin --force nada se toca")
    problemas += _bases_locales()
    for problema in problemas:
        print(f"PROBLEMA: {problema}")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
