"""Genera las cifras, las tablas y las figuras del documento en LaTeX.

Todo sale de los releases con tag fijo (verificados por sha256), de docs/evidencia/ y de las
capturas de docs/capturas/documento/. Las secciones usan las macros de tables/cifras.tex:
ningún número se escribe a mano. Las tasas llevan en el nombre si son por reseña (PorResena)
o el promedio de las tasas por juego (PromJuegos).

Correr desde la raíz:
  .venv/bin/python documento/generar_figuras.py

Escribe documento/tables/, documento/figures/ y copia las capturas a documento/figures/capturas/.
Los releases se guardan en documento/.cache/ (ignorada por git) y se reutilizan si su sha256
sigue siendo el publicado.
"""

import ast
import base64
import contextlib
import csv
import hashlib
import io
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
# El código del proyecto vive en backend/; docs/ y documento/ siguen en la raíz.
BACKEND = RAIZ / "backend"
sys.path[:0] = [str(BACKEND), str(BACKEND / "modelado"), str(BACKEND / "calidad"), str(BACKEND / "analisis")]

import exploracion as ex  # noqa: E402
import limpieza as li  # noqa: E402
import motivos  # noqa: E402

from bootstrap_prueba_externa import RELEASES as RELEASES_V1_V2  # noqa: E402
from despliegue.preparar_entorno import ENTRENAMIENTO_REF, SERVIDO_REF, SERVIDO_SHA256  # noqa: E402
from despliegue.utilidades import GITHUB_REPO, descargar_verificado  # noqa: E402
from entrenar_baseline import cargar_datos, construir_features, construir_pipeline, evaluar_gkf  # noqa: E402
from entrenar_modelo import _scores_oof  # noqa: E402

DOCUMENTO = RAIZ / "documento"
CACHE = DOCUMENTO / ".cache"
TABLAS = DOCUMENTO / "tables"
FIGURAS = DOCUMENTO / "figures"
EVIDENCIA = RAIZ / "docs" / "evidencia"
CAPTURAS = RAIZ / "docs" / "capturas" / "documento"
RELEASES = {**RELEASES_V1_V2, SERVIDO_REF: SERVIDO_SHA256}

# La paleta del frontend (tema claro), la misma de main.tex. «serie» es el acento un paso más
# saturado: #0E738F no llega al piso de croma del validador de paletas (0.093 < 0.1).
# «negativa» es el par de «serie» para dos grupos que no son niveles de riesgo (ΔE 20 con daltonismo).
PALETA = {"bajo": "#047857", "medio": "#AA4F0A", "alto": "#BE123C", "acento": "#0E738F", "serie": "#0A7EA4",
          "negativa": "#C2410C",
          "nia": "#6D28D9", "neutro": "#475585", "tinta": "#0B0F1F", "tinta_suave": "#4A5279", "rejilla": "#DDE1EE"}
ANCHO_DE_TEXTO = 16 / 2.54  # pulgadas: A4 menos los márgenes de 2.5 cm
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")
MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


# --- formato ---------------------------------------------------------------

def entero(n: int) -> str:
    return f"{n:,}"


def decimal(x: float, decimales: int) -> str:
    return f"{x:.{decimales}f}"


def con_signo(x: float, decimales: int) -> str:
    """Con el signo menos tipográfico: −0.56, no -0.56."""
    return decimal(x, decimales).replace("-", "−")


def decimales_pr_auc(x: float) -> int:
    return 2 - math.floor(math.log10(abs(x)))


def pr_auc(x: float) -> str:
    """Todo PR-AUC con tres cifras significativas: 0.0694, 0.146, 0.369. Así los cocientes que publica el
    documento salen de las mismas cifras que muestra, también con prevalencias cercanas al 2 %."""
    return decimal(x, decimales_pr_auc(x))


def junto_a(x: float, estimacion: float) -> str:
    """Una desviación, un extremo de intervalo o una diferencia, con los decimales de su PR-AUC."""
    return decimal(x, decimales_pr_auc(estimacion))


def porcentaje(x: float, decimales: int = 2) -> str:
    """x es una proporción: 0.0219 → «2.19 %»."""
    return f"{100 * x:.{decimales}f}\\,\\%"


def fecha_larga(momento: datetime) -> str:
    return f"{momento.day} de {MESES[momento.month - 1]} de {momento.year}"


def de_unix(segundos: int) -> datetime:
    return datetime.fromtimestamp(segundos, timezone.utc)


def de_iso(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


def macros_usadas() -> set[str]:
    """Las macros \\cifra… que aparecen en main.tex y en sections/."""
    fuentes = [DOCUMENTO / "main.tex", *sorted((DOCUMENTO / "sections").glob("*.tex"))]
    return {nombre for ruta in fuentes for nombre in re.findall(r"\\cifra([A-Za-z]+)", ruta.read_text(encoding="utf-8"))}


class Cifras:
    """Junta las macros con su fuente y las escribe en tables/cifras.tex."""

    def __init__(self):
        self.macros: dict[str, tuple[str, str]] = {}

    def agregar(self, nombre: str, valor: str, fuente: str) -> None:
        if not nombre.isalpha():
            raise ValueError(f"una macro de LaTeX solo lleva letras: {nombre}")
        if nombre in self.macros:
            raise ValueError(f"macro repetida: {nombre}")
        self.macros[nombre] = (valor, fuente)

    def escribir(self) -> Path:
        """Solo las macros que usa el texto. Las demás se calculan porque protegen una aserción, pero no van
        al documento ni a la lista canónica."""
        usadas = macros_usadas()
        lineas = ["% Generado por documento/generar_figuras.py. No se edita a mano.", ""]
        for nombre, (valor, fuente) in self.macros.items():
            if nombre in usadas:
                lineas.append(f"\\newcommand{{\\cifra{nombre}}}{{{valor}}}  % {fuente}")
        self.escritas = len(lineas) - 2
        ruta = TABLAS / "cifras.tex"
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return ruta


# --- datos -----------------------------------------------------------------

def bajar(ref: str) -> Path:
    """El release descomprimido, reutilizado si ya se bajó con el sha256 publicado."""
    destino = CACHE / f"nexplay_{ref}.db"
    marca = destino.with_suffix(".sha256")
    if destino.exists() and marca.exists() and marca.read_text().strip() == RELEASES[ref]:
        return destino
    descargar_verificado(ref, RELEASES[ref], destino)
    marca.write_text(RELEASES[ref])
    return destino


def publicacion_de_releases() -> dict[str, dict]:
    """Fecha de publicación y tamaño de cada asset, de la API de GitHub (guardada en .cache)."""
    ruta = CACHE / "releases.json"
    if not ruta.exists():
        with urllib.request.urlopen(f"https://api.github.com/repos/{GITHUB_REPO}/releases", timeout=60) as resp:
            ruta.write_bytes(resp.read())
    salida = {}
    for release in json.loads(ruta.read_text()):
        salida[release["tag_name"]] = {
            "publicado": release["published_at"][:10],
            "assets": {a["name"]: {"bytes": a["size"], "sha256": (a.get("digest") or "").removeprefix("sha256:")}
                       for a in release["assets"]},
        }
    return salida


def conteos(db: Path, appids: set[int] | None = None) -> dict:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        filas = con.execute("SELECT appid, playtime_at_review, voted_up FROM resenas").fetchall()
    finally:
        con.close()
    filas = [f for f in filas if appids is None or f[0] in appids]
    positivos = sum(1 for _, minutos, voto in filas if minutos < 120 and voto == 0)
    return {"juegos": len({f[0] for f in filas}), "resenas": len(filas), "positivos": positivos,
            "prevalencia": positivos / len(filas)}


# --- cifras ----------------------------------------------------------------

def cifras_de_datos(cifras: Cifras, rutas: dict[str, Path]) -> None:
    entrenamiento = conteos(rutas["data-v1"])
    catalogo = conteos(rutas[SERVIDO_REF])
    appids_v1 = {int(f["appid"]) for f in csv.DictReader(open(BACKEND / "referencias" / "particion_gkf_data-v1.csv"))}
    todos = {f[0] for f in sqlite3.connect(f"file:{rutas[SERVIDO_REF]}?mode=ro", uri=True).execute(
        "SELECT DISTINCT appid FROM resenas")}
    externos = conteos(rutas[SERVIDO_REF], todos - appids_v1)
    for nombre, c, ref in (("Entrenamiento", entrenamiento, "data-v1"), ("Catalogo", catalogo, SERVIDO_REF),
                           ("Externos", externos, f"{SERVIDO_REF} sin los appids de data-v1")):
        cifras.agregar(f"Juegos{nombre}", entero(c["juegos"]), ref)
        cifras.agregar(f"Resenas{nombre}", entero(c["resenas"]), ref)
        cifras.agregar(f"Positivos{nombre}", entero(c["positivos"]), f"{ref}: minutos < 120 y voto negativo")
        cifras.agregar(f"Prevalencia{nombre}PorResena", porcentaje(c["prevalencia"]), ref)


def percentiles_de_los_cortes() -> list[float]:
    """Los percentiles con que entrenar_modelo.py corta las bandas, leídos de su código: el segundo argumento de
    cada np.percentile, una expresión de constantes como «100 / 3»."""
    arbol = ast.parse((BACKEND / "modelado" / "entrenar_modelo.py").read_text(encoding="utf-8"))
    llamadas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "percentile"]
    percentiles = []
    for llamada in llamadas:
        expresion = llamada.args[1]
        if not all(isinstance(n, (ast.Constant, ast.BinOp, ast.operator)) for n in ast.walk(expresion)):
            raise ValueError(f"el percentil de entrenar_modelo.py no es una expresión de constantes: {ast.unparse(expresion)}")
        percentiles.append(float(eval(compile(ast.Expression(expresion), "entrenar_modelo.py", "eval"), {"__builtins__": {}})))
    if len(percentiles) != 2:
        raise ValueError(f"entrenar_modelo.py tiene {len(percentiles)} cortes por percentil, no dos")
    return sorted(percentiles)


def cifras_del_modelo(cifras: Cifras, rutas: dict[str, Path]) -> dict:
    """El PR-AUC por fold del modelo y del trivial, los cortes de las bandas y el modelo entrenado con todo
    data-v1, como lo arma entrenar_modelo.py."""
    df = cargar_datos(rutas["data-v1"])
    X, y, grupos = construir_features(df, conjunto="juego")
    with contextlib.redirect_stdout(io.StringIO()):
        modelo = evaluar_gkf(construir_pipeline(), X, y, grupos, "juego")
        trivial = evaluar_gkf(DummyClassifier(strategy="prior"), X, y, grupos, "trivial")
    fuente = "GroupKFold de 5 por appid sobre data-v1 (evaluar_gkf)"
    cifras.agregar("PRAUCModelo", pr_auc(modelo.mean()), fuente)
    cifras.agregar("PRAUCModeloStd", junto_a(modelo.std(), modelo.mean()), fuente)
    cifras.agregar("PRAUCTrivial", pr_auc(trivial.mean()), fuente + "; trivial = prevalencia de cada pliegue")
    cifras.agregar("PRAUCTrivialStd", junto_a(trivial.std(), trivial.mean()), fuente)
    # Un decimal: la variación entre folds no justifica centésimas. La prueba externa sigue la misma regla.
    cifras.agregar("PRAUCCociente", decimal(modelo.mean() / trivial.mean(), 1), fuente)
    cifras.agregar("PliegosGanados", str(int((modelo > trivial).sum())), fuente + ": pliegues donde el modelo supera al trivial")
    cifras.agregar("Pliegues", str(len(modelo)), fuente)

    percentiles = percentiles_de_los_cortes()
    cortes = np.percentile(_scores_oof(X, y, grupos), percentiles)
    fuente_cortes = "backend/modelado/entrenar_modelo.py: np.percentile de los scores fuera de fold de las reseñas"
    cifras.agregar("PercentilMedio", decimal(percentiles[0], 1), fuente_cortes)
    cifras.agregar("PercentilAlto", decimal(percentiles[1], 1), fuente_cortes)
    cifras.agregar("UmbralMedio", decimal(cortes[0], 4), fuente_cortes + ", con el percentil del corte medio")
    cifras.agregar("UmbralAlto", decimal(cortes[1], 4), fuente_cortes + ", con el percentil del corte alto")

    cocientes = modelo / trivial
    cifras.agregar("PRAUCFoldMin", pr_auc(modelo.min()), fuente + ": el fold más bajo")
    cifras.agregar("PRAUCFoldMax", pr_auc(modelo.max()), fuente + ": el fold más alto")
    cifras.agregar("CocienteFoldMin", decimal(cocientes.min(), 1), fuente + ": modelo entre trivial, el fold más bajo")
    cifras.agregar("CocienteFoldMax", decimal(cocientes.max(), 1), fuente + ": modelo entre trivial, el fold más alto")
    return {"modelo": modelo, "trivial": trivial, "cortes": cortes, "pipeline": construir_pipeline().fit(X, y),
            "columnas": list(X.columns), "mediana_metacritic": df["metacritic"].median()}


def cifras_de_bandas(cifras: Cifras) -> None:
    bandas = json.loads((BACKEND / "referencias" / "bandas_referencia.json").read_text())["bandas"]
    bandas = {int(appid): (b if isinstance(b, str) else b.get("banda")) for appid, b in bandas.items()}
    appids_v1 = {int(f["appid"]) for f in csv.DictReader(open(BACKEND / "referencias" / "particion_gkf_data-v1.csv"))}
    for nombre, appids in (("Entrenamiento", appids_v1), ("Catalogo", set(bandas))):
        for banda in ("bajo", "medio", "alto"):
            cifras.agregar(f"{banda.capitalize()}{nombre}", str(sum(1 for a in appids if bandas[a] == banda)),
                           "backend/referencias/bandas_referencia.json")


