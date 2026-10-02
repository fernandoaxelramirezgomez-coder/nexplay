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
from collections import Counter

from .. import catalogo, panorama, scoring
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
    if len(partes) == 1:
        return partes[0]
    # «Estrategia e Indie»: ante el sonido i la conjunción es «e» (pero «y hierro»).
    y = "e" if re.match(r"(?i)h?i(?![aeouáéóú])", partes[-1]) else "y"
    return f"{', '.join(partes[:-1])} {y} {partes[-1]}"


def _mayuscula(texto: str) -> str:
    return f"{texto[0].upper()}{texto[1:]}" if texto else texto


def _precio(juego: JuegoCatalogo) -> str:
    if juego.es_gratis:
        return "gratis"
    if juego.precio_final is None:
        return "sin precio en los datos"
    return nia.pesos_hablados(juego.precio_final)


def _cuesta(juego: JuegoCatalogo) -> str:
    """«es gratis», «cuesta $999» o «no tiene precio en los datos»: para decirlo en una frase."""
    if juego.es_gratis:
        return "es gratis"
    if juego.precio_final is None:
        return "no tiene precio en los datos"
    return f"cuesta {nia.pesos_hablados(juego.precio_final)}"


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


def _respuesta_anterior(mensajes: list[MensajeChat]) -> MensajeChat | None:
    return next((m for m in reversed(mensajes[:-1]) if m.rol == "nia"), None)


def _juegos_guardados(mensaje: MensajeChat | None) -> list[JuegoCatalogo]:
    """Los juegos de las tarjetas de un mensaje de Nia, tal como volvieron en el historial."""
    if mensaje is None:
        return []
    return [j for j in (catalogo.obtener(a) for a in mensaje.juegos) if j is not None]


def _ultima_lista(mensajes: list[MensajeChat]) -> list[JuegoCatalogo]:
    """Los juegos de la respuesta anterior: a eso se refieren «de esos» y «esos dos». Primero
    los de sus tarjetas, que vuelven como dato; si no vinieron, los nombres del texto."""
    anterior = _respuesta_anterior(mensajes)
    return _juegos_guardados(anterior) or (_nombrados(anterior.contenido) if anterior else [])


def _resultado(texto: str, **extra) -> dict:
    return {
        "texto": texto, "juegos": [], "sugerencias": [], "pide_juego": False, "pide_perfil": False,
        "fuera_de_tema": False, "oferta": None, **extra,
    }


def _oferta(intencion: str, juegos: list[int] | None = None, criterio: str | None = None,
            pregunta: str | None = None) -> dict:
    return {"intencion": intencion, "juegos": list(juegos or [])[:8], "criterio": criterio, "pregunta": pregunta}


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


