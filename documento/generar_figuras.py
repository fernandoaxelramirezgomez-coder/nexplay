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

import contextlib
import csv
import io
import json
import shutil
import sqlite3
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

from bootstrap_prueba_externa import RELEASES as RELEASES_V1_V2  # noqa: E402
from despliegue.preparar_entorno import SERVIDO_REF, SERVIDO_SHA256  # noqa: E402
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


def porcentaje(x: float, decimales: int = 2) -> str:
    """x es una proporción: 0.0219 → «2.19 %»."""
    return f"{100 * x:.{decimales}f}\\,\\%"


def fecha_larga(momento: datetime) -> str:
    return f"{momento.day} de {MESES[momento.month - 1]} de {momento.year}"


def de_unix(segundos: int) -> datetime:
    return datetime.fromtimestamp(segundos, timezone.utc)


def de_iso(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


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
        lineas = ["% Generado por documento/generar_figuras.py. No se edita a mano.", ""]
        for nombre, (valor, fuente) in self.macros.items():
            lineas.append(f"\\newcommand{{\\cifra{nombre}}}{{{valor}}}  % {fuente}")
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


def cifras_del_modelo(cifras: Cifras, rutas: dict[str, Path]) -> None:
    df = cargar_datos(rutas["data-v1"])
    X, y, grupos = construir_features(df, conjunto="juego")
    with contextlib.redirect_stdout(io.StringIO()):
        modelo = evaluar_gkf(construir_pipeline(), X, y, grupos, "juego")
        trivial = evaluar_gkf(DummyClassifier(strategy="prior"), X, y, grupos, "trivial")
    fuente = "GroupKFold de 5 por appid sobre data-v1 (evaluar_gkf)"
    cifras.agregar("PRAUCModelo", decimal(modelo.mean(), 4), fuente)
    cifras.agregar("PRAUCModeloStd", decimal(modelo.std(), 4), fuente)
    cifras.agregar("PRAUCTrivial", decimal(trivial.mean(), 4), fuente + "; trivial = prevalencia de cada pliegue")
    cifras.agregar("PRAUCTrivialStd", decimal(trivial.std(), 4), fuente)
    # Un decimal: la variación entre folds no justifica centésimas. La prueba externa sigue la misma regla.
    cifras.agregar("PRAUCCociente", decimal(modelo.mean() / trivial.mean(), 1), fuente)
    cifras.agregar("PliegosGanados", str(int((modelo > trivial).sum())), fuente + ": pliegues donde el modelo supera al trivial")
    cifras.agregar("Pliegues", str(len(modelo)), fuente)

    oof = _scores_oof(X, y, grupos)
    cifras.agregar("UmbralMedio", decimal(np.percentile(oof, 100 / 3), 4), "percentil 33.3 de los scores fuera de pliegue")
    cifras.agregar("UmbralAlto", decimal(np.percentile(oof, 200 / 3), 4), "percentil 66.7 de los scores fuera de pliegue")


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
    cifras.agregar("PRAUCExterno", decimal(externa["pr_auc_externo"], 4), "docs/evidencia/prueba-externa.json")
    cifras.agregar("PRAUCExternoTrivial", decimal(externa["pr_auc_trivial"], 4), "docs/evidencia/prueba-externa.json")
    cifras.agregar("PRAUCExternoCociente", decimal(externa["pr_auc_externo"] / externa["pr_auc_trivial"], 1),
                   "docs/evidencia/prueba-externa.json")
    inf, sup = bootstrap["bootstrap"]["ic95_cociente"]
    cifras.agregar("ExternoICInf", decimal(inf, 2), "docs/evidencia/bootstrap-prueba-externa.json")
    cifras.agregar("ExternoICSup", decimal(sup, 2), "docs/evidencia/bootstrap-prueba-externa.json")
    cifras.agregar("ExternoReplicasSinVentaja", str(bootstrap["bootstrap"]["replicas_con_cociente_hasta_1"]),
                   "réplicas del bootstrap con cociente ≤ 1")

    biblioteca = json.loads((EVIDENCIA / "senal-por-biblioteca.json").read_text())["original"]
    for grupo in ("novatos", "veteranos"):
        g = biblioteca["grupos"][grupo]
        cifras.agregar(f"{grupo.capitalize()}PorResena", porcentaje(g["por_resena_pct"] / 100),
                       "docs/evidencia/senal-por-biblioteca.json")
        cifras.agregar(f"{grupo.capitalize()}PromJuegos", porcentaje(g["prom_juegos_pct"] / 100),
                       "docs/evidencia/senal-por-biblioteca.json")
    estratificada = json.loads((EVIDENCIA / "senal-por-biblioteca-estratificada.json").read_text())
    cifras.agregar("RazonMH", decimal(estratificada["razon_mh"], 2), "docs/evidencia/senal-por-biblioteca-estratificada.json")
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


def figura_resenas_por_mes(rutas: dict[str, Path]) -> Path:
    """F1: reseñas de data-v1 por mes de publicación, con la frontera de julio de 2025."""
    con = sqlite3.connect(f"file:{rutas['data-v1']}?mode=ro", uri=True)
    creadas = pd.to_datetime([f[0] for f in con.execute("SELECT timestamp_created FROM resenas")], unit="s", utc=True)
    con.close()
    por_mes = pd.Series(1, index=creadas).resample("MS").sum()
    julio = pd.Timestamp("2025-07-01", tz="UTC")
    desde_julio = (creadas >= julio).mean()

    fig, eje = plt.subplots(figsize=(ANCHO_DE_TEXTO, 2.6))
    eje.bar(por_mes.index, por_mes.values, width=24, color=PALETA["serie"], edgecolor="white", linewidth=0.6)
    eje.axvline(julio - pd.Timedelta(days=15), color=PALETA["tinta_suave"], linewidth=0.8, linestyle=(0, (3, 3)))
    # A la izquierda de la línea, donde no hay barras; la flecha dice hacia dónde se cuenta.
    eje.annotate(f"de julio de 2025 en adelante: {100 * desde_julio:.1f} % de las reseñas →",
                 xy=(julio, por_mes.max() * 0.75), xytext=(-10, 0), textcoords="offset points", ha="right",
                 va="center", color=PALETA["tinta"], fontsize=8)
    primera = por_mes[por_mes > 0].index[0]
    eje.annotate(f"la más antigua: {fecha_larga(creadas.min().to_pydatetime())}", xy=(primera, por_mes[primera]),
                 xytext=(4, 34), textcoords="offset points", ha="left", color=PALETA["tinta"], fontsize=8,
                 arrowprops={"arrowstyle": "-", "color": PALETA["tinta_suave"], "linewidth": 0.6, "shrinkA": 2,
                             "shrinkB": 1})
    marcas = [m for m in por_mes.index if m.month in (1, 7)]
    eje.set_xticks(marcas, [f"{MESES_CORTOS[m.month - 1]} {m.year}" for m in marcas])
    eje.set_ylabel("reseñas por mes")
    eje.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    return guardar_figura(fig, "resenas-por-mes")


def cifras_del_objetivo(cifras: Cifras, rutas: dict[str, Path]) -> pd.DataFrame:
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
    return sensibilidad


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

    fig, eje = plt.subplots(figsize=(ANCHO_DE_TEXTO, 2.8))
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


def tabla_de_correlaciones(cifras: Cifras, por_juego: pd.DataFrame) -> Path:
    """§7.2: Spearman de la tasa por juego contra cada variable del juego (00 §3.4)."""
    correlaciones = ex.correlaciones_del_juego(por_juego)
    fuente = "data-v1: Spearman de la tasa por juego (ex.correlaciones_del_juego)"
    for nombre, variable in (("TieneNota", "tiene nota de la crítica"), ("Nota", "nota de la crítica (con nota)"),
                             ("Precio", "precio (juegos de pago)")):
        cifras.agregar(f"Spearman{nombre}", con_signo(correlaciones.loc[variable, "Spearman"], 2), fuente)
    cifras.agregar("SpearmanPrecioP", decimal(correlaciones.loc["precio (juegos de pago)", "p"], 2), fuente + ": valor p")
    cifras.agregar("GratisEntrenamiento", str(int(por_juego["es_gratis"].sum())), "data-v1: juegos gratis")

    nombres = {"precio (juegos de pago)": "Precio (juegos de pago con precio)", "es gratis": "Es gratis",
               "descuento": "Descuento", "tiene nota de la crítica": "Tiene nota de la crítica",
               "nota de la crítica (con nota)": "Nota de la crítica (solo los que la tienen)"}
    def valor_p(p: float) -> str:
        return "<\\,0.001" if p < 0.001 else decimal(p, 3)

    filas = [f"{nombres[variable]} & {int(f['juegos'])} & {con_signo(f['Spearman'], 2)} & {valor_p(f['p'])} \\\\"
             for variable, f in correlaciones.iterrows()]
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabular}{lrrr}", "\\toprule", "Variable del juego & Juegos & Spearman & p \\\\", "\\midrule",
        *filas, "\\bottomrule", "\\end{tabular}",
    ]
    ruta = TABLAS / "correlaciones.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def cifras_de_coeficientes(cifras: Cifras, juegos: pd.DataFrame, resenas: pd.DataFrame) -> pd.DataFrame:
    """§7.2 y §9.5: los coeficientes del modelo B+ con su IC al 95 % por bootstrap sobre juegos."""
    coeficientes = ex.coeficientes_con_bootstrap(ex.con_juego(resenas, juegos))
    # Lo que dice el texto: con todo junto, solo la crítica se aleja del cero.
    if coeficientes.loc[["metacritic_disponible", "metacritic"], "cruza el cero"].any():
        raise ValueError("un coeficiente de la crítica ya cruza el cero")
    if not coeficientes.loc[["log_precio_final", "descuento", "es_gratis"], "cruza el cero"].all():
        raise ValueError("el precio, el descuento o la gratuidad ya no cruzan el cero")
    fuente = "data-v1: ex.coeficientes_con_bootstrap, 1,000 réplicas sobre appid"
    for nombre, variable in (("TieneNota", "metacritic_disponible"), ("Nota", "metacritic")):
        cifras.agregar(f"Coef{nombre}ICInf", con_signo(coeficientes.loc[variable, "IC 2.5 %"], 2), fuente)
        cifras.agregar(f"Coef{nombre}ICSup", con_signo(coeficientes.loc[variable, "IC 97.5 %"], 2), fuente)
    return coeficientes


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


