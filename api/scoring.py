"""Regla de oro: esta función tiene firma estable. Carga modelo/nexplay.pkl
una sola vez al importar el módulo (conjunto 'compra': GroupKFold por appid,
optimizado a PR-AUC) y predice con las mismas entradas y salida que el
simulador que reemplaza. Nada fuera de este archivo debe cambiar cuando el
modelo se re-entrene."""

import logging
import pickle
import random
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from .schemas import MotivoInsatisfaccion, NivelRiesgo, PerfilJugador, Plataforma, PrediccionRiesgo

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent / "datos" / "nexplay.db"
_MODELO_PATH = Path(__file__).resolve().parent.parent / "modelo" / "nexplay.pkl"

_NOTA_PLATAFORMA_SIN_DATOS = (
    "El lado del juego transfiere, pero no existe fuente de entrenamiento propia de "
    "{plataforma}: la señal viene de reseñas de Steam (PC)."
)

_MOTIVOS_SIMULADOS = [
    "rendimiento/optimización",
    "bugs al lanzamiento",
    "contenido pagado (dlc/microtransacciones)",
    "diferencia con lo prometido en marketing",
    "curva de aprendizaje/dificultad",
    "servidores/matchmaking",
]


def _cargar_artefacto() -> dict:
    with open(_MODELO_PATH, "rb") as f:
        return pickle.load(f)


_ARTEFACTO = _cargar_artefacto()
_PIPELINE = _ARTEFACTO["pipeline"]
_FEATURES = _ARTEFACTO["features"]
_VERSION_MODELO = _ARTEFACTO["version"]
_MEDIANA_METACRITIC = _ARTEFACTO["mediana_metacritic"]
# Tercios de la distribución de scores out-of-fold (GroupKFold), no valores
# fijos: con prevalencia 2.19% un umbral fijo como 0.66 es inalcanzable.
_UMBRAL_MEDIO = _ARTEFACTO["umbral_medio"]
_UMBRAL_ALTO = _ARTEFACTO["umbral_alto"]

logger.info(
    "modelo cargado: version=%s features=%s umbral_medio=%.4f umbral_alto=%.4f",
    _VERSION_MODELO, _FEATURES, _UMBRAL_MEDIO, _UMBRAL_ALTO,
)


def _atributos_juego(appid: int) -> dict:
    con = sqlite3.connect(_DB_PATH)
    try:
        fila = con.execute(
            "SELECT es_gratis, precio_final, descuento, metacritic FROM juegos WHERE appid = ?",
            (appid,),
        ).fetchone()
    finally:
        con.close()
    if fila is None:
        logger.warning("appid=%s sin fila en juegos; se usan valores neutros", appid)
        return {"es_gratis": 0, "precio_final": 0.0, "descuento": 0.0, "metacritic": None}
    es_gratis, precio_final, descuento, metacritic = fila
    return {"es_gratis": es_gratis, "precio_final": precio_final, "descuento": descuento, "metacritic": metacritic}


def _nivel_desde_riesgo(riesgo: float) -> NivelRiesgo:
    if riesgo < _UMBRAL_MEDIO:
        return NivelRiesgo.BAJO
    if riesgo < _UMBRAL_ALTO:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.ALTO


def _construir_features(perfil: PerfilJugador, appid: int) -> pd.DataFrame:
    juego = _atributos_juego(appid)
    metacritic = juego["metacritic"]
    fila = {
        # compras_al_anio es el sustituto declarado de num_games_owned (ver
        # CLAUDE.md); el formulario siempre lo pide, así que no existe la
        # bandera de "perfil privado" en producción (esa bandera solo tiene
        # sentido sobre datos de Steam, donde el perfil puede no ser público).
        "privacidad_perfil": 0,
        "log_num_games_owned": np.log1p(perfil.compras_al_anio),
        "es_gratis": int(juego["es_gratis"] or 0),
        "log_precio_final": np.log1p(juego["precio_final"] or 0.0),
        "descuento": juego["descuento"] or 0.0,
        "metacritic_disponible": int(metacritic is not None),
        "metacritic": metacritic if metacritic is not None else _MEDIANA_METACRITIC,
    }
    return pd.DataFrame([fila])[_FEATURES]


def predecir(perfil: PerfilJugador, appid: int) -> PrediccionRiesgo:
    X = _construir_features(perfil, appid)
    riesgo = round(float(_PIPELINE.predict_proba(X)[0, 1]), 4)
    nota_plataforma = (
        _NOTA_PLATAFORMA_SIN_DATOS.format(plataforma=perfil.plataforma.value)
        if perfil.plataforma != Plataforma.PC
        else None
    )
    logger.info("prediccion appid=%s riesgo=%.4f", appid, riesgo)
    return PrediccionRiesgo(
        appid=appid,
        riesgo=riesgo,
        nivel=_nivel_desde_riesgo(riesgo),
        modelo_version=_VERSION_MODELO,
        nota_plataforma=nota_plataforma,
    )


def motivos_frecuentes(appid: int) -> list[MotivoInsatisfaccion]:
    # rng propio (no random global) para que la respuesta sea estable por appid.
    # Sigue simulado: la explicación por motivos no es parte de este cambio.
    rng = random.Random(appid)
    motivos = rng.sample(_MOTIVOS_SIMULADOS, k=rng.randint(2, 4))
    frecuencias = sorted((round(rng.uniform(0.05, 0.6), 2) for _ in motivos), reverse=True)
    return [MotivoInsatisfaccion(motivo=m, frecuencia=f) for m, f in zip(motivos, frecuencias)]
