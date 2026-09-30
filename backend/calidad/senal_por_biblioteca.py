"""¿Dejan más señal de arrepentimiento temprano los veteranos que los novatos?

El encuadre de NexPlay dice que los jugadores con biblioteca grande se arrepienten más que los
novatos: 1.34 % contra 0.45 %. Esa cifra no tenía fuente en el repo. Este script la reproduce
con su definición original, prerregistrada en docs/evidencia/senal-por-biblioteca.md antes de
correrlo, y después prueba su robustez con cuartiles.

Definición original:
- reseñas de data-v1 (83 juegos) con perfil público, num_games_owned > 0 (el 0 es bandera de
  privacidad, no biblioteca vacía);
- novatos, de 1 a 19 juegos; veteranos, 20 o más;
- señal: playtime_at_review < 120 y voted_up = 0.

Cada grupo se mide de dos formas: por reseña (señales entre reseñas del grupo) y como promedio
de las tasas por juego, donde cada juego pesa igual. La diferencia entre veteranos y novatos
lleva un IC 95 % por bootstrap sobre juegos (2,000 réplicas, semilla 42), porque las reseñas
de un mismo juego no son independientes.

Robustez: los cuartiles de num_games_owned en perfiles públicos. Q1 es hasta el percentil 25;
Q4, por encima del 75. Mismo bootstrap.

num_games_owned describe al autor cuando se descargó la reseña, no cuando compró el juego. Es
contexto del encuadre y no entra al modelo de título.

Uso:
  python calidad/senal_por_biblioteca.py [--cache DIR]
"""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "modelado")]

from despliegue.utilidades import descargar_verificado  # noqa: E402
from entrenar_baseline import cargar_datos  # noqa: E402

RELEASE = "data-v1"
SHA256 = "2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7"
NOVATO_HASTA = 19
# La cifra que se quiere reproducir: % por reseña, redondeado a dos decimales.
ESPERADO = {"novatos": 0.45, "veteranos": 1.34}
REPLICAS = 2000
SEMILLA = 42
SALIDA = RAIZ / "docs" / "evidencia" / "senal-por-biblioteca.json"


def resenas_publicas(cache: Path) -> tuple[pd.DataFrame, int]:
    df = cargar_datos(descargar_verificado(RELEASE, SHA256, cache / f"nexplay_{RELEASE}.db"))
    df["senal"] = ((df["playtime_at_review"] < 120) & (df["voted_up"] == 0)).astype(int)
    publicas = df[df["num_games_owned"] > 0].reset_index(drop=True)
    return publicas, len(df) - len(publicas)


