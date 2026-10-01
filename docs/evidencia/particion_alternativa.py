"""¿Cuánto depende el PR-AUC del modelo de título de la partición? Prueba de robustez, prerregistrada.

GroupKFold reparte los juegos por tamaño, y 73 de los 83 juegos de data-v1 empatan en 1,500 reseñas
(el tope de la ingesta). Cada versión de scikit-learn desempata distinto: la 1.6.1 de Colab arma otra
partición que la congelada en referencias/particion_gkf_data-v1.csv. Toda evaluación del proyecto usa
la congelada (splits_congelados, en modelado/entrenar_baseline.py). Este script mide el mismo modelo
con la partición de la 1.6.1, para el documento.

Prerregistro. Este archivo se commitea antes de correrlo, y particion-alternativa.json sale de él sin
editarlo. Es descriptivo: fija el método y lo que se reporta, sin criterio de pasa o no pasa. Antes de
escribirlo ya se conocía, por una corrida en Colab, que esa partición da 0.0692 ± 0.0412 y que el
modelo supera al trivial en los 5 folds; lo que queda fijo aquí es cómo se calcula y qué se registra.

Método:
- datos: la base de entrenamiento data-v1 que deja despliegue/preparar_entorno.py, reconocida por su
  sha256 (83 juegos, 123,972 reseñas);
- modelo: construir_features(conjunto="juego") y construir_pipeline(), los de producción, sin cambios;
- particiones: la congelada (el CSV) y la que arma GroupKFold(n_splits=5) de scikit-learn 1.6.1
  (particion_groupkfold); con otra versión el script no corre;
- por fold y por partición: juegos, reseñas, positivos, PR-AUC del modelo y del clasificador trivial
  (DummyClassifier(strategy="prior"), como en entrenar_baseline.py);
- resumen: media y desviación estándar (np.std, como evaluar_gkf) de cada partición, folds en que el
  modelo supera al trivial, juegos que quedan en el mismo fold en las dos y juegos empatados.

Solo lee: no escribe modelos, umbrales ni referencias.

Uso (en un entorno con scikit-learn 1.6.1):
  python docs/evidencia/particion_alternativa.py
"""

import hashlib
import json
import platform
import subprocess
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.optimize import OptimizeWarning
from sklearn.dummy import DummyClassifier
from sklearn.metrics import average_precision_score

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "modelado")]

from despliegue.preparar_entorno import origen_de_release  # noqa: E402
from entrenar_baseline import (  # noqa: E402
    DB_ENTRENAMIENTO, cargar_datos, construir_features, construir_pipeline, leer_particion,
    particion_groupkfold, splits_de,
)

VERSION_SKLEARN = "1.6.1"
SALIDA = RAIZ / "docs" / "evidencia" / "particion-alternativa.json"

# scikit-learn 1.6.1 le pasa `iprint` al L-BFGS-B de SciPy, que en las versiones nuevas ya no lo
# acepta y avisa. No cambia el ajuste.
warnings.filterwarnings("ignore", message="Unknown solver options: iprint", category=OptimizeWarning)


def _firma(folds: pd.Series) -> str:
    """La misma firma que analisis/exploracion.py (firma_de_particion)."""
    return hashlib.sha256("\n".join(f"{appid},{fold}" for appid, fold in folds.sort_index().items()).encode()).hexdigest()


def _git(*argumentos: str) -> str:
    return subprocess.run(["git", "-C", str(RAIZ), *argumentos], capture_output=True, text=True, check=True).stdout.strip()


