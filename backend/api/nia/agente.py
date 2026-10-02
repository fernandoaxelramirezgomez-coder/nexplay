"""Nia: el chat de la ficha. Responde sobre un juego concreto con los datos que le
arma el backend, nunca con lo que el modelo crea recordar.

Con clave y modelo configurados llama a OpenAI; sin ellos, o si la llamada falla,
responde en modo demostración con reglas sobre esos mismos datos. La respuesta dice
siempre en qué modo salió, para que nadie confunda una cosa con la otra.

Reglas de vocabulario de NexPlay que van en el prompt y que el modo demostración
respeta por construcción: se habla de "arrepentimiento temprano" (nunca "abandono"),
es una señal proxy, se habla de riesgo de arrepentimiento bajo, medio o alto y nunca de
probabilidades ni scores, y no se recomienda
comprar ni no comprar.
"""

import hashlib
import json
import logging
import re
import unicodedata
import uuid
from decimal import ROUND_HALF_UP, Decimal

from .. import catalogo, panorama, scoring, valoraciones
from ..config import configuracion
from ..schemas import MAXIMO_RESPUESTA, MensajeChat, PerfilJugador, SugerenciaNia
from . import herramientas, reglas

logger = logging.getLogger(__name__)

_REFERENCIAS: dict | None = None

_FRASES_BANDA = {
    "bajo": "tiende a generar menos arrepentimiento temprano que el resto del catálogo",
    "medio": "no se distingue del resto del catálogo en arrepentimiento temprano",
    "alto": "tiende a generar más arrepentimiento temprano que el resto del catálogo",
}

# Nia no copia la tarjeta «Qué mueve esta estimación»: dice lo mismo como idea, con los
# mismos campos de la API que pinta la ficha (dirección, banda neutral y evidencia), para no
# contradecirla. calidad/verificar_nia.py lo comprueba en los 123 juegos.
PISTA_SOLIDA = "la pista más confiable del modelo"
PISTA_DEBIL = "una pista débil"
CASI_NO_MUEVE = "casi no mueve la estimación"
# Solo para un factor dentro de la banda neutral (cerca_de_lo_tipico): qué es lo normal lo
# decide el modelo, no un umbral de puntos.
EN_LO_NORMAL = "en lo normal del catálogo"

# Qué es la señal, dicho para alguien que llega nuevo. Va fija arriba del chat (en /nia, en la
# ficha y en la burbuja) y es lo que Nia contesta si preguntan qué significa: las respuestas no
# la repiten. Es la misma frase que EXPLICACION_SENAL en frontend/src/app/dominio/textos-nia.ts,
# para no decirlo dos veces de forma distinta (calidad/verificar_nia.py lo comprueba).
EXPLICACION_SENAL = (
    "El riesgo se basa en reseñas de gente que no recomendó el juego tras jugar menos de 2 horas."
    " Es una señal, no prueba que se arrepintiera."
)

# La cara de Nia según el nivel: ninguna sonrisa junto a un riesgo alto.
EMOJI_DEL_NIVEL = {"bajo": "🙂", "medio": "🤔", "alto": "😬"}

# Sin perfil no hay sugerencias. Con perfil se muestran coincidencias con lo declarado; Nia no
# elige por nadie, así que la invitación no puede sonar a «con tu perfil te digo cuál».
INVITA_AL_PERFIL = (
    "Sin perfil no sé qué géneros te gustan 🎮 Con uno te muestro qué juegos coinciden con ellos; elegir sigue"
    " siendo tuyo. Toma un minuto, ¿lo armamos?"
)

# Los avisos de la estimación, dichos como se le dirían a alguien.
_AVISOS_HABLADOS = {
    "precio_imputado": "Steam no dio su precio y el modelo lo tomó como 0, lo que tiende a bajar su riesgo",
    "gratis_extrapola": "ojo: al entrenar, el modelo vio muy pocos juegos gratis, así que tómalo con cuidado",
}

_IDEAS_SI_NO = {
    "gratuidad del juego": ("es gratis", "es de pago"),
    "descuento actual del juego": ("está con descuento", "no tiene descuento"),
    "cobertura de crítica especializada": ("la crítica especializada sí lo reseñó", "la crítica especializada no lo reseñó"),
}


def cifras_de_los_datos() -> dict:
    """Las cifras de reseñas y juegos que Nia puede citar, de una sola fuente para los dos modos:
    la muestra del catálogo que se sirve (data-v3) y el corte con que se entrenó el modelo
    (data-v1, del artefacto). Son distintas y no se mezclan."""
    p = panorama.resumen()
    modelo = scoring.ficha_del_modelo()
    return {
        "juegos_del_catalogo": p.juegos,
        "resenas_del_catalogo": p.resenas_descargadas,
        "juegos_del_entrenamiento": modelo.get("juegos_entrenamiento"),
        "resenas_del_entrenamiento": modelo.get("resenas_entrenamiento"),
    }


def cifras_habladas() -> str:
    """Las dos cifras en una frase que dice qué es cada una: OpenAI decía «123,972 reseñas
    de 83 juegos» y las reglas «184,367 reseñas» ante la misma pregunta."""
    c = cifras_de_los_datos()
    texto = f"El catálogo tiene {c['juegos_del_catalogo']} juegos y {c['resenas_del_catalogo']:,} reseñas de Steam"
    if not c["juegos_del_entrenamiento"] or not c["resenas_del_entrenamiento"]:
        return texto + "."
    texto += (
        f"; el modelo aprendió de {c['juegos_del_entrenamiento']} de esos juegos,"
        f" con {c['resenas_del_entrenamiento']:,} reseñas"
    )
    otros = c["juegos_del_catalogo"] - c["juegos_del_entrenamiento"]
    return texto + (f", y los otros {otros} sirven para probarlo." if otros > 0 else ".")


