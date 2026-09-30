"""El idioma real de cada reseña.

Steam etiqueta casi todas como inglés porque la ingesta pide language=english, pero una parte
está escrita en otro idioma. El modelo de embeddings (all-MiniLM-L6-v2) está entrenado para
inglés, así que hay que saber cuáles son."""

import re

import pandas as pd
from lingua import Language, LanguageDetectorBuilder

# Los idiomas más frecuentes en las reseñas de Steam. Con todos los de lingua, un texto corto
# en inglés se confunde con idiomas que casi no aparecen.
IDIOMAS = (
    Language.ENGLISH, Language.SPANISH, Language.PORTUGUESE, Language.RUSSIAN, Language.GERMAN,
    Language.FRENCH, Language.TURKISH, Language.POLISH, Language.CHINESE, Language.JAPANESE,
    Language.KOREAN, Language.ITALIAN, Language.UKRAINIAN, Language.DUTCH, Language.SWEDISH,
    Language.CZECH, Language.HUNGARIAN, Language.FINNISH, Language.DANISH, Language.ROMANIAN,
    Language.INDONESIAN, Language.VIETNAMESE, Language.THAI, Language.ARABIC, Language.GREEK,
    Language.BOKMAL, Language.TAGALOG,
)
# Solo se decide un idioma si le saca esta distancia al segundo más probable. Con 0.25,
# «yes yes yes yeeeees» salía finés y «bow bow bow», polaco; con 0.5 lo dudoso queda
# indeterminado. Medido en data-v1.
DISTANCIA_MINIMA = 0.5
# Con menos letras no hay de dónde decidir: «gg», «10/10».
MINIMO_LETRAS = 20
INDETERMINADO = "indeterminado"
# Con `re` de Python: en pandas 3 las expresiones de `str` van por Arrow, donde \w es solo ASCII.
_LETRA = re.compile(r"[^\W\d_]")

_detector = None


def _detector_de_idioma():
    global _detector
    if _detector is None:
        _detector = (
            LanguageDetectorBuilder.from_languages(*IDIOMAS)
            .with_minimum_relative_distance(DISTANCIA_MINIMA)
            .with_preloaded_language_models()
            .build()
        )
    return _detector


def idioma_de(textos: pd.Series) -> pd.Series:
    """El idioma de cada texto en minúsculas ('english', 'spanish'…) o 'indeterminado', con el
    mismo índice que `textos`."""
    textos = textos.fillna("").str.strip()
    decidibles = textos[textos.map(lambda texto: len(_LETRA.findall(texto))) >= MINIMO_LETRAS]
    idiomas = pd.Series(INDETERMINADO, index=textos.index)
    detectados = _detector_de_idioma().detect_languages_in_parallel_of(decidibles.tolist())
    idiomas.loc[decidibles.index] = [idioma.name.lower() if idioma else INDETERMINADO for idioma in detectados]
    return idiomas
