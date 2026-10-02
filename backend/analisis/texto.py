"""Parte A de los modelos de texto: ¿el texto distingue las negativas tempranas de las tardías?

Lo que se mide y la regla de decisión están en docs/evidencia/modelos-texto-prerregistro.md, commiteado
antes de escribir este archivo (COMMIT_DEL_PRERREGISTRO). Aquí solo se calcula y se aplica esa regla: los
parámetros son los del prerregistro y no se ajustan.

Ninguno de estos modelos entra al score de riesgo ni a la imagen de Render: Y sale de esas mismas reseñas.

Uso, desde backend/:
    python analisis/texto.py      # escribe ../docs/evidencia/modelos-texto.json
"""

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import date
from importlib import metadata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# Corre desde analisis/: la raíz (despliegue) y modelado/ (lo importa exploracion) no están en sys.path.
sys.path[:0] = [str(RAIZ), str(RAIZ / "analisis"), str(RAIZ / "modelado")]

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score  # noqa: E402
from sklearn.naive_bayes import MultinomialNB  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from despliegue.utilidades import descargar_verificado  # noqa: E402
from entrenar_baseline import SEMILLA, splits_congelados  # noqa: E402
from exploracion import cargar_release, senal  # noqa: E402
from limpieza import FIRMA_LIMPIO_DATA_V1, firma_del_conjunto, limpiar  # noqa: E402

COMMIT_DEL_PRERREGISTRO = "6bbcea6"
PRERREGISTRO = "docs/evidencia/modelos-texto-prerregistro.md"
DATA_V1_SHA256 = "2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7"
MODELO_EMBEDDINGS = "sentence-transformers/all-MiniLM-L6-v2"
REVISION_EMBEDDINGS = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MAXIMO_DE_TOKENS = 256
REPLICAS = 2000

# §3 del prerregistro. Sobre texto_norm: minúsculas y sin puntuación («2.5h» queda «2 5h»).
MARCA_DURACION = "duracion"
CANTIDAD = (r"(?:\d+(?: \d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
            r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|hundreds of|thousands of|"
            r"hundred|thousand|a|an|half|few|couple of|couple|several|many|some)")
PATRON_DURACION = re.compile(
    rf"\b(?:{CANTIDAD} )?(?:seconds|minutes?|hours?|hrs?)\b"            # la unidad siempre, con su cantidad si la hay
    r"|\b\d+(?: \d+)? (?:secs?|second|mins?|h)\b"                       # abreviatura después de una cifra
    r"|\b\d+(?: \d+)?(?:hours?|hrs?|h|minutes?|mins?|seconds?|secs?)\b"  # cifra pegada a su unidad
)
# Lo que la máscara no debe dejar: si aparece, la máscara no cubre lo que el prerregistro dice.
UNIDAD_SUELTA = re.compile(r"\b(?:seconds|minutes?|hours?|hrs?)\b")
# §4: la palabra salió de §3.7 del 00 sobre estos mismos datos; la referencia es optimista.
PATRON_REFUND = re.compile(r"\brefund", re.IGNORECASE)

# Los candidatos a mejor modelo, del más simple al más complejo (§4 y §7). «refund» es referencia.
CANDIDATOS = ("tfidf_nb", "tfidf_lr", "minilm_lr")
NOMBRES = {"trivial": "Trivial", "refund": "Regla «refund»", "tfidf_nb": "TF-IDF + NB", "tfidf_lr": "TF-IDF + LR",
           "minilm_lr": "MiniLM + LR"}
SIN_MASCARA = ("tfidf_nb", "tfidf_lr")