def cifras_de_evidencia(cifras: Cifras) -> None:
    externa = json.loads((EVIDENCIA / "prueba-externa.json").read_text())["resumen"]
    bootstrap = json.loads((EVIDENCIA / "bootstrap-prueba-externa.json").read_text())
    cifras.agregar("PRAUCExterno", pr_auc(externa["pr_auc_externo"]), "docs/evidencia/prueba-externa.json")
    cifras.agregar("PRAUCExternoTrivial", pr_auc(externa["pr_auc_trivial"]), "docs/evidencia/prueba-externa.json")
    cifras.agregar("PRAUCExternoCociente", decimal(externa["pr_auc_externo"] / externa["pr_auc_trivial"], 1),
                   "docs/evidencia/prueba-externa.json")
    inf, sup = bootstrap["bootstrap"]["ic95_cociente"]
    cifras.agregar("ExternoICInf", decimal(inf, 2), "docs/evidencia/bootstrap-prueba-externa.json")
    cifras.agregar("ExternoICSup", decimal(sup, 2), "docs/evidencia/bootstrap-prueba-externa.json")
    cifras.agregar("ExternoReplicasSinVentaja", str(bootstrap["bootstrap"]["replicas_con_cociente_hasta_1"]),
                   "réplicas del bootstrap con cociente ≤ 1")
    cifras.agregar("ExternoReplicas", entero(bootstrap["bootstrap"]["replicas"]), "docs/evidencia/bootstrap-prueba-externa.json")

    biblioteca = json.loads((EVIDENCIA / "senal-por-biblioteca.json").read_text())["original"]
    veterano = re.search(r"veteranos: (\d+) o más", biblioteca["definicion"])[1]
    cifras.agregar("UmbralVeterano", veterano, "docs/evidencia/senal-por-biblioteca.json: definición de veterano")
    for grupo in ("novatos", "veteranos"):
        g = biblioteca["grupos"][grupo]
        cifras.agregar(f"{grupo.capitalize()}PorResena", porcentaje(g["por_resena_pct"] / 100),
                       "docs/evidencia/senal-por-biblioteca.json")
        cifras.agregar(f"{grupo.capitalize()}PromJuegos", porcentaje(g["prom_juegos_pct"] / 100),
                       "docs/evidencia/senal-por-biblioteca.json")
    estratificada = json.loads((EVIDENCIA / "senal-por-biblioteca-estratificada.json").read_text())
    # Un cociente: un decimal, como los cocientes contra el trivial. Los extremos de su intervalo, dos.
    cifras.agregar("RazonMH", decimal(estratificada["razon_mh"], 1), "docs/evidencia/senal-por-biblioteca-estratificada.json")
    inf, sup = estratificada["bootstrap"]["ic95_razon_mh"]
    cifras.agregar("RazonMHICInf", decimal(inf, 2), "docs/evidencia/senal-por-biblioteca-estratificada.json")
    cifras.agregar("RazonMHICSup", decimal(sup, 2), "docs/evidencia/senal-por-biblioteca-estratificada.json")


def cifras_del_periodo(cifras: Cifras, rutas: dict[str, Path]) -> None:
    """Cuándo se publicaron las reseñas y cuándo se bajaron. Fechas en UTC."""
    julio = datetime(2025, 7, 1, tzinfo=timezone.utc).timestamp()
    for nombre, ref in (("Entrenamiento", "data-v1"), ("Catalogo", SERVIDO_REF)):
        con = sqlite3.connect(f"file:{rutas[ref]}?mode=ro", uri=True)
        creadas = np.array([f[0] for f in con.execute("SELECT timestamp_created FROM resenas")])
        descargas = con.execute("SELECT min(descargado_en), max(descargado_en) FROM resenas").fetchone()
        con.close()
        cifras.agregar(f"DesdeJulio{nombre}PorResena", porcentaje((creadas >= julio).mean(), 1),
                       f"{ref}: reseñas publicadas desde el 1 de julio de 2025 (UTC)")
        cifras.agregar(f"ResenaMasAntigua{nombre}", fecha_larga(de_unix(creadas.min())), f"{ref}: timestamp_created mínimo")
        cifras.agregar(f"ResenaMasReciente{nombre}", fecha_larga(de_unix(creadas.max())), f"{ref}: timestamp_created máximo")
        cifras.agregar(f"DescargaDesde{nombre}", fecha_larga(de_iso(descargas[0])), f"{ref}: resenas.descargado_en mínimo")
        cifras.agregar(f"DescargaHasta{nombre}", fecha_larga(de_iso(descargas[1])), f"{ref}: resenas.descargado_en máximo")

    juegos, resenas = ex.cargar_release(rutas["data-v1"])
    cobertura = ex.cobertura_por_juego(resenas, juegos)
    cifras.agregar("TopeIngesta", entero(ex.TOPE_DE_LA_INGESTA), "backend/ingesta/ingesta_steam.py: MAX_RESENAS_POR_JUEGO")
    cifras.agregar("JuegosEnElTope", str(int((cobertura["reseñas"] >= ex.TOPE_DE_LA_INGESTA).sum())),
                   "data-v1: juegos con el tope de reseñas")
    dias = cobertura["días cubiertos"]
    cifras.agregar("DiasCubiertosMin", entero(int(dias.min())), "data-v1: días entre la primera y la última reseña")
    cifras.agregar("DiasCubiertosMax", entero(int(dias.max())), "data-v1: días entre la primera y la última reseña")
    cifras.agregar("DiasCubiertosMediana", entero(int(round(dias.median()))), "data-v1: mediana de días cubiertos")


def cifras_del_objetivo(cifras: Cifras, rutas: dict[str, Path]) -> None:
    """§6: dónde caen las reseñas respecto a 120 minutos y qué tanto importa el umbral."""
    _, resenas = ex.cargar_release(rutas["data-v1"])
    minutos, voto = resenas["playtime_at_review"], resenas["voted_up"]
    prevalencia = ex.senal(resenas).mean()
    cifras.agregar("ExactitudTrivialPorResena", porcentaje(1 - prevalencia), "data-v1: aciertos de decir siempre «no»")
    for nombre, pulgar in (("Negativas", 0), ("Positivas", 1)):
        cifras.agregar(f"{nombre}AntesDelUmbralPorResena", porcentaje((minutos[voto == pulgar] < ex.UMBRAL_REEMBOLSO).mean(), 1),
                       f"data-v1: reseñas {nombre.lower()} escritas antes de 120 minutos")
    ventanas = {"AntesDelUmbral": (110, 120), "DespuesDelUmbral": (120, 130), "AntesDeTresHoras": (170, 180),
                "DesdeTresHoras": (180, 190)}
    for nombre, pulgar in (("Negativas", 0), ("Positivas", 1)):
        for ventana, (desde, hasta) in ventanas.items():
            por_minuto = (minutos[voto == pulgar].between(desde, hasta - 1)).sum() / (hasta - desde)
            cifras.agregar(f"{nombre}PorMinuto{ventana}", decimal(por_minuto, 1),
                           f"data-v1: reseñas {nombre.lower()} por minuto entre {desde} y {hasta - 1}")
    juegos = resenas.loc[minutos.between(180, 189) & (voto == 1), "appid"].nunique()
    cifras.agregar("JuegosSaltoTresHoras", str(juegos), "data-v1: juegos con positivas entre 180 y 189 minutos")

    sensibilidad = ex.sensibilidad_umbral(resenas)
    otros = sensibilidad.drop(index=ex.UMBRAL_REEMBOLSO)["Spearman con 120"]
    cifras.agregar("SpearmanUmbralMin", decimal(otros.min(), 2), "Spearman del orden de los juegos con 60, 90 y 180 contra 120")
    cifras.agregar("SpearmanUmbralMax", decimal(otros.max(), 2), "Spearman del orden de los juegos con 60, 90 y 180 contra 120")


def figura_minutos_al_resenar(rutas: dict[str, Path]) -> Path:
    """F2: minutos jugados al reseñar, por pulgar, en escala log. Intervalos del mismo ancho en log,
    con un borde en 180 y ninguno en 120, como en el notebook 00."""
    _, resenas = ex.cargar_release(rutas["data-v1"])
    pulgar = resenas["voted_up"].map({1: "positivas", 0: "negativas"})
    log_minutos = np.log10(resenas["playtime_at_review"] + 1)
    ancho = np.log10(181) / 22
    bordes = np.arange(0, log_minutos.max() + ancho, ancho)
    if np.isclose(10 ** bordes - 1, ex.UMBRAL_REEMBOLSO, atol=1).any():
        raise ValueError("un borde de la figura cae en 120 minutos")
    barras = ex.histograma_por_grupo(log_minutos, pulgar, bordes)

    fig, eje = plt.subplots(figsize=(ANCHO_DE_TEXTO, 2.35))
    for grupo, color in (("positivas", PALETA["serie"]), ("negativas", PALETA["negativa"])):
        porcentajes = barras.loc[barras["grupo"] == grupo, "%"].to_numpy()
        eje.step(bordes, np.append(porcentajes, porcentajes[-1]), where="post", color=color, linewidth=1.6, label=grupo)
    for minutos, estilo, texto, lado in ((120, (0, (4, 3)), "120 min: ventana de reembolso", "right"),
                                         (180, (0, (1, 2)), "180 min: salto de las positivas", "left")):
        x = np.log10(minutos + 1)
        eje.axvline(x, color=PALETA["tinta_suave"], linewidth=0.8, linestyle=estilo)
        eje.annotate(texto, xy=(x, 1), xycoords=("data", "axes fraction"), xytext=(-4 if lado == "right" else 4, -2),
                     textcoords="offset points", ha=lado, va="top", fontsize=7.5, color=PALETA["tinta"])
    marcas = [10, 120, 600, 6_000, 60_000]
    eje.set_xticks(np.log10(np.array(marcas) + 1), [f"{m:,}" for m in marcas])
    eje.set_xlabel("minutos jugados al escribir la reseña (escala log)")
    eje.set_ylabel("% de las reseñas del grupo")
    # Aire arriba para las etiquetas de las líneas; la leyenda, donde las curvas ya bajaron.
    eje.set_ylim(0, barras["%"].max() * 1.3)
    eje.legend(frameon=False, loc="upper right", fontsize=8)
    return guardar_figura(fig, "minutos-al-resenar")


def cifras_por_juego(cifras: Cifras, juegos: pd.DataFrame, resenas: pd.DataFrame) -> pd.DataFrame:
    """§7.1 y §7.2: la tasa de señal de cada juego de data-v1 y qué tanto varía entre juegos."""
    if (ex.variables_constantes_por_juego(ex.con_juego(resenas, juegos)) > 0).any():
        raise ValueError("una variable del modelo cambia dentro de un juego")
    por_juego = ex.tasa_por_juego(resenas, juegos)
    con_nota = por_juego["metacritic"].notna()
    fuente = "data-v1: tasa de señal de cada juego"
    cifras.agregar("TasaJuegoMinPorResena", porcentaje(por_juego["tasa"].min()), fuente + ", la menor")
    cifras.agregar("TasaJuegoMaxPorResena", porcentaje(por_juego["tasa"].max()), fuente + ", la mayor")
    cifras.agregar("ResenasJuegoMin", entero(int(por_juego["reseñas"].min())), "data-v1: reseñas del juego con menos")
    cifras.agregar("NivelDeConfianza", porcentaje(0.95, 0), "intervalos de Wilson (z = 1.96) y del bootstrap (percentiles 2.5 y 97.5)")
    cifras.agregar("Sobredispersion", entero(round(ex.sobredispersion(por_juego))),
                   "data-v1: ji cuadrada de Pearson entre sus grados de libertad (ex.sobredispersion)")
    cifras.agregar("TasaConNotaMedianaJuegos", porcentaje(por_juego.loc[con_nota, "tasa"].median()),
                   fuente + ", mediana de los que tienen nota de Metacritic")
    cifras.agregar("TasaSinNotaMedianaJuegos", porcentaje(por_juego.loc[~con_nota, "tasa"].median()),
                   fuente + ", mediana de los que no tienen nota")
    return por_juego


def cifras_de_correlaciones(cifras: Cifras, por_juego: pd.DataFrame) -> None:
    """§5.4: Spearman de la tasa por juego contra cada variable del juego (00 §3.4). El texto dice que solo
    la crítica se aleja del azar, con valores p por debajo de una milésima."""
    correlaciones = ex.correlaciones_del_juego(por_juego)
    critica = ["tiene nota de la crítica", "nota de la crítica (con nota)"]
    if (correlaciones.loc[critica, "p"] >= 0.001).any() or (correlaciones.drop(index=critica)["p"] < 0.05).any():
        raise ValueError("cambió qué variables del juego se alejan del azar")
    fuente = "data-v1: Spearman de la tasa por juego (ex.correlaciones_del_juego)"
    for nombre, variable in (("TieneNota", "tiene nota de la crítica"), ("Nota", "nota de la crítica (con nota)"),
                             ("Precio", "precio (juegos de pago)")):
        cifras.agregar(f"Spearman{nombre}", con_signo(correlaciones.loc[variable, "Spearman"], 2), fuente)
    cifras.agregar("SpearmanPrecioP", decimal(correlaciones.loc["precio (juegos de pago)", "p"], 2), fuente + ": valor p")
    cifras.agregar("GratisEntrenamiento", str(int(por_juego["es_gratis"].sum())), "data-v1: juegos gratis")


