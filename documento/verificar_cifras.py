"""Comprueba que cada cifra del documento sea la canónica y que ninguna se escriba a mano.

La lista canónica vive solo aquí. Es la sección 4 del Prompt Maestro v2 con las correcciones
acordadas el 2026-09-30:
- idioma 98.7 %, no 99.3 %;
- cobertura de motivos 34.0 % de 2,706 negativas tempranas del conjunto limpio, no 33.9 %;
- el catálogo servido es data-v3 (las mismas 123 y 184,367 de data-v2);
- el IC externo sale de docs/evidencia/bootstrap-prueba-externa.json;
- veteranos contra novatos, con la definición prerregistrada sobre data-v1: la cifra anterior
  se retiró.
Y del 2026-10-01:
- el extremo superior del IC de «tiene nota» es −0.55 (vale −0.554932); el −0.56 anterior
  redondeaba dos veces el −0.555 que muestra el notebook;
- la razón de Mantel-Haenszel va con un decimal (2.6), como todo cociente; sus extremos, con dos;
- con el documento de 9 secciones, la lista solo guarda las cifras que el texto usa.
Y del 2026-10-02:
- todo PR-AUC con tres cifras significativas, y su desviación, su intervalo o su diferencia con los
  decimales de su estimación (el fold 1 pasa de 0.1459 a 0.146);
- el tag y el commit del código no son cifras canónicas: se comprueban contra los notebooks y git;
- la Parte A (docs/evidencia/modelos-texto.json y el notebook 02) y la lectura para negocio del 01;
- en 7.6, la tabla de bandas OOF del 01 reemplaza las tasas por banda y cobertura de crítica;
- el anexo cita la corrida de los tres notebooks en Colab con codigo-v6 (2026-10-02);
- 8.2 cita la prueba local del camino con IA, verificar_nia.py --openai del 2026-10-02 sobre codigo-v7.

Falla (exit 1) si:
- una macro de tables/cifras.tex no coincide con su valor canónico;
- se genera una macro que no está en la lista;
- una canónica no se usa en main.tex ni en sections/, o el texto usa una que no se generó;
- un PR-AUC no tiene tres cifras significativas, o su desviación o intervalo no lleva sus decimales;
- la macro TagCodigo no es el CODIGO_REF de los notebooks, o CommitCodigo no es su commit;
- una sección trae un número con decimales o con % fuera de una macro. Las referencias a una
  sección de un notebook («notebook 00, §3.4») y las medidas de diseño («0.49\textwidth») no
  cuentan: no son cifras.

Uso:
  .venv/bin/python documento/verificar_cifras.py
"""

