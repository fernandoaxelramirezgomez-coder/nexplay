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
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from analisis.motivos import PALABRAS_CLAVE_POR_CATEGORIA, categorias_de

from .schemas import (
    AvisoEstimacion,
    DireccionFactor,
    Evidencia,
    FactorPrediccion,
    MotivoInsatisfaccion,
    NivelFriccion,
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
UMBRAL_MIN_CASOS = 5

# Por debajo de este aporte (en log-odds), un factor "casi no mueve la estimación" y se muestra
# sin flecha. Es el menor umbral que deja 0 flechas contradiciendo la cifra que se muestra
# (nota contra el promedio del catálogo, precio contra la mediana): con 0.05 quedaban cinco
# notas de 86 que el modelo lee por debajo de su media de entrenamiento (86.97).
UMBRAL_TIPICO = 0.10

# Qué tan firme es cada efecto, según el bootstrap sobre juegos de los coeficientes del
# modelo B+ (notebook 00, §3.4): la crítica no cruza el cero; precio, descuento y gratuidad,
# sí. Las compras del jugador no están en el modelo de título.
_EVIDENCIA_POR_VARIABLE = {
    "metacritic_disponible": Evidencia.SOLIDA,
    "metacritic": Evidencia.SOLIDA,
    "log_precio_final": Evidencia.DEBIL,
    "descuento": Evidencia.DEBIL,
    "es_gratis": Evidencia.DEBIL,
    "log_num_games_owned": Evidencia.DEBIL,
}

_AVISO_PRECIO_IMPUTADO = (
    "Estimación menos confiable: a este juego le falta el precio y el modelo lo tomó como 0, "
    "lo que tiende a bajar su riesgo estimado."
)

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


def ficha_del_modelo() -> dict:
    """Con qué se entrenó el modelo servido: versión, corte de datos, juegos y reseñas. Sale
    del artefacto ya cargado; lo lee el Inicio para decir con cuántos juegos que no vio se
    probó. Los artefactos viejos sin estos campos devuelven None."""
    return {
        "version": _VERSION_MODELO,
        "datos": _ARTEFACTO.get("datos_tag"),
        "juegos_entrenamiento": _ARTEFACTO.get("juegos_entrenamiento"),
        "resenas_entrenamiento": _ARTEFACTO.get("filas_entrenamiento"),
    }


_REFERENCIAS: dict | None = None


def referencias_del_catalogo() -> dict:
    """Contra qué se leen la nota y el precio: el promedio de la nota de los juegos que la
    tienen (un decimal, como lo muestra la ficha) y el precio mediano de los de pago con precio.
    La mediana y no el promedio: el modelo usa el logaritmo del precio, y su referencia se
    parece más a la mediana que al promedio, que los juegos caros inflan.

    Sale de la misma base que se sirve y no de api.catalogo, que importa este módulo y
    puntúa cada juego al cargarse."""
    global _REFERENCIAS
    if _REFERENCIAS is None:
        con = sqlite3.connect(_DB_PATH)
        try:
            filas = con.execute("SELECT es_gratis, precio_final, metacritic FROM juegos").fetchall()
        finally:
            con.close()
        notas = [nota for _, _, nota in filas if nota is not None]
        precios = [precio / 100 for gratis, precio, _ in filas if not gratis and precio is not None]
        _REFERENCIAS = {
            "nota_promedio": round(float(np.mean(notas)), 1) if notas else None,
            "precio_mediano": round(float(np.median(precios)), 2) if precios else None,
        }
    return _REFERENCIAS


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


def _construir_features(perfil: PerfilJugador, appid: int, juego: dict | None = None) -> pd.DataFrame:
    juego = juego if juego is not None else _atributos_juego(appid)
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


def _lectura_contra_el_catalogo(feature: str, juego: dict, estandarizado: float) -> dict:
    """La cifra del juego, la referencia del catálogo contra la que se lee y si queda por
    encima. En las variables de sí o no, "alto" es que se cumple."""
    referencias = referencias_del_catalogo()
    gratis = bool(juego["es_gratis"])
    if feature == "metacritic" and juego["metacritic"] is not None:
        valor, referencia = float(juego["metacritic"]), referencias["nota_promedio"]
        return {"valor": valor, "referencia": referencia, "alto": valor > referencia}
    if feature == "log_precio_final":
        if not gratis and juego["precio_final"] is None:
            return {"valor": None, "referencia": referencias["precio_mediano"], "alto": False, "imputado": True}
        valor = 0.0 if gratis else juego["precio_final"] / 100
        return {"valor": valor, "referencia": referencias["precio_mediano"], "alto": valor > referencias["precio_mediano"]}
    if feature == "descuento":
        return {"valor": float(juego["descuento"] or 0), "referencia": None, "alto": (juego["descuento"] or 0) > 0}
    if feature == "es_gratis":
        return {"valor": None, "referencia": None, "alto": gratis}
    if feature == "metacritic_disponible":
        return {"valor": None, "referencia": None, "alto": juego["metacritic"] is not None}
    return {"valor": None, "referencia": None, "alto": estandarizado > 0}


def _factores_prediccion(X: pd.DataFrame, juego: dict) -> list[FactorPrediccion]:
    """Contribución de cada variable al log-odds del score: coeficiente de la
    regresión logística por el valor ya estandarizado (mismo StandardScaler
    del pipeline), que es lo que la regresión logística realmente suma.
    Se devuelven las tres de mayor magnitud absoluta, en ese orden: el primero es siempre el
    que más aporta, aunque sea de evidencia débil o describa un precio que falta."""
    escalador = _PIPELINE.named_steps["escalar"]
    clf = _PIPELINE.named_steps["clf"]
    valores_estandarizados = escalador.transform(X)[0]
    contribuciones = clf.coef_[0] * valores_estandarizados

    factores = []
    for feature, valor_estandarizado, contribucion in zip(_FEATURES, valores_estandarizados, contribuciones):
        lectura = _lectura_contra_el_catalogo(feature, juego, valor_estandarizado)
        factores.append(
            FactorPrediccion(
                etiqueta=_ETIQUETAS_FEATURES[feature],
                valor_relativo=NivelRelativo.ALTO if lectura["alto"] else NivelRelativo.BAJO,
                contribucion=round(float(contribucion), 4),
                direccion=DireccionFactor.AUMENTA if contribucion > 0 else DireccionFactor.REDUCE,
                evidencia=_EVIDENCIA_POR_VARIABLE[feature],
                cerca_de_lo_tipico=bool(abs(contribucion) < UMBRAL_TIPICO),
                valor=lectura["valor"],
                referencia=lectura["referencia"],
                imputado=lectura.get("imputado", False),
            )
        )
    factores.sort(key=lambda f: abs(f.contribucion), reverse=True)
    return factores[:3]


def _avisos(juego: dict) -> list[AvisoEstimacion]:
    avisos = []
    if juego["es_gratis"]:
        gratis = _ARTEFACTO.get("gratis_entrenamiento")
        cuantos = f"solo {gratis} juegos gratis" if gratis is not None else "muy pocos juegos gratis"
        avisos.append(AvisoEstimacion(
            codigo="gratis_extrapola",
            texto=f"En los datos de entrenamiento había {cuantos}; para los gratis, el modelo extrapola.",
        ))
    elif juego["precio_final"] is None:
        avisos.append(AvisoEstimacion(codigo="precio_imputado", texto=_AVISO_PRECIO_IMPUTADO))
    return avisos


# Existe solo porque predecir() pide un perfil en su firma; ningún dato de este perfil
# mueve el score, porque el modelo es de título. Vive aquí, y no en cada módulo que
# necesita la banda de un juego, para que todos puntúen con lo mismo.
_PERFIL_NEUTRO = PerfilJugador(
    compras_al_anio=5,  # a medio camino entre 0 y el umbral de "veterano" (10)
    horas_por_semana=8,
    tolerancia_friccion=NivelFriccion.MEDIA,
    tags_preferidos=[],
    tags_rechazados=[],
    plataforma=Plataforma.PC,
    segmento="novato",
    disponibilidad="media",
)


def predecir(perfil: PerfilJugador, appid: int) -> PrediccionRiesgo:
    juego = _atributos_juego(appid)
    X = _construir_features(perfil, appid, juego)
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
        factores=_factores_prediccion(X, juego),
        avisos=_avisos(juego),
    )