def pesos_enteros(valor: float) -> int:
    """Los pesos redondeados a la unidad, con 50 centavos hacia arriba (round() de Python
    deja 282.50 en 282): así un precio se dice igual en todas las respuestas."""
    return int(Decimal(str(valor)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def pesos_hablados(valor: float) -> str:
    """$283: en pesos enteros y sin «MXN», que en una frase sobra."""
    return f"${pesos_enteros(valor):,}"


def _frente_a_lo_normal(razon: float) -> str:
    """El precio contra el precio mediano del catálogo, en palabras. Nunca «en lo normal»:
    eso lo dice solo la banda neutral."""
    if razon < 0.35:
        return "menos de un tercio de lo normal"
    if razon < 0.65:
        return "como la mitad de lo normal"
    if razon < 0.9:
        return "algo menos que lo normal"
    if razon <= 1.1:
        return "más o menos lo normal"
    if razon < 1.6:
        return "algo más que lo normal"
    if razon < 2.4:
        return "alrededor del doble de lo normal"
    if razon < 3:
        return "casi el triple de lo normal"
    if razon < 3.4:
        return "el triple de lo normal"
    return f"unas {round(razon)} veces lo normal"


def precio_frente_al_catalogo(precio: float, mediano: float | None) -> str:
    """«cuesta $999, casi el triple de lo normal del catálogo ($350)»."""
    if not mediano:
        return f"cuesta {pesos_hablados(precio)}"
    return f"cuesta {pesos_hablados(precio)}, {_frente_a_lo_normal(precio / mediano)} del catálogo ({pesos_hablados(mediano)})"


def idea_de_factor(factor) -> str:
    """Lo que dice un factor de la API, como se le diría a alguien y sin su efecto."""
    if factor.etiqueta == "precio del juego":
        if factor.imputado or factor.valor is None:
            return "Steam no dio su precio y el modelo lo tomó como 0"
        if factor.valor == 0:
            return "es gratis"
        return precio_frente_al_catalogo(factor.valor, factor.referencia)
    if factor.etiqueta == "nota de Metacritic" and factor.valor is not None:
        if factor.referencia is None:
            return f"la crítica le dio {factor.valor:g}"
        if factor.cerca_de_lo_tipico:
            donde = EN_LO_NORMAL
        else:
            donde = f"{'arriba' if factor.valor > factor.referencia else 'abajo'} de lo normal del catálogo"
        return f"la crítica le dio {factor.valor:g}, {donde} ({factor.referencia:.1f})"
    si, no = _IDEAS_SI_NO.get(factor.etiqueta, (f"{factor.etiqueta} alto", f"{factor.etiqueta} bajo"))
    return si if factor.valor_relativo.value == "alto" else no


def efecto_hablado(factor: dict) -> str:
    """«sube su riesgo», «baja su riesgo» o, dentro de la banda neutral, que casi no mueve."""
    if factor["efecto"] is None:
        return CASI_NO_MUEVE
    return f"{factor['efecto']} su riesgo"


def generos_declarados(generos: list[str] | None) -> list[str]:
    """Los géneros declarados que son géneros del catálogo, con su nombre de Steam. Se
    comparan sin mayúsculas y lo demás se descarta: al modelo no llega texto libre."""
    del_catalogo = {g.lower(): g for j in catalogo.buscar() for g in j.generos}
    return list(dict.fromkeys(
        del_catalogo[g.strip().lower()] for g in generos or [] if g.strip().lower() in del_catalogo
    ))


def afinidad(juego, generos: list[str] | None) -> dict | None:
    """Qué géneros de los que declaró la persona tiene el juego y cuáles no. No mueve el
    riesgo."""
    declarados = generos_declarados(generos)
    if not declarados:
        return None
    tiene = {g.lower() for g in juego.generos}
    return {
        "declarados": declarados,
        "coinciden": [g for g in declarados if g.lower() in tiene],
        "no_tiene": [g for g in declarados if g.lower() not in tiene],
    }


def quejas_en_conteos(datos: dict) -> list[tuple[str, int]]:
    """Los motivos como cuántas reseñas los mencionan, no como porcentaje: la mediana del
    catálogo es de 4 reseñas que dicen por qué, y «100%» sobre 5 suena más firme de lo que es."""
    return [(m.motivo, round(m.frecuencia * datos["clasificadas"])) for m in datos["motivos"]]

def _factores_visibles(factores, juego) -> list[dict]:
    """Los factores del modelo como idea, con su efecto y qué tan firme es, en el orden de
    la API (de mayor a menor aporte).

    Mismo filtro que factoresVisibles() en dominio/factores.ts: solo se quita la nota de un
    juego sin nota, porque la cobertura ya dice que no la tiene. El precio que falta se
    queda, marcado como imputado, igual que en la ficha."""
    visibles = []
    for factor in factores:
        if juego.metacritic is None and factor.etiqueta == "nota de Metacritic":
            continue
        visibles.append(
            {
                "etiqueta": factor.etiqueta,
                # Dentro de la banda neutral no sube ni baja: casi no mueve la estimación.
                "efecto": None if factor.cerca_de_lo_tipico else "sube" if factor.direccion.value == "aumenta" else "baja",
                "debil": factor.evidencia.value == "debil",
                "imputado": factor.imputado,
                "idea": idea_de_factor(factor),
                "pista": PISTA_DEBIL if factor.evidencia.value == "debil" else PISTA_SOLIDA,
            }
        )
    return visibles


def linea_de_factor(factor: dict) -> str:
    """Un factor en una línea, ya como idea, para el modelo de lenguaje y ficha_juego: así no
    tiene etiquetas que copiar."""
    idea = f"{factor['idea'][0].upper()}{factor['idea'][1:]}"
    if factor["efecto"] is None:
        return f"{idea}: {CASI_NO_MUEVE}; no es razón de su riesgo."
    return f"{idea}: eso {efecto_hablado(factor)}. Es {factor['pista']}."


_SISTEMA = """Eres Nia, la asistente de NexPlay: una amiga gamer, cercana y cálida, que lee los
datos del catálogo como los leería alguien que reseña juegos y te cuenta qué dicen.

Cómo hablas:
- En español, en tono cercano y alegre, como una amiga que sabe de juegos. Saluda solo si
  es el primer mensaje de la conversación; después ve directo.
- Usa de 1 a 3 emojis por respuesta, nunca más, y que vayan con el tono: junto a un riesgo
  alto, nada de caritas felices (🙂, 😊); usa 😬 o 🤔.
- Habla con las palabras de quien pregunta, no con nombres de variables ni etiquetas:
  primero responde lo que se preguntó (sí, no, un poco, en parte) y después da la razón en
  una frase natural.
- **60 palabras o menos.** La primera oración responde lo que se preguntó, directo, y nombra
  el juego del que hablas; lo demás es el porqué. No cierres con una pregunta: NexPlay agrega
  al final una que sí se puede cumplir ("¿Te cuento qué dicen sus reseñas?").
- Recuerdas la conversación: si te piden "resume", "en corto" o "lo que dijiste antes",
  resume tus propias respuestas anteriores del hilo, sin repetirlas completas. Si dicen "de
  esos" o "¿y cuál de esos…?", se refieren a la última lista de juegos que diste.
- Nunca repitas la misma respuesta dos veces seguidas: si ya lo dijiste, di que puedes resumirlo o
  seguir con otra cosa.

Puedes hablar de UN juego —el que esté abierto— o del catálogo entero. Para lo segundo
tienes herramientas: úsalas siempre en vez de recordar, porque de este catálogo no sabes
nada de memoria.

Reglas que no puedes romper:
- Responde en texto plano: sin markdown, sin asteriscos para resaltar, sin viñetas ni
  títulos. Lo que escribas se pinta tal cual, así que un **así** se ve con los asteriscos.
- Usa siempre "arrepentimiento temprano", nunca "abandono", ni siquiera para citar la
  pregunta: si te preguntan por el abandono, contesta con arrepentimiento temprano.
- El riesgo es una señal proxy: sale de reseñas de Steam de gente que jugó menos de 2 horas
  y no recomendó el juego, y no confirma que alguien se arrepintiera. Nunca digas que
  alguien se arrepintió. Esa explicación ya está fija arriba del chat: no la repitas en tus
  respuestas. Solo si preguntan qué significa la señal o el riesgo, contesta con esta misma
  frase: «__EXPLICACION_SENAL__». Si la pregunta es de otra cosa —el precio, la crítica, los
  géneros—, respóndela y ya: no metas el riesgo ni el aviso donde nadie los pidió.
- Si quien pregunta dice que juega poco, o cuántas horas juega, usa esa cifra para decirle
  en cuántas sesiones llegaría a las dos horas de la ventana de reembolso, en vez de
  repetir que la ventana son 120 minutos.
- Habla del riesgo de arrepentimiento: bajo, medio o alto. Nunca digas "banda": quien usa
  NexPlay no sabe qué es. Nunca des probabilidades, porcentajes de riesgo
  ni scores numéricos del modelo. Las quejas de las reseñas se dicen en conteos («5 de las
  11 hablan de rendimiento»), nunca en porcentaje; si son menos de 10, di que son pocas y
  que hay que tomarlo con cautela.
- El riesgo de arrepentimiento lo asigna un modelo entrenado con reseñas de Steam, a partir
  de datos del juego (precio, gratuidad, descuento, nota y cobertura de crítica). Las reseñas
  de un juego explican sus motivos, no su riesgo: nunca digas que el riesgo sale de sus
  reseñas. Es del juego, igual para cualquiera: no digas que es el riesgo de quien pregunta.
- Para explicar por qué un juego tiene ese riesgo, usa las ideas de "Qué mueve su riesgo"
  del contexto, sin inventar otras variables y sin pegar etiquetas («Precio: … · …») ni
  flechas. Van de lo que más pesa a lo que menos: nombra primero la primera, como idea
  («cuesta casi el triple de lo normal del catálogo»). Di qué tan firme es como viene: «es
  una pista débil» o «es la pista más confiable del modelo»; nunca «evidencia débil» ni
  «no se distingue de cero». Lo que «casi no mueve la estimación» no lo des como razón, y
  di «en lo normal» solo de lo que el contexto dice que está en lo normal.
- Si el contexto trae "Avisos de esta estimación", cada vez que hables del riesgo de ese
  juego di cada aviso, con esas palabras o las tuyas. Cuentan dentro de las 60
  palabras: si no cabe todo, recorta los factores, nunca el aviso, la explicación de la señal
  ni el emoji. Si el contexto no trae avisos, no hables de avisos.
- La nota y el precio se comparan con lo normal del catálogo, con las cifras de la línea
  "Catálogo". Di el precio en palabras («casi el triple de lo normal del catálogo») además
  de la cifra, en pesos enteros como vienen («$283», nunca con centavos); no digas «precio
  mediano» ni hables de un promedio que use el modelo.
- El precio aparece en dos lugares distintos y no hay que confundirlos: como variable del
  modelo (en "Qué mueve su riesgo") y como queja en las reseñas (en "Quejas").
  Pueden apuntar en direcciones opuestas; si te preguntan por el precio, di de cuál hablas.
- No recomiendes comprar ni no comprar, ni digas si vale la pena. Describe lo que dicen
  los datos y deja la decisión a quien pregunta.
- Nunca des un dictamen: nada de "adecuado", "te conviene" ni "es para ti". Di lo que dicen
  los datos de lo que le importa, lo que no dicen y que la decisión es suya.
- Si dice qué le importa, llévalo a las categorías de quejas y da sus conteos: rendimiento,
  fps, lag o estabilidad → rendimiento y bugs; errores → bugs; difícil o reto → dificultad;
  jugabilidad o mando → controles; historia o duración → contenido; caro → precio. Si hay
  quejas de eso, dilo como alerta ("Ojo con eso"), nunca a favor; si no hay, di que eso no
  garantiza nada. Lo que no es una categoría (gráficos, música) no está en los datos: dilo.
- La conclusión sale de las cifras que citas: si citas quejas, no concluyas a favor.
- Responde solo con los datos del contexto o de las herramientas. Si te preguntan algo que
  no está ahí, dilo con claridad en vez de inventarlo.
- El catálogo son 123 juegos de Steam y nada más. Para filtrar, comparar o contar usa
  buscar_juegos, resolver_juego, ficha_juego, panorama_del_catalogo o metodologia. Nunca
  nombres un juego, un precio o una nota que no te haya devuelto una herramienta.
- Hay dos cifras de reseñas y no se mezclan: las del catálogo y las del entrenamiento del
  modelo. Si dices las dos, di cuál es cuál con las palabras de "que_es_cada_cifra"
  (panorama_del_catalogo); nunca des una por la otra.
- Si la pregunta es de un juego ("¿por qué tiene ese riesgo?", "¿cuánto cuesta?") y no hay
  ningún juego abierto ni nombrado en la conversación, llama a pedir_juego en vez de
  adivinar cuál.
- Si piden recomendaciones o sugerencias para ellos, llama a sugerencias_del_perfil: es la
  lista que ya calculó NexPlay con lo que declararon. Preséntalas como "sugerencias según tu
  perfil", con el riesgo de cada una, y nunca digas cuál comprar. Di en qué géneros
  coincide cada una (coincide_en) y cuáles de los declarados no tiene (no_tiene), nunca
  como porcentaje. Si responde sin_perfil, invita a crear el perfil: con él verá qué juegos
  coinciden con sus géneros. Nunca digas que con el perfil elegirás, sabrás cuál le conviene
  o le dirás cuál comprar: son coincidencias y la decisión sigue siendo suya.
- Si preguntan si un juego encaja con ellos, usa "Tus géneros" del contexto (o los géneros
  que declararon, contra los del juego que te den las herramientas): di qué géneros
  coinciden y cuáles no, con sus nombres. Nunca des la afinidad como porcentaje ni como
  fracción, y aclara que no cambia el riesgo. Si no declararon géneros, invita a crear el
  perfil.
- buscar_juegos devuelve hasta 8 en orden alfabético. Si trae "hay_mas", dilo con ese
  número y di que el resto está en Explorar con esos filtros; no inventes los que faltan
  ni escribas la URL, que en una respuesta de chat es ruido.
- Filtrar y ordenar sí; elegir por alguien, no. Aunque te pidan "el mejor" o "cuál me
  compro", describe lo que dicen los datos y deja la decisión a quien pregunta.
- Las opiniones y los comentarios que la gente escribe en NexPlay no son datos del
  catálogo y no los tienes: no hables de ellos.
- Si la pregunta no es de videojuegos, del catálogo o de NexPlay (trivia, tareas, datos
  personales, otros temas), no la contestes aunque sepas la respuesta: di que solo hablas
  de los juegos del catálogo y ofrece filtrarlo por género, precio o riesgo.
- Nunca digas que un juego es el mejor, que encabeza el catálogo, que es el número uno ni
  el más recomendable. Si piden "el mejor", ofrece ordenar por precio, riesgo o crítica y
  pregunta por cuál; ordenar por un criterio que ya dieron sí se vale.
- Si dices cuántos juegos cumplen algo, nombra todos los que muestras; si no caben, di
  cuántos más hay ("y 2 más en Explorar").
- Los juegos que nombras y te devolvió una herramienta se pintan como tarjetas, cada una con
  su riesgo: no digas el riesgo de cada uno ni los enumeres («bajo, bajo y alto,
  respectivamente», «Hades (riesgo bajo)»). Si importa, di cuántos hay de cada nivel.
- "Horas típicas" son las horas que llevaba jugadas, en la mediana, quien recomendó el
  juego; no es lo que dura. Si preguntan cuánto dura, contesta así, con las horas típicas
  del contexto o de la herramienta:
  «No hay duración oficial; quienes lo recomiendan jugaron X h (mediana)».
  Si no las hay, di que tampoco hay ese dato.
- Si piden negritas, viñetas o tablas, di en una frase que escribes en texto simple y
  responde lo que pidieron.
- Si piden jugar con amigos, multijugador, cooperativo u online, busca el género
  "Multijugador masivo" y ofrécelo, aclarando que el catálogo no tiene un dato específico
  de cooperativo ni de en línea.
- Si en la pregunta aparece "[dato personal]", di que no guardas datos personales.
- Cuando venga al caso, nombra las fortalezas y las debilidades del juego, siempre salidas
  de los datos: la nota de la crítica o su ausencia, el riesgo, el precio frente al
  catálogo y los motivos más mencionados. No opines por tu cuenta ni inventes otras.
- Para decir en qué se destaca o en qué se queda corto frente a otros juegos, usa solo las
  cifras de la línea "Catálogo" del contexto. Nunca inventes datos de otro juego.
- Si preguntan por un juego que no es el del contexto y que el contexto no marca como
  parte del catálogo, empieza la respuesta con esta frase, con el nombre que usaron:
  "<Juego> no está en este catálogo de Steam, así que no tengo ninguna señal sobre él
  para comparar." Después sigue con lo que sí sabes del juego del contexto. No inventes
  nada de ese otro juego.
"""


# Los emojis que cuentan para el tope de 3: pictogramas, símbolos misceláneos y los de
# ⌛ o ⭐. Las flechas de texto (→), ™ y ® no son emojis y no cuentan.
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF]\ufe0f?")
MAXIMO_EMOJIS = 3

# "banda" es jerga del proyecto: la gente ve "riesgo". El prompt lo pide y aun así se
# escapa ("su banda de arrepentimiento temprano es baja"), así que se corrige a la salida.
_MASCULINO = {"alta": "alto", "baja": "bajo", "media": "medio"}
_BANDA = (
    (re.compile(r"\b([Ll]a|[Ee]sa|[Ee]sta) banda\b"),
     lambda m: {"la": "el", "La": "El", "esa": "ese", "Esa": "Ese", "esta": "este", "Esta": "Este"}[m.group(1)] + " riesgo"),
    (re.compile(r"\b[Bb]andas?\b"), lambda m: "riesgo" if m.group(0)[0] == "b" else "Riesgo"),
    (re.compile(r"\b([Rr]iesgo) (alta|baja|media)\b"), lambda m: f"{m.group(1)} {_MASCULINO[m.group(2)]}"),
    (re.compile(r"\b([Rr]iesgo[^.]{0,40}?) es (alta|baja|media)\b"), lambda m: f"{m.group(1)} es {_MASCULINO[m.group(2)]}"),
    # «¿Cuál es la tasa de abandono?»: el modelo repetía la palabra de la pregunta.
    (re.compile(r"\b([Aa])bandono\b"), lambda m: "arrepentimiento temprano" if m.group(1) == "a" else "Arrepentimiento temprano"),
)


# «Hades, Rust y Apex tienen riesgo bajo, alto y bajo, respectivamente», «Diablo® IV (riesgo
# alto)»: con tarjetas, el riesgo de cada juego ya va en su píldora. El prompt lo pide y no
# siempre se cumple, así que también se quita a la salida.
_NIVEL = r"(?:bajo|medio|alto)"
_RIESGOS_ENUMERADOS = (
    re.compile(
        rf",?\s+(?:que\s+)?(?:tienen|con|de)\s+(?:un\s+)?riesgos?(?:\s+de\s+arrepentimiento(?:\s+temprano)?)?\s+"
        rf"{_NIVEL}(?:\s*,\s*{_NIVEL})*,?\s+y\s+{_NIVEL},?\s+respectivamente(?:,(?=\s))?",
        re.IGNORECASE,
    ),
    re.compile(rf"\s*\((?:riesgo\s+)?(?:de\s+arrepentimiento\s+)?{_NIVEL}\)", re.IGNORECASE),
)


def sin_riesgos_enumerados(texto: str) -> str:
    """Quita el riesgo dicho juego por juego; se usa solo cuando la respuesta trae tarjetas."""
    for patron in _RIESGOS_ENUMERADOS:
        texto = patron.sub("", texto)
    return re.sub(r"\s+([.,;:])", r"\1", texto).strip()


def palabras(texto: str) -> int:
    """Palabras de una respuesta, sin contar los emojis."""
    return len([p for p in EMOJI.sub(" ", texto).split() if p.strip("¡!¿?.,;:")])


def pulir(texto: str) -> str:
    """Lo que el prompt pide y a veces no se cumple: sin "banda" ni "abandono" y con 3 emojis
    como máximo."""
    for patron, reemplazo in _BANDA:
        texto = patron.sub(reemplazo, texto)
    vistos = 0

    def uno(m: re.Match) -> str:
        nonlocal vistos
        vistos += 1
        return m.group(0) if vistos <= MAXIMO_EMOJIS else ""

    texto = EMOJI.sub(uno, texto)
    return re.sub(r"[ \t]{2,}", " ", texto).strip()


# Qué prompt produjo una respuesta, para poder comparar los votos de antes y después de
# cambiarlo. Sale del texto mismo: una etiqueta a mano se queda vieja sin que nadie lo
# note, y entonces los votos de dos prompts distintos se suman como si fueran uno.
_SISTEMA = _SISTEMA.replace("__EXPLICACION_SENAL__", EXPLICACION_SENAL)

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
        "appid": appid,
        "nombre": juego.nombre,
        "banda": prediccion.nivel.value,
        "factores": _factores_visibles(prediccion.factores, juego),
        # Juegos gratis (el modelo extrapola) y de pago sin precio (lo tomó como 0).
        "avisos": [aviso.texto for aviso in prediccion.avisos],
        "avisos_hablados": [_AVISOS_HABLADOS.get(aviso.codigo, aviso.texto) for aviso in prediccion.avisos],
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
        # Las de «Horas típicas» en la ficha técnica: mediana de horas de quien lo recomendó.
        "horas_tipicas": _horas_tipicas(appid),
    }


