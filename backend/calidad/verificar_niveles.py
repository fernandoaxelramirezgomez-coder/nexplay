"""Una sola definición de los niveles de riesgo en todo el sitio.

Los cortes entre bajo, medio y alto están en los percentiles 33.3 y 66.7 de las estimaciones
fuera de pliegue del entrenamiento (modelado/entrenar_modelo.py), no en tercios del catálogo:
con ellos el catálogo queda en 43, 37 y 43. Antes, Nia, la metodología y Panorama decían
«tres partes iguales del catálogo», «tercios del score» o «relativo al catálogo». Revisa:

1. La definición de la API (CORTES_DE_NIVEL en api/nia/agente.py) es la misma del frontend
   (frontend/src/app/dominio/etiqueta-riesgo.ts), y sus conteos son los del catálogo.
2. La metodología que Nia le da al modelo (herramientas.metodologia) la usa.
3. Ningún texto de frontend/src, de api ni del README de la raíz vuelve a la definición anterior.
4. El README de la raíz dice la definición tal cual, con los conteos del catálogo.
5. entrenar_modelo.py sigue cortando en esos percentiles: si cambian, la definición también.
6. La señal por nivel del Inicio (api/panorama.py): sus externos son los 40 de la prueba externa
   y su cociente e intervalo son los de docs/evidencia/senal-por-nivel.md.

Uso, desde backend/:
    python calidad/verificar_niveles.py        # sale 1 si algún chequeo falla
"""

import json
import logging
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# Corre desde calidad/, así que la raíz no está en sys.path y `api` no se encontraría.
sys.path.insert(0, str(RAIZ))
logging.disable(logging.CRITICAL)

from api import catalogo, panorama  # noqa: E402
from api.nia import agente as nia  # noqa: E402
from api.nia import herramientas  # noqa: E402

DEFINICION_DEL_FRONTEND = RAIZ.parent / "frontend" / "src" / "app" / "dominio" / "etiqueta-riesgo.ts"
ENTRENAR_MODELO = RAIZ / "modelado" / "entrenar_modelo.py"
README = RAIZ.parent / "README.md"
EXTERNOS = RAIZ.parent / "docs" / "evidencia" / "prueba-externa.json"
EVIDENCIA_SENAL = RAIZ.parent / "docs" / "evidencia" / "senal-por-nivel.md"

# Lo que decían antes los textos: nada de esto es cierto con los cortes de hoy.
DEFINICION_ANTERIOR = re.compile(
    r"tercios del (?:score|catálogo|modelo)|son tercios|tres tercios|tres partes iguales|partes iguales del catálogo"
    r"|relativo al catálogo|terciles? de (?:la|los)|reparte el catálogo en tres|compara un juego con los demás",
    re.IGNORECASE,
)


def _textos_del_sitio() -> list[Path]:
    rutas = []
    for carpeta, patrones in ((RAIZ.parent / "frontend" / "src", ("*.ts", "*.html")), (RAIZ / "api", ("*.py", "*.md"))):
        for patron in patrones:
            rutas += [r for r in carpeta.rglob(patron) if not r.name.endswith(".spec.ts")]
    return sorted(rutas) + [README]


def main() -> int:
    problemas = []

    del_frontend = re.search(r"export const CORTES_DE_NIVEL =\s*'([^']+)'", DEFINICION_DEL_FRONTEND.read_text())
    if del_frontend is None or del_frontend.group(1) != nia.CORTES_DE_NIVEL:
        problemas.append(f"la definición del frontend no es la de la API: {del_frontend and del_frontend.group(1)!r}")
    cuantos = {nivel: sum(j.banda_riesgo.value == nivel for j in catalogo.buscar()) for nivel in ("bajo", "medio", "alto")}
    definicion = nia.definicion_de_los_niveles()
    esperada = f"{nia.CORTES_DE_NIVEL}; en el catálogo quedan {cuantos['bajo']}, {cuantos['medio']} y {cuantos['alto']}."
    if definicion != esperada:
        problemas.append(f"la definición no da los conteos del catálogo ({cuantos}): {definicion}")
    print(f"1 · definición: {definicion}")

    if definicion not in herramientas.metodologia()["texto"]:
        problemas.append("la metodología de Nia no usa la definición de los niveles")
    print("2 · la metodología de Nia usa la definición")

    rutas = _textos_del_sitio()
    for ruta in rutas:
        for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1):
            if encontrada := DEFINICION_ANTERIOR.search(linea):
                problemas.append(f"{ruta.relative_to(RAIZ.parent)}:{numero} dice «{encontrada.group(0)}»")
    print(f"3 · definición anterior: revisados {len(rutas)} archivos de frontend/src, api y el README")

    # El README parte las líneas a su ancho: se compara con los espacios juntos.
    if definicion not in " ".join(README.read_text(encoding="utf-8").split()):
        problemas.append(f"el README de la raíz no dice la definición de los niveles: {definicion}")
    print("4 · el README de la raíz dice la definición")

    entrenar = ENTRENAR_MODELO.read_text()
    if "np.percentile(oof, 100 / 3)" not in entrenar or "np.percentile(oof, 200 / 3)" not in entrenar:
        problemas.append("entrenar_modelo.py ya no corta en los percentiles 33.3 y 66.7 de los scores OOF")
    print("5 · entrenar_modelo.py corta en los percentiles 33.3 y 66.7 de las estimaciones OOF")

    cortes = {corte.corte: corte for corte in panorama.resumen().senal_por_nivel}
    externos = {juego["appid"] for juego in json.loads(EXTERNOS.read_text(encoding="utf-8"))["por_titulo"]}
    sin_ver = {juego.appid for juego in catalogo.buscar()} - panorama.juegos_de_entrenamiento()
    if sin_ver != externos or cortes["externos"].juegos != len(externos):
        problemas.append(f"los juegos que el modelo no vio ({len(sin_ver)}) no son los {len(externos)} de la prueba externa")
    if [n.juegos for n in cortes["catalogo"].niveles] != [cuantos["bajo"], cuantos["medio"], cuantos["alto"]]:
        problemas.append("la señal por nivel no cuenta los juegos de cada nivel del catálogo")
    evidencia = EVIDENCIA_SENAL.read_text(encoding="utf-8")
    catalogo_md = re.search(r"\| Catálogo \(123\) \| \*\*([\d.]+)×\*\*", evidencia)
    externos_md = re.search(r"\| Externos \(40\) \| \*\*([\d.]+)×\*\* \| ([\d.]+)× a ([\d.]+)× \|", evidencia)
    ext = cortes["externos"]
    calculado = (f"{cortes['catalogo'].cociente_alto_bajo:.2f}", f"{ext.cociente_alto_bajo:.2f}",
                 f"{ext.ic_inferior:.2f}", f"{ext.ic_superior:.2f}")
    if not (catalogo_md and externos_md) or calculado != (catalogo_md.group(1), *externos_md.groups()):
        problemas.append(f"la señal por nivel del Inicio {calculado} no es la de {EVIDENCIA_SENAL.name}")
    print(f"6 · el Inicio: {ext.cociente_alto_bajo:.2f}× en los {ext.juegos} externos ({ext.ic_inferior:.2f}× a "
          f"{ext.ic_superior:.2f}×) y {cortes['catalogo'].cociente_alto_bajo:.2f}× en los 123, como la evidencia")

    print()
    for problema in problemas:
        print(f"PROBLEMA: {problema}")
    if problemas:
        return 1
    print("niveles: una sola definición en todo el sitio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