def _por_fold(X: pd.DataFrame, y: pd.Series, grupos: pd.Series, particion: pd.Series) -> list[dict]:
    filas = []
    for numero, (entrenamiento, validacion) in enumerate(splits_de(grupos, particion)):
        y_val = y.iloc[validacion]
        modelo = construir_pipeline().fit(X.iloc[entrenamiento], y.iloc[entrenamiento])
        trivial = DummyClassifier(strategy="prior").fit(X.iloc[entrenamiento], y.iloc[entrenamiento])
        filas.append({
            "fold": numero,
            "juegos": int(grupos.iloc[validacion].nunique()),
            "resenas": int(len(validacion)),
            "positivos": int(y_val.sum()),
            "pr_auc_modelo": float(average_precision_score(y_val, modelo.predict_proba(X.iloc[validacion])[:, 1])),
            "pr_auc_trivial": float(average_precision_score(y_val, trivial.predict_proba(X.iloc[validacion])[:, 1])),
        })
    return filas


def _resumen(filas: list[dict]) -> dict:
    modelo = np.array([f["pr_auc_modelo"] for f in filas])
    trivial = np.array([f["pr_auc_trivial"] for f in filas])
    return {"pr_auc_media": float(modelo.mean()), "pr_auc_std": float(modelo.std()),
            "trivial_media": float(trivial.mean()), "folds_donde_gana_el_modelo": int((modelo > trivial).sum())}


def main() -> int:
    if sklearn.__version__ != VERSION_SKLEARN:
        print(f"este script mide la partición de scikit-learn {VERSION_SKLEARN}; aquí hay {sklearn.__version__}")
        return 1
    origen = origen_de_release(DB_ENTRENAMIENTO)
    if origen != "data-v1":
        print(f"{DB_ENTRENAMIENTO} no es la base de data-v1 (origen: {origen}); corre despliegue/preparar_entorno.py")
        return 1

    df = cargar_datos(DB_ENTRENAMIENTO)
    X, y, grupos = construir_features(df, conjunto="juego")
    congelada = leer_particion()
    alternativa = particion_groupkfold(grupos)
    resenas_por_juego = grupos.value_counts()
    empate = int(resenas_por_juego.mode().iloc[0])

    por_fold = {"congelada": _por_fold(X, y, grupos, congelada), "alternativa": _por_fold(X, y, grupos, alternativa)}
    resultado = {
        "generado": date.today().isoformat(),
        "script": "docs/evidencia/particion_alternativa.py",
        "codigo": {"commit": _git("rev-parse", "HEAD"), "arbol_limpio": _git("status", "--porcelain") == ""},
        "entorno": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                    "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
        "datos": {"release": origen, "sha256_base": hashlib.sha256(DB_ENTRENAMIENTO.read_bytes()).hexdigest(),
                  "resenas": int(len(df)), "juegos": int(grupos.nunique()), "prevalencia": float(y.mean())},
        "particiones": {
            "congelada": {"origen": "referencias/particion_gkf_data-v1.csv", "firma": _firma(congelada)},
            "alternativa": {"origen": f"GroupKFold(n_splits=5) de scikit-learn {sklearn.__version__}",
                            "firma": _firma(alternativa),
                            "fold_por_appid": {str(appid): int(fold) for appid, fold in alternativa.items()}},
            "juegos_con_el_mismo_fold": int(alternativa.eq(congelada.reindex(alternativa.index)).sum()),
            "juegos_empatados": int(resenas_por_juego.eq(empate).sum()),
            "resenas_del_empate": empate,
        },
        "por_fold": por_fold,
        "resumen": {nombre: _resumen(filas) for nombre, filas in por_fold.items()},
    }
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    for nombre, resumen in resultado["resumen"].items():
        print(f"{nombre:<12} PR-AUC {resumen['pr_auc_media']:.4f} ± {resumen['pr_auc_std']:.4f}; "
              f"gana al trivial en {resumen['folds_donde_gana_el_modelo']} de {len(por_fold[nombre])} folds")
    particiones = resultado["particiones"]
    print(f"juegos con el mismo fold: {particiones['juegos_con_el_mismo_fold']} de {grupos.nunique()}; "
          f"empatados en {empate:,} reseñas: {particiones['juegos_empatados']}")
    print(f"escrito en {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