def cifras_de_coeficientes(cifras: Cifras, juegos: pd.DataFrame, resenas: pd.DataFrame) -> pd.DataFrame:
    """§7.2 y §9.4: los coeficientes del modelo B+ con su IC al 95 % por bootstrap sobre juegos."""
    coeficientes = ex.coeficientes_con_bootstrap(ex.con_juego(resenas, juegos))
    # Lo que dice el texto: con todo junto, solo la crítica se aleja del cero.
    if coeficientes.loc[["metacritic_disponible", "metacritic"], "cruza el cero"].any():
        raise ValueError("un coeficiente de la crítica ya cruza el cero")
    if not coeficientes.loc[["log_precio_final", "descuento", "es_gratis"], "cruza el cero"].all():
        raise ValueError("el precio, el descuento o la gratuidad ya no cruzan el cero")
    fuente = "data-v1: ex.coeficientes_con_bootstrap, 1,000 réplicas sobre appid"
    for nombre, variable in (("TieneNota", "metacritic_disponible"), ("Nota", "metacritic"), ("Precio", "log_precio_final"),
                             ("Descuento", "descuento"), ("Gratis", "es_gratis")):
        cifras.agregar(f"Coef{nombre}ICInf", con_signo(coeficientes.loc[variable, "IC 2.5 %"], 2), fuente)
        cifras.agregar(f"Coef{nombre}ICSup", con_signo(coeficientes.loc[variable, "IC 97.5 %"], 2), fuente)
    cifras.agregar("CoefPrecioReplicasPositivas", porcentaje(coeficientes.loc["log_precio_final", "réplicas > 0"], 1),
                   fuente + ": réplicas con el coeficiente del precio mayor que cero")
    return coeficientes


def tabla_de_conjuntos(cifras: Cifras, juegos: pd.DataFrame, resenas: pd.DataFrame, trivial: np.ndarray) -> Path:
    """§9.1 y §9.2 (T9): el mismo modelo con los conjuntos juego, compra y completo, contra el trivial
    (01, celdas 31 a 33, y docs/evidencia/simulacion_123.txt para las 30 particiones)."""
    df = ex.con_juego(resenas, juegos)
    resultados, variables = {}, {}
    for conjunto in ("juego", "compra", "completo"):
        X, y, grupos = construir_features(df, conjunto=conjunto)
        with contextlib.redirect_stdout(io.StringIO()):
            resultados[conjunto] = evaluar_gkf(construir_pipeline(), X, y, grupos, conjunto)
        variables[conjunto] = X.shape[1]
    juego, compra = resultados["juego"], resultados["compra"]
    if pr_auc(juego.mean()) != cifras.macros["PRAUCModelo"][0]:
        raise ValueError("el conjunto juego ya no da el PR-AUC del modelo")
    fuente = "GroupKFold de 5 por appid sobre data-v1 (evaluar_gkf)"
    for conjunto in ("compra", "completo"):
        cifras.agregar(f"PRAUC{conjunto.capitalize()}", pr_auc(resultados[conjunto].mean()), fuente + f", conjunto {conjunto}")
        cifras.agregar(f"PRAUC{conjunto.capitalize()}Std", junto_a(resultados[conjunto].std(), resultados[conjunto].mean()), fuente + f", conjunto {conjunto}")
    cifras.agregar("DiferenciaCompraJuego", junto_a(compra.mean() - juego.mean(), juego.mean()), fuente + ": compra menos juego")
    cifras.agregar("FoldsCompraGana", str(int((compra > juego).sum())), fuente + ": folds donde compra supera a juego")

    # Las 30 particiones no se recalculan aquí (tardan minutos); se lee la evidencia y se comprueba que
    # corresponda a este modelo.
    simulacion = (EVIDENCIA / "simulacion_123.txt").read_text(encoding="utf-8").split("===== data-v2")[0]
    medias = re.findall(r"^\s+(?:juego|compra)\s+por fold: .*media=([\d.]+)", simulacion, re.M)
    if medias != [decimal(juego.mean(), 4), decimal(compra.mean(), 4)]:
        raise ValueError("docs/evidencia/simulacion_123.txt ya no corresponde al modelo")
    gana, total = re.search(r"particiones donde compra supera a juego: (\d+)/(\d+)", simulacion).groups()
    cifras.agregar("ParticionesCompraGana", gana, "docs/evidencia/simulacion_123.txt, data-v1")
    cifras.agregar("ParticionesSimuladas", total, "docs/evidencia/simulacion_123.txt, data-v1")

    descripcion = {"juego": "gratuidad, precio, descuento y crítica", "compra": "las de juego y los juegos del autor",
                   "completo": "las de compra, la bandera de perfil privado y las posteriores a la reseña"}
    trivial_media = trivial.mean()
    filas = [f"Trivial & ninguna & 0 & {cifras.macros['PRAUCTrivial'][0]} & {cifras.macros['PRAUCTrivialStd'][0]} & "
             f"{decimal(1, 1)}× \\\\"]
    for conjunto in ("juego", "compra", "completo"):
        nombre = "Juego (el del sitio)" if conjunto == "juego" else conjunto.capitalize()
        veces = decimal(resultados[conjunto].mean() / trivial_media, 1)
        if conjunto != "completo" and veces != cifras.macros[f"VecesTrivial{conjunto.capitalize()}"][0]:
            raise ValueError(f"las veces el trivial de {conjunto} no son las que imprime el 01")
        filas.append(f"{nombre} & {descripcion[conjunto]} & {variables[conjunto]} & {pr_auc(resultados[conjunto].mean())} & "
                     f"{junto_a(resultados[conjunto].std(), resultados[conjunto].mean())} & "
                     f"{veces}× \\\\")
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{l >{\\raggedright\\arraybackslash}X rrrr}", "\\toprule",
        "Conjunto & Variables & Cuántas & PR-AUC & \\begin{tabular}[b]{@{}r@{}}Desv. entre\\\\folds\\end{tabular} & "
        "\\begin{tabular}[b]{@{}r@{}}Veces el\\\\trivial\\end{tabular} \\\\", "\\midrule",
        *filas, "\\bottomrule", "\\end{tabularx}",
    ]
    ruta = TABLAS / "conjuntos.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def cifras_de_la_particion(cifras: Cifras, juegos: pd.DataFrame, resenas: pd.DataFrame) -> None:
    """§9.3: el PR-AUC con reseñas repartidas al azar (00, celda 73), con otras particiones por juego
    (celda 74) y con la partición que arma scikit-learn en Colab (docs/evidencia/particion-alternativa.json)."""
    df = ex.con_juego(resenas, juegos)
    aleatorio = ex.kfold_contra_groupkfold(df).loc["KFold aleatorio (fuga)"]
    fuente = "data-v1: KFold de 5 sobre reseñas, sin agrupar por juego (ex.kfold_contra_groupkfold)"
    cifras.agregar("PRAUCKFold", pr_auc(aleatorio["PR-AUC media"]), fuente)
    cifras.agregar("PRAUCKFoldStd", junto_a(aleatorio["std entre folds"], aleatorio["PR-AUC media"]), fuente)
    particiones = ex.sensibilidad_a_la_particion(df)
    fuente = "data-v1: GroupKFold con los juegos repartidos al azar (ex.sensibilidad_a_la_particion)"
    cifras.agregar("ParticionesAleatorias", str(len(particiones)), fuente)
    cifras.agregar("PRAUCParticionMin", pr_auc(particiones.min()), fuente)
    cifras.agregar("PRAUCParticionMax", pr_auc(particiones.max()), fuente)
    cifras.agregar("JuegosEmpatadosEnElTope", str(int((resenas.groupby("appid").size() == ex.TOPE_DE_LA_INGESTA).sum())),
                   "data-v1: juegos con exactamente el tope de reseñas")

    evidencia = json.loads((EVIDENCIA / "particion-alternativa.json").read_text())
    if pr_auc(evidencia["resumen"]["congelada"]["pr_auc_media"]) != cifras.macros["PRAUCModelo"][0]:
        raise ValueError("docs/evidencia/particion-alternativa.json ya no corresponde al modelo")
    congelada = ex.leer_particion()
    alternativa = {int(appid): fold for appid, fold in evidencia["particiones"]["alternativa"]["fold_por_appid"].items()}
    fuente = "docs/evidencia/particion-alternativa.json"
    cifras.agregar("VersionSklearnColab", evidencia["entorno"]["scikit-learn"], fuente)
    cifras.agregar("JuegosMismoFoldColab", str(sum(1 for appid, fold in alternativa.items() if congelada[appid] == fold)),
                   fuente + ": juegos con el mismo fold que la partición congelada")
    resumen = evidencia["resumen"]["alternativa"]
    cifras.agregar("PRAUCParticionAlternativa", pr_auc(resumen["pr_auc_media"]), fuente)
    cifras.agregar("PRAUCParticionAlternativaStd", junto_a(resumen["pr_auc_std"], resumen["pr_auc_media"]), fuente)
    cifras.agregar("PliegosGanadosAlternativa", str(resumen["folds_donde_gana_el_modelo"]), fuente)


# Los grupos de §10.3: en las bandas baja y media todos los juegos tienen nota de Metacritic.
GRUPOS_POR_BANDA = (("bajo", True, "Bajo"), ("medio", True, "Medio"), ("alto", True, "AltoConNota"), ("alto", False, "AltoSinNota"))
MACROS_POR_BANDA = {("Entrenamiento", "Bajo"), ("Entrenamiento", "AltoSinNota"), ("Externos", "Bajo"), ("Externos", "Medio"),
                    ("Externos", "AltoSinNota")}


def cifras_por_banda(cifras: Cifras, rutas: dict[str, Path]) -> None:
    """§7.6: la tasa de señal por banda y cobertura de crítica en los 83 (descriptivo: el modelo los vio) y en
    los 40 externos, por reseña y como promedio por juego. Replica docs/evidencia/metacritic-por-banda.md con
    los releases y las bandas de referencia."""
    bandas = {int(appid): b["banda"] for appid, b in json.loads((BACKEND / "referencias" / "bandas_referencia.json").read_text())["bandas"].items()}
    juegos_v1, resenas_v1 = ex.cargar_release(rutas["data-v1"])
    juegos_v2, resenas_v2 = ex.cargar_release(rutas["data-v2"])
    externos = set(juegos_v2["appid"]) - set(juegos_v1["appid"])
    cortes = {"Entrenamiento": ex.tasa_por_juego(resenas_v1, juegos_v1),
              "Externos": ex.tasa_por_juego(resenas_v2[resenas_v2["appid"].isin(externos)], juegos_v2[juegos_v2["appid"].isin(externos)])}
    alto_con_nota, alto_sin_nota = 0, 0
    for corte, por_juego in cortes.items():
        por_juego = por_juego.assign(banda=por_juego.index.map(bandas), con_nota=por_juego["metacritic"].notna())
        if (~por_juego["con_nota"] & (por_juego["banda"] != "alto")).any():
            raise ValueError("hay juegos sin nota fuera de la banda alta")
        for banda, con_nota, nombre in GRUPOS_POR_BANDA:
            grupo = por_juego[(por_juego["banda"] == banda) & (por_juego["con_nota"] == con_nota)]
            fuente = f"{corte.lower()}: banda {banda}, {'con' if con_nota else 'sin'} nota (bandas_referencia.json)"
            cifras.agregar(f"Tasa{nombre}{corte}PorResena", porcentaje(grupo["y1"].sum() / grupo["reseñas"].sum()), fuente)
            cifras.agregar(f"Tasa{nombre}{corte}PromJuegos", porcentaje(grupo["tasa"].mean()), fuente)
            alto_con_nota += len(grupo) if nombre == "AltoConNota" else 0
            alto_sin_nota += len(grupo) if nombre == "AltoSinNota" else 0
    cifras.agregar("JuegosAltoConNota", str(alto_con_nota), "los 123: banda alta con nota de Metacritic")
    cifras.agregar("AltoSinNotaCatalogo", str(alto_sin_nota), "los 123: banda alta sin nota de Metacritic")


def features_como_la_api(juegos: pd.DataFrame, mediana_metacritic: float) -> pd.DataFrame:
    """Las cinco variables de cada juego como las arma backend/api/scoring.py: los faltantes en 0 y la
    nota que falta con la mediana de data-v1."""
    return pd.DataFrame({
        "es_gratis": juegos["es_gratis"].fillna(0).astype(int), "log_precio_final": np.log1p(juegos["precio_final"].fillna(0)),
        "descuento": juegos["descuento"].fillna(0), "metacritic_disponible": juegos["metacritic"].notna().astype(int),
        "metacritic": juegos["metacritic"].fillna(mediana_metacritic),
    })


# La pareja del recorrido de la sección 3 (aprobada por el dueño) y el estante que se abre después.
PAYDAY_3, DEAD_SPACE = 1272080, 1693980
ESTANTE_ACCION_BAJO = ["Grand Theft Auto V Legacy", "Team Fortress 2", "Resident Evil 4", "Apex Legends™"]