# Lo que no se resume: otro resumen y las respuestas que no dijeron nada del catálogo (no lo
# sé, pedir el juego, no coronar, ya te lo conté). «¡Hola!» no va aquí: el modelo abre con él
# su primera respuesta, y por eso el resumen se la saltaba entera; un saludo solo, sin nada
# más, se queda fuera porque no le queda ninguna oración que resumir.
_DE_TRAMITE = (
    "Va, en corto", "Más corto", "Eso no lo sé", "No corono", "¿De qué juego hablamos", "Aún no te he contado",
    "Ya te lo conté", "¡De nada", "Sin perfil no sé",
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
    # «Y 2 más en Explorar» es la cola de una lista: suelta no dice nada.
    oraciones = [o for o in oraciones if o and not o.endswith("?") and len(o.split()) >= 2 and not _COLA.match(o)]
    # La respuesta corta con que abre («Un poco 💸», «En parte 🎮», «Sobre todo, de
    # rendimiento 🔍», «Soy Nia») no dice de qué se habló: se resume lo que sigue.
    while oraciones and (len(oraciones[0].split()) < 3 or _APERTURA.match(oraciones[0])):
        oraciones = oraciones[1:]
    return oraciones


_COLA = re.compile(r"^Y \d+ más\b")
_APERTURA = re.compile(
    r"^(?:un poco|en parte|no mucho|casi no|no se sabe|muy poco|nada todavía|(?:sobre todo, )?de [\wáéíóúñ ]{1,30})$",
    re.IGNORECASE,
)


_TOPE_DURO = 50


def _primera_clausula(oracion: str) -> str:
    """Lo que dice la oración sin su detalle: antes de la lista que abren los dos puntos o un
    guion largo («Hay 7 gratis: A, B…», «hay 7 gratis—A, B…») o, si no hay lista, antes de la
    primera coma o punto y coma. Si eso queda en menos de tres palabras, la oración entera.
    Con el guion largo cortaba en la primera coma y dejaba media lista."""
    # Los dos puntos de un nombre («Amnesia: The Bunker») no abren ninguna lista.
    nombres = [n for n in (j.nombre for j in catalogo.buscar()) if ":" in n and n in oracion]
    protegida = oracion
    for nombre in nombres:
        protegida = protegida.replace(nombre, nombre.replace(":", "\x00"))
    for corte in (r":\s|\s*[—–]\s*", r"(?<=\w)[,;]\s"):
        clausula = re.split(corte, protegida, maxsplit=1)[0]
        if clausula != protegida and len(clausula.split()) >= 3:
            return clausula.replace("\x00", ":")
    return oracion


# «Hay 7 gratis» sin la lista que lo seguía no dice de qué: se lee «Hay 7 juegos gratis».
_CUANTOS_SIN_SUSTANTIVO = re.compile(r"\b([Hh]ay) (\d+) (gratis|gratuitos)\b")


def _resumen(pregunta: str, mensajes: list[MensajeChat]) -> dict | None:
    """Junta lo que Nia ya dijo en el hilo, de todas sus respuestas y no solo de las
    últimas: primero una oración de cada una y, si hay lugar, las siguientes por turnos.
    Si ni la primera de cada una cabe, se acortan a su primera cláusula y luego a las
    mismas palabras cada una."""
    if not _dice(pregunta, *_PIDE_RESUMEN):
        return None
    respuestas = [_oraciones_de(p) for p in _respuestas_previas(mensajes) if not p.startswith(_DE_TRAMITE)]
    respuestas = [r for r in respuestas if r]
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
    cuerpo = _CUANTOS_SIN_SUSTANTIVO.sub(r"\1 \2 juegos \3", cuerpo)
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
        "nota de la crítica. ¿Por cuál empezamos?",
        oferta=_oferta("ordenar"),
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
    # Lo que Nia y la ficha dicen al explicar el riesgo: «¿qué significa evidencia débil?»
    # es una pregunta de seguimiento, no de otro tema.
    "evidencia", "estimacion", "extrapol", "confiable", "factor", "median", "tipico",
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
    appids = _de_las_sugerencias(sugerencias)
    if not appids:
        return _resultado(nia.INVITA_AL_PERFIL, pide_perfil=True)
    return _resultado(
        "Estos coinciden con lo que declaraste en tu perfil ✨ Son coincidencias, no una elección: decidir es tuyo,"
        " y el riesgo de cada uno va en su tarjeta. ¿Los ordeno por riesgo?",
        sugerencias=appids,
    )


def _de_las_sugerencias(sugerencias: list[SugerenciaNia]) -> list[int]:
    return [s.appid for s in sugerencias if catalogo.obtener(s.appid) is not None][:4]


def _fortalezas_y_debilidades(juego: JuegoCatalogo) -> str:
    datos = nia.contexto(juego.appid)
    ref = nia._referencias_del_catalogo()
    a_favor, en_contra, aparte = [], [], []
    # La nota pesa a favor o en contra según el modelo, como en la ficha: dentro de la banda
    # neutral no es ni lo uno ni lo otro.
    nota = next((f for f in datos["factores"] if f["etiqueta"] == "nota de Metacritic"), None)
    if juego.metacritic is None:
        en_contra.append("la crítica especializada no lo reseñó")
    elif nota is None:
        aparte.append(f"la crítica le dio {juego.metacritic}")
    elif nota["efecto"] is None:
        aparte.append(nota["idea"])
    else:
        (a_favor if nota["efecto"] == "baja" else en_contra).append(nota["idea"])
    banda = juego.banda_riesgo.value
    if banda != "medio":
        (a_favor if banda == "bajo" else en_contra).append(f"su riesgo es {banda}")
    if juego.es_gratis:
        a_favor.append("es gratis")
    elif juego.precio_final and ref["precio_mediano"] and juego.precio_final <= ref["precio_mediano"]:
        a_favor.append("cuesta menos que lo normal del catálogo")
    elif juego.precio_final:
        en_contra.append("cuesta más que lo normal del catálogo")
    if datos["motivos"]:
        principal = datos["motivos"][0]
        en_contra.append(f"en sus reseñas negativas lo que más sale es {principal.motivo}")
    partes = []
    if a_favor:
        partes.append(f"a favor, {_lista(a_favor)}")
    if en_contra:
        partes.append(f"en contra, {_lista(en_contra)}")
    if aparte:
        partes.append(_lista(aparte))
    if banda == "medio":
        partes.append("y su riesgo es medio")
    return "; ".join(partes)


# «¿Cuál me compro?»: con modelo también va por reglas. El modelo contestaba que con el perfil
# elegiría por la persona; con perfil solo se muestran coincidencias.
_ELECCION = ("cual me compro", "cual compro", "cual elijo", "cual escojo", "cual me llevo", "que me compro",
             "que juego compro", "cual me conviene")


def pide_eleccion(pregunta: str) -> bool:
    return _dice(_norm(pregunta), *_ELECCION)


def _vale_la_pena(pregunta: str, datos: dict | None, appid: int | None, mensajes: list[MensajeChat],
                  sugerencias: list[SugerenciaNia]) -> dict | None:
    eleccion = _dice(pregunta, *_ELECCION)
    un_juego = _dice(pregunta, "vale la pena", "es bueno", "esta bueno", "recomendarias comprarlo", "comprarlo",
                     "lo compro", "me lo compro")
    if not (eleccion or un_juego):
        return None
    if datos is not None and appid is not None and not eleccion:
        juego = catalogo.obtener(appid)
        return _resultado(
            f"Decidir es tuyo 🤔 pero esto dicen los datos de {juego.nombre}: {_fortalezas_y_debilidades(juego)}. "
            "¿Te cuento qué dicen sus reseñas?",
            juegos=[appid],
        )
    candidatos = _nombrados(pregunta) or _ultima_lista(mensajes)
    if len(candidatos) >= 2:
        # El riesgo de cada uno va en su tarjeta: aquí solo lo que no se ve en ella.
        partes = [f"{j.nombre} {_cuesta(j)}" for j in candidatos[:3]]
        return _resultado(
            f"Elegir es tuyo 🤔 En corto: {'; '.join(partes)}, y su riesgo va en cada tarjeta. ¿Qué pesa más para"
            " ti: el precio, el riesgo o la crítica?",
            juegos=[j.appid for j in candidatos[:3]],
        )
    if len(candidatos) == 1:
        juego = candidatos[0]
        return _resultado(
            f"Decidir es tuyo 🤔 pero esto dicen los datos de {juego.nombre}: {_fortalezas_y_debilidades(juego)}. "
            "¿Te cuento qué dicen sus reseñas?",
            juegos=[juego.appid],
        )
    if eleccion and _de_las_sugerencias(sugerencias):
        return _resultado(
            "Elegir es tuyo 🤔 Te dejo los que coinciden con lo que declaraste en tu perfil, con su riesgo en cada"
            " tarjeta. ¿Qué pesa más para ti: el precio, el riesgo o la crítica?",
            sugerencias=_de_las_sugerencias(sugerencias),
        )
    if eleccion:
        return _resultado(
            "Elegir es tuyo 🤔 pero te ayudo a comparar. ¿Qué pesa más para ti: el precio, el riesgo o la crítica?",
            oferta=_oferta("ordenar"),
        )
    return None


_COMPARAR = ("compara", "comparar", "comparame", "vs", "versus", "diferencia", "diferencias")


def pide_comparar(pregunta: str) -> bool:
    return _dice(_norm(pregunta), *_COMPARAR)


def _compara(pregunta: str, appid: int | None) -> dict | None:
    if not _dice(pregunta, *_COMPARAR):
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
    juegos = juegos[:3]
    con_nota = [j for j in juegos if j.metacritic is not None]
    sin_nota = [j.nombre for j in juegos if j.metacritic is None]
    critica = []
    if con_nota:
        critica.append(f"La crítica le dio {_lista([f'{j.metacritic} a {j.nombre}' for j in con_nota])}")
    if sin_nota:
        critica.append(f"{_lista(sin_nota)} no {'tiene' if len(sin_nota) == 1 else 'tienen'} nota de la crítica")
    precios = []
    for j in juegos:
        if not j.es_gratis and j.precio_final is None:
            precios.append(f"de {j.nombre} no hay precio, así que su estimación es menos confiable")
        else:
            precios.append(f"{j.nombre} {_cuesta(j)}")
    # El riesgo de cada uno va en su tarjeta: el texto no lo repite juego por juego. Primero
    # lo que las distingue, para que el resumen del hilo se quede con eso.
    critica_, precio_ = f"{'; '.join(critica)} 📊", f"{_mayuscula(_lista(precios))}."
    tarjetas = "El riesgo de cada uno va en su tarjeta."
    # Con tres títulos largos no cabe todo en 60 palabras: primero se quita el precio, luego la crítica.
    for frases in ((critica_, precio_, tarjetas), (critica_, tarjetas), (f"{tarjetas[:-1]} 📊",)):
        texto = f"{' '.join(frases)} {nia.CIERRE_DE_COMPARAR}"
        if nia.palabras(texto) <= nia.MAXIMO_PALABRAS:
            break
    return _resultado(texto, juegos=[j.appid for j in juegos])


def responde_de_esos(pregunta: str, mensajes: list[MensajeChat]) -> bool:
    """«¿Y el más barato de esos dos?»: con los juegos del turno anterior las reglas lo
    contestan, y con modelo también, porque el modelo no siempre sabía cuáles eran."""
    return _de_esos(_norm(pregunta), mensajes) is not None


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
        elegidos = gratis + de_pago[:1]
        cierre = "¿Te cuento qué dicen sus reseñas?" if len(elegidos) == 1 else nia.CIERRE_DE_COMPARAR
        return _resultado(f"De esos {total}, {cuerpo} 💸 {cierre}", juegos=[j.appid for j in elegidos])
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
            return _resultado(f"De esos {total}, ninguno es gratis 🙈 ¿Te busco gratuitos en todo el catálogo?",
                              oferta=_oferta("buscar", pregunta="¿Hay juegos gratis?"))
        return _resultado(
            f"De esos {total}, {_lista([j.nombre for j in gratis])} {'es gratis' if len(gratis) == 1 else 'son gratis'} 🎁 "
            + ("¿Te cuento de él?" if len(gratis) == 1 else "¿Los ordeno por riesgo?"),
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
                return _resultado(f"De esos {total}, ninguno tiene riesgo {banda} 🙈 ¿Busco en todo el catálogo?",
                                  oferta=_oferta("buscar", pregunta=f"Juegos con riesgo {banda}"))
            return _resultado(
                f"De esos {total}, con riesgo {banda}: {_lista([j.nombre for j in cumplen])} 🎯 "
                + ("¿Te cuento de él?" if len(cumplen) == 1 else "¿Los ordeno por precio?"),
                juegos=[j.appid for j in cumplen],
            )
    return None


# Frases que hablan de UN juego sin nombrarlo: sin juego abierto, hay que pedirlo.
_DE_UN_JUEGO = (
    "ese riesgo", "este riesgo", "ese juego", "este juego", "esta juego", "por que tiene", "cuanto cuesta",
    "que dice la critica", "sus resenas", "que dicen las resenas", "explicamelo", "de que trata", "si, explicamelo",
    "es bueno", "vale la pena", "encaja conmigo", "encaja con mis gustos", "encaja con mi perfil",
)


def necesita_juego(pregunta: str, mensajes: list[MensajeChat], appid: int | None) -> bool:
    """La pregunta es de un juego, no hay juego fijado y el hilo reciente no deja claro cuál:
    no nombra ninguno o nombra varios."""
    if appid is not None:
        return False
    # «Sí, explícamelo» a una oferta la cumple: no pide un juego.
    if es_afirmacion(pregunta) and _oferta_previa(mensajes) is not None:
        return False
    texto = _norm(pregunta)
    if not _dice(texto, *_DE_UN_JUEGO) or _nombrados(pregunta):
        return False
    return len(_juegos_recientes(mensajes)) != 1


def _juegos_recientes(mensajes: list[MensajeChat]) -> list[JuegoCatalogo]:
    return _juegos_guardados(_respuesta_anterior(mensajes)) or _nombrados(" ".join(m.contenido for m in mensajes[-5:-1]))


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
    return _resultado("¿De qué juego hablamos? 👀 Búscalo aquí y te lo explico.", pide_juego=True,
                      oferta=_oferta("elegir_juego"))


def _precio_hablado(juego: JuegoCatalogo) -> str:
    if juego.es_gratis:
        return "es gratis"
    if juego.precio_final is None:
        return "no hay dato de su precio, así que su riesgo es menos confiable"
    return nia.precio_frente_al_catalogo(juego.precio_final, nia._referencias_del_catalogo()["precio_mediano"])


def _critica_hablada(juego: JuegoCatalogo, datos: dict) -> str:
    """La nota con la lectura de la ficha: «en lo normal» solo si el modelo la deja en la
    banda neutral."""
    if juego.metacritic is None:
        return "la crítica especializada no lo reseñó"
    nota = next((f for f in datos["factores"] if f["etiqueta"] == "nota de Metacritic"), None)
    return nota["idea"] if nota else f"la crítica le dio {juego.metacritic}"


def _ficha_corta(juego: JuegoCatalogo) -> dict:
    datos = nia.contexto(juego.appid)
    banda = juego.banda_riesgo.value
    precio = _precio_hablado(juego)
    union = ", y " if "," in precio else " y "
    return _resultado(
        f"{juego.nombre} tiene riesgo {banda} {nia.EMOJI_DEL_NIVEL[banda]} {_mayuscula(precio)}{union}"
        f"{_critica_hablada(juego, datos)}. ¿Te cuento por qué tiene ese riesgo?",
        juegos=[juego.appid],
    )


# «¿Cuphead es para mí si me importa el rendimiento?»: lo que la persona nombra se lleva a las
# categorías de quejas y se dice en conteos. Si las quejas lo tocan, es una alerta; si no, no
# es aval. Nunca un dictamen («adecuado», «te conviene»): lo que dicen los datos de eso, lo que
# no dicen y que decidir es de quien pregunta.
_ASPECTOS = (
    # (palabras de la persona, categorías de quejas, lo que esas quejas no dicen)
    (("rendimiento", "fps", "lag", "estabilidad", "estable", "optimizacion", "optimizado", "se traba", "crashea"),
     ("rendimiento", "bugs"), "no dicen cómo corre en tu equipo"),
    (("bugs", "bug", "errores", "fallas", "glitches"), ("bugs",), "no dicen si ya los corrigieron"),
    (("dificil", "dificultad", "reto", "desafiante"), ("dificultad",), "no dicen qué tan difícil se te hará a ti"),
    (("controles", "jugabilidad", "mando"), ("controles",), "no dicen cómo se siente en tus manos"),
    (("historia", "trama", "contenido", "rejugabilidad"), ("contenido",), "no cuentan de qué trata ni cuánto dura"),
    (("caro", "vale lo que cuesta"), ("precio",), "no dicen si a ti te parece caro"),
)
# Lo que no se mide: se dice que no está en los datos, con las categorías que sí hay.
_SIN_MEDIR = {"graficos": "los gráficos", "grafica": "la gráfica", "musica": "la música", "arte": "el arte",
              "sonido": "el sonido", "doblaje": "el doblaje", "ambientacion": "la ambientación"}
# «Caro» solo cuenta como aspecto si la persona dice que le importa; si no, es una pregunta de precio.
_LE_IMPORTA = ("me gusta", "me importa", "me importan", "me preocupa", "me interesa", "busco", "prefiero",
               "para mi", "adecuado", "adecuada", "me conviene", "me sirve", "odio", "no soporto")
_CATEGORIAS = ("rendimiento", "bugs", "dificultad", "controles", "contenido", "precio")


def _aspecto_pedido(pregunta: str, original: str, appid: int | None):
    """El juego, las categorías, lo que no dicen y lo que no se mide, si la pregunta es por un
    aspecto de un solo juego (el nombrado o el de la ficha). None si no."""
    nombrados = _nombrados(original)
    if len(nombrados) > 1:
        return None
    juego = nombrados[0] if nombrados else catalogo.obtener(appid) if appid is not None else None
    if juego is None:
        return None
    grupos = [g for g in _ASPECTOS if _dice(pregunta, *g[0])]
    if grupos and grupos[0][1] == ("precio",) and len(grupos) == 1 and not _dice(pregunta, *_LE_IMPORTA):
        return None
    sin_medir = [nombre for palabra, nombre in _SIN_MEDIR.items() if _dice(pregunta, palabra)]
    if not grupos and not (sin_medir and _dice(pregunta, *_LE_IMPORTA)):
        return None
    categorias = list(dict.fromkeys(c for g in grupos for c in g[1]))
    return juego, categorias, grupos[0][2] if grupos else None, sin_medir


def pide_aspecto(pregunta: str, appid: int | None) -> bool:
    """Con modelo, solo si pide un veredicto («¿es adecuado para mí si me importa…?»): ahí el
    modelo daba un dictamen. «¿Hades es difícil?» sigue yendo al modelo, con la misma regla."""
    normal = _norm(pregunta)
    return _dice(normal, *_LE_IMPORTA) and _aspecto_pedido(normal, pregunta, appid) is not None


def _aspecto(pregunta: str, original: str, appid: int | None) -> dict | None:
    pedido = _aspecto_pedido(pregunta, original, appid)
    if pedido is None:
        return None
    juego, categorias, limite, sin_medir = pedido
    nombre, tarjeta = juego.nombre, {"juegos": [juego.appid]} if appid is None else {}
    if not categorias:
        return _resultado(
            f"De {_lista(sin_medir)} no tengo datos 🤷 De {nombre} solo cuento quejas de {_lista(list(_CATEGORIAS))};"
            " decidir es tuyo. ¿Te cuento qué dicen sus reseñas?",
            **tarjeta,
        )
    datos = nia.contexto(juego.appid)
    total, banda = datos["clasificadas"], datos["banda"]
    if total == 0:
        ninguna = "no tiene reseñas negativas tempranas" if datos["n_casos"] == 0 else "ninguna de sus reseñas negativas tempranas dice por qué"
        return _resultado(
            f"No tengo cómo saberlo de {nombre} 🤷 {_mayuscula(ninguna)}, así que de {_lista(categorias)} no hay"
            f" quejas que contar; decidir es tuyo. ¿Te cuento por qué tiene riesgo {banda}?",
            **tarjeta,
        )
    conteos = dict(nia.quejas_en_conteos(datos))
    orden = sorted(categorias, key=lambda c: -conteos.get(c, 0))
    con_quejas = [(c, conteos[c]) for c in orden if conteos.get(c, 0) > 0]
    sin_quejas = [c for c in orden if conteos.get(c, 0) == 0]
    if not con_quejas:
        cuantas = "su única reseña negativa temprana que dice por qué" if total == 1 else f"sus {total} reseñas negativas tempranas que dicen por qué"
        ninguna = " ni de ".join(sin_quejas)
        pocas = ", y son pocas" if total < 10 else ""
        return _resultado(
            f"Ninguna queja de eso en {nombre} 🔍 De {cuantas}, ninguna habla de {ninguna}. Que nadie se queje no"
            f" garantiza nada{pocas}: {limite}; decidir es tuyo. ¿Te cuento qué más dicen sus reseñas?",
            **tarjeta,
        )
    (primera, c1), resto = con_quejas[0], con_quejas[1:]
    partes = [f"{c1} {'habla' if c1 == 1 else 'hablan'} de {primera}", *(f"{c} de {cat}" for cat, c in resto)]
    partes += [f"ninguna de {cat}" for cat in sin_quejas]
    if total == 1:
        cuerpo = f"Su única reseña negativa temprana que dice por qué habla de {primera}"
        cuerpo += f", no de {' ni de '.join(sin_quejas)}" if sin_quejas else ""
    else:
        cuerpo = f"De sus {total} reseñas negativas tempranas que dicen por qué, {_lista(partes)}"
    cautela = f"Son pocas, tómalo con cautela, y {limite}" if total < 10 else f"Eso sí, {limite}"
    return _resultado(
        f"Ojo con eso en {nombre} ⚠️ {cuerpo}. {cautela}; decidir es tuyo. ¿Te cuento qué más dicen sus reseñas?",
        **tarjeta,
    )


# «¿Encaja conmigo?»: qué géneros declarados tiene el juego y cuáles no. Sin porcentajes.
_ENCAJA = (
    "encaja conmigo", "encaja con mis gustos", "encaja con mi perfil", "encaja con mis generos", "encaja con lo que",
    "es para mi", "va conmigo", "va con mis gustos", "me va a gustar", "coincide con mis gustos",
    "coincide con mi perfil", "es de mis generos",
)
_CUANTOS_EN_LETRA = {1: "uno", 2: "dos", 3: "tres", 4: "cuatro"}


def _encaja(pregunta: str, original: str, appid: int | None, mensajes: list[MensajeChat],
            generos: list[str] | None) -> dict | None:
    if not _dice(pregunta, *_ENCAJA):
        return None
    juego = catalogo.obtener(appid) if appid is not None else None
    if juego is None:
        nombrados = _nombrados(original) or _juegos_recientes(mensajes)
        juego = nombrados[0] if len(nombrados) == 1 else None
    if juego is None:
        # «¿Qué juego es para mí?» es pedir sugerencias, no medir uno.
        return None
    afinidad = nia.afinidad(juego, generos)
    if afinidad is None:
        return _resultado(
            "Para decirte si encaja necesito tus géneros 🎮 Tu perfil toma un minuto. ¿Lo armamos?", pide_perfil=True
        )
    nombre, coinciden, faltan = juego.nombre, afinidad["coinciden"], afinidad["no_tiene"]
    if not coinciden:
        cuerpo = (f"No mucho 🎮 Steam pone {nombre} en {_lista(juego.generos) if juego.generos else 'ningún género'},"
                  f" y ninguno está entre tus géneros ({_lista(afinidad['declarados'])}).")
    elif not faltan:
        cuales = "tu género" if len(coinciden) == 1 else "los géneros que declaraste"
        cuerpo = f"Sí 🎮 {nombre} es de {_lista(coinciden)}, {cuales}."
    else:
        cuantos = _CUANTOS_EN_LETRA.get(len(coinciden), str(len(coinciden)))
        cuerpo = (f"En parte 🎮 {nombre} es de {_lista(coinciden)}, {cuantos} de tus géneros; de {_lista(faltan)},"
                  " que también declaraste, no tiene nada.")
    return _resultado(
        f"{cuerpo} Tu perfil no cambia su riesgo, que sigue en {juego.banda_riesgo.value}. "
        "¿Te cuento por qué tiene ese riesgo?",
        juegos=[juego.appid],
    )


def _genero_de(texto: str) -> str:
    generos = {g for juego in catalogo.buscar() for g in juego.generos}
    directo = next((g for g in sorted(generos, key=len, reverse=True) if _dice(texto, _norm(g))), "")
    if directo:
        return directo
    return next((g for clave, g in _SINONIMOS_GENERO.items() if _dice(texto, clave)), "")


def _filtros_del_catalogo(pregunta: str, texto_original: str, listar: bool = False) -> dict | None:
    genero = _genero_de(pregunta)
    banda = next((b for b in _ORDEN_BANDAS if _dice(pregunta, f"riesgo {b}", f"riesgos {b}s")), "")
    gratis = _dice(pregunta, *_GRATIS)
    baratos = _dice(pregunta, *_BARATOS)
    caros = _dice(pregunta, *_CAROS)
    poco_tiempo = _dice(pregunta, "jugar poco", "partidas cortas", "poco tiempo", "entre semana", "rato corto")
    dificil = _dice(pregunta, "dificil", "dificiles", "retador", "retadores")
    facil = _dice(pregunta, "facil", "faciles", "relajado", "relajados", "tranquilo")
    nuevo = _dice(pregunta, "nuevo", "nuevos", "reciente", "recientes", "de este ano", "lo mas nuevo")
    # Tras «¿Quieres ver cuáles?», la misma búsqueda se repite para listarlos.
    cuantos = _dice(pregunta, "cuantos") and not listar
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
            f"Multijugador masivo, con {len(juegos)}: {nombres}. ¿Los ordeno por riesgo?",
            juegos=[j.appid for j in juegos[:5]],
        )
    if facil and not (genero or banda or gratis or precio_max):
        return _resultado(
            "No tengo un dato de qué tan fácil es un juego 🙈 Lo más cercano es el riesgo bajo: menos gente lo "
            "deja con una reseña negativa en las primeras 2 horas. ¿Te muestro esos?",
            oferta=_oferta("buscar", pregunta="Juegos con riesgo bajo"),
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
            f"de {nia.pesos_hablados(precio_max)} o menos" if precio_max else "",
            f"que se recomiendan con {HORAS_DE_SESION_CORTA} h o menos" if poco_tiempo else "",
            "donde lo que más se menciona es la dificultad" if dificil else "",
            "lanzados de 2024 en adelante" if nuevo else "",
        ) if parte
    )
    total = len(juegos)
    if not total:
        return _resultado(f"No hay {descripcion} en el catálogo 🙈 ¿Te muestro qué géneros hay en el catálogo?")
    if cuantos:
        return _resultado(
            f"En el catálogo hay {total} {descripcion}, de {len(catalogo.buscar())} 🎯 ¿Quieres ver cuáles?",
            oferta=_oferta("buscar", pregunta=texto_original),
        )
    mostrados = juegos[: herramientas.MAXIMO_RESULTADOS]
    if baratos:
        nombres = _lista([f"{j.nombre} ({_precio(j)})" for j in mostrados[:5]])
        cabeza = f"¡Los {descripcion} más baratos! 💸"
        cola = "¿Los ordeno por riesgo?"
        return _resultado(f"{cabeza} {nombres}. {cola}", juegos=[j.appid for j in mostrados[:5]])
    if caros:
        nombres = _lista([f"{j.nombre} ({_precio(j)})" for j in mostrados[:5]])
        return _resultado(f"¡Los {descripcion} más caros! 💰 {nombres}. ¿Los ordeno por riesgo?",
                          juegos=[j.appid for j in mostrados[:5]])
    # Si son todos gratis, ordenarlos por precio no dice nada.
    remate = "¿Te cuento de él?" if total == 1 else "¿Los ordeno por riesgo?" if gratis else "¿Los ordeno por precio?"
    # «¿Hay algo gratis?» se contesta con un sí antes de la lista.
    if total == 1:
        for plural, singular in (("juegos", "juego"), ("gratuitos", "gratuito"), ("se recomiendan", "se recomienda"),
                                 ("lanzados", "lanzado")):
            descripcion = descripcion.replace(plural, singular, 1)
    apertura = f"Sí, hay {total} {descripcion}" if _dice(pregunta, "hay") else f"Hay {total} {descripcion}"
    # Los nombres también cuentan palabras: con títulos largos se muestran menos, hasta
    # que la respuesta quepa en 60. Hasta uno: con uno o dos resultados el ciclo no corría.
    for cuantos_nombres in range(len(mostrados), 0, -1):
        visibles = mostrados[:cuantos_nombres]
        cuantos_texto = "" if total <= len(visibles) else f"Los primeros {len(visibles)}: "
        resto = f" Y {total - len(visibles)} más en Explorar." if total > len(visibles) else ""
        texto = f"{apertura} 🎮 {cuantos_texto}{_lista([j.nombre for j in visibles])}.{resto} {remate}"
        if nia.palabras(texto) <= 60:
            break
    return _resultado(texto, juegos=[j.appid for j in visibles])


