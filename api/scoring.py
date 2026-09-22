"""Regla de oro: esta función tiene firma estable. Carga modelo/nexplay.pkl
una sola vez al importar el módulo (conjunto 'juego', entrenado con data-v1:
GroupKFold por appid, optimizado a PR-AUC) y predice con las mismas entradas y
salida que el simulador que reemplaza. Nada fuera de este archivo debe cambiar
cuando el modelo se re-entrene.

Es un modelo de título: el riesgo depende solo del juego. predecir() sigue
recibiendo el perfil (el contrato de /prediccion no cambia y el perfil aporta la
nota de plataforma), pero ningún dato del perfil entra al score."""

import logging
import pickle
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from .schemas import (
    DireccionFactor,
    FactorPrediccion,
    MotivoInsatisfaccion,
    NivelRelativo,
    NivelRiesgo,
    PerfilJugador,
    Plataforma,
    PrediccionRiesgo,
)

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent / "datos" / "nexplay.db"
_MODELO_PATH = Path(__file__).resolve().parent.parent / "modelo" / "nexplay.pkl"

_NOTA_PLATAFORMA_SIN_DATOS = (
    "El lado del juego transfiere, pero no existe fuente de entrenamiento propia de "
    "{plataforma}: la señal viene de reseñas de Steam (PC)."
)

# Frases nominales: la UI las arma como "{etiqueta}, por encima/debajo del
# promedio del catálogo — {direccion} el riesgo estimado", así que tienen que
# leerse como sustantivo, no como afirmación binaria fija (ver nota sobre
# metacritic_disponible: la etiqueta no debe decir si el juego "tiene" o no
# algo, porque eso ya lo dice valor_relativo).
_ETIQUETAS_FEATURES = {
    "log_num_games_owned": "compras declaradas por año",
    "es_gratis": "gratuidad del juego",
    "log_precio_final": "precio del juego",
    "descuento": "descuento actual del juego",
    "metacritic_disponible": "cobertura de crítica especializada",
    "metacritic": "nota de Metacritic",
}

# Con menos reseñas Y=1 que esto, cualquier frecuencia por término es ruido de
# muestra chica (mismo criterio que descarta diferencias de PR-AUC menores al
# ruido entre folds en el notebook): mejor no reportar motivos que inventar
# certeza sobre 2 o 3 reseñas.
_UMBRAL_MIN_CASOS = 5

# Palabras clave en inglés: la ingesta filtra language=english (ver
# ingesta_steam.py), así que es lo que hay en el texto de las reseñas.
_PALABRAS_CLAVE_POR_CATEGORIA: dict[str, list[str]] = {
    "rendimiento": [
        "fps", "lag", "laggy", "lagging", "stutter", "stuttering", "freeze", "freezing",
        "freezes", "crash", "crashes", "crashing", "crashed", "optimize", "optimise",
        "optimization", "optimisation", "framerate", "frame rate", "sluggish",
        "memory leak", "loading times", "load times",
    ],
    "bugs": [
        "bug", "bugs", "buggy", "glitch", "glitches", "glitchy", "broken", "game-breaking",
        "gamebreaking", "softlock", "softlocked", "unplayable",
    ],
    "dificultad": [
        "difficult", "difficulty", "hard", "hardcore", "frustrating", "frustrated",
        "unfair", "punishing", "grind", "grindy", "grinding", "brutal",
    ],
    "controles": [
        "controls", "controller", "clunky", "unresponsive", "aiming", "aim assist",
        "keybind", "keybinding", "key bindings", "input lag", "camera controls",
    ],
    "contenido": [
        "content", "short", "shallow", "repetitive", "repetition", "empty", "lacking",
        "incomplete", "unfinished", "dlc", "pay to win", "filler",
    ],
    # "refund", "waste of money" y "not worth" se descartaron: son insatisfaccion
    # generica (aparecen en cualquier resena Y=1 sin importar el motivo), no
    # queja de costo especificamente.
    "precio": [
        "price", "priced", "pricing", "cost", "costly", "overpriced", "expensive",
        "paywall", "cash grab", "microtransaction", "microtransactions",
    ],
}


def _compilar_patrones() -> dict[str, re.Pattern]:
    return {
        categoria: re.compile(
            r"\b(?:" + "|".join(re.escape(palabra) for palabra in palabras) + r")\b",
            re.IGNORECASE,
        )
        for categoria, palabras in _PALABRAS_CLAVE_POR_CATEGORIA.items()
    }


