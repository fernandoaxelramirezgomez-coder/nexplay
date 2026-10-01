"""¿Cuántas veces más señal hay en riesgo alto que en riesgo bajo, y en qué juegos?

El Inicio dice que los juegos de riesgo alto tienen «4.2×» más reseñas con señal de
arrepentimiento temprano (Y=1: menos de 120 minutos jugados y voto negativo) que los de
riesgo bajo. Esa cifra sale de los 123 juegos del catálogo, y en 83 de ellos la señal fue
la etiqueta con la que se entrenó el modelo: ahí el cociente describe, no evalúa.

Este script calcula el mismo cociente en tres cortes —los 123, los 83 de data-v1 y los 40
que el modelo nunca vio— con los juegos y las reseñas con señal de cada nivel. Para los
cortes chicos agrega un intervalo por remuestreo de juegos (bootstrap dentro de cada
nivel, 2,000 repeticiones, semilla fija): con 13 juegos por nivel, un juego con muchas
reseñas mueve la cifra.

Solo lee: datos/nexplay.db y docs/evidencia/prueba-externa.json (los 40 externos). Los
niveles salen del mismo camino que sirve la API (api.catalogo).

Uso:
  python calidad/senal_por_nivel.py > ../docs/evidencia/senal-por-nivel.txt   # desde backend/
"""

import json
import random
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from api import catalogo  # noqa: E402

_DB = RAIZ / "datos" / "nexplay.db"
_EXTERNOS = RAIZ.parent / "docs" / "evidencia" / "prueba-externa.json"
_BANDAS = ("bajo", "medio", "alto")
_REPETICIONES = 2000
_SEMILLA = 42


def _conteos_por_appid() -> dict[int, tuple[int, int]]:
    """Reseñas descargadas y reseñas con señal (Y=1) de cada juego."""
    con = sqlite3.connect(f"file:{_DB}?mode=ro", uri=True)
    try:
        filas = con.execute(
            "SELECT appid, COUNT(*),"
            " SUM(CASE WHEN playtime_at_review < 120 AND voted_up = 0 THEN 1 ELSE 0 END)"
            " FROM resenas GROUP BY appid"
        ).fetchall()
    finally:
        con.close()
    return {appid: (total, senal or 0) for appid, total, senal in filas}


def _tasa(juegos: list[tuple[int, int]]) -> float:
    resenas = sum(r for r, _ in juegos)
    return sum(s for _, s in juegos) / resenas if resenas else 0.0


def _intervalo(bajo: list[tuple[int, int]], alto: list[tuple[int, int]]) -> tuple[float, float]:
    """Intervalo del 95 % del cociente alto/bajo, remuestreando juegos en cada nivel."""
    azar = random.Random(_SEMILLA)
    cocientes = []
    for _ in range(_REPETICIONES):
        b = _tasa([azar.choice(bajo) for _ in bajo])
        a = _tasa([azar.choice(alto) for _ in alto])
        if b:
            cocientes.append(a / b)
    cocientes.sort()
    return cocientes[int(0.025 * len(cocientes))], cocientes[int(0.975 * len(cocientes)) - 1]


def main() -> int:
    externos = {j["appid"] for j in json.loads(_EXTERNOS.read_text(encoding="utf-8"))["por_titulo"]}
    conteos = _conteos_por_appid()
    juegos = catalogo.buscar()

    cortes = {
        "catálogo (123)": [j for j in juegos],
        "data-v1 (83)": [j for j in juegos if j.appid not in externos],
        "externos (40)": [j for j in juegos if j.appid in externos],
    }
    resultados = {}
    for nombre, corte in cortes.items():
        por_banda = {b: [conteos[j.appid] for j in corte if j.banda_riesgo.value == b and j.appid in conteos] for b in _BANDAS}
        print(f"===== {nombre}")
        print(f"{'nivel':6} {'juegos':>6} {'reseñas':>9} {'con señal':>10} {'señal':>7}")
        for banda in _BANDAS:
            filas = por_banda[banda]
            print(
                f"{banda:6} {len(filas):>6} {sum(r for r, _ in filas):>9,} {sum(s for _, s in filas):>10,}"
                f" {_tasa(filas):>6.2%}"
            )
        cociente = _tasa(por_banda["alto"]) / _tasa(por_banda["bajo"])
        bajo_ic, alto_ic = _intervalo(por_banda["bajo"], por_banda["alto"])
        print(f"cociente alto/bajo: {cociente:.2f}×  (intervalo 95 % por juegos: {bajo_ic:.2f}× a {alto_ic:.2f}×)\n")
        resultados[nombre] = cociente

    ext = resultados["externos (40)"]
    decision = "clara (2× o más)" if ext >= 2 else "menor que 2×"
    print(f"En los 40 que el modelo nunca vio el cociente es {ext:.2f}×: {decision}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