def cifras_del_recorrido(cifras: Cifras, rutas: dict[str, Path], modelo: dict) -> None:
    """§3: lo que ve en el sitio quien duda entre PAYDAY 3 y Dead Space, con el precio al corte de datos
    (el día en que se observó, juegos.descargado_en) y los motivos como los calcula /explicacion: sobre las
    reseñas con la señal de cada juego, en porcentaje de las que caen en alguna categoría."""
    juegos = ex.cargar_release(rutas[SERVIDO_REF])[0].set_index("appid")
    X = features_como_la_api(juegos, modelo["mediana_metacritic"])[modelo["columnas"]]
    scores = pd.Series(modelo["pipeline"].predict_proba(X)[:, 1], index=juegos.index)
    medio, alto = modelo["cortes"]
    banda = pd.Series(np.select([scores < medio, scores < alto], ["bajo", "medio"], "alto"), index=juegos.index)
    appids_v1 = {int(f["appid"]) for f in csv.DictReader(open(BACKEND / "referencias" / "particion_gkf_data-v1.csv"))}
    # Lo que dice el texto: PAYDAY 3 es de riesgo alto y se vio al entrenar; Dead Space es de riesgo bajo y es externo.
    if (banda[PAYDAY_3], banda[DEAD_SPACE]) != ("alto", "bajo") or PAYDAY_3 not in appids_v1 or DEAD_SPACE in appids_v1:
        raise ValueError("cambió la pareja del recorrido")
    con = sqlite3.connect(f"file:{rutas[SERVIDO_REF]}?mode=ro", uri=True)
    principal = {PAYDAY_3: "contenido", DEAD_SPACE: "rendimiento"}
    for appid, nombre in ((PAYDAY_3, "Payday"), (DEAD_SPACE, "DeadSpace")):
        juego = juegos.loc[appid]
        fuente = f"{SERVIDO_REF}: {juego['nombre']}"
        cifras.agregar(f"{nombre}Metacritic", str(int(juego["metacritic"])), fuente)
        cifras.agregar(f"{nombre}Precio", f"{juego['precio_final'] / 100:,.2f}", fuente + ", precio_final / 100")
        cifras.agregar(f"{nombre}FechaPrecio", fecha_larga(de_iso(juego["descargado_en"])), fuente + ", juegos.descargado_en (UTC)")
        textos = pd.Series([t for (t,) in con.execute(
            "SELECT texto FROM resenas WHERE appid = ? AND playtime_at_review < ? AND voted_up = 0", (appid, ex.UMBRAL_REEMBOLSO))])
        tabla = motivos.tabla_de_motivos(textos)
        clasificadas = tabla[tabla.any(axis=1)]
        frecuencia = clasificadas.mean().sort_values(ascending=False)
        if frecuencia.index[0] != principal[appid]:
            raise ValueError(f"cambió el motivo principal de {juego['nombre']}")
        cifras.agregar(f"{nombre}Casos", str(len(textos)), fuente + ": reseñas con la señal")
        cifras.agregar(f"{nombre}Clasificadas", str(len(clasificadas)), fuente + ": con al menos un motivo")
        cifras.agregar(f"{nombre}MotivoPrincipal", porcentaje(round(frecuencia.iloc[0], 2), 0),
                       fuente + f": {principal[appid]}, sobre las clasificadas (como /explicacion)")
    con.close()
    dead_space = juegos.loc[DEAD_SPACE]
    cifras.agregar("DeadSpacePrecioInicial", f"{dead_space['precio_inicial'] / 100:,.2f}", f"{SERVIDO_REF}: Dead Space, precio_inicial / 100")
    cifras.agregar("DeadSpaceDescuento", porcentaje(dead_space["descuento"] / 100, 0), f"{SERVIDO_REF}: Dead Space, descuento")

    accion = juegos["generos"].fillna("").str.split("|").map(lambda generos: "Acción" in generos)
    # Como dominio/estantes.ts: en el estante «bajo», del score más bajo al más alto.
    estante = scores[accion & (banda == "bajo")].sort_values()
    if list(juegos.loc[estante.index[:4], "nombre"]) != ESTANTE_ACCION_BAJO:
        raise ValueError("cambiaron las primeras tarjetas del estante de riesgo bajo de Acción")
    cifras.agregar("EstanteAccionBajo", str(len(estante)), f"{SERVIDO_REF}: juegos de Acción con riesgo bajo")
    tactil = re.search(r"\.compacto \{\s*min-height: (\d+)px", (RAIZ / "frontend" / "src" / "styles" / "base.css").read_text(encoding="utf-8"))
    cifras.agregar("ObjetivoTactil", tactil[1], "frontend/src/styles/base.css: min-height de .compacto")


def cifras_de_casos_al_filo(cifras: Cifras, rutas: dict[str, Path], modelo: dict) -> None:
    """§10.4: los juegos más cerca de un corte. Califica los 123 como la API (la nota que falta, con la mediana
    de data-v1) y comprueba que salgan las bandas de referencia."""
    juegos = ex.cargar_release(rutas[SERVIDO_REF])[0].set_index("appid")
    X = features_como_la_api(juegos, modelo["mediana_metacritic"])
    scores = pd.Series(modelo["pipeline"].predict_proba(X)[:, 1], index=juegos.index)
    medio, alto = modelo["cortes"]
    banda = pd.Series(np.select([scores < medio, scores < alto], ["bajo", "medio"], "alto"), index=juegos.index)
    referencia = {int(appid): b["banda"] for appid, b in json.loads((BACKEND / "referencias" / "bandas_referencia.json").read_text())["bandas"].items()}
    if any(referencia[appid] != banda[appid] for appid in juegos.index):
        raise ValueError("los scores ya no dan las bandas de referencia")
    distancia = np.minimum((scores - medio).abs(), (scores - alto).abs()).sort_values()
    # El texto nombra los dos juegos más cerca de un corte.
    if list(juegos.loc[distancia.index[:2], "nombre"]) != ["Hollow Knight", "Warframe"]:
        raise ValueError("cambiaron los juegos más cerca de un corte")
    fuente = "modelo juego entrenado con data-v1, sobre los atributos de " + SERVIDO_REF
    for appid, nombre in zip(distancia.index[:2], ("ScoreHollowKnight", "ScoreWarframe")):
        cifras.agregar(nombre, decimal(scores[appid], 4), fuente)


def constantes_de_scoring() -> dict:
    """UMBRAL_TIPICO, UMBRAL_MIN_CASOS, las etiquetas y la evidencia de cada variable, leídas de
    backend/api/scoring.py sin importarlo: al importarse, la API carga el modelo y la base servida."""
    valores = {}
    for nodo in ast.parse((BACKEND / "api" / "scoring.py").read_text(encoding="utf-8")).body:
        if not (isinstance(nodo, ast.Assign) and isinstance(nodo.targets[0], ast.Name)):
            continue
        nombre = nodo.targets[0].id
        if nombre in ("UMBRAL_TIPICO", "UMBRAL_MIN_CASOS", "_ETIQUETAS_FEATURES"):
            valores[nombre] = ast.literal_eval(nodo.value)
        elif nombre == "_EVIDENCIA_POR_VARIABLE":
            valores[nombre] = {ast.literal_eval(k): v.attr for k, v in zip(nodo.value.keys, nodo.value.values)}
    return valores


def flechas_que_contradicen(juegos: pd.DataFrame, aportes: pd.DataFrame, umbral: float, nota_promedio: float,
                            precio_mediano: float) -> list[str]:
    """Los factores que la ficha mostraría con flecha (entre los tres de mayor aporte, con aporte de al menos
    `umbral`) cuya dirección contradice la cifra que se muestra al lado: una nota por encima del promedio del
    catálogo que sube el riesgo, o un precio por encima de la mediana que lo baja. Replica _factores_prediccion."""
    contradicen = []
    for appid, fila in aportes.iterrows():
        aporte, juego = fila.to_dict(), juegos.loc[appid]
        gratis = bool(juego["es_gratis"])
        if gratis:
            aporte["es_gratis"] += aporte.pop("log_precio_final")
        for variable in sorted(aporte, key=lambda v: abs(aporte[v]), reverse=True)[:3]:
            if abs(aporte[variable]) < umbral:
                continue
            if variable == "metacritic" and pd.notna(juego["metacritic"]) and (juego["metacritic"] > nota_promedio) != (aporte[variable] < 0):
                contradicen.append(juego["nombre"])
            if (variable == "log_precio_final" and not gratis and pd.notna(juego["precio_final"])
                    and (juego["precio_final"] / 100 > precio_mediano) != (aporte[variable] > 0)):
                contradicen.append(juego["nombre"])
    return contradicen


def cifras_de_factores(cifras: Cifras, rutas: dict[str, Path], modelo: dict) -> None:
    """§7.7: las referencias del catálogo contra las que se lee cada factor y UMBRAL_TIPICO, con la comprobación
    de que ninguna flecha contradiga la cifra que muestra la ficha, y de que la evidencia de cada variable sea la
    que dice el texto."""
    scoring = constantes_de_scoring()
    solidas = {v for v, e in scoring["_EVIDENCIA_POR_VARIABLE"].items() if e == "SOLIDA"}
    if solidas != {"metacritic_disponible", "metacritic"}:
        raise ValueError("cambió qué variables tienen evidencia sólida")
    juegos = ex.cargar_release(rutas[SERVIDO_REF])[0].set_index("appid")
    # Como referencias_del_catalogo(): la nota, promedio de los que la tienen; el precio, mediana de los de pago.
    nota_promedio = round(float(juegos["metacritic"].dropna().mean()), 1)
    precio_mediano = round(float((juegos.loc[(juegos["es_gratis"] == 0) & juegos["precio_final"].notna(), "precio_final"] / 100).median()), 2)
    pipeline, columnas = modelo["pipeline"], list(modelo["columnas"])
    escalador, coeficientes = pipeline.named_steps["escalar"], pipeline.named_steps["clf"].coef_[0]
    X = features_como_la_api(juegos, modelo["mediana_metacritic"])[columnas]
    aportes = pd.DataFrame(escalador.transform(X) * coeficientes, index=juegos.index, columns=columnas)
    umbral = scoring["UMBRAL_TIPICO"]
    contradicen = flechas_que_contradicen(juegos, aportes, umbral, nota_promedio, precio_mediano)
    if contradicen:
        raise ValueError(f"con UMBRAL_TIPICO hay flechas que contradicen la cifra de la ficha: {contradicen}")
    fuente = "backend/api/scoring.py"
    cifras.agregar("UmbralTipico", decimal(umbral, 2), fuente + ": UMBRAL_TIPICO")
    cifras.agregar("NotaPromedioCatalogo", decimal(nota_promedio, 1), f"{SERVIDO_REF}: promedio de Metacritic de los juegos que la tienen")
    cifras.agregar("PrecioMedianoCatalogo", decimal(precio_mediano, 2), f"{SERVIDO_REF}: mediana de precio de los de pago con precio")
    cifras.agregar("MediaNotaModelo", decimal(escalador.mean_[columnas.index("metacritic")], 2),
                   "media de metacritic del StandardScaler del modelo (data-v1, con la nota que falta imputada)")


# Las categorías que nombra el texto de §11.5, en el orden de backend/analisis/motivos.py.
CATEGORIAS_DE_MOTIVOS = ["rendimiento", "bugs", "dificultad", "controles", "contenido", "precio"]


def cifras_de_motivos(cifras: Cifras, limpio: pd.DataFrame) -> None:
    """§7.8: qué parte de las negativas tempranas del conjunto limpio menciona algún motivo de la lista de
    palabras clave de /explicacion (00 §3.8). Una reseña puede mencionar varios o ninguno."""
    if list(motivos.PALABRAS_CLAVE_POR_CATEGORIA) != CATEGORIAS_DE_MOTIVOS:
        raise ValueError("cambiaron las categorías de motivos")
    senal = limpio[ex.senal(limpio)]
    tabla = motivos.tabla_de_motivos(senal["texto"])
    cobertura = tabla.any(axis=1).mean()
    por_motivo = tabla.mean().sort_values()
    # El texto dice que rendimiento y bugs son los más frecuentes.
    if set(por_motivo.index[-2:]) != {"rendimiento", "bugs"}:
        raise ValueError("cambiaron los motivos más frecuentes")
    if entero(len(senal)) != cifras.macros["NegativasTempranasLimpias"][0]:
        raise ValueError("las negativas tempranas de los motivos no son las del conjunto limpio")
    scoring = constantes_de_scoring()
    fuente = "conjunto limpio de data-v1: negativas tempranas con al menos un motivo (motivos.tabla_de_motivos)"
    cifras.agregar("CoberturaMotivosPorResena", porcentaje(cobertura, 1), fuente)
    cifras.agregar("SinMotivoPorResena", porcentaje(1 - cobertura, 1), fuente.replace("con al menos un", "sin ningún"))
    cifras.agregar("CategoriasMotivos", str(len(CATEGORIAS_DE_MOTIVOS)), "backend/analisis/motivos.py: PALABRAS_CLAVE_POR_CATEGORIA")
    cifras.agregar("UmbralMinCasos", str(scoring["UMBRAL_MIN_CASOS"]), "backend/api/scoring.py: UMBRAL_MIN_CASOS")


# Los endpoints de backend/api/main.py por grupo, según el primer tramo de la ruta.
GRUPOS_DE_ENDPOINTS = {
    "Riesgo": ("catalogo", "perfil", "prediccion", "explicacion", "panorama"),
    "Comunidad": ("valoraciones", "comentarios"),
    "Nia": ("nia",),
}