# Con el apóstrofo tipográfico (’) en el nombre: sin él, «¿qué tal Don’t Starve Together?»
# se leía como «Don» y se daba por fuera del catálogo.
_FUERA = re.compile(r"(?:que tal|se parece a(?:l)?|parecido a(?:l)?)\s+(?:el |la |los |las )?([a-z0-9][a-z0-9 :'’.-]{2,40})")


def _con_ese_nombre(nombre: str) -> list[JuegoCatalogo]:
    """Los juegos cuyo nombre contiene lo escrito como palabras completas: «Apex» está en
    «Apex Legends™». Con menos de 4 letras no busca, como las variantes del nombre."""
    def comparable(texto: str) -> str:
        return nia._sin_marcas(_norm(texto)).replace("'", "").replace("’", "").strip()

    buscado = comparable(nombre)
    if len(buscado) < 4:
        return []
    patron = re.compile(rf"(?<!\w){re.escape(buscado)}(?!\w)")
    return [j for j in catalogo.buscar() if patron.search(comparable(j.nombre))]


# «¿Y Super Mario Odyssey?», «¿Tienen Zelda?»: un título suelto después de una muletilla.
# Solo cuenta si lo escrito parece un título (una palabra con mayúscula o un número), para no
# leer «¿y el más barato?» como un juego.
_FUERA_CORTO = re.compile(
    r"^(?:y|y que tal|tienen|tienes|hay|esta|que sabes de|que opinas de|hablame de)\s+(?:el |la |los |las )?"
    r"([a-z0-9][a-z0-9 :'’.-]{2,40})$"
)
_PARECE_TITULO = re.compile(r"(?:^|\s)[A-ZÁÉÍÓÚÑ0-9]")
# Lo que no va en un título y sí en una pregunta: deícticos («este juego», «ese»), «según»,
# palabras de pregunta y verbos. «¿Qué tal es este juego según las críticas?» no pregunta por un
# juego llamado «es este juego según las críticas», y «¿qué tal este?» no busca «este».
_NO_VA_EN_UN_TITULO = frozenset("""
    este esta estos estas ese esa esos esas eso esto aquel aquella juego juegos segun que cual cuales como cuanto
    cuanta cuantos donde cuando porque por es son era fue sera seria estan tiene tienen hay vale valen cuesta cuestan
    dice dicen opina opinan parece parecen gusta gustan sirve conviene recomiendas recomienda puedo puedes quiero
    quieres sabes crees se me te le lo
""".split())