# §7, copiadas del prerregistro: la conclusión no se redacta después de ver el resultado.
CONCLUSIONES = {
    1: "M no supera al trivial: es una moneda. Se descarta. Conclusión: las quejas tempranas no tienen lenguaje "
       "propio. La ficha presenta los motivos como quejas generales.",
    2: "M supera al trivial pero no a «refund»: un modelo no aporta más que una palabra. Se descarta el modelo y se "
       "documenta la regla. Lo que distingue a las tempranas es mencionar el reembolso, que es una acción y no un "
       "motivo. La ficha presenta los motivos como quejas generales.",
    3: "M supera a los dos. Se guarda el modelo más simple cuya diferencia pareada contra M incluye 0 y que supera "
       "al trivial y a «refund». Conclusión: las quejas tempranas tienen lenguaje propio, más allá de «refund». Los "
       "motivos de la ficha se pueden presentar como propios de ese momento.",
}


# --- Datos ----------------------------------------------------------------------------------

def enmascarar_duraciones(textos: pd.Series) -> pd.Series:
    """Cada duración se vuelve la palabra `duracion`, que dice que hubo una, no cuál. Con `re` de Python, como
    limpieza.py, para que el resultado no dependa de la versión de pandas."""
    return textos.map(lambda texto: " ".join(PATRON_DURACION.sub(f" {MARCA_DURACION} ", texto).split()))


def negativas_en_ingles(limpio: pd.DataFrame) -> pd.DataFrame:
    """Las negativas sin la marca de otro idioma, ordenadas por id, con la clase (temprana = 1), el texto
    normalizado del 00 y el texto enmascarado con el que se decide."""
    negativas = limpio[(limpio["voted_up"] == 0) & ~limpio["no_ingles"]].sort_values("recommendationid")
    return pd.DataFrame({
        "recommendationid": negativas["recommendationid"].to_numpy(),
        "appid": negativas["appid"].to_numpy(),
        "temprana": senal(negativas).astype(int).to_numpy(),
        "texto_norm": negativas["texto_norm"].to_numpy(),
        "texto_modelo": enmascarar_duraciones(negativas["texto_norm"]).to_numpy(),
    })


def folds_de(negativas: pd.DataFrame) -> np.ndarray:
    """El fold de validación de cada reseña en la partición congelada."""
    fold = np.full(len(negativas), -1)
    for numero, (_, validacion) in enumerate(splits_congelados(negativas["appid"])):
        fold[validacion] = numero
    return fold


def conteos_por_fold(negativas: pd.DataFrame, fold: np.ndarray) -> pd.DataFrame:
    tabla = negativas.assign(fold=fold).groupby("fold").agg(
        juegos=("appid", "nunique"), negativas=("temprana", "size"), tempranas=("temprana", "sum"))
    tabla["prevalencia"] = tabla["tempranas"] / tabla["negativas"]
    return tabla


# --- Modelos --------------------------------------------------------------------------------

def _tfidf() -> TfidfVectorizer:
    return TfidfVectorizer(ngram_range=(1, 2), min_df=5, sublinear_tf=True)


def _regresion() -> LogisticRegression:
    return LogisticRegression(class_weight="balanced", max_iter=2000, random_state=SEMILLA)


def modelos_tfidf() -> dict[str, Pipeline]:
    return {"tfidf_nb": Pipeline([("tfidf", _tfidf()), ("nb", MultinomialNB(alpha=1.0))]),
            "tfidf_lr": Pipeline([("tfidf", _tfidf()), ("lr", _regresion())])}


def modelo_embeddings() -> Pipeline:
    return Pipeline([("escalar", StandardScaler()), ("lr", _regresion())])


def regla_refund(textos: pd.Series) -> np.ndarray:
    return textos.map(lambda texto: PATRON_REFUND.search(texto) is not None).to_numpy(dtype=float)


