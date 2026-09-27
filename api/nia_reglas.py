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

from . import catalogo, nia, panorama
from . import nia_herramientas as herramientas
from .schemas import JuegoCatalogo, MensajeChat, SugerenciaNia

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


def _primera_oracion(texto: str) -> str:
    sin_emojis = nia.EMOJI.sub("", texto).strip()
    oracion = re.split(r"(?<=[.!?])\s+", sin_emojis, maxsplit=1)[0]
    return oracion.strip("¡!¿ ").rstrip(".")


def _resultado(texto: str, **extra) -> dict:
    return {"texto": texto, "juegos": [], "sugerencias": [], "pide_juego": False, "pide_perfil": False, **extra}


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


# Al juntar oraciones, la de en medio empieza en minúscula; los nombres propios no.
_INICIOS_COMUNES = {"de", "del", "en", "los", "las", "el", "la", "hay", "con", "salen", "todos", "solo", "decidir",
                    "elegir", "no", "aun", "va", "para", "eso", "esa", "ese", "steam"}


def _en_minuscula(oracion: str) -> str:
    primera = oracion.split(" ", 1)[0]
    return oracion[0].lower() + oracion[1:] if _norm(primera).strip(",") in _INICIOS_COMUNES - {"steam"} else oracion


def _resumen(pregunta: str, mensajes: list[MensajeChat]) -> dict | None:
    if not _dice(pregunta, "resume", "resumen", "resumir", "resumelo", "resumeme", "en corto", "lo que dijiste",
                 "lo que me dijiste", "mas corto", "menos texto"):
        return None
    # Un resumen anterior no se resume otra vez: repetiría "Va, en corto" dentro de sí.
    previas = [
        _primera_oracion(p) for p in _respuestas_previas(mensajes) if not p.startswith(("Va, en corto", "Más corto"))
    ]
    previas = [p for p in previas if len(p.split()) >= 3]
    if not previas:
        return _resultado("Aún no te he contado nada 🙂 ¿Por dónde empezamos: un juego o el catálogo?")
    # "Más corto" pide menos que el resumen de antes: la mitad de palabras, y lo último.
    corto = _dice(pregunta, "mas corto", "menos texto", "mas breve", "lo mas que puedas", "mas resumido")
    tope = 22 if corto else 40
    # Las más recientes, hasta el tope: el resumen no puede ser más largo que lo resumido.
    elegidas: list[str] = []
    for oracion in reversed(previas):
        if sum(len(o.split()) for o in elegidas) + len(oracion.split()) > tope:
            break
        elegidas.insert(0, oracion)
    elegidas = elegidas or [previas[-1].split(";")[0]]
    cuerpo = "; ".join(_en_minuscula(o) if i else o for i, o in enumerate(elegidas))
    if corto:
        return _resultado(f"Más corto ✍️ {cuerpo[0].upper()}{cuerpo[1:]}. ¿Seguimos?")
    return _resultado(f"Va, en corto ✍️ {cuerpo}. ¿Seguimos con alguno?")


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
    elif ref["metacritic_promedio"] and juego.metacritic >= ref["metacritic_promedio"]:
        a_favor.append(f"su Metacritic ({juego.metacritic}) está arriba del promedio")
    else:
        en_contra.append(f"su Metacritic ({juego.metacritic}) está abajo del promedio")
    banda = juego.banda_riesgo.value
    if banda != "medio":
        (a_favor if banda == "bajo" else en_contra).append(f"su riesgo es {banda}")
    if juego.es_gratis:
        a_favor.append("es gratis")
    elif juego.precio_final and ref["precio_promedio"] and juego.precio_final <= ref["precio_promedio"]:
        a_favor.append("cuesta menos que el promedio")
    elif juego.precio_final:
        en_contra.append("cuesta más que el promedio")
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
    """La pregunta es de un juego, no hay juego fijado y el hilo reciente no nombra ninguno."""
    if appid is not None:
        return False
    texto = _norm(pregunta)
    if not _dice(texto, *_DE_UN_JUEGO) or _nombrados(pregunta):
        return False
    recientes = " ".join(m.contenido for m in mensajes[-5:-1])
    return not _nombrados(recientes)


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
        resto = " El resto está en Explorar con esos filtros." if total > len(visibles) else ""
        texto = f"¡Hay {total} {descripcion}! 🎮 {cuantos_texto}: {_lista([j.nombre for j in visibles])}.{resto} {remate}"
        if nia.palabras(texto) <= 60:
            break
    return _resultado(texto, juegos=[j.appid for j in visibles])


