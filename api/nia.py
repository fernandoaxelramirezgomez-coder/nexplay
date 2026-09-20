"""Nia: el chat de la ficha. Responde sobre un juego concreto con los datos que le
arma el backend, nunca con lo que el modelo crea recordar.

Con clave y modelo configurados llama a OpenAI; sin ellos, o si la llamada falla,
responde en modo demostración con reglas sobre esos mismos datos. La respuesta dice
siempre en qué modo salió, para que nadie confunda una cosa con la otra.

Reglas de vocabulario de NexPlay que van en el prompt y que el modo demostración
respeta por construcción: se habla de "arrepentimiento temprano" (nunca "abandono"),
es una señal proxy, se usan bandas y nunca probabilidades ni scores, y no se recomienda
comprar ni no comprar.
"""

import logging

from . import catalogo, scoring
from .config import configuracion
from .schemas import MensajeChat, PerfilJugador

logger = logging.getLogger(__name__)

_FRASES_BANDA = {
    "bajo": "tiende a generar menos arrepentimiento temprano que el resto del catálogo",
    "medio": "no se distingue del resto del catálogo en arrepentimiento temprano",
    "alto": "tiende a generar más arrepentimiento temprano que el resto del catálogo",
}

_SISTEMA = """Eres Nia, la asistente de NexPlay. Respondes en español, en tono cercano y
en menos de 120 palabras, sobre UN juego concreto.

Reglas que no puedes romper:
- Usa siempre "arrepentimiento temprano", nunca "abandono".
- Es una señal proxy construida con reseñas de Steam donde alguien jugó menos de 120
  minutos y calificó negativo. No sabes si alguien se arrepintió de verdad.
- Habla de bandas (bajo, medio, alto). Nunca des probabilidades, porcentajes de riesgo
  ni scores numéricos del modelo. Los porcentajes de los motivos sí puedes citarlos.
- No recomiendes comprar ni no comprar, ni digas si vale la pena. Describe lo que dicen
  los datos y deja la decisión a quien pregunta.
- Responde solo con los datos del contexto. Si te preguntan algo que no está ahí, dilo
  con claridad en vez de inventarlo.
"""


def contexto(appid: int, perfil: PerfilJugador | None) -> dict:
    """Los datos reales del juego, tal como los sirve la API."""
    juego = catalogo.obtener(appid)
    if juego is None:
        raise ValueError(f"appid {appid} no está en el catálogo")

    prediccion = scoring.predecir(perfil, appid) if perfil else None
    explicacion = scoring.motivos_frecuentes(appid)
    nivel = prediccion.nivel.value if prediccion else juego.banda_riesgo.value

    return {
        "nombre": juego.nombre,
        "banda": nivel,
        "banda_es_del_perfil": prediccion is not None and perfil is not None,
        "generos": juego.generos,
        "metacritic": juego.metacritic,
        "precio": None if juego.es_gratis else juego.precio_final,
        "es_gratis": juego.es_gratis,
        "moneda": juego.moneda,
        "lanzamiento": juego.fecha_lanzamiento,
        "motivos": explicacion["motivos"],
        "n_casos": explicacion["n_casos"],
        "pct_clasificados": explicacion["pct_clasificados"],
    }


def _texto_precio(datos: dict) -> str:
    if datos["es_gratis"]:
        return "es gratuito"
    if datos["precio"] is None:
        return "no tiene precio disponible en los datos"
    return f"cuesta {datos['precio']:.2f} {datos['moneda'] or ''}".strip()


def _texto_critica(datos: dict) -> str:
    nota = datos["metacritic"]
    if nota is None:
        return "no tiene cobertura de crítica especializada (sin nota de Metacritic)"
    juicio = "bien" if nota >= 75 else "de forma mixta" if nota >= 50 else "mal"
    return f"la crítica especializada lo calificó {juicio} (Metacritic {nota})"


def _texto_motivos(datos: dict) -> str:
    motivos = datos["motivos"]
    if not motivos:
        return (
            f"hay muy pocas reseñas de arrepentimiento temprano de este juego "
            f"({datos['n_casos']}) para señalar un motivo dominante"
        )
    # scoring.motivos_frecuentes() devuelve modelos MotivoInsatisfaccion, no diccionarios.
    principal = motivos[0]
    resto = ", ".join(m.motivo for m in motivos[1:3])
    texto = (
        f"el motivo más mencionado es {principal.motivo} "
        f"({principal.frecuencia:.0%} de las reseñas clasificadas)"
    )
    return f"{texto}, y después {resto}" if resto else texto


