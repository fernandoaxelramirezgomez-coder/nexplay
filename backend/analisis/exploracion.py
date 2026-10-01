"""Las cuentas de notebooks/00_exploracion.ipynb.

Viven aquí para que el notebook importe en vez de copiar, y para que los modelos de texto
(Parte A y Parte B) usen exactamente las mismas. Cada chequeo devuelve una tabla: el notebook
la muestra y hace el assert."""

import contextlib
import hashlib
import io
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import sklearn
from scipy.stats import spearmanr
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold, KFold

# leer_particion no se usa aquí: el notebook la llama como ex.leer_particion().
from entrenar_baseline import (  # noqa: F401
    N_SPLITS, SEMILLA, construir_features, construir_pipeline, evaluar_gkf, leer_particion, particion_groupkfold, splits_de,
)
from entrenar_modelo import _scores_oof
from limpieza import PALABRAS_DE_UNA_COPIA, clave_de_copia, es_plantilla, palabras

# La ventana de reembolso de Steam: define la señal, no se elige con datos.
UMBRAL_REEMBOLSO = 120
# MAX_RESENAS_POR_JUEGO de ingesta/ingesta_steam.py (importarlo crea carpetas y configura el log).
# Se piden de 100 en 100, así que un juego que lo alcanza llega hasta 1,599.
TOPE_DE_LA_INGESTA = 1500

PALETA = {"VERDE_OSC": "#2e8b57", "VERDE_CLA": "#90ee90", "ROJO": "#e53935", "GRIS": "#90a4ae", "AZUL": "#1976d2"}
# El mismo color para lo mismo en todas las figuras.
COLOR_GRUPO = {"positiva": PALETA["VERDE_OSC"], "negativa tardía": PALETA["GRIS"], "negativa temprana": PALETA["ROJO"]}
COLOR_RELEASE = {"data-v1 (83)": PALETA["AZUL"], "externos (40)": PALETA["VERDE_CLA"]}


# --- Gráficas -------------------------------------------------------------------------------

def configurar_graficas(exportar_estatico: bool) -> bool:
    """La plantilla con la paleta fija. Con `exportar_estatico`, cada figura se guarda también
    como PNG, para que se vea en GitHub. Eso pide kaleido y un Chrome: en Colab, o donde kaleido
    no logra exportar, se apaga con un aviso y las gráficas quedan solo interactivas. Devuelve si
    la exportación quedó encendida."""
    pio.templates["nexplay"] = go.layout.Template(
        layout=go.Layout(
            colorway=[PALETA["AZUL"], PALETA["ROJO"], PALETA["VERDE_OSC"], PALETA["GRIS"], PALETA["VERDE_CLA"]],
            font={"family": "Arial, sans-serif", "size": 13},
            title={"font": {"size": 16}},
            margin={"l": 60, "r": 30, "t": 60, "b": 50},
        )
    )
    pio.templates.default = "plotly_white+nexplay"
    if exportar_estatico:
        motivo = _por_que_no_exportar()
        if motivo:
            print(f"Exportación estática apagada: {motivo}. Las gráficas se ven interactivas, sin PNG.")
            return False
        pio.renderers.default = "notebook_connected+png"
        pio.renderers["png"].width, pio.renderers["png"].height = 900, 480
    return exportar_estatico


def _por_que_no_exportar() -> str | None:
    """None si kaleido puede guardar un PNG; si no, el motivo en una frase."""
    if "google.colab" in sys.modules:
        return "en Colab no hace falta"
    try:
        go.Figure().to_image(format="png", width=20, height=20)
    except Exception as exc:  # kaleido lanza tipos distintos según lo que falte: el paquete o Chrome
        detalle = str(exc).strip().splitlines()
        return f"kaleido no pudo exportar una figura de prueba ({detalle[0].rstrip('.') if detalle else type(exc).__name__})"
    return None


# --- Carga ----------------------------------------------------------------------------------

