"""
NexPlay - Baseline: regresion logistica vs clasificador trivial
=================================================================

Pregunta que responde este script: con las variables estructuradas que ya
tenemos (autor de la reseña + metadatos del juego, SIN texto ni nada
derivado de la variable objetivo), ¿hay señal para separar arrepentimiento
temprano (Y=1) de no-arrepentimiento?

Nada de esto es el modelo final ni toca api/scoring.py: es el chequeo de
"vale la pena seguir por este camino" antes de invertir en feature
engineering o en texto.

Reglas del proyecto que este script respeta:
- Y = 1 si playtime_at_review < 120 Y voted_up == 0 (arrepentimiento
  temprano, proxy). Ninguna de las dos variables se usa como feature.
- GroupKFold por appid: el modelo se valida contra juegos que no vio.
- Metrica: PR-AUC (average_precision_score). La clase esta desbalanceada.
- num_games_owned == 0 es bandera de privacidad, no biblioteca vacia: se
  modela con un flag explicito, no se imputa como cero silenciosamente.
- Nada de playtime_forever ni columnas derivadas de la reseña despues del
  momento de la compra: fuga garantizada, porque en produccion el perfil
  se declara en el formulario, no se observa post-hoc.

Uso:
    python entrenar_baseline.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DB_PATH = Path(__file__).resolve().parent / "datos" / "nexplay.db"
N_SPLITS = 5
SEMILLA = 42


def cargar_datos(db_path: Path = DB_PATH) -> pd.DataFrame:
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT
            r.appid,
            r.num_games_owned,
            r.num_reviews,
            r.steam_purchase,
            r.received_for_free,
            r.written_during_early_access,
            r.playtime_at_review,
            r.voted_up,
            j.es_gratis,
            j.precio_final,
            j.descuento,
            j.metacritic
        FROM resenas r
        JOIN juegos j ON j.appid = r.appid
        """,
        con,
    )
    con.close()
    return df


def construir_features(df: pd.DataFrame, conjunto: str = "completo") -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """conjunto='completo': todo lo estructurado que ya tenemos (incluye
    columnas que solo existen porque el autor ya reseño, ej. num_reviews).
    conjunto='compra': solo lo que se conoce ANTES de que el jugador juegue,
    es decir lo que el formulario de alta podria llegar a declarar o el
    catalogo ya sabe del juego.
    conjunto='juego': solo el lado del juego, nada del jugador — el piso de
    lo que transfiere sin depender de ningun dato de perfil."""
    y = ((df["playtime_at_review"] < 120) & (df["voted_up"] == 0)).astype(int)
    grupos = df["appid"]

    X = pd.DataFrame(index=df.index)

    if conjunto == "completo":
        # privacidad_perfil solo se evaluo aqui: en GroupKFold sobre 'compra'
        # la diferencia de PR-AUC frente a quitarla (0.0036) fue un orden de
        # magnitud menor que la desviacion entre folds (0.027) — sin senal
        # real, se saca del conjunto que sirve a produccion.
        X["privacidad_perfil"] = (df["num_games_owned"] == 0).astype(int)

    if conjunto != "juego":
        # --- lado del jugador ---
        X["log_num_games_owned"] = np.log1p(df["num_games_owned"])

    if conjunto == "completo":
        # Solo se conocen despues de que el jugador ya reseño ese juego
        # (num_reviews cambia con el tiempo; steam_purchase/received_for_free/
        # written_during_early_access son atributos de ESA reseña puntual).
        X["log_num_reviews"] = np.log1p(df["num_reviews"])
        X["steam_purchase"] = df["steam_purchase"].fillna(0).astype(int)
        X["received_for_free"] = df["received_for_free"].fillna(0).astype(int)
        X["written_during_early_access"] = df["written_during_early_access"].fillna(0).astype(int)

    # --- lado del juego (conocido antes de comprar, transferible) ---
    X["es_gratis"] = df["es_gratis"].fillna(0).astype(int)
    X["log_precio_final"] = np.log1p(df["precio_final"].fillna(0))
    X["descuento"] = df["descuento"].fillna(0)
    X["metacritic_disponible"] = df["metacritic"].notna().astype(int)
    mediana_metacritic = df["metacritic"].median()
    X["metacritic"] = df["metacritic"].fillna(mediana_metacritic)

    return X, y, grupos


def construir_pipeline() -> Pipeline:
    """Mismo pipeline en entrenar_baseline.py, entrenar_modelo.py y el
    notebook: regresion logistica con class_weight='balanced', sin tuning."""
    return Pipeline([
        ("escalar", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEMILLA)),
    ])