def _parece_un_titulo(tramo: str) -> bool:
    palabras = re.findall(r"[a-z0-9ñ]+", _norm(tramo))
    return 0 < len(palabras) <= 6 and not any(p in _NO_VA_EN_UN_TITULO for p in palabras)


def _titulo_suelto(pregunta: str, original: str) -> str | None:
    limpia, limpio = pregunta.strip(" ¿?¡!."), original.strip(" ¿?¡!.")
    encontrado = _FUERA_CORTO.match(limpia)
    if not encontrado or len(limpia) != len(limpio):
        return None
    tramo = limpio[encontrado.start(1):encontrado.end(1)]
    return tramo if _PARECE_TITULO.search(tramo) and _parece_un_titulo(tramo) else None


def _fuera_del_catalogo(pregunta: str, original: str, datos: dict | None) -> dict | None:
    encontrado = _FUERA.search(pregunta)
    if encontrado:
        # Se cita como lo escribió la persona: quitar acentos no cambia el largo del texto,
        # así que el mismo tramo sirve en el original.
        tramo = original[encontrado.start(1):encontrado.end(1)] if len(original) == len(pregunta) else encontrado.group(1)
    else:
        tramo = _titulo_suelto(pregunta, original)
        if tramo is None:
            return None
    nombre = tramo.strip(" ?.!¿¡")
    if not nombre or not _parece_un_titulo(nombre) or _nombrados(nombre):
        return None
    # Una parte del nombre («Apex», «Battlefield») tampoco es estar fuera del catálogo.
    parecidos = _con_ese_nombre(nombre)
    if parecidos and datos is not None and _dice(pregunta, "se parece"):
        return None
    if len(parecidos) == 1:
        return _ficha_corta(parecidos[0])
    if parecidos:
        return _resultado(
            f"Con «{nombre}» hay {len(parecidos)} en el catálogo: {_lista([j.nombre for j in parecidos])} 🎮 "
            + nia.CIERRE_DE_COMPARAR,
            juegos=[j.appid for j in parecidos],
        )
    if datos is not None and _dice(pregunta, "se parece"):
        generos = _lista(datos["generos"]) if datos["generos"] else "sin géneros registrados"
        return _resultado(
            f"No tengo cómo comparar {datos['nombre']} con juegos de fuera del catálogo 🤔 Lo que sí sé: Steam lo "
            f"clasifica como {generos}. ¿Te cuento qué dicen sus reseñas?",
            oferta=_oferta("resenas", [datos["appid"]]),
        )
    return _resultado(
        f"No encuentro «{nombre}» en este catálogo de Steam, así que no tengo señal sobre él 🤔 "
        "¿Te muestro qué géneros hay en el catálogo?"
    )


# «¿De dónde salen estos datos?»: con modelo también va por reglas, para que las cifras sean
# las mismas en los dos modos (nia.cifras_habladas) y digan cuál es del catálogo y cuál del
# entrenamiento.
_DE_DONDE_SALEN = (
    "de donde salen", "de donde sacas", "de donde sacan", "de donde vienen", "de donde sale la informacion",
    "que datos usan", "que datos usas", "fuentes",
)


