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

import hashlib
import logging
import re
import unicodedata
import uuid

from . import catalogo, scoring, valoraciones
from .config import configuracion
from .schemas import MensajeChat, PerfilJugador

logger = logging.getLogger(__name__)

_REFERENCIAS: dict | None = None

_FRASES_BANDA = {
    "bajo": "tiende a generar menos arrepentimiento temprano que el resto del catálogo",
    "medio": "no se distingue del resto del catálogo en arrepentimiento temprano",
    "alto": "tiende a generar más arrepentimiento temprano que el resto del catálogo",
}

# Mismas frases que COMO_SE_LEE en frontend/src/app/dominio/factores.ts: lo que la ficha
# muestra en "Qué mueve esta estimación" es lo que Nia tiene que poder decir con las mismas
# palabras. Si se cambia una, se cambian las dos.
_LECTURA_FACTORES = {
    "gratuidad del juego": ("Es gratis", "Es de pago"),
    "precio del juego": ("Cuesta más que el promedio del catálogo", "Cuesta menos que el promedio"),
    "descuento actual del juego": ("Está con descuento", "No está con descuento"),
    "cobertura de crítica especializada": ("Tiene nota de la crítica", "No tiene nota de la crítica"),
    "nota de Metacritic": (
        "Su nota de Metacritic está por encima del promedio del catálogo",
        "Su nota de Metacritic está por debajo del promedio",
    ),
    "compras declaradas por año": ("Compras más juegos que el promedio", "Compras menos juegos que el promedio"),
}

def _lectura_factor(factor) -> str:
    alto, bajo = _LECTURA_FACTORES.get(
        factor.etiqueta,
        (f"{factor.etiqueta}, por encima del promedio del catálogo", f"{factor.etiqueta}, por debajo del promedio"),
    )
    return alto if factor.valor_relativo.value == "alto" else bajo


def _factores_visibles(factores, juego) -> list[dict]:
    """Los factores del modelo con la frase de la ficha y su efecto.

    Fuera los que describen un valor imputado y no el juego: sin precio conocido el modelo
    lee 0 y sin nota usa la mediana del catálogo. Mismo filtro que factoresVisibles() en
    dominio/factores.ts, para que Nia no cite un factor que la ficha esconde."""
    precio_imputado = juego.precio_final is None and not juego.es_gratis
    visibles = []
    for factor in factores:
        if precio_imputado and factor.etiqueta == "precio del juego":
            continue
        if juego.metacritic is None and factor.etiqueta == "nota de Metacritic":
            continue
        visibles.append(
            {
                "etiqueta": factor.etiqueta,
                "lectura": _lectura_factor(factor),
                "efecto": "sube" if factor.direccion.value == "aumenta" else "baja",
            }
        )
    return visibles


