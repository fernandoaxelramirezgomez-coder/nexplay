"""Simulación sin artefactos: ¿qué pasaría si B+ se entrenara con 123 juegos (data-v2)
en vez de 83 (data-v1)? Solo validación cruzada en memoria; no escribe ningún modelo.

Mide, para cada corte:
- el GroupKFold de producción (5 folds, determinista): PR-AUC por fold de 'juego' y
  'compra', y la diferencia pareada fold a fold (mismos folds para los dos conjuntos);
- 30 particiones aleatorias de juegos en 5 folds: la desviación entre folds promedio y la
  distribución del aporte del lado del jugador, para no depender de un solo reparto.
"""
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from entrenar_baseline import N_SPLITS, cargar_datos, construir_features, construir_pipeline  # noqa: E402

# Las dos bases que deja preparar_entorno.py en un entorno limpio de frontend-angular.
CORTES = {
    "data-v1 (83)": RAIZ / "datos" / "entrenamiento" / "nexplay_data-v1.db",
    "data-v2 (123)": RAIZ / "datos" / "nexplay.db",
}
REPETICIONES = 30


def pr_auc_por_fold(X, y, folds):
    salida = []
    for tr, va in folds:
        m = construir_pipeline().fit(X.iloc[tr], y.iloc[tr])
        salida.append(average_precision_score(y.iloc[va], m.predict_proba(X.iloc[va])[:, 1]))
    return np.array(salida)


def folds_aleatorios(grupos, semilla):
    juegos = np.array(sorted(grupos.unique()))
    rng = np.random.default_rng(semilla)
    rng.shuffle(juegos)
    fold_de = {a: i % N_SPLITS for i, a in enumerate(juegos)}
    asignado = grupos.map(fold_de).to_numpy()
    return [(np.where(asignado != k)[0], np.where(asignado == k)[0]) for k in range(N_SPLITS)]


for nombre, db in CORTES.items():
    df = cargar_datos(db)
    Xj, y, g = construir_features(df, conjunto="juego")
    Xc, _, _ = construir_features(df, conjunto="compra")
    print(f"\n===== {nombre}: filas={len(df):,} juegos={g.nunique()} prevalencia={y.mean():.4f}")

    folds = list(GroupKFold(n_splits=N_SPLITS).split(Xj, y, groups=g))
    pj, pc = pr_auc_por_fold(Xj, y, folds), pr_auc_por_fold(Xc, y, folds)
    dif = pc - pj
    print("GroupKFold de producción (mismos folds para los dos conjuntos):")
    print(f"  juego  por fold: {np.round(pj, 4)}  media={pj.mean():.4f}  std={pj.std():.4f}")
    print(f"  compra por fold: {np.round(pc, 4)}  media={pc.mean():.4f}  std={pc.std():.4f}")
    print(f"  compra - juego por fold: {np.round(dif, 4)}  media={dif.mean():+.4f}  std={dif.std(ddof=1):.4f}")
    print(f"  aporte del jugador: {100 * (1 - pj.mean() / pc.mean()):.1f}% del PR-AUC; folds donde compra gana: {(dif > 0).sum()}/{N_SPLITS}")
    print(f"  diferencia de medias / std entre folds de juego = {abs(dif.mean()) / pj.std():.2f}  "
          f"(t pareado = {dif.mean() / (dif.std(ddof=1) / np.sqrt(N_SPLITS)):.2f}, con {N_SPLITS - 1} gl)")

    stds, aportes, difs, gana = [], [], [], 0
    for semilla in range(REPETICIONES):
        fa = folds_aleatorios(g, semilla)
        a, b = pr_auc_por_fold(Xj, y, fa), pr_auc_por_fold(Xc, y, fa)
        stds.append(a.std()); aportes.append(1 - a.mean() / b.mean()); difs.append(b.mean() - a.mean()); gana += b.mean() > a.mean()
    stds, aportes, difs = map(np.array, (stds, aportes, difs))
    print(f"{REPETICIONES} particiones aleatorias de juegos en {N_SPLITS} folds:")
    print(f"  std entre folds de 'juego': media={stds.mean():.4f}  (rango {stds.min():.4f}–{stds.max():.4f})")
    print(f"  aporte del jugador: media={100 * aportes.mean():.1f}%  percentil 2.5–97.5 = {100 * np.percentile(aportes, 2.5):.1f}% a {100 * np.percentile(aportes, 97.5):.1f}%")
    print(f"  compra - juego (media por partición): media={difs.mean():+.4f}  rango {difs.min():+.4f} a {difs.max():+.4f}")
    print(f"  particiones donde compra supera a juego: {gana}/{REPETICIONES}")
    print(f"  diferencia media / std entre folds media = {abs(difs.mean()) / stds.mean():.2f}")