_FUERA = re.compile(r"(?:que tal|se parece a(?:l)?|parecido a(?:l)?)\s+(?:el |la |los |las )?([a-z0-9][a-z0-9 :'.-]{2,40})")


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
        base = f"{nombre} es gratis 🎁" if juego.es_gratis else f"{nombre} cuesta {_precio(juego)} 💸"
        return _resultado(f"{base}{(' ' + factor) if factor else ''} ¿Te cuento qué dicen sus reseñas?", juegos=[appid])
    if _dice(pregunta, "critica", "metacritic", "nota", "prensa"):
        return _resultado(f"En {nombre}, {nia._texto_critica(datos)} ⭐ ¿Quieres saber de qué se queja la gente?", juegos=[appid])
    if _dice(pregunta, "motivo", "motivos", "queja", "quejas", "problema", "problemas", "bug", "bugs", "rendimiento",
             "resenas", "que dicen"):
        return _resultado(f"En {nombre}, {nia._texto_motivos(datos)} 🔍 ¿Te cuento por qué tiene riesgo {banda}?", juegos=[appid])
    if _dice(pregunta, "genero", "generos", "tipo de juego", "de que trata"):
        generos = _lista(datos["generos"]) if datos["generos"] else "sin géneros registrados"
        return _resultado(f"Steam clasifica {nombre} como {generos} 🎮 ¿Te cuento su riesgo?", juegos=[appid])
    if _dice(pregunta, "banda", "por que", "porque", "riesgo", "estimacion", "explicamelo", "explica"):
        factores = datos["factores"][:2]
        if factores:
            lectura = _lista([f"{f['lectura'][0].lower()}{f['lectura'][1:]} (lo {f['efecto']})" for f in factores])
            porque = f" Lo que más lo mueve: {lectura}."
        else:
            porque = " El modelo no destaca ninguna variable de este juego."
        return _resultado(f"{nombre} tiene riesgo {banda} 🙂{porque}{senal} ¿Te cuento qué dicen esas reseñas?", juegos=[appid])
    return None


def _no_se(datos: dict | None) -> dict:
    if datos is not None:
        return _resultado(
            f"Eso no lo sé con los datos que tengo 🙈 De {datos['nombre']} te cuento su riesgo, sus reseñas, la "
            "crítica o el precio. ¿Por cuál empiezo?"
        )
    return _resultado(
        "Eso no lo sé con estos datos 🙈 Puedo filtrar el catálogo por género, precio o riesgo, o contarte de un "
        "juego. ¿Qué se te antoja?"
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
        lambda: _saludo_o_gracias(pregunta, datos),
        lambda: _resumen(pregunta, mensajes),
        lambda: _sugerencias(pregunta, sugerencias),
        lambda: _compara(pregunta, appid),
        lambda: _vale_la_pena(pregunta, datos, appid, mensajes),
        lambda: _de_esos(pregunta, mensajes),
        lambda: _pedir_juego() if necesita_juego(original, mensajes, appid) else None,
        lambda: _de_donde_salen(pregunta),
        lambda: _del_juego(pregunta, datos, appid, mensajes) if datos is not None and appid is not None else None,
        lambda: None if datos is not None else _nombrado_sin_ficha(original),
        lambda: _filtros_del_catalogo(pregunta, original),
        lambda: _fuera_del_catalogo(pregunta, original, datos),
    )
    resultado = next((r for r in (intento() for intento in intentos) if r is not None), None) or _no_se(datos)

    previas = _respuestas_previas(mensajes)
    if previas and nia.pulir(resultado["texto"]) == previas[-1]:
        resultado = _resultado("Ya te lo conté arriba 🙂 ¿Te lo resumo o vemos otra cosa?")
    return resultado


def _nombrado_sin_ficha(original: str) -> dict | None:
    juegos = _nombrados(original)
    return _ficha_corta(juegos[0]) if len(juegos) == 1 else None


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