def pide_de_donde_salen(pregunta: str) -> bool:
    return _dice(_norm(pregunta), *_DE_DONDE_SALEN)


def _de_donde_salen(pregunta: str) -> dict | None:
    if not _dice(pregunta, *_DE_DONDE_SALEN, "metodologia", "que datos"):
        return None
    return _resultado(
        f"De Steam 📊 {nia.cifras_habladas()} La nota de la crítica es la de Metacritic que muestra Steam."
        " ¿Te cuento cómo se calcula el riesgo?"
    )


# «¿Cómo calculan el riesgo?»: corto y en llano, con lo mismo que dicen la línea fija de
# arriba del chat y la metodología. Con modelo también va por reglas: el modelo contestaba
# «¿Quieres conocer la metodología completa?» sin contestar.
_COMO_SE_CALCULA = (
    "como calculan", "como calculas", "como se calcula", "como sacan", "como obtienen", "como estiman",
    "como se estima", "como se obtiene el riesgo", "como funciona el riesgo", "que mide el riesgo",
)


def pide_como_se_calcula(pregunta: str) -> bool:
    return _dice(_norm(pregunta), *_COMO_SE_CALCULA)


def _como_se_calcula(pregunta: str) -> dict | None:
    if not pide_como_se_calcula(pregunta):
        return None
    juegos = scoring.ficha_del_modelo()["juegos_entrenamiento"] or "varios"
    return _resultado(
        f"Con datos del juego, no con tus gustos 🧮 Un modelo aprendió de {juegos} juegos cómo se relacionan"
        " la gratuidad, el precio, el descuento y la crítica con las reseñas de gente que no lo recomendó tras jugar"
        " menos de 2 horas. Bajo, medio y alto comparan su estimación con las del entrenamiento. ¿Te cuento de dónde salen"
        " los datos?"
    )


# «¿Qué opina la gente en los comentarios?»: lo que Nia lee y lo que no, con precisión. Los
# comentarios de NexPlay no los lee (herramientas.py no toca valoraciones.db); de Steam solo
# tiene las quejas de las reseñas negativas tempranas, contadas por tema.
_COMENTARIOS = (
    "comentario", "comentarios", "que opina la gente", "que opinan los demas", "que opinan los jugadores", "que dice la gente",
    "que opina la comunidad", "opiniones de la gente",
)


def pide_comentarios(pregunta: str) -> bool:
    return _dice(_norm(pregunta), *_COMENTARIOS)


def _comentarios(pregunta: str, original: str, appid: int | None) -> dict | None:
    if not _dice(pregunta, *_COMENTARIOS):
        return None
    no_los_leo = "Los comentarios de NexPlay no los leo; están en la ficha de cada juego 💬"
    nombrados = _nombrados(original)
    juego = nombrados[0] if nombrados else catalogo.obtener(appid) if appid is not None else None
    if juego is None:
        return _resultado(
            f"{no_los_leo} De las reseñas de Steam sí sé, contado por tema, de qué se queja quien no recomendó"
            " un juego tras jugar menos de 2 horas. ¿De qué juego te cuento?",
            pide_juego=True,
        )
    return _resultado(
        f"{no_los_leo} De {juego.nombre} sí tengo sus reseñas de Steam, contadas por tema: de qué se queja quien no"
        " lo recomendó tras jugar menos de 2 horas. ¿Te cuento qué dicen?",
        juegos=[juego.appid] if appid is None else [],
    )


# «¿Qué significa la señal?»: la misma frase fija de arriba del chat, ni una más.
_QUE_SIGNIFICA_LA_SENAL = (
    "que significa la senal", "que significa esa senal", "que es la senal", "que es esa senal",
    "que significa el riesgo", "que quiere decir el riesgo", "que significa ese riesgo", "que es una senal proxy",
    "senal proxy", "que significa arrepentimiento temprano", "que es el arrepentimiento temprano",
)


def pide_que_significa_la_senal(pregunta: str) -> bool:
    return _dice(_norm(pregunta), *_QUE_SIGNIFICA_LA_SENAL)


def _que_significa_la_senal(pregunta: str) -> dict | None:
    if not pide_que_significa_la_senal(pregunta):
        return None
    return _resultado(f"{nia.EXPLICACION_SENAL} 🔍 ¿Te cuento cómo se calcula el riesgo?")


# Con una ficha abierta, «este juego», «este», «ese» o «el juego» son el juego de la ficha:
# «¿qué tal este?» y «cuéntame de este juego» piden su resumen, no un juego llamado «este».
_PIDE_EL_RESUMEN = re.compile(r"^(?:y )?(?:que tal|que opinas|que me dices|que onda|hablame|cuentame|platicame|como es)\b")
_SOLO_SENALA_AL_JUEGO = frozenset("de del sobre con este ese esta esa el la juego es un poco algo".split())


def _resumen_del_abierto(pregunta: str, appid: int | None) -> dict | None:
    limpia = pregunta.strip(" ¿?¡!.")
    pide = _PIDE_EL_RESUMEN.match(limpia)
    if appid is None or pide is None:
        return None
    if any(p not in _SOLO_SENALA_AL_JUEGO for p in re.findall(r"[a-z0-9ñ]+", limpia[pide.end():])):
        return None
    # En su propia ficha, la tarjeta del juego sobra.
    return {**_ficha_corta(catalogo.obtener(appid)), "juegos": []}


def _del_juego(pregunta: str, datos: dict, appid: int, mensajes: list[MensajeChat]) -> dict | None:
    """Lo de siempre dentro de una ficha (precio, crítica, riesgo, motivos, géneros), con la
    voz nueva. Qué es la señal no se dice aquí: está fija arriba del chat."""
    nombre, banda = datos["nombre"], datos["banda"]
    if _dice(pregunta, "precio", "cuesta", "caro", "barato", "oferta", "descuento"):
        return _resultado(_sobre_el_precio(pregunta, datos, catalogo.obtener(appid)), juegos=[appid])
    if _dice(pregunta, "critica", "criticas", "critico", "criticos", "metacritic", "nota", "prensa", "calificacion"):
        return _resultado(f"En {nombre}, {nia._texto_critica(datos)} ⭐ ¿Quieres saber de qué se queja la gente?", juegos=[appid])
    if _dice(pregunta, "motivo", "motivos", "queja", "quejas", "problema", "problemas", "bug", "bugs", "rendimiento",
             "resenas", "que dicen"):
        return _resultado(f"{_sobre_las_quejas(datos)} ¿Te cuento por qué tiene riesgo {banda}?", juegos=[appid])
    if _dice(pregunta, "cuanto dura", "dura", "duracion", "cuantas horas", "horas tipicas", "cuanto tiempo", "largo"):
        # Steam no publica cuánto dura un juego: lo único que hay son las horas de quien lo
        # recomendó, y se dicen como lo que son.
        horas = datos.get("horas_tipicas")
        if horas is None:
            return _resultado(
                f"No hay duración oficial de {nombre}, y tampoco horas de quienes lo recomiendan: hay pocas reseñas"
                " positivas con horas jugadas ⏱️ ¿Te cuento qué dicen sus reseñas?",
                juegos=[appid],
            )
        return _resultado(
            f"No hay duración oficial de {nombre}; quienes lo recomiendan jugaron {horas:g} h (mediana) ⏱️ "
            "¿Te cuento su riesgo?",
            juegos=[appid],
        )
    if _dice(pregunta, "genero", "generos", "tipo de juego", "de que trata"):
        generos = _lista(datos["generos"]) if datos["generos"] else "sin géneros registrados"
        return _resultado(f"Steam clasifica {nombre} como {generos} 🎮 ¿Te cuento su riesgo?", juegos=[appid])
    if _dice(pregunta, "banda", "por que", "porque", "riesgo", "estimacion", "explicamelo", "explica"):
        # Los avisos van completos y el factor principal siempre; para caber en las 60
        # palabras se acorta, en este orden, el segundo factor y la pregunta de cierre.
        for cuantos, cierre in _VARIANTES_DEL_PORQUE:
            texto = f"{_porque_del_riesgo(datos, cuantos)} {cierre}"
            if nia.palabras(texto) <= nia.MAXIMO_PALABRAS:
                break
        return _resultado(texto, juegos=[appid])
    return None


_VARIANTES_DEL_PORQUE = (
    (2, "¿Te cuento qué dicen sus reseñas?"),
    (1, "¿Te cuento qué dicen sus reseñas?"),
    (1, "¿Sigo con sus motivos?"),
)

# «¿El precio influye?» se contesta con cuánto; «¿cuánto cuesta?», con el precio.
_INFLUYE = ("influye", "importa", "afecta", "pesa", "mueve", "sube", "tiene que ver", "cuenta el precio")


