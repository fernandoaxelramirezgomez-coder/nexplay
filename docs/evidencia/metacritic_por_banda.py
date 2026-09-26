"""¿La banda alta es solo "no tiene nota de Metacritic"?

33 de los 43 juegos de riesgo alto del catálogo no tienen nota, y en bajo y medio no hay
ninguno sin ella. Eso deja una duda razonable: si la cobertura de crítica arrastra la
banda, la banda no estaría diciendo nada más.

Este script cuenta la tasa real de arrepentimiento temprano (Y=1: menos de 120 minutos
jugados y voto negativo) por banda y por cobertura de crítica, separando los 83 títulos
con los que se entrenó el modelo (data-v1) de los 40 que nunca vio. Juntarlos mezcla lo
descriptivo con lo evaluativo: en los 83 el modelo ya conoce la respuesta.

Solo lee: datos/nexplay.db y docs/evidencia/prueba-externa.json, que es donde quedaron
anotados los 40 títulos externos. Las bandas salen del mismo camino que sirve la API
(api.catalogo -> scoring.prediccion_de_titulo).

Uso:
  python docs/evidencia/metacritic_por_banda.py > docs/evidencia/metacritic-por-banda.txt
"""

import json
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from api import catalogo  # noqa: E402

_DB = RAIZ / "datos" / "nexplay.db"
_EXTERNOS = RAIZ / "docs" / "evidencia" / "prueba-externa.json"
_BANDAS = ("bajo", "medio", "alto")


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


def _appids_externos() -> set[int]:
    datos = json.loads(_EXTERNOS.read_text(encoding="utf-8"))
    return {j["appid"] for j in datos["por_titulo"]}, datos["resumen"]


def main() -> int:
    externos, resumen_externo = _appids_externos()
    conteos = _conteos_por_appid()
    juegos = catalogo.buscar()

    # (corte, banda, con nota) -> [juegos, filas, señal]
    cubos: dict[tuple[str, str, bool], list[int]] = {}
    for juego in juegos:
        filas, senal = conteos.get(juego.appid, (0, 0))
        corte = "externos (40)" if juego.appid in externos else "data-v1 (83)"
        clave = (corte, juego.banda_riesgo.value, juego.metacritic is not None)
        cubo = cubos.setdefault(clave, [0, 0, 0])
        cubo[0] += 1
        cubo[1] += filas
        cubo[2] += senal

    for corte in ("data-v1 (83)", "externos (40)"):
        propios = {k: v for k, v in cubos.items() if k[0] == corte}
        print(f"\n===== {corte}")
        print(f"{'banda':6} {'cobertura':10} {'juegos':>7} {'reseñas':>9} {'con señal':>10} {'prevalencia':>12}")
        for banda in _BANDAS:
            for con_nota in (True, False):
                cubo = propios.get((corte, banda, con_nota))
                if not cubo:
                    continue
                cuantos, filas, senal = cubo
                etiqueta = "con nota" if con_nota else "sin nota"
                print(f"{banda:6} {etiqueta:10} {cuantos:7} {filas:9,} {senal:10,} {senal / filas:11.2%}")
        total = [sum(c[i] for c in propios.values()) for i in range(3)]
        print(f"{'total':6} {'':10} {total[0]:7} {total[1]:9,} {total[2]:10,} {total[2] / total[1]:11.2%}")

    # Cuadres contra lo ya publicado, para que la tabla no se sostenga sola.
    ext = [v for k, v in cubos.items() if k[0] == "externos (40)"]
    print(f"\ncuadre externos: {sum(c[0] for c in ext)} juegos (json: {resumen_externo['titulos_nuevos']}),"
          f" {sum(c[1] for c in ext):,} filas (json: {resumen_externo['filas']:,}),"
          f" {sum(c[2] for c in ext):,} con señal (json: {resumen_externo['positivos']:,})")
    altos_con_nota = sum(v[0] for k, v in cubos.items() if k[1] == "alto" and k[2])
    print(f"'alto con nota' en todo el catálogo: {altos_con_nota} juegos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
