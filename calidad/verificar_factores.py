"""La regla de «Qué mueve esta estimación» en los 123 juegos (decisión del 2026-09-30).

1. El primer factor es el de mayor aporte según el modelo, sin excepciones.
2. Todo factor de precio, descuento o gratuidad lleva evidencia «debil».
3. Todo factor de crítica (cobertura o nota) lleva evidencia «solida».
4. Los juegos gratis llevan el aviso «gratis_extrapola».
5. Los juegos con precio imputado llevan el aviso «precio_imputado», y el factor de precio se
   muestra marcado como imputado, en su lugar por aporte. En GTA V Legacy es el primero; en
   New World lo supera la falta de nota de la crítica, y el chequeo 1 ya exige ese orden.
6. Fuera de la banda neutral, ninguna flecha contradice la cifra que se muestra: una nota por
   encima del promedio del catálogo no sube el riesgo, un precio por debajo de la mediana no
   lo sube, y un descuento no lo sube.
7. `cerca_de_lo_tipico` coincide con |aporte| < scoring.UMBRAL_TIPICO. Imprime cuántos juegos
   caen en la banda por factor.
8. Ningún texto del sitio dice «no con sus reseñas»: el modelo sí se entrenó con reseñas.

Es la puerta de aceptación de la ronda «explicar el riesgo»
(docs/plan/mejoras/01-antes-del-reembolso.md, «Aparte»). La interfaz la cubren los specs de
frontend/src/app/dominio/factores.ts y calidad/capturar_ui.py.

El aporte se calcula aquí por separado —coeficiente × valor estandarizado, con el pipeline
del artefacto— para no fiarse del orden que manda la API.

Uso, desde la raíz:
    python calidad/verificar_factores.py        # sale 1 si algún chequeo falla
"""

import collections
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# Corre desde calidad/, así que la raíz no está en sys.path y `api` no se encontraría.
sys.path.insert(0, str(RAIZ))

from api import catalogo, scoring  # noqa: E402

EVIDENCIA_ESPERADA = {
    "precio del juego": "debil",
    "descuento actual del juego": "debil",
    "gratuidad del juego": "debil",
    "cobertura de crítica especializada": "solida",
    "nota de Metacritic": "solida",
}
DEBILES = {etiqueta for etiqueta, nivel in EVIDENCIA_ESPERADA.items() if nivel == "debil"}
FRASE_PROHIBIDA = "no con sus reseñas"


def _contradice(factor) -> bool:
    """Si la flecha va contra la comparación que se muestra junto al factor."""
    sube = factor.direccion.value == "aumenta"
    if factor.etiqueta == "nota de Metacritic" and factor.valor is not None and factor.referencia is not None:
        return (factor.valor > factor.referencia and sube) or (factor.valor < factor.referencia and not sube)
    if factor.etiqueta == "precio del juego" and factor.valor is not None and factor.referencia is not None:
        return (factor.valor < factor.referencia and sube) or (factor.valor > factor.referencia and not sube)
    if factor.etiqueta == "descuento actual del juego" and factor.valor is not None:
        return (factor.valor > 0 and sube) or (factor.valor == 0 and not sube)
    return False


ARCHIVOS_REVISADOS = 0


def _textos_con_la_frase_prohibida() -> list[tuple[str, str]]:
    global ARCHIVOS_REVISADOS
    encontrados = []
    for carpeta, patrones in ((RAIZ / "frontend" / "src", ("*.ts", "*.html")), (RAIZ / "api", ("*.py",))):
        for patron in patrones:
            for ruta in carpeta.rglob(patron):
                if ruta.name.endswith(".spec.ts"):
                    continue
                ARCHIVOS_REVISADOS += 1
                for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                    if FRASE_PROHIBIDA in linea:
                        encontrados.append((str(ruta.relative_to(RAIZ)), f"línea {numero}"))
    return encontrados


def _mayor_aporte(appid: int) -> str:
    X = scoring._construir_features(scoring._PERFIL_NEUTRO, appid)
    escalador = scoring._PIPELINE.named_steps["escalar"]
    coeficientes = scoring._PIPELINE.named_steps["clf"].coef_[0]
    aportes = coeficientes * escalador.transform(X)[0]
    variable = scoring._FEATURES[int(abs(aportes).argmax())]
    return scoring._ETIQUETAS_FEATURES[variable]