def tabla_de_limpieza(cifras: Cifras, limpio: pd.DataFrame, pasos: list) -> Path:
    """§8.2 (T4): la bitácora de la limpieza, regla por regla, como la del notebook 00 (celda 54)."""
    bitacora = li.bitacora(pasos).set_index("regla")
    if list(bitacora.index) != list(REGLAS_DE_LIMPIEZA):
        raise ValueError("cambiaron las reglas de limpieza o su orden")
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

    filas = []
    for regla, f in bitacora.iterrows():
        nombre, accion = REGLAS_DE_LIMPIEZA[regla]
        afectadas = int(f["afectadas"])
        filas.append(f"{nombre} & {accion} & {entero(afectadas)} ({porcentaje(afectadas / f['filas antes'], 1)}) & "
                     f"{entero(int(f['filas después']))} \\\\")
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{>{\\raggedright\\arraybackslash}X >{\\raggedright\\arraybackslash}p{4.4cm} rr}",
        "\\toprule", "Regla, en orden & Qué se hace & Afectadas & Quedan \\\\", "\\midrule",
        *filas, "\\bottomrule", "\\end{tabularx}",
    ]
    ruta = TABLAS / "limpieza.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


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

    if decimal(ex.pr_auc_con_particion(ex.con_juego(resenas, juegos), folds).mean(), 4) != cifras.macros["PRAUCModelo"][0]:
        raise ValueError("el PR-AUC con la partición congelada no coincide con el del modelo")
    sin_cortas = resenas[~li.marcar_cortas(resenas)[0]["es_corta"]]
    if ex.senal(sin_cortas).mean() <= ex.senal(resenas).mean():
        raise ValueError("quitar las cortas ya no sube la prevalencia")
    for nombre, filtrado in (("SinDuplicados", li.quitar_duplicados_exactos(resenas)[0]),
                             ("SinVacias", li.quitar_vacias(resenas)[0]), ("SinCortas", sin_cortas)):
        cifras.agregar(f"PRAUC{nombre}", decimal(ex.pr_auc_con_particion(ex.con_juego(filtrado, juegos), folds).mean(), 4),
                       "data-v1 con una regla de limpieza, partición congelada (ex.pr_auc_con_particion)")