def cifras_de_nia(cifras: Cifras) -> None:
    """§8.2: cuántas herramientas tiene Nia y cómo salieron sus pruebas. Los conteos salen del código
    (sin importarlo) y los resultados, de docs/evidencia/nia-pruebas.md, que deben cuadrar con ellos."""
    herramientas = len(re.findall(r'"name": "', (BACKEND / "api" / "nia" / "herramientas.py").read_text(encoding="utf-8")))
    preguntas = next(len(nodo.value.elts) for nodo in ast.parse((BACKEND / "calidad" / "preguntas_nia.py").read_text(encoding="utf-8")).body
                     if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", "") == "PREGUNTAS")
    trampas = len(json.loads((BACKEND / "calidad" / "preguntas_trampa.json").read_text(encoding="utf-8"))["casos"])
    evidencia = (EVIDENCIA / "nia-pruebas.md").read_text(encoding="utf-8")
    aprobadas, total = re.search(r"(\d+) de (\d+) en las dos corridas", evidencia).groups()
    dia, respuestas, por_revisar = re.search(r"\((\d+) de septiembre, (\d+) respuestas\) terminó con (\d+) casos por revisar", evidencia).groups()
    if int(total) != preguntas or int(respuestas) != trampas:
        raise ValueError("docs/evidencia/nia-pruebas.md ya no corresponde a las preguntas del repo")
    cifras.agregar("NiaHerramientas", str(herramientas), "backend/api/nia/herramientas.py: esquemas de herramientas")
    cifras.agregar("PreguntasNia", str(preguntas), "backend/calidad/preguntas_nia.py: PREGUNTAS")
    cifras.agregar("PreguntasNiaAprobadas", aprobadas, "docs/evidencia/nia-pruebas.md: regresión")
    cifras.agregar("PreguntasTrampa", str(trampas), "backend/calidad/preguntas_trampa.json: casos")
    cifras.agregar("TrampasPorRevisar", por_revisar, "docs/evidencia/nia-pruebas.md: última corrida de trampas")
    cifras.agregar("FechaCorridaTrampas", f"{dia} de septiembre de 2026", "docs/evidencia/nia-pruebas.md: última corrida de trampas")
    # La prueba local del camino con IA: la fecha sale del nombre de su salida, que tiene que terminar limpia.
    corrida = max(EVIDENCIA.glob("verificar-nia-openai-*.txt"))
    if not corrida.read_text(encoding="utf-8").rstrip().endswith("sin problemas: 6 juegos × 3 preguntas"):
        raise ValueError(f"{corrida.name} no termina sin problemas")
    fecha = datetime.strptime(corrida.stem.removeprefix("verificar-nia-openai-"), "%Y-%m-%d")
    cifras.agregar("FechaCorridaNiaIA", fecha_larga(fecha), f"docs/evidencia/{corrida.name}: verificar_nia.py --openai")


def cifras_de_endpoints(cifras: Cifras) -> None:
    """§8.1: cuántos endpoints tiene la API y cuántos de cada grupo, leídos de backend/api/main.py sin importarlo."""
    endpoints = []
    for nodo in ast.parse((BACKEND / "api" / "main.py").read_text(encoding="utf-8")).body:
        for decorador in getattr(nodo, "decorator_list", []):
            if isinstance(decorador, ast.Call) and getattr(decorador.func, "attr", "") in ("get", "post", "put", "delete"):
                endpoints.append(ast.literal_eval(decorador.args[0]))
    agrupados = 0
    for grupo, prefijos in GRUPOS_DE_ENDPOINTS.items():
        cuantos = sum(1 for ruta in endpoints if ruta.split("/")[1] in prefijos)
        agrupados += cuantos
        cifras.agregar(f"Endpoints{grupo}", str(cuantos), f"backend/api/main.py: rutas de {', '.join(prefijos)}")
    if agrupados != len(endpoints):
        raise ValueError("hay endpoints de backend/api/main.py que no caen en ningún grupo")
    cifras.agregar("Endpoints", str(len(endpoints)), "backend/api/main.py: rutas con @app.get/post/put/delete")


def figura_pr_auc_por_fold(modelo: np.ndarray, trivial: np.ndarray) -> Path:
    """F6: el PR-AUC del modelo y del trivial en cada fold de la partición congelada y en la prueba externa."""
    externa = json.loads((EVIDENCIA / "prueba-externa.json").read_text())["resumen"]
    etiquetas = [f"fold {i + 1}" for i in range(len(modelo))] + [f"{externa['titulos_nuevos']} externos"]
    del_modelo = [*modelo, externa["pr_auc_externo"]]
    del_trivial = [*trivial, externa["pr_auc_trivial"]]
    x = np.arange(len(etiquetas), dtype=float)
    x[-1] += 0.6
    ancho = 0.36
    fig, eje = plt.subplots(figsize=(ANCHO_DE_TEXTO, 2.4))
    eje.bar(x - ancho / 2, del_trivial, ancho, color=PALETA["neutro"], alpha=0.35, label="trivial (la prevalencia)")
    eje.bar(x + ancho / 2, del_modelo, ancho, color=PALETA["serie"], label="modelo")
    for xi, m, t in zip(x, del_modelo, del_trivial):
        eje.annotate(f"{m / t:.1f}×", xy=(xi + ancho / 2, m), xytext=(0, 2), textcoords="offset points", ha="center",
                     va="bottom", fontsize=7.5, color=PALETA["tinta"])
    eje.axvline((x[-2] + x[-1]) / 2, color=PALETA["tinta_suave"], linewidth=0.8, linestyle=(0, (3, 3)))
    eje.set_xticks(x, etiquetas)
    eje.set_ylabel("PR-AUC")
    eje.set_ylim(0, max(del_modelo) * 1.18)
    eje.legend(frameon=False, loc="upper center", fontsize=8)
    return guardar_figura(fig, "pr-auc-por-fold")


def conjunto_limpio(resenas: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """data-v1 con todas las reglas de limpieza: el mismo conjunto que guarda el notebook 00."""
    limpio, pasos = li.limpiar(resenas)
    if li.firma_del_conjunto(limpio) != li.FIRMA_LIMPIO_DATA_V1:
        raise ValueError("el conjunto limpio cambió: revisar las reglas o la versión de lingua")
    return limpio, pasos


# Cómo se llama cada regla de backend/analisis/limpieza.py en la tabla y qué hace con las reseñas.
REGLAS_DE_LIMPIEZA = {
    "quitar_duplicados_exactos": (f"Texto idéntico de {li.PALABRAS_DE_UNA_COPIA} palabras o más", "se quitan; queda la más antigua"),
    "quitar_vacias": ("Reseña vacía", "se quitan"),
    "marcar_cortas": (f"Menos de {li.MINIMO_PALABRAS} palabras", "se marcan"),
    "marcar_no_ingles": ("Otro idioma, según lingua", "se marcan"),
    "marcar_plantillas": ("Plantilla de casillas", "se marcan"),
    "normalizar_texto": ("Normalización del texto", "se agrega \\texttt{texto\\_norm}"),
}


def cifras_de_limpieza(cifras: Cifras, limpio: pd.DataFrame, pasos: list) -> None:
    """§6: lo que quita y lo que marca cada regla de la limpieza (00, bloque 2), y el idioma."""
    bitacora = li.bitacora(pasos).set_index("regla")
    if list(bitacora.index) != list(REGLAS_DE_LIMPIEZA):
        raise ValueError("cambiaron las reglas de limpieza o su orden")
    # El texto dice que solo las dos primeras reglas quitan filas.
    if (bitacora["filas antes"] != bitacora["filas después"]).sum() != 2:
        raise ValueError("cambió cuántas reglas de limpieza quitan filas")
    fuente = "data-v1: bitácora de li.limpiar"
    cifras.agregar("DuplicadosQuitados", entero(int(bitacora.loc["quitar_duplicados_exactos", "afectadas"])), fuente)
    cifras.agregar("VaciasQuitadas", entero(int(bitacora.loc["quitar_vacias", "afectadas"])), fuente)
    cifras.agregar("ResenasLimpias", entero(len(limpio)), "conjunto limpio de data-v1: reseñas")
    cifras.agregar("CortasPorResena", porcentaje(limpio["es_corta"].mean(), 1), "conjunto limpio: menos de 3 palabras")
    otro_idioma = limpio["no_ingles"]
    cifras.agregar("IdiomaInglesPorResena", porcentaje(1 - otro_idioma.mean(), 1),
                   "conjunto limpio: en inglés o indeterminado según lingua")
    cifras.agregar("OtroIdioma", entero(int(otro_idioma.sum())), "conjunto limpio: en otro idioma según lingua")
    # El texto nombra los tres idiomas más frecuentes.
    if limpio.loc[otro_idioma, "idioma_detectado"].value_counts().head(3).index.tolist() != ["russian", "spanish", "portuguese"]:
        raise ValueError("cambiaron los idiomas más frecuentes entre las reseñas en otro idioma")


def cifras_de_validacion(cifras: Cifras, juegos: pd.DataFrame, resenas: pd.DataFrame) -> None:
    """§8.1 y §8.2: copias de texto que cruzan folds, y qué le pasaría al modelo de riesgo si se
    entrenara con la limpieza (00, celdas 36 y 56). La limpieza no se le aplica."""
    folds = ex.leer_particion()
    copias = ex.copias_de_texto(resenas, li.PALABRAS_DE_UNA_COPIA)
    cifras.agregar("PalabrasDeUnaCopia", str(li.PALABRAS_DE_UNA_COPIA), "backend/analisis/limpieza.py: PALABRAS_DE_UNA_COPIA")
    cifras.agregar("TextosEntreJuegos", entero(copias["textos en 2+ juegos"]),
                   f"data-v1: textos idénticos de {li.PALABRAS_DE_UNA_COPIA}+ palabras en 2 o más juegos")
    cifras.agregar("CopiasEnFoldsDistintos", entero(ex.copias_en_folds_distintos(resenas, copias["claves entre juegos"], folds)),
                   "data-v1: de esos textos, los que caen en folds distintos de la partición congelada")

    if pr_auc(ex.pr_auc_con_particion(ex.con_juego(resenas, juegos), folds).mean()) != cifras.macros["PRAUCModelo"][0]:
        raise ValueError("el PR-AUC con la partición congelada no coincide con el del modelo")
    sin_cortas = resenas[~li.marcar_cortas(resenas)[0]["es_corta"]]
    if ex.senal(sin_cortas).mean() <= ex.senal(resenas).mean():
        raise ValueError("quitar las cortas ya no sube la prevalencia")
    for nombre, filtrado in (("SinDuplicados", li.quitar_duplicados_exactos(resenas)[0]),
                             ("SinVacias", li.quitar_vacias(resenas)[0]), ("SinCortas", sin_cortas)):
        cifras.agregar(f"PRAUC{nombre}", pr_auc(ex.pr_auc_con_particion(ex.con_juego(filtrado, juegos), folds).mean()),
                       "data-v1 con una regla de limpieza, partición congelada (ex.pr_auc_con_particion)")


# T8: cada candidata, cuándo se conoce y si entra al modelo de riesgo. Las del juego se comprueban
# contra construir_features(conjunto="juego"); las del autor, contra conjunto="completo".
VARIABLES_CANDIDATAS = [
    ("\\texttt{es\\_gratis}, precio (en logaritmo) y descuento", "en la tienda, antes de comprar", "sí"),
    ("Si tiene nota de Metacritic, y la nota", "en la tienda, antes de comprar",
     "sí; la nota que falta se rellena con la mediana, junto a la bandera"),
    ("\\texttt{num\\_games\\_owned}: juegos del autor", "en la reseña; en el sitio se declara «compras al año»",
     "no: su aporte cabe en el ruido entre folds, y 0 es un perfil privado"),
    ("\\texttt{num\\_reviews}: reseñas del autor", "al descargar; cambia con el tiempo", "no: no está disponible al momento de la compra"),
    ("\\texttt{steam\\_purchase}, \\texttt{received\\_for\\_free} y \\texttt{written\\_during\\_early\\_access}",
     "en la reseña", "no: no están disponibles al momento de la compra"),
    ("\\texttt{playtime\\_at\\_review} y \\texttt{voted\\_up}", "en la reseña", "no: definen $Y$"),
    ("Texto de la reseña", "en la reseña", "no: sería una fuga, porque $Y$ sale de esas mismas reseñas"),
]


def tabla_de_variables(juegos: pd.DataFrame, resenas: pd.DataFrame) -> Path:
    """§8.5 (T8): qué variables se conocen antes de comprar y cuáles entran al modelo de riesgo."""
    df = ex.con_juego(resenas, juegos)
    juego = list(construir_features(df, conjunto="juego")[0].columns)
    if juego != ["es_gratis", "log_precio_final", "descuento", "metacritic_disponible", "metacritic"]:
        raise ValueError(f"cambiaron las variables del modelo de riesgo: {juego}")
    completo = set(construir_features(df, conjunto="completo")[0].columns)
    del_autor = {"log_num_games_owned", "log_num_reviews", "steam_purchase", "received_for_free", "written_during_early_access"}
    if not del_autor <= completo:
        raise ValueError("cambiaron las variables del autor que se evaluaron")
    filas = [f"{variable} & {cuando} & {entra} \\\\" for variable, cuando, entra in VARIABLES_CANDIDATAS]
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{>{\\raggedright\\arraybackslash}X >{\\raggedright\\arraybackslash}p{4.2cm} "
        ">{\\raggedright\\arraybackslash}p{4.6cm}}",
        "\\toprule", "Variable & Cuándo se conoce & ¿Entra al modelo de riesgo? \\\\", "\\midrule",
        *filas, "\\bottomrule", "\\end{tabularx}",
    ]
    ruta = TABLAS / "variables.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def cifras_del_texto(cifras: Cifras, limpio: pd.DataFrame) -> None:
    """§7.3: qué distingue el texto de una negativa temprana (00 §3.7), sobre el conjunto limpio."""
    grupo = ex.grupo_de_resena(limpio)
    conteo = grupo.value_counts()
    refund = ex.menciones(limpio["texto"], grupo, r"\brefund")
    palabras = ex.cuantiles_por_grupo(li.palabras(limpio["texto"]), grupo)["mediana"]
    for corto, largo, g in (("Tempranas", "NegativasTempranas", "negativa temprana"),
                            ("Tardias", "NegativasTardias", "negativa tardía"), ("Positivas", "Positivas", "positiva")):
        cifras.agregar(f"{largo}Limpias", entero(int(conteo[g])), f"conjunto limpio de data-v1: reseñas {g}s")
        cifras.agregar(f"Refund{corto}PorResena", porcentaje(refund[g], 1), f"conjunto limpio: {g}s que mencionan «refund»")
        cifras.agregar(f"PalabrasMediana{corto}", entero(int(palabras[g])), f"conjunto limpio: mediana de palabras, {g}s")

    # Las palabras que nombra el texto tienen que seguir entre las 15 que más distinguen a cada lado.
    tempranas = limpio.loc[grupo == "negativa temprana", "texto_norm"]
    contra_positivas = ex.log_odds_informativo(tempranas, limpio.loc[grupo == "positiva", "texto_norm"], li.STOPWORDS_SIN_NEGACIONES)
    contra_tardias = ex.log_odds_informativo(tempranas, limpio.loc[grupo == "negativa tardía", "texto_norm"], li.STOPWORDS_SIN_NEGACIONES)
    esperadas = ((contra_positivas.head(1), {"not"}), (contra_tardias.head(15), {"tutorial", "account", "login", "settings", "minutes"}),
                 (contra_tardias.tail(15), {"hours", "boss", "mods", "dlc"}))
    for tabla, del_texto in esperadas:
        if not del_texto <= set(tabla["palabra"]):
            raise ValueError(f"cambiaron las palabras que distinguen a las negativas tempranas: {sorted(del_texto)}")


def cifras_de_externos(cifras: Cifras, rutas: dict[str, Path]) -> None:
    """§5.6: los 83 de entrenamiento contra los 40 externos (00 §3.6). Solo describe: no decide nada."""
    juegos_v1, resenas_v1 = ex.cargar_release(rutas["data-v1"])
    juegos_v2, resenas_v2 = ex.cargar_release(rutas["data-v2"])
    externos = set(juegos_v2["appid"]) - set(juegos_v1["appid"])
    juegos_ext = juegos_v2[juegos_v2["appid"].isin(externos)]
    resenas_ext = resenas_v2[resenas_v2["appid"].isin(externos)]
    if ex.llaves(juegos_ext, resenas_ext)["casos"].sum() or ex.resumen_de_rango(ex.casos_de_rango(juegos_ext, resenas_ext))["casos"].sum():
        raise ValueError("los 40 externos ya no pasan las validaciones de llaves y rangos")
    for nombre, juegos, resenas in (("Entrenamiento", juegos_v1, resenas_v1), ("Externos", juegos_ext, resenas_ext)):
        por_juego = ex.tasa_por_juego(resenas, juegos)
        if nombre == "Externos":
            cifras.agregar("GratisExternos", str(int(por_juego["es_gratis"].sum())), "los 40 externos: juegos gratis")
            cifras.agregar("SinNotaExternos", str(int(por_juego["metacritic"].isna().sum())), "los 40 externos: juegos sin nota")
        # Los gratis y los de pago sin precio no tienen precio_final: la mediana es la de los de pago con precio.
        cifras.agregar(f"PrecioMediano{nombre}", decimal(por_juego["precio_final"].median() / 100, 2),
                       f"{nombre.lower()}: mediana de precio_final / 100, juegos de pago con precio")
        cifras.agregar(f"Tasa{nombre}MedianaJuegos", porcentaje(por_juego["tasa"].median()), f"{nombre.lower()}: mediana de las tasas por juego")
        cifras.agregar(f"Tasa{nombre}PromJuegos", porcentaje(por_juego["tasa"].mean()), f"{nombre.lower()}: promedio de las tasas por juego")


def figura_tasa_por_juego(por_juego: pd.DataFrame, prevalencia: float) -> Path:
    """F3: la tasa de señal de cada juego de data-v1, de menor a mayor, con su intervalo de Wilson."""
    orden = por_juego.sort_values(["tasa", "nombre"]).reset_index()
    fig, eje = plt.subplots(figsize=(ANCHO_DE_TEXTO, 2.3))
    eje.errorbar(orden.index, 100 * orden["tasa"],
                 yerr=[100 * (orden["tasa"] - orden["ic_bajo"]), 100 * (orden["ic_alto"] - orden["tasa"])],
                 fmt="o", markersize=3.2, color=PALETA["serie"], ecolor=PALETA["tinta_suave"], elinewidth=0.7, capsize=0)
    eje.axhline(100 * prevalencia, color=PALETA["tinta_suave"], linewidth=0.8, linestyle=(0, (3, 3)))
    eje.annotate(f"prevalencia por reseña: {100 * prevalencia:.2f} %", xy=(len(orden) / 2, 100 * prevalencia), xytext=(0, 3),
                 textcoords="offset points", ha="center", va="bottom", fontsize=7.5, color=PALETA["tinta"])
    menor = orden[orden["tasa"] == orden["tasa"].min()]
    mayor = orden.iloc[-1]
    eje.annotate(f"{mayor['nombre'].replace('™', '')}: {100 * mayor['tasa']:.2f} %", xy=(orden.index[-1], 100 * mayor["tasa"]),
                 xytext=(-8, 0), textcoords="offset points", ha="right", va="center", fontsize=7.5, color=PALETA["tinta"])
    nombres = [n.replace("™", "") for n in menor["nombre"]]
    if len(nombres) > 1:
        texto = f"la más baja, {100 * orden['tasa'].min():.2f} %, empatada en {len(nombres)} juegos:\n" \
                f"{', '.join(nombres[:-1])} y {nombres[-1]}"
    else:
        texto = f"la más baja: {nombres[0]}, {100 * orden['tasa'].min():.2f} %"
    eje.annotate(texto, xy=(menor.index[-1] / 2, 100 * orden["tasa"].min()), xytext=(0, 40), textcoords="offset points",
                 ha="left", va="bottom", fontsize=7.5, color=PALETA["tinta"], linespacing=1.3,
                 arrowprops={"arrowstyle": "-", "color": PALETA["tinta_suave"], "linewidth": 0.6, "shrinkA": 1, "shrinkB": 3})
    eje.set_xlim(-2, len(orden) + 1)
    eje.set_xticks([])
    eje.set_xlabel(f"los {len(orden)} juegos de data-v1, de menor a mayor tasa")
    eje.set_ylabel("tasa de señal del juego")
    eje.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f} %"))
    return guardar_figura(fig, "tasa-por-juego")


def figura_tasa_contra_nota(por_juego: pd.DataFrame) -> Path:
    """F4: tasa de señal contra la nota de Metacritic, con los juegos sin nota en un panel aparte."""
    con_nota = por_juego[por_juego["metacritic"].notna()]
    sin_nota = por_juego[por_juego["metacritic"].isna()].sort_index()
    fig, (izquierda, derecha) = plt.subplots(1, 2, figsize=(ANCHO_DE_TEXTO, 2.45), sharey=True,
                                             gridspec_kw={"width_ratios": [1, 4], "wspace": 0.06})
    # Dispersión horizontal fija (semilla 42) para que los puntos no se encimen y dos corridas den lo mismo.
    dispersion = np.random.default_rng(42).uniform(-0.28, 0.28, len(sin_nota))
    izquierda.scatter(dispersion, 100 * sin_nota["tasa"], s=14, color=PALETA["negativa"], linewidths=0)
    mediana_sin = 100 * sin_nota["tasa"].median()
    izquierda.hlines(mediana_sin, -0.4, 0.4, color=PALETA["tinta"], linewidth=1.2)
    izquierda.annotate("mediana", xy=(-0.4, mediana_sin), xytext=(0, 2), textcoords="offset points", ha="left",
                       va="bottom", fontsize=7, color=PALETA["tinta"])
    izquierda.set_xlim(-0.5, 0.5)
    izquierda.set_xticks([0], [f"sin nota ({len(sin_nota)})"])
    derecha.scatter(con_nota["metacritic"], 100 * con_nota["tasa"], s=14, color=PALETA["serie"], linewidths=0)
    derecha.set_xlabel(f"nota de Metacritic ({len(con_nota)} juegos con nota)")
    derecha.tick_params(axis="y", left=False)
    izquierda.set_yscale("log")
    marcas = [0.1, 0.3, 1, 3, 10, 30]
    izquierda.set_yticks(marcas, [f"{m:g} %" for m in marcas])
    izquierda.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    izquierda.set_ylim(0.1, 35)
    izquierda.set_ylabel("tasa de señal del juego (escala log)")
    return guardar_figura(fig, "tasa-contra-nota")


def estilo_de_figuras() -> None:
    plt.rcParams.update({
        "font.family": "Inter", "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
        "text.color": PALETA["tinta"], "axes.labelcolor": PALETA["tinta_suave"],
        "xtick.color": PALETA["tinta_suave"], "ytick.color": PALETA["tinta_suave"],
        "axes.edgecolor": PALETA["rejilla"], "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": PALETA["rejilla"], "grid.linewidth": 0.6,
        "axes.axisbelow": True, "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    })


def guardar_figura(fig, nombre: str) -> Path:
    """PDF sin fecha de creación, para que dos corridas den el mismo archivo."""
    ruta = FIGURAS / f"{nombre}.pdf"
    fig.savefig(ruta, metadata={"CreationDate": None, "Creator": None, "Producer": None})
    plt.close(fig)
    return ruta


# --- tablas ----------------------------------------------------------------

def tabla_descriptiva(rutas: dict[str, Path]) -> Path:
    """§5.1: estadísticas descriptivas del corte de entrenamiento y del catálogo servido."""
    columnas = []
    for ref in ("data-v1", SERVIDO_REF):
        juegos, resenas = ex.cargar_release(rutas[ref])
        senal = ex.senal(resenas)
        creadas = pd.to_datetime(resenas["timestamp_created"], unit="s", utc=True)
        julio = pd.Timestamp("2025-07-01", tz="UTC")
        de_pago = juegos.loc[(juegos["es_gratis"] == 0) & juegos["precio_final"].notna(), "precio_final"] / 100
        notas = juegos["metacritic"].dropna()

        def corta(momento: pd.Timestamp) -> str:
            return f"{momento.day} {MESES_CORTOS[momento.month - 1]} {momento.year}"

        columnas.append([
            entero(len(juegos)), entero(len(resenas)), entero(int(senal.sum())), porcentaje(senal.mean()),
            f"{corta(creadas.min())} a {corta(creadas.max())}", porcentaje((creadas >= julio).mean(), 1),
            porcentaje((resenas["num_games_owned"] > 0).mean(), 1), str(int(juegos["es_gratis"].sum())),
            f"{de_pago.median():,.2f} ({de_pago.min():,.2f} a {de_pago.max():,.2f})",
            f"{notas.median():.0f} ({notas.min():.0f} a {notas.max():.0f})", str(int(juegos["metacritic"].isna().sum())),
        ])
    renglones = ["Juegos", "Reseñas", "Reseñas con la señal ($Y = 1$)", "Prevalencia por reseña", "Reseñas publicadas",
                 "Publicadas desde julio de 2025", "Reseñas con perfil público", "Juegos gratis",
                 "Precio de los de pago en pesos: mediana (mín.\\ a máx.)", "Nota de Metacritic: mediana (mín.\\ a máx.)",
                 "Juegos sin nota de Metacritic"]
    filas = [f"{r} & {a} & {b} \\\\" for r, a, b in zip(renglones, *columnas)]
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{>{\\raggedright\\arraybackslash}X rr}", "\\toprule",
        f" & Entrenamiento (data-v1) & Catálogo ({SERVIDO_REF}) \\\\", "\\midrule", *filas, "\\bottomrule", "\\end{tabularx}",
    ]
    ruta = TABLAS / "descriptiva.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


# Cómo se llama cada archivo de un release en las tablas del anexo; el pie de la de releases da el nombre completo.
NOMBRE_DE_ASSET = {"nexplay_reproducible.db.xz": "base", "nexplay_extracto.parquet": "extracto"}


def tabla_de_sha256() -> Path:
    """Anexo: el sha256 de cada archivo de los releases, según la API de GitHub. Se comprueba contra el que
    usa el código: las bases, contra RELEASES; los extractos, contra el notebook 01."""
    publicacion = publicacion_de_releases()
    notebook = (RAIZ / "notebooks" / "01_modelo_riesgo.ipynb").read_text(encoding="utf-8")
    del_notebook = dict(re.findall(r'(PARQUET_\w+_SHA256)\s*=\s*\\"([0-9a-f]{64})\\"', notebook))
    esperados = {("data-v1", "nexplay_extracto.parquet"): del_notebook["PARQUET_ENTRENAMIENTO_SHA256"],
                 ("data-v2", "nexplay_extracto.parquet"): del_notebook["PARQUET_PRUEBA_SHA256"]}
    esperados.update({(ref, "nexplay_reproducible.db.xz"): sha for ref, sha in RELEASES.items()})
    filas = []
    for ref in ("data-v1", "data-v2", SERVIDO_REF):
        for asset, datos in sorted(publicacion[ref]["assets"].items()):
            if esperados.get((ref, asset)) != datos["sha256"]:
                raise ValueError(f"el sha256 de {ref}/{asset} en GitHub no es el que usa el código")
            filas.append(f"{ref} & {NOMBRE_DE_ASSET[asset]} & \\texttt{{{datos['sha256']}}} \\\\")
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabular}{lll}", "\\toprule", "Release & Archivo & sha256 \\\\", "\\midrule",
        *filas, "\\bottomrule", "\\end{tabular}",
    ]
    ruta = TABLAS / "sha256.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def cifras_de_reproducibilidad(cifras: Cifras, tag: str) -> None:
    """Anexo: el tag que clonan los notebooks, su commit y la corrida vigente en Colab. Las celdas, los errores, los
    avisos y las versiones se cuentan en las tres descargas, cuyo sha256 debe ser el de docs/evidencia/colab/README.md.
    Falla si esa corrida no clonó el mismo commit que los notebooks: el anexo dice que el código entregado corrió
    en Colab."""

    def commit_de(etiqueta: str) -> str:
        return subprocess.run(["git", "rev-parse", "--short", f"{etiqueta}^{{commit}}"], cwd=RAIZ, capture_output=True,
                              text=True, check=True).stdout.strip()

    commit = commit_de(tag)
    cifras.agregar("TagCodigo", tag, "CODIGO_REF de los tres notebooks")
    cifras.agregar("CommitCodigo", commit, "git: el commit al que apunta el tag que clonan los notebooks")

    carpeta = EVIDENCIA / "colab"
    fuente = "docs/evidencia/colab/README.md"
    leeme = (carpeta / "README.md").read_text(encoding="utf-8")
    fecha, tag_colab = re.search(r"^## Los tres: (\d{4}-\d{2}-\d{2}), `([\w-]+)`", leeme, re.M).groups()
    if commit_de(tag_colab) != commit:
        raise ValueError(f"la corrida vigente en Colab clonó {tag_colab} y los notebooks clonan {tag} ({commit}): "
                         "falta correrlos en Colab con ese tag")
    vigente = leeme.split("\n## Los tres:")[1].split("\n## ")[0]

    def fila(titulo: str) -> list[str]:
        return [c.strip(" `") for c in re.search(rf"^\| {titulo} \|(.+)\|$", vigente, re.M)[1].split("|")]

    archivos, huellas, celdas, tiempos = (fila("Archivo"), fila("sha256"), fila("Celdas de código ejecutadas"),
                                          fila("Tiempo, medido con las mismas versiones de Colab, no en Colab"))
    for nombre, archivo, huella, celdas_leeme, tiempo in zip(("Cero", "Uno", "Dos"), archivos, huellas, celdas, tiempos):
        contenido = (carpeta / archivo).read_bytes()
        if hashlib.sha256(contenido).hexdigest() != huella:
            raise ValueError(f"{archivo} no tiene el sha256 que da {fuente}")
        codigo = [c for c in json.loads(contenido)["cells"] if c["cell_type"] == "code"]
        salidas = [s for c in codigo for s in c.get("outputs", [])]
        ejecutadas = f"{sum(c.get('execution_count') is not None for c in codigo)} de {len(codigo)}"
        refs = {m[1] for c in codigo if (m := re.search(r'CODIGO_REF\s*=\s*"([^"]+)"', "".join(c["source"])))}
        if ejecutadas != celdas_leeme or refs != {tag_colab}:
            raise ValueError(f"{archivo}: {ejecutadas} celdas y CODIGO_REF {sorted(refs)}, no lo que dice {fuente}")
        if any(s["output_type"] == "error" or s.get("name") == "stderr" for s in salidas):
            raise ValueError(f"{archivo} trae errores o avisos")
        cifras.agregar(f"Celdas{nombre}", ejecutadas, f"docs/evidencia/colab/{archivo}: celdas de código ejecutadas")
        cifras.agregar(f"Tiempo{nombre}", tiempo.removesuffix(" s"), fuente + ": segundos, con las versiones de Colab")

    uno = json.loads((carpeta / archivos[1]).read_bytes())
    entorno = texto_de(celda_con(uno, "Constancia del entorno"))
    versiones = dict(re.findall(r"^(python|numpy|pandas|scikit-learn)\s+([\d.]+)$", entorno, re.M))
    if versiones["scikit-learn"] != cifras.macros["VersionSklearnColab"][0]:
        raise ValueError("la versión de scikit-learn de Colab no cuadra entre la evidencia")
    for archivo, (nombre, marcas) in zip(archivos[1:], CELDAS_CON_CIFRAS.items()):
        corrida, guardado = json.loads((carpeta / archivo).read_bytes()), notebook_en(tag, nombre)
        for marca in marcas:
            if texto_de(celda_con(corrida, marca)).strip() != texto_de(celda_con(guardado, marca)).strip():
                raise ValueError(f"la celda con «{marca}» imprimió en Colab otra cosa que en {tag}:notebooks/{nombre}")
    cifras.agregar("FechaColab", fecha_larga(datetime.fromisoformat(fecha)), fuente + ": la corrida vigente")
    for nombre, paquete in (("Python", "python"), ("Numpy", "numpy"), ("Pandas", "pandas")):
        cifras.agregar(f"Version{nombre}Colab", versiones[paquete], f"docs/evidencia/colab/{archivos[1]}: su entorno")


