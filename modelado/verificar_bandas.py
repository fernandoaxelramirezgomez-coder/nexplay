"""Compara la banda de riesgo de cada juego del catálogo contra una referencia
versionada (docs/bandas_referencia.json).

Sirve para detectar que un reentrenamiento (por ejemplo, el del build de Docker
con preparar_entorno.py) clasifica distinto de lo validado. Las bandas salen del
mismo camino que sirve la API: api/catalogo.py puntúa cada juego con su perfil
neutro vía scoring.predecir().

Solo se comparan las bandas: entrenar_modelo.py pone la fecha del día en
modelo_version, así que un modelo reentrenado nunca coincide ni en versión ni en
hash con el de la referencia.

Uso:
  python verificar_bandas.py              compara; sale con 1 si algo difiere
  python verificar_bandas.py --generar    reescribe la referencia con el modelo actual
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Corre desde modelado/, así que la raíz no está en sys.path y `api` no se encontraría.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import catalogo, scoring  # noqa: E402

_RAIZ = Path(__file__).resolve().parents[1]
_REFERENCIA = _RAIZ / "docs" / "bandas_referencia.json"


def _catalogo_actual() -> dict[str, dict]:
    return {
        str(j.appid): {"nombre": j.nombre, "banda": j.banda_riesgo.value, "riesgo": j.riesgo}
        for j in catalogo.buscar()
    }


def _distancia_al_umbral(riesgo: float) -> str:
    umbrales = {"bajo/medio": scoring._UMBRAL_MEDIO, "medio/alto": scoring._UMBRAL_ALTO}
    corte, umbral = min(umbrales.items(), key=lambda par: abs(riesgo - par[1]))
    return f"a {abs(riesgo - umbral):.1e} del corte {corte} ({umbral:.6f})"


def generar(ruta: Path) -> int:
    actual = _catalogo_actual()
    if not actual:
        print("el catálogo está vacío: no se genera la referencia")
        return 1
    referencia = {
        "generado": date.today().isoformat(),
        "modelo_version": scoring._VERSION_MODELO,
        "umbrales": {"medio": scoring._UMBRAL_MEDIO, "alto": scoring._UMBRAL_ALTO},
        "perfil": "neutro (api/catalogo.py, _PERFIL_NEUTRO)",
        "nota": "solo 'bandas' se compara; lo demás es trazabilidad",
        "bandas": {
            appid: {"nombre": j["nombre"], "banda": j["banda"]}
            for appid, j in sorted(actual.items(), key=lambda par: int(par[0]))
        },
    }
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(referencia, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    conteo = {b: sum(j["banda"] == b for j in actual.values()) for b in ("bajo", "medio", "alto")}
    print(f"referencia escrita en {ruta}: {len(actual)} juegos, bajo/medio/alto = "
          f"{conteo['bajo']}/{conteo['medio']}/{conteo['alto']} (modelo {scoring._VERSION_MODELO})")
    return 0


def comparar(ruta: Path) -> int:
    referencia = json.loads(ruta.read_text(encoding="utf-8"))["bandas"]
    actual = _catalogo_actual()

    problemas = []
    if len(actual) != len(referencia):
        problemas.append(f"el catálogo tiene {len(actual)} juegos y la referencia {len(referencia)}")
    for appid in sorted(referencia.keys() - actual.keys(), key=int):
        problemas.append(f"falta {appid} ({referencia[appid]['nombre']}): está en la referencia y no en el catálogo")
    for appid in sorted(actual.keys() - referencia.keys(), key=int):
        problemas.append(f"sobra {appid} ({actual[appid]['nombre']}): está en el catálogo y no en la referencia")
    for appid in sorted(referencia.keys() & actual.keys(), key=int):
        ref, act = referencia[appid]["banda"], actual[appid]["banda"]
        if ref != act:
            problemas.append(
                f"{actual[appid]['nombre']} ({appid}): {ref} -> {act}; "
                f"score {actual[appid]['riesgo']:.4f}, {_distancia_al_umbral(actual[appid]['riesgo'])}"
            )

    if problemas:
        print(f"BANDAS DISTINTAS de la referencia {ruta.name} (modelo actual {scoring._VERSION_MODELO}):")
        for problema in problemas:
            print(f"  - {problema}")
        return 1
    print(f"bandas idénticas a la referencia: {len(actual)} juegos (modelo actual {scoring._VERSION_MODELO})")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verifica las bandas del catálogo contra la referencia versionada")
    parser.add_argument("--generar", action="store_true", help="reescribe la referencia con el modelo actual")
    parser.add_argument("--referencia", type=Path, default=_REFERENCIA, help="ruta del JSON (por defecto %(default)s)")
    args = parser.parse_args()
    sys.exit(generar(args.referencia) if args.generar else comparar(args.referencia))
