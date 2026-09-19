"""Captura la UI de NexPlay con Chromium headless, para revisar los cambios
visuales sin abrir un navegador a mano.

Guarda en docs/capturas/ (ignorada por git; la captura del README es otra,
docs/captura-interfaz.png, y este script no la toca):
  catalogo.png             catálogo completo
  ficha-wild-hearts.png    ficha de Wild Hearts tras "Ver segunda opinión"

Requiere la API y la UI corriendo (uvicorn api.main:app / python ui/app.py).
Una sola vez:
  pip install -r requirements-dev.txt
  playwright install chromium
  sudo playwright install-deps chromium   # librerías del sistema (Linux/WSL)

Uso:
  python scripts/capturar_ui.py [--url http://localhost:7860]
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Error as ErrorPlaywright
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as TiempoAgotado

_RAIZ = Path(__file__).resolve().parent.parent
_DESTINO = _RAIZ / "docs" / "capturas"

_APPID_FICHA = 1938010  # Wild Hearts
_VIEWPORT = {"width": 1440, "height": 900}
_TIMEOUT_MS = 60_000

# Las 83 tarjetas tienen el mismo botón: se ubica el de la tarjeta cuya portada
# es del appid buscado, subiendo hasta el contenedor más cercano que ya lo incluye.
_BOTON_OPINION = (
    "xpath=//img[contains(@src, '/apps/{appid}/')]"
    "/ancestor::div[.//button[normalize-space()='Ver segunda opinión']][1]"
    "//button[normalize-space()='Ver segunda opinión']"
)

_JS_CONTAR_FALLBACKS = """
selector => {
    const imgs = [...document.querySelectorAll(selector)].filter(i => i.offsetParent !== null);
    return [imgs.filter(i => i.src.startsWith('data:image/svg')).length, imgs.length];
}
"""


def _esperar_portadas(pagina: Page, selector: str) -> tuple[int, int]:
    """Devuelve (portadas que cayeron al SVG de respaldo, portadas visibles)."""
    pagina.wait_for_function(
        """selector => [...document.querySelectorAll(selector)]
            .filter(i => i.offsetParent !== null)
            .every(i => i.complete && i.naturalWidth > 0)""",
        arg=selector,
        timeout=_TIMEOUT_MS,
    )
    return pagina.evaluate(_JS_CONTAR_FALLBACKS, selector)


def _recorrer_pagina(pagina: Page) -> None:
    # Las portadas son loading='lazy' y una captura de página completa no
    # dispara la carga de las que están fuera de pantalla: hay que bajar.
    altura = pagina.evaluate("document.documentElement.scrollHeight")
    for y in range(0, altura, _VIEWPORT["height"] // 2):
        pagina.evaluate("y => window.scrollTo(0, y)", y)
        pagina.wait_for_timeout(120)
    pagina.evaluate("window.scrollTo(0, 0)")


def _capturar_catalogo(pagina: Page) -> None:
    try:
        pagina.locator(".nexplay-card-wrap").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        sys.exit("La UI cargó pero el catálogo está vacío: ¿está corriendo la API?")

    _recorrer_pagina(pagina)
    fallbacks, total = _esperar_portadas(pagina, ".nexplay-card-inner img")
    destino = _DESTINO / "catalogo.png"
    pagina.screenshot(path=destino, full_page=True)
    print(f"catálogo: {destino.relative_to(_RAIZ)} ({total} portadas, {fallbacks} con imagen de respaldo)")


def _capturar_ficha(pagina: Page) -> None:
    pagina.locator(_BOTON_OPINION.format(appid=_APPID_FICHA)).click()

    # .nexplay-ficha-nombre solo existe en la ficha real, no en el skeleton de
    # carga; "Segunda opinión" es lo último que llena _abrir_ficha().
    nombre = pagina.locator(".nexplay-ficha-nombre")
    nombre.wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_role("heading", name="Segunda opinión").wait_for(state="visible", timeout=_TIMEOUT_MS)
    fallbacks, _ = _esperar_portadas(pagina, "div:has(> .nexplay-ficha-nombre) img")

    pagina.wait_for_timeout(600)  # deja terminar el fade-in del panel (0.35 s)
    pagina.evaluate("window.scrollTo(0, 0)")
    destino = _DESTINO / "ficha-wild-hearts.png"
    pagina.screenshot(path=destino, full_page=True)
    print(f"ficha:    {destino.relative_to(_RAIZ)} ({nombre.inner_text()}, {fallbacks} con imagen de respaldo)")


def capturar(url: str) -> None:
    _DESTINO.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page(viewport=_VIEWPORT)
            try:
                pagina.goto(url, wait_until="domcontentloaded", timeout=15_000)
            except ErrorPlaywright as exc:
                sys.exit(
                    f"No pude abrir {url}: {exc.message.splitlines()[0]}\n"
                    "¿Están corriendo la API y la UI? (uvicorn api.main:app / python ui/app.py)"
                )
            _capturar_catalogo(pagina)
            _capturar_ficha(pagina)
        finally:
            navegador.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captura el catálogo y la ficha de la UI de NexPlay.")
    parser.add_argument("--url", default="http://localhost:7860", help="URL de la UI (por defecto %(default)s)")
    capturar(parser.parse_args().url)
