import logging

from fastapi import FastAPI, HTTPException

from . import catalogo, scoring
from .schemas import (
    ExplicacionJuego,
    FormularioAlta,
    JuegoCatalogo,
    PerfilJugador,
    PrediccionRiesgo,
    SolicitudPrediccion,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NexPlay",
    description="Riesgo de arrepentimiento temprano al comprar un videojuego (señal proxy, no observada).",
)

_UMBRAL_VETERANO_COMPRAS = 10
_UMBRAL_DISPONIBILIDAD_ALTA = 10
_UMBRAL_DISPONIBILIDAD_MEDIA = 4


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
        tolerancia_friccion=formulario.tolerancia_friccion,
        tags_preferidos=formulario.tags_preferidos,
        tags_rechazados=formulario.tags_rechazados,
        plataforma=formulario.plataforma,
        segmento=segmento,
        disponibilidad=disponibilidad,
    )


@app.get("/catalogo", response_model=list[JuegoCatalogo])
def buscar_catalogo(q: str = "") -> list[JuegoCatalogo]:
    return catalogo.buscar(q)


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
    return ExplicacionJuego(appid=appid, nombre=juego.nombre, motivos=scoring.motivos_frecuentes(appid))
