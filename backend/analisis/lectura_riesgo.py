"""Tablas y gráficas para leer el modelo de riesgo en términos de negocio (notebooks/01_modelo_riesgo.ipynb).

Describen lo que el 01 ya calculó: no eligen variables, umbrales ni modelo. No importan limpieza.py (lingua):
el 01 no la necesita."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from graficas import PALETA

BANDAS = ("bajo", "medio", "alto")


def banda_de(score: pd.Series, cortes: tuple[float, float]) -> pd.Series:
    """bajo / medio / alto con los mismos cortes por terciles que usa la API."""
    return pd.Series(np.select([score < cortes[0], score < cortes[1]], ["bajo", "medio"], "alto"), index=score.index)


def tabla_de_bandas(appid: pd.Series, y: pd.Series, score, cortes: tuple[float, float]) -> pd.DataFrame:
    """Por banda: juegos, reseñas, tasa real de señal y veces la base (la prevalencia de este conjunto).

    La banda es del juego: el modelo de título da el mismo score a todas sus reseñas (salvo el último bit, que
    cambia según cómo agrupa las cuentas el álgebra lineal). Si un juego tuviera dos de verdad, algo cambió en el
    modelo y la tabla no aplica."""
    datos = pd.DataFrame({"appid": np.asarray(appid), "y": np.asarray(y), "score": np.asarray(score, dtype=float)})
    if (datos.groupby("appid")["score"].agg(lambda s: s.max() - s.min()) > 1e-9).any():
        raise ValueError("un juego tiene más de un score: la banda ya no es del juego")
    por_juego = datos.groupby("appid").agg(score=("score", "first"), reseñas=("y", "size"), señal=("y", "sum"))
    por_juego["banda"] = banda_de(por_juego["score"], cortes)
    tabla = por_juego.groupby("banda").agg(juegos=("score", "size"), reseñas=("reseñas", "sum"), señal=("señal", "sum"))
    tabla = tabla.reindex(list(BANDAS), fill_value=0)
    tabla["tasa de señal"] = tabla["señal"] / tabla["reseñas"]
    tabla["veces la base"] = tabla["tasa de señal"] / datos["y"].mean()
    return tabla


def tabla_comparativa(pr_auc_por_fold: dict[str, np.ndarray], trivial: str = "trivial") -> pd.DataFrame:
    """Media y desviación entre folds de cada modelo, y cuántas veces el PR-AUC del trivial."""
    base = pr_auc_por_fold[trivial].mean()
    return pd.DataFrame({
        nombre: {"PR-AUC media": valores.mean(), "std entre folds": valores.std(), "veces el trivial": valores.mean() / base}
        for nombre, valores in pr_auc_por_fold.items()
    }).T.rename_axis("modelo")


def figura_pr_auc_por_fold(modelo: np.ndarray, trivial: np.ndarray, nombre: str) -> go.Figure:
    """Barras por fold: el modelo contra el trivial (la prevalencia de ese fold), con la media del modelo."""
    folds = [f"fold {k}" for k in range(1, len(modelo) + 1)]
    figura = go.Figure([
        go.Bar(name="trivial (la prevalencia del fold)", x=folds, y=trivial, marker_color=PALETA["GRIS"]),
        go.Bar(name=f"modelo {nombre}", x=folds, y=modelo, marker_color=PALETA["AZUL"],
               text=[f"{v:.3f}" for v in modelo], textposition="outside"),
    ])
    figura.add_hline(y=modelo.mean(), line_dash="dash", line_color=PALETA["AZUL"],
                     annotation_text=f"media del modelo: {modelo.mean():.3f}", annotation_position="top right")
    figura.update_layout(barmode="group", title=f"PR-AUC por fold: modelo {nombre} contra el trivial",
                         yaxis_title="PR-AUC", legend={"orientation": "h", "y": -0.15})
    return figura
