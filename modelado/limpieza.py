"""La limpieza del texto de las reseñas para los modelos de texto (Parte A y Parte B).

Cada regla es una función que recibe las reseñas y devuelve las que siguen más un `Paso` para
la bitácora: qué regla, cuántas filas había, cuántas quedan y por qué. Solo dos reglas quitan
filas (duplicados de 8+ palabras y vacías); las demás marcan una columna, para no cambiar la
población que se estudia.

No se aplica al modelo de riesgo: ese se entrena con data-v1 tal cual, y verificar_bandas.py
compara contra esas bandas."""

import hashlib
import re
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from idioma import INDETERMINADO, idioma_de

# Menos que esto no alcanza para un motivo: «good», «10/10», «yes».
MINIMO_PALABRAS = 3
# Desde este largo, dos textos idénticos son una copia (memes, plantillas, la misma reseña en
# varios juegos). Más cortos, coinciden porque mucha gente escribe «good game».
PALABRAS_DE_UNA_COPIA = 8
NEGACIONES = frozenset({"not", "no", "nor", "never", "nothing", "none", "nobody", "nowhere", "neither", "cannot", "without"})
STOPWORDS_SIN_NEGACIONES = frozenset(ENGLISH_STOP_WORDS - NEGACIONES)

# La reseña plantilla de Steam: casillas marcadas («☐ Bad ☑ Good») o encabezados «---{ Graphics }---».
_CASILLAS = r"[☐☑☒□■✓✔✗✘✅❌]"
_CASILLA = re.compile(_CASILLAS)
_ENCABEZADO = re.compile(r"---\s*\{")
_MINIMO_CASILLAS = 3

_BBCODE = re.compile(r"\[/?[a-z0-9*]+(?:=[^\]]*)?\]", re.IGNORECASE)
_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
# Las contracciones se abren para que la negación quede como palabra: «don't» → «do not».
# Sin apóstrofo también, porque en Steam casi nadie lo escribe: «dont», «cant».
_IRREGULARES = {"won't": "will not", "can't": "can not", "shan't": "shall not", "ain't": "is not",
                "wont": "will not", "cant": "can not", "aint": "is not"}
_SIN_APOSTROFO = re.compile(r"\b(do|does|did|is|are|was|were|would|could|should|have|has|had|must|need)nt\b")


@dataclass
class Paso:
    regla: str
    motivo: str
    antes: int
    despues: int
    afectadas: pd.DataFrame

    def fila(self) -> dict:
        return {"regla": self.regla, "filas antes": self.antes, "filas después": self.despues,
                "afectadas": len(self.afectadas), "motivo": self.motivo}


def bitacora(pasos: list[Paso]) -> pd.DataFrame:
    return pd.DataFrame([paso.fila() for paso in pasos])


def palabras(textos: pd.Series) -> pd.Series:
    return textos.fillna("").map(lambda texto: len(texto.split()))


def clave_de_copia(textos: pd.Series) -> pd.Series:
    return textos.fillna("").map(lambda texto: " ".join(texto.split()).casefold())


def quitar_duplicados_exactos(resenas: pd.DataFrame) -> tuple[pd.DataFrame, Paso]:
    """Texto idéntico de 8+ palabras, en el mismo juego o en otro: se queda la reseña más antigua."""
    orden = resenas.sort_values(["timestamp_created", "recommendationid"])
    clave = clave_de_copia(orden["texto"])
    copia = (palabras(orden["texto"]) >= PALABRAS_DE_UNA_COPIA) & clave.duplicated()
    quedan = resenas.loc[resenas.index.difference(orden.index[copia])]
    return quedan, Paso("quitar_duplicados_exactos", f"texto idéntico de {PALABRAS_DE_UNA_COPIA}+ palabras; queda la más antigua",
                        len(resenas), len(quedan), orden[copia])


def quitar_vacias(resenas: pd.DataFrame) -> tuple[pd.DataFrame, Paso]:
    vacia = resenas["texto"].fillna("").str.strip().eq("")
    return resenas[~vacia], Paso("quitar_vacias", "sin texto no hay nada que leer", len(resenas), int((~vacia).sum()), resenas[vacia])


def marcar_cortas(resenas: pd.DataFrame) -> tuple[pd.DataFrame, Paso]:
    """No quita filas: quitarlas cambiaría la población. La Parte B las deja fuera del conjunto de
    referencia; la Parte A entrena con todas y reporta por longitud."""
    marcadas = resenas.assign(es_corta=palabras(resenas["texto"]) < MINIMO_PALABRAS)
    return marcadas, Paso("marcar_cortas", f"menos de {MINIMO_PALABRAS} palabras; se marcan, no se quitan",
                          len(resenas), len(marcadas), marcadas[marcadas["es_corta"]])


