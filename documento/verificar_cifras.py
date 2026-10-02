"""Comprueba que cada cifra del documento sea la canónica y que ninguna se escriba a mano.

La lista canónica vive solo aquí. Es la sección 4 del Prompt Maestro v2 con las correcciones
acordadas el 2026-09-30:
- idioma 98.7 %, no 99.3 %;
- cobertura de motivos 34.0 % de 2,706 negativas tempranas del conjunto limpio, no 33.9 %;
- el catálogo servido es data-v3 (las mismas 123 y 184,367 de data-v2);
- el IC externo sale de docs/evidencia/bootstrap-prueba-externa.json;
- veteranos contra novatos, con la definición prerregistrada sobre data-v1: la cifra anterior
  se retiró.
Y una del 2026-10-01: el extremo superior del IC de «tiene nota» es −0.55 (vale −0.554932); el
−0.56 anterior redondeaba dos veces el −0.555 que muestra el notebook.

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
    # Los cocientes contra el trivial van con un decimal: la variación entre folds no justifica centésimas.
    "PRAUCCociente": "3.2",
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
    "PRAUCExternoCociente": "1.5",
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
    # periodo y calidad (§5), contrastadas con el 00 §1 y §3.1
    "DesdeJulioEntrenamientoPorResena": "96.1" + PORCIENTO,
    "DesdeJulioCatalogoPorResena": "97.1" + PORCIENTO,
    "ResenaMasAntiguaEntrenamiento": "8 de abril de 2023",
    "ResenaMasRecienteEntrenamiento": "14 de septiembre de 2026",
    "ResenaMasAntiguaCatalogo": "8 de abril de 2023",
    "ResenaMasRecienteCatalogo": "21 de septiembre de 2026",
    "DescargaDesdeEntrenamiento": "14 de septiembre de 2026",
    "DescargaHastaEntrenamiento": "14 de septiembre de 2026",
    "DescargaDesdeCatalogo": "14 de septiembre de 2026",
    "DescargaHastaCatalogo": "21 de septiembre de 2026",
    "TopeIngesta": "1,500",
    "JuegosEnElTope": "81",
    "DiasCubiertosMin": "4",
    "DiasCubiertosMax": "1,252",
    "DiasCubiertosMediana": "64",
    "PrivadosEntrenamientoPorResena": "59.9" + PORCIENTO,
    "SinNotaEntrenamiento": "23",
    "PagoSinPrecioEntrenamiento": "2",
    "MetacriticVerificadoExternos": "40 de 40",
    # objetivo (§6), contrastadas con el 00 §3.3
    "ExactitudTrivialPorResena": "97.81" + PORCIENTO,
    "NegativasAntesDelUmbralPorResena": "15.6" + PORCIENTO,
    "PositivasAntesDelUmbralPorResena": "2.0" + PORCIENTO,
    "NegativasPorMinutoAntesDelUmbral": "11.9",
    "NegativasPorMinutoDespuesDelUmbral": "12.2",
    "NegativasPorMinutoAntesDeTresHoras": "9.9",
    "NegativasPorMinutoDesdeTresHoras": "12.4",
    "PositivasPorMinutoAntesDelUmbral": "17.4",
    "PositivasPorMinutoDespuesDelUmbral": "18.6",
    "PositivasPorMinutoAntesDeTresHoras": "17.6",
    "PositivasPorMinutoDesdeTresHoras": "81.7",
    "JuegosSaltoTresHoras": "81",
    # del 00: se generan con las secciones 6 a 8
    "IdiomaInglesPorResena": "98.7" + PORCIENTO,
    "NegativasTempranasLimpias": "2,706",
    "CoberturaMotivosPorResena": "34.0" + PORCIENTO,
    "SpearmanUmbralMin": "0.96",
    "SpearmanUmbralMax": "0.99",
    "RefundTempranasPorResena": "9.5" + PORCIENTO,
    "RefundPositivasPorResena": "0.2" + PORCIENTO,
    "CoefTieneNotaICInf": "−1.04",
    "CoefTieneNotaICSup": "−0.55",
    "CoefNotaICInf": "−0.56",
    "CoefNotaICSup": "−0.07",
    # exploración (§7), contrastadas con el 00 §3.2, §3.4, §3.6 y §3.7
    "TasaJuegoMinPorResena": "0.13" + PORCIENTO,
    "TasaJuegoMaxPorResena": "27.13" + PORCIENTO,
    "ResenasJuegoMin": "682",
    "NivelDeConfianza": "95" + PORCIENTO,
    "Sobredispersion": "107",
    "TasaConNotaMedianaJuegos": "0.73" + PORCIENTO,
    "TasaSinNotaMedianaJuegos": "2.13" + PORCIENTO,
    "SpearmanTieneNota": "−0.40",
    "SpearmanNota": "−0.42",
    "SpearmanPrecio": "0.18",
    "SpearmanPrecioP": "0.12",
    "GratisEntrenamiento": "2",
    "NegativasTardiasLimpias": "14,353",
    "PositivasLimpias": "105,885",
    "RefundTardiasPorResena": "2.9" + PORCIENTO,
    "PalabrasMedianaTempranas": "22",
    "PalabrasMedianaTardias": "27",
    "PalabrasMedianaPositivas": "8",
    "GratisExternos": "5",
    "SinNotaExternos": "10",
    "PrecioMedianoEntrenamiento": "400.00",
    "PrecioMedianoExternos": "269.99",
    "TasaEntrenamientoMedianaJuegos": "0.80" + PORCIENTO,
    "TasaExternosMedianaJuegos": "1.40" + PORCIENTO,
    "TasaEntrenamientoPromJuegos": "2.33" + PORCIENTO,
    "TasaExternosPromJuegos": "2.33" + PORCIENTO,
    # procesamiento (§8), contrastadas con el 00, celdas 36, 40 a 54 y 56
    "PalabrasDeUnaCopia": "8",
    "TextosEntreJuegos": "57",
    "CopiasEnFoldsDistintos": "52",
    "DuplicadosQuitados": "483",
    "VaciasQuitadas": "545",
    "ResenasLimpias": "122,944",
    "CortasPorResena": "22.7" + PORCIENTO,
    "OtroIdioma": "1,637",
    "PRAUCSinDuplicados": "0.0695",
    "PRAUCSinVacias": "0.0696",
    "PRAUCSinCortas": "0.0800",
    # modelación (§9), contrastadas con el 01 (celdas 31 a 35), el 00 (celdas 73, 74 y 90),
    # docs/evidencia/simulacion_123.txt y docs/evidencia/particion-alternativa.json. El conjunto
    # completo no tenía registro anterior: su cifra es la de evaluar_gkf con la partición congelada.
    "PRAUCCompra": "0.0709",
    "PRAUCCompraStd": "0.0270",
    "PRAUCCompleto": "0.0849",
    "PRAUCCompletoStd": "0.0207",
    "DiferenciaCompraJuego": "0.0015",
    "FoldsCompraGana": "3",
    "ParticionesCompraGana": "16",
    "ParticionesSimuladas": "30",
    "PRAUCKFold": "0.0799",
    "PRAUCKFoldStd": "0.0032",
    "ParticionesAleatorias": "20",
    "PRAUCParticionMin": "0.0477",
    "PRAUCParticionMax": "0.0873",
    "JuegosEmpatadosEnElTope": "73",
    "VersionSklearnColab": "1.6.1",
    "JuegosMismoFoldColab": "12",
    "PRAUCParticionAlternativa": "0.0692",
    "PRAUCParticionAlternativaStd": "0.0412",
    "PliegosGanadosAlternativa": "5",
    "CoefPrecioICInf": "−0.01",
    "CoefPrecioICSup": "0.94",
    "CoefDescuentoICInf": "−0.31",
    "CoefDescuentoICSup": "0.07",
    "CoefGratisICInf": "−0.12",
    "CoefGratisICSup": "0.79",
    "CoefPrecioReplicasPositivas": "96.6" + PORCIENTO,
    # evaluación (§10), contrastadas con el 01 (celda 31), docs/evidencia/metacritic-por-banda.md,
    # bootstrap-prueba-externa.json y README.md (casos al filo). Los promedios por juego no tenían
    # registro anterior: salen de las mismas tasas por juego de los releases.
    "PRAUCFoldMin": "0.0367",
    "PRAUCFoldMax": "0.1459",
    "CocienteFoldMin": "1.8",
    "CocienteFoldMax": "5.8",
    "ExternoReplicas": "2,000",
    "TasaBajoEntrenamientoPorResena": "0.66" + PORCIENTO,
    "TasaBajoEntrenamientoPromJuegos": "0.66" + PORCIENTO,
    "TasaAltoSinNotaEntrenamientoPorResena": "5.37" + PORCIENTO,
    "TasaAltoSinNotaEntrenamientoPromJuegos": "5.78" + PORCIENTO,
    "TasaBajoExternosPorResena": "1.86" + PORCIENTO,
    "TasaBajoExternosPromJuegos": "1.86" + PORCIENTO,
    "TasaMedioExternosPorResena": "1.63" + PORCIENTO,
    "TasaMedioExternosPromJuegos": "1.61" + PORCIENTO,
    "TasaAltoSinNotaExternosPorResena": "3.66" + PORCIENTO,
    "TasaAltoSinNotaExternosPromJuegos": "3.64" + PORCIENTO,
    "JuegosAltoConNota": "10",
    "AltoSinNotaCatalogo": "33",
    "ScoreHollowKnight": "0.2857",
    "ScoreWarframe": "0.3918",
    # interpretabilidad (§11), contrastadas con el 00 (celda 110), backend/api/scoring.py (UMBRAL_TIPICO,
    # UMBRAL_MIN_CASOS y la media 86.97 de su comentario) y el plan (nota promedio 85.5). El precio
    # mediano del catálogo no tenía registro anterior: se calcula como referencias_del_catalogo().
    "SinMotivoPorResena": "66.0" + PORCIENTO,
    "CategoriasMotivos": "6",
    "UmbralMinCasos": "5",
    "UmbralTipico": "0.10",
    "NotaPromedioCatalogo": "85.5",
    "PrecioMedianoCatalogo": "349.88",
    "MediaNotaModelo": "86.97",
    # arquitectura (§12): las rutas de backend/api/main.py, como en el plan (T11, 17 endpoints)
    "Endpoints": "17",
}

_MACRO = re.compile(r"^\\newcommand\{\\cifra(?P<nombre>[A-Za-z]+)\}\{(?P<valor>.*)\}\s*(%.*)?$")
_COMENTARIO = re.compile(r"(?<!\\)%.*$")
# Un decimal, o un número seguido de % con o sin el espacio fino de LaTeX («100\,\%»).
_NUMERO_SUELTO = re.compile(r"(?<![\w\\.])\d+[.,]\d+|\d+(?:\s|\\,)*\\%")


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