import re
import subprocess
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
    "JuegosExternos": "40",
    # modelo: GroupKFold de 5 por appid sobre data-v1
    "PRAUCModelo": "0.0694",
    "PRAUCModeloStd": "0.0415",
    "PRAUCTrivial": "0.0219",
    # Los cocientes contra el trivial van con un decimal: la variación entre folds no justifica centésimas.
    "PRAUCCociente": "3.2",
    "PliegosGanados": "5",
    "Pliegues": "5",
    "PercentilMedio": "33.3",
    "PercentilAlto": "66.7",
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
    # periodo y calidad (§5), contrastadas con el 00 §1 y §3.1
    "DesdeJulioEntrenamientoPorResena": "96.1" + PORCIENTO,
    "ResenaMasAntiguaEntrenamiento": "8 de abril de 2023",
    "DescargaHastaEntrenamiento": "14 de septiembre de 2026",
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
    "PositivasPorMinutoAntesDelUmbral": "17.4",
    "PositivasPorMinutoDespuesDelUmbral": "18.6",
    # del 00: se generan con las secciones 6 a 8
    "IdiomaInglesPorResena": "98.7" + PORCIENTO,
    "NegativasTempranasLimpias": "2,706",
    "CoberturaMotivosPorResena": "34.0" + PORCIENTO,
    "SpearmanUmbralMin": "0.96",
    "SpearmanUmbralMax": "0.99",
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
    "GratisExternos": "5",
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
    "PRAUCCompleto": "0.0849",
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
    # bootstrap-prueba-externa.json y README.md (casos al filo).
    "CocienteFoldMin": "1.8",
    "CocienteFoldMax": "5.8",
    "ExternoReplicas": "2,000",
    "AltoSinNotaCatalogo": "33",
    # lectura para negocio del 01 (7.1, 7.5 y 7.6), contrastadas con sus salidas guardadas en codigo-v6:
    # «fold 1: 0.1459 · media de los otros cuatro: 0.0503 · el fold 1 es el 42% de la suma» y la tabla de
    # bandas con 6.29× y 1.93×. Las «veces el trivial» (3.1704 y 3.2380) las comprueba el generador en la tabla 9.
    "PRAUCFoldUno": "0.146",
    "PRAUCOtrosFolds": "0.0503",
    "FoldUnoParteDeLaSuma": "42" + PORCIENTO,
    "BajoOOF": "27",
    "MedioOOF": "27",
    "AltoOOF": "29",
    "AltoSobreBajoOOF": "6.3",
    "AltoSobreBajoExternos": "1.9",
    # Parte A (7.9), contrastadas con docs/evidencia/modelos-texto.json y con las salidas guardadas del 02
    # en codigo-v6 (tabla_top_k: 0.430 y 2.676; cobertura_del_sitio: 35 de 40).
    "NegativasTexto": "16,836",
    "TempranasTexto": "2,670",
    "PrevalenciaTextoPorResena": "15.86" + PORCIENTO,
    "DuracionesEnmascaradas": "2,442",
    "PrerregistroTexto": "6bbcea6",
    "CodigoTexto": "59694a6",
    "PRAUCTextoTrivial": "0.161",
    "PRAUCTextoRefund": "0.185",
    "PRAUCTextoNB": "0.226",
    "PRAUCTextoMiniLM": "0.323",
    "PRAUCTextoLR": "0.369",
    "PRAUCTextoLRICInf": "0.288",
    "PRAUCTextoLRICSup": "0.421",
    "CocienteTextoLR": "2.3",
    "CocienteTextoLRICInf": "2.05",
    "CocienteTextoLRICSup": "2.53",
    "DiferenciaTextoLRRefund": "0.184",
    "DiferenciaTextoLRRefundICInf": "0.137",
    "DiferenciaTextoLRRefundICSup": "0.205",
    "RamaTexto": "3",
    "TopDiezTempranasPorResena": "43.0" + PORCIENTO,
    "TopDiezVeces": "2.7",
    "PalabrasTopTemprana": "40",
    "PalabrasSinCategoria": "35",
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
    "Endpoints": "19",
    "EndpointsRiesgo": "5",
    "EndpointsComunidad": "8",
    "EndpointsNia": "5",
    "EndpointsSistema": "1",
    # planteamiento y estrategia (secciones 2 y 3): docs/evidencia/senal-por-biblioteca.md, las capturas del
    # recorrido (los mismos precios, notas y motivos) y frontend/src/styles/base.css
    "UmbralVeterano": "20",
    "NovatosPorResena": "0.67" + PORCIENTO,
    "VeteranosPorResena": "2.89" + PORCIENTO,
    "NovatosPromJuegos": "0.97" + PORCIENTO,
    "VeteranosPromJuegos": "2.72" + PORCIENTO,
    "RazonMH": "2.6",
    "RazonMHICInf": "1.84",
    "RazonMHICSup": "4.12",
    "PaydayMetacritic": "66",
    "PaydayPrecio": "344.00",
    "PaydayFechaPrecio": "14 de septiembre de 2026",
    "PaydayCasos": "113",
    "PaydayClasificadas": "33",
    "PaydayMotivoPrincipal": "48" + PORCIENTO,
    "DeadSpaceMetacritic": "87",
    "DeadSpacePrecio": "349.75",
    "DeadSpaceFechaPrecio": "21 de septiembre de 2026",
    "DeadSpaceCasos": "80",
    "DeadSpaceClasificadas": "45",
    "DeadSpaceMotivoPrincipal": "71" + PORCIENTO,
    "DeadSpacePrecioInicial": "1,399.00",
    "DeadSpaceDescuento": "75" + PORCIENTO,
    "EstanteAccionBajo": "25",
    "ObjetivoTactil": "44",
    # resolución (sección 8): backend/api/nia/herramientas.py, backend/calidad/ y docs/evidencia/nia-pruebas.md
    "NiaHerramientas": "5",
    "PreguntasNia": "25",
    "PreguntasNiaAprobadas": "25",
    "PreguntasTrampa": "48",
    "TrampasPorRevisar": "0",
    "FechaCorridaTrampas": "30 de septiembre de 2026",
    "CommitTrampas": "c5478f6",
    # docs/evidencia/verificar-nia-openai-2026-10-02.txt: la prueba local del camino con IA
    "FechaCorridaNiaIA": "2 de octubre de 2026",
    # docs/evidencia/verificar-nia-openai-2026-10-03.txt: la misma prueba sobre el Nia de producción, posterior al tag
    "FechaCorridaNiaProduccion": "3 de octubre de 2026",
    "CommitNiaProduccion": "334fc71",
    # contexto de mercado (sección 2): docs/evidencia/contexto-mercado.json, con la cita textual de cada fuente,
    # verificadas el 2026-10-02 (GamingOnLinux con datos de SteamDB; Alinea Analytics)
    "LanzamientosSteam": "19,008",
    "LanzamientosPocasResenas": "9,269",
    "FechaCorteLanzamientos": "12 de diciembre de 2025",
    "IngresosSteam": "17.7 mil millones",
    "FechaCorteIngresos": "19 de diciembre de 2025",
    # datos (4.4): backend/analisis/diccionario.py, COLUMNAS
    "ColumnasDiccionario": "41",
    # anexo: docs/evidencia/colab/, la corrida de los tres con codigo-v8, el tag de entrega (README y las tres descargas)
    "FechaColab": "2 de octubre de 2026",
    "CeldasCero": "69 de 69",
    "CeldasUno": "28 de 28",
    "CeldasDos": "24 de 24",
    "TiempoCero": "184",
    "TiempoUno": "28",
    "TiempoDos": "378",
    "VersionPythonColab": "3.13.15",
    "VersionNumpyColab": "2.1.3",
    "VersionPandasColab": "2.2.3",
}

