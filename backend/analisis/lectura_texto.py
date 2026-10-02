"""Lectura para negocio de los modelos de texto (notebooks/02_modelos_texto.ipynb, después de la decisión).

Todo aquí es descriptivo y posterior a la decisión del prerregistro: usa los puntajes fuera de fold que ya
calculó texto.py y no cambia la regla, sus cifras ni lo registrado en docs/evidencia/modelos-texto.json."""

import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.base import clone
from sklearn.metrics import precision_recall_curve

import texto as tx
from entrenar_baseline import SEMILLA, splits_congelados
from graficas import COLOR_GRUPO, PALETA
from limpieza import STOPWORDS_SIN_NEGACIONES
from motivos import categorias_de

RECALL = np.linspace(0.01, 1, 100)
TOP_K = (0.10, 0.20, 0.30)
# El modelo que se guarda va en azul. El rojo no se usa para modelos porque en el 00 y en las nubes es «temprana».
COLOR_MODELO = {"trivial": PALETA["GRIS"], "refund": PALETA["GRIS"], "tfidf_nb": PALETA["VERDE_CLA"],
                "tfidf_lr": PALETA["AZUL"], "minilm_lr": PALETA["VERDE_OSC"]}


# --- Cuánto separa cada modelo ----------------------------------------------------------------

def figura_pr_auc_con_ic(tabla: pd.DataFrame) -> go.Figure:
    """Barras de la media de los 5 folds con su IC (bootstrap sobre juegos) y una línea en el trivial.
    `tabla` es tx.resumen."""
    modelos = ["refund", *tx.CANDIDATOS]
    medias = tabla.loc[modelos, "PR-AUC media"]
    bajo = medias - [tabla.loc[m, "IC media"][0] for m in modelos]
    alto = [tabla.loc[m, "IC media"][1] for m in modelos] - medias
    figura = go.Figure(go.Bar(
        x=[tx.NOMBRES[m] for m in modelos], y=medias, marker_color=[COLOR_MODELO[m] for m in modelos],
        error_y={"type": "data", "symmetric": False, "array": alto, "arrayminus": bajo, "color": "#455a64"},
        text=[f"{v:.3f}" for v in medias], textposition="inside", insidetextanchor="start",
    ))
    trivial = tabla.loc["trivial", "PR-AUC media"]
    figura.add_hline(y=trivial, line_dash="dash", line_color=PALETA["GRIS"],
                     annotation_text=f"trivial (la prevalencia): {trivial:.3f}", annotation_position="top left")
    figura.update_layout(title="PR-AUC media de los 5 folds, con su IC del 95 %", yaxis_title="PR-AUC")
    return figura


def curva_pr_media(y: np.ndarray, score: np.ndarray, fold: np.ndarray, recall: np.ndarray = RECALL) -> np.ndarray:
    """La precisión de cada fold en cada nivel de recall, promediada entre folds.

    Es la precisión en escalón que suma el PR-AUC: para un recall r, la del umbral más alto que ya alcanza r.
    Así el área bajo la curva media se parece a la media de los PR-AUC por fold, que es la cifra de la tabla."""
    curvas = []
    for k in np.unique(fold):
        precision, alcanzado, _ = precision_recall_curve(y[fold == k], score[fold == k])
        # `alcanzado` baja de 1 a 0: el último punto con alcanzado ≥ r es el del umbral más alto.
        indice = np.searchsorted(-alcanzado, -recall, side="right") - 1
        curvas.append(precision[indice])
    return np.mean(curvas, axis=0)


def figura_curvas_pr(curvas: dict[str, np.ndarray], recall: np.ndarray = RECALL) -> go.Figure:
    figura = go.Figure()
    for nombre, precision in curvas.items():
        figura.add_trace(go.Scatter(x=recall, y=precision, mode="lines", name=tx.NOMBRES[nombre],
                                    line={"color": COLOR_MODELO[nombre], "width": 3 if nombre == "tfidf_lr" else 2,
                                          "dash": "dash" if nombre == "trivial" else "solid", "shape": "hv"}))
    figura.update_layout(title="Precisión contra recall, promedio de los 5 folds",
                         xaxis_title="recall: qué parte de las tempranas encuentra",
                         yaxis_title="precisión: qué parte de lo señalado es temprana", yaxis_range=[0, 1])
    return figura


