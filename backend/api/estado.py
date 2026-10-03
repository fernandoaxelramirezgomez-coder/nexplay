"""Lo que GET /estado cuenta del sistema: si Nia tiene modelo de lenguaje, qué release de datos
se sirve, cuántos juegos y con qué modelo de riesgo.

Todo sale de lo que ya está en memoria (el catálogo, el artefacto del modelo, la
configuración) o de una marca que se lee una sola vez al arrancar. Tiene que ser barato: la
vista de Administración lo pide al abrirse y, en Render, también sirve para saber si el
servicio ya despertó. De OpenAI solo dice si hay clave y qué modelo; la clave nunca sale.
"""

import json
from pathlib import Path

from . import catalogo, scoring
from .config import configuracion
from .schemas import EstadoSistema

# La marca que deja despliegue/preparar_entorno.py junto a la base del catálogo: de qué release
# salió. Sin ella (la base original de la ingesta, en desarrollo) el release no se sabe.
_MARCA = Path(__file__).resolve().parent.parent / "datos" / "nexplay.db.origen.json"


def release_servido(marca: Path = _MARCA) -> str | None:
    try:
        return json.loads(marca.read_text(encoding="utf-8")).get("ref")
    except (OSError, ValueError, AttributeError):
        return None


_RELEASE = release_servido()


def estado() -> EstadoSistema:
    modelo = scoring.ficha_del_modelo()
    con_openai = configuracion.hay_openai
    return EstadoSistema(
        nia_con_openai=con_openai,
        modelo_nia=configuracion.nexplay_modelo_nia.strip() if con_openai else None,
        datos_release=_RELEASE,
        juegos_catalogo=len(catalogo.buscar()),
        modelo_version=modelo["version"],
        modelo_datos=modelo["datos"],
        modelo_juegos_entrenamiento=modelo["juegos_entrenamiento"],
    )
