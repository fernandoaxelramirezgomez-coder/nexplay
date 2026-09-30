"""El modo demostración de Nia: respuestas por reglas sobre los mismos datos, sin modelo.

Antes contestaba cualquier cosa que no reconociera con la explicación del riesgo, y a
«resume», «es bueno el juego?» o «¿y cuál de esos…?» les daba siete veces la misma
respuesta. Aquí cada pregunta pasa por una lista de intenciones, en orden, y la última
admite que no sabe en vez de repetirse.

Todas las respuestas siguen la voz de Nia: 60 palabras o menos, de 1 a 3 emojis y una
pregunta corta al final. La primera oración de cada una se sostiene sola, porque «resume»
junta las primeras oraciones de lo que ya dijo: el hilo es lo único que se recuerda.
"""

import re

from .. import catalogo, panorama
from ..schemas import JuegoCatalogo, MensajeChat, SugerenciaNia
from . import agente as nia
from . import herramientas

# Cuántas horas típicas cuentan como "para jugar poco": las mismas que usan las
# sugerencias del perfil (HORAS_DE_SESION_CORTA en frontend/src/app/dominio/sugerencias.ts).
HORAS_DE_SESION_CORTA = 20

_ORDEN_BANDAS = ("bajo", "medio", "alto")

# Sinónimos de géneros que Steam nombra de otra forma.
_SINONIMOS_GENERO = {
    "rpg": "Rol",
    "mmo": "Multijugador masivo",
    "simulacion": "Simuladores",
    "simulador": "Simuladores",
    "carrera": "Carreras",
    "deporte": "Deportes",
    "f2p": "Free to Play",
}

# Lo que se pide para jugar con otros. El catálogo no tiene un dato de cooperativo ni de
# en línea: lo más cercano es el género «Multijugador masivo», y se dice así.
_SOCIAL = ("multijugador", "multiplayer", "cooperativo", "cooperativos", "coop", "co-op", "online", "en linea",
           "con amigos", "con mis amigos", "con otros", "en grupo")
_SINONIMOS_GENERO.update({clave: "Multijugador masivo" for clave in _SOCIAL})

_GRATIS = ("gratis", "gratuito", "gratuitos", "free", "f2p", "sin pagar", "sin costo")
_BARATOS = ("barato", "baratos", "economico", "economicos", "que no cueste mucho", "mas barato")
_CAROS = ("caro", "caros", "mas caro")


def _norm(texto: str) -> str:
    return nia._sin_acentos(texto)


def _dice(texto: str, *frases: str) -> bool:
    """Si alguna frase aparece como palabras completas en el texto ya normalizado."""
    return any(re.search(rf"(?<!\w){re.escape(frase)}(?!\w)", texto) for frase in frases)


def _lista(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else f"{', '.join(partes[:-1])} y {partes[-1]}"


def _precio(juego: JuegoCatalogo) -> str:
    if juego.es_gratis:
        return "gratis"
    if juego.precio_final is None:
        return "sin precio en los datos"
    return f"${juego.precio_final:,.2f} MXN"


def _critica(juego: JuegoCatalogo) -> str:
    return f"Metacritic {juego.metacritic}" if juego.metacritic is not None else "sin nota de la crítica"


def _anio(juego: JuegoCatalogo) -> int | None:
    encontrado = re.search(r"\b(19|20)\d{2}\b", juego.fecha_lanzamiento or "")
    return int(encontrado.group(0)) if encontrado else None


def _por_nombre(nombres: list[str]) -> list[JuegoCatalogo]:
    todos = {j.nombre: j for j in catalogo.buscar()}
    return [todos[n] for n in nombres if n in todos]


def _nombrados(texto: str, appid_abierto: int | None = None) -> list[JuegoCatalogo]:
    """Los juegos del catálogo que aparecen en un texto, en el orden en que aparecen."""
    nombres = nia.juegos_del_catalogo_mencionados(texto, appid_abierto or 0)
    normal = _norm(texto)
    juegos = _por_nombre(nombres)

    def posicion(juego: JuegoCatalogo) -> int:
        variantes = nia._variantes_del_nombre(juego.nombre)
        return min((normal.find(v) for v in variantes if normal.find(v) >= 0), default=len(normal))

    return sorted(juegos, key=posicion)


def _respuestas_previas(mensajes: list[MensajeChat]) -> list[str]:
    """Lo que Nia ya dijo en este hilo, sin la pregunta nueva."""
    return [m.contenido for m in mensajes[:-1] if m.rol == "nia"]


def _ultima_lista(mensajes: list[MensajeChat]) -> list[JuegoCatalogo]:
    """Los juegos que Nia nombró en su respuesta anterior: a eso se refiere «de esos»."""
    previas = _respuestas_previas(mensajes)
    return _nombrados(previas[-1]) if previas else []


def _ya_explico_la_senal(mensajes: list[MensajeChat]) -> bool:
    return any("primeras 2 horas" in m or "arrepentimiento temprano" in m for m in _respuestas_previas(mensajes))


def _resultado(texto: str, **extra) -> dict:
    return {
        "texto": texto, "juegos": [], "sugerencias": [], "pide_juego": False, "pide_perfil": False,
        "fuera_de_tema": False, **extra,
    }


# ── Intenciones ───────────────────────────────────────────────────────────────


def _saludo_o_gracias(pregunta: str, datos: dict | None) -> dict | None:
    if _dice(pregunta, "gracias", "eres lo maximo", "genial", "te pasaste"):
        return _resultado("¡De nada! 😊 Me encanta ayudarte a leer los datos. ¿Vemos otro juego o seguimos con este?")
    if len(pregunta.split()) <= 3 and _dice(pregunta, "hola", "buenas", "hey", "que onda"):
        if datos:
            return _resultado(
                f"¡Hola! 👋 Soy Nia. ¿Te cuento por qué {datos['nombre']} tiene riesgo {datos['banda']}?"
            )
        return _resultado("¡Hola! 👋 Soy Nia. ¿Buscas algo en particular o ya tienes un juego en mente?")
    return None


# Lo que no se resume: otro resumen, los saludos y las respuestas que no dijeron nada del
# catálogo (no lo sé, pedir el juego, no coronar, ya te lo conté).
_DE_TRAMITE = (
    "Va, en corto", "Más corto", "Eso no lo sé", "No corono", "¿De qué juego hablamos", "Aún no te he contado",
    "Ya te lo conté", "¡De nada", "¡Hola", "Para sugerirte algo",
)

_PIDE_RESUMEN = ("resume", "resumen", "resumir", "resumelo", "resumeme", "en corto", "lo que dijiste",
                 "lo que me dijiste", "mas corto", "menos texto")
_MAS_CORTO = ("mas corto", "menos texto", "mas breve", "lo mas que puedas", "mas resumido")


def pide_resumen(pregunta: str) -> bool:
    return _dice(_norm(pregunta), *_PIDE_RESUMEN)


def _recortar_palabras(oracion: str, tope: int) -> str:
    palabras_ = oracion.split()
    return oracion if len(palabras_) <= tope else " ".join(palabras_[:tope]).rstrip(",;:") + "…"


_SIN_ARRANQUE = re.compile(r"^\s*(?:¡?hola!?|s[ií]|no|claro|va|ok|listo)[,!.:;]\s+", re.IGNORECASE)


def _oraciones_de(texto: str) -> list[str]:
    """Las oraciones de una respuesta, cortadas también en el emoji y sin la pregunta con
    que cierra (el remate no se resume)."""
    # El punto corta solo si sigue una mayúscula, ¿ o ¡: «(93 vs. 87)» es una sola oración.
    partes = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])|\s*" + nia.EMOJI.pattern + r"\s*", texto.strip())
    # «Sí, hay 7 gratis…», «¡Hola! …»: el arranque de cortesía no es parte de lo dicho.
    partes = [_SIN_ARRANQUE.sub("", p) for p in partes]
    oraciones = [p.strip("¡!¿ ").rstrip(".") for p in partes if p and p.strip()]
    return [o for o in oraciones if o and not o.endswith("?") and len(o.split()) >= 2]