_SISTEMA = """Eres Nia, la asistente de NexPlay y experta en crítica de videojuegos:
lees los datos del catálogo como los leería alguien que reseña juegos, y explicas qué
dicen. Respondes en español, en tono cercano y en **60 palabras o menos**, sobre UN juego
concreto. La primera oración responde lo que se preguntó, directo; lo demás es el porqué.

Reglas que no puedes romper:
- Responde en texto plano: sin markdown, sin asteriscos para resaltar, sin viñetas ni
  títulos. Lo que escribas se pinta tal cual, así que un **así** se ve con los asteriscos.
- Usa siempre "arrepentimiento temprano", nunca "abandono".
- Es una señal proxy construida con reseñas de Steam donde alguien jugó menos de 120
  minutos y calificó negativo. No sabes si alguien se arrepintió de verdad. Eso se explica
  **solo en tu primera respuesta de la conversación**, o si te lo preguntan: si ya hay
  respuestas tuyas más arriba, di "esa señal" o "el arrepentimiento temprano" y sigue.
- Si quien pregunta dice que juega poco, o cuántas horas juega, usa esa cifra para decirle
  en cuántas sesiones llegaría a las dos horas de la ventana de reembolso, en vez de
  repetir que la ventana son 120 minutos.
- Habla de bandas (bajo, medio, alto). Nunca des probabilidades, porcentajes de riesgo
  ni scores numéricos del modelo. Los porcentajes de los motivos sí puedes citarlos, y
  cuando cites uno di sobre cuántas reseñas clasificadas está calculado.
- La banda la asigna el modelo con datos del juego (precio, gratuidad, descuento, nota y
  cobertura de crítica). Las reseñas explican los motivos, no la banda. Nunca digas que la
  banda sale de las reseñas.
- Para explicar por qué un juego quedó en su banda, usa las líneas de "Qué mueve esta
  estimación" del contexto, con esas mismas palabras y sin inventar otras variables.
- El precio aparece en dos lugares distintos y no hay que confundirlos: como variable del
  modelo (en "Qué mueve esta estimación") y como motivo en las reseñas (en "Motivos").
  Pueden apuntar en direcciones opuestas; si te preguntan por el precio, di de cuál hablas.
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


# Qué prompt produjo una respuesta, para poder comparar los votos de antes y después de
# cambiarlo. Sale del texto mismo: una etiqueta a mano se queda vieja sin que nadie lo
# note, y entonces los votos de dos prompts distintos se suman como si fueran uno.
VERSION_PROMPT = hashlib.sha256(_SISTEMA.encode("utf-8")).hexdigest()[:8]

# En modo demostración el prompt no interviene: atribuirle el voto sería falso.
VERSION_REGLAS = "reglas"


def contexto(appid: int) -> dict:
    """Los datos reales del juego, tal como los sirve la API.

    Sin perfil: la banda y los factores son del título y el perfil declarado no mueve
    ninguno de los dos. Lo que el perfil aporta (afinidad, sesiones hasta las dos horas)
    lo trae la conversación, no el contexto."""
    juego = catalogo.obtener(appid)
    if juego is None:
        raise ValueError(f"appid {appid} no está en el catálogo")

    # Siempre, con perfil o sin él: la banda y los factores son del título, y sin los
    # factores Nia no tiene con qué explicar de dónde sale la banda.
    prediccion = scoring.prediccion_de_titulo(appid)
    explicacion = scoring.motivos_frecuentes(appid)

    return {
        "nombre": juego.nombre,
        "banda": prediccion.nivel.value,
        "factores": _factores_visibles(prediccion.factores, juego),
        "generos": juego.generos,
        "metacritic": juego.metacritic,
        "precio": None if juego.es_gratis else juego.precio_final,
        "es_gratis": juego.es_gratis,
        "moneda": juego.moneda,
        "lanzamiento": juego.fecha_lanzamiento,
        "motivos": explicacion["motivos"],
        "n_casos": explicacion["n_casos"],
        "pct_clasificados": explicacion["pct_clasificados"],
        # Las reseñas sobre las que se calcula cada porcentaje de motivo, no las
        # analizadas: la misma cuenta que hace clasificadas() en ficha/motivos-barras.ts.
        "clasificadas": round(explicacion["n_casos"] * explicacion["pct_clasificados"]),
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


def _texto_factores(datos: dict) -> str:
    """Las variables del modelo en prosa, con las palabras de la ficha."""
    if not datos["factores"]:
        return "el modelo no destaca ninguna variable de este juego"
    partes = [f"{f['lectura'][0].lower()}{f['lectura'][1:]} ({f['efecto']} el riesgo estimado)" for f in datos["factores"]]
    return "; ".join(partes)


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
    cuantas = datos["clasificadas"]
    sobre = "de 1 reseña clasificada" if cuantas == 1 else f"de las {cuantas} reseñas clasificadas"
    texto = (
        f"el motivo más mencionado es {principal.motivo} "
        f"({principal.frecuencia:.0%} {sobre})"
    )
    return f"{texto}, y después {resto}" if resto else texto


def _factor_de_precio(datos: dict) -> str | None:
    """Si el precio, la gratuidad o el descuento están entre las variables del modelo.

    Es la distinción que más se confunde: que el precio mueva la estimación no es lo mismo
    que la gente se queje del precio en las reseñas."""
    # En un juego gratuito lo que dice algo es la gratuidad, no que su precio de 0 quede
    # por debajo del promedio.
    etiquetas = (
        ("gratuidad del juego", "descuento actual del juego", "precio del juego")
        if datos["es_gratis"]
        else ("precio del juego", "descuento actual del juego", "gratuidad del juego")
    )
    factor = next((f for e in etiquetas for f in datos["factores"] if f["etiqueta"] == e), None)
    if factor is None:
        return None
    lectura = f"{factor['lectura'][0].lower()}{factor['lectura'][1:]}"
    return f"En el modelo, del precio lo que pesa es que {lectura}: eso {factor['efecto']} el riesgo estimado."


def _explicacion_de_la_banda(datos: dict) -> str:
    """De dónde sale la banda: de las variables del juego, nunca de las reseñas."""
    return (
        f"Esa banda la pone el modelo con datos del juego: {_texto_factores(datos)}. "
        "Las reseñas explican los motivos, no la banda."
    )


def _demostracion(datos: dict, pregunta: str) -> str:
    """Respuesta por reglas sobre los mismos datos, para que la demo funcione sin clave."""
    pregunta = pregunta.lower()
    nombre, banda = datos["nombre"], datos["banda"]
    # La banda es del juego (modelo de título): no hay una versión "para tu perfil".
    rotulo = "Para cualquier perfil"

    if any(palabra in pregunta for palabra in ("precio", "cuesta", "caro", "barato", "oferta")):
        factor = _factor_de_precio(datos)
        aparte = f" {factor}" if factor else ""
        return f"{nombre} {_texto_precio(datos)}. {rotulo}, su riesgo es {banda}.{aparte}"
    if any(palabra in pregunta for palabra in ("crítica", "critica", "metacritic", "nota", "reseñas de prensa")):
        return f"En {nombre}, {_texto_critica(datos)}. {rotulo}, su riesgo es {banda}."
    if any(palabra in pregunta for palabra in ("banda", "por qué", "porque", "riesgo", "estimación", "estimacion")):
        return f"{rotulo}, {nombre} {_FRASES_BANDA.get(banda, '')}. {_explicacion_de_la_banda(datos)}"
    if any(palabra in pregunta for palabra in ("motivo", "queja", "problema", "bug", "rendimiento")):
        return f"En {nombre}, {_texto_motivos(datos)}. {rotulo}, su riesgo es {banda}."
    if any(palabra in pregunta for palabra in ("género", "genero", "tipo de juego", "de qué trata")):
        generos = ", ".join(datos["generos"]) or "sin géneros registrados"
        return f"{nombre} está clasificado en Steam como: {generos}. {rotulo}, su riesgo es {banda}."

    motivos = _texto_motivos(datos, senal_ya_nombrada=True)
    motivos = f"En las reseñas con esa señal, {motivos}" if datos["motivos"] else motivos[0].upper() + motivos[1:]
    return (
        f"{rotulo}, {nombre} {_FRASES_BANDA.get(banda, '')}. {_explicacion_de_la_banda(datos)} "
        f"{motivos}."
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
            # Un decimal, el mismo que muestra la ficha (85.5): con el entero, Nia decía
            # 86 y la ficha 85.5 para el mismo promedio.
            "metacritic_promedio": round(sum(notas) / len(notas), 1) if notas else None,
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
        f"Reseñas clasificadas, sobre las que se calcula cada porcentaje de motivo: {datos['clasificadas']}",
    ]
    if datos["motivos"]:
        motivos = "; ".join(f"{m.motivo} {m.frecuencia:.0%}" for m in datos["motivos"])
        sobre = "1 clasificada" if datos["clasificadas"] == 1 else f"las {datos['clasificadas']} clasificadas"
        lineas.append(f"Motivos (sobre {sobre}): {motivos}")
    else:
        lineas.append("Motivos: no hay suficientes reseñas para señalar uno")
    # Las mismas frases y el mismo orden que la ficha muestra en "Qué mueve esta
    # estimación": sin esto, Nia atribuía la banda a las reseñas negativas.
    lineas.append("Qué mueve esta estimación (variables del modelo, en el orden de la ficha):")
    if datos["factores"]:
        lineas += [f"- {f['lectura']} → {f['efecto']} el riesgo estimado" for f in datos["factores"]]
    else:
        lineas.append("- sin variables destacadas para este juego")
    lineas.append(
        "Estas variables son las que producen la banda. Los motivos de las reseñas dicen de"
        " qué se queja la gente, no por qué el modelo puso esa banda."
    )
    ref = _referencias_del_catalogo()
    bandas = " / ".join(f"{n} {b}" for b, n in ref["bandas"].items())
    lineas.append(
        f"Catálogo ({ref['juegos']} juegos, para comparar): precio mediano"
        f" {ref['precio_mediano']:.0f} MXN; Metacritic promedio {ref['metacritic_promedio']}"
        f" entre los {ref['con_nota']} que tienen nota (es el promedio contra el que se lee"
        f" el factor de la nota); bandas {bandas}"
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


def _con_constancia(salida: dict, appid: int, usuario: str, pregunta: str) -> dict:
    """Le pone id a la respuesta y la deja anotada, para que su voto tenga a qué apuntar.

    Si la base de valoraciones falla, la respuesta se entrega igual y solo se pierde la
    posibilidad de votarla: no contestar por no poder anotar sería el peor intercambio."""
    salida["id"] = str(uuid.uuid4())
    salida["version_prompt"] = VERSION_PROMPT if salida["modo"] == "openai" else VERSION_REGLAS
    try:
        valoraciones.registrar_respuesta_nia(
            id_respuesta=salida["id"],
            usuario=usuario,
            appid=appid,
            pregunta=pregunta,
            respuesta=salida["respuesta"],
            modo=salida["modo"],
            modelo=salida["modelo"],
            version_prompt=salida["version_prompt"],
        )
    except Exception as exc:
        logger.warning("no se pudo anotar la respuesta de Nia (%s): no se podrá votar", type(exc).__name__)
    return salida


def responder(appid: int, mensajes: list[MensajeChat], usuario: str, _perfil: PerfilJugador | None = None) -> dict:
    """El perfil llega porque /nia lo recibe desde siempre, pero no entra al contexto: el
    riesgo es del título. Lo que la persona cuente de sus horas lo lee Nia en el hilo."""
    datos = contexto(appid)
    ultima = next((m.contenido for m in reversed(mensajes) if m.rol == "usuario"), "")

    if not configuracion.hay_openai:
        logger.info("sin clave de OpenAI configurada; appid=%s responde en modo demostración", appid)
        return _con_constancia(
            {
                "respuesta": _demostracion(datos, ultima),
                "modo": "demostracion",
                "modelo": None,
                "aviso": "Modo demostración: respuesta armada con reglas sobre los datos del juego, sin modelo de lenguaje.",
            },
            appid, usuario, ultima,
        )

    try:
        texto = _preguntar_a_openai(datos, mensajes, juegos_del_catalogo_mencionados(ultima, appid))
        if texto:
            return _con_constancia(
                {"respuesta": texto, "modo": "openai", "modelo": configuracion.nexplay_modelo_nia, "aviso": None},
                appid, usuario, ultima,
            )
        logger.warning("OpenAI devolvió una respuesta vacía para appid=%s; se usa el modo demostración", appid)
    except Exception as exc:  # falla de red, clave inválida, modelo inexistente, sin paquete
        # El mensaje real, no solo el tipo: sin él no se puede saber por qué cayó. Se le
        # quita cualquier cosa con forma de clave antes de escribirlo.
        logger.warning(
            "falló la llamada a OpenAI para appid=%s (%s: %s); se usa el modo demostración",
            appid, type(exc).__name__, _sin_claves(str(exc)),
        )

    return _con_constancia(
        {
            "respuesta": _demostracion(datos, ultima),
            "modo": "demostracion",
            "modelo": None,
            "aviso": "No se pudo usar el modelo configurado; esta respuesta se armó con reglas sobre los datos del juego.",
        },
        appid, usuario, ultima,
    )