def tabla_top_k(y: np.ndarray, scores: dict[str, np.ndarray], fold: np.ndarray, ids: np.ndarray,
                ks: tuple[float, ...] = TOP_K, referencia: str = "tfidf_lr") -> pd.DataFrame:
    """En cada fold, qué parte de las k % reseñas con score más alto son tempranas, promediado entre folds, y
    cuántas veces la prevalencia es eso para el modelo `referencia`. Los empates se rompen por id, para que la
    tabla no dependa del orden de las filas."""
    filas = {}
    for k in ks:
        fila = {"prevalencia": np.mean([y[fold == f].mean() for f in np.unique(fold)])}
        for nombre, score in scores.items():
            aciertos = []
            for f in np.unique(fold):
                en_fold = fold == f
                orden = np.lexsort((ids[en_fold], -score[en_fold]))
                aciertos.append(y[en_fold][orden[: math.ceil(k * en_fold.sum())]].mean())
            fila[tx.NOMBRES[nombre]] = np.mean(aciertos)
        fila[f"veces la prevalencia ({tx.NOMBRES[referencia]})"] = fila[tx.NOMBRES[referencia]] / fila["prevalencia"]
        filas[f"{k:.0%} con score más alto"] = fila
    return pd.DataFrame(filas).T


# --- Qué palabras pesan ------------------------------------------------------------------------

def coeficientes_por_fold(textos: pd.Series, y: np.ndarray, appid: pd.Series) -> pd.DataFrame:
    """El coeficiente de cada término en TF-IDF + LR, reajustado con el entrenamiento de cada fold (el mismo
    Pipeline que decide). Un término que no entra al vocabulario de un fold queda vacío en ese fold."""
    por_fold = {}
    for numero, (entrenamiento, _) in enumerate(splits_congelados(appid)):
        modelo = clone(tx.modelos_tfidf()["tfidf_lr"]).fit(textos.iloc[entrenamiento], y[entrenamiento])
        por_fold[f"fold {numero + 1}"] = pd.Series(modelo["lr"].coef_[0], index=modelo["tfidf"].get_feature_names_out())
    return pd.DataFrame(por_fold)


def palabras_estables(coeficientes: pd.DataFrame) -> pd.DataFrame:
    """Los términos que están en los 5 folds con el mismo signo, con su coeficiente medio: positivo empuja hacia
    temprana, negativo hacia tardía."""
    completos = coeficientes.dropna()
    signos = np.sign(completos)
    estables = completos[(signos.nunique(axis=1) == 1) & (signos.iloc[:, 0] != 0)]
    return estables.mean(axis=1).rename("coeficiente medio").sort_values().to_frame()


def es_de_duracion(terminos: pd.Index) -> np.ndarray:
    return np.asarray(terminos.str.contains(rf"\b{tx.MARCA_DURACION}\b", regex=True), dtype=bool)


