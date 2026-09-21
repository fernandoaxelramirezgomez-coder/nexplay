import logging
import os
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from . import catalogo, limites, nia, scoring, valoraciones
from .config import configuracion
from .schemas import (
    Comentario,
    ExplicacionJuego,
    RespuestaNia,
    FormularioAlta,
    JuegoCatalogo,
    NivelFriccion,
    NivelRiesgo,
    PerfilJugador,
    PrediccionRiesgo,
    ReaccionComentario,
    ResumenValoraciones,
    SolicitudComentario,
    SolicitudEdicionComentario,
    SolicitudNia,
    SolicitudPrediccion,
    SolicitudReaccion,
    SolicitudValoracion,
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


# El id de usuario viaja como parámetro: es anónimo, lo genera el navegador y sirve para
# saber cuál valoración es suya, no para autenticar a nadie.
_USUARIO = Query(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
# En el hilo es opcional: sin él se lee igual, solo que nada sale marcado como propio.
_USUARIO_OPCIONAL = Query(None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


def _exigir_juego(appid: int) -> None:
    if catalogo.obtener(appid) is None:
        raise HTTPException(status_code=404, detail="appid no encontrado en el catálogo")


@app.get("/valoraciones/{appid}", response_model=ResumenValoraciones)
def ver_valoraciones(appid: int, usuario: str = _USUARIO) -> ResumenValoraciones:
    _exigir_juego(appid)
    return ResumenValoraciones(**valoraciones.resumen(appid, usuario))


@app.put("/valoraciones/{appid}", response_model=ResumenValoraciones)
def valorar(appid: int, solicitud: SolicitudValoracion) -> ResumenValoraciones:
    _exigir_juego(appid)
    logger.info("calificación appid=%s estrellas=%s", appid, solicitud.calificacion)
    return ResumenValoraciones(**valoraciones.guardar(appid, solicitud.usuario, solicitud.calificacion))


@app.delete("/valoraciones/{appid}", response_model=ResumenValoraciones)
def quitar_valoracion(appid: int, usuario: str = _USUARIO) -> ResumenValoraciones:
    _exigir_juego(appid)
    return ResumenValoraciones(**valoraciones.borrar(appid, usuario))


# Los comentarios son un hilo público: se insertan y no se editan. El tope por ventana
# frena el spam sin moderación; al reiniciar la API los contadores vuelven a cero.
_LIMITE_COMENTARIOS = limites.LimitePorVentana(
    maximo=int(os.environ.get("NEXPLAY_COMENTARIOS_POR_MINUTO", "3")), ventana_segundos=60.0
)


@contextmanager
def _errores_de_comentario():
    """403 y 404 del hilo, en un solo lugar: el módulo no sabe de HTTP."""
    try:
        yield
    except valoraciones.ComentarioInexistente:
        raise HTTPException(status_code=404, detail="comentario no encontrado") from None
    except valoraciones.ComentarioAjeno:
        raise HTTPException(
            status_code=403, detail="ese comentario es de otra persona: solo quien lo escribió puede cambiarlo"
        ) from None


@app.get("/comentarios/{appid}", response_model=list[Comentario])
def ver_comentarios(appid: int, usuario: str | None = _USUARIO_OPCIONAL) -> list[Comentario]:
    _exigir_juego(appid)
    return [Comentario(**comentario) for comentario in valoraciones.comentarios(appid, usuario)]


@app.post("/comentarios/{appid}", response_model=list[Comentario], status_code=201)
def comentar(appid: int, solicitud: SolicitudComentario, peticion: Request) -> list[Comentario]:
    _exigir_juego(appid)

    ip = peticion.client.host if peticion.client else "sin-ip"
    espera = _LIMITE_COMENTARIOS.revisar(f"usuario:{solicitud.usuario}", f"ip:{ip}")
    if espera:
        logger.info("comentario rechazado por frecuencia appid=%s", appid)
        raise HTTPException(
            status_code=429,
            detail="Estás comentando muy seguido. Espera un momento antes de enviar otro.",
            headers={"Retry-After": str(max(1, int(espera) + 1))},
        )

    logger.info("comentario nuevo appid=%s largo=%s", appid, len(solicitud.texto))
    return [
        Comentario(**comentario)
        for comentario in valoraciones.agregar_comentario(appid, solicitud.usuario, solicitud.texto)
    ]


@app.put("/comentarios/{appid}/{id_comentario}", response_model=list[Comentario])
def editar_comentario(appid: int, id_comentario: int, solicitud: SolicitudEdicionComentario) -> list[Comentario]:
    _exigir_juego(appid)
    with _errores_de_comentario():
        hilo = valoraciones.editar_comentario(appid, id_comentario, solicitud.usuario, solicitud.texto)
    logger.info("comentario editado appid=%s id=%s", appid, id_comentario)
    return [Comentario(**comentario) for comentario in hilo]


@app.delete("/comentarios/{appid}/{id_comentario}", response_model=list[Comentario])
def borrar_comentario(appid: int, id_comentario: int, usuario: str = _USUARIO) -> list[Comentario]:
    _exigir_juego(appid)
    with _errores_de_comentario():
        hilo = valoraciones.borrar_comentario_propio(appid, id_comentario, usuario)
    logger.info("comentario borrado por su dueño appid=%s id=%s", appid, id_comentario)
    return [Comentario(**comentario) for comentario in hilo]


# Reaccionar es un clic, no escribir: el tope es más alto que el de publicar, pero existe
# para que no sea un hueco de spam.
_LIMITE_REACCIONES = limites.LimitePorVentana(
    maximo=int(os.environ.get("NEXPLAY_REACCIONES_POR_MINUTO", "30")), ventana_segundos=60.0
)


@app.put("/comentarios/{appid}/{id_comentario}/reaccion", response_model=ReaccionComentario)
def reaccionar(
    appid: int, id_comentario: int, solicitud: SolicitudReaccion, peticion: Request
) -> ReaccionComentario:
    _exigir_juego(appid)

    ip = peticion.client.host if peticion.client else "sin-ip"
    espera = _LIMITE_REACCIONES.revisar(f"reaccion-usuario:{solicitud.usuario}", f"reaccion-ip:{ip}")
    if espera:
        logger.info("reacción rechazada por frecuencia appid=%s id=%s", appid, id_comentario)
        raise HTTPException(
            status_code=429,
            detail="Estás reaccionando muy seguido. Espera un momento.",
            headers={"Retry-After": str(max(1, int(espera) + 1))},
        )

    with _errores_de_comentario():
        return ReaccionComentario(**valoraciones.alternar_reaccion(appid, id_comentario, solicitud.usuario))


# Nia consulta un modelo de pago: el tope por ventana es un límite de costo.
_LIMITE_NIA = limites.LimitePorVentana(maximo=configuracion.nexplay_nia_por_minuto, ventana_segundos=60.0)


@app.post("/nia", response_model=RespuestaNia)
def preguntar_a_nia(solicitud: SolicitudNia, peticion: Request) -> RespuestaNia:
    _exigir_juego(solicitud.appid)

    ip = peticion.client.host if peticion.client else "sin-ip"
    espera = _LIMITE_NIA.revisar(f"nia-usuario:{solicitud.usuario}", f"nia-ip:{ip}")
    if espera:
        logger.info("pregunta a Nia rechazada por frecuencia appid=%s", solicitud.appid)
        raise HTTPException(
            status_code=429,
            detail="Nia está recibiendo muchas preguntas seguidas. Espera un momento.",
            headers={"Retry-After": str(max(1, int(espera) + 1))},
        )

    respuesta = nia.responder(solicitud.appid, solicitud.mensajes, solicitud.perfil)
    logger.info("respuesta de Nia appid=%s modo=%s", solicitud.appid, respuesta["modo"])
    return RespuestaNia(**respuesta)
