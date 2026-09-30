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
import re
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
sys.path[:0] = [str(RAIZ), str(RAIZ / "modelado"), str(RAIZ / "calidad"), str(RAIZ / "analisis")]

import exploracion as ex  # noqa: E402
from limpieza import PALABRAS_DE_UNA_COPIA  # noqa: E402

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
PALETA = {"bajo": "#047857", "medio": "#AA4F0A", "alto": "#BE123C", "acento": "#0E738F", "serie": "#0A7EA4",
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
    appids_v1 = {int(f["appid"]) for f in csv.DictReader(open(RAIZ / "referencias" / "particion_gkf_data-v1.csv"))}
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
    cifras.agregar("PRAUCCociente", decimal(modelo.mean() / trivial.mean(), 2), fuente)
    cifras.agregar("PliegosGanados", str(int((modelo > trivial).sum())), fuente + ": pliegues donde el modelo supera al trivial")
    cifras.agregar("Pliegues", str(len(modelo)), fuente)

    oof = _scores_oof(X, y, grupos)
    cifras.agregar("UmbralMedio", decimal(np.percentile(oof, 100 / 3), 4), "percentil 33.3 de los scores fuera de pliegue")
    cifras.agregar("UmbralAlto", decimal(np.percentile(oof, 200 / 3), 4), "percentil 66.7 de los scores fuera de pliegue")


def cifras_de_bandas(cifras: Cifras) -> None:
    bandas = json.loads((RAIZ / "referencias" / "bandas_referencia.json").read_text())["bandas"]
    bandas = {int(appid): (b if isinstance(b, str) else b.get("banda")) for appid, b in bandas.items()}
    appids_v1 = {int(f["appid"]) for f in csv.DictReader(open(RAIZ / "referencias" / "particion_gkf_data-v1.csv"))}
    for nombre, appids in (("Entrenamiento", appids_v1), ("Catalogo", set(bandas))):
        for banda in ("bajo", "medio", "alto"):
            cifras.agregar(f"{banda.capitalize()}{nombre}", str(sum(1 for a in appids if bandas[a] == banda)),
                           "referencias/bandas_referencia.json")


def cifras_de_evidencia(cifras: Cifras) -> None:
    externa = json.loads((EVIDENCIA / "prueba-externa.json").read_text())["resumen"]
    bootstrap = json.loads((EVIDENCIA / "bootstrap-prueba-externa.json").read_text())
    cifras.agregar("PRAUCExterno", decimal(externa["pr_auc_externo"], 4), "docs/evidencia/prueba-externa.json")
    cifras.agregar("PRAUCExternoTrivial", decimal(externa["pr_auc_trivial"], 4), "docs/evidencia/prueba-externa.json")
    cifras.agregar("PRAUCExternoCociente", decimal(externa["pr_auc_externo"] / externa["pr_auc_trivial"], 2),
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
    cifras.agregar("TopeIngesta", entero(ex.TOPE_DE_LA_INGESTA), "ingesta/ingesta_steam.py: MAX_RESENAS_POR_JUEGO")
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
    publicacion = publicacion_de_releases()
    filas = []
    for ref in ("data-v1", "data-v2", SERVIDO_REF):
        c = conteos(rutas[ref])
        for asset, datos in sorted(publicacion[ref]["assets"].items()):
            nombre = asset.replace("_", "\\_\\allowbreak{}").replace(".", ".\\allowbreak{}")
            filas.append(f"{ref} & {publicacion[ref]['publicado']} & \\texttt{{{nombre}}} & "
                         f"{datos['bytes'] / 1e6:.1f} & \\texttt{{{datos['sha256'][:12]}…}} & "
                         f"{entero(c['juegos'])} & {entero(c['resenas'])} \\\\")
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{ll>{\\raggedright\\arraybackslash}Xrlrr}",
        "\\toprule",
        "Release & Publicado & Asset & MB & sha256 & Juegos & Reseñas \\\\",
        "\\midrule", *filas, "\\bottomrule", "\\end{tabularx}",
    ]
    ruta = TABLAS / "releases.tex"
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def codigo(texto: str) -> str:
    """Los nombres de columna (los que llevan guion bajo) en monoespaciada, escapados para LaTeX."""
    return re.sub(r"\w*_\w*", lambda m: "\\texttt{" + m.group(0).replace("_", "\\_\\allowbreak{}") + "}", texto)


def tabla_de_calidad(cifras: Cifras, rutas: dict[str, Path]) -> Path:
    """T3: los chequeos de validación del 00 (§1.2–1.5) sobre data-v1, con lo que se hizo."""
    juegos, resenas = ex.cargar_release(rutas["data-v1"])
    esquema_resenas = ex.esquema(rutas["data-v1"], "resenas", resenas)
    llaves = ex.llaves(juegos, resenas)
    rango = ex.resumen_de_rango(ex.casos_de_rango(juegos, resenas))
    copias = ex.copias_de_texto(resenas, PALABRAS_DE_UNA_COPIA)
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

    filas = [
        fila("Nulos en las reseñas", f"{int(esquema_resenas['nulos'].sum())} en {len(esquema_resenas)} columnas", "ninguna"),
        fila("Llaves: reseña repetida, juego sin reseñas, reseña sin juego", f"{int(llaves['casos'].sum())} casos", "ninguna"),
        fila(f"Rangos duros ({len(duras)} reglas: minutos ≥ 0, voto 0/1, fechas, precio, descuento, nota)",
             f"{int(duras.sum())} casos", "ninguna"),
        *(fila(codigo(regla), f"{int(casos)} {'caso' if casos == 1 else 'casos'}", "se conservan y se documentan")
          for regla, casos in blandas.items()),
        fila("Juegos de pago sin precio", f"{len(de_pago_sin_precio)}: {', '.join(de_pago_sin_precio)}",
             "precio tomado como 0, con aviso (§\\ref{sec:procesamiento})"),
        fila("Juegos sin nota de Metacritic", f"{sin_nota} de {len(juegos)}", "es un dato: variable " + codigo("metacritic_disponible")),
        fila("Nota de Metacritic contra la tienda hoy (40 externos)", f"{coinciden} de {len(verificacion)} iguales", "ninguna"),
        fila(f"Textos repetidos de {PALABRAS_DE_UNA_COPIA}+ palabras",
             f"{copias['sobrantes en el mismo juego']:,} en el mismo juego; {copias['textos en 2+ juegos']:,} en 2+ juegos",
             "se marcan, no se borran (§\\ref{sec:procesamiento})"),
        fila("Reseñas plantilla", f"{len(plantillas):,} ({100 * len(plantillas) / len(resenas):.2f}\\,\\%)", "se marcan, no se borran"),
        fila(f"Perfil privado ({codigo('num_games_owned')} = 0)", f"{100 * privados:.1f}\\,\\% de las reseñas",
             "bandera de privacidad, no biblioteca vacía"),
    ]
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabularx}{\\textwidth}{>{\\raggedright\\arraybackslash}X >{\\raggedright\\arraybackslash}p{4.2cm} >{\\raggedright\\arraybackslash}p{4.2cm}}",
        "\\toprule", "Chequeo (data-v1) & Resultado & Qué se hizo \\\\", "\\midrule", *filas, "\\bottomrule",
        "\\end{tabularx}",
    ]
    ruta = TABLAS / "calidad.tex"
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
    tablas = [tabla_de_releases(rutas), tabla_de_calidad(cifras, rutas)]
    ruta_cifras = cifras.escribir()
    estilo_de_figuras()
    figuras = [figura_resenas_por_mes(rutas)]
    capturas = copiar_capturas()

    print(f"{len(cifras.macros)} cifras en {ruta_cifras.relative_to(RAIZ)}")
    print(f"tablas: {', '.join(t.name for t in tablas)} · figuras: {', '.join(f.name for f in figuras)}")
    print(f"{len(capturas)} capturas copiadas a {(FIGURAS / 'capturas').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