# --- lo que se toma de los notebooks del tag, sin recalcular ---------------

# Las celdas de las que el documento toma cifras: su texto en el tag debe ser el que imprimió la corrida en Colab.
CELDAS_CON_CIFRAS = {
    "01_modelo_riesgo": ("lr.figura_pr_auc_por_fold(", "lr.tabla_comparativa(", "lr.tabla_de_bandas("),
    "02_modelos_texto": ("tx.decidir(", "lt.tabla_top_k(", "lt.cobertura_del_sitio("),
}

def tag_de_codigo() -> str:
    """El tag que clonan los notebooks (su CODIGO_REF), el mismo en los tres. De él salen el tag y el commit del
    anexo, y de sus notebooks, las figuras y cifras que el documento toma tal como se guardaron."""
    tags = {re.search(r'CODIGO_REF = \\"([^"\\]+)\\"', ruta.read_text(encoding="utf-8"))[1]
            for ruta in sorted((RAIZ / "notebooks").glob("0*.ipynb"))}
    if len(tags) != 1:
        raise ValueError(f"los notebooks no clonan el mismo tag: {sorted(tags)}")
    return tags.pop()


def notebook_en(tag: str, nombre: str) -> dict:
    salida = subprocess.run(["git", "show", f"{tag}:notebooks/{nombre}.ipynb"], cwd=RAIZ, capture_output=True,
                            text=True, check=True).stdout
    return json.loads(salida)