def duracion_aparte(coeficientes: pd.DataFrame, estables: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Lo que las nubes dejan fuera: el coeficiente de `duracion` sola en cada fold y cuántos términos con
    `duracion` (pares como «first duracion») pasan el filtro de los 5 folds, hacia cada lado."""
    unigrama = coeficientes.loc[tx.MARCA_DURACION]
    con_duracion = estables[es_de_duracion(estables.index)]["coeficiente medio"]
    conteo = pd.Series({"hacia temprana": int((con_duracion > 0).sum()), "hacia tardía": int((con_duracion < 0).sum())},
                       name="términos con duracion, estables en los 5 folds")
    return unigrama, conteo


# Lo que no se dibuja aunque pese: términos ofensivos o fuera de tema (enfermedades, sexo, política). No cambia
# ningún coeficiente ni la decisión; el notebook imprime cuáles quedaron fuera. Un término sale si alguna de sus
# palabras está en la lista, o si es una de las frases.
FUERA_DEL_DIBUJO = frozenset({"ass", "piss", "pissed", "pisses", "bastard", "wtf", "sex", "cancer", "aids", "suicide",
                              "racist", "political", "politics", "woke", "dei"})
FRASES_FUERA_DEL_DIBUJO = frozenset({"hate you"})


def es_palabra_vacia(termino: str) -> bool:
    """Solo palabras vacías (las stopwords del 00, que conservan las negaciones): «and the», «your»."""
    return all(palabra in STOPWORDS_SIN_NEGACIONES for palabra in termino.split())


def va_fuera_del_dibujo(termino: str) -> bool:
    return termino in FRASES_FUERA_DEL_DIBUJO or any(palabra in FUERA_DEL_DIBUJO for palabra in termino.split())


def para_las_nubes(estables: pd.DataFrame) -> tuple[dict[str, float], dict[str, float], pd.DataFrame]:
    """Todos los términos estables hacia cada lado, del de más peso al de menos, sin los que llevan `duracion`
    (se reportan aparte), sin los hechos solo de palabras vacías y sin la lista declarada. Devuelve también los de
    la lista que pesaban, para reportarlos."""
    pesos = estables["coeficiente medio"]
    pesos = pesos[~es_de_duracion(pesos.index) & ~pesos.index.map(es_palabra_vacia)]
    fuera = pesos.index.map(va_fuera_del_dibujo)
    quedan = pesos[~fuera]
    tempranas = quedan[quedan > 0].sort_values(ascending=False)
    tardias = (-quedan[quedan < 0]).sort_values(ascending=False)
    return tempranas.to_dict(), tardias.to_dict(), pesos[fuera].sort_values().to_frame()


def silueta_de_control(ancho: int = 1400, alto: int = 760) -> np.ndarray:
    """La forma de las nubes: un control de videojuegos (cuerpo y dos empuñaduras), con la cruceta, cuatro botones y
    dos sticks como huecos. En la máscara de wordcloud, 255 es donde no van palabras."""
    from PIL import Image, ImageDraw

    imagen = Image.new("L", (ancho, alto), 255)
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((260, 40, 1140, 430), radius=190, fill=0)
    dibujo.ellipse((150, 170, 560, 730), fill=0)
    dibujo.ellipse((840, 170, 1250, 730), fill=0)
    dibujo.rectangle((300, 290, 1100, 470), fill=0)
    dibujo.rectangle((345, 190, 375, 290), fill=255)
    dibujo.rectangle((310, 225, 410, 255), fill=255)
    for x, y in ((1040, 170), (1000, 210), (1080, 210), (1040, 250)):
        dibujo.ellipse((x - 22, y - 22, x + 22, y + 22), fill=255)
    for x, y in ((540, 340), (860, 340)):
        dibujo.ellipse((x - 50, y - 50, x + 50, y + 50), fill=255)
    return np.array(imagen)


def figura_nube(pesos: dict[str, float], color: str, titulo: str) -> tuple[go.Figure, int]:
    """Nube con forma de control: entran todas las palabras que quepan, de la de más peso a la de menos, y la de más
    peso es la más grande. Un solo color. Se muestra con px.imshow para que salga como PNG por el mismo camino que
    las demás gráficas. Devuelve también cuántas cupieron. wordcloud se importa aquí: solo la necesita esta figura."""
    from wordcloud import WordCloud

    nube = WordCloud(background_color="white", mask=silueta_de_control(), contour_width=4, contour_color=color,
                     prefer_horizontal=0.9, min_font_size=5, random_state=SEMILLA, max_words=len(pesos),
                     collocations=False, color_func=lambda *_, **__: color).generate_from_frequencies(pesos)
    figura = px.imshow(nube.to_array())
    figura.update_xaxes(visible=False)
    figura.update_yaxes(visible=False)
    figura.update_layout(title=titulo, margin={"l": 10, "r": 10, "t": 50, "b": 10})
    figura.update_traces(hoverinfo="skip", hovertemplate=None)
    return figura, len(nube.layout_)


def cobertura_del_sitio(pesos: dict[str, float], n: int = 40) -> pd.DataFrame:
    """Las n palabras que más empujan hacia un lado y en qué categoría de motivos del sitio caen (motivos.py, las
    mismas palabras clave de /explicacion). «—» quiere decir que hoy la ficha no la cuenta en ningún motivo."""
    primeras = pd.Series(pesos).head(n)
    return pd.DataFrame({"coeficiente medio": primeras,
                         "categoría del sitio": [", ".join(categorias_de(t)) or "—" for t in primeras.index]})


COLOR_NUBE = {"temprana": COLOR_GRUPO["negativa temprana"], "tardía": COLOR_GRUPO["negativa tardía"]}


# --- Ejemplos ----------------------------------------------------------------------------------

def ejemplos_con_score_alto(negativas: pd.DataFrame, score: np.ndarray, fold: np.ndarray, resenas: pd.DataFrame,
                            nombres: pd.Series, n: int = 3, minimo_palabras: int = 8, largo: int = 300) -> pd.DataFrame:
    """Las n tempranas (aciertos) y las n tardías (errores) con el score más alto, entre las reseñas de
    `minimo_palabras` o más para que se puedan leer. El percentil es dentro del fold de la reseña: los scores de
    folds distintos salen de modelos distintos. El texto es el original, recortado a `largo` caracteres."""
    datos = negativas[["recommendationid", "appid", "temprana"]].assign(score=score, fold=fold)
    datos["percentil del score"] = datos.groupby("fold")["score"].rank(pct=True)
    originales = resenas.set_index("recommendationid").loc[datos["recommendationid"], ["texto", "playtime_at_review"]]
    datos["texto"] = originales["texto"].to_numpy()
    datos["minutos jugados"] = originales["playtime_at_review"].to_numpy()
    datos = datos[datos["texto"].str.split().str.len() >= minimo_palabras]
    elegidos = []
    for clase, nombre in ((1, "acierto: temprana"), (0, "error: tardía")):
        mejores = datos[datos["temprana"] == clase].sort_values(["score", "recommendationid"], ascending=[False, True]).head(n)
        elegidos.append(mejores.assign(caso=nombre))
    tabla = pd.concat(elegidos)
    tabla["juego"] = tabla["appid"].map(nombres)
    tabla["texto"] = tabla["texto"].map(lambda t: " ".join(t.split())).map(lambda t: t[:largo] + ("…" if len(t) > largo else ""))
    return tabla[["caso", "juego", "minutos jugados", "percentil del score", "texto"]].reset_index(drop=True)
