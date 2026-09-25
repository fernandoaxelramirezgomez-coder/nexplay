"""Entrena el modelo final que sirve api/scoring.py: conjunto 'juego' (solo
el lado del juego: gratuidad, precio, descuento y cobertura/nota de crítica),
ajustado sobre TODOS los datos de entrenamiento.

Es un modelo de título: estima el riesgo del juego, igual para cualquier
persona. El lado del jugador (compras al año) aportaba ~2% del PR-AUC,
dentro del ruido entre folds, así que se deja fuera; el perfil declarado
sirve para afinidad, no mueve el riesgo.

Se entrena siempre con el mismo corte de datos (el release data-v1, 83
juegos), aunque el catálogo que sirve la API sea más grande: los títulos que
llegaron después quedan como prueba externa y nunca tocan el entrenamiento,
los umbrales ni la elección de variables. preparar_entorno.py baja ese asset,
verifica su sha256 y pasa la ruta, el tag y el sha256 a este script; todo eso
queda guardado en el artefacto.

La generalización a juegos nuevos ya se midió con GroupKFold en
entrenar_baseline.py; este script no repite esa validación de PR-AUC, pero
sí corre un GroupKFold para obtener predicciones out-of-fold: son la base
para calibrar los cortes bajo/medio/alto (tercios de la distribución real
de scores, no valores de probabilidad fijos — con prevalencia ~2% un
umbral fijo como 0.66 puede ser inalcanzable).

Uso:
    python entrenar_modelo.py --db datos/entrenamiento/nexplay_data-v1.db \\
        --tag-datos data-v1 --sha256-asset <sha256 del .xz del release>
"""

import argparse
import pickle
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold

from entrenar_baseline import N_SPLITS, cargar_datos, construir_features, construir_pipeline

MODELO_PATH = Path(__file__).resolve().parents[1] / "modelo" / "nexplay.pkl"
VERSION_MODELO = f"logreg-juego-{date.today().isoformat()}"
CONJUNTO = "juego"


def _scores_oof(X, y, grupos) -> np.ndarray:
    """Predicciones out-of-fold (cada fila puntuada por un modelo que no la
    vio en entrenamiento) para calibrar los cortes de riesgo sobre una
    distribución de validación, no sobre el ajuste optimista in-sample."""
    gkf = GroupKFold(n_splits=N_SPLITS)
    oof = np.zeros(len(X))
    for idx_train, idx_val in gkf.split(X, y, groups=grupos):
        pipeline = construir_pipeline()
        pipeline.fit(X.iloc[idx_train], y.iloc[idx_train])
        oof[idx_val] = pipeline.predict_proba(X.iloc[idx_val])[:, 1]
    return oof


def main():
    parser = argparse.ArgumentParser(description="Entrena el modelo de título de NexPlay")
    parser.add_argument("--db", type=Path, required=True, help="base SQLite de entrenamiento (el asset data-v1)")
    parser.add_argument("--tag-datos", help="tag del release del que salió la base, p. ej. data-v1")
    parser.add_argument("--sha256-asset", help="sha256 del asset comprimido de ese release")
    args = parser.parse_args()
    if not args.db.exists():
        parser.error(f"no existe {args.db}; preparar_entorno.py la descarga y la verifica")

    df = cargar_datos(args.db)
    X, y, grupos = construir_features(df, conjunto=CONJUNTO)
    mediana_metacritic = df["metacritic"].median()

    oof = _scores_oof(X, y, grupos)
    umbral_medio = float(np.percentile(oof, 100 / 3))
    umbral_alto = float(np.percentile(oof, 200 / 3))

    pipeline = construir_pipeline()
    pipeline.fit(X, y)

    artefacto = {
        "pipeline": pipeline,
        "features": list(X.columns),
        "version": VERSION_MODELO,
        "conjunto": CONJUNTO,
        "mediana_metacritic": mediana_metacritic,
        "umbral_medio": umbral_medio,
        "umbral_alto": umbral_alto,
        # Procedencia: con qué datos exactos se entrenó.
        "datos_tag": args.tag_datos,
        "datos_sha256": args.sha256_asset,
        "filas_entrenamiento": int(len(df)),
        "juegos_entrenamiento": int(grupos.nunique()),
    }

    MODELO_PATH.parent.mkdir(exist_ok=True)
    with open(MODELO_PATH, "wb") as f:
        pickle.dump(artefacto, f)

    print(f"modelo guardado en {MODELO_PATH}")
    print(f"version={VERSION_MODELO}  conjunto={CONJUNTO}")
    print(f"features={artefacto['features']}")
    print(f"datos={args.tag_datos}  sha256={args.sha256_asset}")
    print(f"filas={len(df)}  juegos={grupos.nunique()}  prevalencia={y.mean():.4f}")
    print(f"umbral_medio={umbral_medio:.4f}  umbral_alto={umbral_alto:.4f}  (tercios de scores OOF)")


if __name__ == "__main__":
    main()
