"""Contratos Pydantic de entrada y salida de la API. Fuente única de verdad
del contrato: cualquier cambio aquí es un cambio de contrato con el cliente (UI)."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Plataforma(str, Enum):
    PC = "pc"
    PLAYSTATION = "playstation"
    XBOX = "xbox"
    NINTENDO = "nintendo"


class NivelFriccion(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class NivelRiesgo(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


class DireccionFactor(str, Enum):
    AUMENTA = "aumenta"
    REDUCE = "reduce"


class NivelRelativo(str, Enum):
    ALTO = "alto"
    BAJO = "bajo"


class Evidencia(str, Enum):
    SOLIDA = "solida"
    DEBIL = "debil"


def _normalizar_tags(tags: list[str]) -> list[str]:
    return [t.strip().lower() for t in tags if t.strip()]


class FormularioAlta(BaseModel):
    """Datos que el jugador declara al darse de alta (no se infieren)."""

    compras_al_anio: int = Field(
        ..., ge=0, le=365, description="Juegos comprados en el último año; sustituto de num_games_owned"
    )
    horas_por_semana: float = Field(..., ge=0, le=168, description="Horas disponibles para jugar por semana")
    tolerancia_friccion: int = Field(
        ..., ge=1, le=5, description="Escala 1 (nula tolerancia a la fricción) a 5 (muy alta)"
    )
    tags_preferidos: list[str] = Field(
        default_factory=list, description="Tags de Steam que el jugador busca en un juego"
    )
    tags_rechazados: list[str] = Field(
        default_factory=list, description="Tags de Steam que el jugador evita"
    )
    plataforma: Plataforma

    @field_validator("tags_preferidos", "tags_rechazados")
    @classmethod
    def _validar_tags(cls, valor: list[str]) -> list[str]:
        return _normalizar_tags(valor)


class PerfilJugador(BaseModel):
    """Perfil derivado del formulario de alta. Es lo que consume /prediccion.

    Los rangos son los mismos que en FormularioAlta y no son decorativos: scoring.py
    calcula log1p(compras_al_anio), que con un valor negativo da NaN y hace fallar al
    modelo. Sin estos límites, un perfil inválido salía como 500 en vez de 422."""

    compras_al_anio: int = Field(..., ge=0, le=365)
    horas_por_semana: float = Field(..., ge=0, le=168)
    tolerancia_friccion: NivelFriccion = Field(
        ..., description="'baja', 'media' o 'alta', heurística sobre la escala 1-5 declarada"
    )
    tags_preferidos: list[str]
    tags_rechazados: list[str]
    plataforma: Plataforma
    segmento: str = Field(..., description="'novato' o 'veterano', heurística sobre compras_al_anio")
    disponibilidad: str = Field(..., description="'baja', 'media' o 'alta', heurística sobre horas_por_semana")


class JuegoCatalogo(BaseModel):
    appid: int
    nombre: str
    plataformas: list[Plataforma]
    generos: list[str] = Field(default_factory=list, description="Géneros de Steam (no tags de usuario)")
    metacritic: Optional[int] = Field(None, description="Nota de Metacritic; None si el juego no tiene cobertura")
    es_gratis: bool = False
    precio_final: Optional[float] = Field(
        None, description="En unidades de moneda (ya convertido de centavos); None si no hay precio disponible"
    )
    moneda: Optional[str] = None
    fecha_lanzamiento: Optional[str] = None
    descripcion: Optional[str] = Field(
        None,
        description="short_description de Steam; None cuando la tienda solo la tiene en inglés (ver catalogo.py)",
    )
    portada_url: str = Field(..., description="Campo derivado del appid, no una columna de la base")
    video_url: Optional[str] = Field(
        None, description="Primer tráiler de Steam en HLS (.m3u8); None si el juego no tiene videos"
    )
    tienda_url: str = Field(..., description="Campo derivado del appid, no una columna de la base")
    banda_riesgo: NivelRiesgo = Field(
        ..., description="Riesgo estimado del título (ver catalogo.py); es el mismo para cualquier perfil"
    )
    riesgo: float = Field(
        ..., ge=0, le=1, description="Score numérico del título; para ordenar dentro de una banda, no para mostrar como probabilidad"
    )


class SolicitudPrediccion(BaseModel):
    perfil: PerfilJugador
    appid: int = Field(..., description="appid de Steam del juego a evaluar")


class FactorPrediccion(BaseModel):
    etiqueta: str = Field(..., description="Variable del modelo en lenguaje claro, no el nombre técnico")
    valor_relativo: NivelRelativo = Field(
        ...,
        description="Nota y precio: si el valor está por encima de la referencia del catálogo. En las variables de sí o "
        "no (gratis, con nota, con descuento): alto si se cumple",
    )
    contribucion: float = Field(
        ..., description="Coeficiente × valor estandarizado de la variable; unidades de log-odds, no de probabilidad"
    )
    direccion: DireccionFactor = Field(..., description="Si esta variable aumenta o reduce el riesgo estimado")
    evidencia: Evidencia = Field(
        ...,
        description="Sólida si su efecto no cruza el cero en el bootstrap sobre juegos del notebook 00 (§3.4); débil "
        "si con 83 juegos no se distingue de cero",
    )
    cerca_de_lo_tipico: bool = Field(
        ..., description="Aporte menor que el umbral de lo típico: casi no mueve la estimación y se muestra sin flecha"
    )
    valor: Optional[float] = Field(
        None, description="La nota o el precio en MXN de este juego; None en las variables de sí o no y en el precio que falta"
    )
    referencia: Optional[float] = Field(
        None, description="Contra qué se lee el valor: el promedio de la nota o el precio mediano del catálogo, en MXN"
    )
    imputado: bool = Field(False, description="Falta el dato y el modelo usó un sustituto (el precio, tomado como 0)")


class AvisoEstimacion(BaseModel):
    codigo: Literal["gratis_extrapola", "precio_imputado"]
    texto: str


class PrediccionRiesgo(BaseModel):
    appid: int
    riesgo: float = Field(
        ..., ge=0, le=1, description="Probabilidad estimada de arrepentimiento temprano (proxy, no observado)"
    )
    nivel: NivelRiesgo
    modelo_version: str
    nota_plataforma: Optional[str] = Field(
        None, description="Advertencia si el perfil declara una plataforma sin datos de entrenamiento propios"
    )
    factores: list[FactorPrediccion] = Field(
        default_factory=list,
        description="Las tres variables con mayor contribución absoluta al score, ordenadas por magnitud",
    )
    avisos: list[AvisoEstimacion] = Field(
        default_factory=list, description="Lo que hace menos firme esta estimación: juegos gratis, precio que falta"
    )


class MotivoInsatisfaccion(BaseModel):
    motivo: str
    frecuencia: float = Field(
        ...,
        ge=0,
        le=1,
        description="Proporción de reseñas clasificadas (no del total Y=1) que mencionan este motivo",
    )


class SolicitudValoracion(BaseModel):
    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo generado por el navegador; identifica, no autentica",
    )
    # strict: un 3.5, un "3" o un true dan 422 en vez de convertirse en silencio.
    calificacion: int = Field(..., ge=1, le=5, strict=True, description="Estrellas, de 1 a 5")


class ResumenValoraciones(BaseModel):
    appid: int
    promedio: Optional[float] = Field(
        None, description="Promedio de estrellas; None si nadie ha calificado (no 0.0, que parecería una nota)"
    )
    total: int = Field(..., description="Cuántas personas calificaron la segunda opinión")
    mia: Optional[int] = Field(None, ge=1, le=5, description="Las estrellas de quien pregunta, si ya calificó")


class Comentario(BaseModel):
    """Entrada del hilo público. Nunca lleva el id de quien la escribió: `es_mio` ya
    responde lo único que el cliente necesita saber de esa identidad."""

    id: int
    texto: str
    creado: str = Field(..., description="Cuándo apareció en el hilo; no cambia al editar")
    actualizado: Optional[str] = Field(None, description="Cuándo se editó por última vez")
    editado: bool = False
    reacciones: int = Field(0, description="Cuántas personas le dieron pulgar arriba")
    reaccione_mia: bool = Field(False, description="Si quien pregunta ya reaccionó")
    es_mio: bool = Field(False, description="Si lo escribió quien pregunta; solo entonces puede editarlo")


class _TextoComentario(BaseModel):
    """Lo común entre publicar y editar: el mismo tope de 500 y el mismo id anónimo."""

    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo del navegador; se guarda para el límite de frecuencia, nunca se devuelve",
    )
    texto: str = Field(..., min_length=1, max_length=500)

    @field_validator("texto")
    @classmethod
    def _limpiar_texto(cls, valor: str) -> str:
        limpio = valor.strip()
        if not limpio:
            raise ValueError("el comentario no puede ser solo espacios")
        return limpio


class SolicitudComentario(_TextoComentario):
    """POST /comentarios/{appid}: agrega uno al final del hilo."""


class SolicitudEdicionComentario(_TextoComentario):
    """PUT /comentarios/{appid}/{id}: solo el dueño cambia su propio texto."""


class SolicitudReaccion(BaseModel):
    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo del navegador; una reacción por persona y comentario",
    )


class ReaccionComentario(BaseModel):
    comentario_id: int
    reacciones: int
    reaccione_mia: bool


#: Lo que escribe la persona. Es el límite que importa: acota costo y abuso.
MAXIMO_PREGUNTA = 500
#: Lo que respondió Nia y vuelve en el historial. Sus respuestas son de 60 palabras o menos
#: (api/nia/agente.py, ajustar_largo), unos 450 caracteres; con 500 de tope una larga rompía la
#: pregunta siguiente, y con 4,000 cualquiera podía fabricar un historial de 40 «respuestas»
#: enormes para que lo mandáramos al modelo.
MAXIMO_RESPUESTA = 1500
#: Juegos que puede llevar una oferta o un mensaje de Nia: los de sus tarjetas.
MAXIMO_JUEGOS_DE_UN_MENSAJE = 8

#: Lo que Nia puede ofrecer al cerrar. Cada una la cumplen las reglas cuando la persona dice
#: «sí» (api/nia/reglas.py, _cumplir): una pregunta de cierre que no sea una de estas no se
#: puede cumplir, y calidad/verificar_nia.py lo revisa.
IntencionOferta = Literal[
    "riesgo", "resenas", "ficha", "resenas_de_varios", "ordenar", "buscar", "generos", "como_se_calcula",
    "de_donde_salen", "crear_perfil", "elegir_juego", "resumen", "aclarar",
]


class OfertaNia(BaseModel):
    """La pregunta con que cerró Nia, como dato: qué ofreció y de qué juegos. Vuelve en el
    historial para que «sí», «cuéntame» o «dale» la cumplan."""

    intencion: IntencionOferta
    juegos: list[int] = Field(
        default_factory=list, max_length=MAXIMO_JUEGOS_DE_UN_MENSAJE,
        description="De qué juegos es la oferta; vacía si es del catálogo",
    )
    criterio: Optional[Literal["precio", "riesgo", "nota"]] = Field(
        None, description="Para ordenar; None si la oferta es preguntar por cuál"
    )
    pregunta: Optional[str] = Field(
        None, max_length=MAXIMO_PREGUNTA, description="Para buscar: la búsqueda que ofreció, ya escrita"
    )


class MensajeChat(BaseModel):
    rol: Literal["usuario", "nia"]
    contenido: str = Field(..., min_length=1, max_length=MAXIMO_RESPUESTA)
    oferta: Optional[OfertaNia] = Field(None, description="Solo en mensajes de Nia: lo que ofreció al cerrar")
    juegos: list[int] = Field(
        default_factory=list, max_length=MAXIMO_JUEGOS_DE_UN_MENSAJE,
        description="Solo en mensajes de Nia: los juegos de sus tarjetas, a los que se refieren «esos dos» o «ese juego»",
    )

    @model_validator(mode="after")
    def _limitar_lo_que_escribe_la_persona(self) -> "MensajeChat":
        if self.rol == "usuario" and len(self.contenido) > MAXIMO_PREGUNTA:
            raise ValueError(f"la pregunta no puede pasar de {MAXIMO_PREGUNTA} caracteres")
        if self.rol == "usuario" and (self.oferta is not None or self.juegos):
            raise ValueError("solo los mensajes de Nia llevan oferta o juegos")
        return self


#: Mensajes del hilo que acepta /nia: la conversación entera, para que las reglas puedan
#: resumirla. Al modelo llegan solo los últimos turnos, con tope de caracteres (api/nia/agente.py).
MAXIMO_MENSAJES_NIA = 40


class SugerenciaNia(BaseModel):
    """Un juego que el navegador sugirió con el perfil declarado, con su porqué ya escrito.
    El perfil no viaja: solo esta lista, que es lo que Nia puede enseñar."""

    appid: int
    razones: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("razones")
    @classmethod
    def _razones_cortas(cls, razones: list[str]) -> list[str]:
        return [r.strip()[:120] for r in razones if r.strip()]


class SolicitudNia(BaseModel):
    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo del navegador; solo se usa para el límite de frecuencia",
    )
    appid: Optional[int] = Field(
        None, description="El juego del que se habla; sin él, Nia habla del catálogo entero"
    )
    mensajes: list[MensajeChat] = Field(..., min_length=1, max_length=MAXIMO_MENSAJES_NIA)
    perfil: Optional[PerfilJugador] = Field(
        None, description="Se acepta por compatibilidad y no se usa: el riesgo es del juego y el perfil no viaja a Nia"
    )
    sugerencias: list[SugerenciaNia] = Field(
        default_factory=list,
        max_length=6,
        description="Las sugerencias que el navegador calculó con el perfil; vacía si no hay perfil",
    )
    generos: list[str] = Field(
        default_factory=list,
        max_length=12,
        description="Los géneros que declaró la persona, para decir cuáles coinciden con un juego. No mueven el riesgo,"
        " no se guardan ni se registran; si Nia responde con IA, viajan a OpenAI junto con la pregunta",
    )

    @field_validator("generos")
    @classmethod
    def _generos_cortos(cls, generos: list[str]) -> list[str]:
        return [g.strip()[:40] for g in generos if g.strip()]


class RespuestaNia(BaseModel):
    respuesta: str
    # "reglas": hay modelo configurado pero esta respuesta no lo usó (pedir el juego, el
    # resumen, "el mejor", una pregunta que no es de juegos). No se muestra como «Con IA».
    modo: Literal["openai", "demostracion", "reglas"]
    modelo: Optional[str] = Field(None, description="Modelo usado; None en modo demostración")
    aviso: Optional[str] = Field(None, description="Qué mostrar cuando la respuesta no vino del modelo")
    id: str = Field(..., description="Identifica esta respuesta para poder votarla")
    pasos: list[str] = Field(
        default_factory=list, description="Qué consultó antes de responder, en orden; vacío si no consultó nada"
    )
    juegos: list[int] = Field(
        default_factory=list,
        description="Appids que la respuesta menciona y que una herramienta devolvió en este turno",
    )
    sugerencias: list[int] = Field(
        default_factory=list,
        description="Appids que se pintan como «Sugerencia según tu perfil»: salen de la lista que mandó el navegador",
    )
    oferta: Optional[OfertaNia] = Field(
        None, description="Lo que ofrece la pregunta con que cierra; el chat la devuelve en el historial"
    )
    pide_juego: bool = Field(False, description="La pregunta es de un juego y no hay ninguno fijado: el chat abre el buscador")
    pide_perfil: bool = Field(False, description="Pidieron sugerencias sin perfil: el chat invita a crearlo")
    fuera_de_tema: bool = Field(
        False,
        description="La pregunta no encaja con nada del catálogo: el chat muestra ahí sus avisos, y no antes",
    )
    version_prompt: str = Field(
        ..., description="Qué prompt la produjo: hash del texto del sistema, o 'reglas' en modo demostración"
    )


class OpinionNia(BaseModel):
    """La opinión corta de Nia sobre un juego, para el carrusel del Inicio. Sale de las
    reglas del chat con los datos del catálogo: no llama a ningún modelo ni se guarda."""

    appid: int
    nombre: str
    nivel: NivelRiesgo
    pregunta: str
    respuesta: str


class SolicitudVotoNia(BaseModel):
    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo generado por el navegador; identifica, no autentica",
    )
    voto: Literal[-1, 1] = Field(..., description="1 es 👍 y -1 es 👎; cualquier otro valor da 422")
    motivo: Optional[str] = Field(
        None,
        max_length=60,
        description="Solo acompaña al 👎, y solo uno de los motivos de la lista; con 👍 se ignora",
    )


class SolicitudQuitarVotoNia(BaseModel):
    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo generado por el navegador; va en el cuerpo, no en la URL",
    )


class VotoNia(BaseModel):
    id_respuesta: str
    voto: Optional[Literal[-1, 1]] = Field(None, description="None si esa persona no ha votado esta respuesta")
    motivo: Optional[str] = None


class ExplicacionJuego(BaseModel):
    appid: int
    nombre: str
    n_casos: int = Field(..., description="Reseñas Y=1 (arrepentimiento temprano) analizadas para este appid")
    pct_clasificados: float = Field(
        ...,
        ge=0,
        le=1,
        description="Proporción de esas reseñas que mencionan al menos una categoría de motivo",
    )
    motivos: list[MotivoInsatisfaccion]


class TramoPlaytime(BaseModel):
    """Cuántas reseñas se escribieron dentro de cada tramo de horas jugadas. El primero
    es el de la ventana de reembolso de Steam, que es donde se define la etiqueta."""

    tramo: str
    cuantas: int
    fraccion: float = Field(..., ge=0, le=1)


class VentanaMuestra(BaseModel):
    desde: str = Field(..., description="Fecha de la reseña más vieja, YYYY-MM-DD")
    hasta: str


class DescargasMuestra(BaseModel):
    """Cuándo se descargó cada fuente, del primer al último registro guardado (UTC). Es la
    fecha de la sección Fuentes y del pie; no dice nada de cuándo se escribieron las reseñas,
    eso es `ventana`."""

    appdetails: VentanaMuestra = Field(..., description="Los juegos: precio, géneros, Metacritic, tráileres")
    appreviews: VentanaMuestra = Field(..., description="Las reseñas")


class FichaModelo(BaseModel):
    """Con qué se entrenó el modelo servido. El Inicio cuenta cuántos juegos del catálogo
    quedaron fuera del entrenamiento: con esos se probó."""

    version: str
    datos: Optional[str] = Field(None, description="Tag del release de entrenamiento, p. ej. data-v1")
    juegos_entrenamiento: Optional[int] = None
    resenas_entrenamiento: Optional[int] = None


class CalidadMuestra(BaseModel):
    """Qué tan buena es la muestra de reseñas, en proporciones sobre el total descargado."""

    compradas_en_steam: float = Field(..., ge=0, le=1)
    recibidas_gratis: float = Field(..., ge=0, le=1)
    acceso_anticipado: float = Field(..., ge=0, le=1)
    con_voto_util: float = Field(..., ge=0, le=1, description="Al menos un voto de 'útil' de otra persona")
    perfiles_privados: float = Field(
        ..., ge=0, le=1, description="num_games_owned = 0: bandera de privacidad, no biblioteca vacía"
    )
    en_ingles: float = Field(..., ge=0, le=1)
    resenas_en_ingles: int = Field(
        ..., description="El conteo, no la proporción: redondeada a cuatro decimales, 184366/184367 da 1.0"
    )


class JuegoPanorama(BaseModel):
    """Una fila por juego. No trae la banda de riesgo a propósito: el cliente la cruza
    con /catalogo, que es donde vive."""

    appid: int
    resenas: int = Field(..., description="Reseñas descargadas de este juego")
    casos_senal: int = Field(..., description="De esas, las que cumplen playtime < 120 min y voto negativo")
    prevalencia: float = Field(..., ge=0, le=1)
    resenas_en_steam: Optional[int] = Field(None, description="Las que Steam reporta en total para el juego")
    positivas_en_steam: Optional[int] = Field(
        None, description="De esas, las positivas: el sentimiento de los jugadores. Descriptivo, no entra al modelo"
    )
    consenso: Optional[str] = Field(None, description="Resumen de Steam, p. ej. 'Very Positive'")
    motivo_principal: Optional[str] = Field(None, description="None si el juego no llega al mínimo de casos")
    horas_al_recomendar: Optional[float] = Field(
        None,
        description=(
            "Mediana de horas jugadas al escribir las reseñas positivas: cuánto llevaba quien lo recomendó. "
            "Descriptivo, no entra al modelo. None con menos de 10 reseñas positivas"
        ),
    )


class PanoramaCatalogo(BaseModel):
    """Panorama de la muestra de reseñas con la que trabaja NexPlay. Es descriptivo: sale
    de contar la base, no de predecir nada, así que ninguna cifra de aquí es un score."""

    juegos: int
    resenas_descargadas: int
    resenas_en_steam: int
    cobertura: float = Field(..., ge=0, le=1, description="descargadas / las que Steam reporta")
    ventana: VentanaMuestra
    descargas: DescargasMuestra
    modelo: FichaModelo
    casos_senal: int
    prevalencia: float = Field(..., ge=0, le=1)
    playtime_al_resenar: list[TramoPlaytime]
    muestra: CalidadMuestra
    motivos: list[MotivoInsatisfaccion] = Field(
        default_factory=list, description="Motivos agregados de todo el catálogo, sobre las reseñas clasificadas"
    )
    resenas_clasificadas: int = Field(..., description="Casos Y=1 que mencionan al menos un motivo")
    por_juego: list[JuegoPanorama]
