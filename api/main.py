import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import catalogo, scoring
from .schemas import (
    ExplicacionJuego,
    FormularioAlta,
    JuegoCatalogo,
    NivelFriccion,
    NivelRiesgo,
    PerfilJugador,
    PrediccionRiesgo,
    SolicitudPrediccion,
)

app = FastAPI(
    title="NexPlay",
    description="Riesgo de arrepentimiento temprano al comprar un videojuego (señal proxy, no observada).",
)

# Orígenes de desarrollo (Gradio y Angular locales) siempre permitidos;
# NEXPLAY_CORS_ORIGENES agrega orígenes adicionales separados por coma.
_ORIGENES_DEV = ["http://localhost:7860", "http://localhost:4200"]
_origenes_extra = [o.strip() for o in os.environ.get("NEXPLAY_CORS_ORIGENES", "").split(",") if o.strip()]
_origenes_permitidos = list(dict.fromkeys(_ORIGENES_DEV + _origenes_extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origenes_permitidos,
    allow_methods=["*"],
    allow_headers=["*"],
)

_UMBRAL_VETERANO_COMPRAS = 10
_UMBRAL_DISPONIBILIDAD_ALTA = 10
_UMBRAL_DISPONIBILIDAD_MEDIA = 4
_UMBRAL_FRICCION_ALTA = 4
_UMBRAL_FRICCION_MEDIA = 3


def _derivar_tolerancia_friccion(escala: int) -> NivelFriccion:
    if escala >= _UMBRAL_FRICCION_ALTA:
        return NivelFriccion.ALTA
    if escala >= _UMBRAL_FRICCION_MEDIA:
        return NivelFriccion.MEDIA
    return NivelFriccion.BAJA


def _derivar_perfil(formulario: FormularioAlta) -> PerfilJugador:
    segmento = "veterano" if formulario.compras_al_anio >= _UMBRAL_VETERANO_COMPRAS else "novato"

    if formulario.horas_por_semana >= _UMBRAL_DISPONIBILIDAD_ALTA:
        disponibilidad = "alta"
    elif formulario.horas_por_semana >= _UMBRAL_DISPONIBILIDAD_MEDIA:
        disponibilidad = "media"
    else:
        disponibilidad = "baja"

    return PerfilJugador(
        compras_al_anio=formulario.compras_al_anio,
        horas_por_semana=formulario.horas_por_semana,
        tolerancia_friccion=_derivar_tolerancia_friccion(formulario.tolerancia_friccion),
        tags_preferidos=formulario.tags_preferidos,
        tags_rechazados=formulario.tags_rechazados,
        plataforma=formulario.plataforma,
        segmento=segmento,
        disponibilidad=disponibilidad,
    )


@app.get("/catalogo", response_model=list[JuegoCatalogo])
def buscar_catalogo(q: str = "", genero: str = "", riesgo: NivelRiesgo | None = None) -> list[JuegoCatalogo]:
    return catalogo.buscar(q, genero, riesgo)


@app.post("/perfil", response_model=PerfilJugador)
def crear_perfil(formulario: FormularioAlta) -> PerfilJugador:
    perfil = _derivar_perfil(formulario)
    logger.info("perfil derivado: segmento=%s disponibilidad=%s", perfil.segmento, perfil.disponibilidad)
    return perfil


@app.post("/prediccion", response_model=PrediccionRiesgo)
def predecir_riesgo(solicitud: SolicitudPrediccion) -> PrediccionRiesgo:
    if catalogo.obtener(solicitud.appid) is None:
        raise HTTPException(status_code=404, detail="appid no encontrado en el catálogo")
    return scoring.predecir(solicitud.perfil, solicitud.appid)


@app.get("/explicacion/{appid}", response_model=ExplicacionJuego)
def explicar_juego(appid: int) -> ExplicacionJuego:
    juego = catalogo.obtener(appid)
    if juego is None:
        raise HTTPException(status_code=404, detail="appid no encontrado en el catálogo")
    return ExplicacionJuego(appid=appid, nombre=juego.nombre, **scoring.motivos_frecuentes(appid))
