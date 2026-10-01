"""Pruebas A (anticipación) y B (confianza) de la mejora 01, «Antes de que cierre tu reembolso».

Los criterios están en docs/plan/mejoras/01-antes-del-reembolso.md y se commitearon antes de
correr esto (7b0ba52). Aquí solo se mide y se compara contra ellos; los números de
CRITERIOS son los de la ficha, no se ajustan.

Uso, desde backend/:
    python analisis/antes_del_reembolso.py > ../docs/evidencia/antes-del-reembolso.txt
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# Corre desde analisis/: la raíz (despliegue) y modelado/ (lo importa exploracion) no están en sys.path.
sys.path[:0] = [str(RAIZ), str(RAIZ / "analisis"), str(RAIZ / "modelado")]

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from despliegue.utilidades import descargar_verificado  # noqa: E402
from exploracion import cargar_release, senal  # noqa: E402
from motivos import PALABRAS_CLAVE_POR_CATEGORIA, tabla_de_motivos  # noqa: E402

COMMIT_DE_LOS_CRITERIOS = "7b0ba52"
SEMILLA = 42
# El orden fijo de las categorías: desempata el motivo principal y los dos principales.
CATEGORIAS = list(PALABRAS_CLAVE_POR_CATEGORIA)
RELEASES = {
    "data-v1": "2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7",  # los 83
    "data-v2": "9d5a54f6cbb5f361e397eb043989e592cbff1d553c57ef8a41aae41e2c763d72",  # los 40 externos
}
JUEGOS_NOMBRADOS = {1938010: "WILD HEARTS™", 1145360: "Hades", 1172470: "Apex Legends™"}

CRITERIOS = {
    "minimo_evaluable": 10,
    "a_evaluables_83": 20,
    "a_acierto_83": 0.70,
    "a_ventaja_83": 0.10,
    "a_evaluables_40": 8,
    "a_acierto_40": 0.60,
    "b_minimo_referencia": 30,
    "b_minimo_referencia_respaldo": 20,
    "b_referencias_minimas": 8,
    "b_rejilla": (5, 10, 15, 20, 25, 30),
    "b_estabilidad": 0.80,
    "b_n_maximo": 20,
    "b_juegos_minimos": 30,
    "replicas": 1000,
}
TAMANOS = [(10, 15, "10–15"), (16, 30, "16–30"), (31, None, "más de 30")]


def quejas_con_motivo(resenas: pd.DataFrame) -> pd.DataFrame:
    """Reseñas con señal que mencionan al menos una categoría: una columna booleana por
    categoría, más appid, fecha e id."""
    con_senal = resenas[senal(resenas)]
    motivos = tabla_de_motivos(con_senal["texto"])
    quejas = pd.concat([con_senal[["appid", "timestamp_created", "recommendationid"]], motivos], axis=1)
    return quejas[motivos.any(axis=1)].reset_index(drop=True)


def _orden(conteos: np.ndarray) -> np.ndarray:
    """Las categorías con al menos una mención, de más a menos mencionada; los empates se
    quedan en el orden fijo porque el ordenamiento es estable."""
    mencionadas = np.flatnonzero(conteos > 0)
    return mencionadas[np.argsort(-conteos[mencionadas], kind="stable")]


def motivo_principal(conteos: np.ndarray) -> str:
    return CATEGORIAS[_orden(conteos)[0]]


def dos_principales(conteos: np.ndarray) -> list[str]:
    return [CATEGORIAS[i] for i in _orden(conteos)[:2]]


def mitades_por_fecha(quejas_juego: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordenadas = quejas_juego.sort_values(["timestamp_created", "recommendationid"])
    mitad = len(ordenadas) // 2
    return ordenadas.iloc[:mitad], ordenadas.iloc[mitad:]


def _conteos(quejas: pd.DataFrame) -> np.ndarray:
    return quejas[CATEGORIAS].to_numpy().sum(axis=0)


def prueba_anticipacion(quejas: pd.DataFrame, linea_base: str | None = None) -> tuple[pd.DataFrame, str]:
    """Por juego evaluable: el motivo principal de la mitad vieja, los dos principales de la
    nueva y si acierta. Sin `linea_base`, el motivo de la base sale de las mitades viejas
    juntas de estos juegos."""
    filas, viejas = [], []
    for appid, del_juego in quejas.groupby("appid"):
        if len(del_juego) < CRITERIOS["minimo_evaluable"]:
            continue
        vieja, nueva = mitades_por_fecha(del_juego)
        viejas.append(vieja)
        filas.append({"appid": appid, "quejas": len(del_juego), "principal vieja": motivo_principal(_conteos(vieja)),
                      "dos principales nueva": dos_principales(_conteos(nueva))})
    tabla = pd.DataFrame(filas)
    if linea_base is None:
        linea_base = motivo_principal(_conteos(pd.concat(viejas)))
    tabla["acierto propio"] = [p in dos for p, dos in zip(tabla["principal vieja"], tabla["dos principales nueva"])]
    tabla["acierto base"] = [linea_base in dos for dos in tabla["dos principales nueva"]]
    return tabla, linea_base


def ventaja_con_intervalo(tabla: pd.DataFrame) -> tuple[float, float, float]:
    """Acierto propio − acierto de la base, con IC 95 % por bootstrap pareado sobre juegos."""
    propio = tabla["acierto propio"].to_numpy(dtype=float)
    base = tabla["acierto base"].to_numpy(dtype=float)
    generador = np.random.default_rng(SEMILLA)
    indices = generador.integers(0, len(tabla), size=(CRITERIOS["replicas"], len(tabla)))
    diferencias = propio[indices].mean(axis=1) - base[indices].mean(axis=1)
    return propio.mean() - base.mean(), *np.percentile(diferencias, [2.5, 97.5])


def por_tamano(tabla: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for desde, hasta, nombre in TAMANOS:
        grupo = tabla[(tabla["quejas"] >= desde) & ((tabla["quejas"] <= hasta) if hasta else True)]
        filas.append({"quejas con motivo": nombre, "juegos": len(grupo),
                      "acierto propio": grupo["acierto propio"].mean() if len(grupo) else np.nan,
                      "acierto base": grupo["acierto base"].mean() if len(grupo) else np.nan})
    return pd.DataFrame(filas).set_index("quejas con motivo")


def estabilidad(matriz: np.ndarray, k: int, generador: np.random.Generator) -> float:
    """% de réplicas de k quejas (con reemplazo) cuyo motivo principal es el del juego completo.
    argmax toma el primero de los empatados: el mismo orden fijo."""
    principal = int(np.argmax(matriz.sum(axis=0)))
    indices = generador.integers(0, len(matriz), size=(CRITERIOS["replicas"], k))
    conteos = matriz[indices].sum(axis=1)
    return float((np.argmax(conteos, axis=1) == principal).mean())


def prueba_confianza(quejas: pd.DataFrame) -> dict:
    """N: el menor k con estabilidad mediana ≥ 80 % en los juegos de referencia."""
    por_juego = {appid: g[CATEGORIAS].to_numpy(dtype=int) for appid, g in quejas.groupby("appid")}
    minimo, rejilla = CRITERIOS["b_minimo_referencia"], CRITERIOS["b_rejilla"]
    referencia = sorted(a for a, m in por_juego.items() if len(m) >= minimo)
    if len(referencia) < CRITERIOS["b_referencias_minimas"]:
        minimo = CRITERIOS["b_minimo_referencia_respaldo"]
        rejilla = tuple(k for k in rejilla if k <= minimo)
        referencia = sorted(a for a, m in por_juego.items() if len(m) >= minimo)
    generador = np.random.default_rng(SEMILLA)
    curva = pd.DataFrame({k: [estabilidad(por_juego[a], k, generador) for a in referencia] for k in rejilla},
                         index=pd.Index(referencia, name="appid"))
    medianas = curva.median()
    alcanzan = medianas[medianas >= CRITERIOS["b_estabilidad"]]
    return {"minimo de referencia": minimo, "referencia": referencia, "curva": curva, "medianas": medianas,
            "N": int(alcanzan.index[0]) if len(alcanzan) else None}


def main() -> int:
    # Rutas relativas a backend/: así la evidencia no lleva rutas de una máquina.
    os.chdir(RAIZ)
    destino = Path("extracto") / "antes_del_reembolso"
    rutas = {ref: descargar_verificado(ref, sha, destino / f"nexplay_{ref}.db") for ref, sha in RELEASES.items()}
    juegos_v1, resenas_v1 = cargar_release(rutas["data-v1"])
    juegos_v2, resenas_v2 = cargar_release(rutas["data-v2"])
    externos = sorted(set(juegos_v2["appid"]) - set(juegos_v1["appid"]))
    assert not set(externos) & set(juegos_v1["appid"])
    quejas_83 = quejas_con_motivo(resenas_v1)
    quejas_40 = quejas_con_motivo(resenas_v2[resenas_v2["appid"].isin(externos)])
    nombres = pd.concat([juegos_v1, juegos_v2]).drop_duplicates("appid").set_index("appid")["nombre"]
    pd.set_option("display.width", 160)

    print(f"Mejora 01 · pruebas A y B. Criterios fijados en el commit {COMMIT_DE_LOS_CRITERIOS}.")
    print(f"data-v1: {len(juegos_v1)} juegos, {len(quejas_83):,} quejas con motivo | "
          f"externos (data-v2): {len(externos)} juegos, {len(quejas_40):,} quejas con motivo\n")

    # --- A en los 83 ------------------------------------------------------------------------
    tabla_83, base = prueba_anticipacion(quejas_83)
    ventaja, ic_bajo, ic_alto = ventaja_con_intervalo(tabla_83)
    propio_83, base_83 = tabla_83["acierto propio"].mean(), tabla_83["acierto base"].mean()
    a1 = len(tabla_83) >= CRITERIOS["a_evaluables_83"]
    a2 = propio_83 >= CRITERIOS["a_acierto_83"]
    a3 = ventaja >= CRITERIOS["a_ventaja_83"]
    a4 = ic_bajo > 0
    print("A · anticipación, 83 juegos (data-v1)")
    print(f"  motivo de la línea base (mitades viejas juntas): {base}")
    print(f"  1. juegos evaluables (≥ {CRITERIOS['minimo_evaluable']} quejas): {len(tabla_83)}  "
          f"(pide ≥ {CRITERIOS['a_evaluables_83']}) → {'cumple' if a1 else 'NO cumple'}")
    print(f"  2. acierto propio: {propio_83:.1%}  (pide ≥ {CRITERIOS['a_acierto_83']:.0%}) → {'cumple' if a2 else 'NO cumple'}")
    print(f"     acierto de la base: {base_83:.1%}")
    print(f"  3. ventaja sobre la base: {100 * ventaja:+.1f} puntos  (pide ≥ {100 * CRITERIOS['a_ventaja_83']:.0f}) → "
          f"{'cumple' if a3 else 'NO cumple'}")
    print(f"  4. IC 95 % de la ventaja: [{100 * ic_bajo:+.1f}, {100 * ic_alto:+.1f}] puntos  (pide > 0) → "
          f"{'cumple' if a4 else 'NO cumple'}")
    a_83 = "no concluyente" if not a1 else ("PASA" if a2 and a3 and a4 else "NO PASA")
    print(f"  A en los 83: {a_83}\n")
    print("  por tamaño del juego (no es criterio):")
    print(por_tamano(tabla_83).to_string(float_format=lambda x: f"{x:.1%}"), "\n")

    # --- A en los 40 ------------------------------------------------------------------------
    tabla_40, _ = prueba_anticipacion(quejas_40, linea_base=base)
    print("A · confirmación en los 40 externos (data-v2), misma línea base")
    if len(tabla_40) < CRITERIOS["a_evaluables_40"]:
        a_40 = "no alcanza a concluir"
        print(f"  juegos evaluables: {len(tabla_40)} (pide ≥ {CRITERIOS['a_evaluables_40']}) → {a_40}")
    else:
        propio_40, base_40 = tabla_40["acierto propio"].mean(), tabla_40["acierto base"].mean()
        confirma = propio_40 >= CRITERIOS["a_acierto_40"] and propio_40 >= base_40
        a_40 = "CONFIRMA" if confirma else "NO CONFIRMA"
        print(f"  juegos evaluables: {len(tabla_40)} | acierto propio: {propio_40:.1%} (pide ≥ {CRITERIOS['a_acierto_40']:.0%}) | "
              f"acierto de la base: {base_40:.1%} (el propio debe ser ≥) → {a_40}")
    if len(tabla_40):
        print("  por tamaño del juego (no es criterio):")
        print(por_tamano(tabla_40).to_string(float_format=lambda x: f"{x:.1%}"))
    print()

    # --- B ----------------------------------------------------------------------------------
    confianza = prueba_confianza(quejas_83)
    print("B · confianza, juegos de referencia de los 83")
    print(f"  referencia: {len(confianza['referencia'])} juegos con ≥ {confianza['minimo de referencia']} quejas con motivo")
    cuartiles = confianza["curva"].quantile([0.25, 0.5, 0.75]).T
    cuartiles.columns = ["p25", "mediana", "p75"]
    print(cuartiles.rename_axis("k quejas").to_string(float_format=lambda x: f"{x:.1%}"))
    n = confianza["N"]
    quejas_por_juego = pd.concat([quejas_83, quejas_40]).groupby("appid").size()
    todos = pd.Index(sorted(set(juegos_v1["appid"]) | set(externos)))
    quejas_por_juego = quejas_por_juego.reindex(todos, fill_value=0)
    if n is None:
        b = "NO PASA"
        print(f"  ningún k de la rejilla llega a una estabilidad mediana de {CRITERIOS['b_estabilidad']:.0%} → {b}")
    else:
        llegan = quejas_por_juego >= n
        en_83 = int(llegan[llegan.index.isin(juegos_v1["appid"])].sum())
        en_40 = int(llegan[llegan.index.isin(externos)].sum())
        b = "PASA" if n <= CRITERIOS["b_n_maximo"] and llegan.sum() >= CRITERIOS["b_juegos_minimos"] else "NO PASA"
        print(f"  N = {n} quejas con motivo (pide ≤ {CRITERIOS['b_n_maximo']})")
        print(f"  juegos con ≥ N: {int(llegan.sum())} de {len(todos)} (83: {en_83}, 40: {en_40}; pide ≥ {CRITERIOS['b_juegos_minimos']}) → {b}")
    for appid, nombre in JUEGOS_NOMBRADOS.items():
        cuantas = int(quejas_por_juego.get(appid, 0))
        estado = "" if n is None else (" · llega a N" if cuantas >= n else " · no llega a N")
        print(f"    {nombre}: {cuantas} quejas con motivo{estado}")
    print()

    print("Resumen contra la regla de decisión (C la corre el equipo):")
    print(f"  A en los 83: {a_83} | A en los 40: {a_40} | B: {b} | C: pendiente")
    sigue = a_83 == "PASA" and b == "PASA" and a_40 != "NO CONFIRMA"
    print(f"  {'Sigue a C (maqueta y guion)' if sigue else 'No se construye: falla A o B, o los 40 no confirman'}"
          f"{' · «no confirmado en juegos externos»' if sigue and a_40 == 'no alcanza a concluir' else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
