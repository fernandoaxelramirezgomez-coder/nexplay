"""Qué es cada columna de las bases y cada variable del modelo, en una frase corta.

Un solo diccionario para los notebooks: el 00 lo pone junto al esquema de las tablas (`exploracion.esquema`) y
el 01 lo muestra como la tabla de variables de su sección 5. Las variables salen de `construir_features`, así
que la tabla no puede listar una que el código ya no arma."""

import pandas as pd

from entrenar_baseline import construir_features

QUE_ES = "qué es / para qué sirve"

# (tabla, columna) → qué es. `descargado_en` está en las dos tablas y no significa lo mismo.
COLUMNAS = {
    ("resenas", "recommendationid"): "Id único de la reseña en Steam",
    ("resenas", "appid"): "Id del juego; une la reseña con su juego",
    ("resenas", "num_games_owned"): "Juegos en la biblioteca del autor; 0 = perfil privado",
    ("resenas", "num_reviews"): "Reseñas escritas por el autor; posterior a la compra",
    ("resenas", "playtime_forever"): "Minutos jugados en total hasta la descarga",
    ("resenas", "playtime_last_two_weeks"): "Minutos jugados en las dos semanas antes de descargar",
    ("resenas", "playtime_at_review"): "Minutos jugados al reseñar; define la señal (< 120)",
    ("resenas", "last_played"): "Última vez que el autor jugó, como marca de tiempo",
    ("resenas", "idioma"): "Idioma que reporta Steam; la ingesta pidió inglés",
    ("resenas", "texto"): "Texto de la reseña; lo leen los modelos de texto",
    ("resenas", "timestamp_created"): "Cuándo se publicó la reseña, como marca de tiempo",
    ("resenas", "timestamp_updated"): "Cuándo se editó la reseña por última vez",
    ("resenas", "voted_up"): "Pulgar: 1 la recomienda, 0 no; define la señal",
    ("resenas", "votes_up"): "Votos de «útil» que recibió la reseña",
    ("resenas", "votes_funny"): "Votos de «gracioso» que recibió la reseña",
    ("resenas", "weighted_vote_score"): "Puntaje de utilidad que Steam calcula para la reseña",
    ("resenas", "comment_count"): "Comentarios que recibió la reseña en Steam",
    ("resenas", "steam_purchase"): "Si el autor compró el juego en Steam",
    ("resenas", "received_for_free"): "Si el autor recibió el juego gratis",
    ("resenas", "written_during_early_access"): "Si se escribió durante el acceso anticipado",
    ("resenas", "descargado_en"): "Cuándo la ingesta descargó esta reseña",
    ("juegos", "appid"): "Id del juego en Steam; llave de la tabla",
    ("juegos", "nombre"): "Nombre del juego como aparece en la tienda",
    ("juegos", "tipo"): "Tipo de producto en Steam; aquí siempre «game»",
    ("juegos", "fecha_lanzamiento"): "Fecha de lanzamiento que muestra la tienda",
    ("juegos", "proximamente"): "Si la tienda lo marca como «próximamente»",
    ("juegos", "es_gratis"): "Si el juego es gratuito; entra al modelo",
    ("juegos", "precio_inicial"): "Precio sin descuento, en centavos de peso",
    ("juegos", "precio_final"): "Precio con descuento al corte; entra al modelo",
    ("juegos", "descuento"): "Descuento al corte de datos, en %; entra al modelo",
    ("juegos", "moneda"): "Moneda del precio; pesos mexicanos (MXN)",
    ("juegos", "generos"): "Géneros que asigna Steam; sirven para la afinidad",
    ("juegos", "categorias"): "Categorías de Steam: un jugador, cooperativo, logros…",
    ("juegos", "desarrolladores"): "Estudios que desarrollaron el juego",
    ("juegos", "editores"): "Empresas que publicaron el juego",
    ("juegos", "metacritic"): "Nota de la crítica en Metacritic; algunos no tienen",
    ("juegos", "soporta_windows"): "Si corre en Windows, según la tienda",
    ("juegos", "soporta_mac"): "Si corre en macOS, según la tienda",
    ("juegos", "soporta_linux"): "Si corre en Linux, según la tienda",
    ("juegos", "descripcion_corta"): "Descripción breve de la tienda; la muestra la ficha",
    ("juegos", "descargado_en"): "Cuándo se consultó la tienda; fecha del precio",
}

# variable del modelo → (columna de la que sale, transformación, qué es)
VARIABLES = {
    "es_gratis": ("es_gratis", "0 o 1; si falta, 0", "Si el juego es gratuito, sin precio de entrada"),
    "log_precio_final": ("precio_final", "log(1 + precio); si falta, 0", "Precio al corte, en escala logarítmica"),
    "descuento": ("descuento", "en %; si falta, 0", "Descuento del día del corte de datos"),
    "metacritic_disponible": ("metacritic", "1 si hay nota, 0 si no", "Si la crítica cubrió el juego en Metacritic"),
    "metacritic": ("metacritic", "si falta, la mediana de data-v1", "Nota de la crítica, con la mediana si falta"),
    "log_num_games_owned": ("num_games_owned", "log(1 + juegos)", "Tamaño de la biblioteca de quien reseña"),
    "privacidad_perfil": ("num_games_owned", "1 si vale 0", "Perfil privado: Steam no muestra su biblioteca"),
    "log_num_reviews": ("num_reviews", "log(1 + reseñas)", "Cuántas reseñas ha escrito el autor"),
    "steam_purchase": ("steam_purchase", "0 o 1; si falta, 0", "Si el autor compró el juego en Steam"),
    "received_for_free": ("received_for_free", "0 o 1; si falta, 0", "Si el autor recibió el juego gratis"),
    "written_during_early_access": ("written_during_early_access", "0 o 1; si falta, 0",
                                    "Si se escribió durante el acceso anticipado"),
}

CONJUNTOS = ("juego", "compra", "completo")
_COLUMNAS_CRUDAS = ("appid", "num_games_owned", "num_reviews", "steam_purchase", "received_for_free",
                    "written_during_early_access", "playtime_at_review", "voted_up", "es_gratis", "precio_final",
                    "descuento", "metacritic")


def descripciones(tabla: str, columnas) -> pd.Series:
    """Qué es cada columna de `tabla`; vacío si el diccionario no la tiene (el notebook lo comprueba)."""
    return pd.Series([COLUMNAS.get((tabla, columna), "") for columna in columnas], index=list(columnas), name=QUE_ES)


def tabla_de_variables() -> pd.DataFrame:
    """Cada variable que arma `construir_features`, de qué columna sale, cómo se transforma, qué es y en qué
    conjuntos está. El de producción es 'juego'. Los conjuntos se leen del código con una fila de prueba."""
    prueba = pd.DataFrame([dict.fromkeys(_COLUMNAS_CRUDAS, 1)])
    en_conjunto = {conjunto: list(construir_features(prueba, conjunto)[0].columns) for conjunto in CONJUNTOS}
    orden = list(dict.fromkeys(v for conjunto in CONJUNTOS for v in en_conjunto[conjunto]))
    faltan = [v for v in orden if v not in VARIABLES]
    if faltan:
        raise KeyError(f"variables sin descripción en diccionario.VARIABLES: {faltan}")
    filas = []
    for variable in orden:
        columna, transformacion, que_es = VARIABLES[variable]
        filas.append({"variable": variable, "sale de": columna, "transformación": transformacion, QUE_ES: que_es,
                      **{conjunto: "✓" if variable in en_conjunto[conjunto] else "" for conjunto in CONJUNTOS}})
    return pd.DataFrame(filas).set_index("variable")