def _horas_tipicas(appid: int) -> float | None:
    from .. import panorama  # aquí y no arriba: panorama carga el catálogo al importarse

    fila = next((f for f in panorama.resumen().por_juego if f.appid == appid), None)
    return fila.horas_al_recomendar if fila else None


def _texto_precio(datos: dict) -> str:
    if datos["es_gratis"]:
        return "es gratis"
    if datos["precio"] is None:
        return "no tiene precio en los datos"
    return f"cuesta {pesos_hablados(datos['precio'])}"


def _texto_critica(datos: dict) -> str:
    nota = datos["metacritic"]
    if nota is None:
        return "la crítica especializada no lo cubrió (sin nota de Metacritic)"
    juicio = "bien" if nota >= 75 else "de forma mixta" if nota >= 50 else "mal"
    return f"la crítica especializada lo calificó {juicio} (Metacritic {nota})"


def factor_del_precio(datos: dict) -> dict | None:
    """El factor del modelo que habla del precio: el precio, la gratuidad o el descuento.

    Es la distinción que más se confunde: que el precio mueva la estimación no es lo mismo
    que la gente se queje del precio en las reseñas."""
    # En un juego gratuito lo que dice algo es la gratuidad, no que su precio de 0 quede
    # por debajo del promedio.
    etiquetas = (
        ("gratuidad del juego", "descuento actual del juego", "precio del juego")
        if datos["es_gratis"]
        else ("precio del juego", "descuento actual del juego", "gratuidad del juego")
    )
    return next((f for e in etiquetas for f in datos["factores"] if f["etiqueta"] == e), None)


