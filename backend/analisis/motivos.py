"""Las palabras clave de los motivos de arrepentimiento temprano, en un módulo sin efectos al
importar.

api/scoring.py las usa para /explicacion y /panorama. El notebook de exploración y los modelos
de texto las usan sin cargar la API, que al importarse lee modelo/nexplay.pkl."""

import re

import pandas as pd

# Palabras clave en inglés: la ingesta filtra language=english (ver
# ingesta_steam.py), así que es lo que hay en el texto de las reseñas.
PALABRAS_CLAVE_POR_CATEGORIA: dict[str, list[str]] = {
    "rendimiento": [
        "fps", "lag", "laggy", "lagging", "stutter", "stuttering", "freeze", "freezing",
        "freezes", "crash", "crashes", "crashing", "crashed", "optimize", "optimise",
        "optimization", "optimisation", "framerate", "frame rate", "sluggish",
        "memory leak", "loading times", "load times",
    ],
    "bugs": [
        "bug", "bugs", "buggy", "glitch", "glitches", "glitchy", "broken", "game-breaking",
        "gamebreaking", "softlock", "softlocked", "unplayable",
    ],
    "dificultad": [
        "difficult", "difficulty", "hard", "hardcore", "frustrating", "frustrated",
        "unfair", "punishing", "grind", "grindy", "grinding", "brutal",
    ],
    "controles": [
        "controls", "controller", "clunky", "unresponsive", "aiming", "aim assist",
        "keybind", "keybinding", "key bindings", "input lag", "camera controls",
    ],
    "contenido": [
        "content", "short", "shallow", "repetitive", "repetition", "empty", "lacking",
        "incomplete", "unfinished", "dlc", "pay to win", "filler",
    ],
    # "refund", "waste of money" y "not worth" se descartaron: son insatisfaccion
    # generica (aparecen en cualquier resena Y=1 sin importar el motivo), no
    # queja de costo especificamente.
    "precio": [
        "price", "priced", "pricing", "cost", "costly", "overpriced", "expensive",
        "paywall", "cash grab", "microtransaction", "microtransactions",
    ],
}


def _compilar_patrones() -> dict[str, re.Pattern]:
    return {
        categoria: re.compile(
            r"\b(?:" + "|".join(re.escape(palabra) for palabra in palabras) + r")\b",
            re.IGNORECASE,
        )
        for categoria, palabras in PALABRAS_CLAVE_POR_CATEGORIA.items()
    }


PATRONES_MOTIVOS = _compilar_patrones()


def categorias_de(texto: str) -> list[str]:
    """Las categorías que menciona un texto; una reseña puede caer en varias o en ninguna."""
    return [categoria for categoria, patron in PATRONES_MOTIVOS.items() if patron.search(texto)]


def tabla_de_motivos(textos: pd.Series) -> pd.DataFrame:
    """Una columna booleana por categoría, con el mismo índice que `textos`."""
    textos = textos.fillna("")
    return pd.DataFrame({categoria: textos.str.contains(patron) for categoria, patron in PATRONES_MOTIVOS.items()})