# T8: cada candidata, cuándo se conoce y si entra al modelo de riesgo. Las del juego se comprueban
# contra construir_features(conjunto="juego"); las del autor, contra conjunto="completo".
VARIABLES_CANDIDATAS = [
    ("\\texttt{es\\_gratis}, precio (en logaritmo) y descuento", "en la tienda, antes de comprar", "sí"),
    ("Si tiene nota de Metacritic, y la nota", "en la tienda, antes de comprar",
     "sí; la nota que falta se rellena con la mediana, junto a la bandera"),
    ("\\texttt{num\\_games\\_owned}: juegos del autor", "en la reseña; en el sitio se declara «compras al año»",
     "no: su aporte cabe en el ruido entre folds, y 0 es un perfil privado"),
    ("\\texttt{num\\_reviews}: reseñas del autor", "al descargar; cambia con el tiempo", "no: describe al autor después de reseñar"),
    ("\\texttt{steam\\_purchase}, \\texttt{received\\_for\\_free} y \\texttt{written\\_during\\_early\\_access}",
     "en la reseña", "no: solo existen porque la reseña ya se escribió"),
    ("\\texttt{playtime\\_at\\_review} y \\texttt{voted\\_up}", "en la reseña", "no: definen $Y$"),
    ("Texto de la reseña", "en la reseña", "no: solo lo leen la exploración y los motivos"),
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


def tabla_de_externos(cifras: Cifras, rutas: dict[str, Path]) -> Path:
    """§7.4: los 83 de entrenamiento contra los 40 externos (00 §3.6). Solo describe: no decide nada."""
    juegos_v1, resenas_v1 = ex.cargar_release(rutas["data-v1"])
    juegos_v2, resenas_v2 = ex.cargar_release(rutas["data-v2"])
    externos = set(juegos_v2["appid"]) - set(juegos_v1["appid"])
    juegos_ext = juegos_v2[juegos_v2["appid"].isin(externos)]
    resenas_ext = resenas_v2[resenas_v2["appid"].isin(externos)]
    if ex.llaves(juegos_ext, resenas_ext)["casos"].sum() or ex.resumen_de_rango(ex.casos_de_rango(juegos_ext, resenas_ext))["casos"].sum():
        raise ValueError("los 40 externos ya no pasan las validaciones de llaves y rangos")

    columnas = {}
    for nombre, juegos, resenas in (("Entrenamiento", juegos_v1, resenas_v1), ("Externos", juegos_ext, resenas_ext)):
        por_juego = ex.tasa_por_juego(resenas, juegos)
        # Los gratis y los de pago sin precio no tienen precio_final: la mediana es la de los de pago con precio.
        precio = decimal(por_juego["precio_final"].median() / 100, 2)
        mediana, promedio = porcentaje(por_juego["tasa"].median()), porcentaje(por_juego["tasa"].mean())
        gratis = str(int(por_juego["es_gratis"].sum()))
        if nombre == "Externos":
            cifras.agregar("GratisExternos", gratis, "los 40 externos: juegos gratis")
            cifras.agregar("SinNotaExternos", str(int(por_juego["metacritic"].isna().sum())), "los 40 externos: juegos sin nota")
        cifras.agregar(f"PrecioMediano{nombre}", precio, f"{nombre.lower()}: mediana de precio_final / 100, juegos de pago con precio")
        cifras.agregar(f"Tasa{nombre}MedianaJuegos", mediana, f"{nombre.lower()}: mediana de las tasas por juego")
        cifras.agregar(f"Tasa{nombre}PromJuegos", promedio, f"{nombre.lower()}: promedio de las tasas por juego")
        columnas[nombre] = [
            entero(len(por_juego)), entero(len(resenas)), str(int((por_juego["reseñas"] >= ex.TOPE_DE_LA_INGESTA).sum())),
            gratis, str(int(por_juego["metacritic"].isna().sum())), str(int(por_juego["metacritic"].median())), precio,
            porcentaje(ex.senal(resenas).mean()), mediana, promedio,
        ]
    renglones = ["Juegos", "Reseñas", f"Juegos con el tope de {entero(ex.TOPE_DE_LA_INGESTA)} reseñas", "Juegos gratis",
                 "Juegos sin nota de la crítica", "Nota mediana (los que la tienen)", "Precio mediano de los de pago (pesos)",
                 "Tasa de señal por reseña", "Tasa de señal por juego: mediana", "Tasa de señal por juego: promedio"]
    filas = [f"{r} & {a} & {b} \\\\" for r, a, b in zip(renglones, columnas["Entrenamiento"], columnas["Externos"])]
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabular}{lrr}", "\\toprule", " & Entrenamiento (data-v1) & Externos \\\\", "\\midrule",
        *filas, "\\bottomrule", "\\end{tabular}",
    ]
    ruta = TABLAS / "externos.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def figura_tasa_por_juego(por_juego: pd.DataFrame, prevalencia: float) -> Path:
    """F3: la tasa de señal de cada juego de data-v1, de menor a mayor, con su intervalo de Wilson."""
    orden = por_juego.sort_values(["tasa", "nombre"]).reset_index()
    fig, eje = plt.subplots(figsize=(ANCHO_DE_TEXTO, 2.7))
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
    eje.annotate(texto, xy=(menor.index[-1] / 2, 100 * orden["tasa"].min()), xytext=(0, 52), textcoords="offset points",
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
    fig, (izquierda, derecha) = plt.subplots(1, 2, figsize=(ANCHO_DE_TEXTO, 2.9), sharey=True,
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


def tabla_de_calidad(cifras: Cifras, rutas: dict[str, Path]) -> Path:
    """T3: los chequeos de validación del 00 (§1.2–1.5) sobre data-v1, con lo que se hizo."""
    juegos, resenas = ex.cargar_release(rutas["data-v1"])
    esquema_resenas = ex.esquema(rutas["data-v1"], "resenas", resenas)
    llaves = ex.llaves(juegos, resenas)
    rango = ex.resumen_de_rango(ex.casos_de_rango(juegos, resenas))
    copias = ex.copias_de_texto(resenas, li.PALABRAS_DE_UNA_COPIA)
    plantillas = ex.plantillas(resenas)
    privados = (resenas["num_games_owned"] == 0).mean()
    sin_precio = juegos[juegos["precio_final"].isna()]
    de_pago_sin_precio = sin_precio[sin_precio["es_gratis"] == 0]["nombre"].tolist()
    sin_nota = int(juegos["metacritic"].isna().sum())
    verificacion = list(csv.DictReader(open(EVIDENCIA / "verificacion-40-steam.csv")))
    coinciden = sum(1 for f in verificacion if f["mc_guardado"] == f["mc_hoy"])
    duras = rango.loc[list(ex.REGLAS_DURAS), "casos"]
    blandas = rango.drop(index=list(ex.REGLAS_DURAS))["casos"]

    cifras.agregar("PrivadosEntrenamientoPorResena", porcentaje(privados, 1), "data-v1: num_games_owned = 0")
    cifras.agregar("SinNotaEntrenamiento", str(sin_nota), "data-v1: juegos sin nota de Metacritic")
    cifras.agregar("PagoSinPrecioEntrenamiento", str(len(de_pago_sin_precio)), "data-v1: juegos de pago sin precio")
    cifras.agregar("MetacriticVerificadoExternos", f"{coinciden} de {len(verificacion)}",
                   "docs/evidencia/verificacion-40-steam.csv")

    def fila(chequeo: str, resultado: str, decision: str) -> str:
        return f"{chequeo} & {resultado} & {decision} \\\\"

    def grupo(titulo: str) -> str:
        return f"\\multicolumn{{3}}{{l}}{{\\textit{{{titulo}}}}} \\\\"

    # Los 2 casos de «es_gratis coherente con el precio» son los mismos juegos de pago sin precio: van en una fila.
    incoherentes = int(blandas["es_gratis coherente con el precio"])
    assert incoherentes == len(de_pago_sin_precio), "la gratuidad incoherente ya no son solo los de pago sin precio"
    mas_minutos = int(blandas["playtime_at_review ≤ playtime_forever"])
    nota = ("\\textsuperscript{a}~\\texttt{playtime\\_at\\_review} y \\texttt{playtime\\_forever}; "
            "\\textsuperscript{b}~\\texttt{es\\_gratis} y \\texttt{precio\\_final}; "
            "\\textsuperscript{c}~\\texttt{metacritic\\_disponible}; \\textsuperscript{d}~\\texttt{num\\_games\\_owned}.")
    filas = [
        grupo("Sin hallazgos"),
        fila("Nulos en las reseñas", f"{int(esquema_resenas['nulos'].sum())} en {len(esquema_resenas)} columnas", "nada que corregir"),
        fila("Llaves: reseña repetida, juego sin reseñas, reseña sin juego", f"{int(llaves['casos'].sum())} casos", "nada que corregir"),
        fila(f"Rangos imposibles ({len(duras)} reglas: minutos negativos, voto fuera de 0 y 1, fechas, precio, descuento, nota)",
             f"{int(duras.sum())} casos", "nada que corregir"),
        fila(f"Nota de Metacritic contra la de la tienda hoy ({len(verificacion)} juegos externos)",
             f"{coinciden} de {len(verificacion)} iguales", "nada que corregir"),
        "\\midrule",
        grupo("Hallazgos y qué se hizo"),
        fila("Más minutos al reseñar que en total\\textsuperscript{a}", f"{mas_minutos} {'caso' if mas_minutos == 1 else 'casos'}",
             "se conserva: la señal no cambia con ninguno de los dos contadores"),
        fila("Juegos de pago sin precio\\textsuperscript{b}", f"{len(de_pago_sin_precio)}: {', '.join(de_pago_sin_precio)}",
             "precio tomado como 0, con aviso en la ficha (§\\ref{sec:procesamiento})"),
        fila("Juegos sin nota de Metacritic", f"{sin_nota} de {len(juegos)}", "la falta de nota es una variable del modelo\\textsuperscript{c}"),
        fila(f"Textos repetidos de {li.PALABRAS_DE_UNA_COPIA} palabras o más",
             f"{copias['sobrantes en el mismo juego']:,} en el mismo juego; {copias['textos en 2+ juegos']:,} en 2 o más juegos",
             "se marcan, no se borran (§\\ref{sec:procesamiento})"),
        fila("Reseñas plantilla", f"{len(plantillas):,} ({100 * len(plantillas) / len(resenas):.2f}\\,\\%)", "se marcan, no se borran"),
        fila("Perfil privado: aparece con 0 juegos\\textsuperscript{d}", f"{100 * privados:.1f}\\,\\% de las reseñas",
             "es una bandera de privacidad, no una biblioteca vacía"),
    ]
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{>{\\raggedright\\arraybackslash}X >{\\raggedright\\arraybackslash}p{3.9cm} >{\\raggedright\\arraybackslash}p{4.4cm}}",
        "\\toprule", "Chequeo (data-v1) & Resultado & Qué se hizo \\\\", "\\midrule", *filas, "\\bottomrule",
        f"\\multicolumn{{3}}{{>{{\\raggedright\\arraybackslash}}p{{\\dimexpr\\textwidth-2\\tabcolsep}}}}{{\\footnotesize Columnas: {nota}}} \\\\",
        "\\end{tabularx}",
    ]
    ruta = TABLAS / "calidad.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def tabla_de_umbrales(sensibilidad: pd.DataFrame) -> Path:
    """T5: la señal con 60, 90, 120 y 180 minutos, y qué tanto se parece el orden de los juegos al de 120."""
    filas = [f"{umbral} & {entero(int(f['Y=1']))} & {porcentaje(f['prevalencia'])} & {decimal(f['Spearman con 120'], 3)} \\\\"
             for umbral, f in sensibilidad.iterrows()]
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabular}{rrrr}", "\\toprule",
        "Umbral (min) & Reseñas con señal & Prevalencia por reseña & Spearman con 120 (por juego) \\\\",
        "\\midrule", *filas, "\\bottomrule", "\\end{tabular}",
    ]
    ruta = TABLAS / "umbral.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


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
    cifras_del_modelo(cifras, rutas)
    cifras_de_bandas(cifras)
    cifras_de_evidencia(cifras)
    cifras_del_periodo(cifras, rutas)
    sensibilidad = cifras_del_objetivo(cifras, rutas)
    juegos_v1, resenas_v1 = ex.cargar_release(rutas["data-v1"])
    por_juego = cifras_por_juego(cifras, juegos_v1, resenas_v1)
    cifras_de_coeficientes(cifras, juegos_v1, resenas_v1)
    limpio, pasos = conjunto_limpio(resenas_v1)
    cifras_del_texto(cifras, limpio)
    cifras_de_validacion(cifras, juegos_v1, resenas_v1)
    tablas = [tabla_de_releases(rutas), tabla_de_calidad(cifras, rutas), tabla_de_umbrales(sensibilidad),
              tabla_de_correlaciones(cifras, por_juego), tabla_de_externos(cifras, rutas),
              tabla_de_limpieza(cifras, limpio, pasos), tabla_de_variables(juegos_v1, resenas_v1)]
    ruta_cifras = cifras.escribir()
    estilo_de_figuras()
    figuras = [figura_resenas_por_mes(rutas), figura_minutos_al_resenar(rutas),
               figura_tasa_por_juego(por_juego, ex.senal(resenas_v1).mean()), figura_tasa_contra_nota(por_juego)]
    capturas = copiar_capturas()
    copiar_logo()

    print(f"{len(cifras.macros)} cifras en {ruta_cifras.relative_to(RAIZ)}")
    print(f"tablas: {', '.join(t.name for t in tablas)} · figuras: {', '.join(f.name for f in figuras)}")
    print(f"{len(capturas)} capturas copiadas a {(FIGURAS / 'capturas').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
