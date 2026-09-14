"""Contratos Pydantic de entrada y salida de la API. Fuente única de verdad
del contrato: cualquier cambio aquí es un cambio de contrato con el cliente (UI)."""

from enum import Enum

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


class SolicitudPrediccion(BaseModel):
    perfil: PerfilJugador
    appid: int = Field(..., description="appid de Steam del juego a evaluar")


class PrediccionRiesgo(BaseModel):
    appid: int
    riesgo: float = Field(
        ..., ge=0, le=1, description="Probabilidad estimada de arrepentimiento temprano (proxy, no observado)"
    )
    nivel: NivelRiesgo
    modelo_version: str


class MotivoInsatisfaccion(BaseModel):
    motivo: str
    frecuencia: float = Field(
        ..., ge=0, le=1, description="Proporción de reseñas negativas tempranas que mencionan este motivo"
    )


class ExplicacionJuego(BaseModel):
    appid: int
    nombre: str
    motivos: list[MotivoInsatisfaccion]