def _sobre_el_precio(pregunta: str, datos: dict, juego: JuegoCatalogo) -> str:
    """El precio y lo que hace en el modelo, que no es lo mismo que la gente se queje del
    precio en sus reseñas. Primero la respuesta: sí, un poco, casi no o no se sabe."""
    nombre = datos["nombre"]
    factor = nia.factor_del_precio(datos)
    if factor is not None and factor["imputado"]:
        return (f"No se sabe 💸 Steam no dio el precio de {nombre} y el modelo lo tomó como 0, lo que tiende a bajar"
                " su riesgo: tómalo con cuidado. ¿Te cuento qué dicen sus reseñas?")
    if factor is None or factor["etiqueta"] == "descuento actual del juego":
        dicho = f"{nombre} {_precio_hablado(juego)}" + (f" y {factor['idea']}" if factor else "")
        sujeto = "eso" if factor else "su precio"
    else:
        dicho, sujeto = f"{nombre} {factor['idea']}", "eso"
    if factor is None or factor["efecto"] is None:
        respuesta, modelo, pista = "Casi no", f"en el modelo {sujeto} {nia.CASI_NO_MUEVE}", ""
    else:
        respuesta, modelo = ("Un poco" if factor["debil"] else "Sí"), f"en el modelo eso {nia.efecto_hablado(factor)}"
        principal = next((f for f in datos["factores"] if f["efecto"] is not None), None)
        if not factor["debil"]:
            pista = f" Es {factor['pista']}."
        elif principal is not None and principal is not factor:
            pista = f" Pero es {factor['pista']}, y lo que más pesa es que {principal['idea']}, que lo {principal['efecto']}."
        else:
            pista = f" Pero es {factor['pista']}."
    for con_pista in (pista, pista.split(", y lo que más pesa")[0].rstrip(".") + "." if pista else ""):
        if _dice(pregunta, *_INFLUYE):
            texto = f"{respuesta} 💸 {dicho}, y {modelo}.{con_pista} ¿Te cuento qué dicen sus reseñas?"
        else:
            texto = f"{dicho}; {modelo} 💸{con_pista} ¿Te cuento qué dicen sus reseñas?"
        # Con nombres y cifras largas no cabe en 60 palabras: se quita lo que más pesa.
        if nia.palabras(texto) <= nia.MAXIMO_PALABRAS:
            break
    return texto


def _sobre_las_quejas(datos: dict) -> str:
    """De qué se queja la gente, en conteos: con 5 reseñas, «100%» suena más firme de lo que es."""
    nombre, n = datos["nombre"], datos["n_casos"]
    conteos = nia.quejas_en_conteos(datos)
    if not conteos:
        if n == 0:
            return f"Nada todavía 🔍 {nombre} no tiene reseñas negativas tempranas en los datos."
        cuantas = "una sola reseña negativa temprana" if n == 1 else f"solo {n} reseñas negativas tempranas"
        return f"Muy poco 🔍 De {nombre} hay {cuantas}: no alcanza para saber de qué se queja la gente."
    total = datos["clasificadas"]
    principal, primero = conteos[0]
    empatados = [m for m, c in conteos if c == primero]
    if total == 1:
        apertura, cuerpo = f"De {principal}", f"La única reseña negativa temprana de {nombre} que dice por qué habla de {principal}."
    elif primero == total:
        otros = "".join(f", y {c} también de {m}" for m, c in conteos[1:2])
        apertura = f"De {principal}"
        cuerpo = f"Las {total} reseñas negativas tempranas de {nombre} que dicen por qué hablan de {principal}{otros}."
    else:
        apertura = f"De {_lista(empatados[:3])}" if len(empatados) > 1 else f"Sobre todo, de {principal}"
        # La cifra primero: si el resumen se queda con la primera cláusula, se queda con ella.
        otros = [f"{c} de {m}" for m, c in conteos[1:3]]
        cuerpo = (f"{primero} de las {total} reseñas negativas tempranas de {nombre} que dicen por qué"
                  f" {'habla' if primero == 1 else 'hablan'} de {principal}"
                  + (f", {_lista(otros)}" if otros else "") + ".")
    cautela = " Son pocas, tómalo con cautela." if total < 10 else ""
    return f"{apertura} 🔍 {cuerpo}{cautela}"


def _porque_del_riesgo(datos: dict, cuantos: int) -> str:
    """El riesgo y su porqué, en el orden del modelo: primero el factor que más aporta, con
    qué tan firme es, y después los avisos de la estimación, dichos en llano. Lo que está en
    la banda neutral no se da como razón, y el emoji va con el nivel."""
    nombre, banda = datos["nombre"], datos["banda"]
    emoji = nia.EMOJI_DEL_NIVEL[banda]
    razones = [f for f in datos["factores"] if f["efecto"] is not None][:cuantos]
    avisos = list(datos["avisos_hablados"])
    if not razones:
        return (f"{nombre} tiene riesgo {banda} {emoji} Ninguno de sus datos se aleja mucho de lo típico del catálogo."
                + "".join(f" {_mayuscula(a)}." for a in avisos))
    principal = razones[0]
    if principal["imputado"]:
        # El precio que falta es la razón y el aviso a la vez: se dice una sola vez.
        texto = f"{nombre} tiene riesgo {banda}, pero tómalo con cuidado 🤔 {_mayuscula(nia._AVISOS_HABLADOS['precio_imputado'])}."
        avisos.remove(nia._AVISOS_HABLADOS["precio_imputado"])
    elif (banda == "alto" and principal["efecto"] == "sube") or (banda == "bajo" and principal["efecto"] == "baja"):
        firme = f", aunque es {principal['pista']}" if principal["debil"] else f", {principal['pista']}"
        texto = f"{nombre} tiene riesgo {banda} sobre todo porque {principal['idea']}{firme} {emoji}"
    else:
        texto = (f"{nombre} tiene riesgo {banda} {emoji} Lo que más pesa es que {principal['idea']}, y eso"
                 f" {nia.efecto_hablado(principal)}; es {principal['pista']}.")
    dichos = [principal]
    for otro in razones[1:]:
        if otro["imputado"]:
            # El precio que falta lo dice su aviso, que va al final y completo.
            continue
        # «También» une dos factores que empujan hacia el mismo lado; si empuja al contrario,
        # «en cambio». «Otra pista confiable» solo si ya se dijo una confiable.
        conector = "También lo" if otro["efecto"] == dichos[-1]["efecto"] else "En cambio, lo"
        if otro["debil"]:
            firme = f", aunque es {nia.PISTA_DEBIL}"
        elif any(not dicho["debil"] for dicho in dichos):
            firme = ", otra pista confiable"
        else:
            firme = f", {nia.PISTA_SOLIDA}"
        texto += f" {conector} {otro['efecto']} que {otro['idea']}{firme}."
        dichos.append(otro)
    return texto + "".join(f" {_mayuscula(a)}." for a in avisos)


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


# ── Ofertas: toda pregunta de cierre se puede cumplir ─────────────────────────
# La pregunta con que cierra Nia viaja como dato (intención y juegos) y vuelve en el
# historial; «sí», «cuéntame» o «dale» la cumplen aquí, también con modelo. Así no vuelve a
# pasar «¿Te cuento sus otros puntos débiles?» → «sí» → «Eso no lo sé».

# Cada cierre y lo que ofrece. Un cierre que no esté aquí ni lleve su oferta explícita no se
# puede cumplir: calidad/verificar_nia.py lo marca.
_CIERRES = (
    (r"te cuento (?:por que .*tiene (?:riesgo \w+|ese riesgo)|su riesgo)|empiezo por su riesgo", "riesgo"),
    (r"te cuento (?:que (?:mas )?dicen(?: sus resenas| las resenas de .+)?|sus resenas)|sigo con sus motivos"
     r"|quieres saber de que se queja la gente", "resenas"),
    (r"te cuento de que se queja la gente en cada uno", "resenas_de_varios"),
    (r"los ordeno por (precio|riesgo|nota|critica)", "ordenar"),
    (r"que pesa mas para ti(?:: el precio, el riesgo o la critica)?|por precio, por riesgo o por critica", "ordenar"),
    (r"te muestro que generos hay(?: en el catalogo)?(?: mientras)?", "generos"),
    (r"te cuento como se calcula el riesgo", "como_se_calcula"),
    (r"te cuento de donde salen los datos", "de_donde_salen"),
    (r"(?:toma un minuto, )?lo armamos", "crear_perfil"),
    (r"de que juego (?:te cuento|hablamos)|cuales comparo", "elegir_juego"),
    (r"te lo resumo", "resumen"),
    (r"te cuento de (?:el|ella|.+)", "ficha"),
    (r"vemos otro juego o seguimos con este|buscas algo en particular o ya tienes un juego en mente"
     r"|por donde empezamos(?:: un juego o el catalogo)?|seguimos(?: con alguno)?|que quieres saber"
     r"|te ayudo con algun juego del catalogo|por cual empiezo|que se te antoja|por cual empezamos", "aclarar"),
)
_DE_UN_SOLO_JUEGO = ("riesgo", "resenas", "ficha")
_CRITERIOS_DICHOS = {"precio": "precio", "critica": "nota", "nota": "nota", "riesgo": "riesgo"}


def _pregunta_de_cierre(texto: str) -> str:
    """La pregunta con que cierra el texto, desde su último «¿», normalizada y sin signos ni
    emojis. «Toma un minuto, ¿lo armamos?» cierra con «lo armamos»."""
    limpio = nia.EMOJI.sub("", texto).rstrip()
    if not limpio.endswith("?"):
        return ""
    inicio = limpio.rfind("¿")
    pregunta = limpio[inicio:] if inicio >= 0 else nia._oraciones(limpio)[-1]
    return _norm(pregunta).replace("¿", "").replace("¡", "").strip(" ?!.")


