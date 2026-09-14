"""Regla de oro: esta función tiene firma estable. Hoy simula el riesgo; cuando
el modelo (GroupKFold por appid, optimizado a PR-AUC) esté entrenado, esta capa
carga el .pkl desde modelo/ y predice con las mismas entradas y salida. Nada
fuera de este archivo debe cambiar cuando eso pase."""

import hashlib
import logging
import random

from .schemas import MotivoInsatisfaccion, NivelRiesgo, PerfilJugador, Plataforma, PrediccionRiesgo

logger = logging.getLogger(__name__)

_VERSION_MODELO = "simulado-0.1"

_UMBRAL_MEDIO = 0.33
_UMBRAL_ALTO = 0.66

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


def _nivel_desde_riesgo(riesgo: float) -> NivelRiesgo:
    if riesgo < _UMBRAL_MEDIO:
        return NivelRiesgo.BAJO
    if riesgo < _UMBRAL_ALTO:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.ALTO


def _riesgo_simulado(perfil: PerfilJugador, appid: int) -> float:
    # Determinista: hash estable del perfil + appid, no random.
    # Así el simulador se comporta como se comportará el modelo real
    # (misma entrada -> misma salida) sin necesitar el .pkl todavía.
    clave = f"{appid}|{perfil.model_dump_json()}"
    digest = hashlib.sha256(clave.encode("utf-8")).hexdigest()
    return round(int(digest[:8], 16) / 0xFFFFFFFF, 4)


def predecir(perfil: PerfilJugador, appid: int) -> PrediccionRiesgo:
    riesgo = _riesgo_simulado(perfil, appid)
    nota_plataforma = (
        _NOTA_PLATAFORMA_SIN_DATOS.format(plataforma=perfil.plataforma.value)
        if perfil.plataforma != Plataforma.PC
        else None
    )
    logger.info("prediccion simulada appid=%s riesgo=%.4f", appid, riesgo)
    return PrediccionRiesgo(
        appid=appid,
        riesgo=riesgo,
        nivel=_nivel_desde_riesgo(riesgo),
        modelo_version=_VERSION_MODELO,
        nota_plataforma=nota_plataforma,
    )


def motivos_frecuentes(appid: int) -> list[MotivoInsatisfaccion]:
    # rng propio (no random global) para que la respuesta sea estable por appid
    # sin afectar la aleatoriedad de predecir().
    rng = random.Random(appid)
    motivos = rng.sample(_MOTIVOS_SIMULADOS, k=rng.randint(2, 4))
    frecuencias = sorted((round(rng.uniform(0.05, 0.6), 2) for _ in motivos), reverse=True)
    return [MotivoInsatisfaccion(motivo=m, frecuencia=f) for m, f in zip(motivos, frecuencias)]