def celda_con(notebook: dict, marca: str) -> dict:
    """La única celda de código que contiene `marca`."""
    celdas = [c for c in notebook["cells"] if c["cell_type"] == "code" and marca in "".join(c["source"])]
    if len(celdas) != 1:
        raise ValueError(f"«{marca}» está en {len(celdas)} celdas de código, no en una")
    return celdas[0]


def texto_de(celda: dict) -> str:
    return "\n".join("".join(s.get("data", {}).get("text/plain") or s.get("text") or "") for s in celda.get("outputs", []))


def pngs_de(celda: dict) -> list[bytes]:
    return [base64.b64decode(s["data"]["image/png"]) for s in celda.get("outputs", []) if "image/png" in s.get("data", {})]


def figuras_de_los_notebooks(tag: str) -> list[Path]:
    """Las barras de PR-AUC con IC y las dos nubes del 02, los PNG tal como los guardó el notebook en el tag."""
    notebook = notebook_en(tag, "02_modelos_texto")
    barras = pngs_de(celda_con(notebook, "lt.figura_pr_auc_con_ic("))
    nubes = pngs_de(celda_con(notebook, "lt.para_las_nubes("))
    if len(barras) != 1 or len(nubes) != 2:
        raise ValueError("cambiaron las figuras guardadas del 02")
    destino = FIGURAS / "notebooks"
    destino.mkdir(exist_ok=True)
    rutas = []
    # La celda de las nubes muestra primero la de temprana y después la de tardía.
    for nombre, png in (("02-pr-auc-con-ic", barras[0]), ("02-nube-temprana", nubes[0]), ("02-nube-tardia", nubes[1])):
        ruta = destino / f"{nombre}.png"
        ruta.write_bytes(png)
        rutas.append(ruta)
    return rutas


def cifras_de_la_parte_a(cifras: Cifras, tag: str) -> None:
    """§7.9: los modelos de texto, de docs/evidencia/modelos-texto.json, y la lectura para negocio del 02 (§6), de
    sus salidas guardadas en el tag. El notebook tiene que decir que coincide con el JSON."""
    registro = json.loads((EVIDENCIA / "modelos-texto.json").read_text(encoding="utf-8"))
    notebook = notebook_en(tag, "02_modelos_texto")
    prerregistro, codigo = registro["prerregistro"]["commit"], registro["codigo"]["commit"]
    if f"Coincide con docs/evidencia/modelos-texto.json (código {codigo})" not in texto_de(celda_con(notebook, "tx.decidir(")):
        raise ValueError("el notebook 02 del tag no coincide con docs/evidencia/modelos-texto.json")
    # El prerregistro se commiteó antes que el código, y el JSON salió con el árbol limpio.
    if subprocess.run(["git", "merge-base", "--is-ancestor", prerregistro, codigo], cwd=RAIZ).returncode != 0:
        raise ValueError("el prerregistro no es anterior al código de los modelos de texto")
    if not registro["codigo"]["arbol_limpio"]:
        raise ValueError("modelos-texto.json no salió de un árbol limpio")
    datos, modelos, decision = registro["datos"], registro["modelos"], registro["decision"]
    if str(datos["juegos"]) != cifras.macros["JuegosEntrenamiento"][0]:
        raise ValueError("los modelos de texto no usan los juegos de data-v1")
    if (decision["rama"], decision["mejor"], decision["elegido"]) != (3, "tfidf_lr", "tfidf_lr"):
        raise ValueError("cambió la decisión de la Parte A")
    fuente = "docs/evidencia/modelos-texto.json"
    cifras.agregar("NegativasTexto", entero(datos["negativas"]), fuente + ": negativas en inglés")
    cifras.agregar("TempranasTexto", entero(datos["tempranas"]), fuente + ": negativas tempranas")
    cifras.agregar("PrevalenciaTextoPorResena", porcentaje(datos["tempranas"] / datos["negativas"]), fuente)
    cifras.agregar("DuracionesEnmascaradas", entero(datos["con_duracion_enmascarada"]), fuente + ": con duración escrita")
    cifras.agregar("RamaTexto", str(decision["rama"]), fuente + ": rama de la regla prerregistrada")
    cifras.agregar("PrerregistroTexto", prerregistro, fuente + ": commit del prerregistro")
    cifras.agregar("CodigoTexto", codigo, fuente + ": commit del código que lo corrió")
    for clave, nombre in (("trivial", "Trivial"), ("refund", "Refund"), ("tfidf_nb", "NB"), ("minilm_lr", "MiniLM"),
                          ("tfidf_lr", "LR")):
        cifras.agregar(f"PRAUCTexto{nombre}", pr_auc(modelos[clave]["PR-AUC media"]), fuente + f": {clave}, media de 5 folds")
    lr = modelos["tfidf_lr"]
    media = lr["PR-AUC media"]
    cifras.agregar("PRAUCTextoLRICInf", junto_a(lr["IC media"][0], media), fuente + ": IC 95 % de la media")
    cifras.agregar("PRAUCTextoLRICSup", junto_a(lr["IC media"][1], media), fuente + ": IC 95 % de la media")
    cifras.agregar("CocienteTextoLR", decimal(lr["cociente"], 1), fuente + ": TF-IDF + LR entre el trivial")
    cifras.agregar("CocienteTextoLRICInf", decimal(lr["IC cociente"][0], 2), fuente)
    cifras.agregar("CocienteTextoLRICSup", decimal(lr["IC cociente"][1], 2), fuente)
    cifras.agregar("DiferenciaTextoLRRefund", junto_a(lr["− refund"], media), fuente + ": TF-IDF + LR menos «refund»")
    cifras.agregar("DiferenciaTextoLRRefundICInf", junto_a(lr["IC − refund"][0], media), fuente)
    cifras.agregar("DiferenciaTextoLRRefundICSup", junto_a(lr["IC − refund"][1], media), fuente)

    fuente = f"notebooks/02_modelos_texto.ipynb en {tag}, salida guardada"
    top = re.search(r"10% con score más alto\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
                    texto_de(celda_con(notebook, "lt.tabla_top_k(")))
    if decimal(float(top[1]), 3) != cifras.macros["PRAUCTextoTrivial"][0]:
        raise ValueError("la prevalencia del 10 % superior no es la del JSON")
    cifras.agregar("TopDiezTempranasPorResena", porcentaje(float(top[3]), 1), fuente + ": TF-IDF + LR, 10 % con score más alto")
    cifras.agregar("TopDiezVeces", decimal(float(top[5]), 1), fuente + ": veces la prevalencia")
    cobertura = re.search(r"de las (\d+) palabras que más empujan hacia temprana, (\d+) no caen",
                          texto_de(celda_con(notebook, "lt.cobertura_del_sitio(")))
    cifras.agregar("PalabrasTopTemprana", cobertura[1], fuente + ": las que más empujan hacia temprana")
    cifras.agregar("PalabrasSinCategoria", cobertura[2], fuente + ": las que no caen en ninguna categoría del sitio")
    # Las palabras que nombra el texto son las del «Qué vemos» de las nubes.
    que_vemos = next("".join(c["source"]) for c in notebook["cells"]
                     if c["cell_type"] == "markdown" and "Hacia tardía pesan" in "".join(c["source"]))
    if not all(f"`{palabra}`" in que_vemos for palabra in ("refunded", "tutorial", "account", "login", "mods", "update", "boss")):
        raise ValueError("cambiaron las palabras que pesan en las nubes del 02")


