"""Nia, la asistente del catálogo.

- agente.py: arma el contexto, habla con el modelo de lenguaje y pule su respuesta.
- reglas.py: las respuestas por reglas, con o sin modelo (trivia, «el mejor», resúmenes…).
- herramientas.py: las funciones que el modelo puede llamar para consultar el catálogo.

main.py usa `nia.responder` y `nia.reglas.opinion_corta`."""

from . import agente, herramientas, reglas
from .agente import responder

__all__ = ["agente", "herramientas", "reglas", "responder"]
