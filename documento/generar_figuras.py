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
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "modelado"), str(RAIZ / "calidad")]

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

# La paleta del frontend (tema claro), la misma de main.tex.
PALETA = {"bajo": "#047857", "medio": "#AA4F0A", "alto": "#BE123C", "acento": "#0E738F", "nia": "#6D28D9",
          "neutro": "#475585"}


# --- formato ---------------------------------------------------------------

def entero(n: int) -> str:
    return f"{n:,}"


def decimal(x: float, decimales: int) -> str:
    return f"{x:.{decimales}f}"


def porcentaje(x: float, decimales: int = 2) -> str:
    """x es una proporción: 0.0219 → «2.19 %»."""
    return f"{100 * x:.{decimales}f}\\,\\%"


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


# --- tablas ----------------------------------------------------------------

def tabla_de_releases(rutas: dict[str, Path]) -> Path:
    publicacion = publicacion_de_releases()
    filas = []
    for ref in ("data-v1", "data-v2", SERVIDO_REF):
        c = conteos(rutas[ref])
        for asset, datos in sorted(publicacion[ref]["assets"].items()):
            filas.append(f"{ref} & {publicacion[ref]['publicado']} & \\texttt{{{asset.replace('_', chr(92) + '_')}}} & "
                         f"{datos['bytes'] / 1e6:.1f} & \\texttt{{{datos['sha256'][:12]}…}} & "
                         f"{entero(c['juegos'])} & {entero(c['resenas'])} \\\\")
    contenido = [
        "% Generado por documento/generar_figuras.py. No se edita a mano.",
        "\\begin{tabular}{llp{4.2cm}rlrr}",
        "\\toprule",
        "Release & Publicado & Asset & MB & sha256 & Juegos & Reseñas \\\\",
        "\\midrule", *filas, "\\bottomrule", "\\end{tabular}",
    ]
    ruta = TABLAS / "releases.tex"
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
    ruta_cifras = cifras.escribir()
    ruta_releases = tabla_de_releases(rutas)
    capturas = copiar_capturas()

    print(f"{len(cifras.macros)} cifras en {ruta_cifras.relative_to(RAIZ)}")
    print(f"tabla de releases en {ruta_releases.relative_to(RAIZ)}")
    print(f"{len(capturas)} capturas copiadas a {(FIGURAS / 'capturas').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