def cifras_de_la_lectura_del_01(cifras: Cifras, tag: str, modelo: dict) -> Path:
    """§7.1, §7.5 y §7.6: la lectura para negocio del 01, de sus salidas guardadas en el tag. La tabla de bandas
    se arma con los valores que imprimió el notebook, sin recalcular, y se comprueba contra los releases."""
    notebook = notebook_en(tag, "01_modelo_riesgo")
    fuente = f"notebooks/01_modelo_riesgo.ipynb en {tag}, salida guardada"
    folds = re.search(r"fold 1: ([\d.]+) · media de los otros cuatro: ([\d.]+) · el fold 1 es el (\d+)% de la suma",
                      texto_de(celda_con(notebook, "lr.figura_pr_auc_por_fold(")))
    por_fold = modelo["modelo"]
    if (decimal(por_fold[0], 4), decimal(por_fold[1:].mean(), 4)) != (folds[1], folds[2]):
        raise ValueError("el PR-AUC por fold del 01 ya no es el del modelo")
    cifras.agregar("PRAUCFoldUno", pr_auc(float(folds[1])), fuente + ": fold 1")
    cifras.agregar("PRAUCOtrosFolds", pr_auc(float(folds[2])), fuente + ": media de los otros cuatro folds")
    cifras.agregar("FoldUnoParteDeLaSuma", f"{folds[3]}\\,\\%", fuente + ": parte de la suma de los cinco")
    veces = dict(re.findall(r"^(juego|compra)\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s*$", texto_de(celda_con(notebook, "lr.tabla_comparativa(")), re.M))
    for conjunto in ("juego", "compra"):
        cifras.agregar(f"VecesTrivial{conjunto.capitalize()}", decimal(float(veces[conjunto]), 1), fuente + f": {conjunto} entre el trivial")

    salida = texto_de(celda_con(notebook, "lr.tabla_de_bandas("))
    filas, conjunto = [], None
    for linea in salida.splitlines():
        m = re.match(r"^(data-v1 \(OOF\)|externos \(\d+\))?\s+(bajo|medio|alto)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s*$", linea)
        if m:
            conjunto = m[1] or conjunto
            filas.append((conjunto, m[2], int(m[3]), int(m[4]), int(m[5]), float(m[6]), float(m[7])))
    if len(filas) != 6:
        raise ValueError("cambió la tabla de bandas del 01")
    # Los totales de cada conjunto son los de su release, y las bandas externas, las de prueba-externa.json.
    externa = json.loads((EVIDENCIA / "prueba-externa.json").read_text())["resumen"]
    for prefijo, resenas, positivos in (("data-v1", "ResenasEntrenamiento", "PositivosEntrenamiento"),
                                        ("externos", "ResenasExternos", "PositivosExternos")):
        del_conjunto = [f for f in filas if f[0].startswith(prefijo)]
        if (entero(sum(f[3] for f in del_conjunto)), entero(sum(f[4] for f in del_conjunto))) != \
                (cifras.macros[resenas][0], cifras.macros[positivos][0]):
            raise ValueError(f"la tabla de bandas del 01 no suma las reseñas de {prefijo}")
    if {f[1]: f[2] for f in filas if f[0].startswith("externos")} != externa["bandas"]:
        raise ValueError("las bandas externas del 01 no son las de prueba-externa.json")
    for f in filas:
        if f[0].startswith("externos") and f[1] in ("bajo", "medio"):
            if porcentaje(f[5]) != cifras.macros[f"Tasa{f[1].capitalize()}ExternosPorResena"][0]:
                raise ValueError("la tasa externa del 01 no es la de las bandas de referencia")
    alto_sobre_bajo = re.search(r"data-v1 \(OOF\): ([\d.]+)× · externos \(\d+\): ([\d.]+)×", salida)
    for nombre, impreso, prefijo in (("AltoSobreBajoOOF", alto_sobre_bajo[1], "data-v1"), ("AltoSobreBajoExternos", alto_sobre_bajo[2], "externos")):
        tasa = {f[1]: f[4] / f[3] for f in filas if f[0].startswith(prefijo)}
        if decimal(tasa["alto"] / tasa["bajo"], 2) != impreso:
            raise ValueError("la razón alta entre baja impresa no cuadra con los conteos")
        cifras.agregar(nombre, decimal(float(impreso), 1), fuente + f": tasa de la banda alta entre la baja, {prefijo}")
    for f in filas:
        if f[0].startswith("data-v1"):
            cifras.agregar(f"{f[1].capitalize()}OOF", str(f[2]), fuente + f": juegos de data-v1 en la banda {f[1]} con score fuera de fold")

    nombres = {"data-v1 (OOF)": "data-v1, OOF", **{f[0]: f"{f[0].split()[1][1:-1]} externos" for f in filas if f[0].startswith("externos")}}
    renglones, anterior = [], None
    for f in filas:
        if anterior is not None and f[0] != anterior:
            renglones.append("\\midrule")
        renglones.append(f"{nombres[f[0]] if f[0] != anterior else ''} & {f[1]} & {f[2]} & {entero(f[3])} & {entero(f[4])} & "
                         f"{porcentaje(f[5])} & {decimal(f[6], 1)}× \\\\")
        anterior = f[0]
    contenido = [
        "% Generado por documento/generar_figuras.py con la salida guardada del 01; no se recalcula.",
        "\\begin{tabular}{llrrrrr}", "\\toprule",
        "Conjunto & Banda & Juegos & Reseñas & \\begin{tabular}[b]{@{}r@{}}Con\\\\señal\\end{tabular} & "
        "\\begin{tabular}[b]{@{}r@{}}Tasa de\\\\señal\\end{tabular} & \\begin{tabular}[b]{@{}r@{}}Veces\\\\la base\\end{tabular} \\\\",
        "\\midrule",
        *renglones, "\\bottomrule", "\\end{tabular}",
    ]
    ruta = TABLAS / "bandas_oof.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def cifras_del_contexto(cifras: Cifras) -> None:
    """§2: el contexto de mercado, de docs/evidencia/contexto-mercado.json. Cada valor tiene que estar en su cita
    textual, tal como la publicó la fuente, y su fecha de corte sale del mismo archivo."""
    contexto = json.loads((EVIDENCIA / "contexto-mercado.json").read_text(encoding="utf-8"))["cifras"]
    fuente = "docs/evidencia/contexto-mercado.json"
    for clave, nombre in (("lanzamientos_2025", "LanzamientosSteam"), ("lanzamientos_10_resenas_o_menos", "LanzamientosPocasResenas")):
        dato = contexto[clave]
        if entero(dato["valor"]) not in dato["cita"]:
            raise ValueError(f"{fuente}: {clave} no está en su cita")
        cifras.agregar(nombre, entero(dato["valor"]), f"{fuente}: {dato['fuente']}")
    cifras.agregar("FechaCorteLanzamientos", fecha_larga(datetime.fromisoformat(contexto["lanzamientos_2025"]["corte"])),
                   f"{fuente}: fecha de la cuenta de lanzamientos")
    ingresos = contexto["ingresos_brutos_2025_miles_de_millones_usd"]
    if f"${decimal(ingresos['valor'], 1)} billion" not in ingresos["cita"]:
        raise ValueError(f"{fuente}: los ingresos no están en su cita")
    cifras.agregar("IngresosSteam", f"{decimal(ingresos['valor'], 1)} mil millones", f"{fuente}: {ingresos['fuente']}")
    cifras.agregar("FechaCorteIngresos", fecha_larga(datetime.fromisoformat(ingresos["corte"])),
                   f"{fuente}: fecha de la estimación de ingresos")


def cifras_del_diccionario(cifras: Cifras) -> None:
    """§4.4: cuántas columnas describe backend/analisis/diccionario.py, el diccionario del 00 (§1.2)."""
    arbol = ast.parse((BACKEND / "analisis" / "diccionario.py").read_text(encoding="utf-8"))
    columnas = next(len(n.value.keys) for n in arbol.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "COLUMNAS")
    cifras.agregar("ColumnasDiccionario", str(columnas), "backend/analisis/diccionario.py: COLUMNAS")


def tabla_de_releases(rutas: dict[str, Path]) -> Path:
    """T2: un renglón por release, con lo que trae y para qué sirve. El sha256 completo va en el anexo."""
    publicacion = publicacion_de_releases()
    juegos = {ref: conteos(rutas[ref]) for ref in ("data-v1", "data-v2", SERVIDO_REF)}
    externos = juegos["data-v2"]["juegos"] - juegos["data-v1"]["juegos"]
    para_que = {
        "data-v1": "Entrenar, elegir las variables y fijar los umbrales.",
        "data-v2": f"Suma {externos} juegos que el modelo no ve: la prueba externa.",
        SERVIDO_REF: "data-v2 más los totales públicos de Steam por juego. Lo sirve la API.",
    }
    filas = []
    for ref in ("data-v1", "data-v2", SERVIDO_REF):
        mb = {asset: f"{datos['bytes'] / 1e6:.1f}" for asset, datos in publicacion[ref]["assets"].items()}
        filas.append(f"{ref} & {publicacion[ref]['publicado']} & {entero(juegos[ref]['juegos'])} & "
                     f"{entero(juegos[ref]['resenas'])} & {mb.get('nexplay_reproducible.db.xz', '---')} & "
                     f"{mb.get('nexplay_extracto.parquet', '---')} & {para_que[ref]} \\\\")
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{llrrrr>{\\raggedright\\arraybackslash}X}",
        "\\toprule",
        "Release & Publicado & Juegos & Reseñas & \\begin{tabular}[b]{@{}r@{}}Base\\\\(MB)\\end{tabular} & "
        "\\begin{tabular}[b]{@{}r@{}}Extracto\\\\(MB)\\end{tabular} & Para qué \\\\",
        "\\midrule", *filas, "\\bottomrule", "\\end{tabularx}",
    ]
    ruta = TABLAS / "releases.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def cifras_de_calidad(cifras: Cifras, rutas: dict[str, Path]) -> None:
    """§4 y §6: los chequeos de validación del 00 (bloque 1) sobre data-v1. El texto dice que las llaves y
    los rangos imposibles no tienen casos, y nombra los tres hallazgos que tocan al modelo."""
    juegos, resenas = ex.cargar_release(rutas["data-v1"])
    if ex.llaves(juegos, resenas)["casos"].sum():
        raise ValueError("data-v1 ya tiene casos en las llaves")
    rango = ex.resumen_de_rango(ex.casos_de_rango(juegos, resenas))
    if rango.loc[list(ex.REGLAS_DURAS), "casos"].sum():
        raise ValueError("data-v1 ya tiene rangos imposibles")
    sin_precio = juegos[juegos["precio_final"].isna()]
    de_pago_sin_precio = sin_precio[sin_precio["es_gratis"] == 0]
    # La gratuidad incoherente son los mismos juegos de pago sin precio: el texto los cuenta una sola vez.
    if int(rango.loc["es_gratis coherente con el precio", "casos"]) != len(de_pago_sin_precio):
        raise ValueError("la gratuidad incoherente ya no son solo los de pago sin precio")
    verificacion = list(csv.DictReader(open(EVIDENCIA / "verificacion-40-steam.csv")))
    coinciden = sum(1 for f in verificacion if f["mc_guardado"] == f["mc_hoy"])
    cifras.agregar("PrivadosEntrenamientoPorResena", porcentaje((resenas["num_games_owned"] == 0).mean(), 1),
                   "data-v1: num_games_owned = 0")
    cifras.agregar("SinNotaEntrenamiento", str(int(juegos["metacritic"].isna().sum())), "data-v1: juegos sin nota de Metacritic")
    cifras.agregar("PagoSinPrecioEntrenamiento", str(len(de_pago_sin_precio)), "data-v1: juegos de pago sin precio")
    cifras.agregar("MetacriticVerificadoExternos", f"{coinciden} de {len(verificacion)}", "docs/evidencia/verificacion-40-steam.csv")


def copiar_capturas() -> list[Path]:
    destino = FIGURAS / "capturas"
    destino.mkdir(parents=True, exist_ok=True)
    copiadas = []
    for origen in sorted(CAPTURAS.glob("*.png")):
        shutil.copyfile(origen, destino / origen.name)
        copiadas.append(destino / origen.name)
    return copiadas


def copiar_logo() -> Path:
    """El logo de NexPlay para la portada, tal como lo sirve el frontend."""
    destino = FIGURAS / "logo-nexplay.png"
    shutil.copyfile(RAIZ / "frontend" / "public" / "logo-header.png", destino)
    return destino


def main() -> None:
    for carpeta in (CACHE, TABLAS, FIGURAS):
        carpeta.mkdir(parents=True, exist_ok=True)
    rutas = {ref: bajar(ref) for ref in RELEASES}

    cifras = Cifras()
    cifras_de_datos(cifras, rutas)
    modelo = cifras_del_modelo(cifras, rutas)
    cifras_de_bandas(cifras)
    cifras_de_evidencia(cifras)
    cifras_del_periodo(cifras, rutas)
    cifras_de_calidad(cifras, rutas)
    cifras_del_objetivo(cifras, rutas)
    juegos_v1, resenas_v1 = ex.cargar_release(rutas["data-v1"])
    por_juego = cifras_por_juego(cifras, juegos_v1, resenas_v1)
    cifras_de_correlaciones(cifras, por_juego)
    cifras_de_coeficientes(cifras, juegos_v1, resenas_v1)
    limpio, pasos = conjunto_limpio(resenas_v1)
    cifras_del_texto(cifras, limpio)
    cifras_de_limpieza(cifras, limpio, pasos)
    cifras_de_validacion(cifras, juegos_v1, resenas_v1)
    cifras_de_la_particion(cifras, juegos_v1, resenas_v1)
    cifras_de_externos(cifras, rutas)
    cifras_por_banda(cifras, rutas)
    cifras_de_casos_al_filo(cifras, rutas, modelo)
    cifras_del_recorrido(cifras, rutas, modelo)
    cifras_de_factores(cifras, rutas, modelo)
    cifras_de_motivos(cifras, limpio)
    cifras_de_endpoints(cifras)
    cifras_de_nia(cifras)
    cifras_del_diccionario(cifras)
    cifras_del_contexto(cifras)
    tag = tag_de_codigo()
    cifras_de_reproducibilidad(cifras, tag)
    cifras_de_la_parte_a(cifras, tag)
    # La lectura del 01 va antes de la tabla de conjuntos, que comprueba sus «veces el trivial» contra el notebook.
    tablas = [tabla_de_releases(rutas), tabla_de_sha256(), tabla_descriptiva(rutas), tabla_de_variables(juegos_v1, resenas_v1),
              cifras_de_la_lectura_del_01(cifras, tag, modelo), tabla_de_conjuntos(cifras, juegos_v1, resenas_v1, modelo["trivial"])]
    ruta_cifras = cifras.escribir()
    estilo_de_figuras()
    figuras = [figura_minutos_al_resenar(rutas), figura_tasa_por_juego(por_juego, ex.senal(resenas_v1).mean()),
               figura_tasa_contra_nota(por_juego), figura_pr_auc_por_fold(modelo["modelo"], modelo["trivial"]),
               *figuras_de_los_notebooks(tag)]
    capturas = copiar_capturas()
    copiar_logo()

    print(f"{len(cifras.macros)} cifras calculadas; {cifras.escritas} usadas en el texto, en {ruta_cifras.relative_to(RAIZ)}")
    print(f"tablas: {', '.join(t.name for t in tablas)} · figuras: {', '.join(f.name for f in figuras)}")
    print(f"{len(capturas)} capturas copiadas a {(FIGURAS / 'capturas').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