_MACRO = re.compile(r"^\\newcommand\{\\cifra(?P<nombre>[A-Za-z]+)\}\{(?P<valor>.*)\}\s*(%.*)?$")
_COMENTARIO = re.compile(r"(?<!\\)%.*$")
# Un decimal, o un número seguido de % con o sin el espacio fino de LaTeX («100\,\%»).
# Un número seguido de una unidad de longitud («0.49\textwidth», «6.6cm») es diseño, no una cifra.
_NUMERO_SUELTO = re.compile(r"(?<![\w\\.])\d+[.,]\d+(?![\d.,])(?!\s*(?:cm|mm|pt|em|ex|in|\\textwidth|\\linewidth|\\textheight)\b)"
                            r"|\d+(?:\s|\\,)*\\%")
_SECCION_DE_NOTEBOOK = re.compile(r"notebook[ ~]0[01],?[ ~]*§\d+(?:\.\d+)*")
_USO = re.compile(r"\\cifra([A-Za-z]+)")
# Se comprueban contra los notebooks y git, no contra un valor fijo: siguen al tag de entrega.
IDENTIFICADORES = ("TagCodigo", "CommitCodigo")
# Diferencias de PR-AUC que llevan los decimales de su estimación.
DIFERENCIAS = {"DiferenciaCompraJuego": "PRAUCModelo", "DiferenciaTextoLRRefund": "PRAUCTextoLR",
               "DiferenciaTextoLRRefundICInf": "PRAUCTextoLR", "DiferenciaTextoLRRefundICSup": "PRAUCTextoLR"}


def macros_generadas() -> dict[str, str]:
    ruta = DOCUMENTO / "tables" / "cifras.tex"
    if not ruta.exists():
        sys.exit("falta tables/cifras.tex: corre primero documento/generar_figuras.py")
    return {m["nombre"]: m["valor"] for m in map(_MACRO.match, ruta.read_text(encoding="utf-8").splitlines()) if m}