def oferta_del_cierre(texto: str, juegos: list[int], appid: int | None) -> dict | None:
    """Lo que ofrece la pregunta con que cierra un texto, con sus juegos: los de sus tarjetas o
    el de la ficha. None si el cierre no es uno que las reglas sepan cumplir."""
    cierre = _pregunta_de_cierre(texto)
    for patron, intencion in _CIERRES:
        encontrado = re.fullmatch(patron, cierre)
        if not encontrado:
            continue
        criterio = _CRITERIOS_DICHOS.get(encontrado.group(1)) if encontrado.groups() and encontrado.group(1) else None
        if intencion == "ficha" and cierre not in ("te cuento de el", "te cuento de ella"):
            nombrados = _nombrados(cierre)
            if len(nombrados) != 1:
                return None
            return _oferta("ficha", [nombrados[0].appid])
        if intencion in _DE_UN_SOLO_JUEGO:
            uno = juegos[:1] if len(juegos) == 1 else [appid] if appid is not None else []
            return _oferta(intencion, uno) if uno else None
        return _oferta(intencion, juegos, criterio)
    return None


_AFIRMATIVAS = frozenset(
    "si sii siii sip simon va vale dale ok okay okey claro que sale andale orale bueno perfecto de acuerdo adelante"
    " por favor porfa porfavor cuentame cuentamelo cuentamelos platicame explicame explicamelo muestramelos"
    " muestramelo muestrame hazlo me interesa obvio ya venga a ver pues mas sobre eso y lo los tambien yes please"
    .split()
)
# Un sí fuerte, con sus errores de dedo («sii», «sip», «dalee», «okis»): lo que sigue puede ser
# cualquier cosa que no pida otra cosa («si te me lo acabas de preguntar», «dale pues»).
_SI_FUERTE = re.compile(
    r"^(?:s+i+p?|s+e+p|z+i+|si+m|simon|va+|vale|da+le+|ok+(?:ay|ey|is?)?|okey|claro|sale|andale|orale|bueno"
    r"|perfecto|adelante|porfa(?:vor)?|obvio|venga|yes|yep)$"
)
# Arranques que también abren pedidos («cuéntame de este juego», «me gusta…», «de esos…»): solo
# son un sí si todo el mensaje son palabras de afirmación («cuéntame más sobre eso»,
# «explícamelo», «de acuerdo», «me interesa»).
_ARRANQUES = frozenset(
    "de por me a cuentame cuentamelo cuentamelos platicame explicame explicamelo muestramelos muestramelo"
    " muestrame hazlo".split()
)
# Lo que convierte un «sí, …» en otra pregunta: un tema concreto («sí, ¿cuánto cuesta?»).
_PIDE_OTRA_COSA = frozenset("""
    precio precios cuesta cuestan cuanto critica criticas nota metacritic resena resenas motivos quejas riesgo
    genero generos dura duracion horas compara comparar gratis barato baratos caro caros comentarios perfil
    rendimiento bugs dificultad controles historia graficos multijugador recomiendas
""".split())


def es_afirmacion(pregunta: str) -> bool:
    """Un sí a lo que Nia acaba de ofrecer, sin pedir otra cosa: «sí», «sí, explícamelo», «va»,
    «dale pues», «si cuentame mas sobre eso», «si te me lo acabas de preguntar», «sii». «Sí,
    ¿cuánto cuesta?» o «sí, ¿y la crítica?» piden otra cosa y no cuentan."""
    palabras = re.findall(r"[a-zñ]+", _norm(pregunta))
    # Una pregunta detrás del sí es otra pregunta: «si, ¿por qué?». «¿Va?» sola sí cuenta.
    if not 0 < len(palabras) <= 12 or ("?" in pregunta and len(palabras) > 1):
        return False
    if all(p in _AFIRMATIVAS for p in palabras) and (_SI_FUERTE.match(palabras[0]) or palabras[0] in _ARRANQUES):
        return True
    return bool(_SI_FUERTE.match(palabras[0])) and not any(p in _PIDE_OTRA_COSA for p in palabras) and not _nombrados(pregunta)


def _oferta_previa(mensajes: list[MensajeChat], appid: int | None = None) -> dict | None:
    """La oferta de la respuesta inmediata anterior de Nia: la que viene como dato o, si no vino,
    la que se lee en su pregunta de cierre."""
    anterior = _respuesta_anterior(mensajes)
    if anterior is None:
        return None
    if anterior.oferta is not None:
        return anterior.oferta.model_dump()
    return oferta_del_cierre(anterior.contenido, anterior.juegos, appid)


def _criterio_dicho(pregunta: str) -> str | None:
    """«el precio», «por riesgo», «la crítica»: la respuesta a «¿por cuál los ordeno?»."""
    if len(pregunta.split()) > 6:
        return None
    for palabra, criterio in (("precio", "precio"), ("barato", "precio"), ("riesgo", "riesgo"),
                              ("critica", "nota"), ("nota", "nota"), ("metacritic", "nota")):
        if _dice(pregunta, palabra):
            return criterio
    return None


def responde_al_seguimiento(pregunta: str, mensajes: list[MensajeChat], appid: int | None = None) -> bool:
    """Un sí a la oferta anterior, o el criterio que pidió: se cumple con reglas aunque haya
    modelo, porque lo ofrecido tiene que poder hacerse. Sin oferta que cumplir, no es seguro."""
    oferta = _oferta_previa(mensajes, appid)
    if oferta is None:
        return False
    return es_afirmacion(pregunta) or (oferta["intencion"] == "ordenar" and bool(_criterio_dicho(_norm(pregunta))))


def _seguimiento(pregunta: str, datos: dict | None, appid: int | None, mensajes: list[MensajeChat],
                 sugerencias: list[SugerenciaNia]) -> dict | None:
    oferta = _oferta_previa(mensajes, appid)
    if es_afirmacion(pregunta):
        if oferta is None:
            # Un sí sin oferta guardada responde al saludo: en la ficha, «¿Te explico por qué
            # tiene ese riesgo?»; en el catálogo, se pregunta qué busca.
            oferta = _oferta("riesgo", [appid]) if appid is not None else _oferta("aclarar")
        return _cumplir(oferta, datos, appid, mensajes, sugerencias)
    if oferta and oferta["intencion"] == "ordenar" and (criterio := _criterio_dicho(pregunta)):
        return _ordenar(oferta["juegos"], criterio)
    return None


def _cumplir(oferta: dict, datos: dict | None, appid: int | None, mensajes: list[MensajeChat],
             sugerencias: list[SugerenciaNia]) -> dict:
    intencion = oferta["intencion"]
    juegos = [a for a in oferta.get("juegos") or [] if catalogo.obtener(a) is not None]
    juego = juegos[0] if juegos else appid
    if intencion in _DE_UN_SOLO_JUEGO and juego is None:
        return _pedir_juego()
    if intencion == "riesgo":
        return _del_juego_ofrecido(juego, "¿Por qué tiene ese riesgo?", appid, mensajes)
    if intencion == "resenas":
        return _del_juego_ofrecido(juego, "¿Qué dicen las reseñas?", appid, mensajes)
    if intencion == "ficha":
        return _ficha_corta(catalogo.obtener(juego))
    if intencion == "resenas_de_varios":
        if len(juegos) == 1:
            return _del_juego_ofrecido(juegos[0], "¿Qué dicen las reseñas?", appid, mensajes)
        return _quejas_de_varios(juegos) if juegos else _pedir_juego()
    if intencion == "ordenar":
        return _ordenar(juegos, oferta.get("criterio"))
    if intencion == "buscar":
        pregunta = oferta.get("pregunta") or ""
        return _filtros_del_catalogo(_norm(pregunta), pregunta, listar=True) or _aclarar(datos)
    if intencion == "generos":
        return _generos_del_catalogo()
    if intencion == "como_se_calcula":
        return _como_se_calcula("como se calcula")
    if intencion == "de_donde_salen":
        return _de_donde_salen("de donde salen")
    if intencion == "crear_perfil":
        return _resultado(
            "¡Va! 🎮 Abajo está el botón para crear tu perfil: son unas preguntas sobre cómo juegas y toma un"
            " minuto. ¿Te muestro qué géneros hay en el catálogo mientras?",
            pide_perfil=True,
        )
    if intencion == "elegir_juego":
        return _pedir_juego()
    if intencion == "resumen":
        return _resumen("resume", mensajes) or _aclarar(datos)
    return _aclarar(datos)


def _del_juego_ofrecido(juego: int, pregunta: str, appid: int | None, mensajes: list[MensajeChat]) -> dict:
    """Lo ofrecido de un juego, como si lo hubieran preguntado; fuera de su ficha, con tarjeta."""
    hilo = [*mensajes[:-1], MensajeChat(rol="usuario", contenido=pregunta)]
    resultado = _del_juego(_norm(pregunta), nia.contexto(juego), juego, hilo)
    if juego != appid:
        resultado["juegos"] = [juego]
    return resultado


def _aclarar(datos: dict | None) -> dict:
    """Un sí a una pregunta abierta («¿Por dónde empezamos?»): se ofrece algo concreto."""
    if datos is not None:
        return _resultado(
            f"Va 🙂 De {datos['nombre']} te cuento su riesgo, sus reseñas, la crítica o el precio. ¿Empiezo por su riesgo?"
        )
    return _resultado(
        "Va 🙂 Puedo filtrar el catálogo por género, precio o riesgo, o contarte de un juego. ¿Te muestro qué"
        " géneros hay en el catálogo?"
    )