def evaluar_gkf(modelo, X, y, grupos, nombre: str) -> np.ndarray:
    gkf = GroupKFold(n_splits=N_SPLITS)
    pr_aucs = []
    for fold, (idx_train, idx_val) in enumerate(gkf.split(X, y, groups=grupos), 1):
        modelo.fit(X.iloc[idx_train], y.iloc[idx_train])
        proba = modelo.predict_proba(X.iloc[idx_val])[:, 1]
        pr_auc = average_precision_score(y.iloc[idx_val], proba)
        pr_aucs.append(pr_auc)
        n_pos_val = y.iloc[idx_val].sum()
        print(f"  [{nombre}] fold {fold}: PR-AUC={pr_auc:.4f}  (n_val={len(idx_val)}, positivos={n_pos_val})")
    pr_aucs = np.array(pr_aucs)
    print(f"  [{nombre}] PR-AUC media={pr_aucs.mean():.4f}  std={pr_aucs.std():.4f}\n")
    return pr_aucs


def correr_conjunto(df: pd.DataFrame, conjunto: str) -> dict:
    X, y, grupos = construir_features(df, conjunto)

    prevalencia = y.mean()
    print(f"--- conjunto='{conjunto}' ---")
    print(f"n={len(df)}  juegos={grupos.nunique()}  prevalencia Y=1={prevalencia:.4f} ({100*prevalencia:.2f}%)")
    print(f"Features: {list(X.columns)}\n")

    print(f"=== [{conjunto}] Clasificador trivial (DummyClassifier, strategy=prior) ===")
    trivial = DummyClassifier(strategy="prior")
    pr_aucs_trivial = evaluar_gkf(trivial, X, y, grupos, f"{conjunto}/trivial")

    print(f"=== [{conjunto}] Regresion logistica (class_weight=balanced, sin tuning) ===")
    logreg = construir_pipeline()
    pr_aucs_logreg = evaluar_gkf(logreg, X, y, grupos, f"{conjunto}/logreg")

    logreg.fit(X, y)
    coefs = pd.Series(logreg.named_steps["clf"].coef_[0], index=X.columns).sort_values()
    print(f"=== [{conjunto}] Coeficientes (entrenado con todos los datos) ===")
    print(coefs.to_string())
    print()

    return {
        "trivial": pr_aucs_trivial,
        "logreg": pr_aucs_logreg,
    }


def comparar_variantes_privacidad(df: pd.DataFrame) -> dict:
    """Experimento ya aprobado (ver construir_features): compara PR-AUC del
    conjunto 'compra' con la bandera privacidad_perfil, sin ella, y sobre el
    subconjunto donde vale 0 (perfil publico) — ahi la bandera es constante
    y por eso no se incluye como feature en esa variante. Conclusion: la
    diferencia con/sin bandera (0.0036) es un orden de magnitud menor que la
    desviacion entre folds (0.027), por eso 'compra' ya no la incluye."""
    X, y, grupos = construir_features(df, conjunto="compra")
    privacidad_perfil = (df["num_games_owned"] == 0).astype(int)

    X_con = X.copy()
    X_con.insert(0, "privacidad_perfil", privacidad_perfil)
    con_privacidad = evaluar_gkf(construir_pipeline(), X_con, y, grupos, "con_privacidad")

    sin_privacidad = evaluar_gkf(construir_pipeline(), X, y, grupos, "sin_privacidad")

    mask = privacidad_perfil == 0
    X_publico = X[mask].reset_index(drop=True)
    y_publico = y[mask].reset_index(drop=True)
    grupos_publico = grupos[mask].reset_index(drop=True)
    print(f"  [solo_publico] n={len(X_publico)} ({100 * len(X_publico) / len(X):.2f}% del total)")
    solo_publico = evaluar_gkf(construir_pipeline(), X_publico, y_publico, grupos_publico, "solo_publico")

    return {
        "con_privacidad": con_privacidad,
        "sin_privacidad": sin_privacidad,
        "solo_publico": solo_publico,
        "n_solo_publico": len(X_publico),
    }


def main():
    df = cargar_datos()

    resultados = {
        "completo": correr_conjunto(df, "completo"),
        "compra": correr_conjunto(df, "compra"),
        "juego": correr_conjunto(df, "juego"),
    }

    print("=== Comparacion final ===")
    for conjunto in ("completo", "compra", "juego"):
        t, l = resultados[conjunto]["trivial"], resultados[conjunto]["logreg"]
        print(f"{conjunto:<10} trivial={t.mean():.4f}+/-{t.std():.4f}  logreg={l.mean():.4f}+/-{l.std():.4f}  logreg/trivial={l.mean()/t.mean():.2f}x")

    base = resultados["completo"]["logreg"].mean()
    for conjunto in ("compra", "juego"):
        caida = 1 - resultados[conjunto]["logreg"].mean() / base
        print(f"\nlogreg('{conjunto}') vs logreg('completo'): {100*caida:.1f}% menos PR-AUC")

    caida_jugador = 1 - resultados["juego"]["logreg"].mean() / resultados["compra"]["logreg"].mean()
    print(f"logreg('juego') vs logreg('compra'): {100*caida_jugador:.1f}% menos PR-AUC al quitar tambien num_games_owned/privacidad")


if __name__ == "__main__":
    main()
