"""Entrena el modelo final que sirve api/scoring.py: conjunto 'compra'
(lado del jugador declarado en el formulario + lado del juego, nada
post-compra), ajustado sobre TODOS los datos.

La generalización a juegos nuevos ya se midió con GroupKFold en
entrenar_baseline.py; este script no repite esa validación de PR-AUC, pero
sí corre un GroupKFold para obtener predicciones out-of-fold: son la base
para calibrar los cortes bajo/medio/alto (tercios de la distribución real
de scores, no valores de probabilidad fijos — con prevalencia 2.19% un
umbral fijo como 0.66 puede ser inalcanzable).

Uso:
    python entrenar_modelo.py
"""

import pickle
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from entrenar_baseline import N_SPLITS, SEMILLA, cargar_datos, construir_features

MODELO_PATH = Path(__file__).resolve().parent / "modelo" / "nexplay.pkl"
VERSION_MODELO = f"logreg-compra-{date.today().isoformat()}"


def _construir_pipeline() -> Pipeline:
    return Pipeline([
        ("escalar", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEMILLA)),
    ])


def _scores_oof(X, y, grupos) -> np.ndarray:
    """Predicciones out-of-fold (cada fila puntuada por un modelo que no la
    vio en entrenamiento) para calibrar los cortes de riesgo sobre una
    distribución de validación, no sobre el ajuste optimista in-sample."""
    gkf = GroupKFold(n_splits=N_SPLITS)
    oof = np.zeros(len(X))
    for idx_train, idx_val in gkf.split(X, y, groups=grupos):
        pipeline = _construir_pipeline()
        pipeline.fit(X.iloc[idx_train], y.iloc[idx_train])
        oof[idx_val] = pipeline.predict_proba(X.iloc[idx_val])[:, 1]
    return oof


def main():
    df = cargar_datos()
    X, y, grupos = construir_features(df, conjunto="compra")
    mediana_metacritic = df["metacritic"].median()

    oof = _scores_oof(X, y, grupos)
    umbral_medio = float(np.percentile(oof, 100 / 3))
    umbral_alto = float(np.percentile(oof, 200 / 3))

    pipeline = _construir_pipeline()
    pipeline.fit(X, y)

    artefacto = {
        "pipeline": pipeline,
        "features": list(X.columns),
        "version": VERSION_MODELO,
        "mediana_metacritic": mediana_metacritic,
        "umbral_medio": umbral_medio,
        "umbral_alto": umbral_alto,
    }

    MODELO_PATH.parent.mkdir(exist_ok=True)
    with open(MODELO_PATH, "wb") as f:
        pickle.dump(artefacto, f)

    print(f"modelo guardado en {MODELO_PATH}")
    print(f"version={VERSION_MODELO}")
    print(f"features={artefacto['features']}")
    print(f"n={len(df)}  prevalencia={y.mean():.4f}")
    print(f"umbral_medio={umbral_medio:.4f}  umbral_alto={umbral_alto:.4f}  (tercios de scores OOF)")


if __name__ == "__main__":
    main()
