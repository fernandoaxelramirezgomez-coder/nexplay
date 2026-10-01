"""¿La diferencia entre veteranos y novatos se sostiene dentro de cada juego?

En data-v1 los veteranos dejan más señal que los novatos (senal_por_biblioteca.py), pero se
concentran en juegos con más señal. Este script compara a los dos grupos dentro de cada juego:
razón de riesgos de Mantel-Haenszel, veteranos contra novatos, estratificada por appid. El
prerregistro está en docs/evidencia/senal-por-biblioteca.md, sección «Análisis estratificado
por juego», commiteado antes de la primera corrida.

- Datos y grupos: los de senal_por_biblioteca.py (data-v1, perfiles públicos; novatos de 1 a
  19 juegos y veteranos con 20 o más; señal: menos de 120 minutos y voto negativo).
- Por juego k, con a y n1 las señales y reseñas de veteranos, c y n0 las de novatos, y
  N = n1 + n0:
  RR_MH = Σ a·n0/N / Σ c·n1/N.
  Solo aportan los juegos con reseñas de los dos grupos.
- IC 95 %: bootstrap sobre appid (2,000 réplicas con reemplazo, semilla 42). Una réplica sin
  señales de novatos en sus juegos informativos tiene razón infinita: se cuenta, y entra al
  percentil como +∞ sin interpolar (numpy, method="inverted_cdf").
- Regla, fijada antes de correr: si el IC queda completo por encima de 1, la diferencia se
  sostiene dentro de cada juego; si cruza el 1, parte de ella puede venir de qué juegos compra
  cada grupo. Si quedara completo por debajo de 1, se reporta antes de escribir ninguna frase.

Uso:
  python calidad/senal_por_biblioteca_estratificada.py [--cache DIR]   # desde backend/
"""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "calidad")]

from senal_por_biblioteca import NOVATO_HASTA, RELEASE, REPLICAS, SEMILLA, SHA256, resenas_publicas  # noqa: E402

SALIDA = RAIZ.parent / "docs" / "evidencia" / "senal-por-biblioteca-estratificada.json"
FRASES = {
    "encima": "La diferencia se sostiene dentro de cada juego.",
    "cruza": "Parte de la diferencia puede venir de qué juegos compra cada grupo.",
}


def razon_mh(a, n1, c, n0, pesos) -> float:
    total = n1 + n0
    informativo = (n1 > 0) & (n0 > 0)
    numerador = (pesos * np.where(informativo, a * n0 / np.where(informativo, total, 1), 0)).sum()
    denominador = (pesos * np.where(informativo, c * n1 / np.where(informativo, total, 1), 0)).sum()
    return np.inf if denominador == 0 else numerador / denominador


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "nexplay-releases",
                        help="dónde dejar el release descargado")
    args = parser.parse_args()

    df, _ = resenas_publicas(args.cache)
    df["grupo"] = np.where(df["num_games_owned"] <= NOVATO_HASTA, "novatos", "veteranos")
    tabla = df.groupby(["appid", "grupo"])["senal"].agg(["size", "sum"]).unstack(fill_value=0)
    n1, a = tabla[("size", "veteranos")].to_numpy(float), tabla[("sum", "veteranos")].to_numpy(float)
    n0, c = tabla[("size", "novatos")].to_numpy(float), tabla[("sum", "novatos")].to_numpy(float)
    juegos = len(tabla)
    informativo = (n1 > 0) & (n0 > 0)

    punto = razon_mh(a, n1, c, n0, np.ones(juegos))
    cruda = (a.sum() / n1.sum()) / (c.sum() / n0.sum())

    rng = np.random.default_rng(SEMILLA)
    replicas = np.array([
        razon_mh(a, n1, c, n0, np.bincount(rng.integers(0, juegos, juegos), minlength=juegos).astype(float))
        for _ in range(REPLICAS)
    ])
    ic95 = [float(v) for v in np.percentile(replicas, [2.5, 97.5], method="inverted_cdf")]
    if ic95[0] > 1:
        lectura, frase = "encima", FRASES["encima"]
    elif ic95[1] < 1:
        lectura, frase = "debajo", None
    else:
        lectura, frase = "cruza", FRASES["cruza"]

    resultado = {
        "generado": date.today().isoformat(),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                                 text=True).stdout.strip(),
        "release": {RELEASE: SHA256},
        "definicion": f"data-v1, perfiles públicos; novatos: 1 a {NOVATO_HASTA} juegos; veteranos: {NOVATO_HASTA + 1} o más",
        "metodo": "razón de riesgos de Mantel-Haenszel, veteranos contra novatos, estratificada por appid",
        "juegos": juegos,
        "juegos_informativos": int(informativo.sum()),
        "juegos_informativos_con_senal": int((informativo & ((a + c) > 0)).sum()),
        "senales_en_informativos": {"veteranos": int(a[informativo].sum()), "novatos": int(c[informativo].sum())},
        "razon_cruda_por_resena": round(float(cruda), 3),
        "razon_mh": round(float(punto), 3),
        "bootstrap": {"replicas": REPLICAS, "semilla": SEMILLA, "unidad": "juego (appid), con reemplazo",
                      "percentil": "numpy inverted_cdf (sin interpolar)",
                      "ic95_razon_mh": [round(v, 3) if np.isfinite(v) else "inf" for v in ic95],
                      "replicas_infinitas": int(np.isinf(replicas).sum())},
        "regla": {"encima": FRASES["encima"], "cruza": FRASES["cruza"],
                  "debajo": "se reporta antes de escribir ninguna frase"},
        "lectura": lectura,
        "frase": frase,
    }
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"juegos: {juegos}; informativos (con reseñas de los dos grupos): {int(informativo.sum())}; "
          f"de esos, con alguna señal: {resultado['juegos_informativos_con_senal']}")
    print(f"razón cruda por reseña: {cruda:.2f} · Mantel-Haenszel por juego: {punto:.2f}, "
          f"IC 95 % [{ic95[0]:.2f}, {ic95[1]:.2f}] ({resultado['bootstrap']['replicas_infinitas']} réplicas infinitas)")
    print(f"lectura: {lectura} → {frase or 'reportar antes de escribir ninguna frase'}")
    print(f"guardado en {SALIDA.relative_to(RAIZ.parent)}")


if __name__ == "__main__":
    main()
