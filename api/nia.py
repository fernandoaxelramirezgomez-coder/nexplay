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
import re
import unicodedata

from . import catalogo, scoring
from .config import configuracion
from .schemas import MensajeChat, PerfilJugador

logger = logging.getLogger(__name__)

_REFERENCIAS: dict | None = None

_FRASES_BANDA = {
    "bajo": "tiende a generar menos arrepentimiento temprano que el resto del catálogo",
    "medio": "no se distingue del resto del catálogo en arrepentimiento temprano",
    "alto": "tiende a generar más arrepentimiento temprano que el resto del catálogo",
}

_SISTEMA = """Eres Nia, la asistente de NexPlay y experta en crítica de videojuegos:
lees los datos del catálogo como los leería alguien que reseña juegos, y explicas qué
dicen. Respondes en español, en tono cercano y en menos de 120 palabras, sobre UN juego
concreto.

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
- Cuando venga al caso, nombra las fortalezas y las debilidades del juego, siempre salidas
  de los datos: la nota de la crítica o su ausencia, la banda, el precio frente al
  catálogo y los motivos más mencionados. No opines por tu cuenta ni inventes otras.
- Para decir en qué se destaca o en qué se queda corto frente a otros juegos, usa solo las
  cifras de la línea "Catálogo" del contexto. Nunca inventes datos de otro juego.
- Si preguntan por un juego que no es el del contexto y que el contexto no marca como
  parte del catálogo, empieza la respuesta con esta frase, con el nombre que usaron:
  "<Juego> no está en este catálogo de Steam, así que no tengo ninguna señal sobre él
  para comparar." Después sigue con lo que sí sabes del juego del contexto. No inventes
  nada de ese otro juego.
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
        return "la crítica especializada no lo cubrió (sin nota de Metacritic)"
    juicio = "bien" if nota >= 75 else "de forma mixta" if nota >= 50 else "mal"
    return f"la crítica especializada lo calificó {juicio} (Metacritic {nota})"


def _texto_motivos(datos: dict, senal_ya_nombrada: bool = False) -> str:
    """senal_ya_nombrada: la frase anterior ya dijo "arrepentimiento temprano", así que
    aquí se nombra como "esa señal" en vez de repetirlo."""
    motivos = datos["motivos"]
    if not motivos:
        n = datos["n_casos"]
        senal = "con esa señal" if senal_ya_nombrada else "de arrepentimiento temprano"
        if n == 0:
            return f"no hay reseñas {senal}, así que no se puede señalar un motivo dominante"
        if n == 1:
            return f"hay una sola reseña {senal}: no alcanza para señalar un motivo dominante"
        return f"hay solo {n} reseñas {senal}, muy pocas para señalar un motivo dominante"
    # scoring.motivos_frecuentes() devuelve modelos MotivoInsatisfaccion, no diccionarios.
    principal = motivos[0]
    resto = " y ".join(m.motivo for m in motivos[1:3])
    texto = (
        f"el motivo más mencionado es {principal.motivo} "
        f"({principal.frecuencia:.0%} de las reseñas clasificadas)"
    )
    return f"{texto}, y después {resto}" if resto else texto


def _demostracion(datos: dict, pregunta: str) -> str:
    """Respuesta por reglas sobre los mismos datos, para que la demo funcione sin clave."""
    pregunta = pregunta.lower()
    nombre, banda = datos["nombre"], datos["banda"]
    # La banda es del juego (modelo de título): no hay una versión "para tu perfil".
    rotulo = "Para cualquier perfil"

    if any(palabra in pregunta for palabra in ("precio", "cuesta", "caro", "barato", "oferta")):
        return f"{nombre} {_texto_precio(datos)}. {rotulo}, su riesgo es {banda}."
    if any(palabra in pregunta for palabra in ("crítica", "critica", "metacritic", "nota", "reseñas de prensa")):
        return f"En {nombre}, {_texto_critica(datos)}. {rotulo}, su riesgo es {banda}."
    if any(palabra in pregunta for palabra in ("motivo", "queja", "problema", "bug", "rendimiento", "por qué", "porque")):
        return f"En {nombre}, {_texto_motivos(datos)}. {rotulo}, su riesgo es {banda}."
    if any(palabra in pregunta for palabra in ("género", "genero", "tipo de juego", "de qué trata")):
        generos = ", ".join(datos["generos"]) or "sin géneros registrados"
        return f"{nombre} está clasificado en Steam como: {generos}. {rotulo}, su riesgo es {banda}."

    motivos = _texto_motivos(datos, senal_ya_nombrada=True)
    motivos = f"En las reseñas con esa señal, {motivos}" if datos["motivos"] else motivos[0].upper() + motivos[1:]
    return (
        f"{rotulo}, {nombre} {_FRASES_BANDA.get(banda, '')}. {motivos}. "
        f"Además, {_texto_critica(datos)}, y el juego {_texto_precio(datos)}."
    )


def _referencias_del_catalogo() -> dict:
    """Cifras del catálogo para que la comparación tenga con qué compararse. Se calculan
    una vez: el catálogo se carga al importar y no cambia mientras corre la API."""
    global _REFERENCIAS
    if _REFERENCIAS is None:
        juegos = catalogo.buscar()
        precios = sorted(j.precio_final for j in juegos if j.precio_final)
        notas = [j.metacritic for j in juegos if j.metacritic is not None]
        _REFERENCIAS = {
            "juegos": len(juegos),
            "precio_mediano": precios[len(precios) // 2] if precios else None,
            "metacritic_promedio": round(sum(notas) / len(notas)) if notas else None,
            "con_nota": len(notas),
            "bandas": {b: sum(1 for j in juegos if j.banda_riesgo.value == b) for b in ("bajo", "medio", "alto")},
        }
    return _REFERENCIAS


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def juegos_del_catalogo_mencionados(pregunta: str, appid_abierto: int) -> list[str]:
    """Nombres del catálogo que aparecen en la pregunta, sin contar el juego abierto.

    Nia solo recibe los datos de un juego, así que sin esto no puede distinguir "no está
    en el catálogo" de "está, pero no es el que tienes abierto", y diría lo primero de
    cualquiera.

    Se compara sin acentos, sin los símbolos de marca y también por la parte antes de los
    dos puntos ("Cities: Skylines" se reconoce con "Cities"). Prefiere equivocarse de más:
    una palabra común que coincide con un título ("celeste") solo agrega una línea al
    contexto, mientras que no reconocer un juego del catálogo haría que Nia dijera que no
    está."""
    texto = _sin_acentos(pregunta)
    encontrados = []
    for juego in catalogo.buscar():
        if juego.appid == appid_abierto:
            continue
        for variante in _variantes_del_nombre(juego.nombre):
            if re.search(rf"(?<!\w){re.escape(variante)}(?!\w)", texto):
                encontrados.append(juego.nombre)
                break
    # "Portal 2" ya implica "Portal": se queda el título más largo de cada coincidencia.
    return [n for n in encontrados if not any(n != otro and _sin_acentos(n) in _sin_acentos(otro) for otro in encontrados)]


def _variantes_del_nombre(nombre: str) -> list[str]:
    """El nombre completo y su primera parte, normalizados; descarta lo muy corto."""
    limpio = _sin_acentos(nombre.replace("™", "").replace("®", "")).strip()
    variantes = {limpio, limpio.split(":")[0].strip(), limpio.split(" - ")[0].strip()}
    return [v for v in variantes if len(v) >= 4]


def _donde(valor: float, referencia: float, igual: str = "igual a") -> str:
    """Arriba, abajo o igual. Sin el caso de empate, un valor idéntico al promedio se
    contaba como "por debajo"."""
    if valor > referencia:
        return "por encima del" if igual == "igual al" else "por encima de"
    if valor < referencia:
        return "por debajo del" if igual == "igual al" else "por debajo de"
    return igual


def _texto_comparacion(datos: dict, ref: dict) -> str:
    """Dónde cae este juego dentro del catálogo, en palabras y sin adjetivos de valor."""
    partes = []
    if datos["es_gratis"]:
        partes.append("es gratuito, y el precio mediano del catálogo es"
                      f" {ref['precio_mediano']:.0f} MXN")
    elif datos["precio"] is not None and ref["precio_mediano"]:
        partes.append(f"su precio está {_donde(datos['precio'], ref['precio_mediano'])} la mediana del catálogo")
    if datos["metacritic"] is None:
        partes.append("no tiene nota de Metacritic, como otros del catálogo")
    elif ref["metacritic_promedio"]:
        donde = _donde(datos["metacritic"], ref["metacritic_promedio"], "igual al")
        partes.append(f"su nota está {donde} promedio de los que sí tienen")
    partes.append(f"su banda es {datos['banda']}")
    return "; ".join(partes)


def _contexto_para_prompt(datos: dict, mencionados: list[str] | None = None) -> str:
    lineas = [
        f"Juego: {datos['nombre']}",
        f"Banda de riesgo del juego (la misma para cualquier perfil): {datos['banda']}",
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
    ref = _referencias_del_catalogo()
    bandas = " / ".join(f"{n} {b}" for b, n in ref["bandas"].items())
    lineas.append(
        f"Catálogo ({ref['juegos']} juegos, para comparar): precio mediano"
        f" {ref['precio_mediano']:.0f} MXN; Metacritic promedio {ref['metacritic_promedio']}"
        f" entre los {ref['con_nota']} que tienen nota; bandas {bandas}"
    )
    lineas.append(f"Este juego frente al catálogo: {_texto_comparacion(datos, ref)}")
    if mencionados:
        lineas.append(
            "Otros juegos del catálogo que nombra la pregunta (no tienes sus datos aquí, así que NO son"
            f" juegos fuera del catálogo): {', '.join(mencionados)}"
        )
    return "\n".join(lineas)


def _sin_claves(texto: str) -> str:
    """Tapa todo lo que parezca una clave de API (sk-...) y recorta mensajes enormes."""
    return re.sub(r"sk-[A-Za-z0-9_\-]{4,}", "sk-…", texto)[:500]


# Los modelos de OpenAI no aceptan los mismos parámetros: los nuevos piden
# max_completion_tokens y rechazan max_tokens (y algunos solo admiten la temperatura por
# omisión). Cuál es el bueno depende del modelo que esté en .env, así que en vez de
# fijarlo se empieza por el nuevo y se corrige con lo que responde la propia API.
_EQUIVALENTES = {"max_completion_tokens": "max_tokens", "max_tokens": "max_completion_tokens"}
_MAXIMO_REINTENTOS = 3
# Lo que el modelo configurado aceptó la primera vez, para no volver a gastar una petición
# rechazada en cada pregunta. Vive en memoria: se recalcula al reiniciar la API.
_PARAMETROS_APRENDIDOS: dict[str, dict] = {}
_PARAMETRO_RECHAZADO = re.compile(r"'param': '([^']+)'")
_CODIGO_RECHAZO = re.compile(r"'code': '(unsupported_parameter|unsupported_value)'")


def _parametro_rechazado(error: str) -> tuple[str, str] | None:
    """Qué parámetro rechazó OpenAI y por qué, leído del cuerpo del 400."""
    codigo = _CODIGO_RECHAZO.search(error)
    parametro = _PARAMETRO_RECHAZADO.search(error)
    return (parametro.group(1), codigo.group(1)) if codigo and parametro else None


def _crear_con_reintentos(cliente, conversacion: list[dict]):
    """Llama al modelo y, si rechaza un parámetro, lo traduce a su equivalente o lo quita.

    Un modelo nuevo responde 400 'Unsupported parameter: max_tokens ... use
    max_completion_tokens'; uno viejo hace lo contrario. Así funcionan los dos sin tener
    que adivinar cuál está configurado."""
    modelo = configuracion.nexplay_modelo_nia
    opcionales = _PARAMETROS_APRENDIDOS.get(
        modelo, {"max_completion_tokens": configuracion.nexplay_nia_max_tokens, "temperature": 0.3}
    )
    parametros = {"model": modelo, "messages": conversacion, **opcionales}
    for _ in range(_MAXIMO_REINTENTOS):
        try:
            respuesta = cliente.chat.completions.create(**parametros)
            _PARAMETROS_APRENDIDOS[modelo] = {k: v for k, v in parametros.items() if k not in ("model", "messages")}
            return respuesta
        except Exception as exc:
            rechazado = _parametro_rechazado(str(exc))
            if not rechazado or rechazado[0] not in parametros:
                raise
            nombre, codigo = rechazado
            valor = parametros.pop(nombre)
            equivalente = _EQUIVALENTES.get(nombre) if codigo == "unsupported_parameter" else None
            if equivalente:
                parametros[equivalente] = valor
                logger.info("el modelo no acepta %s; se reintenta con %s", nombre, equivalente)
            else:
                logger.info("el modelo no acepta %s=%r; se reintenta sin ese parámetro", nombre, valor)
    respuesta = cliente.chat.completions.create(**parametros)
    _PARAMETROS_APRENDIDOS[modelo] = {k: v for k, v in parametros.items() if k not in ("model", "messages")}
    return respuesta


def _preguntar_a_openai(datos: dict, mensajes: list[MensajeChat], mencionados: list[str]) -> str:
    from openai import OpenAI  # perezoso: sin el paquete, Nia sigue en modo demostración

    cliente = OpenAI(api_key=configuracion.openai_api_key, timeout=configuracion.nexplay_nia_timeout)
    conversacion = [
        {"role": "system", "content": _SISTEMA},
        {"role": "system", "content": f"Datos del juego:\n{_contexto_para_prompt(datos, mencionados)}"},
        *(
            {"role": "user" if mensaje.rol == "usuario" else "assistant", "content": mensaje.contenido}
            for mensaje in mensajes
        ),
    ]
    respuesta = _crear_con_reintentos(cliente, conversacion)
    return (respuesta.choices[0].message.content or "").strip()


def responder(appid: int, mensajes: list[MensajeChat], perfil: PerfilJugador | None) -> dict:
    datos = contexto(appid, perfil)
    ultima = next((m.contenido for m in reversed(mensajes) if m.rol == "usuario"), "")

    if not configuracion.hay_openai:
        logger.info("sin clave de OpenAI configurada; appid=%s responde en modo demostración", appid)
        return {
            "respuesta": _demostracion(datos, ultima),
            "modo": "demostracion",
            "modelo": None,
            "aviso": "Modo demostración: respuesta armada con reglas sobre los datos del juego, sin modelo de lenguaje.",
        }

    try:
        texto = _preguntar_a_openai(datos, mensajes, juegos_del_catalogo_mencionados(ultima, appid))
        if texto:
            return {"respuesta": texto, "modo": "openai", "modelo": configuracion.nexplay_modelo_nia, "aviso": None}
        logger.warning("OpenAI devolvió una respuesta vacía para appid=%s; se usa el modo demostración", appid)
    except Exception as exc:  # falla de red, clave inválida, modelo inexistente, sin paquete
        # El mensaje real, no solo el tipo: sin él no se puede saber por qué cayó. Se le
        # quita cualquier cosa con forma de clave antes de escribirlo.
        logger.warning(
            "falló la llamada a OpenAI para appid=%s (%s: %s); se usa el modo demostración",
            appid, type(exc).__name__, _sin_claves(str(exc)),
        )

    return {
        "respuesta": _demostracion(datos, ultima),
        "modo": "demostracion",
        "modelo": None,
        "aviso": "No se pudo usar el modelo configurado; esta respuesta se armó con reglas sobre los datos del juego.",
    }