def prediccion_de_titulo(appid: int) -> PrediccionRiesgo:
    """La predicción del juego, sin perfil: la banda y los factores que la mueven.

    Es lo que sirve el catálogo y lo que Nia usa para explicar la banda. El riesgo es del
    título, así que no hay una versión "para tu perfil" de esto."""
    return predecir(_PERFIL_NEUTRO, appid)


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


def contar_motivos(appid: int) -> tuple[dict[str, int], int, int]:
    """Cuántas reseñas Y=1 de este juego menciona cada categoría, cuántas se clasificaron
    en alguna y cuántos casos Y=1 hay en total.

    Devuelve conteos crudos y no frecuencias porque quien agrega todo el catálogo
    (api/panorama.py) necesita sumar reseñas, no promediar porcentajes de juegos con
    muestras de tamaños muy distintos."""
    textos = _textos_resenas_y1(appid)
    conteos = {categoria: 0 for categoria in PALABRAS_CLAVE_POR_CATEGORIA}
    n_clasificados = 0
    for texto in textos:
        categorias_encontradas = categorias_de(texto)
        if not categorias_encontradas:
            continue
        n_clasificados += 1
        for categoria in categorias_encontradas:
            conteos[categoria] += 1
    return conteos, n_clasificados, len(textos)


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

    conteos, n_clasificados, n_casos = contar_motivos(appid)
    if n_casos < UMBRAL_MIN_CASOS:
        logger.info("appid=%s con %s casos Y=1 (< %s): sin motivos, muestra insuficiente", appid, n_casos, UMBRAL_MIN_CASOS)
        return {**sin_datos, "n_casos": n_casos}

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
