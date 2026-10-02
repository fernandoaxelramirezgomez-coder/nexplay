"""Ejecuta los tres notebooks con el código del último commit y compara sus salidas con las guardadas.

No escribe nada en notebooks/: las salidas que se guardan en el repo se eligen a mano (el 01 guarda las de
Colab; el 00, las de una corrida local con PNG; el 02, las de una corrida local). Esto comprueba, en local, que los notebooks corren de punta a punta con el código de
este checkout y dan las mismas cifras.

Cómo lo hace:
- exporta el último commit (git archive HEAD) como repo_nexplay/ en una carpeta temporal. Es lo mismo que
  traerá el tag, y al encontrarlo la celda de clon no clona;
- ejecuta 00_exploracion, 01_modelo_riesgo y 02_modelos_texto ahí, en ese orden;
- compara, celda por celda, el stdout, el texto de las tablas y los errores contra lo guardado. El stdout se
  une antes de comparar, porque Jupyter lo parte distinto en cada corrida. Las gráficas no se comparan.
  Las celdas del clon, de las versiones del entorno y de la configuración de las gráficas (con PNG solo si
  hay Chrome) cambian de una máquina a otra: se listan aparte.

Sale con 1 si falta algo o si un notebook no termina (sus asserts, 34 en el 00, 6 en el 01 y 22 en el 02,
detienen la ejecución si una cifra deja de sostenerse). Las celdas con una salida distinta se listan con su diff para
revisarlas, pero no hacen fallar: las salidas guardadas pueden venir de Colab, y otra versión de pandas escribe
distinto los tipos o desempata en otro orden sin que cambie ninguna cifra.

Uso, desde backend/ (make notebooks, desde la raíz, instala antes lo que hace falta):
  python calidad/correr_notebooks.py                        # en una carpeta temporal nueva
  python calidad/correr_notebooks.py --carpeta /ruta/vacia
"""

import argparse
import difflib
import importlib.util
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOTEBOOKS = ("00_exploracion", "01_modelo_riesgo", "02_modelos_texto")
PAQUETES = {"nbclient": "nbclient", "nbformat": "nbformat", "ipykernel": "ipykernel", "plotly": "plotly",
            "lingua": "lingua-language-detector",
            "sentence_transformers": "sentence-transformers", "pyarrow": "pyarrow", "requests": "requests",
            "wordcloud": "wordcloud"}
# Las celdas cuya salida depende de la máquina, reconocidas por su código.
MARCAS_DE_ENTORNO = ("repo_nexplay ya existe", "__version__", "configurar_graficas")
# Cómo empiezan las líneas con la cifra principal de cada notebook, para verlas sin abrirlos.
CIFRAS = ("GroupKFold por appid ", "PR-AUC GroupKFold del modelo de produccion", "Rama ")


def _comprobar_paquetes() -> None:
    faltan = [paquete for modulo, paquete in PAQUETES.items() if importlib.util.find_spec(modulo) is None]
    if faltan:
        sys.exit(f"Faltan paquetes para los notebooks: {', '.join(faltan)}.\n"
                 "Corre `make notebooks` desde la raíz (los instala), o desde backend/:\n"
                 "  pip install -r requirements-notebooks.txt -r requirements-dev.txt")


def _git(*argumentos: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *argumentos], capture_output=True, check=False)


def _preparar_carpeta(carpeta: Path | None) -> Path:
    if carpeta is None:
        return Path(tempfile.mkdtemp(prefix="nexplay-notebooks-"))
    if carpeta.exists() and any(carpeta.iterdir()):
        sys.exit(f"{carpeta} ya existe y no está vacía: usa otra carpeta o bórrala tú.")
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta.resolve()


def _exportar_commit(destino: Path) -> str:
    if shutil.which("git") is None:
        sys.exit("Hace falta git para exportar el último commit.")
    commit = _git("rev-parse", "--short", "HEAD")
    if commit.returncode != 0:
        sys.exit(f"{REPO} no es un checkout de git con commits: no hay código que exportar.")
    if _git("status", "--porcelain", "--untracked-files=no").stdout.strip():
        print("Aviso: hay cambios sin commit. Se ejecuta el último commit (HEAD), no el árbol de trabajo.")
    archivo = _git("archive", "HEAD")
    if archivo.returncode != 0:
        sys.exit(f"git archive falló: {archivo.stderr.decode(errors='replace').strip()}")
    with tarfile.open(fileobj=io.BytesIO(archivo.stdout)) as tar:
        tar.extractall(destino / "repo_nexplay", filter="data")
    return commit.stdout.decode().strip()