def numeros_sueltos() -> list[str]:
    hallazgos = []
    for ruta in sorted((DOCUMENTO / "sections").glob("*.tex")):
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            sin_comentario = _SECCION_DE_NOTEBOOK.sub("", _COMENTARIO.sub("", linea))
            for m in _NUMERO_SUELTO.finditer(sin_comentario):
                hallazgos.append(f"{ruta.name}:{n}: «{m.group(0)}» escrito a mano")
    return hallazgos


def macros_usadas() -> set[str]:
    fuentes = [DOCUMENTO / "main.tex", *sorted((DOCUMENTO / "sections").glob("*.tex"))]
    return {n for ruta in fuentes for linea in ruta.read_text(encoding="utf-8").splitlines()
            for n in _USO.findall(_COMENTARIO.sub("", linea))}


def decimales(valor: str) -> int:
    return len(valor.split(".")[1]) if "." in valor else 0


def pr_auc_fuera_de_regla(generadas: dict[str, str]) -> list[str]:
    """Todo PR-AUC con tres cifras significativas; su desviación, intervalo o diferencia, con sus decimales."""
    fallas = []
    for nombre, valor in generadas.items():
        es_pr_auc = nombre.startswith("PRAUC") and "Cociente" not in nombre  # un cociente lleva un decimal
        base = DIFERENCIAS.get(nombre) or (re.sub(r"(Std|ICInf|ICSup)$", "", nombre) if es_pr_auc else None)
        if base is None:
            continue
        if base != nombre:
            if base in generadas and decimales(valor) != decimales(generadas[base]):
                fallas.append(f"\\cifra{nombre} = «{valor}» no lleva los decimales de \\cifra{base} = «{generadas[base]}»")
        elif len(valor.replace(".", "").lstrip("0")) != 3:
            fallas.append(f"\\cifra{nombre} = «{valor}» no tiene tres cifras significativas")
    return fallas


def identificadores_incorrectos(generadas: dict[str, str]) -> list[str]:
    raiz = DOCUMENTO.parent
    tags = {re.search(r'CODIGO_REF = \\"([^"\\]+)\\"', ruta.read_text(encoding="utf-8"))[1]
            for ruta in sorted((raiz / "notebooks").glob("0*.ipynb"))}
    tag = generadas.get("TagCodigo")
    fallas = [] if tags == {tag} else [f"\\cifraTagCodigo = «{tag}», pero los notebooks clonan {sorted(tags)}"]
    commit = subprocess.run(["git", "rev-parse", "--short", f"{tag}^{{commit}}"], cwd=raiz, capture_output=True, text=True)
    if commit.returncode != 0 or commit.stdout.strip() != generadas.get("CommitCodigo"):
        fallas.append(f"\\cifraCommitCodigo = «{generadas.get('CommitCodigo')}» no es el commit de {tag}")
    return fallas


def main() -> int:
    generadas = macros_generadas()
    usadas = macros_usadas()
    fallas = [f"\\cifra{n}: generada «{v}», canónica «{CANONICAS[n]}»"
              for n, v in generadas.items() if n in CANONICAS and v != CANONICAS[n]]
    fallas += [f"\\cifra{n} = «{v}» no está en la lista canónica" for n, v in generadas.items()
               if n not in CANONICAS and n not in IDENTIFICADORES]
    fallas += pr_auc_fuera_de_regla(generadas)
    fallas += identificadores_incorrectos(generadas)
    fallas += [f"\\cifra{n} es canónica pero el texto no la usa: sale de la lista" for n in CANONICAS if n not in usadas]
    fallas += [f"\\cifra{n} se usa en el texto pero no se generó" for n in sorted(usadas - set(generadas))]
    fallas += numeros_sueltos()

    coinciden = sum(1 for n, v in generadas.items() if CANONICAS.get(n) == v)
    print(f"{len(generadas)} cifras generadas; {coinciden} coinciden con la lista canónica; {len(usadas)} usadas en el texto")
    for falla in fallas:
        print("FALLA", falla)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
