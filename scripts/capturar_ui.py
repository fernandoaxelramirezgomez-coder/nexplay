"""Captura la UI de NexPlay con Chromium headless, para revisar los cambios
visuales sin abrir un navegador a mano.

--frontend gradio (por defecto, http://localhost:7860) guarda en docs/capturas/:
  catalogo.png             catálogo completo
  ficha-wild-hearts.png    ficha de Wild Hearts tras "Ver segunda opinión"

--frontend angular (http://localhost:4200) guarda en docs/capturas/angular/:
  shell.png                cabecera, navegación y estado del catálogo

docs/capturas/ está ignorada por git; la captura del README es otra,
docs/captura-interfaz.png, y este script no la toca. En ambos modos revisa que
no aparezca "abandono" ni un score de riesgo con decimales.

Requiere la API y la UI corriendo (uvicorn api.main:app, y python ui/app.py o
npx ng serve en frontend/). Una sola vez:
  pip install -r requirements-dev.txt
  playwright install chromium
  sudo playwright install-deps chromium   # librerías del sistema (Linux/WSL)

Uso:
  python scripts/capturar_ui.py [--frontend gradio|angular] [--url URL]
"""

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import Error as ErrorPlaywright
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as TiempoAgotado

_RAIZ = Path(__file__).resolve().parent.parent
_DESTINOS = {"gradio": _RAIZ / "docs" / "capturas", "angular": _RAIZ / "docs" / "capturas" / "angular"}
_URLS = {"gradio": "http://localhost:7860", "angular": "http://localhost:4200"}

_APPID_FICHA = 1938010  # Wild Hearts
_VIEWPORT = {"width": 1440, "height": 900}
_TIMEOUT_MS = 60_000

# Los scores del modelo son decimales como 0.7424: nunca deben verse en pantalla.
_SCORE_VISIBLE = re.compile(r"\b0[.,]\d{3,}\b")

# Las 83 tarjetas de Gradio tienen el mismo botón: se ubica el de la tarjeta cuya
# portada es del appid buscado, subiendo hasta el contenedor que ya lo incluye.
_BOTON_OPINION_GRADIO = (
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


def _esperar_quietud(pagina: Page) -> None:
    # Angular abre cada ruta con una transición de vista: sin esperar, la captura
    # sale a mitad del fundido y los colores se ven apagados.
    pagina.wait_for_function(
        "() => document.getAnimations().every(a => a.playState !== 'running' || a.effect?.getTiming().iterations === Infinity)",
        timeout=_TIMEOUT_MS,
    )


def _revisar_vocabulario(pagina: Page, donde: str) -> list[str]:
    texto = pagina.inner_text("body")
    problemas = []
    if "abandono" in texto.lower():
        problemas.append(f"{donde}: aparece 'abandono'")
    if scores := _SCORE_VISIBLE.findall(texto):
        problemas.append(f"{donde}: scores visibles {scores[:5]}")
    return problemas


def _abrir(pagina: Page, url: str) -> None:
    try:
        pagina.goto(url, wait_until="domcontentloaded", timeout=15_000)
    except ErrorPlaywright as exc:
        sys.exit(
            f"No pude abrir {url}: {exc.message.splitlines()[0]}\n"
            "¿Están corriendo la API y la UI? (uvicorn api.main:app / python ui/app.py / npx ng serve)"
        )


# --- Gradio ---------------------------------------------------------------


def _gradio_catalogo(pagina: Page, destino: Path) -> list[str]:
    try:
        pagina.locator(".nexplay-card-wrap").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        sys.exit("La UI cargó pero el catálogo está vacío: ¿está corriendo la API?")

    _recorrer_pagina(pagina)
    fallbacks, total = _esperar_portadas(pagina, ".nexplay-card-inner img")
    ruta = destino / "catalogo.png"
    pagina.screenshot(path=ruta, full_page=True)
    print(f"catálogo: {ruta.relative_to(_RAIZ)} ({total} portadas, {fallbacks} con imagen de respaldo)")
    return _revisar_vocabulario(pagina, "catálogo")


def _gradio_ficha(pagina: Page, destino: Path) -> list[str]:
    pagina.locator(_BOTON_OPINION_GRADIO.format(appid=_APPID_FICHA)).click()

    # .nexplay-ficha-nombre solo existe en la ficha real, no en el skeleton de
    # carga; "Segunda opinión" es lo último que llena _abrir_ficha().
    nombre = pagina.locator(".nexplay-ficha-nombre")
    nombre.wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_role("heading", name="Segunda opinión").wait_for(state="visible", timeout=_TIMEOUT_MS)
    fallbacks, _ = _esperar_portadas(pagina, "div:has(> .nexplay-ficha-nombre) img")

    pagina.wait_for_timeout(600)  # deja terminar el fade-in del panel (0.35 s)
    pagina.evaluate("window.scrollTo(0, 0)")
    ruta = destino / "ficha-wild-hearts.png"
    pagina.screenshot(path=ruta, full_page=True)
    print(f"ficha:    {ruta.relative_to(_RAIZ)} ({nombre.inner_text()}, {fallbacks} con imagen de respaldo)")
    return _revisar_vocabulario(pagina, "ficha")


def _capturar_gradio(pagina: Page, url: str, destino: Path) -> list[str]:
    _abrir(pagina, url)
    return _gradio_catalogo(pagina, destino) + _gradio_ficha(pagina, destino)


# --- Angular --------------------------------------------------------------


def _angular_shell(pagina: Page, url: str, destino: Path) -> list[str]:
    _abrir(pagina, url)
    pagina.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
    try:
        pagina.get_by_test_id("catalogo-conteo").wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        sys.exit("El shell cargó pero el catálogo no: ¿está corriendo la API en el puerto que espera environment.ts?")
    _esperar_quietud(pagina)
    ruta = destino / "shell.png"
    pagina.screenshot(path=ruta)
    print(f"shell:    {ruta.relative_to(_RAIZ)} ({pagina.get_by_test_id('catalogo-conteo').inner_text()})")
    return _revisar_vocabulario(pagina, "shell")


def _capturar_angular(pagina: Page, url: str, destino: Path) -> list[str]:
    return _angular_shell(pagina, url, destino)


def capturar(frontend: str, url: str) -> int:
    destino = _DESTINOS[frontend]
    destino.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page(viewport=_VIEWPORT)
            capturador = _capturar_angular if frontend == "angular" else _capturar_gradio
            problemas = capturador(pagina, url, destino)
        finally:
            navegador.close()
    for problema in problemas:
        print(f"PROBLEMA: {problema}")
    return 1 if problemas else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captura la UI de NexPlay (Gradio o Angular).")
    parser.add_argument("--frontend", choices=sorted(_URLS), default="gradio", help="por defecto %(default)s")
    parser.add_argument("--url", help="URL de la UI (por defecto, la del frontend elegido)")
    args = parser.parse_args()
    sys.exit(capturar(args.frontend, args.url or _URLS[args.frontend]))