def _referencias_del_catalogo() -> dict:
    """Las referencias de la ficha (scoring.referencias_del_catalogo: el promedio de la nota y
    el precio mediano) más lo que solo usa Nia para comparar. Se calculan una vez: el catálogo
    se carga al importar y no cambia mientras corre la API."""
    global _REFERENCIAS
    if _REFERENCIAS is None:
        juegos = catalogo.buscar()
        _REFERENCIAS = {
            **scoring.referencias_del_catalogo(),
            "juegos": len(juegos),
            "con_nota": sum(1 for j in juegos if j.metacritic is not None),
            "de_pago_con_precio": sum(1 for j in juegos if not j.es_gratis and j.precio_final is not None),
            "bandas": {b: sum(1 for j in juegos if j.banda_riesgo.value == b) for b in ("bajo", "medio", "alto")},
        }
    return _REFERENCIAS


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _sin_marcas(texto: str) -> str:
    """Sin ™, ® ni ©: el catálogo escribe «Apex Legends™» y casi nadie los teclea."""
    return texto.replace("™", "").replace("®", "").replace("©", "")


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
    # Sin apóstrofos, recto (') ni tipográfico (’): «Don’t Starve» y «Sid Meier’s» del
    # modelo contra «Don't Starve» y «Sid Meier's» del catálogo. Sin ™, ® ni ©, como las
    # variantes: el modelo copia «Diablo® IV» tal cual y no coincidía con «diablo iv».
    texto = _sin_marcas(_sin_acentos(pregunta)).replace("'", "").replace("’", "")
    encontrados = []
    for juego in catalogo.buscar():
        if juego.appid == appid_abierto:
            continue
        for variante in _variantes_del_nombre(juego.nombre):
            if re.search(rf"(?<!\w){re.escape(variante.replace(chr(39), '').replace('’', ''))}(?!\w)", texto):
                encontrados.append(juego.nombre)
                break
    # "Portal 2" ya implica "Portal": se queda el título más largo de cada coincidencia. Con
    # frontera de palabra: "Civilization V" no está dentro de "Civilization VI".
    def dentro(corto: str, largo: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(_sin_acentos(corto))}(?!\w)", _sin_acentos(largo)) is not None

    return [n for n in encontrados if not any(n != otro and dentro(n, otro) for otro in encontrados)]


# Cómo se nombra un juego cuando no sale de su nombre en Steam. Van tal cual, aunque sean
# cortas: son siglas que nadie usa para otra cosa.
_ALIAS = {
    "Grand Theft Auto V Legacy": ("gta", "gta v", "gta 5", "gta v legacy", "grand theft auto v"),
}


def _variantes_del_nombre(nombre: str) -> list[str]:
    """El nombre completo y su primera parte, normalizados, y sus alias; descarta lo muy
    corto que no sea alias."""
    limpio = _sin_acentos(_sin_marcas(nombre)).strip()
    variantes = {limpio, limpio.split(":")[0].strip(), limpio.split(" - ")[0].strip()}
    # "The Sims 4" también se escribe "Los Sims 4": vale sin el artículo del principio.
    variantes |= {v[4:] for v in variantes if v.startswith("the ")}
    # "Sid Meier's Civilization V" también se escribe "Civilization V": sin el posesivo.
    variantes |= {re.sub(r"^[\w ]+?['’]s ", "", v) for v in variantes}
    # "baldurs gate 3" también es Baldur's Gate 3: casi nadie escribe el apóstrofo.
    variantes |= {v.replace("'", "").replace("’", "") for v in variantes}
    return [v for v in variantes if len(v) >= 4] + list(_ALIAS.get(nombre, ()))


