import logging
import os
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from . import catalogo, estado, limites, nia, panorama, scoring, valoraciones
from .config import VECES_POR_IP, configuracion
from .schemas import (
    BuzonSugerencias,
    Comentario,
    EstadoSistema,
    ExplicacionJuego,
    RespuestaNia,
    FormularioAlta,
    JuegoCatalogo,
    NivelFriccion,
    NivelRiesgo,
    OpinionNia,
    PanoramaCatalogo,
    PerfilJugador,
    PrediccionRiesgo,
    ReaccionComentario,
    ResumenValoraciones,
    SolicitudComentario,
    SolicitudEdicionComentario,
    SolicitudNia,
    SolicitudPrediccion,
    SolicitudReaccion,
    SolicitudQuitarVotoNia,
    SolicitudValoracion,
    SolicitudVotoNia,
    VotoNia,
)

app = FastAPI(
    title="NexPlay",
    description="Riesgo de arrepentimiento temprano al comprar un videojuego (señal proxy, no observada).",
)

# Origen de desarrollo (el frontend de Angular local) siempre permitido;
# NEXPLAY_CORS_ORIGENES agrega orígenes adicionales separados por coma.
_ORIGENES_DEV = ["http://localhost:4200"]
_origenes_extra = [o.strip() for o in os.environ.get("NEXPLAY_CORS_ORIGENES", "").split(",") if o.strip()]
_origenes_permitidos = list(dict.fromkeys(_ORIGENES_DEV + _origenes_extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origenes_permitidos,
    allow_methods=["*"],
    allow_headers=["*"],
    # Un 429 dice cuándo volver a intentar; sin exponerlo, el navegador no deja leerlo.
    expose_headers=["Retry-After"],
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


@app.get("/estado", response_model=EstadoSistema)
def ver_estado() -> EstadoSistema:
    """El sistema de un vistazo, para la vista de Administración: sin consultas a la base, así
    que en Render también dice, rápido, si el servicio ya despertó."""
    return estado.estado()


@app.get("/panorama", response_model=PanoramaCatalogo)
def ver_panorama() -> PanoramaCatalogo:
    """Cuántas reseñas hay detrás del catálogo, de cuándo son y cuántas traen la señal.
    Se calcula al arrancar, no por petición."""
    return panorama.resumen()


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


def _ip_del_cliente(peticion: Request) -> str:
    """La IP de quien pide, para los topes por IP. Render está detrás de Cloudflare, que pone la
    IP de origen en CF-Connecting-IP y sobrescribe la que mande el cliente. X-Forwarded-For, la
    que toma uvicorn con --forwarded-allow-ips='*', la controla el cliente: con una falsa en cada
    petición se saltaba el tope. Sin Cloudflare (en local), la del socket."""
    cloudflare = peticion.headers.get("cf-connecting-ip", "").strip()
    if cloudflare:
        return cloudflare
    return peticion.client.host if peticion.client else "sin-ip"


def _topes(variable: str, por_omision: int) -> tuple[limites.LimitePorVentana, limites.LimitePorVentana]:
    """El tope por persona y, aparte, el de la IP: un salón con el mismo Wi-Fi comparte la IP,
    así que su tope es VECES_POR_IP el de una persona, salvo que <variable>_IP diga otro."""
    por_persona = int(os.environ.get(variable, str(por_omision)))
    por_ip = int(os.environ.get(f"{variable}_IP", str(VECES_POR_IP * por_persona)))
    return limites.LimitePorVentana(por_persona, 60.0), limites.LimitePorVentana(por_ip, 60.0)


# Los comentarios son un hilo público: se insertan y no se editan. El tope por ventana
# frena el spam sin moderación; al reiniciar la API los contadores vuelven a cero.
_LIMITE_COMENTARIOS, _LIMITE_COMENTARIOS_IP = _topes("NEXPLAY_COMENTARIOS_POR_MINUTO", 3)


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

    espera = limites.revisar_juntos(
        (_LIMITE_COMENTARIOS, f"usuario:{solicitud.usuario}"),
        (_LIMITE_COMENTARIOS_IP, f"ip:{_ip_del_cliente(peticion)}"),
    )
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
_LIMITE_REACCIONES, _LIMITE_REACCIONES_IP = _topes("NEXPLAY_REACCIONES_POR_MINUTO", 30)


@app.put("/comentarios/{appid}/{id_comentario}/reaccion", response_model=ReaccionComentario)
def reaccionar(
    appid: int, id_comentario: int, solicitud: SolicitudReaccion, peticion: Request
) -> ReaccionComentario:
    _exigir_juego(appid)

    espera = limites.revisar_juntos(
        (_LIMITE_REACCIONES, f"reaccion-usuario:{solicitud.usuario}"),
        (_LIMITE_REACCIONES_IP, f"reaccion-ip:{_ip_del_cliente(peticion)}"),
    )
    if espera:
        logger.info("reacción rechazada por frecuencia appid=%s id=%s", appid, id_comentario)
        raise HTTPException(
            status_code=429,
            detail="Estás reaccionando muy seguido. Espera un momento.",
            headers={"Retry-After": str(max(1, int(espera) + 1))},
        )

    with _errores_de_comentario():
        return ReaccionComentario(**valoraciones.alternar_reaccion(appid, id_comentario, solicitud.usuario))


@app.get("/nia/opiniones", response_model=list[OpinionNia])
def opiniones_de_nia(
    appids: str = Query(
        ...,
        pattern=r"^\d{1,9}(,\d{1,9}){0,5}$",
        description="Hasta 6 appids separados por coma",
    ),
) -> list[OpinionNia]:
    """La opinión corta de Nia sobre cada juego pedido, para el carrusel del Inicio. Sale de
    las reglas del chat con los datos del catálogo: sin modelo de lenguaje y sin guardar
    nada. Un appid que no está en el catálogo se omite."""
    pedidos = [int(appid) for appid in appids.split(",")]
    return [
        OpinionNia(**nia.reglas.opinion_corta(appid)) for appid in pedidos if catalogo.obtener(appid) is not None
    ]


# Nia consulta un modelo de pago: el tope por ventana es un límite de costo. El global solo
# cuenta con modelo y acota el gasto aunque alguien cambie de id y de IP en cada pregunta.
_LIMITE_NIA = limites.LimitePorVentana(configuracion.nexplay_nia_por_minuto, 60.0)
_LIMITE_NIA_IP = limites.LimitePorVentana(
    configuracion.nexplay_nia_por_minuto_ip or VECES_POR_IP * configuracion.nexplay_nia_por_minuto, 60.0
)
_LIMITE_NIA_GLOBAL = limites.LimitePorVentana(configuracion.nexplay_nia_por_minuto_global, 60.0)


def _exigir_cupo_de_nia(usuario: str, ip: str) -> float:
    topes = [(_LIMITE_NIA, f"nia-usuario:{usuario}"), (_LIMITE_NIA_IP, f"nia-ip:{ip}")]
    if configuracion.hay_openai:
        topes.append((_LIMITE_NIA_GLOBAL, "nia-global"))
    return limites.revisar_juntos(*topes)


@app.post("/nia", response_model=RespuestaNia)
def preguntar_a_nia(solicitud: SolicitudNia, peticion: Request) -> RespuestaNia:
    # Sin appid, la pregunta es del catálogo entero y no hay juego que exigir.
    if solicitud.appid is not None:
        _exigir_juego(solicitud.appid)

    espera = _exigir_cupo_de_nia(solicitud.usuario, _ip_del_cliente(peticion))
    if espera:
        logger.info("pregunta a Nia rechazada por frecuencia appid=%s", solicitud.appid)
        raise HTTPException(
            status_code=429,
            detail="Nia está recibiendo muchas preguntas seguidas. Espera un momento.",
            headers={"Retry-After": str(max(1, int(espera) + 1))},
        )

    # Los géneros no van al registro: solo el appid y el modo.
    respuesta = nia.responder(
        solicitud.appid, solicitud.mensajes, solicitud.usuario, solicitud.sugerencias, generos=solicitud.generos
    )
    logger.info("respuesta de Nia appid=%s modo=%s", solicitud.appid, respuesta["modo"])
    return RespuestaNia(**respuesta)


@contextmanager
def _errores_de_voto():
    """404 cuando se vota una respuesta que ya no está: o nunca existió o venció su
    retención de {dias} días."""
    try:
        yield
    except valoraciones.RespuestaNiaInexistente:
        raise HTTPException(
            status_code=404,
            detail=(
                "esa respuesta ya no se puede valorar: las preguntas y respuestas se guardan"
                f" {valoraciones.DIAS_DE_RETENCION_NIA} días"
            ),
        ) from None


# El voto no comparte el tope con los comentarios: escribir un comentario es publicar y
# cambiar de opinión sobre un motivo es corregirse, y corregirse dos veces seguidas no es
# spam. Con el tope de los comentarios, probar los cuatro motivos daba 429.
_LIMITE_VOTOS_NIA, _LIMITE_VOTOS_NIA_IP = _topes("NEXPLAY_VOTOS_NIA_POR_MINUTO", 30)


def _exigir_cupo_de_voto(usuario: str, ip: str) -> None:
    espera = limites.revisar_juntos(
        (_LIMITE_VOTOS_NIA, f"voto-nia:{usuario}"), (_LIMITE_VOTOS_NIA_IP, f"voto-nia-ip:{ip}")
    )
    if espera:
        raise HTTPException(
            status_code=429,
            detail="Demasiados votos seguidos. Espera un momento.",
            headers={"Retry-After": str(max(1, int(espera) + 1))},
        )


@app.put("/nia/valoracion/{id_respuesta}", response_model=VotoNia)
def votar_respuesta_de_nia(id_respuesta: str, solicitud: SolicitudVotoNia, peticion: Request) -> VotoNia:
    _exigir_cupo_de_voto(solicitud.usuario, _ip_del_cliente(peticion))
    # La sugerencia se ve en el buzón de /admin: sin correos ni teléfonos, igual que las preguntas.
    sugerencia = nia.agente.sin_datos_personales(solicitud.sugerencia) if solicitud.sugerencia else None
    with _errores_de_voto():
        voto = valoraciones.guardar_voto_nia(
            id_respuesta, solicitud.usuario, solicitud.voto, solicitud.motivo, sugerencia
        )
    logger.info(
        "voto a Nia %s motivo=%r con sugerencia=%s", "👍" if solicitud.voto == 1 else "👎", voto["motivo"],
        voto["sugerencia"] is not None,
    )
    return VotoNia(**voto)


@app.get("/nia/sugerencias", response_model=BuzonSugerencias)
def buzon_de_sugerencias() -> BuzonSugerencias:
    """El buzón de /admin: cuántos 👍 y 👎 recibió Nia, los 👎 por motivo y las últimas
    sugerencias de texto, sin usuario ni pregunta."""
    return BuzonSugerencias(**valoraciones.buzon_de_sugerencias())


@app.delete("/nia/valoracion/{id_respuesta}", response_model=VotoNia)
def quitar_voto_de_nia(id_respuesta: str, solicitud: SolicitudQuitarVotoNia, peticion: Request) -> VotoNia:
    """El usuario va en el cuerpo, como en el PUT: en la URL acabaría escrito en los
    registros del servidor y en el historial del navegador."""
    _exigir_cupo_de_voto(solicitud.usuario, _ip_del_cliente(peticion))
    with _errores_de_voto():
        return VotoNia(**valoraciones.borrar_voto_nia(id_respuesta, solicitud.usuario))