def _codigos_de_aviso(prediccion) -> set[str] | None:
    avisos = getattr(prediccion, "avisos", None)
    if avisos is None:
        return None
    return {aviso.codigo if hasattr(aviso, "codigo") else aviso["codigo"] for aviso in avisos}


EN_LA_BANDA: collections.Counter = collections.Counter()


def revisar() -> dict[str, list[tuple[str, str]]]:
    """Por chequeo, los juegos que lo rompen, cada uno con el detalle."""
    fallas = {nombre: [] for nombre in ("1 · primer factor", "2 · evidencia débil", "3 · evidencia sólida",
                                         "4 · aviso de gratis", "5 · precio imputado", "6 · flecha contra la cifra",
                                         "7 · banda neutral", "8 · «no con sus reseñas»")}
    for juego in catalogo.buscar():
        prediccion = scoring.prediccion_de_titulo(juego.appid)
        factores = prediccion.factores
        esperado = _mayor_aporte(juego.appid)
        if not factores or factores[0].etiqueta != esperado:
            fallas["1 · primer factor"].append((juego.nombre, f"sale {factores[0].etiqueta if factores else 'nada'}, "
                                                                f"el mayor aporte es {esperado}"))
        for factor in factores:
            nivel = getattr(factor, "evidencia", None)
            chequeo = "2 · evidencia débil" if factor.etiqueta in DEBILES else "3 · evidencia sólida"
            if factor.etiqueta in EVIDENCIA_ESPERADA and nivel != EVIDENCIA_ESPERADA[factor.etiqueta]:
                fallas[chequeo].append((juego.nombre, f"{factor.etiqueta} lleva {getattr(nivel, 'value', nivel) or 'sin campo evidencia'}"))
            en_la_banda = abs(factor.contribucion) < scoring.UMBRAL_TIPICO
            if getattr(factor, "cerca_de_lo_tipico", None) != en_la_banda:
                fallas["7 · banda neutral"].append((juego.nombre, f"{factor.etiqueta}: aporte {factor.contribucion:+.4f}"))
            if en_la_banda:
                EN_LA_BANDA[factor.etiqueta] += 1
            elif _contradice(factor):
                fallas["6 · flecha contra la cifra"].append(
                    (juego.nombre, f"{factor.etiqueta} {factor.valor} contra {factor.referencia}, flecha {factor.direccion.value}"))
        codigos = _codigos_de_aviso(prediccion)
        if juego.es_gratis and (codigos is None or "gratis_extrapola" not in codigos):
            fallas["4 · aviso de gratis"].append((juego.nombre, "sin campo avisos" if codigos is None else "sin el aviso"))
        if not juego.es_gratis and juego.precio_final is None:
            if codigos is None or "precio_imputado" not in codigos:
                fallas["5 · precio imputado"].append((juego.nombre, "sin campo avisos" if codigos is None else "sin el aviso"))
            if not any(f.etiqueta == "precio del juego" and getattr(f, "imputado", False) for f in factores):
                fallas["5 · precio imputado"].append((juego.nombre, "no trae el factor de precio marcado como imputado"))
    fallas["8 · «no con sus reseñas»"] = _textos_con_la_frase_prohibida()
    return fallas


def main() -> int:
    total = len(catalogo.buscar())
    fallas = revisar()
    for nombre, lista in fallas.items():
        if not lista:
            donde = f"{ARCHIVOS_REVISADOS} archivos de frontend/src y api" if nombre.startswith("8") else f"{total} juegos"
            print(f"{nombre}: ok en los {donde}")
            continue
        juegos = {juego for juego, _ in lista}
        print(f"{nombre}: FALLA en {len(juegos)} {'archivos' if nombre.startswith('8') else 'juegos'}")
        for juego, detalle in lista[:6]:
            print(f"    {juego}: {detalle}")
        if len(lista) > 6:
            print(f"    … y {len(lista) - 6} casos más")
    print(f"banda neutral (|aporte| < {scoring.UMBRAL_TIPICO}), juegos por factor: "
          + ", ".join(f"{etiqueta} {cuantos}" for etiqueta, cuantos in EN_LA_BANDA.most_common()))
    return 1 if any(fallas.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
