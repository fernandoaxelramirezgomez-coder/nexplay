"""Comprueba que cada cifra del documento sea la canónica y que ninguna se escriba a mano.

La lista canónica vive solo aquí. Es la sección 4 del Prompt Maestro v2 con las correcciones
acordadas el 2026-09-30:
- idioma 98.7 %, no 99.3 %;
- cobertura de motivos 34.0 % de 2,706 negativas tempranas del conjunto limpio, no 33.9 %;
- el catálogo servido es data-v3 (las mismas 123 y 184,367 de data-v2);
- el IC externo sale de docs/evidencia/bootstrap-prueba-externa.json;
- veteranos contra novatos, con la definición prerregistrada sobre data-v1: la cifra anterior
  se retiró.

Falla (exit 1) si:
- una macro de tables/cifras.tex no coincide con su valor canónico;
- se genera una macro que no está en la lista;
- una sección trae un número con decimales o con % fuera de una macro.

Las canónicas que todavía no se generan se listan como pendientes, sin fallar.

Uso:
  .venv/bin/python documento/verificar_cifras.py
"""

import re
import sys
from pathlib import Path

DOCUMENTO = Path(__file__).resolve().parent
PORCIENTO = "\\,\\%"

CANONICAS = {
    # datos: data-v1 (entrenamiento), data-v3 (catálogo servido) y los 40 externos
    "JuegosEntrenamiento": "83",
    "ResenasEntrenamiento": "123,972",
    "PositivosEntrenamiento": "2,714",
    "PrevalenciaEntrenamientoPorResena": "2.19" + PORCIENTO,
    "JuegosCatalogo": "123",
    "ResenasCatalogo": "184,367",
    "PositivosCatalogo": "4,126",
    "PrevalenciaCatalogoPorResena": "2.24" + PORCIENTO,
    "JuegosExternos": "40",
    "ResenasExternos": "60,395",
    "PositivosExternos": "1,412",
    "PrevalenciaExternosPorResena": "2.34" + PORCIENTO,
    # modelo: GroupKFold de 5 por appid sobre data-v1
    "PRAUCModelo": "0.0694",
    "PRAUCModeloStd": "0.0415",
    "PRAUCTrivial": "0.0219",
    "PRAUCTrivialStd": "0.0037",
    "PRAUCCociente": "3.17",
    "PliegosGanados": "5",
    "Pliegues": "5",
    "UmbralMedio": "0.2858",
    "UmbralAlto": "0.3916",
    "BajoEntrenamiento": "30",
    "MedioEntrenamiento": "23",
    "AltoEntrenamiento": "30",
    "BajoCatalogo": "43",
    "MedioCatalogo": "37",
    "AltoCatalogo": "43",
    # prueba externa
    "PRAUCExterno": "0.0356",
    "PRAUCExternoTrivial": "0.0234",
    "PRAUCExternoCociente": "1.52",
    "ExternoICInf": "1.03",
    "ExternoICSup": "2.33",
    "ExternoReplicasSinVentaja": "27",
    # veteranos contra novatos (data-v1, perfiles públicos)
    "NovatosPorResena": "0.67" + PORCIENTO,
    "VeteranosPorResena": "2.89" + PORCIENTO,
    "NovatosPromJuegos": "0.97" + PORCIENTO,
    "VeteranosPromJuegos": "2.72" + PORCIENTO,
    "RazonMH": "2.62",
    "RazonMHICInf": "1.84",
    "RazonMHICSup": "4.12",
    # del 00: se generan con las secciones 6 a 8
    "IdiomaInglesPorResena": "98.7" + PORCIENTO,
    "NegativasTempranasLimpias": "2,706",
    "CoberturaMotivosPorResena": "34.0" + PORCIENTO,
    "SpearmanUmbralMin": "0.96",
    "SpearmanUmbralMax": "0.99",
    "RefundTempranasPorResena": "9.5" + PORCIENTO,
    "RefundPositivasPorResena": "0.2" + PORCIENTO,
    "CoefTieneNotaICInf": "−1.04",
    "CoefTieneNotaICSup": "−0.56",
    "CoefNotaICInf": "−0.56",
    "CoefNotaICSup": "−0.07",
}

_MACRO = re.compile(r"^\\newcommand\{\\cifra(?P<nombre>[A-Za-z]+)\}\{(?P<valor>.*)\}\s*(%.*)?$")
_COMENTARIO = re.compile(r"(?<!\\)%.*$")
_NUMERO_SUELTO = re.compile(r"(?<![\w\\.])\d+[.,]\d+|\d+\s*\\%")


def macros_generadas() -> dict[str, str]:
    ruta = DOCUMENTO / "tables" / "cifras.tex"
    if not ruta.exists():
        sys.exit("falta tables/cifras.tex: corre primero documento/generar_figuras.py")
    return {m["nombre"]: m["valor"] for m in map(_MACRO.match, ruta.read_text(encoding="utf-8").splitlines()) if m}


def numeros_sueltos() -> list[str]:
    hallazgos = []
    for ruta in sorted((DOCUMENTO / "sections").glob("*.tex")):
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            sin_comentario = _COMENTARIO.sub("", linea)
            for m in _NUMERO_SUELTO.finditer(sin_comentario):
                hallazgos.append(f"{ruta.name}:{n}: «{m.group(0)}» escrito a mano")
    return hallazgos


def main() -> int:
    generadas = macros_generadas()
    fallas = [f"\\cifra{n}: generada «{v}», canónica «{CANONICAS[n]}»"
              for n, v in generadas.items() if n in CANONICAS and v != CANONICAS[n]]
    fallas += [f"\\cifra{n} = «{v}» no está en la lista canónica" for n, v in generadas.items() if n not in CANONICAS]
    fallas += numeros_sueltos()
    pendientes = [n for n in CANONICAS if n not in generadas]

    coinciden = sum(1 for n, v in generadas.items() if CANONICAS.get(n) == v)
    print(f"{len(generadas)} cifras generadas; {coinciden} coinciden con la lista canónica")
    if pendientes:
        print(f"pendientes de generar ({len(pendientes)}): {', '.join(pendientes)}")
    for falla in fallas:
        print("FALLA", falla)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