def _demostracion(datos: dict, pregunta: str) -> str:
    """Respuesta por reglas sobre los mismos datos, para que la demo funcione sin clave."""
    pregunta = pregunta.lower()
    nombre, banda = datos["nombre"], datos["banda"]
    rotulo = "Para tu perfil" if datos["banda_es_del_perfil"] else "Con un perfil neutro"

    if any(palabra in pregunta for palabra in ("precio", "cuesta", "caro", "barato", "oferta")):
        return f"{nombre} {_texto_precio(datos)}. {rotulo}, su banda es {banda}."
    if any(palabra in pregunta for palabra in ("crítica", "critica", "metacritic", "nota", "reseñas de prensa")):
        return f"En {nombre}, {_texto_critica(datos)}. {rotulo}, su banda es {banda}."
    if any(palabra in pregunta for palabra in ("motivo", "queja", "problema", "bug", "rendimiento", "por qué", "porque")):
        return f"En {nombre}, {_texto_motivos(datos)}. {rotulo}, su banda de riesgo es {banda}."
    if any(palabra in pregunta for palabra in ("género", "genero", "tipo de juego", "de qué trata")):
        generos = ", ".join(datos["generos"]) or "sin géneros registrados"
        return f"{nombre} está clasificado en Steam como: {generos}. {rotulo}, su banda es {banda}."

    return (
        f"{rotulo}, {nombre} {_FRASES_BANDA.get(banda, '')}. En las reseñas de arrepentimiento "
        f"temprano, {_texto_motivos(datos)}. Además, {_texto_critica(datos)} y {_texto_precio(datos)}."
    )


def _contexto_para_prompt(datos: dict) -> str:
    lineas = [
        f"Juego: {datos['nombre']}",
        f"Banda de riesgo ({'perfil declarado' if datos['banda_es_del_perfil'] else 'perfil neutro'}): {datos['banda']}",
        f"Géneros: {', '.join(datos['generos']) or 'sin datos'}",
        f"Crítica: {_texto_critica(datos)}",
        f"Precio: {_texto_precio(datos)}",
        f"Lanzamiento: {datos['lanzamiento'] or 'sin dato'}",
        f"Reseñas de arrepentimiento temprano analizadas: {datos['n_casos']}"
        f" ({datos['pct_clasificados']:.0%} mencionan algún motivo)",
    ]
    if datos["motivos"]:
        motivos = "; ".join(f"{m.motivo} {m.frecuencia:.0%}" for m in datos["motivos"])
        lineas.append(f"Motivos (sobre las clasificadas): {motivos}")
    else:
        lineas.append("Motivos: no hay suficientes reseñas para señalar uno")
    return "\n".join(lineas)


def _preguntar_a_openai(datos: dict, mensajes: list[MensajeChat]) -> str:
    from openai import OpenAI  # perezoso: sin el paquete, Nia sigue en modo demostración

    cliente = OpenAI(api_key=configuracion.openai_api_key, timeout=configuracion.nexplay_nia_timeout)
    conversacion = [
        {"role": "system", "content": _SISTEMA},
        {"role": "system", "content": f"Datos del juego:\n{_contexto_para_prompt(datos)}"},
        *(
            {"role": "user" if mensaje.rol == "usuario" else "assistant", "content": mensaje.contenido}
            for mensaje in mensajes
        ),
    ]
    respuesta = cliente.chat.completions.create(
        model=configuracion.nexplay_modelo_nia,
        messages=conversacion,
        max_tokens=configuracion.nexplay_nia_max_tokens,
        temperature=0.3,
    )
    return (respuesta.choices[0].message.content or "").strip()


def responder(appid: int, mensajes: list[MensajeChat], perfil: PerfilJugador | None) -> dict:
    datos = contexto(appid, perfil)
    ultima = next((m.contenido for m in reversed(mensajes) if m.rol == "usuario"), "")

    if not configuracion.hay_openai:
        return {
            "respuesta": _demostracion(datos, ultima),
            "modo": "demostracion",
            "modelo": None,
            "aviso": "Modo demostración: respuesta armada con reglas sobre los datos del juego, sin modelo de lenguaje.",
        }

    try:
        texto = _preguntar_a_openai(datos, mensajes)
        if texto:
            return {"respuesta": texto, "modo": "openai", "modelo": configuracion.nexplay_modelo_nia, "aviso": None}
        logger.warning("OpenAI devolvió una respuesta vacía; se usa el modo demostración")
    except Exception as exc:  # falla de red, clave inválida, modelo inexistente, sin paquete
        logger.warning("falló la llamada a OpenAI (%s); se usa el modo demostración", type(exc).__name__)

    return {
        "respuesta": _demostracion(datos, ultima),
        "modo": "demostracion",
        "modelo": None,
        "aviso": "No se pudo usar el modelo configurado; esta respuesta se armó con reglas sobre los datos del juego.",
    }