def _quejas_de_varios(appids: list[int]) -> dict:
    """De qué se queja la gente en cada uno, en conteos y en una frase por juego."""
    partes, pocas = [], False
    juegos = [catalogo.obtener(a) for a in appids[:3]]
    for juego in juegos:
        datos = nia.contexto(juego.appid)
        conteos, total = nia.quejas_en_conteos(datos), datos["clasificadas"]
        if not conteos:
            partes.append(f"de {juego.nombre} no hay reseñas negativas tempranas que digan por qué")
            continue
        pocas |= total < 10
        motivo, cuantas = conteos[0]
        if total == 1:
            partes.append(f"en {juego.nombre}, la única que dice por qué habla de {motivo}")
        else:
            partes.append(f"en {juego.nombre}, {cuantas} de {total} {'habla' if cuantas == 1 else 'hablan'} de {motivo}")
    cautela = " Son pocas, tómalo con cautela." if pocas else ""
    return _resultado(
        f"Esto dicen sus reseñas negativas tempranas 🔍 {_mayuscula('; '.join(partes))}.{cautela} ¿Los ordeno por riesgo?",
        juegos=[j.appid for j in juegos],
    )


_ORDENES = {
    "precio": ("Del más barato al más caro 💸", "Los más baratos del catálogo 💸"),
    "riesgo": ("De menor a mayor riesgo 📊", "Los de menor riesgo del catálogo 📊"),
    "nota": ("De mejor a peor nota de la crítica ⭐", "Los de mejor nota de la crítica ⭐"),
}


def _ordenar(appids: list[int], criterio: str | None) -> dict:
    """Los juegos ofrecidos (o el catálogo, si no hay) en el orden que pidieron. Ordenar no es
    elegir: el primero no se corona, y el cierre ofrece sus reseñas."""
    juegos = [j for j in (catalogo.obtener(a) for a in appids) if j is not None]
    if criterio is None:
        return _resultado("Dime cuál y los ordeno 📊 ¿Por precio, por riesgo o por crítica?",
                          oferta=_oferta("ordenar", [j.appid for j in juegos]))
    del_catalogo = not juegos
    juegos = juegos or catalogo.buscar()
    if criterio == "precio":
        juegos = sorted(juegos, key=lambda j: (0 if j.es_gratis else 1, j.precio_final if j.precio_final is not None else float("inf")))
        nombre = lambda j: f"{j.nombre} ({_precio(j)})"
    elif criterio == "nota":
        juegos = sorted(juegos, key=lambda j: -(j.metacritic if j.metacritic is not None else -1))
        nombre = lambda j: f"{j.nombre} ({j.metacritic if j.metacritic is not None else 'sin nota'})"
    else:
        juegos = sorted(juegos, key=lambda j: j.riesgo)
        nombre = lambda j: j.nombre
    entre, catalogo_entero = _ORDENES[criterio]
    for cuantos in range(min(5, len(juegos)), 0, -1):
        visibles = juegos[:cuantos]
        cabeza = catalogo_entero if del_catalogo else entre
        texto = (f"{cabeza} {_lista([nombre(j) for j in visibles])}."
                 f" ¿Te cuento qué dicen las reseñas de {visibles[0].nombre}?")
        if nia.palabras(texto) <= nia.MAXIMO_PALABRAS:
            break
    return _resultado(texto, juegos=[j.appid for j in visibles],
                      oferta=_oferta("resenas", [visibles[0].appid]))


def _generos_del_catalogo() -> dict:
    conteo = Counter(g for j in catalogo.buscar() for g in j.generos)
    generos = [g for g, _ in conteo.most_common()]
    for cuantos in range(len(generos), 0, -1):
        visibles = generos[:cuantos]
        resto = f" y {len(generos) - cuantos} más" if cuantos < len(generos) else ""
        texto = (f"Los géneros del catálogo, del más común al menos 🎮 {', '.join(visibles)}{resto}."
                 f" ¿Te muestro los juegos de {generos[0]}?")
        if nia.palabras(texto) <= nia.MAXIMO_PALABRAS:
            break
    return _resultado(texto, oferta=_oferta("buscar", pregunta=f"Juegos de {generos[0]}"))


def responder(
    datos: dict | None,
    appid: int | None,
    mensajes: list[MensajeChat],
    sugerencias: list[SugerenciaNia],
    generos: list[str] | None = None,
) -> dict:
    """La respuesta del modo demostración: texto, juegos para tarjetas, sugerencias del
    perfil y si hay que pedir el juego o el perfil. Los géneros declarados solo sirven para
    «¿encaja conmigo?»."""
    original = next((m.contenido for m in reversed(mensajes) if m.rol == "usuario"), "")
    pregunta = _norm(original)

    intentos = (
        lambda: _datos_personales(original),
        lambda: _instrucciones(pregunta),
        # Antes que todo lo demás: un «sí» cumple lo que Nia ofreció en su respuesta anterior.
        lambda: _seguimiento(pregunta, datos, appid, mensajes, sugerencias),
        lambda: _saludo_o_gracias(pregunta, datos),
        lambda: _resumen(pregunta, mensajes),
        lambda: _que_significa_la_senal(pregunta),
        lambda: _como_se_calcula(pregunta),
        lambda: _comentarios(pregunta, original, appid),
        # Antes que «¿encaja conmigo?»: «¿es para mí si me importa el rendimiento?» es el aspecto.
        lambda: _aspecto(pregunta, original, appid),
        # Antes que las sugerencias: con un juego, «¿es para mí?» es medir ese juego.
        lambda: _encaja(pregunta, original, appid, mensajes, generos),
        lambda: _el_mejor(pregunta),
        lambda: _sugerencias(pregunta, sugerencias),
        lambda: _compara(pregunta, appid),
        lambda: _vale_la_pena(pregunta, datos, appid, mensajes, sugerencias),
        lambda: _de_esos(pregunta, mensajes),
        lambda: _pedir_juego() if necesita_juego(original, mensajes, appid) else None,
        lambda: _de_donde_salen(pregunta),
        lambda: _del_juego(pregunta, datos, appid, mensajes) if datos is not None and appid is not None else None,
        lambda: _resumen_del_abierto(pregunta, appid) if datos is not None else None,
        lambda: None if datos is not None else _nombrado_sin_ficha(original, mensajes),
        lambda: None if datos is not None else _del_juego_del_hilo(pregunta, original, mensajes),
        lambda: _filtros_del_catalogo(pregunta, original),
        lambda: _fuera_del_catalogo(pregunta, original, datos),
        lambda: _formato(pregunta),
    )
    resultado = next((r for r in (intento() for intento in intentos) if r is not None), None) or _no_se(datos)

    # Con cualquier respuesta anterior, no solo la última: un «sí» tras otro alterna riesgo y
    # reseñas, y al tercero repetía la primera.
    if not resultado["pide_juego"] and nia.pulir(resultado["texto"]) in _respuestas_previas(mensajes):
        resultado = _resultado("Ya te lo conté arriba 🙂 ¿Te lo resumo?")
    if resultado["oferta"] is None:
        resultado["oferta"] = oferta_del_cierre(resultado["texto"], resultado["juegos"] or resultado["sugerencias"], appid)
    return resultado


def es_fuera_de_tema(
    datos: dict | None,
    appid: int | None,
    mensajes: list[MensajeChat],
    sugerencias: list[SugerenciaNia],
    generos: list[str] | None = None,
) -> bool:
    """Si la pregunta no encaja con nada del catálogo. Con IA también se decide aquí, con
    las mismas reglas del modo demostración: no llama a ningún modelo."""
    return bool(responder(datos, appid, mensajes, sugerencias, generos).get("fuera_de_tema"))


# Temas ajenos que se reconocen sin dudar. Con modelo, a media conversación solo estos se
# contestan por reglas: un mensaje sin palabras de juegos después de otra respuesta suele ser un
# seguimiento («¿Y eso es mucho?») y va al modelo con el historial.
_TEMA_AJENO = ("capital de", "mundial", "presidente", "receta", "clima", "horoscopo", "chiste", "tarea", "traduce",
               "traducir", "matematicas", "ecuacion", "futbol", "pelicula", "noticias", "elecciones")


def es_tema_ajeno_seguro(
    pregunta: str,
    datos: dict | None,
    appid: int | None,
    mensajes: list[MensajeChat],
    sugerencias: list[SugerenciaNia],
    generos: list[str] | None = None,
) -> bool:
    """Datos personales e instrucciones, siempre. Un tema sin relación con los juegos, solo si
    abre la conversación o se nombra sin duda; si no, puede ser un seguimiento."""
    if tiene_datos_personales(pregunta) or _dice(_norm(pregunta), *_INSTRUCCIONES):
        return True
    if not sin_relacion_con_juegos(pregunta) or not es_fuera_de_tema(datos, appid, mensajes, sugerencias, generos):
        return False
    abre_la_conversacion = not any(m.rol == "usuario" for m in mensajes[:-1])
    return abre_la_conversacion or _dice(_norm(pregunta), *_TEMA_AJENO)


def fuera_del_catalogo(original: str, datos: dict | None) -> dict | None:
    """«¿Qué tal Zelda?», «¿se parece a Mario?»: la respuesta de un juego que no está."""
    return _fuera_del_catalogo(_norm(original), original, datos)


def _nombrado_sin_ficha(original: str, mensajes: list[MensajeChat]) -> dict | None:
    juegos = _nombrados(original)
    if len(juegos) != 1:
        return None
    juego = juegos[0]
    return _del_juego(_norm(original), nia.contexto(juego.appid), juego.appid, mensajes) or _ficha_corta(juego)


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
        f"{nombre} tiene riesgo {banda} {nia.EMOJI_DEL_NIVEL[banda]} {frase[0].upper()}{frase[1:]}{detalle}. "
        "¿Te cuento más?"
    )
    return {
        "appid": appid,
        "nombre": nombre,
        "nivel": banda,
        "pregunta": f"¿Qué opinas de {nombre}?",
        "respuesta": nia.pulir(respuesta),
    }