def _ejecutar(carpeta: Path, nombre: str):
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    notebook = nbformat.read(carpeta / f"{nombre}.ipynb", as_version=4)
    cliente = NotebookClient(notebook, timeout=3600, kernel_name="python3", resources={"metadata": {"path": str(carpeta)}})
    inicio = time.monotonic()
    try:
        cliente.execute()
    except CellExecutionError as exc:
        nbformat.write(notebook, carpeta / f"{nombre}-ejecutado.ipynb")
        detalle = "\n".join(str(exc).strip().splitlines()[-6:])
        sys.exit(f"{nombre} falló al ejecutarse. Lo ejecutado hasta ahí quedó en "
                 f"{carpeta / (nombre + '-ejecutado.ipynb')}.\nÚltimas líneas del error:\n{detalle}")
    nbformat.write(notebook, carpeta / f"{nombre}-ejecutado.ipynb")
    return notebook, time.monotonic() - inicio


def _salidas(celda) -> list[str]:
    """El stdout unido, el texto de cada tabla o valor y los errores. Ni gráficas ni stderr."""
    stdout = "".join("".join(o["text"]) for o in celda.get("outputs", [])
                     if o["output_type"] == "stream" and o["name"] == "stdout")
    resto = []
    for o in celda.get("outputs", []):
        datos = o.get("data", {})
        if o["output_type"] in ("execute_result", "display_data") and "text/plain" in datos:
            if not {"image/png", "application/vnd.plotly.v1+json"} & set(datos):
                resto.append("".join(datos["text/plain"]))
        elif o["output_type"] == "error":
            resto.append(f"{o['ename']}: {o['evalue']}")
    return ([stdout] if stdout else []) + resto


def _comparar(nombre: str, guardado, ejecutado) -> int:
    if len(guardado.cells) != len(ejecutado.cells):
        print(f"  {nombre}: el notebook ejecutado tiene {len(ejecutado.cells)} celdas y el guardado {len(guardado.cells)}")
        return 1
    distintas, de_entorno, iguales = [], [], 0
    for i, (g, e) in enumerate(zip(guardado.cells, ejecutado.cells)):
        if g.cell_type != "code":
            continue
        if _salidas(g) == _salidas(e):
            iguales += 1
        elif any(marca in g.source for marca in MARCAS_DE_ENTORNO):
            de_entorno.append(i)
        else:
            distintas.append(i)
    print(f"  {nombre}: {iguales} celdas con la misma salida; "
          f"de entorno (clon, versiones o gráficas): {de_entorno or 'ninguna'}; distintas: {distintas or 'ninguna'}")
    for i in distintas:
        diff = difflib.unified_diff("\n".join(_salidas(guardado.cells[i])).splitlines(),
                                    "\n".join(_salidas(ejecutado.cells[i])).splitlines(),
                                    "guardado", "ejecutado", lineterm="", n=0)
        print(f"    celda {i}:")
        for linea in list(diff)[2:12]:
            print(f"      {linea[:150]}")
    return len(distintas)


def _cifras(ejecutado) -> list[str]:
    return [" ".join(linea.split()) for celda in ejecutado.cells if celda.cell_type == "code"
            for texto in _salidas(celda) for linea in texto.splitlines() if linea.strip().startswith(CIFRAS)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta los notebooks con el último commit y compara sus salidas")
    parser.add_argument("--carpeta", type=Path, help="carpeta vacía o nueva para la ejecución (por defecto, una temporal)")
    args = parser.parse_args()

    _comprobar_paquetes()
    carpeta = _preparar_carpeta(args.carpeta)
    commit = _exportar_commit(carpeta)
    for nombre in NOTEBOOKS:
        shutil.copy(REPO / "notebooks" / f"{nombre}.ipynb", carpeta)
    print(f"Ejecutando con el commit {commit} en {carpeta}")

    import nbformat

    diferencias = 0
    for nombre in NOTEBOOKS:
        ejecutado, segundos = _ejecutar(carpeta, nombre)
        print(f"{nombre}: ejecutado en {segundos:.0f} s")
        guardado = nbformat.read(REPO / "notebooks" / f"{nombre}.ipynb", as_version=4)
        diferencias += _comparar(nombre, guardado, ejecutado)
        for linea in _cifras(ejecutado):
            print(f"    {linea}")

    print(f"Los notebooks ejecutados quedaron en {carpeta}; los de notebooks/ no cambiaron.")
    if diferencias:
        print(f"{diferencias} celdas dan una salida distinta de la guardada: revisa el diff de arriba. Si solo cambia "
              "cómo se escribe un tipo o el orden de un empate, no es una cifra distinta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