def embeddings(textos: pd.Series, carpeta: Path) -> np.ndarray:
    """Los vectores de all-MiniLM-L6-v2, congelado, en CPU. Se guardan en `carpeta` con la huella de los
    textos y la revisión en el nombre: si cambia uno de los dos, se vuelven a calcular. sentence-transformers
    se importa aquí para que el resto del módulo no lo necesite."""
    huella = hashlib.sha256("\n".join(textos).encode()).hexdigest()[:12]
    cache = Path(carpeta) / f"minilm_{REVISION_EMBEDDINGS[:8]}_{huella}.npy"
    if cache.exists():
        return np.load(cache)

    from huggingface_hub.utils import disable_progress_bars
    from huggingface_hub.utils import logging as registro_hf
    from sentence_transformers import SentenceTransformer
    from transformers.utils import logging as registro_transformers

    # Sin barras de progreso ni avisos de token en la salida.
    disable_progress_bars()
    registro_hf.set_verbosity_error()
    registro_transformers.set_verbosity_error()
    registro_transformers.disable_progress_bar()

    modelo = SentenceTransformer(MODELO_EMBEDDINGS, revision=REVISION_EMBEDDINGS, device="cpu")
    assert modelo.max_seq_length == MAXIMO_DE_TOKENS, f"el modelo lee {modelo.max_seq_length} tokens, no {MAXIMO_DE_TOKENS}"
    vectores = modelo.encode(textos.tolist(), batch_size=64, show_progress_bar=False)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, vectores)
    return vectores


def scores_fuera_de_fold(modelo: Pipeline, X, y: np.ndarray, appid: pd.Series) -> np.ndarray:
    """El puntaje de cada reseña con el modelo ajustado sin su fold. Todo ajuste (vocabulario, idf, escalado,
    coeficientes) ocurre dentro del Pipeline, solo con el fold de entrenamiento."""
    filas = (lambda idx: X.iloc[idx]) if hasattr(X, "iloc") else (lambda idx: X[idx])
    scores = np.full(len(y), np.nan)
    for entrenamiento, validacion in splits_congelados(appid):
        ajustado = clone(modelo).fit(filas(entrenamiento), y[entrenamiento])
        scores[validacion] = ajustado.predict_proba(filas(validacion))[:, 1]
    return scores


# --- Métrica e intervalos ---------------------------------------------------------------------

def pr_auc_por_fold(y: np.ndarray, score: np.ndarray, fold: np.ndarray) -> np.ndarray:
    return np.array([average_precision_score(y[fold == k], score[fold == k]) for k in np.unique(fold)])


def bootstrap_pareado(y: np.ndarray, scores: dict[str, np.ndarray], fold: np.ndarray, appid: np.ndarray,
                      replicas: int = REPLICAS, semilla: int = SEMILLA) -> dict[str, np.ndarray]:
    """La media de los PR-AUC por fold de cada puntaje, en cada réplica. En cada réplica y en cada fold se
    sacan con reemplazo tantos juegos como tiene el fold, y cada reseña pesa las veces que salió su juego.
    Todos los puntajes se miden con los mismos juegos sorteados: las diferencias quedan pareadas.

    Solo entran las filas de los juegos sorteados (peso > 0): con peso 0, la curva tendría puntos sin
    reseñas."""
    generador = np.random.default_rng(semilla)
    numeros = np.unique(fold)
    juegos_del_fold = [np.unique(appid[fold == k]) for k in numeros]
    filas_del_juego = {juego: np.flatnonzero(appid == juego) for juego in np.unique(appid)}
    por_fold = {nombre: np.empty((replicas, len(numeros))) for nombre in scores}
    for replica in range(replicas):
        for k, juegos in enumerate(juegos_del_fold):
            sorteados, veces = np.unique(generador.choice(juegos, size=len(juegos), replace=True), return_counts=True)
            filas = np.concatenate([filas_del_juego[juego] for juego in sorteados])
            pesos = np.concatenate([np.full(len(filas_del_juego[juego]), v) for juego, v in zip(sorteados, veces)])
            for nombre, score in scores.items():
                por_fold[nombre][replica, k] = average_precision_score(y[filas], score[filas], sample_weight=pesos)
    return {nombre: matriz.mean(axis=1) for nombre, matriz in por_fold.items()}


def intervalo(valores: np.ndarray) -> tuple[float, float]:
    """IC del 95 % por percentiles."""
    bajo, alto = np.percentile(valores, [2.5, 97.5])
    return float(bajo), float(alto)