def cargar_release(ruta: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Las tablas `juegos` y `resenas` completas, en solo lectura."""
    with contextlib.closing(sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)) as con:
        return pd.read_sql("SELECT * FROM juegos", con), pd.read_sql("SELECT * FROM resenas", con)


def tablas_de(ruta: Path) -> list[str]:
    with contextlib.closing(sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)) as con:
        return sorted(nombre for (nombre,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))


def senal(resenas: pd.DataFrame, umbral: int = UMBRAL_REEMBOLSO) -> pd.Series:
    """Y = 1: negativa escrita antes de `umbral` minutos de juego."""
    return (resenas["playtime_at_review"] < umbral) & (resenas["voted_up"] == 0)


def grupo_de_resena(resenas: pd.DataFrame) -> pd.Series:
    grupo = np.select([resenas["voted_up"] == 1, senal(resenas)], ["positiva", "negativa temprana"], "negativa tardía")
    return pd.Series(grupo, index=resenas.index)


def con_juego(resenas: pd.DataFrame, juegos: pd.DataFrame) -> pd.DataFrame:
    """Cada reseña con las columnas del juego que usa el modelo, como las lee entrenar_baseline."""
    columnas = ["appid", "nombre", "es_gratis", "precio_final", "descuento", "metacritic"]
    return resenas.merge(juegos[columnas], on="appid", how="left", validate="many_to_one")


# --- Validación -----------------------------------------------------------------------------

def filas_distintas(a: pd.DataFrame, b: pd.DataFrame, llave: str, columnas: list[str]) -> tuple[int, int]:
    """Cuántas filas de `a` están en `b` y cuántas celdas difieren (dos nulos cuentan como iguales)."""
    juntas = a[[llave, *columnas]].merge(b[[llave, *columnas]], on=llave, suffixes=("_a", "_b"))
    distintas = 0
    for columna in columnas:
        izquierda, derecha = juntas[f"{columna}_a"], juntas[f"{columna}_b"]
        distintas += int((~(izquierda.eq(derecha) | (izquierda.isna() & derecha.isna()))).sum())
    return len(juntas), distintas


def precio_imputado(juegos: pd.DataFrame) -> pd.Series:
    """De pago y sin precio: entrenar_baseline lo lee como 0 (limitación documentada en 01 §4)."""
    return (juegos["es_gratis"] == 0) & juegos["precio_final"].isna()

def esquema(ruta: Path, tabla: str, df: pd.DataFrame) -> pd.DataFrame:
    with contextlib.closing(sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)) as con:
        tipos = {fila[1]: fila[2] for fila in con.execute(f"PRAGMA table_info({tabla})")}
    return pd.DataFrame({
        "tipo SQLite": pd.Series(tipos),
        "dtype": df.dtypes.astype(str),
        "nulos": df.isna().sum(),
        "% nulos": (100 * df.isna().mean()).round(2),
    }).rename_axis("columna")


def llaves(juegos: pd.DataFrame, resenas: pd.DataFrame) -> pd.DataFrame:
    casos = {
        "recommendationid repetido": int(resenas["recommendationid"].duplicated().sum()),
        "appid de reseñas que no está en juegos": int((~resenas["appid"].isin(juegos["appid"])).sum()),
        "juegos sin reseñas": int((~juegos["appid"].isin(resenas["appid"])).sum()),
        "appid repetido en juegos": int(juegos["appid"].duplicated().sum()),
    }
    return pd.Series(casos, name="casos").rename_axis("chequeo").to_frame()


def casos_de_rango(juegos: pd.DataFrame, resenas: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Las filas que rompen cada regla. Las de `REGLAS_DURAS` deben quedar vacías."""
    creada = pd.to_datetime(resenas["timestamp_created"], unit="s", utc=True)
    editada = pd.to_datetime(resenas["timestamp_updated"], unit="s", utc=True)
    descargada = pd.to_datetime(resenas["descargado_en"], utc=True, format="ISO8601")
    precio = juegos["precio_final"]
    return {
        "playtime_at_review ≥ 0": resenas[resenas["playtime_at_review"] < 0],
        "voted_up ∈ {0, 1}": resenas[~resenas["voted_up"].isin([0, 1])],
        "creada ≤ editada ≤ descargada": resenas[(creada > editada) | (editada > descargada)],
        "precio ≥ 0": juegos[precio < 0],
        "descuento entre 0 y 100": juegos[~juegos["descuento"].fillna(0).between(0, 100)],
        "Metacritic entre 0 y 100 o nulo": juegos[juegos["metacritic"].notna() & ~juegos["metacritic"].between(0, 100)],
        "playtime_at_review ≤ playtime_forever": resenas[resenas["playtime_at_review"] > resenas["playtime_forever"]],
        "es_gratis coherente con el precio": juegos[precio_imputado(juegos) | ((juegos["es_gratis"] == 1) & (precio > 0))],
    }


REGLAS_DURAS = (
    "playtime_at_review ≥ 0", "voted_up ∈ {0, 1}", "creada ≤ editada ≤ descargada",
    "precio ≥ 0", "descuento entre 0 y 100", "Metacritic entre 0 y 100 o nulo",
)


def resumen_de_rango(casos: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame(
        {"casos": len(filas), "tipo": "assert" if regla in REGLAS_DURAS else "tabla de casos"} for regla, filas in casos.items()
    ).set_index(pd.Index(list(casos), name="regla"))


def copias_de_texto(resenas: pd.DataFrame, minimo_palabras: int = 1) -> dict:
    """Texto idéntico repetido dentro del mismo juego y entre juegos distintos."""
    con_texto = resenas[resenas["texto"].fillna("").str.strip().ne("")]
    con_texto = con_texto[palabras(con_texto["texto"]) >= minimo_palabras].assign(clave=lambda d: clave_de_copia(d["texto"]))
    juegos_por_texto = con_texto.groupby("clave")["appid"].nunique()
    entre = juegos_por_texto[juegos_por_texto > 1].index
    return {
        "sobrantes en el mismo juego": int(con_texto.duplicated(["appid", "clave"]).sum()),
        "textos en 2+ juegos": len(entre),
        "filas con texto de 2+ juegos": int(con_texto["clave"].isin(entre).sum()),
        "ejemplos en el mismo juego": con_texto[con_texto.duplicated(["appid", "clave"])],
        "ejemplos entre juegos": con_texto[con_texto["clave"].isin(entre)].drop_duplicates("clave"),
        "claves entre juegos": entre,
    }


def plantillas(resenas: pd.DataFrame) -> pd.DataFrame:
    return resenas[es_plantilla(resenas["texto"])]


def ejemplos(filas: pd.DataFrame, juegos: pd.DataFrame, n: int = 3, columnas=("texto",), largo: int = 220) -> pd.DataFrame:
    """`n` filas reales al azar (semilla fija), con el nombre del juego y el texto recortado."""
    muestra = filas.sample(min(n, len(filas)), random_state=SEMILLA).merge(juegos[["appid", "nombre"]], on="appid", how="left")
    muestra = muestra[["nombre", "voted_up", "playtime_at_review", *columnas]].copy()
    for columna in columnas:
        muestra[columna] = muestra[columna].fillna("").map(lambda texto: texto if len(texto) <= largo else texto[:largo] + "…")
    return muestra.reset_index(drop=True)


# --- Partición congelada --------------------------------------------------------------------

# La firma de referencias/particion_gkf_data-v1.csv: si el CSV cambia, el notebook falla en 1.6.
FIRMA_PARTICION_DATA_V1 = "416aa8243b570f05f40aa238cb9730faa67d41ecd3f79da7db56558028bb7493"


def firma_de_particion(folds: pd.Series) -> str:
    return hashlib.sha256("\n".join(f"{appid},{fold}" for appid, fold in folds.sort_index().items()).encode()).hexdigest()


def chequeo_de_particion(folds: pd.Series, appids: dict[str, pd.Series]) -> pd.DataFrame:
    """Que el CSV sea una partición válida de los mismos juegos que leen 00 y 01. Todo sale del CSV y de
    los datos, nada de la versión de scikit-learn: da lo mismo en cualquier entorno."""
    juegos = set().union(*map(set, appids.values()))
    filas = [("appids en el CSV", len(folds), len(juegos)),
             ("folds", folds.nunique(), N_SPLITS),
             ("juegos en más de un fold", int(folds.index.duplicated().sum()), 0)]
    filas += [(f"appids de {nombre} fuera del CSV", len(set(serie) - set(folds.index)), 0) for nombre, serie in appids.items()]
    filas += [("appids del CSV fuera de los datos", len(set(folds.index) - juegos), 0),
              ("firma", firma_de_particion(folds), FIRMA_PARTICION_DATA_V1)]
    tabla = pd.DataFrame(filas, columns=["chequeo", "valor", "esperado"]).set_index("chequeo")
    tabla["ok"] = [valor == esperado for valor, esperado in zip(tabla["valor"], tabla["esperado"])]
    return tabla


def groupkfold_de_esta_version(df: pd.DataFrame, folds: pd.Series) -> dict:
    """Lo que arma el GroupKFold de la versión instalada, contra la partición congelada. Solo informa:
    ninguna cuenta del notebook usa esta partición."""
    recalculada = particion_groupkfold(df["appid"])
    resenas = df.groupby("appid").size()
    empate = int(resenas.mode().iloc[0])
    return {"scikit-learn": sklearn.__version__,
            "misma partición": firma_de_particion(recalculada) == firma_de_particion(folds),
            "juegos con el mismo fold": int(recalculada.eq(folds.reindex(recalculada.index)).sum()),
            "juegos": len(recalculada),
            "juegos empatados": int(resenas.eq(empate).sum()),
            "reseñas del empate": empate}


def copias_en_folds_distintos(resenas: pd.DataFrame, claves: pd.Index, folds: pd.Series) -> int:
    """Textos copiados entre juegos que quedan en folds distintos: un modelo de texto los vería
    en entrenamiento y en validación."""
    con_clave = resenas.assign(clave=clave_de_copia(resenas["texto"]), fold=resenas["appid"].map(folds))
    return int((con_clave[con_clave["clave"].isin(claves)].groupby("clave")["fold"].nunique() > 1).sum())


def resumen_por_fold(resenas: pd.DataFrame, folds: pd.Series) -> pd.DataFrame:
    fold = resenas["appid"].map(folds)
    return pd.DataFrame({
        "juegos": resenas.groupby(fold)["appid"].nunique(),
        "reseñas": resenas.groupby(fold).size(),
        "Y=1": senal(resenas).groupby(fold).sum(),
    }).assign(prevalencia=lambda d: (d["Y=1"] / d["reseñas"]).round(4)).rename_axis("fold")


# --- Exploración ----------------------------------------------------------------------------

def cobertura_por_juego(resenas: pd.DataFrame, juegos: pd.DataFrame) -> pd.DataFrame:
    """Cuántas reseñas hay de cada juego y cuántos días cubren. La ingesta pide las más
    recientes (filter=recent) hasta un tope: un juego popular llena el tope en semanas, uno de
    nicho en años."""
    fecha = pd.to_datetime(resenas["timestamp_created"], unit="s")
    por_juego = pd.DataFrame({"reseñas": resenas.groupby("appid").size(),
                              "primera": fecha.groupby(resenas["appid"]).min(),
                              "última": fecha.groupby(resenas["appid"]).max()})
    por_juego["días cubiertos"] = (por_juego["última"] - por_juego["primera"]).dt.days + 1
    return juegos.set_index("appid")[["nombre"]].join(por_juego, how="inner")


def variables_constantes_por_juego(df: pd.DataFrame) -> pd.Series:
    """Cuántos juegos tienen más de un valor en cada variable del modelo: 0 en todas quiere decir
    que el modelo solo puede aprender del juego, no de la reseña."""
    X, _, grupos = construir_features(df, conjunto="juego")
    return (X.groupby(grupos).nunique() > 1).sum().rename("juegos con más de un valor")


def menciones(textos: pd.Series, grupos: pd.Series, patron: str) -> pd.Series:
    """Qué parte de cada grupo menciona `patron` (con `re` de Python, igual en pandas 2 y 3)."""
    compilado = re.compile(patron, re.IGNORECASE)
    return textos.fillna("").map(lambda texto: compilado.search(texto) is not None).groupby(grupos).mean()

def wilson(exitos: pd.Series, total: pd.Series, z: float = 1.96) -> tuple[pd.Series, pd.Series]:
    """Intervalo de Wilson al 95 %: no se sale de [0, 1] con tasas bajas como las de aquí."""
    p = exitos / total
    centro = (p + z**2 / (2 * total)) / (1 + z**2 / total)
    radio = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / (1 + z**2 / total)
    return centro - radio, centro + radio


def tasa_por_juego(resenas: pd.DataFrame, juegos: pd.DataFrame) -> pd.DataFrame:
    por_juego = resenas.assign(y=senal(resenas)).groupby("appid").agg(reseñas=("y", "size"), y1=("y", "sum"))
    por_juego["tasa"] = por_juego["y1"] / por_juego["reseñas"]
    por_juego["ic_bajo"], por_juego["ic_alto"] = wilson(por_juego["y1"], por_juego["reseñas"])
    columnas = ["appid", "nombre", "es_gratis", "precio_final", "descuento", "metacritic"]
    return juegos[columnas].set_index("appid").join(por_juego, how="inner")


def sobredispersion(por_juego: pd.DataFrame) -> float:
    """Cuántas veces más varía la tasa entre juegos de lo que variaría si todos tuvieran la misma
    (1 = nada más que ruido de muestreo)."""
    p = por_juego["y1"].sum() / por_juego["reseñas"].sum()
    esperado = por_juego["reseñas"] * p
    chi2 = ((por_juego["y1"] - esperado) ** 2 / (esperado * (1 - p))).sum()
    return float(chi2 / (len(por_juego) - 1))


def correlaciones_del_juego(por_juego: pd.DataFrame) -> pd.DataFrame:
    """Spearman de la tasa de señal por juego contra cada variable del juego. El precio, solo en
    juegos de pago con precio conocido; la nota, solo en los que la tienen."""
    de_pago = por_juego[(por_juego["es_gratis"] == 0) & por_juego["precio_final"].notna()]
    con_nota = por_juego[por_juego["metacritic"].notna()]
    pares = {
        "precio (juegos de pago)": (de_pago["precio_final"], de_pago["tasa"]),
        "es gratis": (por_juego["es_gratis"], por_juego["tasa"]),
        "descuento": (por_juego["descuento"].fillna(0), por_juego["tasa"]),
        "tiene nota de la crítica": (por_juego["metacritic"].notna().astype(int), por_juego["tasa"]),
        "nota de la crítica (con nota)": (con_nota["metacritic"], con_nota["tasa"]),
    }
    filas = []
    for variable, (x, y) in pares.items():
        resultado = spearmanr(x, y)
        filas.append({"variable": variable, "juegos": len(x), "Spearman": round(resultado.statistic, 3), "p": round(resultado.pvalue, 4)})
    return pd.DataFrame(filas).set_index("variable")


def _en_silencio(funcion, *args):
    """evaluar_gkf imprime cada fold; aquí solo interesa el resultado."""
    with contextlib.redirect_stdout(io.StringIO()):
        return funcion(*args)


def kfold_contra_groupkfold(df: pd.DataFrame) -> pd.DataFrame:
    """El mismo modelo con folds aleatorios de reseñas (el juego se ve en entrenamiento y en
    validación) y con GroupKFold. Solo para mostrar la fuga: nunca para decidir nada."""
    X, y, grupos = construir_features(df, conjunto="juego")
    aleatorio = []
    for entrenamiento, validacion in KFold(n_splits=N_SPLITS, shuffle=True, random_state=SEMILLA).split(X):
        modelo = construir_pipeline().fit(X.iloc[entrenamiento], y.iloc[entrenamiento])
        aleatorio.append(average_precision_score(y.iloc[validacion], modelo.predict_proba(X.iloc[validacion])[:, 1]))
    por_juego = _en_silencio(evaluar_gkf, construir_pipeline(), X, y, grupos, "juego")
    return pd.DataFrame(
        {"PR-AUC media": [np.mean(aleatorio), por_juego.mean()], "std entre folds": [np.std(aleatorio), por_juego.std()]},
        index=pd.Index(["KFold aleatorio (fuga)", "GroupKFold por appid"], name="validación"),
    )


def sensibilidad_umbral(resenas: pd.DataFrame, umbrales=(60, 90, 120, 180)) -> pd.DataFrame:
    """Prevalencia con cada umbral y qué tanto se parece el orden de los juegos al de 120."""
    base = resenas.assign(y=senal(resenas)).groupby("appid")["y"].mean()
    filas = []
    for umbral in umbrales:
        y = senal(resenas, umbral)
        por_juego = y.groupby(resenas["appid"]).mean()
        filas.append({"umbral (min)": umbral, "Y=1": int(y.sum()), "prevalencia": round(y.mean(), 4),
                      "Spearman con 120": round(spearmanr(por_juego, base.loc[por_juego.index]).statistic, 3)})
    return pd.DataFrame(filas).set_index("umbral (min)")


def exactitud_contra_pr_auc(df: pd.DataFrame) -> pd.DataFrame:
    """Por qué exactitud no sirve: «siempre 0» acierta casi todo y no encuentra ningún caso."""
    X, y, grupos = construir_features(df, conjunto="juego")
    trivial = _en_silencio(evaluar_gkf, DummyClassifier(strategy="prior"), X, y, grupos, "trivial")
    modelo = _en_silencio(evaluar_gkf, construir_pipeline(), X, y, grupos, "juego")
    return pd.DataFrame(
        {"exactitud": [1 - y.mean(), np.nan], "PR-AUC (GroupKFold)": [trivial.mean(), modelo.mean()]},
        index=pd.Index(["siempre 0 (trivial)", "modelo del juego"], name="modelo"),
    )


def juego_contra_compra(df: pd.DataFrame) -> dict:
    """La decisión B+: cuánto aporta el lado del jugador frente al ruido entre folds."""
    juego = _en_silencio(evaluar_gkf, construir_pipeline(), *construir_features(df, conjunto="juego"), "juego")
    compra = _en_silencio(evaluar_gkf, construir_pipeline(), *construir_features(df, conjunto="compra"), "compra")
    return {"juego": juego, "compra": compra, "aporte": 1 - juego.mean() / compra.mean(),
            "diferencia": compra.mean() - juego.mean(), "std_juego": juego.std()}


def sensibilidad_a_la_particion(df: pd.DataFrame, repeticiones: int = 20) -> pd.Series:
    """PR-AUC medio con `repeticiones` particiones GroupKFold distintas (los juegos repartidos
    al azar entre folds). Dice cuánto se mueve el PR-AUC solo por el reparto: una diferencia
    menor que ese rango no dice nada de los datos."""
    X, y, grupos = construir_features(df, conjunto="juego")
    medias = {}
    for semilla in range(repeticiones):
        fold = pd.Series(-1, index=df.index)
        divisor = GroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=semilla)
        for numero, (_, validacion) in enumerate(divisor.split(X, y, groups=grupos)):
            fold.iloc[validacion] = numero
        medias[semilla] = pr_auc_con_particion(df, fold.groupby(df["appid"]).first()).mean()
    return pd.Series(medias, name="PR-AUC media").rename_axis("partición")


def _por_juego_y_senal(X: pd.DataFrame, y: pd.Series, grupos: pd.Series) -> pd.DataFrame:
    """Dos filas por juego (con y sin señal) y cuántas reseñas representa cada una. Las
    variables no cambian dentro de un juego, así que es el mismo conjunto, más corto."""
    return (X.assign(y=y.to_numpy(), appid=grupos.to_numpy())
            .groupby(["appid", "y"], as_index=False)
            .agg(**{columna: (columna, "first") for columna in X.columns}, n=("y", "size")))


def _coeficientes_colapsados(tabla: pd.DataFrame, columnas: list[str]) -> np.ndarray:
    """El mismo ajuste que construir_pipeline() fila por fila: el escalador pesa cada fila por
    las reseñas que representa y la regresión, además, por el peso de clase balanceado."""
    positivas = tabla.loc[tabla["y"] == 1, "n"].sum()
    negativas = tabla.loc[tabla["y"] == 0, "n"].sum()
    total = positivas + negativas
    peso = tabla["n"] * np.where(tabla["y"] == 1, total / (2 * positivas), total / (2 * negativas))
    modelo = construir_pipeline().set_params(clf__class_weight=None)
    modelo.fit(tabla[columnas], tabla["y"], escalar__sample_weight=tabla["n"], clf__sample_weight=peso)
    return modelo.named_steps["clf"].coef_[0]


def coeficientes_con_bootstrap(df: pd.DataFrame, repeticiones: int = 1000, semilla: int = SEMILLA) -> pd.DataFrame:
    """Los coeficientes del modelo B+ (variables estandarizadas) con intervalo al 95 % por
    bootstrap sobre juegos: cada réplica remuestrea appids con reemplazo, porque el juego es la
    unidad que varía, no la reseña. `fila por fila` es el ajuste de construir_pipeline() sobre
    todas las reseñas, para comprobar que el atajo colapsado da lo mismo."""
    X, y, grupos = construir_features(df, conjunto="juego")
    columnas = list(X.columns)
    tabla = _por_juego_y_senal(X, y, grupos)
    por_juego = {appid: filas for appid, filas in tabla.groupby("appid")}
    appids = np.array(sorted(por_juego))
    generador = np.random.default_rng(semilla)
    replicas = np.array([
        _coeficientes_colapsados(pd.concat([por_juego[a] for a in generador.choice(appids, len(appids))], ignore_index=True), columnas)
        for _ in range(repeticiones)
    ])
    resultado = pd.DataFrame({
        "coeficiente": _coeficientes_colapsados(tabla, columnas),
        "fila por fila": construir_pipeline().fit(X, y).named_steps["clf"].coef_[0],
        "IC 2.5 %": np.percentile(replicas, 2.5, axis=0),
        "IC 97.5 %": np.percentile(replicas, 97.5, axis=0),
        "réplicas > 0": (replicas > 0).mean(axis=0),
    }, index=pd.Index(columnas, name="variable"))
    resultado["cruza el cero"] = (resultado["IC 2.5 %"] < 0) & (resultado["IC 97.5 %"] > 0)
    return resultado


def _niveles(df: pd.DataFrame) -> pd.Series:
    """El nivel de cada juego como lo calcula entrenar_modelo: tercios de los scores out-of-fold."""
    X, y, grupos = construir_features(df, conjunto="juego")
    cortes = np.percentile(_scores_oof(X, y, grupos), [100 / 3, 200 / 3])
    juegos = X.groupby(grupos).first()
    scores = construir_pipeline().fit(X, y).predict_proba(juegos)[:, 1]
    return pd.Series(np.select([scores < cortes[0], scores < cortes[1]], ["bajo", "medio"], "alto"), index=juegos.index)


def pr_auc_con_particion(df: pd.DataFrame, folds: pd.Series) -> np.ndarray:
    """PR-AUC por fold con la partición congelada: así dos conjuntos de filas se comparan en los
    mismos juegos de validación, y la diferencia es de los datos y no del reparto."""
    X, y, grupos = construir_features(df, conjunto="juego")
    resultados = []
    for entrenamiento, validacion in splits_de(grupos, folds):
        modelo = construir_pipeline().fit(X.iloc[entrenamiento], y.iloc[entrenamiento])
        resultados.append(average_precision_score(y.iloc[validacion], modelo.predict_proba(X.iloc[validacion])[:, 1]))
    return np.array(resultados)


def impacto_en_modelo_congelado(original: pd.DataFrame, filtrado: pd.DataFrame, folds: pd.Series) -> dict:
    """Qué le pasaría al modelo de riesgo si se entrenara con `filtrado`. No se aplica: el modelo
    congelado se entrena con data-v1 tal cual.

    El PR-AUC se mide con la partición congelada antes y después: la diferencia es de las filas
    quitadas, no del reparto. Los niveles salen como al reentrenar, con la misma partición."""
    niveles_antes, niveles_despues = _niveles(original), _niveles(filtrado)
    comunes = niveles_antes.index.intersection(niveles_despues.index)
    return {"filas quitadas": len(original) - len(filtrado),
            "Y=1 quitadas": int(senal(original).sum() - senal(filtrado).sum()),
            "PR-AUC antes": round(pr_auc_con_particion(original, folds).mean(), 4),
            "PR-AUC después (partición congelada)": round(pr_auc_con_particion(filtrado, folds).mean(), 4),
            "juegos que cambian de nivel al reentrenar": int((niveles_antes[comunes] != niveles_despues[comunes]).sum())}


def log_odds_informativo(textos_a: pd.Series, textos_b: pd.Series, stopwords=None, minimo: int = 20) -> pd.DataFrame:
    """Palabras que distinguen a `a` de `b`: log-odds con prior de Dirichlet informativo (Monroe,
    Colaresi y Quinn, 2008). El prior sale de los dos grupos juntos, así que una palabra rara no
    gana solo por aparecer dos veces. `z` > 0 es más de `a`."""
    vectorizador = CountVectorizer(token_pattern=r"(?u)\b[^\W\d_][\w']+\b", stop_words=list(stopwords) if stopwords else None, min_df=minimo)
    conteos = vectorizador.fit_transform(pd.concat([textos_a, textos_b]))
    y_a = np.asarray(conteos[: len(textos_a)].sum(axis=0)).ravel()
    y_b = np.asarray(conteos[len(textos_a):].sum(axis=0)).ravel()
    alfa = (y_a + y_b) / (y_a + y_b).sum() * 1000
    n_a, n_b, alfa_0 = y_a.sum(), y_b.sum(), alfa.sum()
    delta = np.log((y_a + alfa) / (n_a + alfa_0 - y_a - alfa)) - np.log((y_b + alfa) / (n_b + alfa_0 - y_b - alfa))
    z = delta / np.sqrt(1 / (y_a + alfa) + 1 / (y_b + alfa))
    return pd.DataFrame({"palabra": vectorizador.get_feature_names_out(), "z": z, "en a": y_a, "en b": y_b}).sort_values("z", ascending=False)


def coocurrencia(tabla: pd.DataFrame) -> pd.DataFrame:
    """Cuántas reseñas mencionan cada par de categorías; la diagonal es el total de cada una."""
    m = tabla.astype(int)
    return m.T @ m


def histograma_por_grupo(valores: pd.Series, grupos: pd.Series, bordes: np.ndarray) -> pd.DataFrame:
    """El porcentaje de cada grupo en cada intervalo. La figura guarda estos números y no las
    124 mil filas, para que el notebook no pese decenas de MB."""
    tablas = []
    for grupo, serie in valores.groupby(grupos):
        conteos, _ = np.histogram(serie, bins=bordes)
        tablas.append(pd.DataFrame({"grupo": grupo, "centro": (bordes[:-1] + bordes[1:]) / 2, "%": 100 * conteos / len(serie)}))
    return pd.concat(tablas, ignore_index=True)


def cuantiles_por_grupo(valores: pd.Series, grupos: pd.Series) -> pd.DataFrame:
    """Percentiles 5, 25, 50, 75 y 95 por grupo: lo que dibuja una caja sin guardar las filas."""
    return valores.groupby(grupos).quantile([0.05, 0.25, 0.5, 0.75, 0.95]).unstack().set_axis(["p5", "q1", "mediana", "q3", "p95"], axis=1)


def muestra_estratificada(df: pd.DataFrame, grupos: pd.Series, total: int, semilla: int = SEMILLA) -> pd.DataFrame:
    """La misma cantidad de cada grupo, para que el grupo chico (negativas tempranas) se vea."""
    por_grupo = total // grupos.nunique()
    return df.groupby(grupos, group_keys=False).apply(lambda d: d.sample(min(len(d), por_grupo), random_state=semilla))


def proyeccion_2d(textos: pd.Series, modelo: str, revision: str, semilla: int = SEMILLA) -> np.ndarray:
    """Embeddings → PCA a 50 → t-SNE a 2. Solo intuición visual: las distancias de t-SNE no se
    interpretan. sentence-transformers se importa aquí para que el resto no lo necesite."""
    from huggingface_hub.utils import disable_progress_bars
    from huggingface_hub.utils import logging as registro_hf
    from sentence_transformers import SentenceTransformer
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    from transformers.utils import logging as registro_transformers

    # Sin barras de progreso ni avisos de token en la salida del notebook.
    disable_progress_bars()
    registro_hf.set_verbosity_error()
    registro_transformers.set_verbosity_error()
    registro_transformers.disable_progress_bar()

    vectores = SentenceTransformer(modelo, revision=revision, device="cpu").encode(textos.tolist(), batch_size=64, show_progress_bar=False)
    reducidos = PCA(n_components=50, random_state=semilla).fit_transform(vectores)
    return TSNE(n_components=2, random_state=semilla, init="pca").fit_transform(reducidos)
