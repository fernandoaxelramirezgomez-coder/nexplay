"""Contratos Pydantic de entrada y salida de la API. Fuente única de verdad
del contrato: cualquier cambio aquí es un cambio de contrato con el cliente (UI)."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


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
    """Perfil derivado del formulario de alta. Es lo que consume /prediccion."""

    compras_al_anio: int
    horas_por_semana: float
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
    tienda_url: str = Field(..., description="Campo derivado del appid, no una columna de la base")
    banda_riesgo: NivelRiesgo = Field(
        ..., description="Riesgo estimado con un perfil neutro (ver catalogo.py); orientativo para el catálogo, no personalizado"
    )
    riesgo: float = Field(
        ..., ge=0, le=1, description="Score numérico del mismo perfil neutro; para ordenar dentro de una banda, no para mostrar como probabilidad"
    )


class SolicitudPrediccion(BaseModel):
    perfil: PerfilJugador
    appid: int = Field(..., description="appid de Steam del juego a evaluar")


class FactorPrediccion(BaseModel):
    etiqueta: str = Field(..., description="Variable del modelo en lenguaje claro, no el nombre técnico")
    valor_relativo: NivelRelativo = Field(
        ..., description="Si el valor de esta variable, para este juego/perfil, está por encima o por debajo del promedio del catálogo"
    )
    contribucion: float = Field(
        ..., description="Coeficiente × valor estandarizado de la variable; unidades de log-odds, no de probabilidad"
    )
    direccion: DireccionFactor = Field(..., description="Si esta variable aumenta o reduce el riesgo estimado")


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


class MotivoInsatisfaccion(BaseModel):
    motivo: str
    frecuencia: float = Field(
        ...,
        ge=0,
        le=1,
        description="Proporción de reseñas clasificadas (no del total Y=1) que mencionan este motivo",
    )


class Valoracion(BaseModel):
    """El voto de quien pregunta. Los comentarios son un hilo aparte y público."""

    util: bool
    actualizado: str


class SolicitudValoracion(BaseModel):
    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo generado por el navegador; identifica, no autentica",
    )
    util: bool = Field(..., description="True si la segunda opinión le sirvió")


class ResumenValoraciones(BaseModel):
    appid: int
    utiles: int = Field(..., description="Cuántas personas marcaron la segunda opinión como útil")
    no_utiles: int
    total: int
    mia: Optional[Valoracion] = Field(None, description="El voto del usuario que pregunta, si tiene uno")


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


class MensajeChat(BaseModel):
    rol: Literal["usuario", "nia"]
    contenido: str = Field(..., min_length=1, max_length=500)


class SolicitudNia(BaseModel):
    usuario: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Id anónimo del navegador; solo se usa para el límite de frecuencia",
    )
    appid: int
    mensajes: list[MensajeChat] = Field(..., min_length=1, max_length=10)
    perfil: Optional[PerfilJugador] = Field(
        None, description="Si viene, la banda del contexto es la de ese perfil; si no, la del perfil neutro"
    )


class RespuestaNia(BaseModel):
    respuesta: str
    modo: Literal["openai", "demostracion"]
    modelo: Optional[str] = Field(None, description="Modelo usado; None en modo demostración")
    aviso: Optional[str] = Field(None, description="Qué mostrar cuando la respuesta no vino del modelo")


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