def _conteos(df: pd.DataFrame, grupos: pd.Series, a: str, b: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Reseñas y señales de cada juego dentro de cada grupo, alineadas por juego."""
    tabla = df.assign(grupo=grupos).groupby(["appid", "grupo"])["senal"].agg(["size", "sum"]).unstack(fill_value=0)
    return {g: (tabla[("size", g)].to_numpy(float), tabla[("sum", g)].to_numpy(float)) for g in (a, b)}


def _tasas(conteos: dict, pesos: np.ndarray) -> dict[str, dict[str, float]]:
    """Por reseña y promedio por juego, con cada juego repetido según su peso en la réplica."""
    salida = {}
    for grupo, (n, s) in conteos.items():
        con_resenas = n > 0
        por_juego = np.divide(s, n, out=np.zeros_like(s), where=con_resenas)
        salida[grupo] = {
            "por_resena": (pesos * s).sum() / (pesos * n).sum(),
            "prom_juegos": (pesos * por_juego * con_resenas).sum() / (pesos * con_resenas).sum(),
        }
    return salida


def comparar(df: pd.DataFrame, grupos: pd.Series, a: str, b: str) -> dict:
    """b contra a: tasas de cada grupo y la diferencia b − a con su IC por bootstrap sobre juegos."""
    conteos = _conteos(df, grupos, a, b)
    juegos = len(conteos[a][0])
    punto = _tasas(conteos, np.ones(juegos))

    rng = np.random.default_rng(SEMILLA)
    diferencias = {"por_resena": [], "prom_juegos": []}
    for _ in range(REPLICAS):
        pesos = np.bincount(rng.integers(0, juegos, juegos), minlength=juegos).astype(float)
        replica = _tasas(conteos, pesos)
        for medida in diferencias:
            diferencias[medida].append(replica[b][medida] - replica[a][medida])

    def _grupo(g: str) -> dict:
        n, s = conteos[g]
        return {"resenas": int(n.sum()), "senales": int(s.sum()), "juegos": int((n > 0).sum()),
                "por_resena_pct": round(100 * punto[g]["por_resena"], 4),
                "prom_juegos_pct": round(100 * punto[g]["prom_juegos"], 4)}

    return {
        "grupos": {a: _grupo(a), b: _grupo(b)},
        "diferencia_pp": {
            medida: {"punto": round(100 * (punto[b][medida] - punto[a][medida]), 4),
                     "ic95": [round(100 * v, 4) for v in np.percentile(valores, [2.5, 97.5])]}
            for medida, valores in diferencias.items()
        },
        "cociente": {medida: round(punto[b][medida] / punto[a][medida], 3) for medida in ("por_resena", "prom_juegos")},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "nexplay-releases",
                        help="dónde dejar el release descargado")
    args = parser.parse_args()

    df, privadas = resenas_publicas(args.cache)
    original = comparar(df, np.where(df["num_games_owned"] <= NOVATO_HASTA, "novatos", "veteranos"),
                        "novatos", "veteranos")
    reproduce = all(round(original["grupos"][g]["por_resena_pct"], 2) == ESPERADO[g] for g in ESPERADO)

    q25, q75 = (float(v) for v in np.percentile(df["num_games_owned"], [25, 75]))
    extremos = df[(df["num_games_owned"] <= q25) | (df["num_games_owned"] > q75)].reset_index(drop=True)
    cuartiles = comparar(extremos, np.where(extremos["num_games_owned"] <= q25, "Q1", "Q4"), "Q1", "Q4")

    resultado = {
        "generado": date.today().isoformat(),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                                 text=True).stdout.strip(),
        "release": {RELEASE: SHA256},
        "resenas_publicas": int(len(df)),
        "resenas_privadas_excluidas": int(privadas),
        "bootstrap": {"replicas": REPLICAS, "semilla": SEMILLA, "unidad": "juego (appid), con reemplazo"},
        "original": {
            "definicion": f"novatos: 1 a {NOVATO_HASTA} juegos; veteranos: {NOVATO_HASTA + 1} o más (perfiles públicos)",
            "esperado_por_resena_pct": ESPERADO,
            "reproduce": reproduce,
            **original,
        },
        "robustez_cuartiles": {
            "definicion": "Q1: num_games_owned ≤ percentil 25; Q4: > percentil 75 (perfiles públicos, por reseña)",
            "cortes": {"p25": q25, "p75": q75},
            **cuartiles,
        },
    }
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for nombre, bloque, a, b in (("original", original, "novatos", "veteranos"), ("cuartiles", cuartiles, "Q1", "Q4")):
        ga, gb = bloque["grupos"][a], bloque["grupos"][b]
        print(f"[{nombre}] {a}: {ga['por_resena_pct']:.2f} % por reseña, {ga['prom_juegos_pct']:.2f} % promedio por juego "
              f"({ga['resenas']:,} reseñas) · {b}: {gb['por_resena_pct']:.2f} % / {gb['prom_juegos_pct']:.2f} % "
              f"({gb['resenas']:,} reseñas)")
        for medida, d in bloque["diferencia_pp"].items():
            print(f"    diferencia {b} − {a} ({medida}): {d['punto']:+.2f} pp, IC 95 % [{d['ic95'][0]:+.2f}, {d['ic95'][1]:+.2f}]")
    print(f"reproduce 0.45 % contra 1.34 %: {'sí' if reproduce else 'NO'} · cortes de los cuartiles: {q25:g} y {q75:g}")
    print(f"guardado en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