def resumen(por_fold: dict[str, np.ndarray], replicas: dict[str, np.ndarray]) -> pd.DataFrame:
    """Por modelo: la media de los folds y su IC, el cociente contra el trivial y la diferencia pareada contra
    «refund», cada uno con su IC."""
    trivial = por_fold["trivial"].mean()
    filas = {}
    for nombre in ("trivial", "refund", *CANDIDATOS):
        media = por_fold[nombre].mean()
        fila = {"PR-AUC media": media, "std entre folds": por_fold[nombre].std()}
        fila["IC media"] = intervalo(replicas[nombre])
        fila["cociente"] = media / trivial
        fila["IC cociente"] = intervalo(replicas[nombre] / replicas["trivial"])
        if nombre in CANDIDATOS:
            fila["− refund"] = media - por_fold["refund"].mean()
            fila["IC − refund"] = intervalo(replicas[nombre] - replicas["refund"])
        filas[nombre] = fila
    return pd.DataFrame.from_dict(filas, orient="index")


def decidir(por_fold: dict[str, np.ndarray], replicas: dict[str, np.ndarray]) -> dict:
    """La regla de §7 del prerregistro, tal cual."""
    def supera_trivial(nombre: str) -> bool:
        return intervalo(replicas[nombre] / replicas["trivial"])[0] > 1

    def supera_refund(nombre: str) -> bool:
        return intervalo(replicas[nombre] - replicas["refund"])[0] > 0

    mejor = max(CANDIDATOS, key=lambda nombre: por_fold[nombre].mean())
    contra_mejor = {nombre: intervalo(replicas[mejor] - replicas[nombre]) for nombre in CANDIDATOS}
    if not supera_trivial(mejor):
        rama, elegido = 1, None
    elif not supera_refund(mejor):
        rama, elegido = 2, None
    else:
        rama = 3
        elegido = next(nombre for nombre in CANDIDATOS
                       if contra_mejor[nombre][0] <= 0 <= contra_mejor[nombre][1]
                       and supera_trivial(nombre) and supera_refund(nombre))
    return {"mejor": mejor, "supera_trivial": supera_trivial(mejor), "supera_refund": supera_refund(mejor),
            "mejor_menos_cada_uno": contra_mejor, "rama": rama, "elegido": elegido, "conclusion": CONCLUSIONES[rama]}


def sensibilidad(por_fold: dict[str, np.ndarray], replicas: dict[str, np.ndarray]) -> pd.DataFrame:
    """Cuánto ganaban NB y TF-IDF + LR por leer la duración: «sin máscara − con máscara», pareada. No entra a
    la regla. Los puntajes sin máscara llevan el sufijo `_sin`."""
    filas = {}
    for nombre in SIN_MASCARA:
        con, sin = por_fold[nombre].mean(), por_fold[f"{nombre}_sin"].mean()
        filas[nombre] = {"con máscara": con, "sin máscara": sin, "ganancia": sin - con,
                         "IC ganancia": intervalo(replicas[f"{nombre}_sin"] - replicas[nombre])}
    return pd.DataFrame.from_dict(filas, orient="index")


# --- Registro -------------------------------------------------------------------------------

def _redondear(valor):
    if isinstance(valor, dict):
        return {str(k): _redondear(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple, np.ndarray)):
        return [_redondear(v) for v in valor]
    if isinstance(valor, (float, np.floating)):
        return round(float(valor), 6)
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.bool_):
        return bool(valor)
    return valor


def entorno() -> dict:
    paquetes = ("numpy", "pandas", "scikit-learn", "torch", "sentence-transformers", "transformers",
                "lingua-language-detector")
    return {"python": platform.python_version(), **{p: metadata.version(p) for p in paquetes}}


