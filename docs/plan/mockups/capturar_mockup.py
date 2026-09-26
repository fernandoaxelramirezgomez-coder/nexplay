"""Captura un mockup de docs/plan/mockups/ en las tres resoluciones y los dos temas.

Las capturas no se versionan (pesan decenas de MB): se regeneran con esto. El mockup se
mide a sí mismo —contraste de cada texto sobre la zona más clara de cada fondo y la letra
más chica— y aquí se imprime lo que midió, para no tener que abrir las imágenes para saber
si pasa.

Uso:
  python docs/plan/mockups/capturar_mockup.py                  # 6a-identidad.html
  python docs/plan/mockups/capturar_mockup.py otro-mockup.html
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
DESTINO = AQUI / "capturas"
RESOLUCIONES = ((1440, 900), (1024, 1366), (390, 844))


def capturar(nombre: str) -> int:
    pagina_html = AQUI / nombre
    if not pagina_html.exists():
        print(f"no existe {pagina_html}")
        return 1
    DESTINO.mkdir(exist_ok=True)
    base = pagina_html.stem.split("-")[0]
    problemas = 0
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for ancho, alto in RESOLUCIONES:
            for tema in ("oscuro", "claro"):
                contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
                pagina = contexto.new_page()
                pagina.goto(pagina_html.as_uri() + ("#claro" if tema == "claro" else ""), wait_until="networkidle")
                pagina.wait_for_function("document.documentElement.dataset.medido === 'si'")
                pagina.wait_for_timeout(600)
                desborde = pagina.evaluate(
                    "document.documentElement.scrollWidth - document.documentElement.clientWidth"
                )
                ruta = DESTINO / f"{base}-{tema}-{ancho}.png"
                pagina.screenshot(path=ruta, full_page=True)
                fallos = pagina.eval_on_selector_all("td.falla", "celdas => celdas.length")
                minima = pagina.inner_text("#letra-minima")
                print(f"{ancho:>5} {tema:7} desborde {desborde} px · {fallos} contrastes que no pasan · {ruta.name}")
                if ancho == RESOLUCIONES[0][0]:
                    print(f"        {minima}")
                problemas += fallos + (1 if desborde else 0)
                contexto.close()
        navegador.close()
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(capturar(sys.argv[1] if len(sys.argv) > 1 else "6a-identidad.html"))