def marcar_no_ingles(resenas: pd.DataFrame) -> tuple[pd.DataFrame, Paso]:
    idioma = idioma_de(resenas["texto"])
    marcadas = resenas.assign(idioma_detectado=idioma, no_ingles=~idioma.isin(["english", INDETERMINADO]))
    return marcadas, Paso("marcar_no_ingles", "otro idioma con confianza (lingua); se marcan, no se quitan",
                          len(resenas), len(marcadas), marcadas[marcadas["no_ingles"]])


def es_plantilla(textos: pd.Series) -> pd.Series:
    return textos.fillna("").map(
        lambda texto: len(_CASILLA.findall(texto)) >= _MINIMO_CASILLAS or _ENCABEZADO.search(texto) is not None
    ).astype(bool)


def marcar_plantillas(resenas: pd.DataFrame) -> tuple[pd.DataFrame, Paso]:
    marcadas = resenas.assign(es_plantilla=es_plantilla(resenas["texto"]))
    return marcadas, Paso("marcar_plantillas", "reseña plantilla («☐ Bad ☑ Good»); se marcan, no se quitan",
                          len(resenas), len(marcadas), marcadas[marcadas["es_plantilla"]])


def _normalizar(texto: str) -> str:
    t = texto.lower().replace("’", "'")
    t = _URL.sub(" ", _BBCODE.sub(" ", t))
    t = _CASILLA.sub(" ", t)
    for contraccion, abierta in _IRREGULARES.items():
        t = re.sub(rf"\b{re.escape(contraccion)}\b", abierta, t)
    t = _SIN_APOSTROFO.sub(r"\1 not", re.sub(r"n't\b", " not", t))
    t = re.sub(r"(?<!\w)'|'(?!\w)", " ", re.sub(r"[^\w\s']|_", " ", t))
    return " ".join(t.split())


def normalizar_texto(textos: pd.Series) -> pd.Series:
    """Minúsculas, sin BBCode, URLs ni casillas, y con las negaciones como palabra suelta.
    Conserva letras de cualquier alfabeto: una reseña en ruso no queda vacía.

    Con `re` de Python y no con `str.replace`: en pandas 3 el texto vive en Arrow y sus
    expresiones regulares tratan \\w como ASCII, así que el resultado (y la firma) cambiaría
    según la versión de pandas."""
    return textos.fillna("").map(_normalizar)


def normalizar(resenas: pd.DataFrame) -> tuple[pd.DataFrame, Paso]:
    normalizadas = resenas.assign(texto_norm=normalizar_texto(resenas["texto"]))
    cambian = normalizadas["texto_norm"] != normalizadas["texto"].fillna("").str.strip()
    return normalizadas, Paso("normalizar_texto", "minúsculas, sin BBCode ni URLs, negaciones como palabra; agrega texto_norm",
                              len(resenas), len(normalizadas), normalizadas[cambian])


REGLAS = (quitar_duplicados_exactos, quitar_vacias, marcar_cortas, marcar_no_ingles, marcar_plantillas, normalizar)


def limpiar(resenas: pd.DataFrame) -> tuple[pd.DataFrame, list[Paso]]:
    """Todas las reglas, en orden. La Parte A y la Parte B lo llaman igual sobre los 40."""
    pasos = []
    for regla in REGLAS:
        resenas, paso = regla(resenas)
        pasos.append(paso)
    return resenas, pasos


# La firma de limpiar(data-v1) con estas reglas y lingua 2.2.0. Si cambia una regla, cambia la firma:
# se actualiza aquí a propósito, y los modelos de texto (02) ven que su conjunto ya no es el mismo.
FIRMA_LIMPIO_DATA_V1 = "cb1e4b06fdf5a0264471f722446ac73bd06e28db30653819b8f1773c58e3f41e"

_COLUMNAS_DE_LA_FIRMA = ["recommendationid", "texto_norm", "es_corta", "no_ingles", "es_plantilla"]


def firma_del_conjunto(limpio: pd.DataFrame) -> str:
    """sha256 del contenido, no del archivo: los bytes de un parquet cambian con la versión de
    pyarrow aunque las filas sean las mismas."""
    filas = limpio[_COLUMNAS_DE_LA_FIRMA].sort_values("recommendationid").astype(str)
    return hashlib.sha256("\n".join(filas.agg("\t".join, axis=1)).encode()).hexdigest()