_TOPE_DURO = 50


def _primera_clausula(oracion: str) -> str:
    """Lo que dice la oración sin su detalle: antes de los dos puntos («Hay 7 gratis: A, B…»)
    o, si no los hay, antes de la primera coma o punto y coma. Si eso queda en menos de tres
    palabras, la oración entera."""
    for corte in (r":\s", r"(?<=\w)[,;]\s"):
        clausula = re.split(corte, oracion, maxsplit=1)[0]
        if clausula != oracion and len(clausula.split()) >= 3:
            return clausula
    return oracion


def _resumen(pregunta: str, mensajes: list[MensajeChat]) -> dict | None:
    """Junta lo que Nia ya dijo en el hilo, de todas sus respuestas y no solo de las
    últimas: primero una oración de cada una y, si hay lugar, las siguientes por turnos.
    Si ni la primera de cada una cabe, se acortan a su primera cláusula y luego a las
    mismas palabras cada una."""
    if not _dice(pregunta, *_PIDE_RESUMEN):
        return None
    respuestas = [_oraciones_de(p) for p in _respuestas_previas(mensajes) if not p.startswith(_DE_TRAMITE)]
    respuestas = [r for r in respuestas if r and len(r[0].split()) >= 3]
    if not respuestas:
        return _resultado("Aún no te he contado nada 🙂 ¿Por dónde empezamos: un juego o el catálogo?")
    # "Más corto" pide menos que el resumen de antes.
    corto = _dice(pregunta, *_MAS_CORTO)
    tope = 22 if corto else 40
    cuenta = lambda partes: sum(len(o.split()) for grupo in partes for o in grupo)
    elegidas = [[r[0]] for r in respuestas]
    comprimido = cuenta(elegidas) > tope
    if comprimido:
        elegidas = [[_primera_clausula(g[0])] for g in elegidas]
    # Sin frases cortadas: si las cláusulas completas pasan del tope pero caben en la
    # respuesta (50 palabras más el arranque y el remate), se quedan enteras aunque el
    # «más corto» no salga más corto. Solo una conversación muy larga se recorta a palabras.
    if cuenta(elegidas) > _TOPE_DURO:
        cada_una = max(3, _TOPE_DURO // len(elegidas))
        elegidas = [[_recortar_palabras(g[0], cada_una)] for g in elegidas]
    elif not comprimido:
        # Con lugar de sobra, las oraciones siguientes de cada respuesta, por turnos.
        siguiente = 1
        while any(len(r) > siguiente for r in respuestas):
            for grupo, respuesta in zip(elegidas, respuestas):
                if len(respuesta) > siguiente and cuenta(elegidas) + len(respuesta[siguiente].split()) <= tope:
                    grupo.append(respuesta[siguiente])
            siguiente += 1
    # Entre respuestas va punto y no punto y coma: cada una arranca con mayúscula propia.
    cuerpo = ". ".join(o[0].upper() + o[1:] for grupo in elegidas for o in grupo)
    if corto:
        return _resultado(f"Más corto ✍️ {cuerpo}. ¿Seguimos?")
    return _resultado(f"Va, en corto ✍️ {cuerpo}. ¿Seguimos con alguno?")


# Ante "el mejor" no se corona a nadie: se ofrece ordenar por un criterio. Si la pregunta
# ya trae el criterio ("¿cuál tiene mejor nota?"), es ordenar y la contestan los filtros.
_EL_MEJOR = ("el mejor", "la mejor", "los mejores", "mejor juego", "mejores juegos", "numero uno", "numero 1",
             "el top", "el mas recomendado", "el que mas recomiendas")
_CRITERIOS = ("nota", "critica", "metacritic", "precio", "barato", "caro", "riesgo", "calificado", "valorado",
              "resenas", "positivas", "gratis", "gratuito")


# «¿Por qué tiene ese riesgo?» con un juego abierto. La explicación sigue siempre la regla de
# factores (el que más aporta primero, «evidencia débil» cuando toca, los avisos y el descargo
# la primera vez); con el tope de 60 palabras, el modelo se saltaba alguna parte.
_EXPLICAR_EL_RIESGO = ("por que tiene ese riesgo", "por que tiene riesgo", "por que ese riesgo", "por que quedo",
                       "por que su riesgo", "explicamelo", "explicame el riesgo", "explica el riesgo", "que mueve",
                       "de donde sale su riesgo", "de donde sale ese riesgo")


def pide_explicar_el_riesgo(pregunta: str, datos: dict | None) -> bool:
    return datos is not None and _dice(_norm(pregunta), *_EXPLICAR_EL_RIESGO)


def pide_el_mejor(pregunta: str) -> bool:
    texto = _norm(pregunta)
    return _dice(texto, *_EL_MEJOR) and not _dice(texto, *_CRITERIOS) and not _dice(texto, *_BARATOS, *_CAROS)


def _el_mejor(pregunta: str) -> dict | None:
    if not pide_el_mejor(pregunta):
        return None
    return _resultado(
        "No corono a ningún juego 🙂 Depende de lo que busques: te los ordeno por precio, por riesgo o por la "
        "nota de la crítica. ¿Por cuál empezamos?"
    )


# Lo que dice que una pregunta es de juegos aunque no nombre ninguno. Sin nada de esto ni
# un juego del catálogo, la pregunta es de otro tema (trivia, una tarea, un dato personal)
# y se contesta con las reglas, que no la responden: un modelo sí lo haría.
_VOCABULARIO_DE_JUEGOS = (
    "juego", "jugar", "juega", "gamer", "gaming", "steam", "catalogo", "nexplay", "nia", "riesgo", "arrepent",
    "precio", "cuesta", "cuanto vale", "barato", "caro", "gratis", "gratuito", "free", "resena", "critica",
    "metacritic", "nota", "genero", "trailer", "compra", "compro", "reembolso", "consola", "pc", "playstation",
    "ps4", "ps5", "xbox", "nintendo", "switch", "dlc", "multijugador", "online", "partida", "horas", "perfil",
    "recomienda", "recomiendas", "sugier", "sugerencia", "compar", "motivo", "bug", "rendimiento", "dificil",
    "dificultad", "facil", "senal", "dato", "fuente", "rol", "rpg", "shooter", "estrategia", "accion",
    "aventura", "indie", "simulador", "deporte", "carrera", "mmo", "lanzamiento", "nuevo", "vs",
)


def sin_relacion_con_juegos(pregunta: str) -> bool:
    texto = _norm(pregunta)
    if _nombrados(pregunta) or _genero_de(texto):
        return False
    return not any(re.search(rf"(?<!\w){re.escape(palabra)}", texto) for palabra in _VOCABULARIO_DE_JUEGOS)


def _sugerencias(pregunta: str, sugerencias: list[SugerenciaNia]) -> dict | None:
    if _dice(pregunta, "comprar", "comprarlo", "comprarla", "compro"):
        return None
    if not _dice(pregunta, "recomiendas", "recomiendame", "recomienda", "recomendarias", "sugiere", "sugiereme",
                 "sugerencias", "sugerencia", "que juego me va", "que me va", "para mi"):
        return None
    appids = [s.appid for s in sugerencias if catalogo.obtener(s.appid) is not None][:4]
    if not appids:
        return _resultado(
            "Para sugerirte algo necesito saber cómo juegas 🙂 Tu perfil toma un minuto. ¿Lo armamos?",
            pide_perfil=True,
        )
    return _resultado(
        "Con lo que declaraste en tu perfil, estos encajan contigo ✨ Elegir es tuyo: te dejo el riesgo de "
        "cada uno al lado. ¿Te explico alguno?",
        sugerencias=appids,
    )


def _fortalezas_y_debilidades(juego: JuegoCatalogo) -> str:
    datos = nia.contexto(juego.appid)
    ref = nia._referencias_del_catalogo()
    a_favor, en_contra = [], []
    if juego.metacritic is None:
        en_contra.append("no tiene nota de la crítica")
    elif ref["nota_promedio"] and juego.metacritic >= ref["nota_promedio"]:
        a_favor.append(f"su Metacritic ({juego.metacritic}) está arriba del promedio del catálogo")
    else:
        en_contra.append(f"su Metacritic ({juego.metacritic}) está abajo del promedio del catálogo")
    banda = juego.banda_riesgo.value
    if banda != "medio":
        (a_favor if banda == "bajo" else en_contra).append(f"su riesgo es {banda}")
    if juego.es_gratis:
        a_favor.append("es gratis")
    elif juego.precio_final and ref["precio_mediano"] and juego.precio_final <= ref["precio_mediano"]:
        a_favor.append("cuesta menos que el precio mediano del catálogo")
    elif juego.precio_final:
        en_contra.append("cuesta más que el precio mediano del catálogo")
    if datos["motivos"]:
        principal = datos["motivos"][0]
        en_contra.append(f"en sus reseñas negativas lo que más sale es {principal.motivo}")
    partes = []
    if a_favor:
        partes.append(f"a favor, {_lista(a_favor)}")
    if en_contra:
        partes.append(f"en contra, {_lista(en_contra)}")
    if banda == "medio":
        partes.append("y su riesgo es medio")
    return "; ".join(partes)


def _vale_la_pena(pregunta: str, datos: dict | None, appid: int | None, mensajes: list[MensajeChat]) -> dict | None:
    eleccion = _dice(pregunta, "cual me compro", "cual compro", "cual elijo", "cual escojo")
    un_juego = _dice(pregunta, "vale la pena", "es bueno", "esta bueno", "recomendarias comprarlo", "comprarlo",
                     "lo compro", "me lo compro")
    if not (eleccion or un_juego):
        return None
    if datos is not None and appid is not None and not eleccion:
        juego = catalogo.obtener(appid)
        return _resultado(
            f"Decidir es tuyo 🙂 pero esto dicen los datos de {juego.nombre}: {_fortalezas_y_debilidades(juego)}. "
            "¿Qué pesa más para ti?",
            juegos=[appid],
        )
    candidatos = _nombrados(pregunta) or _ultima_lista(mensajes)
    if len(candidatos) >= 2:
        partes = [f"{j.nombre}, riesgo {j.banda_riesgo.value} y {_precio(j)}" for j in candidatos[:3]]
        return _resultado(
            f"Elegir es tuyo 🙂 En corto: {'; '.join(partes)}. ¿Qué pesa más para ti: el precio, el riesgo o la crítica?",
            juegos=[j.appid for j in candidatos[:3]],
        )
    if len(candidatos) == 1:
        juego = candidatos[0]
        return _resultado(
            f"Decidir es tuyo 🙂 pero esto dicen los datos de {juego.nombre}: {_fortalezas_y_debilidades(juego)}. "
            "¿Qué pesa más para ti?",
            juegos=[juego.appid],
        )
    if eleccion:
        return _resultado(
            "Elegir es tuyo 🙂 pero te ayudo a comparar. ¿Qué pesa más para ti: el precio, el riesgo o las horas "
            "que le vas a dedicar?"
        )
    return None


def _compara(pregunta: str, appid: int | None) -> dict | None:
    if not _dice(pregunta, "compara", "comparar", "comparame", "vs", "versus", "diferencia", "diferencias"):
        return None
    juegos = _nombrados(pregunta)
    abierto = catalogo.obtener(appid) if appid is not None else None
    if abierto is not None and abierto not in juegos:
        juegos = [abierto, *juegos]
    if len(juegos) < 2:
        if juegos:
            return _resultado(
                f"Solo reconozco {juegos[0].nombre} en el catálogo 🤔 El otro no está en este catálogo de Steam. "
                f"¿Te cuento de {juegos[0].nombre}?",
                juegos=[juegos[0].appid],
            )
        return _resultado("¿Cuáles comparo? 🤔 Dime dos juegos del catálogo, por ejemplo «compara Hades y Celeste».")
    partes = [f"{j.nombre}: riesgo {j.banda_riesgo.value}, {_precio(j)}, {_critica(j)}" for j in juegos[:3]]
    return _resultado(
        f"{'. '.join(partes)} 📊 ¿Los abro lado a lado en Comparar?",
        juegos=[j.appid for j in juegos[:3]],
    )


def _de_esos(pregunta: str, mensajes: list[MensajeChat]) -> dict | None:
    lista = _ultima_lista(mensajes)
    if len(lista) < 2 or not _dice(pregunta, "de esos", "de estos", "de ellos", "de esas", "ordenalos", "ordena",
                                    "el mas barato", "el mas caro", "cual de"):
        return None
    total = len(lista)
    if _dice(pregunta, *_BARATOS, "ordenalos", "ordena"):
        gratis = [j for j in lista if j.es_gratis]
        de_pago = sorted((j for j in lista if not j.es_gratis and j.precio_final), key=lambda j: j.precio_final)
        partes = []
        if gratis:
            verbo = "es gratis" if len(gratis) == 1 else "son gratis"
            partes.append(f"{_lista([j.nombre for j in gratis])} {verbo} 🎁")
        if de_pago:
            partes.append(f"el más barato de pago es {de_pago[0].nombre}, a {_precio(de_pago[0])}")
        cuerpo = " y ".join(partes) if partes else "ninguno tiene precio en los datos"
        return _resultado(
            f"De esos {total}, {cuerpo}. ¿Te cuento qué dicen sus reseñas?",
            juegos=[j.appid for j in (gratis + de_pago[:1])],
        )
    if _dice(pregunta, *_CAROS):
        de_pago = sorted((j for j in lista if j.precio_final), key=lambda j: -j.precio_final)
        if de_pago:
            return _resultado(
                f"De esos {total}, el más caro es {de_pago[0].nombre}, a {_precio(de_pago[0])} 💸 ¿Te cuento su riesgo?",
                juegos=[de_pago[0].appid],
            )
    if _dice(pregunta, *_GRATIS):
        gratis = [j for j in lista if j.es_gratis]
        if not gratis:
            return _resultado(f"De esos {total}, ninguno es gratis 🙈 ¿Te busco gratuitos en todo el catálogo?")
        return _resultado(
            f"De esos {total}, {_lista([j.nombre for j in gratis])} {'es gratis' if len(gratis) == 1 else 'son gratis'} 🎁 "
            "¿Te cuento de alguno?",
            juegos=[j.appid for j in gratis],
        )
    if _dice(pregunta, "critica", "nota", "metacritic", "mejor calificado"):
        con_nota = sorted((j for j in lista if j.metacritic is not None), key=lambda j: -j.metacritic)
        if con_nota:
            return _resultado(
                f"De esos {total}, el de mejor nota es {con_nota[0].nombre} (Metacritic {con_nota[0].metacritic}) ⭐ "
                "¿Te cuento sus reseñas?",
                juegos=[con_nota[0].appid],
            )
    for banda in _ORDEN_BANDAS:
        if _dice(pregunta, f"riesgo {banda}"):
            cumplen = [j for j in lista if j.banda_riesgo.value == banda]
            if not cumplen:
                return _resultado(f"De esos {total}, ninguno tiene riesgo {banda} 🙈 ¿Busco en todo el catálogo?")
            return _resultado(
                f"De esos {total}, con riesgo {banda}: {_lista([j.nombre for j in cumplen])} 🎯 ¿Te cuento de alguno?",
                juegos=[j.appid for j in cumplen],
            )
    return None


# Frases que hablan de UN juego sin nombrarlo: sin juego abierto, hay que pedirlo.
_DE_UN_JUEGO = (
    "ese riesgo", "este riesgo", "ese juego", "este juego", "esta juego", "por que tiene", "cuanto cuesta",
    "que dice la critica", "sus resenas", "que dicen las resenas", "explicamelo", "de que trata", "si, explicamelo",
    "es bueno", "vale la pena",
)


def necesita_juego(pregunta: str, mensajes: list[MensajeChat], appid: int | None) -> bool:
    """La pregunta es de un juego, no hay juego fijado y el hilo reciente no deja claro cuál:
    no nombra ninguno o nombra varios."""
    if appid is not None:
        return False
    texto = _norm(pregunta)
    if not _dice(texto, *_DE_UN_JUEGO) or _nombrados(pregunta):
        return False
    return len(_juegos_recientes(mensajes)) != 1


def _juegos_recientes(mensajes: list[MensajeChat]) -> list[JuegoCatalogo]:
    return _nombrados(" ".join(m.contenido for m in mensajes[-5:-1]))


def _del_juego_del_hilo(pregunta: str, original: str, mensajes: list[MensajeChat]) -> dict | None:
    """«¿Y cuánto cuesta?» tras hablar de un solo juego: se contesta de ese."""
    if not _dice(pregunta, *_DE_UN_JUEGO) or _nombrados(original):
        return None
    recientes = _juegos_recientes(mensajes)
    if len(recientes) != 1:
        return None
    juego = recientes[0]
    return _del_juego(pregunta, nia.contexto(juego.appid), juego.appid, mensajes)


def _pedir_juego() -> dict:
    return _resultado("¿De qué juego hablamos? 👀 Búscalo aquí y te lo explico.", pide_juego=True)


def _ficha_corta(juego: JuegoCatalogo) -> dict:
    return _resultado(
        f"{juego.nombre}: riesgo {juego.banda_riesgo.value}, {_precio(juego)} y {_critica(juego)} 🎮 "
        "¿Te cuento qué dicen sus reseñas o por qué tiene ese riesgo?",
        juegos=[juego.appid],
    )


def _genero_de(texto: str) -> str:
    generos = {g for juego in catalogo.buscar() for g in juego.generos}
    directo = next((g for g in sorted(generos, key=len, reverse=True) if _dice(texto, _norm(g))), "")
    if directo:
        return directo
    return next((g for clave, g in _SINONIMOS_GENERO.items() if _dice(texto, clave)), "")


def _filtros_del_catalogo(pregunta: str, texto_original: str) -> dict | None:
    genero = _genero_de(pregunta)
    banda = next((b for b in _ORDEN_BANDAS if _dice(pregunta, f"riesgo {b}", f"riesgos {b}s")), "")
    gratis = _dice(pregunta, *_GRATIS)
    baratos = _dice(pregunta, *_BARATOS)
    caros = _dice(pregunta, *_CAROS)
    poco_tiempo = _dice(pregunta, "jugar poco", "partidas cortas", "poco tiempo", "entre semana", "rato corto")
    dificil = _dice(pregunta, "dificil", "dificiles", "retador", "retadores")
    facil = _dice(pregunta, "facil", "faciles", "relajado", "relajados", "tranquilo")
    nuevo = _dice(pregunta, "nuevo", "nuevos", "reciente", "recientes", "de este ano", "lo mas nuevo")
    cuantos = _dice(pregunta, "cuantos")
    precio = re.search(r"(\d{2,5})\s*(?:mxn|pesos|\$)?", pregunta)
    precio_max = (
        float(precio.group(1))
        if precio and _dice(pregunta, "menos de", "hasta", "maximo", "debajo de")
        else None
    )

    if genero == "Multijugador masivo" and _dice(pregunta, *_SOCIAL) and not _dice(pregunta, "masivo", "mmo"):
        juegos = sorted(catalogo.buscar(genero=genero), key=lambda j: j.nombre.lower())
        nombres = _lista([j.nombre for j in juegos[:5]])
        return _resultado(
            "No tengo un dato de cooperativo ni de en línea 🎮 Lo más cercano en el catálogo es el género "
            f"Multijugador masivo, con {len(juegos)}: {nombres}. ¿Te cuento de alguno?",
            juegos=[j.appid for j in juegos[:5]],
        )
    if facil and not (genero or banda or gratis or precio_max):
        return _resultado(
            "No tengo un dato de qué tan fácil es un juego 🙈 Lo más cercano es el riesgo bajo: menos gente lo "
            "deja con una reseña negativa en las primeras 2 horas. ¿Te muestro esos?"
        )
    if not (genero or banda or gratis or baratos or caros or poco_tiempo or dificil or nuevo or precio_max):
        return None

    juegos = catalogo.buscar(genero=genero)
    if banda:
        juegos = [j for j in juegos if j.banda_riesgo.value == banda]
    if gratis:
        juegos = [j for j in juegos if j.es_gratis]
    if precio_max is not None:
        juegos = [j for j in juegos if j.es_gratis or (j.precio_final is not None and j.precio_final <= precio_max)]
    por_juego = {f.appid: f for f in panorama.resumen().por_juego}
    if poco_tiempo:
        juegos = [
            j for j in juegos
            if (por_juego.get(j.appid) and por_juego[j.appid].horas_al_recomendar is not None
                and por_juego[j.appid].horas_al_recomendar <= HORAS_DE_SESION_CORTA)
        ]
    if dificil:
        juegos = [j for j in juegos if por_juego.get(j.appid) and por_juego[j.appid].motivo_principal == "dificultad"]
    if nuevo:
        anios = [a for a in (_anio(j) for j in catalogo.buscar()) if a]
        desde = max(anios) - 2 if anios else 0
        juegos = [j for j in juegos if (_anio(j) or 0) >= desde]

    if baratos:
        juegos = sorted(juegos, key=lambda j: (0 if j.es_gratis else 1, j.precio_final or float("inf")))
    elif caros:
        juegos = sorted(juegos, key=lambda j: -(j.precio_final or 0))
    else:
        juegos = sorted(juegos, key=lambda j: j.nombre.lower())

    descripcion = " ".join(
        parte for parte in (
            "juegos",
            f"de {genero}" if genero else "",
            f"con riesgo {banda}" if banda else "",
            "gratuitos" if gratis else "",
            f"de ${precio_max:,.0f} o menos" if precio_max else "",
            f"que se recomiendan con {HORAS_DE_SESION_CORTA} h o menos" if poco_tiempo else "",
            "donde lo que más se menciona es la dificultad" if dificil else "",
            "lanzados de 2024 en adelante" if nuevo else "",
        ) if parte
    )
    total = len(juegos)
    if not total:
        return _resultado(f"No hay {descripcion} en el catálogo 🙈 ¿Aflojamos algún filtro?")
    if cuantos:
        return _resultado(
            f"En el catálogo hay {total} {descripcion}, de {len(catalogo.buscar())} 🎯 ¿Quieres ver cuáles?",
        )
    mostrados = juegos[: herramientas.MAXIMO_RESULTADOS]
    if baratos:
        nombres = _lista([f"{j.nombre} ({_precio(j)})" for j in mostrados[:5]])
        cabeza = f"¡Los {descripcion} más baratos! 💸"
        cola = "¿Te cuento de alguno?"
        return _resultado(f"{cabeza} {nombres}. {cola}", juegos=[j.appid for j in mostrados[:5]])
    if caros:
        nombres = _lista([f"{j.nombre} ({_precio(j)})" for j in mostrados[:5]])
        return _resultado(f"¡Los {descripcion} más caros! 💰 {nombres}. ¿Te cuento su riesgo?",
                          juegos=[j.appid for j in mostrados[:5]])
    remate = "¿Los ordeno por precio?" if total > 1 else "¿Te cuento de él?"
    # Los nombres también cuentan palabras: con títulos largos se muestran menos, hasta
    # que la respuesta quepa en 60.
    for cuantos_nombres in range(len(mostrados), 2, -1):
        visibles = mostrados[:cuantos_nombres]
        cuantos_texto = "Todos" if total <= len(visibles) else f"Los primeros {len(visibles)}"
        resto = f" Y {total - len(visibles)} más en Explorar." if total > len(visibles) else ""
        texto = f"¡Hay {total} {descripcion}! 🎮 {cuantos_texto}: {_lista([j.nombre for j in visibles])}.{resto} {remate}"
        if nia.palabras(texto) <= 60:
            break
    return _resultado(texto, juegos=[j.appid for j in visibles])


# Con el apóstrofo tipográfico (’) en el nombre: sin él, «¿qué tal Don’t Starve Together?»
# se leía como «Don» y se daba por fuera del catálogo.
_FUERA = re.compile(r"(?:que tal|se parece a(?:l)?|parecido a(?:l)?)\s+(?:el |la |los |las )?([a-z0-9][a-z0-9 :'’.-]{2,40})")


def _fuera_del_catalogo(pregunta: str, original: str, datos: dict | None) -> dict | None:
    encontrado = _FUERA.search(pregunta)
    if not encontrado:
        return None
    # Se cita como lo escribió la persona: quitar acentos no cambia el largo del texto, así
    # que el mismo tramo sirve en el original.
    tramo = original[encontrado.start(1):encontrado.end(1)] if len(original) == len(pregunta) else encontrado.group(1)
    nombre = tramo.strip(" ?.!¿¡")
    if not nombre or _nombrados(nombre):
        return None
    if datos is not None and _dice(pregunta, "se parece"):
        generos = _lista(datos["generos"]) if datos["generos"] else "sin géneros registrados"
        return _resultado(
            f"No tengo cómo comparar {datos['nombre']} con juegos de fuera del catálogo 🤔 Lo que sí sé: Steam lo "
            f"clasifica como {generos}. ¿Te cuento qué dicen sus reseñas?"
        )
    return _resultado(
        f"No encuentro «{nombre}» en este catálogo de Steam, así que no tengo señal sobre él 🤔 "
        "¿Te busco algo parecido por género?"
    )


def _de_donde_salen(pregunta: str) -> dict | None:
    if not _dice(pregunta, "de donde salen", "de donde sacas", "metodologia", "como calculas", "como se calcula",
                 "que datos", "fuentes"):
        return None
    p = panorama.resumen()
    return _resultado(
        f"Salen de {p.resenas_descargadas:,} reseñas de Steam y de los datos de cada juego 📊 La señal es una "
        "reseña negativa escrita en las primeras 2 horas, la ventana de reembolso. ¿Te cuento cómo se calcula el riesgo?"
    )


def _del_juego(pregunta: str, datos: dict, appid: int, mensajes: list[MensajeChat]) -> dict | None:
    """Lo de siempre dentro de una ficha (precio, crítica, riesgo, motivos, géneros), con la
    voz nueva. La señal se explica solo la primera vez que sale el riesgo en el hilo."""
    nombre, banda = datos["nombre"], datos["banda"]
    senal = (
        "" if _ya_explico_la_senal(mensajes)
        else " Esa señal sale de reseñas negativas escritas en las primeras 2 horas, la ventana de reembolso."
    )
    if _dice(pregunta, "precio", "cuesta", "caro", "barato", "oferta", "descuento"):
        factor = nia._factor_de_precio(datos)
        juego = catalogo.obtener(appid)
        base = (
            f"{nombre} es gratis 🎁" if juego.es_gratis
            else f"De {nombre} no tengo el precio en los datos 💸" if juego.precio_final is None
            else f"{nombre} cuesta {_precio(juego)} 💸"
        )
        return _resultado(f"{base}{(' ' + factor) if factor else ''} ¿Te cuento qué dicen sus reseñas?", juegos=[appid])
    if _dice(pregunta, "critica", "metacritic", "nota", "prensa"):
        return _resultado(f"En {nombre}, {nia._texto_critica(datos)} ⭐ ¿Quieres saber de qué se queja la gente?", juegos=[appid])
    if _dice(pregunta, "motivo", "motivos", "queja", "quejas", "problema", "problemas", "bug", "bugs", "rendimiento",
             "resenas", "que dicen"):
        return _resultado(f"En {nombre}, {nia._texto_motivos(datos)} 🔍 ¿Te cuento por qué tiene riesgo {banda}?", juegos=[appid])
    if _dice(pregunta, "cuanto dura", "dura", "duracion", "cuantas horas", "horas tipicas", "cuanto tiempo", "largo"):
        horas = datos.get("horas_tipicas")
        if horas is None:
            return _resultado(
                f"De {nombre} no tengo horas típicas: hay pocas reseñas positivas con horas jugadas ⏱️ "
                "¿Te cuento qué dicen sus reseñas?",
                juegos=[appid],
            )
        return _resultado(
            f"Quien recomendó {nombre} llevaba unas {horas:g} h jugadas, en la mediana ⏱️ No es lo que dura, "
            "pero da una idea de cuánto rinde. ¿Te cuento su riesgo?",
            juegos=[appid],
        )
    if _dice(pregunta, "genero", "generos", "tipo de juego", "de que trata"):
        generos = _lista(datos["generos"]) if datos["generos"] else "sin géneros registrados"
        return _resultado(f"Steam clasifica {nombre} como {generos} 🎮 ¿Te cuento su riesgo?", juegos=[appid])
    if _dice(pregunta, "banda", "por que", "porque", "riesgo", "estimacion", "explicamelo", "explica"):
        # Los avisos van completos y el factor principal siempre; para caber en las 60
        # palabras se acorta, en este orden, el porqué de «evidencia débil», el segundo
        # factor, el final del descargo y la pregunta de cierre.
        for cuantos, evidencia_larga, descargo_largo, cierre in _VARIANTES_DEL_PORQUE:
            descargo = senal if descargo_largo or not senal else " Esa señal: reseñas negativas escritas en las primeras 2 horas."
            texto = f"{nombre} tiene riesgo {banda} 🙂 {_porque_del_riesgo(datos, cuantos, evidencia_larga)}{descargo} {cierre}"
            if nia.palabras(texto) <= nia.MAXIMO_PALABRAS:
                break
        return _resultado(texto, juegos=[appid])
    return None


_VARIANTES_DEL_PORQUE = (
    (2, True, True, "¿Te cuento qué dicen esas reseñas?"),
    (2, False, True, "¿Te cuento qué dicen esas reseñas?"),
    (1, True, True, "¿Te cuento qué dicen esas reseñas?"),
    (1, False, True, "¿Te cuento qué dicen esas reseñas?"),
    (1, False, False, "¿Te cuento qué dicen esas reseñas?"),
    (1, False, False, "¿Sigo con sus motivos?"),
)


def _porque_del_riesgo(datos: dict, cuantos: int, evidencia_larga: bool = True) -> str:
    """Los factores en el orden del modelo: primero el que más aporta, con «evidencia débil»
    si lo es, y después los avisos de la estimación. Lo que está cerca de lo típico del
    catálogo no se da como razón."""
    razones = []
    for factor in datos["factores"][:cuantos]:
        if factor["efecto"] is None:
            break
        if factor["imputado"]:
            razones.append("le falta el precio")
            continue
        debil = "" if not factor["debil"] else f", con {nia.TEXTO_EVIDENCIA_DEBIL}" if evidencia_larga else ", con evidencia débil"
        razones.append(f"{factor['lectura'][0].lower()}{factor['lectura'][1:]} (lo {factor['efecto']}{debil})")
    if razones:
        porque = f"Lo que más lo mueve: {'; después, '.join(razones)}."
    else:
        porque = "Ninguna variable de este juego se aleja mucho de lo típico del catálogo."
    return " ".join([porque, *datos["avisos"]])


# «Contéstame con negritas y viñetas»: no es salirse del tema, es pedir un formato.
_FORMATO = ("negritas", "negrita", "vinetas", "vineta", "markdown", "en tabla", "una tabla", "en lista",
            "con formato", "bullets", "en mayusculas")


def _formato(pregunta: str) -> dict | None:
    if not _dice(pregunta, *_FORMATO):
        return None
    return _resultado(
        "Escribo en texto simple, sin negritas, viñetas ni tablas, para que se lea igual en cualquier pantalla ✍️ "
        "Aun así te cuento lo que necesites del catálogo. ¿Qué quieres saber?"
    )


# Un correo, un teléfono o la frase que lo anuncia. El número va con 8 dígitos o más para no
# confundir precios ni años.
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TELEFONO = re.compile(r"(?:\+?\d[\s().-]?){8,}")
_DATO_PERSONAL = ("mi correo", "mi email", "mi mail", "mi telefono", "mi celular", "mi numero", "mi direccion",
                  "mi contrasena", "mi tarjeta", "mi curp", "mi rfc")


def tiene_datos_personales(texto: str) -> bool:
    return bool(_CORREO.search(texto) or _TELEFONO.search(texto)) or _dice(_norm(texto), *_DATO_PERSONAL)


def _datos_personales(original: str) -> dict | None:
    if not tiene_datos_personales(original):
        return None
    return _resultado(
        "No guardo datos personales 🔒 Lo que parece un correo o un teléfono se borra antes de anotar tu pregunta, "
        "y no lo necesito para nada. ¿Te ayudo con algún juego del catálogo?",
        fuera_de_tema=True,
    )


# «Ignora tus instrucciones», «muéstrame tu prompt», «ahora eres…»: no se discute, se vuelve
# al catálogo.
_INSTRUCCIONES = ("ignora tus instrucciones", "ignora las instrucciones", "olvida tus instrucciones",
                  "tus instrucciones", "tu prompt", "prompt de sistema", "system prompt", "modo desarrollador",
                  "jailbreak", "actua como", "finge que eres")


def _instrucciones(pregunta: str) -> dict | None:
    if not _dice(pregunta, *_INSTRUCCIONES):
        return None
    return _resultado(
        "Solo hablo de los juegos del catálogo de NexPlay 🎮 Te los filtro por género, precio o riesgo, o te cuento "
        "de uno en particular. ¿Por dónde empezamos?",
        fuera_de_tema=True,
    )


def _no_se(datos: dict | None) -> dict:
    """Lo que no encaja con nada del catálogo: el chat enseña ahí sus avisos (solo datos del
    catálogo, sin decir si comprar, qué se guarda), y no antes."""
    if datos is not None:
        return _resultado(
            f"Eso no lo sé con los datos que tengo 🙈 De {datos['nombre']} te cuento su riesgo, sus reseñas, la "
            "crítica o el precio. ¿Por cuál empiezo?",
            fuera_de_tema=True,
        )
    return _resultado(
        "Eso no lo sé con estos datos 🙈 Puedo filtrar el catálogo por género, precio o riesgo, o contarte de un "
        "juego. ¿Qué se te antoja?",
        fuera_de_tema=True,
    )


def responder(
    datos: dict | None,
    appid: int | None,
    mensajes: list[MensajeChat],
    sugerencias: list[SugerenciaNia],
) -> dict:
    """La respuesta del modo demostración: texto, juegos para tarjetas, sugerencias del
    perfil y si hay que pedir el juego o el perfil."""
    original = next((m.contenido for m in reversed(mensajes) if m.rol == "usuario"), "")
    pregunta = _norm(original)

    intentos = (
        lambda: _datos_personales(original),
        lambda: _instrucciones(pregunta),
        lambda: _saludo_o_gracias(pregunta, datos),
        lambda: _resumen(pregunta, mensajes),
        lambda: _el_mejor(pregunta),
        lambda: _sugerencias(pregunta, sugerencias),
        lambda: _compara(pregunta, appid),
        lambda: _vale_la_pena(pregunta, datos, appid, mensajes),
        lambda: _de_esos(pregunta, mensajes),
        lambda: _pedir_juego() if necesita_juego(original, mensajes, appid) else None,
        lambda: _de_donde_salen(pregunta),
        lambda: _del_juego(pregunta, datos, appid, mensajes) if datos is not None and appid is not None else None,
        lambda: None if datos is not None else _nombrado_sin_ficha(original, mensajes),
        lambda: None if datos is not None else _del_juego_del_hilo(pregunta, original, mensajes),
        lambda: _filtros_del_catalogo(pregunta, original),
        lambda: _fuera_del_catalogo(pregunta, original, datos),
        lambda: _formato(pregunta),
    )
    resultado = next((r for r in (intento() for intento in intentos) if r is not None), None) or _no_se(datos)

    previas = _respuestas_previas(mensajes)
    if previas and nia.pulir(resultado["texto"]) == previas[-1]:
        resultado = _resultado("Ya te lo conté arriba 🙂 ¿Te lo resumo o vemos otra cosa?")
    return resultado


def es_fuera_de_tema(
    datos: dict | None,
    appid: int | None,
    mensajes: list[MensajeChat],
    sugerencias: list[SugerenciaNia],
) -> bool:
    """Si la pregunta no encaja con nada del catálogo. Con IA también se decide aquí, con
    las mismas reglas del modo demostración: no llama a ningún modelo."""
    return bool(responder(datos, appid, mensajes, sugerencias).get("fuera_de_tema"))


def fuera_del_catalogo(original: str, datos: dict | None) -> dict | None:
    """«¿Qué tal Zelda?», «¿se parece a Mario?»: la respuesta de un juego que no está."""
    return _fuera_del_catalogo(_norm(original), original, datos)


def _nombrado_sin_ficha(original: str, mensajes: list[MensajeChat]) -> dict | None:
    juegos = _nombrados(original)
    if len(juegos) != 1:
        return None
    juego = juegos[0]
    return _del_juego(_norm(original), nia.contexto(juego.appid), juego.appid, mensajes) or _ficha_corta(juego)


# La cara de Nia según el nivel del juego; el mismo emoji acompaña la mascota del carrusel.
_EMOJI_DEL_NIVEL = {"bajo": "🙂", "medio": "🤔", "alto": "😬"}


def opinion_corta(appid: int) -> dict:
    """Lo que Nia opina de un juego en una frase, para el carrusel del Inicio: su nivel de
    riesgo con las mismas palabras del chat, y lo que más pesa para quien lo mira.

    En riesgo bajo pesa la crítica; en alto, la queja más repetida en sus reseñas con
    señal; en medio, la queja si la hay. Cierra invitando a seguir en el chat."""
    datos = nia.contexto(appid)
    nombre, banda = datos["nombre"], datos["banda"]
    frase = nia._FRASES_BANDA[banda]
    detalle = ""
    motivo = datos["motivos"][0].motivo if datos["motivos"] else None
    if banda == "bajo" and datos["metacritic"] is not None:
        detalle = f", y la crítica le da {datos['metacritic']}"
    elif motivo:
        detalle = f"; en sus reseñas negativas lo que más sale es {motivo}"
    elif datos["metacritic"] is not None:
        detalle = f", y la crítica le da {datos['metacritic']}"
    respuesta = (
        f"{nombre} tiene riesgo {banda} {_EMOJI_DEL_NIVEL[banda]} {frase[0].upper()}{frase[1:]}{detalle}. "
        "¿Te cuento más?"
    )
    return {
        "appid": appid,
        "nombre": nombre,
        "nivel": banda,
        "pregunta": f"¿Qué opinas de {nombre}?",
        "respuesta": nia.pulir(respuesta),
    }