def registro(negativas: pd.DataFrame, conteos: pd.DataFrame, firma: str, por_fold: dict[str, np.ndarray],
             replicas: dict[str, np.ndarray], tabla: pd.DataFrame, sens: pd.DataFrame, decision: dict,
             codigo: dict, tiempos: dict) -> dict:
    """Lo que queda en docs/evidencia/modelos-texto.json."""
    modelos = {}
    for nombre, fila in tabla.iterrows():
        modelos[nombre] = {"nombre": NOMBRES[nombre], "pr_auc_por_fold": por_fold[nombre],
                           **{clave: valor for clave, valor in fila.items() if not (isinstance(valor, float) and np.isnan(valor))}}
    return _redondear({
        "prerregistro": {"archivo": PRERREGISTRO, "commit": COMMIT_DEL_PRERREGISTRO},
        "codigo": codigo,
        "fecha": date.today().isoformat(),
        "entorno": entorno(),
        "datos": {
            "release": "data-v1", "sha256": DATA_V1_SHA256, "firma_limpio": firma,
            "negativas": len(negativas), "tempranas": int(negativas["temprana"].sum()),
            "tardias": int((negativas["temprana"] == 0).sum()), "juegos": negativas["appid"].nunique(),
            "con_duracion_enmascarada": int(negativas["texto_norm"].map(lambda t: PATRON_DURACION.search(t) is not None).sum()),
            "por_fold": conteos.reset_index().to_dict(orient="records"),
        },
        "bootstrap": {"replicas": REPLICAS, "semilla": SEMILLA, "nivel": 0.95, "por": "juegos, dentro de cada fold"},
        "modelos": modelos,
        "sensibilidad_sin_mascara": {nombre: {**fila.to_dict(), "pr_auc_por_fold": por_fold[f"{nombre}_sin"]}
                                     for nombre, fila in sens.iterrows()},
        "decision": decision,
        "tiempos_s": tiempos,
    })


def diferencias_con_registro(registrado: dict, por_fold: dict[str, np.ndarray], decision: dict,
                              tolerancia: float = 1e-3) -> list[str]:
    """Lo que no coincide con docs/evidencia/modelos-texto.json: las medias (con `tolerancia`, porque otra
    versión de torch o de scikit-learn mueve los decimales lejanos), el mejor modelo, la rama y el elegido."""
    distintas = []
    for nombre, datos in registrado["modelos"].items():
        if abs(por_fold[nombre].mean() - datos["PR-AUC media"]) > tolerancia:
            distintas.append(f"{nombre}: PR-AUC media {por_fold[nombre].mean():.4f} contra {datos['PR-AUC media']:.4f}")
    for nombre, datos in registrado["sensibilidad_sin_mascara"].items():
        if abs(por_fold[f"{nombre}_sin"].mean() - datos["sin máscara"]) > tolerancia:
            distintas.append(f"{nombre} sin máscara: {por_fold[f'{nombre}_sin'].mean():.4f} contra {datos['sin máscara']:.4f}")
    for clave in ("mejor", "rama", "elegido"):
        if decision[clave] != registrado["decision"][clave]:
            distintas.append(f"{clave}: {decision[clave]} contra {registrado['decision'][clave]}")
    return distintas


