"""¿Cuánto se mueve el resultado de la prueba externa si cambian los títulos?

En los 40 títulos de data-v2 que no están en data-v1, el modelo de título saca PR-AUC 0.0356
contra 0.0234 del clasificador trivial: 1.52 veces. Con 40 títulos, uno con muchas reseñas
mueve esa cifra. Este script calcula su intervalo.

Método:
- El modelo de producción se entrena en memoria con data-v1: mismas variables, mismo pipeline
  y la mediana de Metacritic de data-v1 para imputar, como la API. No lee ni escribe modelo/.
- 2,000 réplicas remuestreando los 40 títulos con reemplazo (semilla 42). Cada réplica junta
  todas las reseñas de los títulos elegidos.
- En cada réplica, PR-AUC entre la prevalencia de esa réplica, que es el PR-AUC del
  clasificador trivial.
- Intervalo percentil al 95 % (2.5 y 97.5).

Se remuestrean títulos y no reseñas: las reseñas de un mismo juego comparten precio, nota y
momento, así que no son independientes.

Antes del bootstrap comprueba que el punto coincida con docs/evidencia/prueba-externa.json.

Uso:
  python calidad/bootstrap_prueba_externa.py [--cache DIR]
"""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "modelado")]

from despliegue.utilidades import descargar_verificado  # noqa: E402
from entrenar_baseline import cargar_datos, construir_features, construir_pipeline  # noqa: E402

RELEASES = {
    "data-v1": "2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7",  # 83: entrenamiento
    "data-v2": "9d5a54f6cbb5f361e397eb043989e592cbff1d553c57ef8a41aae41e2c763d72",  # 123: de aquí salen los 40
}
REPLICAS = 2000
SEMILLA = 42
SALIDA = RAIZ / "docs" / "evidencia" / "bootstrap-prueba-externa.json"
PRUEBA_EXTERNA = RAIZ / "docs" / "evidencia" / "prueba-externa.json"


def puntuar_externos(cache: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """y, score y appid de cada reseña de los 40 títulos externos."""
    rutas = {ref: descargar_verificado(ref, sha, cache / f"nexplay_{ref}.db") for ref, sha in RELEASES.items()}
    entrenamiento = cargar_datos(rutas["data-v1"])
    X, y, _ = construir_features(entrenamiento, conjunto="juego")
    pipeline = construir_pipeline().fit(X, y)

    catalogo = cargar_datos(rutas["data-v2"])
    externos = catalogo[~catalogo["appid"].isin(set(entrenamiento["appid"]))].reset_index(drop=True)
    X_ext, y_ext, appids = construir_features(externos, conjunto="juego")
    # La mediana de data-v1 y no la de los externos: así imputa la API.
    X_ext["metacritic"] = externos["metacritic"].fillna(entrenamiento["metacritic"].median())
    scores = pipeline.predict_proba(X_ext[X.columns])[:, 1]
    return y_ext.to_numpy(), scores, appids.to_numpy()


def comprobar_punto(pr_auc: float, prevalencia: float, titulos: int) -> None:
    referencia = json.loads(PRUEBA_EXTERNA.read_text(encoding="utf-8"))["resumen"]
    esperado = (referencia["pr_auc_externo"], referencia["prevalencia"], referencia["titulos_nuevos"])
    obtenido = (pr_auc, prevalencia, titulos)
    if titulos != esperado[2] or abs(pr_auc - esperado[0]) > 1e-9 or abs(prevalencia - esperado[1]) > 1e-9:
        raise SystemExit(f"el punto no coincide con prueba-externa.json: esperado {esperado}, obtenido {obtenido}")


def remuestrear(y: np.ndarray, scores: np.ndarray, appids: np.ndarray) -> dict[str, np.ndarray]:
    titulos = np.unique(appids)
    filas_de = {appid: np.flatnonzero(appids == appid) for appid in titulos}
    rng = np.random.default_rng(SEMILLA)
    pr_aucs, prevalencias = np.empty(REPLICAS), np.empty(REPLICAS)
    for i in range(REPLICAS):
        filas = np.concatenate([filas_de[appid] for appid in rng.choice(titulos, size=len(titulos), replace=True)])
        y_replica = y[filas]
        if y_replica.sum() == 0:
            raise SystemExit(f"la réplica {i} no tiene positivos: el PR-AUC no está definido")
        pr_aucs[i] = average_precision_score(y_replica, scores[filas])
        prevalencias[i] = y_replica.mean()
    return {"pr_auc": pr_aucs, "prevalencia": prevalencias, "cociente": pr_aucs / prevalencias}


def _percentiles(valores: np.ndarray) -> list[float]:
    return [round(float(v), 4) for v in np.percentile(valores, [2.5, 97.5])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "nexplay-releases",
                        help="dónde dejar los releases descargados")
    args = parser.parse_args()

    y, scores, appids = puntuar_externos(args.cache)
    pr_auc, prevalencia = float(average_precision_score(y, scores)), float(y.mean())
    titulos = len(np.unique(appids))
    comprobar_punto(pr_auc, prevalencia, titulos)

    replicas = remuestrear(y, scores, appids)
    resultado = {
        "generado": date.today().isoformat(),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                                 text=True).stdout.strip(),
        "releases": RELEASES,
        "punto": {
            "titulos": titulos,
            "filas": int(len(y)),
            "positivos": int(y.sum()),
            "prevalencia": round(prevalencia, 6),
            "pr_auc": round(pr_auc, 6),
            "cociente": round(pr_auc / prevalencia, 4),
        },
        "bootstrap": {
            "replicas": REPLICAS,
            "semilla": SEMILLA,
            "unidad": "título (appid), con reemplazo; cada réplica junta todas sus reseñas",
            "estadistico": "PR-AUC de la réplica / prevalencia de la réplica (PR-AUC del trivial)",
            "ic95_cociente": _percentiles(replicas["cociente"]),
            "ic95_pr_auc": _percentiles(replicas["pr_auc"]),
            "ic95_prevalencia": _percentiles(replicas["prevalencia"]),
            "mediana_cociente": round(float(np.median(replicas["cociente"])), 4),
            "replicas_con_cociente_hasta_1": int((replicas["cociente"] <= 1).sum()),
        },
    }
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    b = resultado["bootstrap"]
    print(f"punto: PR-AUC {pr_auc:.4f} contra {prevalencia:.4f} del trivial = {pr_auc / prevalencia:.2f} veces "
          f"({titulos} títulos, {len(y):,} reseñas)")
    print(f"IC 95 % del cociente ({REPLICAS:,} réplicas por título, semilla {SEMILLA}): "
          f"{b['ic95_cociente'][0]:.2f} a {b['ic95_cociente'][1]:.2f}; mediana {b['mediana_cociente']:.2f}; "
          f"réplicas con cociente ≤ 1: {b['replicas_con_cociente_hasta_1']}")
    print(f"guardado en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
