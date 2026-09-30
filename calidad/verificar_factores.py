"""La regla de «Qué mueve esta estimación» en los 123 juegos (decisión del 2026-09-30).

1. El primer factor es el de mayor aporte según el modelo, sin excepciones.
2. Todo factor de precio, descuento o gratuidad lleva evidencia «debil».
3. Todo factor de crítica (cobertura o nota) lleva evidencia «solida».
4. Los juegos gratis llevan el aviso «gratis_extrapola».
5. Los juegos con precio imputado llevan el aviso «precio_imputado», y el factor de precio se
   muestra en su lugar por aporte, sin ocultarse. En GTA V Legacy es el primero; en New World
   lo supera la falta de nota de la crítica, y el chequeo 1 ya exige ese orden.

Fija el contrato de la ronda «explicar el riesgo»: `FactorPrediccion.evidencia` y
`PrediccionRiesgo.avisos` (código y texto). Hasta esa ronda falla a propósito; ver
docs/plan/mejoras/01-antes-del-reembolso.md. La parte de interfaz (que la ficha deje de ocultar
el precio imputado y pinte la evidencia y los avisos) la cubrirán un spec de
frontend/src/app/dominio/factores.ts y calidad/capturar_ui.py.

El aporte se calcula aquí por separado —coeficiente × valor estandarizado, con el pipeline
del artefacto— para no fiarse del orden que manda la API.

Uso, desde la raíz:
    python calidad/verificar_factores.py        # sale 1 si algún chequeo falla
"""

import sys
from pathlib import Path

# Corre desde calidad/, así que la raíz no está en sys.path y `api` no se encontraría.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import catalogo, scoring  # noqa: E402

EVIDENCIA_ESPERADA = {
    "precio del juego": "debil",
    "descuento actual del juego": "debil",
    "gratuidad del juego": "debil",
    "cobertura de crítica especializada": "solida",
    "nota de Metacritic": "solida",
}
DEBILES = {etiqueta for etiqueta, nivel in EVIDENCIA_ESPERADA.items() if nivel == "debil"}


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


def revisar() -> dict[str, list[tuple[str, str]]]:
    """Por chequeo, los juegos que lo rompen, cada uno con el detalle."""
    fallas = {nombre: [] for nombre in ("1 · primer factor", "2 · evidencia débil", "3 · evidencia sólida",
                                         "4 · aviso de gratis", "5 · precio imputado")}
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
                fallas[chequeo].append((juego.nombre, f"{factor.etiqueta} lleva {nivel or 'sin campo evidencia'}"))
        codigos = _codigos_de_aviso(prediccion)
        if juego.es_gratis and (codigos is None or "gratis_extrapola" not in codigos):
            fallas["4 · aviso de gratis"].append((juego.nombre, "sin campo avisos" if codigos is None else "sin el aviso"))
        if not juego.es_gratis and juego.precio_final is None:
            if codigos is None or "precio_imputado" not in codigos:
                fallas["5 · precio imputado"].append((juego.nombre, "sin campo avisos" if codigos is None else "sin el aviso"))
            if "precio del juego" not in {factor.etiqueta for factor in factores}:
                fallas["5 · precio imputado"].append((juego.nombre, "no trae el factor de precio"))
    return fallas


def main() -> int:
    total = len(catalogo.buscar())
    fallas = revisar()
    for nombre, lista in fallas.items():
        if not lista:
            print(f"{nombre}: ok en los {total} juegos")
            continue
        juegos = {juego for juego, _ in lista}
        print(f"{nombre}: FALLA en {len(juegos)} juegos")
        for juego, detalle in lista[:6]:
            print(f"    {juego}: {detalle}")
        if len(lista) > 6:
            print(f"    … y {len(lista) - 6} casos más")
    return 1 if any(fallas.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