def _texto_comparacion(datos: dict, ref: dict) -> str:
    """Dónde cae este juego dentro del catálogo, en palabras y con sus cifras: el precio
    contra lo normal del catálogo y la nota con la lectura de la ficha («en lo normal» solo
    si el modelo la deja en la banda neutral)."""
    partes = []
    if datos["es_gratis"]:
        partes.append("es gratis")
    elif datos["precio"] is None:
        partes.append("no tiene precio en los datos")
    else:
        partes.append(precio_frente_al_catalogo(datos["precio"], ref["precio_mediano"]))
    nota = next((f for f in datos["factores"] if f["etiqueta"] == "nota de Metacritic"), None)
    if datos["metacritic"] is None:
        partes.append("la crítica especializada no lo reseñó")
    else:
        partes.append(nota["idea"] if nota else f"la crítica le dio {datos['metacritic']}")
    partes.append(f"su riesgo de arrepentimiento es {datos['banda']}")
    return "; ".join(partes)


def _quejas_para_el_modelo(datos: dict) -> str:
    conteos = quejas_en_conteos(datos)
    if not conteos:
        return "Quejas: no hay suficientes reseñas para señalar una"
    total = datos["clasificadas"]
    texto = (f"Quejas (cuántas de las {total} reseñas que dicen por qué mencionan cada una; dilo así, nunca en"
             f" porcentaje): {'; '.join(f'{motivo} {cuantas}' for motivo, cuantas in conteos)}")
    if total < 10:
        texto += ". Son pocas: si las citas, di que hay que tomarlo con cautela"
    return texto


def _linea_de_afinidad(afinidad_: dict | None) -> str | None:
    if afinidad_ is None:
        return None
    return (f"Tus géneros (los que declaró quien pregunta; no cambian el riesgo): {', '.join(afinidad_['declarados'])}."
            f" Coincide en: {', '.join(afinidad_['coinciden']) or 'ninguno'}."
            f" No tiene: {', '.join(afinidad_['no_tiene']) or 'ninguno'}.")


def _contexto_para_prompt(datos: dict, mencionados: list[str] | None = None, generos: list[str] | None = None) -> str:
    lineas = [
        f"Juego: {datos['nombre']}",
        f"Riesgo de arrepentimiento del juego (el mismo para cualquier perfil): {datos['banda']}",
        f"Géneros: {', '.join(datos['generos']) or 'sin datos'}",
        f"Crítica: {_texto_critica(datos)}",
        f"Precio: {_texto_precio(datos)}",
        f"Lanzamiento: {datos['lanzamiento'] or 'sin dato'}",
        "Horas típicas (mediana de horas jugadas de quien lo recomendó; no es lo que dura): "
        + (f"{datos['horas_tipicas']:g} h" if datos.get("horas_tipicas") is not None else "sin dato"),
        f"Reseñas negativas tempranas: {datos['n_casos']}; de ellas, {datos['clasificadas']} dicen por qué se quejan",
        _quejas_para_el_modelo(datos),
    ]
    # El mismo orden que la ficha muestra en «Qué mueve esta estimación», pero como ideas:
    # sin esto Nia atribuía el riesgo a las reseñas, y con las etiquetas las copiaba tal cual.
    lineas.append("Qué mueve su riesgo, de lo que más pesa a lo que menos (son ideas: dilas así, sin etiquetas ni flechas):")
    if datos["factores"]:
        lineas += [f"- {linea_de_factor(f)}" for f in datos["factores"]]
    else:
        lineas.append("- ninguno de sus datos se aleja mucho de lo típico del catálogo")
    lineas.append(
        "Esto es lo que produce el riesgo. Las quejas de las reseñas dicen de qué se queja la gente, no por qué"
        " el modelo puso ese riesgo."
    )
    if datos["avisos_hablados"]:
        lineas.append("Avisos de esta estimación (dilos cada vez que hables de su riesgo):")
        lineas += [f"- {aviso[0].upper()}{aviso[1:]}." for aviso in datos["avisos_hablados"]]
    ref = _referencias_del_catalogo()
    bandas = " / ".join(f"{n} {b}" for b, n in ref["bandas"].items())
    lineas.append(
        f"Catálogo ({ref['juegos']} juegos, para comparar): lo normal del precio es {pesos_hablados(ref['precio_mediano'])} (la"
        f" mediana de los {ref['de_pago_con_precio']} de pago con precio); la nota promedio es {ref['nota_promedio']}"
        f" entre los {ref['con_nota']} que tienen nota; riesgo de arrepentimiento {bandas}"
    )
    lineas.append(f"Este juego frente al catálogo: {_texto_comparacion(datos, ref)}")
    afinidad_ = _linea_de_afinidad(afinidad(catalogo.obtener(datos["appid"]), generos))
    if afinidad_:
        lineas.append(afinidad_)
    if mencionados:
        lineas.append(
            "Otros juegos del catálogo que nombra la pregunta (no tienes sus datos aquí, así que NO son"
            f" juegos fuera del catálogo): {', '.join(mencionados)}"
        )
    return "\n".join(lineas)


def sin_datos_personales(texto: str) -> str:
    """Correos y teléfonos fuera, antes de anotar la pregunta o mandarla al modelo: así es
    cierto que Nia no guarda datos personales (la pregunta se anota 180 días para los votos)."""
    texto = reglas._CORREO.sub("[dato personal]", texto)
    return reglas._TELEFONO.sub("[dato personal]", texto)


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


def _parametros_iniciales() -> dict:
    """Un modelo de chat (sin razonamiento): esfuerzo "none", 400 tokens y temperatura baja.
    Uno de razonamiento: sus tokens de pensar cuentan en el tope, así que 1,200 y esfuerzo
    "low"; esos modelos no aceptan temperatura. Lo que el modelo rechace igual se corrige
    solo en _crear_con_reintentos."""
    if configuracion.nexplay_nia_razonamiento:
        return {"max_completion_tokens": max(configuracion.nexplay_nia_max_tokens, 1200), "reasoning_effort": "low"}
    return {"max_completion_tokens": configuracion.nexplay_nia_max_tokens, "reasoning_effort": "none", "temperature": 0.2}


def _crear_con_reintentos(cliente, conversacion: list[dict], herramientas_disponibles: list[dict] | None = None):
    """Llama al modelo y, si rechaza un parámetro, lo traduce a su equivalente o lo quita.

    Un modelo nuevo responde 400 'Unsupported parameter: max_tokens ... use
    max_completion_tokens'; uno viejo hace lo contrario. Así funcionan los dos sin tener
    que adivinar cuál está configurado."""
    modelo = configuracion.nexplay_modelo_nia
    opcionales = _PARAMETROS_APRENDIDOS.get(modelo, _parametros_iniciales())
    parametros = {"model": modelo, "messages": conversacion, **opcionales}
    if herramientas_disponibles:
        parametros["tools"] = herramientas_disponibles
    for _ in range(_MAXIMO_REINTENTOS):
        try:
            respuesta = cliente.chat.completions.create(**parametros)
            _PARAMETROS_APRENDIDOS[modelo] = {
                k: v for k, v in parametros.items() if k not in ("model", "messages", "tools")
            }
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
    _PARAMETROS_APRENDIDOS[modelo] = {k: v for k, v in parametros.items() if k not in ("model", "messages", "tools")}
    return respuesta


# Cuántas veces puede parar a consultar antes de contestar. Las llamadas de una misma
# ronda van en paralelo, así que comparar cuatro juegos gasta una ronda, no cuatro.
_MAXIMO_RONDAS = 3