def _commit_del_codigo() -> dict:
    corto = subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    sucio = subprocess.run(["git", "-C", str(RAIZ), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True)
    return {"commit": corto.stdout.strip() or None, "arbol_limpio": corto.returncode == 0 and not sucio.stdout.strip()}


def main() -> int:
    # Rutas relativas a backend/: así la evidencia no lleva rutas de una máquina.
    os.chdir(RAIZ)
    carpeta = Path("extracto") / "modelos_texto"
    codigo = _commit_del_codigo()
    if not codigo["arbol_limpio"]:
        print("Aviso: hay cambios sin commit; el JSON lo registra (arbol_limpio = false).")
    tiempos = {}
    inicio = time.monotonic()

    ruta = descargar_verificado("data-v1", DATA_V1_SHA256, carpeta / "nexplay_data-v1.db")
    _, resenas = cargar_release(ruta)
    limpio, _ = limpiar(resenas)
    firma = firma_del_conjunto(limpio)
    if firma != FIRMA_LIMPIO_DATA_V1:
        sys.exit(f"La firma del conjunto limpio no es la del prerregistro ({firma[:12]}… contra {FIRMA_LIMPIO_DATA_V1[:12]}…): no se corre.")
    negativas = negativas_en_ingles(limpio)
    assert not negativas["texto_modelo"].map(lambda t: UNIDAD_SUELTA.search(t) is not None).any(), "la máscara dejó una unidad"
    y, appid = negativas["temprana"].to_numpy(), negativas["appid"]
    fold = folds_de(negativas)
    conteos = conteos_por_fold(negativas, fold)
    tiempos["datos"] = time.monotonic() - inicio
    print(f"Modelos de texto · Parte A. Prerregistro: {PRERREGISTRO} (commit {COMMIT_DEL_PRERREGISTRO}); "
          f"código: {codigo['commit']}{'' if codigo['arbol_limpio'] else ' con cambios sin commit'}.")
    print(f"Negativas en inglés: {len(negativas):,} · tempranas {y.sum():,} · tardías {(y == 0).sum():,} · "
          f"{appid.nunique()} juegos")
    print(conteos.to_string(float_format=lambda x: f"{x:.4f}"), "\n")

    scores = {"trivial": np.zeros(len(y)), "refund": regla_refund(negativas["texto_modelo"])}
    for nombre, modelo in modelos_tfidf().items():
        t = time.monotonic()
        scores[nombre] = scores_fuera_de_fold(modelo, negativas["texto_modelo"], y, appid)
        scores[f"{nombre}_sin"] = scores_fuera_de_fold(modelo, negativas["texto_norm"], y, appid)
        tiempos[nombre] = time.monotonic() - t
    t = time.monotonic()
    vectores = embeddings(negativas["texto_modelo"], carpeta)
    tiempos["embeddings"] = time.monotonic() - t
    t = time.monotonic()
    scores["minilm_lr"] = scores_fuera_de_fold(modelo_embeddings(), vectores, y, appid)
    tiempos["minilm_lr"] = time.monotonic() - t

    por_fold = {nombre: pr_auc_por_fold(y, score, fold) for nombre, score in scores.items()}
    assert np.allclose(por_fold["trivial"], conteos["prevalencia"].to_numpy()), "el trivial no es la prevalencia del fold"
    t = time.monotonic()
    replicas = bootstrap_pareado(y, scores, fold, appid.to_numpy())
    tiempos["bootstrap"] = time.monotonic() - t
    tabla = resumen(por_fold, replicas)
    sens = sensibilidad(por_fold, replicas)
    decision = decidir(por_fold, replicas)
    tiempos["total"] = time.monotonic() - inicio

    pd.set_option("display.width", 200)
    print("PR-AUC por fold (texto enmascarado):")
    print(pd.DataFrame({NOMBRES[n]: por_fold[n] for n in ("trivial", "refund", *CANDIDATOS)}).to_string(float_format=lambda x: f"{x:.4f}"), "\n")
    print(tabla.rename(index=NOMBRES).to_string(float_format=lambda x: f"{x:.4f}"), "\n")
    print("Sensibilidad sin máscara (no entra a la regla):")
    print(sens.rename(index=NOMBRES).to_string(float_format=lambda x: f"{x:.4f}"), "\n")
    print(f"Mejor modelo (M): {NOMBRES[decision['mejor']]} · supera al trivial: {decision['supera_trivial']} · "
          f"supera a «refund»: {decision['supera_refund']}")
    guardado = f" · se guarda {NOMBRES[decision['elegido']]}" if decision["elegido"] else ""
    print(f"Rama {decision['rama']}{guardado}")
    print(decision["conclusion"])

    destino = RAIZ.parent / "docs" / "evidencia" / "modelos-texto.json"
    resultado = registro(negativas, conteos, firma, por_fold, replicas, tabla, sens, decision, codigo, tiempos)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n→ {destino.relative_to(RAIZ.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