_PATRONES_MOTIVOS = _compilar_patrones()


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
        # El modelo de título no usa compras_al_anio: la fila se arma completa y
        # [_FEATURES] se queda solo con las columnas del artefacto, así el mismo
        # código sirve a un modelo con o sin lado del jugador.
        "log_num_games_owned": np.log1p(perfil.compras_al_anio),
        "es_gratis": int(juego["es_gratis"] or 0),
        "log_precio_final": np.log1p(juego["precio_final"] or 0.0),
        "descuento": juego["descuento"] or 0.0,
        "metacritic_disponible": int(metacritic is not None),
        "metacritic": metacritic if metacritic is not None else _MEDIANA_METACRITIC,
    }
    return pd.DataFrame([fila])[_FEATURES]


def _factores_prediccion(X: pd.DataFrame) -> list[FactorPrediccion]:
    """Contribución de cada variable al log-odds del score: coeficiente de la
    regresión logística por el valor ya estandarizado (mismo StandardScaler
    del pipeline), que es lo que la regresión logística realmente suma.
    Se devuelven las tres de mayor magnitud absoluta."""
    escalador = _PIPELINE.named_steps["escalar"]
    clf = _PIPELINE.named_steps["clf"]
    valores_estandarizados = escalador.transform(X)[0]
    contribuciones = clf.coef_[0] * valores_estandarizados

    factores = [
        FactorPrediccion(
            etiqueta=_ETIQUETAS_FEATURES[feature],
            valor_relativo=NivelRelativo.ALTO if valor_estandarizado > 0 else NivelRelativo.BAJO,
            contribucion=round(float(contribucion), 4),
            direccion=DireccionFactor.AUMENTA if contribucion > 0 else DireccionFactor.REDUCE,
        )
        for feature, valor_estandarizado, contribucion in zip(_FEATURES, valores_estandarizados, contribuciones)
    ]
    factores.sort(key=lambda f: abs(f.contribucion), reverse=True)
    return factores[:3]


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
        factores=_factores_prediccion(X),
    )


def _textos_resenas_y1(appid: int) -> list[str]:
    con = sqlite3.connect(_DB_PATH)
    try:
        filas = con.execute(
            "SELECT texto FROM resenas WHERE appid = ? AND playtime_at_review < 120 AND voted_up = 0",
            (appid,),
        ).fetchall()
    finally:
        con.close()
    return [texto for (texto,) in filas if texto]


def motivos_frecuentes(appid: int) -> dict:
    """Motivos de arrepentimiento temprano (señal proxy: Y=1) más frecuentes en
    el texto de esas reseñas, por conteo de palabras clave por categoría — sin
    modelo de lenguaje.

    Las seis categorías no cubren todo el texto libre: `frecuencia` se calcula
    sobre las reseñas clasificadas (con al menos una categoría), no sobre el
    total de casos Y=1, para no verse artificialmente baja cuando la cobertura
    de las categorías es parcial. `pct_clasificados` es esa cobertura.
    """
    sin_datos = {"n_casos": 0, "pct_clasificados": 0.0, "motivos": []}

    textos = _textos_resenas_y1(appid)
    n_casos = len(textos)
    if n_casos < _UMBRAL_MIN_CASOS:
        logger.info("appid=%s con %s casos Y=1 (< %s): sin motivos, muestra insuficiente", appid, n_casos, _UMBRAL_MIN_CASOS)
        return {**sin_datos, "n_casos": n_casos}

    conteos = {categoria: 0 for categoria in _PATRONES_MOTIVOS}
    n_clasificados = 0
    for texto in textos:
        categorias_encontradas = [c for c, patron in _PATRONES_MOTIVOS.items() if patron.search(texto)]
        if not categorias_encontradas:
            continue
        n_clasificados += 1
        for categoria in categorias_encontradas:
            conteos[categoria] += 1

    if n_clasificados == 0:
        logger.info("appid=%s: ninguna reseña Y=1 clasificada en alguna categoría", appid)
        return {**sin_datos, "n_casos": n_casos}

    motivos = [
        MotivoInsatisfaccion(motivo=categoria, frecuencia=round(conteo / n_clasificados, 2))
        for categoria, conteo in conteos.items()
        if conteo > 0
    ]
    motivos.sort(key=lambda m: m.frecuencia, reverse=True)
    pct_clasificados = round(n_clasificados / n_casos, 4)
    logger.info(
        "motivos appid=%s n_casos=%s n_clasificados=%s pct_clasificados=%.2f categorias_con_señal=%s",
        appid, n_casos, n_clasificados, pct_clasificados, len(motivos),
    )
    return {"n_casos": n_casos, "pct_clasificados": pct_clasificados, "motivos": motivos}