# Cuánto del hilo llega al modelo, contando desde lo más reciente: los últimos 10 turnos
# (pregunta y respuesta) y, dentro de eso, hasta 8,000 caracteres, unos 2,000 tokens. El
# resumen de toda la conversación ya no pasa por el modelo (lo hacen las reglas con el hilo
# entero), así que no hace falta mandarle más; y un historial fabricado no llega completo.
MAXIMO_CARACTERES_DE_HISTORIAL = 8000
MAXIMO_TURNOS_AL_MODELO = 10
MAXIMO_CARACTERES_POR_MENSAJE_DE_NIA = MAXIMO_RESPUESTA


def historial_para_el_modelo(mensajes: list[MensajeChat]) -> list[MensajeChat]:
    """Los mensajes más recientes que caben en los topes; la pregunta nueva siempre entra."""
    elegidos: list[MensajeChat] = []
    usados = 0
    for mensaje in reversed(mensajes[-(2 * MAXIMO_TURNOS_AL_MODELO + 1):]):
        if elegidos and usados + len(mensaje.contenido) > MAXIMO_CARACTERES_DE_HISTORIAL:
            break
        elegidos.insert(0, mensaje)
        usados += len(mensaje.contenido)
    return elegidos


# Las dos herramientas que dependen de la solicitud y no del catálogo: se resuelven aquí,
# no en herramientas.py.
_ESQUEMAS_DE_LA_SOLICITUD = [
    {
        "type": "function",
        "function": {
            "name": "pedir_juego",
            "description": (
                "Pide a quien pregunta que elija un juego. Úsala cuando la pregunta es de un juego y no hay"
                " ninguno abierto ni nombrado en la conversación: el chat le muestra un buscador."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sugerencias_del_perfil",
            "description": (
                "Las sugerencias que NexPlay ya calculó con el perfil declarado, con su riesgo y su porqué."
                " Úsala solo si piden recomendaciones para ellos. Si responde sin_perfil, invita a crearlo."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _sugerencias_del_perfil(sugerencias: list[SugerenciaNia], generos: list[str] | None = None) -> dict:
    juegos = []
    for sugerencia in sugerencias:
        juego = catalogo.obtener(sugerencia.appid)
        if juego is not None:
            afinidad_ = afinidad(juego, generos)
            juegos.append({
                **herramientas._resumen_de_juego(juego),
                # En qué géneros coincide y cuáles de los declarados no tiene: los hechos,
                # para que no los vuelva un porcentaje.
                **({"coincide_en": afinidad_["coinciden"], "no_tiene": afinidad_["no_tiene"]} if afinidad_ else {}),
                "porque": sugerencia.razones,
            })
    if not juegos:
        return {"sin_perfil": True}
    return {"sugerencias_segun_tu_perfil": juegos}


def _preguntar_a_openai(
    datos: dict | None,
    mensajes: list[MensajeChat],
    mencionados: list[str],
    sugerencias: list[SugerenciaNia],
    generos: list[str] | None = None,
) -> dict:
    """Devuelve la respuesta, los pasos que dio, los appids que le dieron las herramientas,
    las sugerencias que enseñó y si pidió un juego o el perfil.

    Esos appids son los únicos que pueden acabar en una tarjeta: lo que el modelo nombre
    sin haberlo consultado no se pinta."""
    from openai import OpenAI  # perezoso: sin el paquete, Nia sigue en modo demostración

    cliente = OpenAI(api_key=configuracion.openai_api_key, timeout=configuracion.nexplay_nia_timeout)
    conversacion: list[dict] = [{"role": "system", "content": _SISTEMA}]
    if datos is not None:
        conversacion.append(
            {"role": "system", "content": f"Datos del juego:\n{_contexto_para_prompt(datos, mencionados, generos)}"}
        )
    else:
        conversacion.append({"role": "system", "content": _contexto_del_catalogo(generos)})
    anteriores = next((m.juegos for m in reversed(mensajes[:-1]) if m.rol == "nia"), [])
    nombres_anteriores = [j.nombre for j in (catalogo.obtener(a) for a in anteriores) if j is not None]
    if nombres_anteriores:
        conversacion.append({
            "role": "system",
            "content": "Los juegos de tu respuesta anterior, a los que se refieren «esos», «esos dos», «ese juego» o"
            f" «eso»: {', '.join(nombres_anteriores)}.",
        })
    conversacion += [
        {
            "role": "user" if mensaje.rol == "usuario" else "assistant",
            "content": sin_datos_personales(mensaje.contenido) if mensaje.rol == "usuario" else mensaje.contenido,
        }
        for mensaje in historial_para_el_modelo(mensajes)
    ]

    salida_final = {
        "texto": "", "pasos": [], "appids": set(), "orden": [], "sugerencias": [], "pide_juego": False,
        "pide_perfil": False,
    }
    esquemas = herramientas.ESQUEMAS + _ESQUEMAS_DE_LA_SOLICITUD
    for ronda in range(_MAXIMO_RONDAS):
        # En la última vuelta se le quitan las herramientas: así cierra con lo que tiene
        # en vez de quedarse pidiendo datos hasta agotar el tope.
        ultima = ronda == _MAXIMO_RONDAS - 1
        respuesta = _crear_con_reintentos(cliente, conversacion, None if ultima else esquemas)
        mensaje = respuesta.choices[0].message
        llamadas = getattr(mensaje, "tool_calls", None) or []
        if not llamadas:
            salida_final["texto"] = (mensaje.content or "").strip()
            return salida_final

        conversacion.append({
            "role": "assistant",
            "content": mensaje.content or "",
            "tool_calls": [
                {"id": l.id, "type": "function", "function": {"name": l.function.name, "arguments": l.function.arguments}}
                for l in llamadas
            ],
        })
        for llamada in llamadas:
            try:
                argumentos = json.loads(llamada.function.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}
            nombre = llamada.function.name
            if nombre == "pedir_juego":
                salida_final["pide_juego"] = True
                salida = {"ok": True, "nota": "El chat ya le muestra un buscador: pídele que elija el juego."}
            elif nombre == "sugerencias_del_perfil":
                salida = _sugerencias_del_perfil(sugerencias, generos)
                if salida.get("sin_perfil"):
                    salida_final["pide_perfil"] = True
                else:
                    salida_final["sugerencias"] = [j["appid"] for j in salida["sugerencias_segun_tu_perfil"]]
            else:
                salida = herramientas.ejecutar(nombre, argumentos)
                paso = herramientas.paso_de(nombre, argumentos, salida)
                if paso not in salida_final["pasos"]:
                    salida_final["pasos"].append(paso)
                salida_final["appids"] |= herramientas.appids_de(salida)
                for juego in salida.get("juegos", []) if isinstance(salida.get("juegos"), list) else []:
                    if isinstance(juego, dict) and juego.get("appid") not in salida_final["orden"]:
                        salida_final["orden"].append(juego.get("appid"))
            conversacion.append({
                "role": "tool",
                "tool_call_id": llamada.id,
                "content": json.dumps(salida, ensure_ascii=False)[:4000],
            })

    return salida_final


def _contexto_del_catalogo(generos: list[str] | None = None) -> str:
    """Lo que Nia sabe sin abrir ningún juego: el tamaño del catálogo, sus bandas y, si los
    hay, los géneros que declaró quien pregunta."""
    ref = _referencias_del_catalogo()
    bandas = " / ".join(f"{n} {b}" for b, n in ref["bandas"].items())
    texto = (
        f"No hay ningún juego abierto: quien pregunta habla del catálogo entero, que son"
        f" {ref['juegos']} juegos de Steam, por riesgo de arrepentimiento: {bandas}. Lo normal del precio es"
        f" {pesos_hablados(ref['precio_mediano'])} (la mediana de los {ref['de_pago_con_precio']} de pago con precio) y la nota"
        f" promedio es {ref['nota_promedio']} entre los {ref['con_nota']} que tienen nota. Para cualquier dato concreto,"
        " usa las herramientas: no sabes de memoria qué juegos hay."
    )
    declarados = generos_declarados(generos)
    if declarados:
        texto += (f" Quien pregunta declaró estos géneros: {', '.join(declarados)}. Úsalos para decir cuáles coinciden"
                  " con un juego (sus géneros vienen en las herramientas), nunca como porcentaje; no cambian el riesgo.")
    return texto


# "Hay 7 juegos gratis", "son 3": cuántos dice la respuesta que cumplen.
_CANTIDAD = re.compile(r"\b(?:hay|son|encontre|tengo)\s+(\d{1,3})\b|\b(\d{1,3})\s+(?:juegos|gratuitos|gratis|titulos)\b")


def _juegos_para_tarjeta(
    texto: str, permitidos: set[int], appid: int | None, orden: list[int] | None = None
) -> list[int]:
    """Los appids que la respuesta puede pintar como tarjeta.

    Dos filtros, y los dos hacen falta: el juego tiene que estar en el catálogo y tiene
    que habérselo devuelto una herramienta en este turno. Lo que el modelo nombre de
    memoria no se pinta, aunque exista.

    Si la respuesta dice cuántos son («hay 7 gratis») y la herramienta los devolvió todos,
    salen todos aunque alguno venga nombrado de otra forma («Los Sims 4»): antes decía 7 y
    pintaba 6."""
    nombrados = juegos_del_catalogo_mencionados(texto, appid or 0)
    por_nombre = {j.nombre: j.appid for j in catalogo.buscar()}
    appids = [a for a in (por_nombre[n] for n in nombrados if n in por_nombre) if a in permitidos]
    cantidad = next((int(g) for m in _CANTIDAD.finditer(_sin_acentos(texto)) for g in m.groups() if g), None)
    disponibles = [a for a in (orden or []) if a in permitidos and a != appid]
    if cantidad and len(appids) < cantidad <= len(disponibles):
        appids += [a for a in disponibles if a not in appids][: cantidad - len(appids)]
    return appids


def _con_constancia(salida: dict, appid: int | None, usuario: str, pregunta: str) -> dict:
    """Le pone id a la respuesta y la deja anotada, para que su voto tenga a qué apuntar.

    Si la base de valoraciones falla, la respuesta se entrega igual y solo se pierde la
    posibilidad de votarla: no contestar por no poder anotar sería el peor intercambio."""
    salida["id"] = str(uuid.uuid4())
    salida["version_prompt"] = VERSION_PROMPT if salida["modo"] == "openai" else VERSION_REGLAS
    salida.setdefault("pasos", [])
    salida.setdefault("juegos", [])
    try:
        valoraciones.registrar_respuesta_nia(
            id_respuesta=salida["id"],
            usuario=usuario,
            appid=appid,
            pregunta=sin_datos_personales(pregunta),
            respuesta=salida["respuesta"],
            modo=salida["modo"],
            modelo=salida["modelo"],
            version_prompt=salida["version_prompt"],
        )
    except Exception as exc:
        logger.warning("no se pudo anotar la respuesta de Nia (%s): no se podrá votar", type(exc).__name__)
    return salida


def responder(
    appid: int | None,
    mensajes: list[MensajeChat],
    usuario: str,
    sugerencias: list[SugerenciaNia] | None = None,
    _perfil: PerfilJugador | None = None,
    generos: list[str] | None = None,
) -> dict:
    """Con appid, Nia habla de ese juego; sin él, del catálogo entero con sus herramientas.

    El perfil llega porque /nia lo recibe desde siempre, pero no entra al contexto: el
    riesgo es del título. Lo que sí puede llegar son las sugerencias que el navegador ya
    calculó con el perfil, que Nia solo enseña si se las piden, y los géneros declarados,
    para decir cuáles coinciden con un juego («¿encaja conmigo?»). Ninguno se registra."""
    sugerencias = sugerencias or []
    generos = generos or []
    datos = contexto(appid) if appid is not None else None
    ultima = next((m.contenido for m in reversed(mensajes) if m.rol == "usuario"), "")

    # "¿Por qué tiene ese riesgo?" sin juego: en los dos modos se pide antes de contestar,
    # para que el modelo no adivine de cuál se habla.
    if reglas.necesita_juego(ultima, mensajes, appid):
        pedido = reglas.responder(datos, appid, mensajes, sugerencias, generos)
        # Sin modelo de por medio: no se marca «Con IA», y pedir el juego no es salirse del tema.
        modo = "reglas" if configuracion.hay_openai else "demostracion"
        return _con_constancia(
            {
                "respuesta": pedido["texto"],
                "modo": modo,
                "modelo": None,
                "aviso": None if modo == "reglas" else _AVISO_DEMOSTRACION,
                "pide_juego": True,
                "fuera_de_tema": False,
                "oferta": pedido["oferta"],
            },
            appid, usuario, ultima,
        )

    if not configuracion.hay_openai:
        logger.info("sin clave de OpenAI configurada; appid=%s responde en modo demostración", appid)
        return _de_reglas(datos, appid, mensajes, sugerencias, usuario, ultima, _AVISO_DEMOSTRACION, generos=generos)

    if _por_reglas_aunque_haya_modelo(datos, appid, mensajes, sugerencias, ultima, generos):
        return _de_reglas(datos, appid, mensajes, sugerencias, usuario, ultima, None, modo="reglas", generos=generos)

    try:
        salida = _preguntar_a_openai(
            datos, mensajes, juegos_del_catalogo_mencionados(ultima, appid or 0), sugerencias, generos
        )
        if salida["texto"] or salida["pide_juego"] or salida["pide_perfil"]:
            texto = ajustar_largo(sin_descargo(pulir(salida["texto"]), ultima)) or (
                "¿De qué juego hablamos? 👀 Búscalo aquí y te lo explico." if salida["pide_juego"]
                else INVITA_AL_PERFIL
            )
            juegos = _juegos_para_tarjeta(texto, salida["appids"], appid, salida["orden"])
            if juegos:
                texto = sin_riesgos_enumerados(texto)
            texto, oferta = con_cierre_cumplible(texto, appid, juegos, salida)
            return _con_constancia(
                {
                    "respuesta": texto,
                    "modo": "openai",
                    "modelo": configuracion.nexplay_modelo_nia,
                    "aviso": None,
                    "pasos": salida["pasos"],
                    "juegos": juegos,
                    "sugerencias": salida["sugerencias"],
                    "pide_juego": salida["pide_juego"],
                    "pide_perfil": salida["pide_perfil"],
                    # Lo que no es de juegos ya se contestó con reglas antes de llegar aquí: una
                    # respuesta del modelo no lleva el aviso de tema. Las reglas no entienden
                    # «¿Cyberpunk vale lo que cuesta?» y lo marcaban fuera de tema.
                    "fuera_de_tema": False,
                    "oferta": oferta,
                },
                appid, usuario, ultima,
            )
        logger.warning(
            "OpenAI devolvió una respuesta vacía para appid=%s (con un modelo de razonamiento, el tope de tokens"
            " se pudo ir en pensar: ver NEXPLAY_NIA_RAZONAMIENTO); se usa el modo demostración",
            appid,
        )
    except Exception as exc:  # falla de red, clave inválida, modelo inexistente, sin paquete
        # El mensaje real, no solo el tipo: sin él no se puede saber por qué cayó. Se le
        # quita cualquier cosa con forma de clave antes de escribirlo.
        logger.warning(
            "falló la llamada a OpenAI para appid=%s (%s: %s); se usa el modo demostración",
            appid, type(exc).__name__, _sin_claves(str(exc)),
        )

    return _de_reglas(
        datos, appid, mensajes, sugerencias, usuario, ultima,
        "No se pudo usar el modelo configurado; esta respuesta se armó con reglas sobre los datos.",
        generos=generos,
    )


def con_cierre_cumplible(texto: str, appid: int | None, juegos: list[int], salida: dict) -> tuple[str, dict]:
    """La pregunta final del modelo se cambia por una oferta que las reglas saben cumplir: el
    modelo ofrecía «¿Te cuento sus otros puntos débiles?» y el «sí» acababa en «Eso no lo sé».

    Con un juego, sus reseñas (o su riesgo, si ya habló de reseñas); con dos o más tarjetas,
    ordenarlas por riesgo; sin juego, cómo se calcula el riesgo. Si pidió el juego o el perfil,
    eso."""
    # Fuera la pregunta final, desde su último «¿», con los emojis que la acompañan.
    cuerpo = texto.strip()
    if EMOJI.sub("", cuerpo).rstrip().endswith("?"):
        inicio = cuerpo.rfind("¿")
        cuerpo = cuerpo[:inicio] if inicio >= 0 else " ".join(_oraciones(cuerpo)[:-1])
        cuerpo = cuerpo.rstrip(" ,;:")
    uno = juegos[0] if len(juegos) == 1 else appid if appid is not None and not juegos else None
    sugeridos = salida.get("sugerencias") or []
    if salida.get("pide_juego"):
        oferta, cierre = {"intencion": "elegir_juego", "juegos": []}, "¿De qué juego te cuento?"
    elif salida.get("pide_perfil"):
        oferta, cierre = {"intencion": "crear_perfil", "juegos": []}, "Toma un minuto, ¿lo armamos?"
    elif uno is not None:
        nombre = None if uno == appid else catalogo.obtener(uno).nombre
        if re.search(r"reseñ|queja", cuerpo, re.IGNORECASE):
            oferta = {"intencion": "riesgo", "juegos": [uno]}
            cierre = f"¿Te cuento por qué {nombre} tiene ese riesgo?" if nombre else "¿Te cuento por qué tiene ese riesgo?"
        else:
            oferta = {"intencion": "resenas", "juegos": [uno]}
            cierre = f"¿Te cuento qué dicen las reseñas de {nombre}?" if nombre else "¿Te cuento qué dicen sus reseñas?"
    elif len(juegos) >= 2 or len(sugeridos) >= 2:
        oferta = {"intencion": "ordenar", "juegos": (juegos or sugeridos)[:8], "criterio": "riesgo"}
        cierre = "¿Los ordeno por riesgo?"
    else:
        oferta, cierre = {"intencion": "como_se_calcula", "juegos": []}, "¿Te cuento cómo se calcula el riesgo?"
    if not EMOJI.search(cuerpo):
        cuerpo = f"{cuerpo} 🎮".strip()
    return ajustar_largo(f"{cuerpo} {cierre}"), oferta


_AVISO_DEMOSTRACION = (
    "Modo demostración: respuesta armada con reglas sobre los datos del catálogo, sin modelo de lenguaje."
)


def _por_reglas_aunque_haya_modelo(
    datos: dict | None,
    appid: int | None,
    mensajes: list[MensajeChat],
    sugerencias: list[SugerenciaNia],
    ultima: str,
    generos: list[str] | None = None,
) -> bool:
    """Lo que se contesta con reglas aunque haya modelo, porque la respuesta tiene que ser
    siempre la misma y el prompt no lo garantiza: el resumen (de todas las respuestas del
    hilo, no de la última), "el mejor" (no se corona a nadie), lo que no es de juegos (el
    modelo contestaba la trivia), «¿qué tal X?» o «¿se parece a X?» con un X que no está en
    el catálogo (el modelo a veces se saltaba el «no está en este catálogo») y «¿por qué tiene
    ese riesgo?» con un juego abierto (el modelo se saltaba el aviso, el descargo o el factor
    que más aporta)."""
    return (
        reglas.responde_al_seguimiento(ultima, mensajes)
        or reglas.responde_de_esos(ultima, mensajes)
        or reglas.pide_resumen(ultima)
        or reglas.pide_que_significa_la_senal(ultima)
        or reglas.pide_como_se_calcula(ultima)
        or reglas.pide_de_donde_salen(ultima)
        or reglas.pide_comentarios(ultima)
        or reglas.pide_eleccion(ultima)
        or reglas.pide_aspecto(ultima, appid)
        or reglas.pide_explicar_el_riesgo(ultima, datos)
        or reglas.pide_el_mejor(ultima)
        or (reglas.sin_relacion_con_juegos(ultima) and reglas.es_fuera_de_tema(datos, appid, mensajes, sugerencias, generos))
        or reglas.fuera_del_catalogo(ultima, datos) is not None
    )


_PREGUNTA_POR_LA_SENAL = (
    "que significa", "que es la senal", "que es esa senal", "que quiere decir", "proxy", "como se calcula",
    "de donde sale", "metodologia",
)
# Fin de oración: el punto seguido de mayúscula, ¿ o ¡, o un emoji. «(93 vs. 87)» no corta.
_FIN_DE_ORACION = re.compile(
    r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\U0001F000-\U0001FAFF])|(?<=[\U0001F000-\U0001FAFF\u2600-\u27BF\ufe0f])\s+"
)


def _oraciones(texto: str) -> list[str]:
    return [o for o in _FIN_DE_ORACION.split(texto.strip()) if o]


# Una oración que es el descargo y nada más: empieza hablando de la señal, no de un juego, y
# dice de dónde sale o que no confirma el arrepentimiento. «Llegas a 2 horas en 2 sesiones»
# o «Steam devuelve el dinero si juegas menos de 2 horas» no empiezan así y se quedan.
_ABRE_COMO_DESCARGO = re.compile(
    r"^(?:ojo[:,]?\s+|recuerda(?:\s+que)?\s+|ten en cuenta que\s+)?"
    r"(?:(?:esa|la|esta) señal\b|es una señal\b|el riesgo se basa en reseñas\b|no (?:sabemos|se sabe|s[eé]) si\b"
    r"|no (?:confirma|prueba)\b)",
    re.IGNORECASE,
)
_HABLA_DE_LA_SENAL = re.compile(
    r"proxy|arrepint|primeras 2 horas|menos de 2 horas|120 minutos|reseñas negativas|no recomend", re.IGNORECASE
)


def es_descargo(oracion: str) -> bool:
    limpia = oracion.strip(" ¡¿")
    return bool(_ABRE_COMO_DESCARGO.match(limpia)) and bool(_HABLA_DE_LA_SENAL.search(limpia))


def pregunta_por_la_senal(pregunta: str) -> bool:
    return reglas._dice(_sin_acentos(pregunta), *_PREGUNTA_POR_LA_SENAL)


def sin_descargo(texto: str, ultima: str) -> str:
    """Quita el descargo de la señal, que ya está fijo arriba del chat: solo oraciones
    completas que son el descargo, nunca un pedazo de otra. Si preguntan qué significa, se
    queda."""
    if pregunta_por_la_senal(ultima):
        return texto
    quedan = [o for o in _oraciones(texto) if not es_descargo(o)]
    return " ".join(quedan) if quedan else texto


MAXIMO_PALABRAS = 60


def ajustar_largo(texto: str, maximo: int = MAXIMO_PALABRAS) -> str:
    """Hasta `maximo` palabras sin perder la pregunta del final: se quitan oraciones de en
    medio, no se corta el remate."""
    if palabras(texto) <= maximo:
        return texto
    oraciones = _oraciones(texto)
    ultima = oraciones[-1]
    cierre = ultima if EMOJI.sub("", ultima).rstrip().endswith("?") else ""
    cuerpo = oraciones[:-1] if cierre else oraciones
    elegidas: list[str] = []
    for oracion in cuerpo:
        if palabras(" ".join([*elegidas, oracion, cierre])) > maximo:
            break
        elegidas.append(oracion)
    if not elegidas:
        cabe = max(5, maximo - palabras(cierre))
        elegidas = [" ".join(cuerpo[0].split()[:cabe]).rstrip(",;:") + "…"]
    return " ".join([*elegidas, cierre]).strip()


def _de_reglas(
    datos: dict | None,
    appid: int | None,
    mensajes: list[MensajeChat],
    sugerencias: list[SugerenciaNia],
    usuario: str,
    ultima: str,
    aviso: str | None,
    modo: str = "demostracion",
    generos: list[str] | None = None,
) -> dict:
    resultado = reglas.responder(datos, appid, mensajes, sugerencias, generos)
    return _con_constancia(
        {
            "respuesta": pulir(resultado["texto"]),
            "modo": modo,
            "modelo": None,
            "aviso": aviso,
            "juegos": resultado["juegos"],
            "sugerencias": resultado["sugerencias"],
            "pide_juego": resultado["pide_juego"],
            "pide_perfil": resultado["pide_perfil"],
            "fuera_de_tema": resultado.get("fuera_de_tema", False),
            "oferta": resultado["oferta"],
        },
        appid, usuario, ultima,
    )
