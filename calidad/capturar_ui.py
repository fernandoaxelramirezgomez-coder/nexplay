"""Captura la UI de NexPlay con Chromium headless, para revisar los cambios
visuales sin abrir un navegador a mano.

Guarda en docs/capturas/angular/:
  catalogo.png, catalogo-inicio.png, catalogo-filtrado.png
  ficha-wild-hearts.png, perfil.png, ficha-con-perfil.png, comparar.png
y verifica contra la API (--api): total de tarjetas, conteo y orden de cada
estante, filtro reactivo, factores de la ficha, entrada directa por URL, appid
inexistente, perfil que sobrevive a la recarga, la historia del perfil sin que
cambie el nivel de riesgo, y la comparación sincronizada con ?appids=.

docs/capturas/ está ignorada por git salvo la captura del README,
docs/capturas/captura-interfaz.png, que este script no toca. Revisa además que no
aparezca "abandono" ni un score de riesgo con decimales.

Requiere la API y el frontend corriendo (uvicorn api.main:app y npx ng serve en
frontend/). Una sola vez:
  pip install -r requirements-dev.txt
  playwright install chromium
  sudo playwright install-deps chromium   # librerías del sistema (Linux/WSL)

Uso:
  python calidad/capturar_ui.py [--url URL]
"""

import argparse
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import Error as ErrorPlaywright
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as TiempoAgotado

_RAIZ = Path(__file__).resolve().parent.parent
_DESTINO = _RAIZ / "docs" / "capturas" / "angular"
_URL = "http://localhost:4200"

_APPID_FICHA = 1938010  # Wild Hearts
_VIEWPORT = {"width": 1440, "height": 900}
_TIMEOUT_MS = 60_000

# Los scores del modelo son decimales como 0.7424: nunca deben verse en pantalla.
_SCORE_VISIBLE = re.compile(r"\b0[.,]\d{3,}\b")

# Cuántas portadas cayeron al SVG de respaldo, de las que están a la vista.
_JS_CONTAR_FALLBACKS = """
selector => {
    const imgs = [...document.querySelectorAll(selector)].filter(i => i.offsetParent !== null);
    return [imgs.filter(i => i.src.startsWith('data:image/svg')).length, imgs.length];
}
"""


def _explorar(url: str) -> str:
    """El catálogo vive en /explorar; la raíz es el inicio."""
    return f"{url.rstrip('/')}/explorar"


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


_PROMESA_DE_AJUSTE = (
    "para tu perfil",
    "ajusta la estimación",
    "ajustar esta estimación",
    "se ajusta a cómo juegas",
    "afinar el riesgo",
)


def _revisar_vocabulario(pagina: Page, donde: str) -> list[str]:
    texto = pagina.inner_text("body")
    problemas = []
    if "abandono" in texto.lower():
        problemas.append(f"{donde}: aparece 'abandono'")
    if scores := _SCORE_VISIBLE.findall(texto):
        problemas.append(f"{donde}: scores visibles {scores[:5]}")
    # Modelo de título: el perfil no cambia el riesgo, ningún texto puede prometerlo.
    for frase in _PROMESA_DE_AJUSTE:
        if frase in texto.lower():
            problemas.append(f"{donde}: promete ajustar el riesgo con el perfil ('{frase}')")
    return problemas


def _abrir(pagina: Page, url: str) -> None:
    try:
        pagina.goto(url, wait_until="domcontentloaded", timeout=15_000)
    except ErrorPlaywright as exc:
        sys.exit(
            f"No pude abrir {url}: {exc.message.splitlines()[0]}\n"
            "¿Están corriendo la API y el frontend? (uvicorn api.main:app / npx ng serve en frontend/)"
        )


# --- Angular --------------------------------------------------------------


def _catalogo_api(api: str) -> list[dict]:
    try:
        with urllib.request.urlopen(f"{api}/catalogo", timeout=10) as respuesta:
            return json.load(respuesta)
    except OSError as exc:
        sys.exit(f"No pude leer {api}/catalogo para comparar: {exc}")


def _orden_esperado(juegos: list[dict], banda: str) -> list[int]:
    """Mismo criterio que dominio/estantes.ts en el frontend."""
    del_estante = [j for j in juegos if j["banda_riesgo"] == banda]
    return [j["appid"] for j in sorted(del_estante, key=lambda j: j["riesgo"], reverse=banda != "bajo")]


def _appids_visibles(pagina: Page, banda: str) -> list[int]:
    selector = f"[data-testid='estante-{banda}'] [data-testid='tarjeta-juego']"
    return [int(v) for v in pagina.locator(selector).evaluate_all("nodos => nodos.map(n => n.dataset.appid)")]


def _revisar_overlay(pagina: Page) -> None:
    """ng serve tapa la página con un overlay cuando la compilación falla, y sin esto
    el síntoma es un clic que nunca ocurre."""
    detalle = pagina.evaluate(
        """() => {
            const overlay = document.querySelector('vite-error-overlay');
            return overlay ? (overlay.shadowRoot?.textContent || overlay.textContent || 'sin detalle') : null;
        }"""
    )
    if detalle:
        sys.exit(f"ng serve tiene un error de compilación:\n{' '.join(detalle.split())[:500]}")


def _angular_catalogo(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    _abrir(pagina, _explorar(url))
    _revisar_overlay(pagina)
    pagina.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
    try:
        pagina.get_by_test_id("tarjeta-juego").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        sys.exit("El shell cargó pero el catálogo está vacío: ¿está corriendo la API donde apunta environment.ts?")

    juegos = _catalogo_api(api)
    problemas = []
    total = pagina.get_by_test_id("tarjeta-juego").count()
    if total != len(juegos):
        problemas.append(f"catálogo: {total} tarjetas en pantalla y {len(juegos)} en la API")

    for banda in ("bajo", "medio", "alto"):
        esperado = _orden_esperado(juegos, banda)
        visible = _appids_visibles(pagina, banda)
        conteo = pagina.locator(f"[data-testid='estante-{banda}'] [data-testid='estante-conteo']").inner_text()
        if conteo != f"({len(esperado)})":
            problemas.append(f"estante {banda}: el título dice {conteo} y la API tiene {len(esperado)}")
        if visible != esperado:
            problemas.append(f"estante {banda}: el orden no coincide con el de la API")
        print(f"estante {banda}: {len(visible)} juegos, orden {'OK' if visible == esperado else 'DISTINTO'}")

    # Estado al pasar el cursor: motivo principal y botón de comparar sobre la portada.
    primera = pagina.get_by_test_id("tarjeta-juego").first
    primera.hover()
    pagina.wait_for_function(
        "() => !(document.querySelector(\"[data-testid='tarjeta-motivo']\")?.textContent || '').includes('Buscando')",
        timeout=_TIMEOUT_MS,
    )
    _esperar_quietud(pagina)
    pagina.screenshot(path=destino / "catalogo-hover.png")
    print(f"hover:    catalogo-hover.png ({primera.get_by_test_id('tarjeta-motivo').inner_text()})")
    pagina.mouse.move(0, 0)

    _recorrer_pagina(pagina)
    _esperar_quietud(pagina)
    ruta = destino / "catalogo.png"
    pagina.screenshot(path=ruta, full_page=True)
    pagina.screenshot(path=destino / "catalogo-inicio.png")
    print(f"catálogo: {ruta.relative_to(_RAIZ)} y catalogo-inicio.png ({total} tarjetas)")
    problemas += _revisar_vocabulario(pagina, "catálogo")

    # Filtro reactivo: sin botón, la lista y la URL cambian al teclear.
    esperados_dark = sum("dark" in j["nombre"].lower() for j in juegos)
    pagina.get_by_test_id("filtro-texto").fill("dark")
    try:
        pagina.wait_for_function(
            "n => document.querySelectorAll(\"[data-testid='tarjeta-juego']\").length === n",
            arg=esperados_dark,
            timeout=_TIMEOUT_MS,
        )
    except TiempoAgotado:
        visibles = pagina.get_by_test_id("tarjeta-juego").count()
        problemas.append(f"filtro 'dark': {visibles} tarjetas en pantalla y {esperados_dark} en la API")
    if "q=dark" not in pagina.url:
        problemas.append(f"filtro 'dark': la URL no lo refleja ({pagina.url})")
    _esperar_quietud(pagina)
    pagina.screenshot(path=destino / "catalogo-filtrado.png")
    print(f"filtro:   catalogo-filtrado.png ('dark' → {esperados_dark} juegos, URL con q=dark)")
    pagina.get_by_test_id("filtro-texto").fill("")
    return problemas


def _angular_ficha(pagina: Page, url: str, destino: Path) -> list[str]:
    problemas = []

    # Desde una tarjeta, con un filtro puesto: al volver, el catálogo debe seguir filtrado.
    pagina.get_by_test_id("filtro-texto").fill("dark")
    pagina.wait_for_function(
        "() => document.querySelectorAll(\"[data-testid='tarjeta-juego']\").length === 2", timeout=_TIMEOUT_MS
    )
    pagina.locator("[data-testid='tarjeta-juego'] a").first.click()
    pagina.get_by_test_id("ficha-nombre").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.go_back()
    pagina.get_by_test_id("filtro-texto").wait_for(state="visible", timeout=_TIMEOUT_MS)
    if "q=dark" not in pagina.url:
        problemas.append(f"al volver del juego, el filtro se perdió ({pagina.url})")
    pagina.get_by_test_id("filtro-texto").fill("")
    pagina.wait_for_function(
        "() => document.querySelectorAll(\"[data-testid='tarjeta-juego']\").length > 2", timeout=_TIMEOUT_MS
    )

    # Wild Hearts: sin nota de Metacritic, así que no debe aparecer ese factor.
    pagina.locator(f"[data-testid='tarjeta-juego'][data-appid='{_APPID_FICHA}'] a").click()
    pagina.get_by_test_id("ficha-nombre").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("ficha-veredicto").wait_for(state="visible", timeout=_TIMEOUT_MS)
    # El párrafo de "segunda opinión" salió de la ficha: lo que hay que esperar ahora son
    # los factores, que llegan con la predicción.
    pagina.wait_for_function(
        "() => document.querySelectorAll(\"[data-testid='factores-lista'] li\").length > 0",
        timeout=_TIMEOUT_MS,
    )
    factores = pagina.get_by_test_id("factores").inner_text()
    if "nota de Metacritic" in factores:
        problemas.append("ficha de Wild Hearts: muestra 'nota de Metacritic' aunque el juego no tiene nota")
    plano = " ".join(factores.lower().split())
    # Los factores se leen en lenguaje de jugador: "No tiene nota de la crítica · en este
    # catálogo eso sube el riesgo estimado", no la etiqueta nominal de la API.
    if "no tiene nota de la crítica" not in plano or "sube el riesgo" not in plano:
        problemas.append(f"ficha de Wild Hearts: falta el factor de cobertura de crítica ({plano[:120]})")
    _esperar_portadas(pagina, "[data-testid='ficha'] img")
    _esperar_quietud(pagina)
    ruta = destino / "ficha-wild-hearts.png"
    pagina.screenshot(path=ruta, full_page=True)
    print(f"ficha:    {ruta.relative_to(_RAIZ)} ({pagina.get_by_test_id('ficha-nombre').inner_text()})")
    problemas += _revisar_vocabulario(pagina, "ficha")
    problemas += _sin_filetes_dobles(pagina, "la ficha")

    # Respaldo de la cabecera: si capsule_616x353 no existe, debe usar portada_url.
    pagina.route("**/capsule_616x353.jpg", lambda ruta: ruta.abort())
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("ficha-nombre").wait_for(state="visible", timeout=_TIMEOUT_MS)
    try:
        pagina.wait_for_function(
            "() => (document.querySelector('app-portada-ancha img')?.currentSrc || '').includes('header.jpg')",
            timeout=_TIMEOUT_MS,
        )
        print("respaldo: sin capsule_616x353, la cabecera cae a header.jpg")
    except TiempoAgotado:
        problemas.append("la cabecera no cae a portada_url cuando falta capsule_616x353")
    pagina.unroute("**/capsule_616x353.jpg")

    # Entrada directa por URL y appid inexistente.
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("ficha-nombre").wait_for(state="visible", timeout=_TIMEOUT_MS)
    print(f"directa:  /juego/{_APPID_FICHA} abre {pagina.get_by_test_id('ficha-nombre').inner_text()}")
    _abrir(pagina, f"{url.rstrip('/')}/juego/1")
    try:
        pagina.get_by_test_id("ficha-no-encontrado").wait_for(state="visible", timeout=_TIMEOUT_MS)
        print("faltante: /juego/1 muestra 'Juego no encontrado'")
    except TiempoAgotado:
        problemas.append("/juego/1 no muestra el mensaje de juego no encontrado")
    return problemas


# Dos identidades de prueba para el hilo: el id anónimo vive en localStorage, así que
# cambiarlo es cambiar de persona sin necesidad de otro navegador.
_USUARIO_A = "captura-hilo-a1"
_USUARIO_B = "captura-hilo-b2"
_TEXTO_A = "comentario de prueba <b>con etiquetas</b>"
_TEXTO_A_EDITADO = "comentario de prueba, ya corregido"


def _identificarse(pagina: Page, url: str, usuario: str) -> None:
    """Deja ese id anónimo en localStorage y vuelve a abrir la ficha con él."""
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.evaluate("id => localStorage.setItem('nexplay.usuario.v1', id)", usuario)
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("hilo-comentarios").wait_for(state="visible", timeout=_TIMEOUT_MS)


def _burbuja(pagina: Page, id_comentario: str):
    """Por id, no por texto: al editar, el texto pasa a estar dentro de un textarea."""
    return pagina.locator(f"[data-testid='comentario'][data-id='{id_comentario}']")


def _esperar_burbuja(pagina: Page, texto: str, problemas: list[str], que: str) -> str | None:
    """Espera a que aparezca una burbuja con ese texto y devuelve su id."""
    try:
        burbuja = pagina.locator("[data-testid='comentario']").filter(has_text=texto).last
        burbuja.wait_for(state="visible", timeout=_TIMEOUT_MS)
        return burbuja.get_attribute("data-id")
    except TiempoAgotado:
        aviso = pagina.get_by_test_id("hilo-comentarios").inner_text()
        problemas.append(f"{que}: el comentario no apareció en el hilo ({' '.join(aviso.split())[:160]})")
        return None


def _esperar_conteo(pagina: Page, id_comentario: str, esperado: str, accion, problemas: list[str], que: str) -> None:
    accion()
    try:
        pagina.wait_for_function(
            "([id, n]) => document.querySelector(`[data-id='${id}'] [data-testid='comentario-reacciones']`)"
            "?.textContent.trim() === n",
            arg=[id_comentario, esperado],
            timeout=_TIMEOUT_MS,
        )
    except TiempoAgotado:
        visto = pagina.locator(f"[data-id='{id_comentario}'] [data-testid='comentario-reacciones']").inner_text()
        problemas.append(f"{que}: el conteo quedó en {visto.strip()} y se esperaba {esperado}")


def _angular_hilo(pagina: Page, url: str, destino: Path) -> list[str]:
    """Editar, eliminar y reaccionar en el hilo, con dos identidades distintas."""
    problemas = []
    _identificarse(pagina, url, _USUARIO_A)

    pagina.get_by_test_id("comentario-nuevo").fill(_TEXTO_A)
    pagina.get_by_test_id("enviar-comentario").click()
    id_comentario = _esperar_burbuja(pagina, "comentario de prueba", problemas, "publicar")
    if id_comentario is None:
        return problemas

    mio = _burbuja(pagina, id_comentario)
    # El texto con etiquetas tiene que verse como texto, no convertirse en marcado.
    if mio.locator("b").count():
        problemas.append("el hilo interpretó el HTML del comentario en vez de escaparlo")
    if "<b>" not in mio.inner_text():
        problemas.append(f"el comentario no muestra las etiquetas como texto ({mio.inner_text()[:80]})")
    if mio.get_by_test_id("comentario-editar").count() != 1:
        problemas.append("el comentario propio no ofrece 'Editar'")

    # Editar: cambia el texto y aparece "(editado)".
    mio.get_by_test_id("comentario-editar").click()
    mio.get_by_test_id("comentario-editor").fill(_TEXTO_A_EDITADO)
    _esperar_quietud(pagina)
    ruta = destino / "hilo-editando.png"
    pagina.get_by_test_id("hilo-comentarios").screenshot(path=ruta)
    print(f"hilo:     {ruta.relative_to(_RAIZ)} (editor en línea abierto)")
    mio.get_by_test_id("comentario-guardar-edicion").click()
    try:
        pagina.wait_for_function(
            "([id, texto]) => document.querySelector(`[data-id='${id}'] [data-testid='comentario-editado']`)"
            " && document.querySelector(`[data-id='${id}']`).textContent.includes(texto)",
            arg=[id_comentario, _TEXTO_A_EDITADO],
            timeout=_TIMEOUT_MS,
        )
        print("hilo:     el dueño edita su comentario y queda marcado como '(editado)'")
    except TiempoAgotado:
        problemas.append(f"editar: el comentario no quedó actualizado ({mio.inner_text()[:120]})")
        return problemas
    if "<b>" in mio.inner_text():
        problemas.append("el texto viejo siguió en pantalla tras editar")
    if mio.locator("[data-testid='comentario-editor']").count():
        problemas.append("tras guardar, el editor en línea sigue abierto")

    # Reaccionar: alterna y el conteo lo sigue.
    reaccion = mio.get_by_test_id("comentario-reaccion")
    _esperar_conteo(pagina, id_comentario, "1", reaccion.click, problemas, "reaccionar")
    if reaccion.get_attribute("aria-pressed") != "true":
        problemas.append("tras reaccionar, el botón no queda marcado como activo")
    _esperar_quietud(pagina)
    ruta = destino / "hilo-comentario-propio.png"
    pagina.get_by_test_id("hilo-comentarios").screenshot(path=ruta)
    print(f"hilo:     {ruta.relative_to(_RAIZ)} (editado, con reacción propia)")

    _esperar_conteo(pagina, id_comentario, "0", reaccion.click, problemas, "quitar la reacción")
    if reaccion.get_attribute("aria-pressed") != "false":
        problemas.append("al quitar la reacción, el botón sigue marcado como activo")

    # La otra persona: ve el comentario, puede reaccionar, no puede editarlo.
    _identificarse(pagina, url, _USUARIO_B)
    ajeno = _burbuja(pagina, id_comentario)
    ajeno.wait_for(state="visible", timeout=_TIMEOUT_MS)
    if ajeno.get_by_test_id("comentario-editar").count():
        problemas.append("un comentario ajeno ofrece 'Editar'")
    if ajeno.get_by_test_id("comentario-eliminar").count():
        problemas.append("un comentario ajeno ofrece 'Eliminar'")
    if ajeno.get_by_test_id("comentario-editado").count() != 1:
        problemas.append("la otra persona no ve la marca '(editado)'")
    _esperar_conteo(
        pagina, id_comentario, "1", ajeno.get_by_test_id("comentario-reaccion").click, problemas, "reaccionar como otro"
    )
    _esperar_quietud(pagina)
    ruta = destino / "hilo-visto-por-otro.png"
    pagina.get_by_test_id("hilo-comentarios").screenshot(path=ruta)
    print(f"hilo:     {ruta.relative_to(_RAIZ)} (sin Editar ni Eliminar, con reacción ajena)")

    # De vuelta como el dueño: la reacción del otro cuenta, pero no es suya.
    _identificarse(pagina, url, _USUARIO_A)
    mio = _burbuja(pagina, id_comentario)
    mio.wait_for(state="visible", timeout=_TIMEOUT_MS)
    conteo = mio.get_by_test_id("comentario-reacciones").inner_text().strip()
    if conteo != "1":
        problemas.append(f"el conteo de reacciones no refleja a la otra persona ({conteo})")
    if mio.get_by_test_id("comentario-reaccion").get_attribute("aria-pressed") != "false":
        problemas.append("la reacción ajena aparece como propia")

    # Eliminar: primero pide confirmación, y solo entonces se va.
    mio.get_by_test_id("comentario-eliminar").click()
    mio.get_by_test_id("comentario-confirmar").wait_for(state="visible", timeout=_TIMEOUT_MS)
    _esperar_quietud(pagina)
    ruta = destino / "hilo-confirmar-eliminar.png"
    pagina.get_by_test_id("hilo-comentarios").screenshot(path=ruta)
    print(f"hilo:     {ruta.relative_to(_RAIZ)} (confirmación antes de eliminar)")

    mio.get_by_test_id("comentario-cancelar-eliminar").click()
    if _burbuja(pagina, id_comentario).count() != 1:
        problemas.append("cancelar la confirmación borró el comentario igual")

    mio.get_by_test_id("comentario-eliminar").click()
    mio.get_by_test_id("comentario-confirmar-eliminar").click()
    try:
        pagina.wait_for_function(
            "id => !document.querySelector(`[data-testid='comentario'][data-id='${id}']`)",
            arg=id_comentario,
            timeout=_TIMEOUT_MS,
        )
        print("hilo:     el dueño elimina su comentario y desaparece del hilo")
    except TiempoAgotado:
        problemas.append("el comentario propio no desapareció tras confirmar la eliminación")

    problemas += _revisar_vocabulario(pagina, "hilo")
    return problemas


def _nivel_api(api: str, formulario: dict, appid: int) -> str:
    """Puntúa un appid con un perfil derivado por la API, para comparar niveles."""
    cuerpo = json.dumps(formulario).encode()
    cabeceras = {"Content-Type": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(f"{api}/perfil", cuerpo, cabeceras), timeout=10) as r:
        perfil = json.load(r)
    solicitud = json.dumps({"perfil": perfil, "appid": appid}).encode()
    with urllib.request.urlopen(urllib.request.Request(f"{api}/prediccion", solicitud, cabeceras), timeout=10) as r:
        return json.load(r)["nivel"]


def _appids_sugeridos(pagina: Page) -> list[int]:
    return [int(a) for a in pagina.get_by_test_id("sugerencia").evaluate_all("ts => ts.map(t => t.dataset.appid)")]


def _esperar_sugerencias(pagina: Page, antes: list[int]) -> list[int]:
    """Las sugerencias se recalculan en vivo: espera a que la lista cambie (o a que aparezca
    el aviso de tope relajado) y la devuelve."""
    try:
        pagina.wait_for_function(
            "antes => { const ahora = [...document.querySelectorAll('[data-testid=sugerencia]')].map(t => Number(t.dataset.appid));"
            " return JSON.stringify(ahora) !== JSON.stringify(antes); }",
            arg=antes, timeout=10_000,
        )
    except TiempoAgotado:
        pass
    return _appids_sugeridos(pagina)


def _angular_sugerencias(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Las sugerencias de /perfil (6C): con todo el perfil —géneros, gasto, horas y
    fricción—, en vivo mientras se responde, cada tarjeta con sus razones y su riesgo
    aparte, y sin quedar en blanco por el gasto."""
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/perfil")
    seccion = pagina.get_by_test_id("sugerencias")
    try:
        seccion.wait_for(state="visible", timeout=_TIMEOUT_MS)
        pagina.get_by_test_id("sugerencia").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        return ["con perfil declarado no aparecen sugerencias en /perfil"]

    declarados = {"acción", "rol"}  # los mismos que eligió el paso anterior, con gasto de $200 a $500
    catalogo = {j["appid"]: j for j in _catalogo_api(api)}
    precio = lambda appid: 0 if catalogo[appid]["es_gratis"] else catalogo[appid]["precio_final"]
    tarjetas = pagina.get_by_test_id("sugerencia")
    for i in range(tarjetas.count()):
        tarjeta = tarjetas.nth(i)
        appid = int(tarjeta.get_attribute("data-appid"))
        generos = {g.lower() for g in catalogo[appid]["generos"]}
        if not generos & declarados:
            problemas.append(f"sugiere {catalogo[appid]['nombre']}, que no comparte ningún género declarado")
        if precio(appid) is None or precio(appid) > 500:
            problemas.append(f"sugiere {catalogo[appid]['nombre']}, que pasa del tope de $500 por juego")
        porque = tarjeta.get_by_test_id("sugerencia-porque").inner_text()
        if "coincide en" not in porque.lower():
            problemas.append(f"la sugerencia {appid} no explica qué coincidió ('{porque[:60]}')")
        tipos = tarjeta.get_by_test_id("sugerencia-razones").locator("li").evaluate_all("ls => ls.map(l => l.dataset.tipo)")
        if tipos[:2] != ["generos", "precio"]:
            problemas.append(f"la sugerencia {appid} no dice sus razones de géneros y precio ({tipos})")
        if not tarjeta.get_by_test_id("pildora-banda").count() or "Aparte" not in tarjeta.inner_text():
            problemas.append(f"la sugerencia {appid} no muestra su riesgo aparte")
        # La nota que lleva a la segunda opinión es solo de la banda alta.
        nota = tarjeta.get_by_test_id("sugerencia-nota-alto")
        es_alto = catalogo[appid]["banda_riesgo"] == "alto"
        if es_alto and not nota.count():
            problemas.append(f"la sugerencia {appid} es de banda alta y no dice dónde están los motivos")
        if not es_alto and nota.count():
            problemas.append(f"la sugerencia {appid} no es de banda alta y aun así lleva la nota")

    texto = " ".join(seccion.inner_text().split()).lower()
    for frase in ("recomendación de compra", "no cambian el riesgo del juego", "se recalculan mientras respondes"):
        if frase not in texto:
            problemas.append(f"la sección de sugerencias no dice «{frase}»")
    for frase in _PROMESA_DE_AJUSTE + ("te recomiendo", "deberías", "conviene", "vale la pena", "buena compra"):
        if frase in texto:
            problemas.append(f"las sugerencias usan una fórmula prohibida ('{frase}')")

    _esperar_portadas(pagina, "[data-testid='sugerencias'] img")
    _esperar_quietud(pagina)
    ruta = destino / "sugerencias-perfil.png"
    seccion.screenshot(path=ruta)
    print(f"sugerencias: {tarjetas.count()} con géneros en común, dentro de $500 por juego, con sus razones "
          f"y el riesgo aparte ({ruta.relative_to(_RAIZ)})")

    # En vivo: bajar el tope a $200 cambia la lista sin guardar.
    antes = _appids_sugeridos(pagina)
    pagina.get_by_test_id("grupo-gasto").get_by_text("Hasta $200", exact=True).click()
    ahora = _esperar_sugerencias(pagina, antes)
    relajado = pagina.get_by_test_id("sugerencias-tope-relajado").count()
    fuera = [catalogo[a]["nombre"] for a in ahora if precio(a) is None or precio(a) > 200]
    if ahora == antes or (fuera and not relajado):
        problemas.append(f"al bajar el tope a $200 las sugerencias no se recalcularon ({fuera[:3]})")
    else:
        print(f"sugerencias: en vivo, con tope de $200 cambian sin guardar ({len(ahora)} juegos)")

    # Nunca en blanco: con un género que no tiene nada de $200 o menos, se avisa y se relaja.
    por_genero: dict[str, list[dict]] = {}
    for juego in catalogo.values():
        for genero in juego["generos"]:
            por_genero.setdefault(genero, []).append(juego)
    sin_baratos = sorted(
        g for g, js in por_genero.items()
        if not any(j["es_gratis"] or (j["precio_final"] is not None and j["precio_final"] <= 200) for j in js)
    )
    if sin_baratos:
        genero = sin_baratos[0]
        for elegido in ("Acción", "Rol"):
            pagina.locator(f"[data-testid='chip-genero'][data-genero='{elegido}']").click()
        pagina.locator(f"[data-testid='chip-genero'][data-genero='{genero}']").click()
        try:
            pagina.get_by_test_id("sugerencias-tope-relajado").wait_for(state="visible", timeout=10_000)
            aviso = " ".join(pagina.get_by_test_id("sugerencias-tope-relajado").inner_text().split())
            if not pagina.get_by_test_id("sugerencia").count():
                problemas.append(f"con «{genero}» y tope de $200, las sugerencias quedaron en blanco")
            else:
                print(f"sugerencias: con «{genero}» y tope de $200 no hay nada; avisa y relaja: «{aviso}»")
        except TiempoAgotado:
            problemas.append(f"con «{genero}» y tope de $200 no aparece el aviso de tope relajado")
    else:
        print("sugerencias: todos los géneros tienen algo de $200 o menos; el relajo se prueba en sugerencias.spec")
    return problemas


def _angular_perfil(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/perfil")
    pagina.get_by_test_id("perfil").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("chip-genero").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    problemas += _revisar_vocabulario(pagina, "perfil")
    _esperar_quietud(pagina)
    pagina.screenshot(path=destino / "perfil.png", full_page=True)

    # El formulario arranca vacío: hay que responder las cinco preguntas antes de que
    # "Guardar perfil" se habilite. Que empiece deshabilitado es parte de lo que se revisa.
    # La barra de guardar se ve desde el principio, pegada abajo, y dice qué falta.
    pagina.evaluate("() => scrollTo(0, 0)")
    pagina.wait_for_timeout(300)
    barra = pagina.get_by_test_id("barra-guardar").bounding_box()
    alto_ventana = pagina.viewport_size["height"]
    if not barra or barra["y"] + barra["height"] > alto_ventana:
        problemas.append(f"la barra de guardar no se ve al abrir el formulario ({barra})")
    if pagina.get_by_test_id("crear-perfil").is_enabled():
        problemas.append("el formulario vacío ya deja guardar el perfil")
    estados = [pagina.get_by_test_id("perfil-estado").inner_text()]
    pagina.get_by_test_id("grupo-compras").get_by_text("Muchos", exact=True).click()
    pagina.get_by_test_id("grupo-gasto").get_by_text("$200 a $500", exact=True).click()
    pagina.get_by_test_id("grupo-horas").get_by_text("Media", exact=True).click()
    pagina.get_by_test_id("grupo-plataforma").get_by_text("PC", exact=True).click()
    pagina.get_by_test_id("grupo-plataforma").get_by_text("Xbox", exact=True).click()
    estados.append(pagina.get_by_test_id("perfil-estado").inner_text())
    pagina.get_by_test_id("grupo-friccion").get_by_text("Media", exact=True).click()
    for genero in ("Acción", "Rol"):
        pagina.locator(f"[data-testid='chip-genero'][data-genero='{genero}']").click()
    estados.append(pagina.get_by_test_id("perfil-estado").inner_text())
    esperados = ("0 de 5 respondidas · faltan 5", "4 de 5 respondidas · falta: tolerancia a la fricción",
                 "5 de 5 · listo para guardar")
    if tuple(" ".join(e.split()) for e in estados) != esperados:
        problemas.append(f"la barra de guardar no dice qué falta ({estados})")
    if not pagina.get_by_test_id("crear-perfil").is_enabled():
        problemas.append("con las cinco respuestas puestas, 'Guardar perfil' sigue deshabilitado")
    pagina.get_by_test_id("crear-perfil").click()

    pagina.get_by_test_id("perfil-activo").wait_for(state="visible", timeout=_TIMEOUT_MS)
    # Crear el perfil se queda en la misma página: lo único que el perfil cambia son los
    # juegos parecidos, que aparecen justo debajo. Irse al catálogo los dejaba sin ver.
    if not pagina.url.rstrip("/").endswith("/perfil"):
        problemas.append(f"tras crear el perfil se fue de la página ({pagina.url})")
    elif "Perfil guardado y activo" not in (pagina.get_by_test_id("perfil-guardado").inner_text() if pagina.get_by_test_id("perfil-guardado").count() else ""):
        problemas.append("tras guardar el perfil la barra no dice «Perfil guardado y activo»")
    else:
        print("perfil:   la barra de guardar se ve desde el principio y dice qué falta; al guardar, "
              "«✓ Perfil guardado y activo», se queda en su página y baja a las sugerencias")
    pagina.reload()
    try:
        pagina.get_by_test_id("perfil-activo").wait_for(state="visible", timeout=_TIMEOUT_MS)
        print("perfil:   creado, y sigue activo después de recargar")
    except TiempoAgotado:
        problemas.append("el perfil no sobrevivió a la recarga")

    problemas += _angular_sugerencias(pagina, url, destino, api)

    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("ficha-nombre").wait_for(state="visible", timeout=_TIMEOUT_MS)
    # Modelo de título: con o sin perfil, la banda es la misma y el rótulo también. El
    # rótulo vive en la píldora del encabezado; el veredicto es la línea de riesgo.
    rotulo = " ".join(pagina.get_by_test_id("pildora-banda").first.inner_text().lower().split())
    if not rotulo.startswith("riesgo de arrepentimiento"):
        problemas.append(f"con perfil declarado, la banda cambió de rótulo: '{rotulo}'")
    veredicto = " ".join(pagina.get_by_test_id("ficha-veredicto").inner_text().lower().split())
    if "arrepentimiento temprano" not in veredicto:
        problemas.append(f"el veredicto no usa el vocabulario del proyecto ('{veredicto[:80]}')")
    # La historia son tres líneas —la primera reconoce el género en común— y, con Xbox
    # marcado, la de plataforma con las dos; la nota de plataforma ya no va en el veredicto.
    historia = pagina.get_by_test_id("historia-texto").inner_text()
    plano = " ".join(historia.split())
    if "dentro" not in plano.lower() or "Acción" not in plano:
        problemas.append(f"la historia no reconoce el género en común ('{plano[:120]}')")
    tipos = pagina.get_by_test_id("historia-texto").locator("li").evaluate_all("ls => ls.map(l => l.dataset.tipo)")
    if tipos != ["generos", "tiempo", "compra", "plataforma"]:
        problemas.append(f"la historia no son tres líneas más la de plataforma ({tipos})")
    linea = " ".join(pagina.get_by_test_id("historia-plataforma").inner_text().split()) if "plataforma" in tipos else ""
    if linea != "Juegas en PC y Xbox; el riesgo se calcula con reseñas de Steam.":
        problemas.append(f"la línea de plataforma no nombra las dos marcadas ('{linea}')")
    elif "transfiere" in pagina.get_by_test_id("ficha-resumen").inner_text():
        problemas.append("la nota de plataforma sigue en el panel del veredicto")
    else:
        print(f"ficha:    la historia dice «{linea}» y el veredicto ya no trae la nota")
    if pagina.get_by_test_id("historia-sin-perfil").count():
        problemas.append("con perfil declarado, la historia sigue pidiendo crear uno")
    _esperar_portadas(pagina, "[data-testid='ficha'] img")
    _esperar_quietud(pagina)
    pagina.screenshot(path=destino / "ficha-con-perfil.png", full_page=True)
    print(f"ficha:    ficha-con-perfil.png ({veredicto.splitlines()[0]}; historia: {plano[:70]}…)")

    _esperar_quietud(pagina)
    pagina.get_by_test_id("historia-perfil").screenshot(path=destino / "historia-perfil.png")
    print(f"historia: {(destino / 'historia-perfil.png').relative_to(_RAIZ)}")

    # Los géneros no deben mover el riesgo: el modelo no los usa.
    base = {
        "compras_al_anio": 25,
        "horas_por_semana": 6,
        "tolerancia_friccion": 3,
        "tags_rechazados": [],
        "plataforma": "pc",
    }
    con = _nivel_api(api, {**base, "tags_preferidos": ["acción", "rol"]}, _APPID_FICHA)
    sin = _nivel_api(api, {**base, "tags_preferidos": []}, _APPID_FICHA)
    if con != sin:
        problemas.append(f"los géneros cambiaron el nivel de riesgo ({sin} sin géneros, {con} con géneros)")
    print(f"géneros:  el nivel no cambia por declararlos ({sin} en ambos casos)")

    return problemas + _revisar_vocabulario(pagina, "ficha con perfil")


_PERFIL_V3 = {
    "valores": {"compras": 4, "horas": 6, "friccion": 3, "plataforma": "pc", "generos": ["Acción"]},
    "perfil": {
        "compras_al_anio": 4, "horas_por_semana": 6.0, "tolerancia_friccion": "media",
        "tags_preferidos": ["acción"], "tags_rechazados": [], "plataforma": "pc",
        "segmento": "novato", "disponibilidad": "media",
    },
}


def _angular_6c(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Fase 6C, lo que no cabe en el recorrido del perfil: el camino al perfil desde el
    inicio, la píldora del menú sin perfil, la migración de los perfiles v3, la burbuja
    encima de la barra de guardar y las horas típicas de la ficha técnica."""
    problemas = []
    base = url.rstrip("/")
    navegador = pagina.context.browser

    # Sin perfil: el inicio ya no trae la invitación (la tarjeta «Encaja contigo» lleva a
    # /perfil), y la píldora del menú invita a crearlo.
    contexto = navegador.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    try:
        otra = contexto.new_page()
        _abrir(otra, base)
        otra.get_by_test_id("inicio-por-que").wait_for(state="visible", timeout=_TIMEOUT_MS)
        pildora = otra.get_by_test_id("perfil-inactivo")
        encaja = otra.locator("[data-testid='herramienta-inicio'][data-herramienta='perfil']")
        if otra.get_by_test_id("invitacion-perfil").count():
            problemas.append("el inicio sigue trayendo la invitación al perfil, que repite «Encaja contigo»")
        elif not (encaja.get_attribute("href") or "").endswith("/perfil"):
            problemas.append("sin la invitación, «Encaja contigo» no lleva a /perfil")
        else:
            print("invitación: fuera del inicio; «Encaja contigo» lleva a /perfil")
        texto = " ".join(pildora.inner_text().split()) if pildora.count() else ""
        if "Sin perfil" not in texto or not (pildora.get_attribute("href") or "").endswith("/perfil"):
            problemas.append(f"sin perfil, la píldora del menú no invita a crearlo ('{texto}')")
        else:
            print(f"menú:     sin perfil, la píldora dice «{texto}» y lleva a /perfil")
    finally:
        contexto.close()

    # Un perfil v3: sigue activo, la píldora avisa de la pregunta nueva y el gasto falta.
    contexto = navegador.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    contexto.add_init_script(f"localStorage.setItem('nexplay.perfil.v3', {json.dumps(json.dumps(_PERFIL_V3))})")
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/perfil")
        otra.get_by_test_id("perfil-activo").wait_for(state="visible", timeout=_TIMEOUT_MS)
        pildora = " ".join(otra.get_by_test_id("perfil-activo").inner_text().split())
        gasto = otra.get_by_test_id("estado-gasto").inner_text().strip()
        estado = " ".join(otra.get_by_test_id("perfil-estado").inner_text().split())
        guardado = otra.evaluate("() => [!!localStorage.getItem('nexplay.perfil.v4'), !!localStorage.getItem('nexplay.perfil.v3')]")
        if pildora != "Perfil activo · 1 pregunta nueva" or gasto != "Falta responder" or guardado != [True, False]:
            problemas.append(f"el perfil v3 no migra como se acordó (píldora '{pildora}', gasto '{gasto}', v4/v3 {guardado})")
        else:
            print(f"migración: un perfil v3 sigue activo, la píldora dice «{pildora}», el gasto «{gasto}» "
                  f"y la barra «{estado}»")
    finally:
        contexto.close()

    # En /perfil la burbuja de Nia va encima de la barra de guardar, en escritorio y en teléfono.
    for vista in (_VIEWPORT, {"width": 390, "height": 844}):
        contexto = navegador.new_context(viewport=vista)
        _sin_consultas_a_nia(contexto)
        try:
            otra = contexto.new_page()
            _abrir(otra, f"{base}/perfil")
            otra.get_by_test_id("barra-guardar").wait_for(state="visible", timeout=_TIMEOUT_MS)
            otra.wait_for_timeout(500)
            barra = otra.get_by_test_id("barra-guardar").bounding_box()
            burbuja = otra.locator("app-nia-flotante .burbuja").bounding_box()
            if not barra or not burbuja or burbuja["y"] + burbuja["height"] > barra["y"] + 1:
                problemas.append(f"a {vista['width']} px la burbuja de Nia tapa la barra de guardar ({burbuja}, {barra})")
        finally:
            contexto.close()
    if not any("burbuja de Nia tapa" in p for p in problemas):
        print("perfil:   la burbuja de Nia va encima de la barra de guardar, a 1440 y a 390 px")

    # Horas típicas en la ficha técnica, de /panorama.
    with urllib.request.urlopen(f"{api}/panorama", timeout=10) as respuesta:
        horas = {f["appid"]: f.get("horas_al_recomendar") for f in json.load(respuesta)["por_juego"]}
    if sum(1 for h in horas.values() if h is not None) < len(horas) * 0.9:
        problemas.append("/panorama no trae horas_al_recomendar en casi todos los juegos")
    _abrir(pagina, f"{base}/juego/{_APPID_FICHA}")
    try:
        pagina.get_by_test_id("horas-tipicas").wait_for(state="visible", timeout=_TIMEOUT_MS)
        mostrado = pagina.get_by_test_id("horas-tipicas").inner_text().strip()
        esperado = f"{round(horas[_APPID_FICHA])} h"
        if mostrado != esperado:
            problemas.append(f"la ficha técnica dice «{mostrado}» de horas típicas y /panorama da {horas[_APPID_FICHA]}")
        else:
            print(f"ficha:    «Horas típicas: {mostrado}» en la ficha técnica, de /panorama ({horas[_APPID_FICHA]} h)")
    except TiempoAgotado:
        problemas.append("la ficha técnica no muestra las horas típicas")
    return problemas


def _angular_comparar(pagina: Page, url: str, destino: Path) -> list[str]:
    problemas = []
    elegidos = [_APPID_FICHA, 271590, 1091500]  # Wild Hearts, GTA V Legacy, Cyberpunk 2077

    _abrir(pagina, _explorar(url))
    pagina.get_by_test_id("tarjeta-juego").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    for appid in elegidos:
        pagina.locator(f"[data-testid='tarjeta-juego'][data-appid='{appid}'] [data-testid='boton-comparar']").click()
    try:
        pagina.wait_for_function(
            "texto => document.querySelector(\"[data-testid='nav-comparar-cantidad']\")?.textContent === texto",
            arg=f"({len(elegidos)})",
            timeout=_TIMEOUT_MS,
        )
    except TiempoAgotado:
        visto = pagina.get_by_test_id("nav-comparar-cantidad").inner_text()
        problemas.append(f"el shell dice {visto} tras elegir {len(elegidos)} juegos")

    pagina.get_by_test_id("nav-comparar").click()
    pagina.get_by_test_id("comparar").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("columna-comparar").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.wait_for_function(
        "n => document.querySelectorAll(\"[data-testid='columna-comparar']\").length === n",
        arg=len(elegidos),
        timeout=_TIMEOUT_MS,
    )
    for appid in elegidos:
        if str(appid) not in pagina.url:
            problemas.append(f"la URL de comparación no lleva el appid {appid} ({pagina.url})")
    _esperar_portadas(pagina, "[data-testid='columna-comparar'] img")
    _esperar_quietud(pagina)
    ruta = destino / "comparar.png"
    pagina.screenshot(path=ruta, full_page=True)
    print(f"comparar: {ruta.relative_to(_RAIZ)} ({len(elegidos)} columnas)")
    problemas += _revisar_vocabulario(pagina, "comparar")

    pagina.get_by_test_id("quitar-comparar").first.click()
    pagina.wait_for_function(
        "n => document.querySelectorAll(\"[data-testid='columna-comparar']\").length === n",
        arg=len(elegidos) - 1,
        timeout=_TIMEOUT_MS,
    )
    try:
        pagina.wait_for_function(
            "appid => !new URL(location.href).searchParams.get('appids')?.includes(appid)",
            arg=str(elegidos[0]),
            timeout=_TIMEOUT_MS,
        )
        print("quitar:   queda 1 menos y la URL lo refleja")
    except TiempoAgotado:
        problemas.append(f"al quitar un juego, la URL lo conserva ({pagina.url})")

    # La URL manda: entrar directo con dos appids arma esas dos columnas.
    _abrir(pagina, f"{url.rstrip('/')}/comparar?appids={elegidos[0]},{elegidos[1]}")
    pagina.wait_for_function(
        "() => document.querySelectorAll(\"[data-testid='columna-comparar']\").length === 2", timeout=_TIMEOUT_MS
    )
    print(f"directa:  /comparar?appids= abre 2 columnas y el shell dice {pagina.get_by_test_id('nav-comparar-cantidad').inner_text()}")

    # Entrar a /comparar desde el menú, sin ?appids=, no puede borrar lo elegido: la
    # selección vive en el navegador y la URL sin parámetro no dice nada.
    _abrir(pagina, f"{url.rstrip('/')}/comparar")
    pagina.get_by_test_id("comparar-conteo").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.wait_for_timeout(600)
    quedan = pagina.get_by_test_id("comparar-columnas").locator("[data-testid='columna-comparar']").count()
    if quedan != 2:
        problemas.append(f"entrar a /comparar sin ?appids= dejó {quedan} juegos en vez de 2")
    else:
        print("directa:  entrar sin ?appids= conserva la selección y la vuelve a poner en la URL")

    # Y se puede agregar otro sin salir de la vista.
    pagina.get_by_test_id("abrir-agregar").click()
    pagina.wait_for_timeout(400)
    if pagina.evaluate("() => document.activeElement?.dataset?.testid") != "filtro-texto":
        problemas.append("'+ Agregar juego' no deja el foco en el campo de búsqueda")
    pagina.keyboard.type("portal")
    pagina.wait_for_timeout(600)
    pagina.locator("[data-testid='sugerencias'] li").first.dispatch_event("mousedown")
    pagina.wait_for_timeout(900)
    if pagina.get_by_test_id("comparar-columnas").locator("[data-testid='columna-comparar']").count() != 3:
        problemas.append("agregar un juego desde '+ Agregar juego' no lo suma a la comparación")
    else:
        print("comparar: '+ Agregar juego' busca y agrega sin salir de la vista")

    # El estado vacío es el de una bandeja vacía de verdad: la selección se guarda en el
    # navegador, así que quitar los juegos es lo que lo enseña, no cambiar de URL.
    for _ in range(MAXIMO := 4):
        quitar = pagina.get_by_test_id("quitar-comparar")
        if not quitar.count():
            break
        quitar.first.click()
        pagina.wait_for_timeout(300)
    try:
        pagina.get_by_test_id("comparar-vacio").wait_for(state="visible", timeout=_TIMEOUT_MS)
        print("vacío:    al quitar el último juego, /comparar explica cómo elegir otros")
    except TiempoAgotado:
        problemas.append("al quitar todos los juegos, /comparar no muestra el estado vacío")
    return problemas


def _linea_steam(fila: dict) -> str:
    """Replica dominio/critica.ts: «Steam 94 % positivas (87,051 reseñas)». Redondea como
    Math.round de JavaScript (Python redondea al par)."""
    porcentaje = math.floor(100 * fila["positivas_en_steam"] / fila["resenas_en_steam"] + 0.5)
    return f"Steam {porcentaje} % positivas ({fila['resenas_en_steam']:,} reseñas)"


def _angular_6d(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Fase 6D: la nota de Comparar siempre a la vista, la crítica con Metacritic y Steam
    (o sin Metacritic, lo dice), el bloque «Crítica y público» con su advertencia y sin
    colores de riesgo, y el mismo bloque en la ficha técnica de los juegos sin Metacritic."""
    problemas = []
    base = url.rstrip("/")
    catalogo = {j["appid"]: j for j in _catalogo_api(api)}
    with urllib.request.urlopen(f"{api}/panorama", timeout=10) as respuesta:
        panorama = {f["appid"]: f for f in json.load(respuesta)["por_juego"]}
    sin, con = 2358720, 271590  # Black Myth: Wukong (sin Metacritic) y GTA V (con)
    if catalogo[sin]["metacritic"] is not None or catalogo[con]["metacritic"] is None:
        return ["los juegos de prueba de la 6D cambiaron de Metacritic en la API"]

    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/comparar")
        otra.get_by_test_id("comparar-nota").wait_for(state="visible", timeout=_TIMEOUT_MS)
        vacia = " ".join(otra.get_by_test_id("comparar-nota").inner_text().split())
        _abrir(otra, f"{base}/comparar?appids={sin},{con}")
        otra.get_by_test_id("tabla-comparar").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.get_by_test_id("critica-publico").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(800)
        llena = otra.get_by_test_id("comparar-nota").count()
        # inner_text devuelve el texto ya en mayúsculas (text-transform): se compara sin ellas.
        if "compara hasta 4 juegos lado a lado" not in vacia.lower() or not llena:
            problemas.append("la nota «Compara hasta 4 juegos lado a lado» no se ve antes y después de elegir")
        celdas = [" ".join(c.split()) for c in otra.locator("[data-testid=fila-critica] td").all_inner_texts()]
        esperadas = [
            f"Sin crítica especializada · {_linea_steam(panorama[sin])}",
            f"Metacritic {catalogo[con]['metacritic']} · {_linea_steam(panorama[con])}",
        ]
        if celdas != esperadas:
            problemas.append(f"la fila de crítica no dice lo acordado ({celdas} en vez de {esperadas})")
        advertencia = " ".join(otra.locator(f"[data-testid=columna-comparar][data-appid='{sin}'] [data-testid=critica-advertencia]").inner_text().split())
        esperada = f"Sin crítica especializada; esto viene de {panorama[sin]['resenas_en_steam']:,} reseñas de jugadores."
        if advertencia != esperada:
            problemas.append(f"el bloque «Crítica y público» no trae la advertencia ('{advertencia}')")
        # El porcentaje de Steam nunca va en los colores del riesgo.
        colores = otra.evaluate("""() => {
            const probar = (valor) => { const d = document.createElement('div'); d.style.color = valor; document.body.appendChild(d);
                const c = getComputedStyle(d).color; d.remove(); return c; };
            const riesgo = ['bajo', 'medio', 'alto'].flatMap(n => [probar(`var(--banda-${n})`), probar(`var(--banda-${n}-texto)`)]);
            const usados = [...document.querySelectorAll('[data-testid=critica-publico] .barra span')].map(b => getComputedStyle(b).backgroundColor)
                .concat([...document.querySelectorAll('[data-testid=critica-porcentaje]')].map(p => getComputedStyle(p).color));
            return usados.filter(c => riesgo.includes(c));
        }""")
        if colores:
            problemas.append(f"el porcentaje de Steam usa colores del riesgo ({colores})")
        otra.get_by_test_id("comparar-columnas").screenshot(path=destino / "comparar-critica.png")
        if not any("crítica" in p or "Steam" in p or "nota «Compara" in p for p in problemas):
            print(f"comparar: la nota se ve antes y después de elegir; crítica «{celdas[0]}» y «{celdas[1]}»; "
                  f"el bloque trae la advertencia y ningún color de riesgo ({(destino / 'comparar-critica.png').relative_to(_RAIZ)})")

        # Ficha técnica: sin Metacritic, el bloque; con Metacritic, la línea doble.
        _abrir(otra, f"{base}/juego/{sin}")
        otra.get_by_test_id("metadatos").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.get_by_test_id("metadatos").get_by_test_id("critica-publico").wait_for(state="visible", timeout=_TIMEOUT_MS)
        fila_sin = " ".join(otra.get_by_test_id("ficha-critica").inner_text().split())
        otra.get_by_test_id("metadatos").screenshot(path=destino / "ficha-tecnica-sin-metacritic.png")
        _abrir(otra, f"{base}/juego/{con}")
        otra.get_by_test_id("metadatos").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(800)
        fila_con = " ".join(otra.get_by_test_id("ficha-critica").inner_text().split())
        bloque_con = otra.get_by_test_id("metadatos").get_by_test_id("critica-publico").count()
        esperada_con = f"Metacritic {catalogo[con]['metacritic']} · {_linea_steam(panorama[con])}"
        if fila_sin != "Sin crítica especializada" or fila_con != esperada_con or bloque_con:
            problemas.append(f"la ficha técnica no quedó como se acordó ('{fila_sin}', '{fila_con}', bloque con Metacritic: {bloque_con})")
        else:
            print(f"ficha:    sin Metacritic, la ficha técnica suma «Crítica y público»; con Metacritic dice «{fila_con}» "
                  f"({(destino / 'ficha-tecnica-sin-metacritic.png').relative_to(_RAIZ)})")
    except TiempoAgotado as error:
        problemas.append(f"la 6D no terminó de cargar: {str(error).splitlines()[0]}")
    finally:
        contexto.close()
    return problemas


_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _rango_de_fechas(desde: str, hasta: str) -> str:
    """Replica rangoDeFechas de dominio/formato.ts: «del 14 al 21 sep 2026»."""
    (a_anio, a_mes, a_dia), (b_anio, b_mes, b_dia) = ([int(x) for x in f[:10].split("-")] for f in (desde, hasta))
    if a_anio != b_anio:
        return f"del {a_dia} {_MESES[a_mes - 1]} {a_anio} al {b_dia} {_MESES[b_mes - 1]} {b_anio}"
    if a_mes != b_mes:
        return f"del {a_dia} {_MESES[a_mes - 1]} al {b_dia} {_MESES[b_mes - 1]} {b_anio}"
    return f"el {a_dia} {_MESES[a_mes - 1]} {a_anio}" if a_dia == b_dia else f"del {a_dia} al {b_dia} {_MESES[b_mes - 1]} {b_anio}"


_RUTAS_DE_LA_APP = ["/", "/explorar", f"/juego/{_APPID_FICHA}", "/nia", "/comparar", "/perfil"]
_MENU = ["nav-inicio", "nav-explorar", "nav-nia", "nav-comparar", "nav-perfil"]


def _cifras_esperadas_del_inicio(catalogo: list[dict], panorama: dict) -> dict:
    """Las cifras de «Antes de pagar, esto importa», contadas aquí con /catalogo y /panorama,
    no copiadas de la página: el titular y las tres barras de cada pestaña (señal y reseñas
    positivas; «Precio» salió por circular), los conteos del histograma de precios (todos y
    solo riesgo alto), cuántos juegos tienen precio conocido y las reseñas de la línea de
    confianza."""
    por_juego = {f["appid"]: f for f in panorama["por_juego"]}
    niveles = ("bajo", "medio", "alto")
    redondo = lambda x: int(x + 0.5)  # como Math.round, no el redondeo bancario de Python

    def senal(banda: str) -> float:
        filas = [por_juego[j["appid"]] for j in catalogo if j["banda_riesgo"] == banda and j["appid"] in por_juego]
        return sum(f["casos_senal"] for f in filas) / sum(f["resenas"] for f in filas)

    def positivas(banda: str) -> float:
        de_la_banda = [j for j in catalogo if j["banda_riesgo"] == banda]
        muy = [j for j in de_la_banda if (por_juego.get(j["appid"]) or {}).get("consenso") in ("Overwhelmingly Positive", "Very Positive")]
        return len(muy) / len(de_la_banda)

    rangos = (
        ("Gratis", lambda j: j["es_gratis"]),
        ("<200", lambda j: 0 <= j["precio_final"] < 200), ("200–400", lambda j: 200 <= j["precio_final"] < 400),
        ("400–600", lambda j: 400 <= j["precio_final"] < 600), ("600–900", lambda j: 600 <= j["precio_final"] < 900),
        ("900+", lambda j: j["precio_final"] >= 900),
    )

    def conteos(banda: str | None) -> list[str]:
        salida = []
        for etiqueta, cabe in rangos:
            juegos = [j for j in catalogo if (banda is None or j["banda_riesgo"] == banda)
                      and (j["es_gratis"] if etiqueta == "Gratis" else (not j["es_gratis"] and j["precio_final"] is not None and cabe(j)))]
            salida.append(f"{etiqueta}={len(juegos)}")
        return salida

    return {
        "senal": (f"{senal('alto') / senal('bajo'):.1f}×", [f"{senal(b) * 100:.2f}%" for b in niveles]),
        "positivas": (f"{redondo(positivas('alto') * 100)}%", [f"{redondo(positivas(b) * 100)}%" for b in niveles]),
        "histograma": conteos(None),
        "histograma_alto": conteos("alto"),
        "con_precio": sum(1 for j in catalogo if j["es_gratis"] or j["precio_final"] is not None),
        "resenas": f"{panorama['resenas_descargadas']:,}",
    }


def _medir_inicio(navegador, url: str) -> dict:
    """Alto del documento y palabras del Inicio en los tres anchos, como la medida de antes."""
    medidas = {}
    for ancho, alto in ((1440, 900), (1024, 1366), (390, 844)):
        contexto = navegador.new_context(viewport={"width": ancho, "height": alto}, reduced_motion="reduce")
        _sin_consultas_a_nia(contexto)
        contexto.add_init_script("localStorage.setItem('nexplay.tema.v1', 'oscuro')")
        try:
            otra = contexto.new_page()
            _abrir(otra, url)
            otra.get_by_test_id("antes-de-pagar").wait_for(state="visible", timeout=_TIMEOUT_MS)
            otra.wait_for_timeout(1200)
            medidas[str(ancho)] = otra.evaluate("""() => {
                const palabras = (el) => el ? el.innerText.split(/\\s+/).filter(Boolean).length : 0;
                return {
                    alto_documento: document.scrollingElement.scrollHeight,
                    alto_contenido: Math.round(document.querySelector('main.contenido').getBoundingClientRect().height),
                    palabras_contenido: palabras(document.querySelector('main.contenido')),
                    palabras_pie: palabras(document.querySelector('footer.pie')),
                };
            }""")
        finally:
            contexto.close()
    return medidas


def _angular_5_vistas(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """La reorganización a cinco vistas: el menú, el Inicio con cifras de la API, el panel de
    metodología del pie en cualquier vista, las tres redirecciones y «Tu actividad» en Perfil."""
    problemas = []
    base = url.rstrip("/")
    catalogo = _catalogo_api(api)
    with urllib.request.urlopen(f"{api}/panorama", timeout=10) as respuesta:
        panorama = json.load(respuesta)
    esperado = _cifras_esperadas_del_inicio(catalogo, panorama)
    descargas = panorama["descargas"]
    desde = min(descargas["appdetails"]["desde"], descargas["appreviews"]["desde"])
    hasta = max(descargas["appdetails"]["hasta"], descargas["appreviews"]["hasta"])
    esperada_pie = f"Fuentes: Steam (appreviews y appdetails) y Metacritic, descargadas {_rango_de_fechas(desde, hasta)}."

    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    contexto.add_init_script("localStorage.setItem('nexplay.tema.v1', 'oscuro')")
    try:
        otra = contexto.new_page()
        # El menú: cinco entradas, en el orden de la exposición.
        _abrir(otra, f"{base}/")
        otra.get_by_test_id("antes-de-pagar").wait_for(state="visible", timeout=_TIMEOUT_MS)
        menu = otra.locator("app-barra-lateral nav a.item").evaluate_all("as => as.map(a => a.dataset.testid)")
        if menu != _MENU:
            problemas.append(f"el menú no son las cinco vistas en orden ({menu})")

        # «Antes de pagar, esto importa»: cada pestaña (titular y tres barras), el histograma
        # de precios (todos y solo riesgo alto) y la línea de confianza, contra la API.
        n_antes = len(problemas)
        seccion = otra.get_by_test_id("antes-de-pagar")
        seccion.scroll_into_view_if_needed()
        vistas = []
        pestanas = otra.locator("[data-testid=antes-pestana]").evaluate_all("ps => ps.map(p => p.dataset.metrica)")
        if pestanas != ["senal", "positivas"]:
            problemas.append(f"«Antes de pagar» tiene las pestañas {pestanas}, y «Precio» debía salir")
        for metrica in ("senal", "positivas"):
            otra.locator(f"[data-testid=antes-pestana][data-metrica={metrica}]").click()
            otra.wait_for_timeout(900)
            cifra = otra.get_by_test_id("antes-cifra").inner_text().strip()
            barras = [t.strip() for t in otra.locator("[data-testid=antes-barras] .valor").all_inner_texts()]
            if (cifra, barras) != (esperado[metrica][0], esperado[metrica][1]):
                problemas.append(f"la pestaña {metrica} dice {cifra} {barras} y la API da {esperado[metrica][0]} {esperado[metrica][1]}")
            vistas.append(f"{metrica} {cifra} {' / '.join(barras)}")
        columnas = otra.get_by_test_id("histograma-columna")
        leer = "cs => cs.map(c => c.dataset.rango + '=' + c.dataset.cuantos)"
        if columnas.evaluate_all(leer) != esperado["histograma"]:
            problemas.append(f"el histograma dice {columnas.evaluate_all(leer)} y /catalogo da {esperado['histograma']}")
        otra.locator("[data-testid=histograma-nivel][data-nivel=alto]").click()
        otra.wait_for_timeout(900)
        if columnas.evaluate_all(leer) != esperado["histograma_alto"]:
            problemas.append(f"con «Alto», el histograma dice {columnas.evaluate_all(leer)} y /catalogo da {esperado['histograma_alto']}")
        otra.locator("[data-testid=histograma-nivel][data-nivel=todos]").click()
        nota = " ".join(otra.get_by_test_id("histograma-nota").inner_text().split())
        if not nota.startswith(f"{esperado['con_precio']} juegos con precio conocido"):
            problemas.append(f"la nota del histograma dice «{nota}» y /catalogo da {esperado['con_precio']} con precio conocido")
        if otra.get_by_test_id("antes-metodologia").count():
            problemas.append("«Antes de pagar» repite «Ver metodología», que ya está en el pie")
        confianza = " ".join(otra.get_by_test_id("antes-confianza").inner_text().split())
        if f"{esperado['resenas']} reseñas de Steam" not in confianza or "sin leer las reseñas" not in confianza:
            problemas.append(f"la línea de confianza no dice las reseñas de /panorama o que el riesgo no lee reseñas ('{confianza}')")
        for quitado in ("inicio-hallazgos", "inicio-como-lo-sabemos", "inicio-origenes", "cadena-datos", "inicio-fuentes"):
            if otra.get_by_test_id(quitado).count():
                problemas.append(f"el Inicio todavía muestra {quitado}")
        otra.screenshot(path=destino / "inicio-5-vistas.png", full_page=True)
        seccion.screenshot(path=destino / "inicio-antes-de-pagar.png")
        if len(problemas) == n_antes:
            print(f"inicio:   «Antes de pagar»: {' · '.join(vistas)}; histograma {' '.join(esperado['histograma'])} "
                  f"(alto {' '.join(esperado['histograma_alto'])}), {esperado['con_precio']} con precio conocido: "
                  f"igual que /catalogo y /panorama; sin «Precio» ni «Ver metodología» repetido "
                  f"({(destino / 'inicio-antes-de-pagar.png').relative_to(_RAIZ)})")

        # El pie: «Ver metodología» despliega metodología y fuentes sin cambiar de vista.
        n_antes = len(problemas)
        boton = otra.locator("footer [data-testid=pie-ver-metodologia]")
        boton.click()
        panel = otra.locator("footer #metodologia")
        panel.get_by_test_id("fuentes").wait_for(state="visible", timeout=_TIMEOUT_MS)
        tercios = " ".join(panel.get_by_test_id("metodologia-tercios").inner_text().split())
        enlaces = panel.get_by_test_id("fuente").locator("a").evaluate_all("as => as.map(a => a.href)")
        if boton.get_attribute("aria-expanded") != "true" or otra.url.rstrip("/") != base:
            problemas.append(f"«Ver metodología» no abrió el panel en la misma vista ({otra.url})")
        if tercios != "Los niveles bajo/medio/alto son tercios del score del modelo.":
            problemas.append(f"el panel no trae la línea de los tercios ('{tercios}')")
        if len(enlaces) != 3 or not any("getreviews" in e for e in enlaces) or not panel.get_by_test_id("fuente-servicios").count():
            problemas.append("el panel no trae las tres fuentes enlazadas y Servicios")
        panel.screenshot(path=destino / "pie-metodologia.png")
        if len(problemas) == n_antes:
            print(f"pie:      «Ver metodología» abre metodología, tercios, 3 fuentes y Servicios sin cambiar de vista "
                  f"({(destino / 'pie-metodologia.png').relative_to(_RAIZ)})")

        # Las tres rutas que salieron del menú llevan a su ancla, abierta y a la vista.
        n_antes = len(problemas)
        for vieja, destino_url, prueba in (
            ("/panorama", "/#metodologia", "pie-ver-metodologia"),
            ("/como-funciona", "/#metodologia", "pie-ver-metodologia"),
            ("/historial", "/perfil#actividad", "perfil-actividad"),
        ):
            _abrir(otra, f"{base}{vieja}")
            try:
                otra.wait_for_url(f"{base}{destino_url}", timeout=_TIMEOUT_MS)
                otra.wait_for_timeout(900)
            except TiempoAgotado:
                problemas.append(f"{vieja} no llevó a {destino_url} ({otra.url})")
                continue
            if prueba == "pie-ver-metodologia":
                abierto = otra.get_by_test_id(prueba).get_attribute("aria-expanded") == "true"
                caja = otra.locator("footer #metodologia").bounding_box()
            else:
                abierto = otra.get_by_test_id(prueba).evaluate("d => d.open")
                caja = otra.get_by_test_id(prueba).bounding_box()
            # A la vista: entera en pantalla, o empezando en la mitad de arriba si es más alta.
            # Sin el pie (solo va en el inicio), Perfil ya no da para subir «Tu actividad»
            # hasta arriba, y entera abajo también se lee.
            alto = otra.viewport_size["height"]
            a_la_vista = bool(caja) and caja["y"] >= -2 and (caja["y"] + caja["height"] <= alto + 2 or caja["y"] <= alto / 2)
            if not abierto or not a_la_vista:
                problemas.append(f"{vieja} llegó a {destino_url} pero la sección no quedó abierta y a la vista ({caja})")
        otra.get_by_test_id("perfil-actividad").screenshot(path=destino / "perfil-actividad.png")
        if len(problemas) == n_antes:
            print("rutas:    /panorama y /como-funciona → /#metodologia con el panel abierto; /historial → /perfil#actividad "
                  f"con «Tu actividad» abierta ({(destino / 'perfil-actividad.png').relative_to(_RAIZ)})")

        # La ficha ya no tiene pie: «Cómo calculamos esta estimación» lleva al inicio con el
        # panel de metodología abierto.
        _abrir(otra, f"{base}/juego/{_APPID_FICHA}")
        otra.get_by_test_id("factores-como-calculamos").click()
        try:
            otra.wait_for_url(f"{base}/#metodologia", timeout=_TIMEOUT_MS)
            otra.wait_for_timeout(900)
            abierto = otra.get_by_test_id("pie-ver-metodologia").get_attribute("aria-expanded") == "true"
        except TiempoAgotado:
            abierto = False
        if not abierto:
            problemas.append(f"«Cómo calculamos esta estimación» no lleva al panel de metodología abierto ({otra.url})")
        else:
            print("ficha:    «Cómo calculamos esta estimación» lleva a /#metodologia con el panel abierto")

        # El pie, con la línea de fuentes y «Ver metodología», solo en el inicio: en las otras
        # vistas y en la ficha no hay pie.
        n_antes = len(problemas)
        for ruta in _RUTAS_DE_LA_APP:
            _abrir(otra, f"{base}{ruta}")
            if ruta != "/":
                otra.wait_for_timeout(900)
                if otra.locator("footer").count():
                    problemas.append(f"{ruta}: todavía trae el pie, que va solo en el inicio")
                continue
            linea = otra.locator("footer [data-testid=pie-linea]")
            try:
                otra.wait_for_function(
                    "() => document.querySelector('footer [data-testid=pie-linea]')?.innerText.includes('descargadas')",
                    timeout=_TIMEOUT_MS,
                )
            except TiempoAgotado:
                pass
            texto = " ".join(linea.inner_text().split())
            if texto != esperada_pie:
                problemas.append(f"{ruta}: el pie dice «{texto}» y no «{esperada_pie}»")
            if not otra.locator("footer [data-testid=pie-ver-metodologia]").count():
                problemas.append("el pie del inicio no trae «Ver metodología»")
        if len(problemas) == n_antes:
            print(f"pie:      «{esperada_pie}» y «Ver metodología» solo en el inicio; las otras vistas y la ficha, sin pie")
    except TiempoAgotado as error:
        problemas.append(f"la reorganización no terminó de cargar: {str(error).splitlines()[0]}")
    finally:
        contexto.close()

    # Alto y palabras del Inicio, contra la medida de antes de reorganizar.
    medidas = _medir_inicio(pagina.context.browser, f"{base}/")
    REGISTROS = _RAIZ / "registros"
    REGISTROS.mkdir(exist_ok=True)
    (REGISTROS / "inicio-despues.json").write_text(json.dumps(medidas, indent=2))
    antes_ruta = REGISTROS / "inicio-antes.json"
    antes = json.loads(antes_ruta.read_text()) if antes_ruta.exists() else {}
    for ancho, despues in medidas.items():
        previo = antes.get(ancho)
        comparado = (
            f" (antes {previo['alto_documento']:,} px y {previo['palabras_contenido']} palabras)" if previo else ""
        )
        print(f"medida:   Inicio a {ancho}: {despues['alto_documento']:,} px y {despues['palabras_contenido']} palabras{comparado}")
    return problemas


def _preguntar_en_chat(pagina: Page, pregunta: str) -> None:
    pagina.get_by_test_id("nia-pregunta").fill(pregunta)
    pagina.get_by_test_id("nia-enviar").click()
    pagina.wait_for_function(
        "() => !document.querySelector(\"[data-testid='nia-escribiendo']\")", timeout=_TIMEOUT_MS
    )
    pagina.wait_for_timeout(300)


def _angular_6f(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Fase 6F: Nia con letra de lectura, saludo de la ficha, buscador dentro del chat que
    responde la pregunta pendiente, el hilo sin el perfil y sugerencias rotuladas con su
    riesgo. Lo que antes era el globito de la burbuja es la franja de cada vista
    (_angular_franja_nia)."""
    problemas = []
    base = url.rstrip("/")
    catalogo = {j["appid"]: j for j in _catalogo_api(api)}
    hades = catalogo[1145360]

    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    try:
        otra = contexto.new_page()
        # Ficha: el primer mensaje del chat es el de ese juego, con su riesgo.
        _abrir(otra, f"{base}/juego/{hades['appid']}")
        otra.get_by_test_id("nia-bienvenida").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_function(
            "() => document.querySelector(\"[data-testid='nia-bienvenida']\")?.innerText.includes('Hades')",
            timeout=_TIMEOUT_MS,
        )
        saludo = " ".join(otra.get_by_test_id("nia-bienvenida").locator(".texto").inner_text().split())
        esperado = f"¿Te explico por qué {hades['nombre']} tiene riesgo {hades['banda_riesgo']}? 🙂"
        fichas = [f.strip() for f in otra.get_by_test_id("sugerencia-nia").all_inner_texts()]
        letra = otra.get_by_test_id("nia-bienvenida").locator(".texto").evaluate("e => getComputedStyle(e).fontSize")
        if saludo != esperado or "Sí, explícamelo" not in fichas:
            problemas.append(f"la ficha no abre el chat con su mensaje contextual ('{saludo}', {fichas})")
        if letra != "17px":
            problemas.append(f"la letra del chat mide {letra} y no 17px")

        # /nia sin juego: «¿Por qué tiene ese riesgo?» pide el juego con el buscador; al
        # elegir, la pregunta se responde con ese appid sin repetirla ni borrar el hilo.
        n_antes = len(problemas)
        _abrir(otra, f"{base}/nia")
        otra.get_by_test_id("nia-pregunta").wait_for(state="visible", timeout=_TIMEOUT_MS)
        antes = len(_NIA_CUERPOS)
        _preguntar_en_chat(otra, "¿Qué juegos de acción tienen riesgo bajo?")
        _preguntar_en_chat(otra, "¿Por qué tiene ese riesgo?")
        pide = otra.locator(".mensaje.pide-juego")
        try:
            pide.wait_for(state="visible", timeout=_TIMEOUT_MS)
            borde = pide.evaluate("e => getComputedStyle(e).borderTopStyle")
            otra.get_by_test_id("nia-elegir-buscar").fill("hades")
            otra.get_by_test_id("nia-elegir-resultado").first.click()
            otra.wait_for_function(
                "() => !document.querySelector(\"[data-testid='nia-escribiendo']\")", timeout=_TIMEOUT_MS
            )
            otra.wait_for_timeout(400)
            pide.screenshot(path=destino / "nia-pide-juego.png")
        except TiempoAgotado:
            borde = ""
            problemas.append("sin juego, «¿Por qué tiene ese riesgo?» no pintó el buscador en el chat")
        enviados = _NIA_CUERPOS[antes:]
        if borde != "dashed":
            problemas.append(f"el mensaje que pide el juego no lleva contorno punteado ({borde})")
        if len(enviados) < 3 or enviados[-1].get("appid") != hades["appid"]:
            problemas.append("al elegir el juego, la pregunta pendiente no se reenvió con su appid")
        else:
            ultimo = enviados[-1]["mensajes"]
            preguntas = [m["contenido"] for m in ultimo if m["rol"] == "usuario"]
            if preguntas.count("¿Por qué tiene ese riesgo?") != 1 or ultimo[-1]["contenido"] != "¿Por qué tiene ese riesgo?":
                problemas.append(f"la pregunta reenviada no es la pendiente o va repetida ({preguntas})")
            if len(enviados[1]["mensajes"]) != 3:
                problemas.append(f"la segunda pregunta no llevó el hilo ({len(enviados[1]['mensajes'])} mensajes)")
            # Con el juego ya elegido la pendiente viaja sola: el hilo de antes («los de
            # acción…») hacía que Nia volviera a preguntar de cuál se hablaba.
            if len(ultimo) != 1:
                problemas.append(f"al elegir el juego, la pregunta pendiente viajó con el hilo anterior ({len(ultimo)} mensajes)")
        if any("perfil" in cuerpo for cuerpo in enviados):
            problemas.append("/nia todavía recibe el perfil")
        if "appid=1145360" not in otra.url or not otra.get_by_test_id("nia-juego").count():
            problemas.append(f"la página no reflejó el juego elegido en el chat ({otra.url})")
        if otra.locator("[data-testid='mensaje-usuario']").count() != 2:
            problemas.append("elegir el juego borró o duplicó la conversación")
        if len(problemas) == n_antes:
            print(f"nia:      sin juego pide uno con contorno punteado; al elegir Hades la pregunta viaja con su appid, "
                  f"una sola vez, sin el hilo anterior y sin perfil ({(destino / 'nia-pide-juego.png').relative_to(_RAIZ)})")
    except TiempoAgotado as error:
        problemas.append(f"la 6F no terminó de cargar: {str(error).splitlines()[0]}")
    finally:
        contexto.close()

    # Con perfil: «¿Qué me recomiendas?» manda solo la lista calculada y pinta sus tarjetas.
    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    contexto.add_init_script(
        f"localStorage.setItem('nexplay.perfil.v3', {json.dumps(json.dumps(_PERFIL_EN_LA_BARRA))})"
    )
    try:
        otra = contexto.new_page()
        n_antes = len(problemas)
        _abrir(otra, f"{base}/nia")
        otra.get_by_test_id("nia-pregunta").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(800)
        antes = len(_NIA_CUERPOS)
        _preguntar_en_chat(otra, "¿Qué me recomiendas?")
        cuerpo = _NIA_CUERPOS[antes] if len(_NIA_CUERPOS) > antes else {}
        lista = cuerpo.get("sugerencias", [])
        if not lista or any(set(s) != {"appid", "razones"} for s in lista) or "perfil" in cuerpo:
            problemas.append(f"con perfil, /nia no recibe solo la lista de sugerencias ({list(cuerpo)})")
        tarjetas = otra.get_by_test_id("nia-sugerencia")
        try:
            tarjetas.first.wait_for(state="visible", timeout=_TIMEOUT_MS)
            rotulos = tarjetas.all_inner_texts()
            con_pildora = tarjetas.locator("app-pildora-banda").count()
            if not all("Sugerencia según tu perfil" in r for r in rotulos) or con_pildora != len(rotulos):
                problemas.append("las tarjetas de sugerencia no llevan su rótulo y su riesgo")
            tarjetas.first.locator("xpath=ancestor::li[@data-testid='mensaje-nia']").screenshot(
                path=destino / "nia-sugerencias.png"
            )
        except TiempoAgotado:
            problemas.append("«¿Qué me recomiendas?» con perfil no pintó tarjetas de sugerencia")
        if len(problemas) == n_antes:
            print(f"nia:      con perfil viaja la lista ({len(lista)} juegos con su porqué, sin el perfil) y se pintan "
                  f"{len(rotulos)} tarjetas «Sugerencia según tu perfil» con su riesgo "
                  f"({(destino / 'nia-sugerencias.png').relative_to(_RAIZ)})")
    except TiempoAgotado as error:
        problemas.append(f"la 6F (sugerencias) no terminó de cargar: {str(error).splitlines()[0]}")
    finally:
        contexto.close()

    return problemas


def _angular_nia_flotante(pagina: Page, url: str, destino: Path) -> list[str]:
    """La burbuja de la esquina: grande, saluda al abrirse y conversa sin pedir antes el
    juego; si hace falta uno, lo pide dentro del chat."""
    problemas = []

    _abrir(pagina, _explorar(url))
    burbuja = pagina.get_by_test_id("nia-flotante-burbuja")
    burbuja.wait_for(state="visible", timeout=_TIMEOUT_MS)
    caja = burbuja.bounding_box()
    if not caja or round(caja["width"]) != 84:
        problemas.append(f"la burbuja mide {caja and round(caja['width'])} px y no 84")
    burbuja.click()
    pagina.get_by_test_id("nia-flotante-panel").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("nia").wait_for(state="visible", timeout=_TIMEOUT_MS)
    saludo = " ".join(pagina.get_by_test_id("nia-bienvenida").inner_text().split())
    if "¿Qué juego estás viendo?" not in saludo:
        problemas.append(f"al abrirla, la burbuja no saluda como se acordó ('{saludo}')")
    _esperar_quietud(pagina)
    ruta = destino / "nia-flotante-saludo.png"
    pagina.get_by_test_id("nia-flotante-panel").screenshot(path=ruta)
    print(f"burbuja:  mide {caja and round(caja['width'])} px y saluda «{saludo}» ({ruta.relative_to(_RAIZ)})")

    # «Hablar de un juego» abre el buscador dentro del chat; al elegir, se fija el juego.
    pagina.get_by_test_id("sugerencia-nia").filter(has_text="Hablar de un juego").click()
    pagina.get_by_test_id("nia-elegir-buscar").fill("wild hearts")
    pagina.wait_for_function(
        "() => document.querySelectorAll(\"[data-testid='nia-elegir-resultado']\").length === 1",
        timeout=_TIMEOUT_MS,
    )
    pagina.get_by_test_id("nia-elegir-resultado").first.click()
    try:
        pagina.get_by_test_id("nia-hablando").wait_for(state="visible", timeout=_TIMEOUT_MS)
        elegido = pagina.get_by_test_id("nia-hablando").inner_text()
    except TiempoAgotado:
        elegido = ""
    if "WILD HEARTS" not in elegido.upper():
        problemas.append(f"el buscador del chat no fijó el juego elegido ('{elegido}')")

    antes = len(_NIA_CUERPOS)
    pagina.get_by_test_id("sugerencia-nia").first.click()
    try:
        pagina.get_by_test_id("mensaje-nia").last.wait_for(state="visible", timeout=_TIMEOUT_MS)
        pagina.wait_for_function(
            "() => !document.querySelector(\"[data-testid='nia-escribiendo']\")", timeout=_TIMEOUT_MS
        )
    except TiempoAgotado:
        problemas.append("la burbuja no obtuvo respuesta de Nia")
    enviados = _NIA_CUERPOS[antes:]
    if not enviados or enviados[-1].get("appid") != _APPID_FICHA:
        problemas.append("después de elegir el juego, la pregunta no viajó con su appid")
    _esperar_quietud(pagina)
    ruta = destino / "nia-flotante-chat.png"
    pagina.get_by_test_id("nia-flotante-panel").screenshot(path=ruta)
    elegido = " ".join(elegido.replace("Cambiar", "").split())
    print(f"burbuja:  «Hablar de un juego» abre el buscador en el chat y queda «{elegido}» ({ruta.relative_to(_RAIZ)})")
    problemas += _revisar_vocabulario(pagina, "burbuja de Nia")

    # Escape la cierra y devuelve el foco a la burbuja.
    pagina.keyboard.press("Escape")
    try:
        pagina.get_by_test_id("nia-flotante-panel").wait_for(state="detached", timeout=_TIMEOUT_MS)
        enfocada = pagina.evaluate(
            "() => document.activeElement?.getAttribute('data-testid') === 'nia-flotante-burbuja'"
        )
        if not enfocada:
            problemas.append("al cerrar con Escape, el foco no vuelve a la burbuja")
        print("burbuja:  Escape la cierra y el foco vuelve al botón")
    except TiempoAgotado:
        problemas.append("Escape no cierra el panel de la burbuja")

    # En la ficha, Nia ya vive en la columna lateral: ahí la burbuja no debe salir.
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("ficha-nombre").wait_for(state="visible", timeout=_TIMEOUT_MS)
    if pagina.get_by_test_id("nia-flotante-burbuja").count():
        problemas.append("la burbuja aparece en la ficha, donde Nia ya está en la columna")
    else:
        print("burbuja:  no aparece en la ficha, donde Nia ya está en la columna")

    # La burbuja acompaña en todo el sitio; la única excepción es la ficha, donde Nia ya
    # vive en la columna lateral.
    faltan = []
    # En /nia y en la ficha no: ahí ya hay una conversación abierta y la burbuja sería la
    # misma, ofrecida dos veces.
    for ruta_app, donde in (("", "el inicio"), ("/explorar", "el catálogo"), ("/comparar", "comparar"),
                            ("/perfil", "tu perfil")):
        _abrir(pagina, f"{url.rstrip('/')}{ruta_app}")
        pagina.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
        pagina.wait_for_timeout(400)
        if not pagina.get_by_test_id("nia-flotante-burbuja").count():
            faltan.append(donde)
    if faltan:
        problemas.append(f"la burbuja falta en {', '.join(faltan)}")
    else:
        print("burbuja:  en las cuatro vistas que la llevan; ni en la ficha ni en /nia")
    for ruta_app, donde in (("/nia", "la página de Nia"), (f"/juego/{_APPID_FICHA}", "la ficha")):
        _abrir(pagina, f"{url.rstrip('/')}{ruta_app}")
        pagina.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
        pagina.wait_for_timeout(400)
        if pagina.get_by_test_id("nia-flotante-burbuja").count():
            problemas.append(f"la burbuja aparece en {donde}, donde ya hay una conversación")

    # Y no se posa encima de un botón o un enlace: la esquina de abajo a la derecha tiene
    # que quedar libre mientras se recorre el catálogo.
    _abrir(pagina, _explorar(url))
    pagina.get_by_test_id("tarjeta-juego").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    altura = pagina.evaluate("() => document.documentElement.scrollHeight")
    tapados = []
    # De 40 en 40: con saltos de 120 px, un botón de 32 px podía pasar entero entre dos
    # muestras y el control aprobaba por suerte.
    for y in range(0, max(1, altura - _VIEWPORT["height"]), 40):
        pagina.evaluate("y => window.scrollTo(0, y)", y)
        pagina.wait_for_timeout(80)
        tapados += pagina.evaluate(_JS_BAJO_LA_BURBUJA)
    pagina.evaluate("window.scrollTo(0, 0)")
    if tapados:
        problemas.append(f"la burbuja tapa controles del catálogo: {sorted(set(tapados))[:3]}")
    else:
        print("burbuja:  no tapa ningún control del catálogo al recorrerlo")

    _abrir(pagina, _explorar(url))
    pagina.get_by_test_id("nia-flotante-burbuja").wait_for(state="visible", timeout=_TIMEOUT_MS)
    return problemas


def _angular_movimiento(pagina: Page, url: str) -> list[str]:
    """El logo respira, pero se queda quieto si el sistema pide menos movimiento."""
    problemas = []
    navegador = pagina.context.browser
    if navegador is None:
        return ["no se pudo abrir un contexto con prefers-reduced-motion"]

    medir = """() => {
        const img = document.querySelector('.marca .logo');
        return img ? getComputedStyle(img).animationDuration : null;
    }"""

    def segundos(valor: str | None) -> float:
        """'6s' o '1e-05s' a número; la regla de reduced-motion deja 0.01ms, no 0. """
        return float(valor.rstrip("s")) if valor and valor.endswith("s") else 0.0

    normal = pagina.evaluate(medir)
    if segundos(normal) < 1:
        problemas.append(f"el logo no tiene animación en condiciones normales ({normal})")

    contexto = navegador.new_context(viewport=_VIEWPORT, reduced_motion="reduce")
    _sin_consultas_a_nia(contexto)
    try:
        quieta = contexto.new_page()
        _abrir(quieta, url)
        quieta.wait_for_selector(".marca .logo", timeout=_TIMEOUT_MS)
        reducida = quieta.evaluate(medir)
        if segundos(reducida) > 0.05:
            problemas.append(f"con prefers-reduced-motion el logo sigue animándose ({reducida})")
        else:
            print(f"logo:     respira {normal} y queda quieto con prefers-reduced-motion ({reducida})")
    finally:
        contexto.close()
    return problemas


# Cuántas fichas sin descripción se abren para comprobar el respaldo. Son todas
# equivalentes y abrir el catálogo entero alargaría la corrida sin aportar nada.
_MUESTRA_SIN_DESCRIPCION = 5


def _estrellas_marcadas(pagina: Page) -> list[str]:
    """Qué estrellas tienen aria-checked=true (debería haber una o ninguna)."""
    return pagina.locator("[data-testid='estrellas'] [role='radio'][aria-checked='true']").evaluate_all(
        "nodos => nodos.map(n => n.dataset.estrella)"
    )


def _angular_estrellas(pagina: Page, url: str, destino: Path) -> list[str]:
    """La calificación de 1 a 5: radiogroup con teclado y con ratón, y quitarla."""
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    grupo = pagina.get_by_test_id("estrellas")
    grupo.wait_for(state="visible", timeout=_TIMEOUT_MS)
    conteo = pagina.get_by_test_id("valoracion-conteo")

    radios = grupo.locator("[role='radio']")
    if grupo.get_attribute("role") != "radiogroup" or radios.count() != 5:
        problemas.append(f"las estrellas no son un radiogroup de 5 radios ({radios.count()})")
    etiquetas = radios.evaluate_all("nodos => nodos.map(n => n.getAttribute('aria-label'))")
    if etiquetas[2:3] != ["Calificar con 3 de 5 estrellas"]:
        problemas.append(f"aria-label inesperado en la tercera estrella: {etiquetas[2:3]}")
    tabulables = radios.evaluate_all("nodos => nodos.filter(n => n.tabIndex === 0).length")
    if tabulables != 1:
        problemas.append(f"debe entrar una sola estrella al orden de tabulación, entran {tabulables}")

    # Teclado: desde la primera, tres flechas a la derecha dejan el foco en la cuarta con
    # vista previa hasta ahí, y Enter confirma.
    radios.nth(0).focus()
    for _ in range(3):
        pagina.keyboard.press("ArrowRight")
    enfocada = pagina.evaluate("() => document.activeElement?.dataset.estrella")
    # La vista previa se pinta en el siguiente ciclo de detección de cambios: se espera,
    # en vez de leerla en el mismo instante en que termina la tecla.
    try:
        pagina.wait_for_function(
            "() => document.querySelectorAll(\"[data-testid='estrellas'] .previa\").length === 4",
            timeout=5_000,
        )
    except TiempoAgotado:
        pass
    previas = grupo.locator(".previa").count()
    if enfocada != "4" or previas != 4:
        problemas.append(f"con las flechas el foco quedó en {enfocada} y hay {previas} en vista previa (esperaba 4 y 4)")
    pagina.keyboard.press("Enter")
    try:
        pagina.wait_for_function(
            "() => document.querySelector(\"[data-testid='estrellas'] [data-estrella='4']\")"
            "?.getAttribute('aria-checked') === 'true'",
            timeout=_TIMEOUT_MS,
        )
    except TiempoAgotado:
        problemas.append("Enter no confirmó la calificación con teclado")
    if "★" not in conteo.inner_text():
        problemas.append(f"el resumen no muestra el promedio con estrella ('{conteo.inner_text()}')")
    if _estrellas_marcadas(pagina) != ["4"]:
        problemas.append(f"aria-checked quedó en {_estrellas_marcadas(pagina)}, esperaba solo la 4")
    print(f"estrellas: con teclado, flechas + Enter → 4 · '{conteo.inner_text()}'")

    # Ratón: pasar por encima de la segunda previsualiza dos; el clic confirma.
    radios.nth(1).hover()
    _esperar_quietud(pagina)
    ruta = destino / "estrellas-vista-previa.png"
    pagina.get_by_test_id("valoracion").screenshot(path=ruta)
    radios.nth(1).click()
    try:
        pagina.wait_for_function(
            "() => document.querySelector(\"[data-testid='estrellas'] [data-estrella='2']\")"
            "?.getAttribute('aria-checked') === 'true'",
            timeout=_TIMEOUT_MS,
        )
    except TiempoAgotado:
        problemas.append("el clic en la segunda estrella no cambió la calificación")
    pagina.mouse.move(0, 0)
    _esperar_quietud(pagina)
    ruta_final = destino / "estrellas-calificada.png"
    pagina.get_by_test_id("valoracion").screenshot(path=ruta_final)
    print(f"estrellas: con ratón, clic en la 2 · {ruta.relative_to(_RAIZ)}, {ruta_final.relative_to(_RAIZ)}")

    # Quitarla deja todo como estaba.
    pagina.get_by_test_id("quitar-valoracion").click()
    try:
        pagina.wait_for_function(
            "() => !document.querySelector(\"[data-testid='estrellas'] [aria-checked='true']\")",
            timeout=_TIMEOUT_MS,
        )
        print("estrellas: 'Quitar mi valoración' deja las cinco vacías")
    except TiempoAgotado:
        problemas.append("'Quitar mi valoración' no vació las estrellas")
    return problemas


def _ejemplo_actual(pagina: Page) -> str | None:
    return pagina.get_by_test_id("hero-ejemplo").get_attribute("data-appid")


def _angular_voto_nia(pagina: Page, url: str, destino: Path) -> list[str]:
    """El 👍/👎 de cada respuesta y el aviso de qué se guarda (fase 5b)."""
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("nia-pregunta").wait_for(state="visible", timeout=_TIMEOUT_MS)

    # Sin avisos de entrada: salen dentro de la respuesta que se sale del tema (abajo).
    if pagina.get_by_test_id("nia-aviso-tema").count() or pagina.get_by_test_id("nia-privacidad").count():
        problemas.append("el chat muestra sus avisos antes de que una pregunta se salga del tema")

    if pagina.get_by_test_id("voto-nia").count():
        problemas.append("el voto aparece antes de que Nia haya respondido")

    pagina.get_by_test_id("sugerencia-nia").first.click()
    pagina.get_by_test_id("voto-nia").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    arriba = pagina.get_by_test_id("voto-nia-arriba").first
    abajo = pagina.get_by_test_id("voto-nia-abajo").first

    arriba.click()
    pagina.wait_for_timeout(1200)  # la interfaz agrupa los cambios con ~800 ms de espera
    if arriba.get_attribute("aria-pressed") != "true":
        problemas.append("el 👍 no queda marcado")
    if pagina.get_by_test_id("voto-nia-motivos").count():
        problemas.append("con 👍 aparecen los motivos, que solo tienen sentido con 👎")

    # El mismo pulgar otra vez lo quita.
    arriba.click()
    pagina.wait_for_timeout(1200)
    if arriba.get_attribute("aria-pressed") != "false":
        problemas.append("pulsar el 👍 dos veces no quita el voto")

    abajo.click()
    pagina.get_by_test_id("voto-nia-motivos").wait_for(state="visible", timeout=_TIMEOUT_MS)
    motivos = pagina.get_by_test_id("voto-nia-motivo")
    if motivos.count() != 4:
        problemas.append(f"los motivos del 👎 no son los cuatro de la lista ({motivos.count()})")
    motivos.first.click()
    pagina.wait_for_timeout(1200)
    if motivos.first.get_attribute("aria-pressed") != "true":
        problemas.append("elegir un motivo no lo deja marcado")

    # Probar varios motivos seguidos no puede dejar dos marcados: es lo que pasaba cuando
    # cada clic era una petición y una de ellas fallaba.
    for indice in range(motivos.count()):
        motivos.nth(indice).click()
        pagina.wait_for_timeout(150)
    pagina.wait_for_timeout(1200)
    marcados = [i for i in range(motivos.count()) if motivos.nth(i).get_attribute("aria-pressed") == "true"]
    if len(marcados) > 1:
        problemas.append(f"probar varios motivos deja {len(marcados)} marcados a la vez")
    if pagina.get_by_test_id("voto-nia").inner_text().count("No se pudo"):
        problemas.append("cambiar de motivo varias veces seguidas falla")

    # Y los chips tienen que quedar a la vista, no bajo el borde del hilo.
    caja = pagina.get_by_test_id("voto-nia-motivos").bounding_box()
    hilo = pagina.get_by_test_id("conversacion").bounding_box()
    if caja and hilo and caja["y"] + caja["height"] > hilo["y"] + hilo["height"] + 1:
        problemas.append("los motivos quedan por debajo del borde del hilo")

    ruta = destino / "voto-nia.png"
    pagina.get_by_test_id("nia").screenshot(path=ruta)

    # Una pregunta del catálogo no trae avisos; una que se sale del tema, sí: dentro de la
    # respuesta, con qué se guarda y por cuánto tiempo.
    if pagina.get_by_test_id("nia-aviso-tema").count():
        problemas.append("una pregunta del catálogo trae los avisos de fuera de tema")
    pagina.evaluate(_JS_ESCRIBIR_Y_ENVIAR, "¿Qué clima hace hoy?")
    try:
        pagina.get_by_test_id("nia-aviso-tema").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
        aviso = " ".join(pagina.get_by_test_id("nia-aviso-tema").first.inner_text().split())
        if "datos personales" not in aviso or "180" not in aviso:
            problemas.append(f"el aviso de fuera de tema no dice qué se guarda ni por cuánto ('{aviso[:80]}')")
    except TiempoAgotado:
        problemas.append("una pregunta fuera de tema no trae los avisos")
    if not problemas:
        print(f"voto:     👍/👎 por respuesta y motivos solo con 👎; los avisos (retención de 180 días) solo "
              f"cuando la pregunta se sale del tema ({ruta.relative_to(_RAIZ)})")
    return problemas


# Escribir y pulsar Enter en la misma tarea de JavaScript: lo que pasa al pegar y dar Enter
# de inmediato. Así el control no depende de que la detección de cambios llegue o no a
# pintar lo escrito antes del envío, que era justo la carrera que dejaba el campo lleno.
_JS_ESCRIBIR_Y_ENVIAR = """(texto) => {
  const campo = document.querySelector('[data-testid=nia-pregunta]');
  campo.value = texto;
  campo.dispatchEvent(new Event('input', { bubbles: true }));
  campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
}"""


def _angular_campo_nia(pagina: Page, url: str) -> list[str]:
    """Punto 30 de la fase 6: el campo se vacía al enviar y la segunda pregunta llega sola.
    Antes, si se enviaba antes de que Angular pintara lo escrito, el texto viejo se quedaba
    y la pregunta siguiente llegaba pegada: «uno» y luego «unodos»."""
    problemas = []
    enviados: list[str] = []

    def anotar(peticion) -> None:
        if peticion.method == "POST" and peticion.url.split("?")[0].rstrip("/").endswith("/nia"):
            enviados.append(json.loads(peticion.post_data or "{}")["mensajes"][-1]["contenido"])

    pagina.on("request", anotar)
    try:
        for ruta in ("/nia", f"/juego/{_APPID_FICHA}"):
            enviados.clear()
            _abrir(pagina, f"{url.rstrip('/')}{ruta}")
            campo = pagina.get_by_test_id("nia-pregunta")
            campo.wait_for(state="visible", timeout=_TIMEOUT_MS)
            for pregunta in ("primera pregunta", "segunda pregunta"):
                pagina.evaluate(_JS_ESCRIBIR_Y_ENVIAR, pregunta)
                pagina.wait_for_function(
                    "() => !document.querySelector('[data-testid=nia-pregunta]').disabled", timeout=_TIMEOUT_MS
                )
                if campo.input_value():
                    problemas.append(f"{ruta}: tras enviar «{pregunta}», el campo se queda con «{campo.input_value()}»")
            if enviados != ["primera pregunta", "segunda pregunta"]:
                problemas.append(f"{ruta}: la API recibió {enviados} en vez de las dos preguntas por separado")
    finally:
        pagina.remove_listener("request", anotar)
    if not problemas:
        print("campo:    en /nia y en la ficha, el campo se vacía al enviar y la segunda pregunta llega sola")
    return problemas


def _angular_nia_catalogo(pagina: Page, url: str, destino: Path) -> list[str]:
    """En /nia se puede hablar del catálogo entero sin fijar ningún juego (fase 5a)."""
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/nia")
    pagina.get_by_test_id("nia-pregunta").wait_for(state="visible", timeout=_TIMEOUT_MS)

    if not pagina.get_by_test_id("nia-elegir").count():
        problemas.append("/nia no ofrece elegir un juego")
    # La lista de juegos solo aparece al teclear: 123 al entrar es una columna infinita.
    if pagina.get_by_test_id("nia-sugerencia").count():
        problemas.append("el selector de /nia lista juegos sin que nadie haya escrito nada")
    pagina.get_by_test_id("nia-buscar").fill("hollow")
    try:
        pagina.get_by_test_id("nia-sugerencia").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        problemas.append("el selector de /nia no propone nada al teclear")
    pagina.get_by_test_id("nia-buscar").fill("")
    pagina.wait_for_timeout(300)

    # Y se puede preguntar sin elegir: la API recibe la pregunta sin appid.
    sugerencias = pagina.get_by_test_id("sugerencia-nia")
    if not sugerencias.count():
        return problemas + ["/nia no ofrece preguntas de arranque sin juego elegido"]
    sugerencias.first.click()
    pagina.get_by_test_id("mensaje-nia").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    _esperar_quietud(pagina)
    ruta = destino / "nia-catalogo.png"
    pagina.get_by_test_id("nia-pagina").screenshot(path=ruta)
    if not problemas:
        print(f"catálogo: /nia responde sin juego elegido y propone fijar uno ({ruta.relative_to(_RAIZ)})")
    return problemas


def _angular_carrusel(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """«Análisis crítico con nuestra asistente Nia» en el inicio: los curados de los tres niveles, cada uno con la cara de
    Nia de su nivel, tu pregunta y su opinión, que nombra el mismo riesgo que /catalogo.
    Flechas, pausa y rotación como siempre, y ninguna consulta al chat (POST /nia)."""
    problemas = []
    juegos = _catalogo_api(api)
    niveles = {j["appid"]: j["banda_riesgo"] for j in juegos}
    nombres = {j["appid"]: j["nombre"] for j in juegos}
    pedidas_antes = len(_NIA_PEDIDAS)
    _abrir(pagina, url)
    carrusel = pagina.get_by_test_id("hero-carrusel")
    carrusel.wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("hero-ejemplo").get_by_test_id("hero-respuesta").wait_for(state="visible", timeout=_TIMEOUT_MS)
    etiqueta = pagina.get_by_test_id("hero-etiqueta").inner_text()
    if "Análisis crítico con nuestra asistente Nia" not in etiqueta:
        problemas.append(f"el carrusel perdió su título: {etiqueta!r}")

    # Una vuelta completa con la flecha: qué juegos, qué niveles y qué dice Nia de cada uno.
    pagina.get_by_test_id("hero-siguiente").focus()  # el foco también lo pausa
    vistos: dict[str, str] = {}
    for _ in range(6):
        appid = _ejemplo_actual(pagina)
        diapositiva = pagina.get_by_test_id("hero-ejemplo")
        nivel = niveles.get(int(appid))
        banda = diapositiva.get_by_test_id("pildora-banda").get_attribute("data-banda")
        vistos.setdefault(appid, banda)
        mascota = diapositiva.get_by_test_id("hero-mascota").get_attribute("src") or ""
        pregunta = diapositiva.get_by_test_id("hero-pregunta").inner_text()
        respuesta = diapositiva.get_by_test_id("hero-respuesta")
        texto = respuesta.inner_text() if respuesta.count() else ""
        if banda != nivel:
            problemas.append(f"carrusel {appid}: la píldora dice {banda} y /catalogo {nivel}")
        if not mascota.endswith(f"nia/ficha-{nivel}.png"):
            problemas.append(f"carrusel {appid}: la mascota es {mascota!r}, no la de riesgo {nivel}")
        if nombres.get(int(appid), "?") not in pregunta:
            problemas.append(f"carrusel {appid}: la pregunta no nombra el juego: {pregunta!r}")
        if f"riesgo {nivel}" not in texto:
            problemas.append(f"carrusel {appid}: la opinión de Nia no dice «riesgo {nivel}»: {texto!r}")
        ficha = diapositiva.get_by_test_id("hero-ficha").get_attribute("href")
        seguir = diapositiva.get_by_test_id("hero-seguir-nia").get_attribute("href")
        if ficha != f"/juego/{appid}" or seguir != f"/nia?appid={appid}":
            problemas.append(f"carrusel {appid}: enlaces {ficha!r} y {seguir!r}")
        pagina.get_by_test_id("hero-siguiente").click()
        pagina.wait_for_function(
            "anterior => document.querySelector(\"[data-testid='hero-ejemplo']\")?.dataset.appid !== anterior",
            arg=appid, timeout=_TIMEOUT_MS,
        )
    if set(vistos.values()) != {"bajo", "medio", "alto"}:
        problemas.append(f"el carrusel no cubre los tres niveles: {vistos}")
    print(f"carrusel: {len(vistos)} opiniones de Nia, niveles {sorted(set(vistos.values()))}, "
          "cada una con su mascota y el riesgo de /catalogo")

    antes = _ejemplo_actual(pagina)
    pagina.get_by_test_id("hero-anterior").click()
    pagina.wait_for_function(
        "anterior => document.querySelector(\"[data-testid='hero-ejemplo']\")?.dataset.appid !== anterior",
        arg=antes, timeout=_TIMEOUT_MS,
    )
    _esperar_quietud(pagina)
    ruta = destino / "hero-carrusel.png"
    carrusel.screenshot(path=ruta)
    print(f"carrusel: flechas en ambos sentidos ({ruta.relative_to(_RAIZ)})")

    # Pausa con el ratón encima: pasados 8 s sigue el mismo.
    pagina.get_by_test_id("hero-ejemplo").get_by_test_id("hero-respuesta").hover()
    quieto = _ejemplo_actual(pagina)
    pagina.wait_for_timeout(8500)
    if _ejemplo_actual(pagina) != quieto:
        problemas.append("el carrusel siguió rotando con el ratón encima")

    # Sin ratón ni foco, rota solo en menos de 9 s.
    pagina.mouse.move(5, 5)
    pagina.evaluate("() => document.activeElement?.blur()")
    try:
        pagina.wait_for_function(
            "anterior => document.querySelector(\"[data-testid='hero-ejemplo']\")?.dataset.appid !== anterior",
            arg=quieto, timeout=9500,
        )
        print("carrusel: se pausa con el ratón encima y rota solo cuando se va")
    except TiempoAgotado:
        problemas.append("el carrusel no rota solo sin ratón ni foco")

    # Con prefers-reduced-motion no rota solo.
    navegador = pagina.context.browser
    if navegador is not None:
        contexto = navegador.new_context(viewport=_VIEWPORT, reduced_motion="reduce")
        _sin_consultas_a_nia(contexto)
        try:
            quieta = contexto.new_page()
            _abrir(quieta, url)
            quieta.get_by_test_id("hero-carrusel").wait_for(state="visible", timeout=_TIMEOUT_MS)
            primero = _ejemplo_actual(quieta)
            quieta.wait_for_timeout(8500)
            if _ejemplo_actual(quieta) != primero:
                problemas.append("con prefers-reduced-motion el carrusel rota solo")
            else:
                print("carrusel: con prefers-reduced-motion no rota solo")
        finally:
            contexto.close()
    if len(_NIA_PEDIDAS) != pedidas_antes:
        problemas.append(f"el carrusel consultó al chat {len(_NIA_PEDIDAS) - pedidas_antes} veces")
    else:
        print("carrusel: ninguna consulta al chat (POST /nia); las opiniones salen de GET /nia/opiniones")
    return problemas


def _angular_panel_nia(pagina: Page, url: str, destino: Path) -> list[str]:
    """El chat de la ficha: avatar junto al título y superficie con brillo."""
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    panel = pagina.get_by_test_id("nia")
    panel.wait_for(state="visible", timeout=_TIMEOUT_MS)
    if not pagina.get_by_test_id("nia-avatar").is_visible():
        problemas.append("el panel de Nia de la ficha no muestra el avatar")
    if "destacada" not in (panel.get_attribute("class") or ""):
        problemas.append("el panel de Nia de la ficha no lleva la superficie destacada")
    _esperar_quietud(pagina)
    ruta = destino / "nia-panel-ficha.png"
    panel.screenshot(path=ruta)
    print(f"panel:    Nia en la ficha con avatar y brillo ({ruta.relative_to(_RAIZ)})")
    return problemas


def _estado_video(pagina: Page) -> str | None:
    video = pagina.get_by_test_id("portada-video")
    return video.get_attribute("data-estado") if video.count() else None


def _esperar_video(pagina: Page) -> str | None:
    """Espera a que el tráiler reproduzca o falle; devuelve el estado final."""
    try:
        # Primero que exista: la ficha pinta la cabecera cuando llega el catálogo.
        pagina.get_by_test_id("portada-video").wait_for(state="attached", timeout=_TIMEOUT_MS)
        pagina.wait_for_function(
            "() => { const v = document.querySelector('[data-testid=portada-video]');"
            " return !v || v.dataset.estado !== 'cargando'; }",
            timeout=30_000,
        )
    except TiempoAgotado:
        pass
    return _estado_video(pagina)


def _portada_en_gris(pagina: Page) -> bool:
    filtro = pagina.get_by_test_id("portada-ancha").locator("img").evaluate("i => getComputedStyle(i).filter")
    return "grayscale(1)" in filtro


def _pedir_video_escondido(pagina: Page) -> bool:
    """Si «Ver el tráiler» se esconde con el cursor fuera del video."""
    pagina.mouse.move(0, 0)
    pagina.wait_for_timeout(400)
    return _opacidad(pagina.locator("[data-testid=portada-ancha] .controles")) < 0.95


def _avanza_el_video(pagina: Page) -> bool:
    antes = pagina.get_by_test_id("portada-video").evaluate("v => v.currentTime")
    pagina.wait_for_timeout(1500)
    despues = pagina.get_by_test_id("portada-video").evaluate("v => v.currentTime")
    return despues > antes


def _opacidad(localizador) -> float:
    return float(localizador.evaluate("b => getComputedStyle(b).opacity"))


def _volumen_del_video(pagina: Page) -> float:
    return float(pagina.get_by_test_id("portada-video").evaluate("v => v.volume"))


def _mudo(pagina: Page) -> bool:
    return bool(pagina.get_by_test_id("portada-video").evaluate("v => v.muted"))


def _mover_volumen(pagina: Page, tecla: str, veces: int) -> None:
    pagina.get_by_test_id("portada-volumen").focus()
    for _ in range(veces):
        pagina.keyboard.press(tecla)
    pagina.wait_for_timeout(200)


def _controles_del_video(pagina: Page, destino: Path) -> list[str]:
    """Pausar el tráiler (WCAG 2.2.2) y callar su audio (1.4.2).

    Con cursor, la barra se esconde cuando no está sobre el video (lo pidió el dueño), pero
    se ve los primeros 3 s, en pausa y con el foco dentro: escondida del todo, la revisión
    del usuario final no la encontraba. Con fondo propio y botones de 48 px, y sin «Tráiler ·
    sin sonido»: la corredera de volumen ya dice cómo suena. El tráiler arranca mudo: el
    sonido es siempre una acción de la persona."""
    problemas = []
    controles = pagina.get_by_test_id("portada-controles")
    boton = pagina.get_by_test_id("portada-pausa")
    silenciar = pagina.get_by_test_id("portada-silenciar")
    video = pagina.get_by_test_id("portada-video")
    # Pasados los 3 s del principio y sin cursor encima, la barra se esconde.
    pagina.mouse.move(0, 0)
    pagina.wait_for_timeout(3600)
    sin_cursor = _opacidad(controles)
    caja = pagina.get_by_test_id("portada-ancha").bounding_box()
    pagina.mouse.move(caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2)
    pagina.wait_for_timeout(400)
    con_cursor = _opacidad(controles)
    medidas = boton.bounding_box() or {"width": 0, "height": 0}
    fondo = controles.evaluate("c => getComputedStyle(c).backgroundColor")
    if sin_cursor > 0.05:
        problemas.append(f"sin el cursor encima, los controles del tráiler siguen a la vista (opacidad {sin_cursor})")
    elif con_cursor < 0.95:
        problemas.append(f"con el cursor encima, los controles del tráiler no se ven (opacidad {con_cursor})")
    elif min(medidas["width"], medidas["height"]) < 47.5:
        problemas.append(f"los botones del tráiler miden menos de 48 px ({medidas})")
    elif fondo.startswith("rgba") and float(re.findall(r"[\d.]+", fondo)[3]) < 0.5:
        problemas.append(f"la barra del tráiler no tiene fondo propio ({fondo})")
    elif pagina.get_by_test_id("portada-estado").count():
        problemas.append("la barra del tráiler todavía dice «sin sonido», con el volumen al lado")
    else:
        print("video:    los controles se esconden sin cursor y salen con él; con fondo, de 48 px y sin «sin sonido»")
    pagina.mouse.move(0, 0)

    # Con teclado: foco visible, Enter pausa y el video deja de avanzar.
    # Un Tab antes: el navegador solo pinta :focus-visible si la última interacción fue
    # de teclado, y focus() por script no cuenta como tal.
    pagina.keyboard.press("Tab")
    boton.focus()
    pagina.wait_for_timeout(400)
    ruta = destino / "video-pausa-foco.png"
    pagina.get_by_test_id("portada-ancha").screenshot(path=ruta)
    pagina.keyboard.press("Enter")
    pagina.wait_for_function("() => document.querySelector('[data-testid=portada-video]').dataset.estado === 'pausado'", timeout=_TIMEOUT_MS)
    etiqueta = boton.get_attribute("aria-label")
    quieto = video.evaluate("v => v.paused")
    if not quieto or _avanza_el_video(pagina) or etiqueta != "Reproducir el tráiler":
        problemas.append(f"Enter en el botón no pausa el tráiler (paused={quieto}, etiqueta={etiqueta!r})")
    pagina.locator("body").focus()
    pagina.mouse.move(0, 0)
    pagina.wait_for_timeout(400)
    if _opacidad(controles) < 0.95:
        problemas.append("en pausa y sin cursor, los controles del tráiler se esconden y no hay cómo reanudar")
    boton.focus()
    pagina.keyboard.press("Enter")
    pagina.wait_for_timeout(300)
    if not _avanza_el_video(pagina) or boton.get_attribute("aria-label") != "Pausar el tráiler":
        problemas.append("Enter otra vez no reanuda el tráiler")
    if not problemas:
        print(f"video:    con teclado, Enter pausa y reanuda ({ruta.relative_to(_RAIZ)})")

    # El sonido: arranca mudo, el botón lo activa y la corredera mueve el volumen real.
    problemas += _sonido_del_video(pagina, silenciar)
    pagina.locator("body").focus()
    return problemas


def _caja(localizador) -> tuple[float, float]:
    caja = localizador.bounding_box() or {"x": -1, "y": -1}
    return round(caja["x"], 1), round(caja["y"], 1)


def _sonido_del_video(pagina: Page, silenciar) -> list[str]:
    problemas = []
    pausa = pagina.get_by_test_id("portada-pausa")
    if not _mudo(pagina):
        problemas.append("el tráiler no arranca mudo")

    # Los botones no se mueven al activar el sonido: cuando la corredera se desplegaba,
    # la barra empujaba los dos botones 88 px y el segundo clic caía en la corredera.
    antes_pausa, antes_sonido = _caja(pausa), _caja(silenciar)
    punto = silenciar.bounding_box()
    silenciar.click()
    pagina.wait_for_timeout(300)
    etiqueta = silenciar.get_attribute("aria-label")
    if _mudo(pagina) or etiqueta != "Silenciar el tráiler":
        problemas.append(f"el botón no activa el sonido (mudo={_mudo(pagina)}, etiqueta={etiqueta!r})")
    if _caja(pausa) != antes_pausa or _caja(silenciar) != antes_sonido:
        problemas.append(
            f"los controles se mueven al activar el sonido (pausa {antes_pausa}→{_caja(pausa)},"
            f" sonido {antes_sonido}→{_caja(silenciar)})"
        )

    # Y el mismo punto de la pantalla vuelve a silenciar: es el gesto natural.
    pagina.mouse.click(punto["x"] + punto["width"] / 2, punto["y"] + punto["height"] / 2)
    pagina.wait_for_timeout(300)
    if not _mudo(pagina):
        problemas.append("volver a pulsar en el mismo punto no silencia el tráiler")
    silenciar.click()
    pagina.wait_for_timeout(200)

    antes = _volumen_del_video(pagina)
    _mover_volumen(pagina, "ArrowDown", 4)
    bajado = _volumen_del_video(pagina)
    if bajado >= antes - 0.01:
        problemas.append(f"la corredera no baja el volumen con el teclado ({antes} → {bajado})")

    # Hasta cero: dejar la corredera en el fondo es pedir silencio, no un volumen de cero.
    _mover_volumen(pagina, "ArrowDown", 12)
    if _volumen_del_video(pagina) > 0.001 or not _mudo(pagina):
        problemas.append(f"con la corredera en cero el tráiler no queda mudo (volumen={_volumen_del_video(pagina)})")

    # Se deja como se encontró: el volumen se recuerda entre fichas y las demás vistas del
    # recorrido lo heredarían en cero.
    silenciar.click()
    pagina.wait_for_timeout(200)
    restaurado = _volumen_del_video(pagina)
    if restaurado <= 0 or _mudo(pagina):
        problemas.append(f"activar el sonido con la corredera en cero no sube el volumen ({restaurado})")
    silenciar.click()
    pagina.wait_for_timeout(200)
    if not problemas:
        print(f"video:    arranca mudo; el botón activa el sonido sin mover los controles, el mismo punto vuelve a\n          silenciar y la corredera mueve el volumen ({restaurado:.2f}) y silencia en cero")
    return problemas


_APPID_SIN_VIDEO = 690790  # DiRT Rally 2.0, el único del catálogo sin tráiler


def _portada_del_ancho_del_titulo(pagina: Page) -> list[str]:
    """La portada tiene que abarcar lo mismo que la fila del título y los botones: con
    aspect-ratio más max-height, el techo de alto encogía también el ancho."""
    anchos = pagina.evaluate(
        "() => {"
        " const p = document.querySelector('[data-testid=portada-ancha]');"
        " const t = document.querySelector('.titulos');"
        " return p && t ? [p.getBoundingClientRect().width, t.getBoundingClientRect().width] : null;"
        "}"
    )
    if not anchos:
        return ["no se encontró la portada o la fila del título para medir su ancho"]
    portada, titulo = anchos
    if abs(portada - titulo) > 1:
        return [f"la portada no mide lo mismo que la fila del título ({portada:.0f} contra {titulo:.0f} px)"]
    print(f"ficha:    la portada abarca el mismo ancho que el título y los botones ({portada:.0f} px)")
    return []


def _angular_video(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """El tráiler de la cabecera: nativo o con hls.js, y la portada en gris como respaldo."""
    problemas = []
    base = url.rstrip("/")
    juegos = {j["appid"]: j for j in _catalogo_api(api)}
    con_video = sum(1 for j in juegos.values() if j.get("video_url"))
    print(f"video:    la API trae video_url en {con_video} de {len(juegos)} juegos")
    if not juegos[_APPID_FICHA].get("video_url"):
        return problemas + [f"el juego {_APPID_FICHA} no trae video_url en la API"]

    _abrir(pagina, f"{base}/juego/{_APPID_FICHA}")
    if not _portada_en_gris(pagina):
        problemas.append("la portada de la cabecera no está en escala de grises")
    estado = _esperar_video(pagina)
    via = pagina.get_by_test_id("portada-video").evaluate(
        "v => v.canPlayType('application/vnd.apple.mpegurl') ? 'nativo' : 'hls.js'"
    ) if estado else None
    if estado != "reproduciendo":
        problemas.append(f"el tráiler de la ficha no llegó a reproducir (estado {estado})")
    elif not _avanza_el_video(pagina):
        problemas.append("el tráiler de la ficha está visible pero no avanza")
    else:
        print(f"video:    la ficha reproduce el tráiler con <video> {via}, mudo y en loop")
    problemas += _portada_del_ancho_del_titulo(pagina)
    if estado == "reproduciendo":
        problemas += _controles_del_video(pagina, destino)
    pagina.wait_for_timeout(2500)
    ruta = destino / "video-ficha.png"
    pagina.screenshot(path=ruta)
    ruta_cerca = destino / "video-cabecera.png"
    pagina.get_by_test_id("portada-ancha").screenshot(path=ruta_cerca)
    print(f"video:    capturas {ruta.relative_to(_RAIZ)}, {ruta_cerca.relative_to(_RAIZ)}")

    _abrir(pagina, f"{base}/juego/{_APPID_SIN_VIDEO}")
    pagina.get_by_test_id("portada-ancha").wait_for(timeout=_TIMEOUT_MS)
    if pagina.get_by_test_id("portada-video").count() or not _portada_en_gris(pagina):
        problemas.append("un juego sin tráiler no se queda solo con la portada en gris")
    else:
        print(f"video:    {juegos[_APPID_SIN_VIDEO]['nombre']} (sin tráiler) se queda con la portada en gris")

    # Si el video falla, desaparece y queda la portada.
    pagina.route("**/*.m3u8*", lambda ruta: ruta.abort())
    _abrir(pagina, f"{base}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("portada-ancha").wait_for(timeout=_TIMEOUT_MS)
    try:
        pagina.get_by_test_id("portada-video").wait_for(state="detached", timeout=30_000)
        print("video:    si el tráiler falla, se quita y queda la portada en gris")
    except TiempoAgotado:
        problemas.append(f"con el tráiler caído el video no se quita (estado {_estado_video(pagina)})")
    pagina.unroute("**/*.m3u8*")

    navegador = pagina.context.browser
    # Un navegador sin HLS nativo (Firefox): se finge quitando canPlayType para m3u8.
    contexto = navegador.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    contexto.add_init_script(
        "const original = HTMLMediaElement.prototype.canPlayType;"
        "HTMLMediaElement.prototype.canPlayType = function (tipo) {"
        " return /mpegurl/i.test(tipo) ? '' : original.call(this, tipo); };"
    )
    try:
        otra = contexto.new_page()
        trozos = []
        otra.on("request", lambda r: trozos.append(r.url) if r.url.endswith(".js") else None)
        _abrir(otra, f"{base}/juego/{_APPID_FICHA}")
        estado = _esperar_video(otra)
        if estado != "reproduciendo" or not _avanza_el_video(otra):
            problemas.append(f"sin HLS nativo, hls.js no reproduce el tráiler (estado {estado})")
        else:
            print("video:    sin HLS nativo carga hls.js bajo demanda y reproduce")
    finally:
        contexto.close()

    contexto = navegador.new_context(viewport=_VIEWPORT, reduced_motion="reduce")
    _sin_consultas_a_nia(contexto)
    try:
        otra = contexto.new_page()
        pedidos = []
        otra.on("request", lambda r: pedidos.append(r.url) if "video.akamai" in r.url else None)
        _abrir(otra, f"{base}/juego/{_APPID_FICHA}")
        otra.get_by_test_id("portada-ancha").wait_for(timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(2000)
        if otra.get_by_test_id("portada-video").count() or pedidos:
            problemas.append(f"con prefers-reduced-motion se pide el tráiler ({len(pedidos)} peticiones)")
        elif not _portada_en_gris(otra):
            problemas.append("con prefers-reduced-motion la portada no queda en gris")
        elif not otra.get_by_test_id("portada-pedir-video").count():
            problemas.append("con prefers-reduced-motion no hay botón para ver el tráiler")
        elif _pedir_video_escondido(otra):
            # Sin video corriendo la barra no se esconde: es la única forma de pedirlo.
            problemas.append("con prefers-reduced-motion, «Ver el tráiler» se esconde sin el cursor encima")
        else:
            otra.get_by_test_id("portada-pedir-video").click()
            if _esperar_video(otra) != "reproduciendo":
                problemas.append("con prefers-reduced-motion, «Ver el tráiler» no lo reproduce")
            else:
                print("video:    con prefers-reduced-motion no se pide solo; «Ver el tráiler» lo trae y reproduce")
    finally:
        contexto.close()
    return problemas


def _trailers_esperados(api: str) -> list[int]:
    """Replica dominio/trailers.ts: por nivel, los dos con tráiler más reseñados en Steam."""
    catalogo = _catalogo_api(api)
    try:
        with urllib.request.urlopen(f"{api}/panorama", timeout=10) as respuesta:
            por_juego = {f["appid"]: f for f in json.load(respuesta)["por_juego"]}
    except OSError as exc:
        sys.exit(f"No pude leer {api}/panorama para comparar: {exc}")
    elegidos = []
    for banda in ("bajo", "medio", "alto"):
        del_nivel = [j for j in catalogo if j["banda_riesgo"] == banda and j.get("video_url")]
        del_nivel.sort(key=lambda j: -((por_juego.get(j["appid"]) or {}).get("resenas_en_steam") or -1))
        elegidos += [j["appid"] for j in del_nivel[:2]]
    return elegidos


def _nombre_trailer(pagina: Page) -> str:
    return pagina.get_by_test_id("trailer-nombre").inner_text().strip()


def _terminar_trailer(pagina: Page) -> None:
    """Finge el final del tráiler: esperar uno entero haría la corrida minutos más larga."""
    pagina.locator("[data-testid=trailers] [data-testid=portada-video]").dispatch_event("ended")
    pagina.wait_for_timeout(400)


def _angular_6b(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Fase 6B: el inicio con una sola acción principal, los tráileres de Explorar, las
    tarjetas con el color del riesgo y el resplandor de su portada, y la ficha en bloques."""
    problemas = []
    base = url.rstrip("/")
    catalogo = {j["appid"]: j for j in _catalogo_api(api)}

    # Inicio: una sola acción principal, el buscador a todo lo ancho arriba de «Qué
    # encontramos», y adónde lleva buscar. Antes, «¿Por qué elegir NexPlay?», que lleva a
    # /explorar con el número del catálogo, y las cuatro herramientas con su enlace. Las
    # fuentes enlazadas pasaron al panel del pie (_angular_5_vistas).
    _abrir(pagina, base)
    pagina.get_by_test_id("inicio-buscar").wait_for(state="visible", timeout=_TIMEOUT_MS)
    principales = pagina.locator(".boton-cta:visible")
    if principales.count() != 1 or "Buscar" not in principales.first.inner_text():
        problemas.append(f"el inicio tiene {principales.count()} acciones principales y no solo «Buscar →»")
    pagina.get_by_test_id("inicio-buscar").screenshot(path=destino / "inicio-buscar.png")
    destinos = []
    for escrito, esperado in (("", "/explorar"), ("terraria", "/juego/105600"), ("terra", "/explorar?q=terra")):
        _abrir(pagina, base)
        campo = pagina.get_by_test_id("inicio-buscar").get_by_test_id("filtro-texto")
        campo.wait_for(state="visible", timeout=_TIMEOUT_MS)
        if escrito:
            campo.fill(escrito)
        pagina.get_by_test_id("inicio-buscar-boton").click()
        try:
            pagina.wait_for_url(f"**{esperado}", timeout=_TIMEOUT_MS)
            destinos.append(f"«{escrito}» → {esperado}")
        except TiempoAgotado:
            problemas.append(f"«Buscar →» con «{escrito}» no lleva a {esperado} ({pagina.url})")
    if not problemas:
        print(f"inicio:   una sola acción principal; buscar lleva {', '.join(destinos)}")

    _abrir(pagina, base)
    seccion = pagina.get_by_test_id("inicio-por-que")
    seccion.wait_for(state="visible", timeout=_TIMEOUT_MS)
    seccion.screenshot(path=destino / "inicio-por-que.png")
    accion = " ".join(pagina.get_by_test_id("por-que-explorar").inner_text().split())
    if f"Explorar los {len(catalogo)} juegos" not in accion:
        problemas.append(f"«¿Por qué elegir?» no lleva el número de /catalogo ({len(catalogo)}): {accion!r}")
    esperados = {"motivos": "/juego/1938010", "nia": "/nia", "comparar": "/comparar", "perfil": "/perfil"}
    tarjetas = pagina.get_by_test_id("herramienta-inicio")
    enlaces = {t.get_attribute("data-herramienta"): t.get_attribute("href") for t in tarjetas.all()}
    if enlaces != esperados:
        problemas.append(f"las herramientas del inicio no llevan a su vista: {enlaces}")

    # La nave 🚀 separa la sección del encabezado y, al tocarla, baja hasta ella.
    # El cohete flota sin parar (lo pidió el dueño): un clic forzado, porque Playwright
    # espera a que el botón se quede quieto y nunca lo hace.
    pagina.evaluate("() => window.scrollTo(0, 0)")
    pagina.get_by_test_id("por-que-nave").click(force=True)
    try:
        pagina.wait_for_function(
            "() => { const r = document.querySelector(\"[data-testid='inicio-por-que']\").getBoundingClientRect();"
            " return r.top >= 0 && r.top < 120; }",
            timeout=_TIMEOUT_MS,
        )
        print("inicio:   la nave 🚀 baja a «¿Por qué elegir NexPlay?»")
    except TiempoAgotado:
        problemas.append("la nave no baja a «¿Por qué elegir NexPlay?»")
    pagina.get_by_test_id("por-que-explorar").click()
    try:
        pagina.wait_for_url("**/explorar", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        problemas.append(f"«{accion}» no lleva a /explorar ({pagina.url})")
    if not problemas:
        print(f"inicio:   «¿Por qué elegir NexPlay?» lleva a /explorar («{accion}») y tiene {len(enlaces)} "
              f"herramientas ({', '.join(esperados.values())}) (docs/capturas/angular/inicio-por-que.png)")

    # Tráileres de Explorar.
    esperados = _trailers_esperados(api)
    _abrir(pagina, f"{base}/explorar")
    pagina.mouse.move(0, 0)
    pagina.get_by_test_id("trailers").wait_for(state="visible", timeout=_TIMEOUT_MS)
    nombres = [n.strip() for n in pagina.get_by_test_id("trailer-opcion").locator(".t-nombre").all_inner_texts()]
    if nombres != [catalogo[a]["nombre"] for a in esperados]:
        problemas.append(f"los tráileres no son dos por nivel, los más reseñados ({nombres})")
    estado = _esperar_video(pagina)
    mudo = pagina.locator("[data-testid=trailers] [data-testid=portada-video]").evaluate("v => v.muted")
    if estado != "reproduciendo" or not mudo:
        problemas.append(f"el primer tráiler no arranca solo y mudo (estado {estado}, mudo {mudo})")
    pagina.get_by_test_id("trailers").screenshot(path=destino / "trailers.png")
    avanza = lambda: pagina.get_by_test_id("trailers").get_attribute("data-avanza-solo")
    primero = _nombre_trailer(pagina)
    _terminar_trailer(pagina)
    segundo = _nombre_trailer(pagina)
    if segundo == primero:
        problemas.append("al terminar un tráiler no pasa solo al siguiente")
    pagina.get_by_test_id("trailer-escenario").hover()
    pagina.wait_for_timeout(300)
    quieto_encima = avanza() == "false"
    _terminar_trailer(pagina)
    if not quieto_encima or _nombre_trailer(pagina) != segundo:
        problemas.append("con el cursor encima, los tráileres siguen pasando solos")
    pagina.mouse.move(0, 0)
    pagina.wait_for_timeout(300)
    if avanza() != "true":
        problemas.append("al quitar el cursor, los tráileres no vuelven a pasar solos")
    pagina.get_by_test_id("trailer-opcion").nth(4).click()
    pagina.mouse.move(0, 0)
    pagina.wait_for_timeout(300)
    elegido = pagina.get_by_test_id("trailer-opcion").nth(4).get_attribute("aria-current")
    if elegido != "true" or avanza() != "false":
        problemas.append("tocar un tráiler no lo pone ni deja de pasar solo")
    _esperar_video(pagina)
    trailer_video = pagina.locator("[data-testid=trailers] [data-testid=portada-video]")
    pagina.get_by_test_id("trailers").get_by_test_id("portada-silenciar").click()
    pagina.wait_for_timeout(300)
    con_sonido = not trailer_video.evaluate("v => v.muted")
    pagina.get_by_test_id("trailer-opcion").nth(5).click()
    _esperar_video(pagina)
    siguiente_mudo = trailer_video.evaluate("v => v.muted")
    if not con_sonido or not siguiente_mudo:
        problemas.append(f"el sonido no es solo del tráiler activado (activado {con_sonido}, el siguiente mudo {siguiente_mudo})")
    if not any("tráiler" in p for p in problemas):
        print(f"tráileres: {len(nombres)}, dos por nivel; arrancan mudos y pasan solos; se quedan con el cursor "
              f"encima y dejan de pasar al tocar uno; solo suena el activado ({(destino / 'trailers.png').relative_to(_RAIZ)})")

    # La nave 📚 separa los tráileres de la búsqueda y, al tocarla, baja hasta ella. Clic
    # forzado: flota sin parar y Playwright espera a que se quede quieta.
    pagina.evaluate("() => window.scrollTo(0, 0)")
    pagina.get_by_test_id("catalogo-nave").click(force=True)
    try:
        pagina.wait_for_function(
            "() => { const r = document.querySelector(\"[data-testid='catalogo-busqueda']\").getBoundingClientRect();"
            " return r.top >= 0 && r.top < 120; }",
            timeout=_TIMEOUT_MS,
        )
        print("explorar: la nave 📚 baja a «¿Qué juego estás pensando comprar?» y los géneros")
    except TiempoAgotado:
        problemas.append("la nave 📚 no baja a la búsqueda de Explorar")

    # Los géneros: se eligen varios (basta con tener uno) y elegirlos no sube la página. Se
    # mide dónde queda el botón en pantalla y no scrollY: con un filtro, el contador de
    # arriba ocupa un renglón más y el navegador corre scrollY para que nada se mueva.
    elegir = ("Acción", "Rol")
    esperado = sum(1 for j in catalogo.values() if set(j["generos"]) & set(elegir))
    boton = pagina.locator(f"[data-testid=filtro-genero][data-genero='{elegir[0]}']")
    # La bajada de la nave es suave: se mide con la página ya quieta.
    pagina.wait_for_function(
        "() => { const y = scrollY, quieta = window.__ultimoY === y; window.__ultimoY = y; return quieta; }",
        polling=250, timeout=_TIMEOUT_MS,
    )
    antes = round(boton.bounding_box()["y"])
    for genero in elegir:
        pagina.locator(f"[data-testid=filtro-genero][data-genero='{genero}']").click()
    pagina.wait_for_timeout(600)
    despues = round(boton.bounding_box()["y"])
    prendidos = pagina.locator("[data-testid=filtro-genero][aria-pressed=true]").evaluate_all(
        "bs => bs.map(b => b.dataset.genero)"
    )
    conteo = " ".join(pagina.get_by_test_id("catalogo-conteo").inner_text().split())
    if prendidos != list(elegir) or f"{esperado} de {len(catalogo)}" not in conteo:
        problemas.append(f"elegir {' y '.join(elegir)} deja {prendidos} y «{conteo}» (se esperaban {esperado})")
    elif abs(despues - antes) > 2:
        problemas.append(f"elegir un género mueve los géneros en pantalla de {antes} a {despues} px")
    else:
        print(f"géneros:  {' y '.join(elegir)} a la vez → {conteo}; los géneros no se mueven en pantalla (y = {antes} px)")
    # «Todos» deja el catálogo entero para lo que sigue.
    pagina.locator("[data-testid=filtro-genero][data-genero='']").click()
    pagina.wait_for_timeout(400)

    # Tarjetas: filo del riesgo y resplandor de la portada, siempre visible.
    pagina.get_by_test_id("estante-bajo").scroll_into_view_if_needed()
    pagina.wait_for_timeout(2500)
    tarjetas = pagina.evaluate("""() => [...document.querySelectorAll('app-tarjeta-juego')]
        .filter(t => { const r = t.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0 && r.left < innerWidth && r.right > 0; })
        .map(t => {
            const a = t.querySelector('[data-testid=tarjeta-juego]');
            const probar = document.createElement('div');
            probar.style.color = `var(--banda-${a.dataset.banda}-filo)`;
            t.appendChild(probar);
            const filo = getComputedStyle(probar).color;
            probar.remove();
            return { banda: a.dataset.banda, borde: getComputedStyle(a).borderTopColor, filo,
                     color: getComputedStyle(t).getPropertyValue('--color-portada').trim(),
                     brillo: Number(getComputedStyle(t.querySelector('.resplandor')).opacity) };
        })""")
    sin_color = [x for x in tarjetas if not x["color"]]
    mal_filo = [x for x in tarjetas if x["borde"] != x["filo"]]
    apagadas = [x for x in tarjetas if x["brillo"] < 0.3]
    if not tarjetas or mal_filo or apagadas or len(sin_color) > len(tarjetas) // 2:
        problemas.append(f"tarjetas: {len(mal_filo)} sin el filo de su riesgo, {len(apagadas)} sin resplandor, "
                         f"{len(sin_color)} de {len(tarjetas)} sin color de portada")
    else:
        pagina.get_by_test_id("estante-bajo").screenshot(path=destino / "tarjetas-resplandor.png")
        print(f"tarjetas: {len(tarjetas)} a la vista con el filo de su riesgo y el resplandor de su portada "
              f"({len(tarjetas) - len(sin_color)} con color propio; "
              f"{(destino / 'tarjetas-resplandor.png').relative_to(_RAIZ)})")

    # Con menos movimiento, los tráileres no arrancan ni pasan solos.
    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT, reduced_motion="reduce")
    _sin_consultas_a_nia(contexto)
    try:
        otra = contexto.new_page()
        pedidos = []
        otra.on("request", lambda r: pedidos.append(r.url) if "video.akamai" in r.url else None)
        _abrir(otra, f"{base}/explorar")
        otra.get_by_test_id("trailers").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(1500)
        boton = otra.get_by_test_id("trailers").get_by_test_id("portada-pedir-video")
        if pedidos or not boton.count() or otra.get_by_test_id("trailers").get_attribute("data-avanza-solo") != "false":
            problemas.append(f"con prefers-reduced-motion los tráileres arrancan o pasan solos ({len(pedidos)} peticiones)")
        else:
            print("tráileres: con prefers-reduced-motion no arrancan ni pasan solos; «Ver el tráiler» lo trae")
    finally:
        contexto.close()

    # La ficha en bloques, cada uno con su color; el de perfil, destacado.
    _abrir(pagina, f"{base}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("ficha-veredicto").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("hilo-comentarios").wait_for(state="attached", timeout=_TIMEOUT_MS)
    bloques = pagina.evaluate("""() => ['motivos', 'factores', 'historia-perfil', 'valoracion', 'hilo-comentarios'].map(id => {
        const b = document.querySelector(`[data-testid=${id}]`);
        return { id, bloque: !!b && b.classList.contains('bloque'), seccion: b?.dataset.seccion ?? null,
                 destacado: !!b && b.classList.contains('destacado'),
                 tono: b ? getComputedStyle(b).getPropertyValue('--tono').trim() : '' };
    })""")
    tonos = {b["tono"] for b in bloques}
    if not all(b["bloque"] and b["seccion"] for b in bloques) or len(tonos) != len(bloques):
        problemas.append(f"la ficha no tiene cada sección en su bloque con color propio ({bloques})")
    elif not next(b for b in bloques if b["id"] == "historia-perfil")["destacado"]:
        problemas.append("«Por qué te tocaría a ti» no va destacado")
    else:
        print(f"ficha:    {len(bloques)} secciones en bloque, cada una con su color ({', '.join(b['seccion'] for b in bloques)}); "
              "la de perfil, destacada")
    return problemas


def _angular_como_funciona(pagina: Page, url: str, destino: Path) -> list[str]:
    """Lo que era Cómo funciona vive plegado en el pie: el Inicio no lo repite abierto, el
    panel habla con el vocabulario del proyecto y la ficha enlaza a él sin salir."""
    problemas = []
    base = url.rstrip("/")
    _abrir(pagina, base)
    pagina.get_by_test_id("inicio-por-que").wait_for(state="visible", timeout=_TIMEOUT_MS)
    # Nia ya no saluda desde el pie: en el inicio está su tarjeta y la burbuja.
    if pagina.get_by_test_id("nia-mascota").count():
        problemas.append("el saludo grande de Nia sigue en el inicio, duplicando la burbuja")
    if pagina.locator("footer [data-testid='metodologia']").count():
        problemas.append("el pie abre la metodología sin que nadie la pida")
    pagina.locator("footer [data-testid='pie-ver-metodologia']").click()
    try:
        pagina.locator("footer [data-testid='metodologia']").wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        return problemas + ["«Ver metodología» no despliega la metodología"]
    problemas += _revisar_vocabulario(pagina, "panel de metodología")
    if not any("metodología" in p for p in problemas):
        print("metodología: plegada en el pie y con el vocabulario del proyecto al abrirla")

    # Sin perfil, la ficha ofrece crearlo con una tarjeta de acción del rosa de Tu perfil.
    _abrir(pagina, f"{base}/juego/{_APPID_FICHA}")
    boton = pagina.get_by_test_id("historia-crear-perfil")
    try:
        boton.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        return problemas + ["sin perfil, la ficha no muestra el botón 'Crear tu perfil'"]
    enlace = pagina.get_by_test_id("factores-como-calculamos")
    if not enlace.count() or "#metodologia" not in (enlace.get_attribute("href") or ""):
        problemas.append("'Qué mueve esta estimación' no enlaza al panel de metodología")
    elif not pagina.get_by_test_id("factores").locator("app-factores-modelo").count():
        problemas.append("la sección de factores perdió su contenido al agregar el enlace")
    else:
        print("factores: la sección conserva los factores y enlaza a 'Cómo calculamos esta estimación'")
    clases = boton.get_attribute("class") or ""
    comparar = pagina.get_by_test_id("boton-comparar").get_attribute("class") or ""
    if "tarjeta-accion" not in clases or "compacto" not in comparar:
        problemas.append(f"sin perfil, 'Crear tu perfil' no es tarjeta de acción o 'Comparar' no es compacto ({clases!r}, {comparar!r})")
    ruta = destino / "historia-crear-perfil.png"
    pagina.get_by_test_id("historia-perfil").screenshot(path=ruta)
    boton.click()
    try:
        pagina.get_by_test_id("perfil").wait_for(state="visible", timeout=_TIMEOUT_MS)
        print(f"perfil:   sin perfil, la ficha ofrece 'Crear tu perfil' como tarjeta de acción y lleva a /perfil ({ruta.relative_to(_RAIZ)})")
    except TiempoAgotado:
        problemas.append("'Crear tu perfil' no lleva a /perfil")
    return problemas


def _angular_descripcion(pagina: Page, url: str, api: str) -> list[str]:
    """El párrafo de Steam bajo el nombre: completo en español, o el respaldo discreto."""
    problemas = []

    # Quién tiene descripción en español lo decide la API (api/catalogo.py compara
    # palabras comunes de cada idioma); aquí solo se comprueba que la ficha la respeta.
    catalogo = {j["appid"]: j for j in _catalogo_api(api)}
    sin_texto = [appid for appid, juego in catalogo.items() if juego.get("descripcion") is None]
    if not sin_texto:
        problemas.append("ningún juego cae al respaldo: ¿el filtro de idioma dejó de funcionar?")
    print(f"descripción: la API manda None en {len(sin_texto)} de {len(catalogo)} juegos")

    # Uno en español: el párrafo completo, tal como vino de Steam.
    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("ficha-descripcion").wait_for(state="visible", timeout=_TIMEOUT_MS)
    mostrado = " ".join(pagina.get_by_test_id("ficha-descripcion").inner_text().split())
    esperado = " ".join((catalogo[_APPID_FICHA]["descripcion"] or "").split())
    if mostrado != esperado:
        problemas.append(f"la ficha no muestra la descripción completa ('{mostrado[:80]}')")
    if pagina.get_by_test_id("ficha-sin-descripcion").count():
        problemas.append("con descripción en español, la ficha muestra igual el respaldo")
    print(f"descripción: {catalogo[_APPID_FICHA]['nombre']} muestra {len(mostrado)} caracteres")

    # Una muestra de los que no la tienen: respaldo, y ni rastro del texto original.
    for appid in sorted(sin_texto)[:_MUESTRA_SIN_DESCRIPCION]:
        nombre = catalogo[appid]["nombre"]
        _abrir(pagina, f"{url.rstrip('/')}/juego/{appid}")
        try:
            pagina.get_by_test_id("ficha-sin-descripcion").wait_for(state="visible", timeout=_TIMEOUT_MS)
        except TiempoAgotado:
            problemas.append(f"{nombre}: no cae al mensaje de respaldo")
            continue
        if pagina.get_by_test_id("ficha-descripcion").count():
            problemas.append(f"{nombre}: muestra descripción además del respaldo")
    if not problemas:
        print(f"descripción: los {min(len(sin_texto), _MUESTRA_SIN_DESCRIPCION)} revisados caen al respaldo")

    # "Ver más" solo si el recorte esconde algo: la más larga lo lleva y abre el texto; la
    # más corta cabe en dos líneas y no.
    con_texto = sorted((len(j["descripcion"]), appid) for appid, j in catalogo.items() if j.get("descripcion"))
    corta, larga = con_texto[0][1], con_texto[-1][1]
    _abrir(pagina, f"{url.rstrip('/')}/juego/{larga}")
    pagina.get_by_test_id("ficha-descripcion").wait_for(state="visible", timeout=_TIMEOUT_MS)
    # El veredicto reemplaza a su esqueleto y empuja el botón unos píxeles: se espera a que
    # llegue antes de hacer clic, o el clic cae donde el botón estaba.
    pagina.get_by_test_id("ficha-veredicto").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.wait_for_timeout(500)
    ver_mas = pagina.get_by_test_id("ficha-ver-mas")
    if not ver_mas.count():
        problemas.append(f"{catalogo[larga]['nombre']}: la descripción más larga no ofrece «Ver más»")
    else:
        ver_mas.click()
        try:
            pagina.wait_for_function(
                "() => document.querySelector('[data-testid=ficha-ver-mas]')?.textContent.trim() === 'Ver menos'",
                timeout=5000,
            )
        except TiempoAgotado:
            pass
        abierta = pagina.get_by_test_id("ficha-descripcion").evaluate("p => p.scrollHeight <= p.clientHeight + 1")
        if not abierta or ver_mas.inner_text().strip() != "Ver menos":
            problemas.append(f"«Ver más» no abre la descripción completa (abierta {abierta}, dice {ver_mas.inner_text()!r})")
    _abrir(pagina, f"{url.rstrip('/')}/juego/{corta}")
    pagina.get_by_test_id("ficha-descripcion").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.wait_for_timeout(500)
    if pagina.get_by_test_id("ficha-ver-mas").count():
        problemas.append(f"{catalogo[corta]['nombre']}: la descripción cabe entera y aun así ofrece «Ver más»")
    elif not any("Ver más" in p for p in problemas):
        print(f"ver más:  {catalogo[larga]['nombre']} lo ofrece y abre el texto; "
              f"{catalogo[corta]['nombre']} ({con_texto[0][0]} caracteres) cabe entera y no lo lleva")

    _abrir(pagina, url)
    return problemas


# Lo que Nia debe decir en la ficha según la banda. Replica a propósito el dominio
# (dominio/reaccion-nia.ts) en vez de importarlo: si alguien cambia un texto allá sin
# querer, aquí salta.
# El globo no repite el veredicto (la banda ya está arriba): invita al chat.
_REACCION_ESPERADA = {
    "bajo": "qué la separa del resto del catálogo",
    "medio": "por qué quedó a la mitad",
    "alto": "de dónde sale esta banda",
}


def _un_juego_por_banda(api: str) -> dict[str, int]:
    """El primer appid de cada banda según la API: el catálogo crece, no se fija a mano."""
    elegidos: dict[str, int] = {}
    for juego in sorted(_catalogo_api(api), key=lambda j: j["appid"]):
        elegidos.setdefault(juego["banda_riesgo"], juego["appid"])
    return elegidos


def _una_sola_entrada_a_nia(pagina: Page) -> list[str]:
    """En la ficha se habla con Nia en un solo sitio: su tarjeta de la columna. Ni el globo
    de la reacción ni la mascota de la historia vuelven a ofrecer lo mismo."""
    sobran = []
    for testid, donde in (("nia-reaccion", "la mascota de la reacción"),
                          ("historia-pedir-nia", "la mascota de la historia"),
                          ("historia-mini-nia", "la mascota de la historia")):
        if pagina.get_by_test_id(testid).count():
            sobran.append(donde)
    if sobran:
        return [f"la ficha ofrece más de una entrada a Nia: {', '.join(sorted(set(sobran)))}"]
    if not pagina.get_by_test_id("nia").count():
        return ["la ficha se quedó sin la tarjeta del chat de Nia"]
    print("nia v2:   una sola entrada al chat en la ficha, la tarjeta de la columna")
    return []


# Qué pares de color tienen que pasar, y cuánto piden: 4.5:1 el texto, 3:1 los bordes y
# los controles (WCAG 1.4.3 y 1.4.11). Se miden sobre los tokens ya resueltos por el
# navegador, no sobre lo que dice la documentación, y en cada una de las siete vistas: el
# color de acción, la nebulosa y los rellenos que dependen de él cambian con data-vista.
#
# Un color es un token (--texto) o una pila de capas: la base y, encima, un color con su
# alfa. En la pila, "canal:--x" es rgb(var(--x)) y el alfa puede ser un número o un token
# numérico. Un token que ya trae alfa (--panel) se compone con el suyo.
_FONDOS = ("--fondo", "--fondo-2", "--superficie", "--superficie-2")


def _sobre(base: str, *capas: tuple[str, float | str | None]) -> tuple:
    return (base, *capas)


def _pares_de_contraste() -> list[tuple[str, object, object, float]]:
    """(alcance, frente, fondo, mínimo). El alcance es 'global' o 'vista'."""
    pares: list[tuple[str, object, object, float]] = []
    for frente in ("--texto", "--texto-2", "--enlace"):
        pares += [("global", frente, fondo, 4.5) for fondo in _FONDOS]
    pares += [("global", "--borde-control", fondo, 3.0) for fondo in _FONDOS]
    pares += [("global", "--foco", fondo, 3.0) for fondo in _FONDOS]
    for nivel in ("bajo", "medio", "alto"):
        pares += [("global", f"--banda-{nivel}-texto", fondo, 4.5) for fondo in _FONDOS]
        pares.append(("global", "--texto-sobre-banda", f"--banda-{nivel}", 4.5))
        pares.append(("global", f"--banda-{nivel}-filo", "--superficie", 3.0))
    for estado in ("--exito", "--aviso", "--error", "--info"):
        pares += [("global", estado, fondo, 4.5) for fondo in ("--fondo", "--superficie")]
    # Píldora de perfil activo del menú: en el color de Tu perfil.
    pildora = _sobre("--superficie", ("canal:--canal-perfil", 0.1))
    pares += [
        ("global", "--texto", pildora, 4.5),
        ("global", "--t-perfil", pildora, 3.0),
        ("global", _sobre("--superficie", ("--t-perfil", "--mezcla-filo")), "--superficie", 3.0),
    ]

    # Por vista: el botón principal, el color de acción como texto, el ítem activo del
    # menú, las insignias, las tarjetas de acción y los compactos (data-tono igual a la
    # vista), y el texto sobre la nebulosa en su punto más claro.
    pares += [
        ("vista", "--cta-texto", "--cta-fondo", 4.5),
        ("vista", "--cta-filo", "--fondo", 3.0),
        ("vista", "--cta-filo", "--superficie", 3.0),
    ]
    pares += [("vista", "--neon", fondo, 4.5) for fondo in _FONDOS]
    pares += [
        ("vista", "--neon", "--acento-sistema", 4.5),
        ("vista", "--texto-2", "--acento-sistema", 4.5),
        ("vista", "--neon", "--superficie", 3.0),
        ("vista", "--tono", _sobre("--superficie", ("canal:--tono-canal", 0.14)), 3.0),
    ]
    # Tarjeta y compacto van opacos sobre la superficie, así que lo de abajo no cuenta.
    tarjeta = _sobre("--superficie", ("canal:--tono-canal", 0.12))
    compacto = _sobre("--superficie", ("canal:--tono-canal", 0.1))
    pares += [
        ("vista", "--tono", tarjeta, 4.5),
        ("vista", "--texto-2", tarjeta, 4.5),
        ("vista", "--tono", compacto, 4.5),
        ("vista", _sobre("--superficie", ("--tono", "--mezcla-filo")), "--superficie", 3.0),
    ]
    nebulosa = _sobre("--fondo-2", ("canal:--accion-canal", "--nebulosa"), ("canal:--accion-canal", "--brillo"))
    pares += [
        ("vista", "--texto", nebulosa, 4.5),
        ("vista", "--texto-2", nebulosa, 4.5),
        ("vista", "--texto-2", nebulosa + (("--panel", None),), 4.5),
    ]
    return pares


_CONTRASTES = _pares_de_contraste()

# Un perfil guardado en v3, con tres géneros: al migrar, la píldora dice «Perfil activo · 1
# pregunta nueva» en dos renglones, que es lo más alto que puede aparecer en la barra, y
# tiene que caber con ella.
_PERFIL_EN_LA_BARRA = {
    "valores": {"compras": 4, "horas": 6, "friccion": 3, "plataforma": "pc", "generos": ["Acción", "Rol", "Estrategia"]},
    # Lo que devuelve POST /perfil para esos valores: la fricción viaja como nivel.
    "perfil": {
        "compras_al_anio": 4, "horas_por_semana": 6.0, "tolerancia_friccion": "media",
        "tags_preferidos": ["acción", "rol", "estrategia"], "tags_rechazados": [], "plataforma": "pc",
        "segmento": "novato", "disponibilidad": "media",
    },
}
_VISTAS_DE_COLOR = ("inicio", "explorar", "comparar", "nia", "perfil", "panorama", "neutro")

# Cada token se lee en un elemento con data-vista y data-tono puestos, porque los alias
# (--neon, --cta-fondo, --acento-sistema) se re-declaran ahí. Los colores pasan por un
# canvas para salir en '#rrggbb' o 'rgba(...)'; los canales y los alfas se leen crudos.
_JS_TOKENS = """
({ vistas, colores, crudos }) => {
    const lienzo = document.createElement('canvas').getContext('2d');
    const aColor = (valor) => { lienzo.fillStyle = '#000'; lienzo.fillStyle = valor; return lienzo.fillStyle; };
    const armazon = document.querySelector('.armazon') || document.body;
    return Object.fromEntries(vistas.map(vista => {
        const sonda = document.createElement('div');
        sonda.dataset.vista = vista;
        sonda.dataset.tono = vista;
        armazon.appendChild(sonda);
        const estilo = getComputedStyle(sonda);
        const valores = {};
        for (const nombre of colores) valores[nombre] = aColor(estilo.getPropertyValue(nombre).trim());
        for (const nombre of crudos) valores[nombre] = estilo.getPropertyValue(nombre).trim();
        sonda.remove();
        return [vista, valores];
    }));
}
"""

# Botones y enlaces que quedan debajo de la burbuja de Nia. Un enlace grande puede
# solaparse por una esquina sin estorbar; lo que importa son los controles chicos, así que
# se miran solo los que caben casi enteros dentro de ella.
# Un control está tapado si el centro de lo que se VE de él cae bajo la burbuja: ahí es
# donde cae un toque. Lo que se ve es su caja recortada por los contenedores con scroll
# que lo contienen (un estante horizontal corta la tarjeta que se sale de la pantalla).
# Antes se medía la caja entera, y la píldora de una tarjeta a medio salir, que nadie puede
# pulsar ahí, contaba como tapada por los 6 px de franja que asomaban.
_JS_BAJO_LA_BURBUJA = """
() => {
    const burbuja = document.querySelector('.burbuja')?.getBoundingClientRect();
    if (!burbuja) return [];
    const visible = (elemento) => {
        let r = elemento.getBoundingClientRect();
        let [izq, arr, der, aba] = [r.left, r.top, r.right, r.bottom];
        for (let a = elemento.parentElement; a && a !== document.body; a = a.parentElement) {
            const c = getComputedStyle(a);
            if (c.overflowX !== 'visible' || c.overflowY !== 'visible') {
                const ra = a.getBoundingClientRect();
                izq = Math.max(izq, ra.left); arr = Math.max(arr, ra.top);
                der = Math.min(der, ra.right); aba = Math.min(aba, ra.bottom);
            }
        }
        return der > izq && aba > arr ? { x: (izq + der) / 2, y: (arr + aba) / 2 } : null;
    };
    return [...document.querySelectorAll('button, a')]
        .filter(elemento => !elemento.closest('.flotante'))
        .map(elemento => ({ elemento, caja: elemento.getBoundingClientRect(), centro: visible(elemento) }))
        .filter(({ caja, centro }) => centro && caja.width < 260 && caja.height < 120 &&
                centro.x > burbuja.left && centro.x < burbuja.right &&
                centro.y > burbuja.top && centro.y < burbuja.bottom)
        .map(({ elemento }) => elemento.getAttribute('aria-label') || elemento.textContent.trim().slice(0, 40));
}
"""


def _rgb(valor: str) -> tuple[tuple[float, float, float], float]:
    """'#rrggbb', 'rgba(r, g, b, a)' o 'color(srgb r g b / a)' —lo que da el canvas con un
    color-mix()— a canales 0–255 y alfa."""
    if valor.startswith("#"):
        crudo = valor.lstrip("#")
        return tuple(int(crudo[i:i + 2], 16) for i in (0, 2, 4)), 1.0
    numeros = [float(n) for n in re.findall(r"\d*\.?\d+(?:e-?\d+)?", valor)]
    escala = 255 if valor.startswith("color(srgb") else 1
    return tuple(n * escala for n in numeros[:3]), numeros[3] if len(numeros) > 3 else 1.0


def _luminancia(canales: tuple[float, float, float]) -> float:
    lineal = [(c / 255) / 12.92 if c / 255 <= 0.03928 else (((c / 255) + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]


def _contraste(uno: tuple, otro: tuple) -> float:
    a, b = _luminancia(uno), _luminancia(otro)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _alfa(valor: str) -> float:
    valor = valor.strip()
    return float(valor[:-1]) / 100 if valor.endswith("%") else float(valor)


def _nombres_de_pares() -> tuple[set[str], set[str]]:
    colores, crudos = set(), set()

    def recorrer(color: object) -> None:
        if isinstance(color, str):
            colores.add(color)
            return
        base, *capas = color
        colores.add(base)
        for token, alfa in capas:
            (crudos if token.startswith("canal:") else colores).add(token.removeprefix("canal:"))
            if isinstance(alfa, str):
                crudos.add(alfa)

    for _, frente, fondo, _ in _CONTRASTES:
        recorrer(frente)
        recorrer(fondo)
    return colores, crudos


def _resolver(color: object, tokens: dict[str, str]) -> tuple[float, float, float]:
    """Compone la pila de capas sobre su base; un token suelto se toma tal cual."""
    if isinstance(color, str):
        return _rgb(tokens[color])[0]
    base, *capas = color
    actual = _rgb(tokens[base])[0]
    for token, alfa in capas:
        if token.startswith("canal:"):
            canales = tuple(float(n) for n in tokens[token.removeprefix("canal:")].split()[:3])
            propio = 1.0
        else:
            canales, propio = _rgb(tokens[token])
        a = propio if alfa is None else (_alfa(tokens[alfa]) if isinstance(alfa, str) else alfa)
        actual = tuple(c * a + b * (1 - a) for c, b in zip(canales, actual))
    return actual


def _describir(color: object) -> str:
    if isinstance(color, str):
        return color
    base, *capas = color
    partes = [base] + [f"{t.removeprefix('canal:')}@{a if a is not None else 'propio'}" for t, a in capas]
    return " + ".join(partes)


def _revisar_contrastes(pagina: Page, tema: str) -> list[str]:
    colores, crudos = _nombres_de_pares()
    por_vista = pagina.evaluate(
        _JS_TOKENS, {"vistas": list(_VISTAS_DE_COLOR), "colores": sorted(colores), "crudos": sorted(crudos)}
    )
    faltan = sorted({
        nombre for tokens in por_vista.values() for nombre in colores
        if not tokens[nombre].startswith(("#", "rgba", "color(srgb"))
    } | {nombre for tokens in por_vista.values() for nombre in crudos if not tokens[nombre]})
    if faltan:
        return [f"en tema {tema} no se resolvieron los tokens {faltan}"]
    problemas = []
    peor = ("", 99.0)
    medidos = 0
    for alcance, frente, fondo, minimo in _CONTRASTES:
        vistas = _VISTAS_DE_COLOR if alcance == "vista" else ("inicio",)
        for vista in vistas:
            tokens = por_vista[vista]
            razon = _contraste(_resolver(frente, tokens), _resolver(fondo, tokens))
            medidos += 1
            donde = f" en {vista}" if alcance == "vista" else ""
            if razon < minimo:
                problemas.append(
                    f"en tema {tema}{donde}, {_describir(frente)} sobre {_describir(fondo)} "
                    f"da {razon:.2f}:1 y pide {minimo}:1"
                )
            elif razon - minimo < peor[1]:
                peor = (f"{_describir(frente)} sobre {_describir(fondo)}{donde} con {razon:.2f}:1 (pide {minimo})", razon - minimo)
    if not problemas:
        print(f"contraste: tema {tema}, {medidos} pares pasan; el más justo es {peor[0]}")
    else:
        print(f"contraste: tema {tema}, {len(problemas)} de {medidos} pares no pasan")
    return problemas


# Regla de la 6B: el texto va sobre un fondo que le dé 4.5:1, y la nebulosa no cuenta como
# fondo seguro. Para cada texto visible se compone la pila de background-color de sus
# ancestros; si ningún panel opaco lo cubre antes de llegar al lienzo (.armazon > .columna), se toma
# el punto más claro de la nebulosa de la vista: --fondo-2 con la nebulosa y el brillo de
# su color encima. Donde el texto va sobre un video o una imagen, el contenedor declara su
# peor fondo en data-fondo-peor. Los títulos con degradado recortado (color transparente)
# se miden aparte, con los tokens.
_JS_TEXTO_SOBRE_NEBULOSA = """
() => {
    const aRgba = (valor) => {
        const n = (valor.match(/-?[\\d.]+(e-?\\d+)?/g) || []).map(Number);
        if (valor.startsWith('color(srgb')) return [n[0] * 255, n[1] * 255, n[2] * 255, n.length > 3 ? n[3] : 1];
        if (valor.startsWith('#')) {
            const h = valor.slice(1);
            return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)).concat([1]);
        }
        return [n[0], n[1], n[2], n.length > 3 ? n[3] : 1];
    };
    const mezcla = (arriba, alfa, abajo) => arriba.map((c, i) => c * alfa + abajo[i] * (1 - alfa));
    const lum = (rgb) => {
        const [r, g, b] = rgb.map(c => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const contraste = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
    const armazon = document.querySelector('.armazon') || document.documentElement;
    const tok = (n) => getComputedStyle(armazon).getPropertyValue(n).trim();
    const canal = tok('--accion-canal').split(/\\s+/).map(Number);
    const peorNebulosa = mezcla(canal, Number(tok('--brillo')),
        mezcla(canal, Number(tok('--nebulosa')), aRgba(tok('--fondo-2')).slice(0, 3)));
    const fondoDe = (el) => {
        const capas = [];
        let base = null;
        for (let a = el; a; a = a.parentElement) {
            if (a.dataset && a.dataset.fondoPeor) { base = aRgba(a.dataset.fondoPeor).slice(0, 3); break; }
            const [r, g, b, alfa] = aRgba(getComputedStyle(a).backgroundColor);
            if (alfa > 0) {
                capas.push([[r, g, b], alfa]);
                if (alfa >= 0.999) { base = capas.pop()[0]; break; }
            }
            // El lienzo es la columna del armazón; otras .columna (las de las gráficas) no.
            if (a.classList && a.classList.contains('columna') && a.parentElement?.classList.contains('armazon')) {
                base = peorNebulosa; break;
            }
        }
        let fondo = base || peorNebulosa;
        while (capas.length) { const [c, alfa] = capas.pop(); fondo = mezcla(c, alfa, fondo); }
        return fondo;
    };
    const fallas = [];
    for (const el of document.querySelectorAll('body *')) {
        if (el.closest('svg, .solo-lector, [aria-hidden="true"]')) continue;
        if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        const e = getComputedStyle(el);
        if (e.visibility === 'hidden' || Number(e.opacity) === 0) continue;
        const [cr, cg, cb, ca] = aRgba(e.color);
        if (ca === 0) continue;
        const fondo = fondoDe(el);
        const color = ca < 1 ? mezcla([cr, cg, cb], ca, fondo) : [cr, cg, cb];
        const razon = contraste(color, fondo);
        if (razon < 4.5) {
            fallas.push({
                texto: el.textContent.trim().replace(/\\s+/g, ' ').slice(0, 40),
                razon: Math.round(razon * 100) / 100,
                fondo: '#' + fondo.map(v => Math.round(v).toString(16).padStart(2, '0')).join(''),
            });
        }
    }
    return fallas;
}
"""


def _texto_sobre_la_nebulosa(pagina: Page, donde: str) -> list[str]:
    fallas = pagina.evaluate(_JS_TEXTO_SOBRE_NEBULOSA)
    return [
        f"{donde}: «{f['texto']}» da {f['razon']}:1 sobre {f['fondo']} (pide 4.5:1)"
        for f in fallas[:6]
    ]


def _desborde(pagina: Page) -> int:
    ancho, visible = pagina.evaluate(
        "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"
    )
    return max(0, ancho - visible)


# Elementos con filete arriba que van pegados a otro filete sin texto en medio: en la
# ficha salían dos líneas seguidas cuando un bloque ponía su borde y la pila el suyo.
_JS_FILETES_SEGUIDOS = """
() => {
    const conFilete = e => parseFloat(getComputedStyle(e).borderTopWidth) > 0;
    const sobra = [];
    for (const padre of document.querySelectorAll('.pila-separada, .principal, .lateral')) {
        for (const hijo of padre.children) {
            if (!conFilete(hijo)) continue;
            const primero = hijo.firstElementChild;
            if (primero && conFilete(primero) && !primero.previousSibling?.textContent?.trim()) {
                sobra.push((hijo.tagName + '.' + hijo.className).slice(0, 40));
            }
        }
    }
    return sobra;
}
"""


def _sin_filetes_dobles(pagina: Page, donde: str) -> list[str]:
    sobra = pagina.evaluate(_JS_FILETES_SEGUIDOS)
    if sobra:
        return [f"{donde}: filetes seguidos sin contenido en medio ({sorted(set(sobra))[:3]})"]
    print(f"filetes:  {donde} sin líneas dobles")
    return []


def _contenido_estrecho(pagina: Page, ancho: int) -> str | None:
    """A 390 px el contenido tiene que ocupar la pantalla menos sus márgenes.

    Con la barra convertida en cajón, su columna de la rejilla se quedaba con 240 de los
    390 px y todo lo demás se apretaba en 150: nada desbordaba, así que el control de
    desborde no lo veía."""
    medido = pagina.evaluate(
        "() => { const c = document.querySelector('.contenido');"
        " return c ? Math.round(c.getBoundingClientRect().width) : null; }"
    )
    if medido is None:
        return "no tiene .contenido que medir"
    minimo = round(ancho * 0.85)
    return None if medido >= minimo else f"aprieta el contenido en {medido} px de {ancho} (mínimo {minimo})"


# El texto visible de una página, con el tamaño al que se pinta. Se salta lo que no se
# ve (sin caja, oculto) y lo que es solo para lector de pantalla, que mide 1 px a propósito.
_JS_TEXTOS_VISIBLES = """() => {
  const fuera = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const nodo = w.currentNode, texto = nodo.textContent.trim(), el = nodo.parentElement;
    if (!texto || !el || el.closest('.solo-lector, [aria-hidden="true"], script, style')) continue;
    const c = getComputedStyle(el), r = el.getBoundingClientRect();
    if (c.display === 'none' || c.visibility === 'hidden' || r.width === 0 || r.height === 0) continue;
    fuera.push({ texto: texto.slice(0, 60), px: parseFloat(c.fontSize) });
  }
  for (const e of document.querySelectorAll('[aria-label],[title],[placeholder]'))
    for (const a of ['aria-label', 'title', 'placeholder']) {
      const v = e.getAttribute(a);
      if (v) fuera.push({ texto: v.slice(0, 60), px: null });
    }
  return fuera;
}"""

_JS_PILDORAS_CORTADAS = """() => [...document.querySelectorAll('[data-testid="pildora-banda"]')]
  .filter((p) => p.getBoundingClientRect().width > 0)
  .filter((p) => {
    const r = p.getBoundingClientRect();
    if (p.scrollWidth > p.clientWidth + 1) return true;
    for (let a = p.parentElement; a && a !== document.body; a = a.parentElement) {
      const c = getComputedStyle(a);
      if (c.overflowX === 'visible') continue;
      const ra = a.getBoundingClientRect();
      // Un estante con scroll horizontal corta tarjetas a propósito: ahí no cuenta.
      if (a.scrollWidth > a.clientWidth + 1 && c.overflowX !== 'hidden') return false;
      return r.right > ra.right + 1 || r.left < ra.left - 1;
    }
    return false;
  })
  .map((p) => p.textContent.trim())"""

_VOCABULARIO_RETIRADO = re.compile(r"\bbanda\b|riesgo general", re.IGNORECASE)
_PISO_DE_LETRA = 16


def _angular_letra_y_vocabulario(pagina: Page, url: str) -> list[str]:
    """Fase 6A: nada de lectura bajo 16 px, nada de "banda" ni "Riesgo general" a la vista
    (el nivel se llama riesgo de arrepentimiento). En las cinco vistas y la ficha, con el
    panel de metodología del pie y «Tu actividad» abiertos, para medir también lo plegado."""
    problemas = []
    base = url.rstrip("/")
    rutas = ["/#metodologia", "/explorar", f"/juego/{_APPID_FICHA}", "/nia", "/comparar", "/perfil#actividad"]
    minimas = []
    for ruta in rutas:
        _abrir(pagina, f"{base}{ruta}")
        pagina.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
        pagina.wait_for_timeout(1500)
        textos = pagina.evaluate(_JS_TEXTOS_VISIBLES)
        con_tamano = [t for t in textos if t["px"] is not None]
        if con_tamano:
            menor = min(con_tamano, key=lambda t: t["px"])
            minimas.append((ruta, menor["px"]))
            if menor["px"] < _PISO_DE_LETRA:
                problemas.append(f"{ruta}: hay texto a {menor['px']} px («{menor['texto']}»); el piso es {_PISO_DE_LETRA}")
        # El nombre nuevo es más largo y la píldora no parte línea: si su contenedor la
        # recorta, el desborde de la página no lo ve. Se compara con el ancestro que recorta.
        cortadas = pagina.evaluate(_JS_PILDORAS_CORTADAS)
        for cortada in cortadas[:2]:
            problemas.append(f"{ruta}: la píldora «{cortada}» queda cortada por su contenedor")
        retirados = sorted({t["texto"] for t in textos if _VOCABULARIO_RETIRADO.search(t["texto"])})
        for texto in retirados[:3]:
            problemas.append(f"{ruta}: todavía dice «{texto}»; el nivel se llama riesgo de arrepentimiento")
    if minimas and not problemas:
        peor = min(minimas, key=lambda m: m[1])
        print(f"letra:    las 5 vistas y la ficha sin texto bajo {_PISO_DE_LETRA} px (la más chica, {peor[1]:g} px en {peor[0]}) "
              "y sin «banda» ni «Riesgo general»")

    return problemas


def _angular_barra_y_tema(pagina: Page, url: str, destino: Path) -> list[str]:
    """La barra lateral y los dos temas: sin desborde a 390 px, con los contrastes medidos
    sobre los tokens que el navegador resolvió, y el cajón de móvil abriéndose y
    cerrándose como debe."""
    problemas = []
    base = url.rstrip("/")
    navegador = pagina.context.browser
    if navegador is None:
        return ["sin navegador para revisar la barra y los temas"]

    # 1. Encoger la barra le devuelve ancho al contenido. Se mide en una ventana de
    # 1280 px: a 1440 la página ya topa con su ancho máximo de 1200 y no cambiaría nada.
    contexto = navegador.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    _sin_consultas_a_nia(contexto)
    contexto.add_init_script("localStorage.setItem('nexplay.tema.v1', 'oscuro')")
    try:
        estrecha = contexto.new_page()
        _abrir(estrecha, base)
        estrecha.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
        barra = estrecha.locator("app-barra-lateral").bounding_box()
        contenido = estrecha.locator(".contenido").bounding_box()
        if not barra or not contenido:
            return problemas + ["la barra lateral no se ve en escritorio"]
        estrecha.get_by_test_id("colapsar-barra").click()
        estrecha.wait_for_timeout(400)
        corta = estrecha.locator("app-barra-lateral").bounding_box()
        contenido_corto = estrecha.locator(".contenido").bounding_box()
        if not corta or not contenido_corto or corta["width"] >= barra["width"]:
            problemas.append("encoger la barra no la hace más angosta")
        elif contenido_corto["width"] <= contenido["width"]:
            problemas.append("encoger la barra no le devuelve ancho al contenido")
        else:
            print(
                f"barra:    a 1280 px, {barra['width']:.0f} px expandida y {corta['width']:.0f} encogida; "
                f"el contenido pasa de {contenido['width']:.0f} a {contenido_corto['width']:.0f} px"
            )
        _esperar_quietud(estrecha)
        estrecha.screenshot(path=destino / "barra-encogida.png")
    finally:
        contexto.close()

    # 2. La barra entera cabe sin scroll propio en una pantalla de portátil.
    contexto = navegador.new_context(viewport={"width": 1440, "height": 674}, reduced_motion="reduce")
    _sin_consultas_a_nia(contexto)
    contexto.add_init_script("localStorage.setItem('nexplay.tema.v1', 'oscuro')")
    try:
        baja = contexto.new_page()
        _abrir(baja, f"{base}/explorar")
        baja.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
        baja.wait_for_timeout(600)
        # Tres estados: sin perfil, con la píldora de perfil activo (la más alta) y encogida.
        # Además, ningún subtítulo del menú puede cortarse en puntos suspensivos.
        medir_riel = (
            "() => { const r = document.querySelector('.riel');"
            " const cortados = [...document.querySelectorAll('nav a.item .sub')]"
            "   .filter(s => s.getBoundingClientRect().width > 2 && s.scrollWidth > s.clientWidth + 1)"
            "   .map(s => s.textContent.trim());"
            " return [Math.round(r.scrollHeight), Math.round(r.clientHeight), cortados]; }"
        )
        estados = []
        for estado in ("sin perfil", "con perfil", "encogida"):
            if estado == "con perfil":
                baja.evaluate(
                    "valor => localStorage.setItem('nexplay.perfil.v3', valor)", json.dumps(_PERFIL_EN_LA_BARRA)
                )
                baja.reload()
                baja.get_by_test_id("perfil-activo").wait_for(state="visible", timeout=_TIMEOUT_MS)
            elif estado == "encogida":
                baja.get_by_test_id("colapsar-barra").click()
            baja.wait_for_timeout(600)
            alto, visible, cortados = baja.evaluate(medir_riel)
            if alto > visible + 1:
                problemas.append(f"a 674 px de alto, {estado}, la barra necesita scroll propio ({alto} en {visible})")
            if cortados:
                problemas.append(f"a 674 px, {estado}, el menú corta subtítulos: {cortados}")
            estados.append(f"{estado} {alto}")
        baja.get_by_test_id("colapsar-barra").click()
        baja.evaluate("() => localStorage.removeItem('nexplay.perfil.v3')")
        if not any("674 px" in p for p in problemas):
            print(f"barra:    cabe entera en 674 px de alto sin scroll propio ({', '.join(estados)} px), sin subtítulos cortados")
        # Y el veredicto de la ficha entra sin desplazarse en esa misma pantalla.
        _abrir(baja, f"{base}/juego/{_APPID_FICHA}")
        baja.get_by_test_id("ficha-veredicto").wait_for(state="visible", timeout=_TIMEOUT_MS)
        baja.wait_for_timeout(800)
        caja = baja.get_by_test_id("ficha-veredicto").bounding_box()
        if not caja or caja["y"] + caja["height"] > 674:
            problemas.append(f"a 674 px de alto el veredicto no entra sin desplazarse ({caja})")
        else:
            print(f"ficha:    el veredicto entra sin desplazarse a 674 px (termina en {caja['y'] + caja['height']:.0f})")

        # Y al bajar hasta el final, el chat de la ficha tiene que quedar a la vista: la
        # columna derecha es más alta que la pantalla y antes se llevaba el campo de
        # "Preguntar" al último píxel de la página.
        baja.keyboard.press("End")
        baja.wait_for_timeout(900)
        enviar = baja.get_by_test_id("nia-enviar").bounding_box()
        if not enviar or enviar["y"] < 0 or enviar["y"] + enviar["height"] > 674:
            problemas.append(f"en la ficha a 674 px, el botón de preguntar no queda a la vista al final del scroll ({enviar})")
        else:
            print(f"ficha:    al final del scroll, el botón de preguntar queda a la vista (y={enviar['y']:.0f})")

        # El chat de /nia también tiene que caber: el botón de preguntar es lo último.
        _abrir(baja, f"{base}/nia?appid={_APPID_FICHA}")
        baja.get_by_test_id("nia-enviar").wait_for(state="visible", timeout=_TIMEOUT_MS)
        baja.wait_for_timeout(700)
        boton = baja.get_by_test_id("nia-enviar").bounding_box()
        if not boton or boton["y"] + boton["height"] > 674:
            problemas.append(f"a 674 px de alto el botón de preguntar queda fuera ({boton})")
        elif not baja.get_by_test_id("nia-bienvenida").count():
            problemas.append("el chat vacío de /nia no saluda: queda el hueco")
        else:
            print(f"nia:      el botón de preguntar entra a 674 px (termina en {boton['y'] + boton['height']:.0f})")
    finally:
        contexto.close()

    # 3. Los dos temas en las tres resoluciones de la fase 6 (1440, 1024 y 390): contrastes,
    # desborde y una captura de lo que se ve al entrar a cada vista, para revisar fondos y
    # color de acción sin abrir la app.
    carpeta_vistas = destino / "vistas"
    carpeta_vistas.mkdir(parents=True, exist_ok=True)
    textos_con_falla = 0
    # Las cinco vistas y la ficha, y además lo que se abre desplegado: el panel de
    # metodología del pie y «Tu actividad». Cada ancla va después de otra ruta, para que la
    # navegación sea completa y no solo un cambio de fragmento.
    rutas = [*_RUTAS_DE_LA_APP, "/#metodologia", "/perfil#actividad"]
    for tema in ("oscuro", "claro"):
        for vista, nombre in (
            (_VIEWPORT, "escritorio"),
            ({"width": 1024, "height": 1366}, "tableta"),
            ({"width": 390, "height": 844}, "movil"),
        ):
            contexto = navegador.new_context(viewport=vista, reduced_motion="reduce")
            _sin_consultas_a_nia(contexto)
            contexto.add_init_script(f"localStorage.setItem('nexplay.tema.v1', '{tema}')")
            try:
                otra = contexto.new_page()
                _abrir(otra, base)
                otra.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
                puesto = otra.evaluate("() => document.documentElement.dataset.tema")
                if puesto != tema:
                    problemas.append(f"con '{tema}' guardado, <html> quedó en '{puesto}'")
                if nombre == "escritorio":
                    problemas += _revisar_contrastes(otra, tema)
                for ruta_app in rutas:
                    _abrir(otra, f"{base}{ruta_app}")
                    otra.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
                    otra.wait_for_timeout(600)
                    sobra = _desborde(otra)
                    if sobra:
                        problemas.append(f"tema {tema} en {nombre}: {ruta_app} desborda {sobra} px")
                    sobre_nebulosa = _texto_sobre_la_nebulosa(otra, f"tema {tema} en {nombre}, {ruta_app}")
                    problemas += sobre_nebulosa
                    textos_con_falla += len(sobre_nebulosa)
                    _esperar_quietud(otra)
                    camino, _, ancla = ruta_app.partition("#")
                    slug = (camino.strip("/").split("/")[0] or "inicio") + (f"_{ancla}" if ancla else "")
                    otra.screenshot(path=carpeta_vistas / f"{slug}-{tema}-{vista['width']}.png")
                    # Lo contrario del desborde y igual de roto: que el contenido se
                    # apriete en una franja porque algo se quedó con el ancho.
                    if nombre == "movil":
                        estrecho = _contenido_estrecho(otra, vista["width"])
                        if estrecho:
                            problemas.append(f"tema {tema} en móvil: {ruta_app} {estrecho}")
                    # El inicio es la que cambia con los datos: se guarda entera para poder
                    # revisar las cifras de una corrida a otra.
                    if nombre == "escritorio" and ruta_app == "/":
                        otra.get_by_test_id("antes-de-pagar").wait_for(state="visible", timeout=_TIMEOUT_MS)
                        _recorrer_pagina(otra)
                        _esperar_quietud(otra)
                        destino_ruta = destino / f"inicio-{tema}.png"
                        otra.screenshot(path=destino_ruta, full_page=True)
                        print(f"inicio:   tema {tema} ({destino_ruta.relative_to(_RAIZ)})")
                _abrir(otra, f"{base}/explorar")
                otra.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
                otra.get_by_test_id("catalogo-conteo").wait_for(state="visible", timeout=_TIMEOUT_MS)
                _recorrer_pagina(otra)
                if nombre == "movil":
                    otra.get_by_test_id("abrir-menu").click()
                    otra.wait_for_timeout(500)
                    if not otra.get_by_test_id("velo-menu").count():
                        problemas.append(f"tema {tema}: el cajón no pone velo sobre la página")
                    if not otra.locator("[data-testid='shell'][inert]").count():
                        problemas.append(f"tema {tema}: con el cajón abierto la página no queda inerte")
                    if _desborde(otra):
                        problemas.append(f"tema {tema}: el cajón abierto desborda a 390 px")
                _esperar_quietud(otra)
                ruta = destino / f"barra-{tema}-{nombre}.png"
                otra.screenshot(path=ruta, full_page=nombre == "escritorio")
                limpias = len(rutas) - sum(f"tema {tema} en {nombre}" in p for p in problemas)
                print(f"tema:     {tema} en {nombre}, {limpias} de {len(rutas)} rutas sin desborde "
                      f"({ruta.relative_to(_RAIZ)})")
                if nombre == "movil":
                    # El velo cubre toda la ventana, pero el cajón le tapa los 280 px de la
                    # izquierda: el toque va del lado del contenido.
                    otra.get_by_test_id("velo-menu").click(position={"x": 350, "y": 400})
                    otra.wait_for_timeout(500)
                    if otra.get_by_test_id("velo-menu").count():
                        problemas.append(f"tema {tema}: el velo no cierra el cajón")
                    elif otra.evaluate("() => document.activeElement?.dataset.testid") != "abrir-menu":
                        problemas.append(f"tema {tema}: al cerrar el cajón el foco no vuelve a la hamburguesa")
            finally:
                contexto.close()

    print(f"vistas:   5 vistas, la ficha y 2 paneles × 2 temas × 3 anchos en {carpeta_vistas.relative_to(_RAIZ)}")
    if not textos_con_falla:
        print("nebulosa: en las 5 vistas, la ficha y los 2 paneles, 2 temas y 3 anchos, todo texto da 4.5:1 sobre su fondo; "
              "sin panel, contra el punto más claro de la nebulosa")
    _abrir(pagina, url)
    return problemas

# ── Correcciones de producción (ronda de pruebas del 29 sep 2026) ─────────────────────

# Texto y controles de la página que quedan debajo de la burbuja de Nia a la vista. Sirve
# para el final de cada vista, donde la página le reserva su espacio.
_JS_TEXTO_BAJO_LA_BURBUJA = """
() => {
    const flotante = document.querySelector('[data-testid=nia-flotante]');
    const burbuja = document.querySelector('.burbuja')?.getBoundingClientRect();
    if (!burbuja || flotante?.dataset.oculta === 'true') return [];
    const cruza = (r) => r.width > 0 && r.height > 0 && r.left < burbuja.right && r.right > burbuja.left
        && r.top < burbuja.bottom && r.bottom > burbuja.top;
    const tapados = [];
    const pagina = document.querySelector('.pagina');
    const caminante = document.createTreeWalker(pagina, NodeFilter.SHOW_TEXT);
    for (let nodo = caminante.nextNode(); nodo; nodo = caminante.nextNode()) {
        if (!nodo.textContent.trim()) continue;
        const padre = nodo.parentElement;
        if (!padre || padre.closest('.solo-lector, [aria-hidden=true], [hidden]')) continue;
        // Lo de un <details> cerrado no se ve, aunque Chrome le dé cajas.
        const cerrado = padre.closest('details:not([open])');
        if (cerrado && !padre.closest('summary')) continue;
        const estilo = getComputedStyle(padre);
        if (estilo.visibility === 'hidden' || Number(estilo.opacity) === 0) continue;
        const rango = document.createRange();
        rango.selectNodeContents(nodo);
        if ([...rango.getClientRects()].some(cruza)) tapados.push(nodo.textContent.trim().slice(0, 40));
    }
    for (const control of pagina.querySelectorAll('button, a[href], input, textarea')) {
        if (cruza(control.getBoundingClientRect())) {
            tapados.push(control.getAttribute('aria-label') || control.textContent.trim().slice(0, 40));
        }
    }
    return tapados;
}
"""

# Zonas de toque de menos de 44 px. Cuenta la caja del control o, si lleva .toque-amplio o
# .chip, el ::before que la agranda. Los enlaces dentro de un párrafo quedan fuera, como
# en WCAG 2.5.8, igual que lo que no se puede tocar (oculto, inerte o sin eventos).
_JS_ZONAS_CHICAS = """
() => {
    const tocable = (el) => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return false;
        if (el.closest('[inert], [hidden], [aria-hidden=true]')) return false;
        for (let a = el; a; a = a.parentElement) {
            const e = getComputedStyle(a);
            if (e.visibility === 'hidden' || e.pointerEvents === 'none' || e.display === 'none') return false;
        }
        return true;
    };
    const enLinea = (el) => {
        if (el.tagName !== 'A' || getComputedStyle(el).display !== 'inline') return false;
        const resto = [...el.parentElement.childNodes].filter((n) => n !== el).map((n) => n.textContent).join('');
        return /\\S/.test(resto);
    };
    const salida = [];
    const selector = 'button, a[href], input:not([type=hidden]), textarea, summary, [role=tab], [role=switch]';
    for (const el of document.querySelectorAll(selector)) {
        if (!tocable(el) || enLinea(el)) continue;
        const caja = el.getBoundingClientRect();
        if (caja.width <= 1 && caja.height <= 1 && el.closest('label')) continue;
        const r = el.getBoundingClientRect();
        let ancho = r.width, alto = r.height;
        const antes = getComputedStyle(el, '::before');
        if (antes.content !== 'none' && antes.position === 'absolute') {
            ancho = Math.max(ancho, parseFloat(antes.width) || 0);
            alto = Math.max(alto, parseFloat(antes.height) || 0);
        }
        if (ancho < 43.5 || alto < 43.5) {
            const nombre = el.dataset.testid || el.getAttribute('aria-label') || el.textContent.trim().slice(0, 30) || el.tagName;
            salida.push(`${nombre} (${Math.round(ancho)}×${Math.round(alto)})`);
        }
    }
    return [...new Set(salida)];
}
"""

_VISTAS_CON_BURBUJA = ("/", "/explorar", "/comparar?appids=1145360,367520", "/perfil")


def _al_final(pagina: Page) -> None:
    """Hasta el final de la página, dos veces: lo que carga al bajar la alarga."""
    for _ in range(2):
        pagina.evaluate("() => scrollTo(0, document.scrollingElement.scrollHeight)")
        pagina.wait_for_timeout(700)


def _explorar_sin_resultados(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    problemas = []
    total = len(_catalogo_api(api))
    _abrir(pagina, f"{url.rstrip('/')}/explorar?q=zzzz")
    vacio = pagina.get_by_test_id("catalogo-sin-resultados")
    try:
        vacio.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        return ["Explorar sin resultados no dice nada: no aparece el mensaje"]
    texto = " ".join(vacio.inner_text().split())
    if f"No encontramos «zzzz» en los {total} juegos." not in texto:
        problemas.append(f"Explorar sin resultados dice «{texto}»")
    vacio.scroll_into_view_if_needed()
    vacio.screenshot(path=destino / "explorar-sin-resultados.png")
    pagina.get_by_test_id("limpiar-busqueda").click()
    try:
        pagina.get_by_test_id("estante-bajo").wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        problemas.append("«Limpiar búsqueda» no devuelve los estantes")
    if "q=" in pagina.url or pagina.get_by_test_id("filtro-texto").input_value():
        problemas.append(f"«Limpiar búsqueda» deja el texto ({pagina.url})")
    if not problemas:
        print(f"explorar: sin resultados dice «{texto.split('.')[0]}.» y «Limpiar búsqueda» devuelve el catálogo "
              f"({(destino / 'explorar-sin-resultados.png').relative_to(_RAIZ)})")
    return problemas


def _llenar_perfil(pagina: Page) -> None:
    pagina.get_by_test_id("grupo-compras").get_by_text("Pocos", exact=True).click()
    pagina.get_by_test_id("grupo-gasto").get_by_text("$200 a $500", exact=True).click()
    pagina.get_by_test_id("grupo-horas").get_by_text("Media", exact=True).click()
    pagina.get_by_test_id("grupo-plataforma").get_by_text("PC", exact=True).click()
    pagina.get_by_test_id("grupo-friccion").get_by_text("Media", exact=True).click()
    pagina.get_by_test_id("crear-perfil").click()
    pagina.get_by_test_id("perfil-activo").wait_for(state="visible", timeout=_TIMEOUT_MS)


def _franja_nia(pagina: Page, url: str, destino: Path) -> list[str]:
    """Lo que Nia ofrece en Explorar, Comparar y Perfil va en una franja dentro de la vista,
    no flotando: sale una vez al día, la × la cierra, su botón abre la burbuja; en Comparar
    con dos juegos o más y en Perfil solo con perfil creado."""
    problemas = []
    base = url.rstrip("/")
    navegador = pagina.context.browser

    def contexto_nuevo(ancho: int = 1440, alto: int = 900):
        contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
        _sin_consultas_a_nia(contexto, con_globito=True)
        return contexto

    # Explorar: dentro de la búsqueda, sin flotar; su botón abre la burbuja con cómo filtrar.
    contexto = contexto_nuevo()
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/explorar")
        franja = otra.get_by_test_id("franja-nia")
        franja.wait_for(state="visible", timeout=_TIMEOUT_MS)
        texto = " ".join(franja.inner_text().split())
        dentro = otra.locator("[data-testid=catalogo-busqueda] [data-testid=franja-nia]").count()
        posicion = franja.evaluate("f => getComputedStyle(f).position")
        if "filtrar" not in texto.lower() or not dentro or posicion != "static":
            problemas.append(f"la franja de Explorar no está en la búsqueda o flota ({texto!r}, {posicion})")
        franja.scroll_into_view_if_needed()
        franja.screenshot(path=destino / "franja-explorar.png")
        pedidas = len(_NIA_PEDIDAS)
        otra.get_by_test_id("franja-nia-accion").click()
        otra.get_by_test_id("nia-flotante-panel").wait_for(state="visible", timeout=_TIMEOUT_MS)
        ultimo = " ".join(otra.locator("[data-testid=nia-flotante-panel] [data-testid=mensaje-nia]").last.inner_text().split())
        if "Dime un género" not in ultimo or len(_NIA_PEDIDAS) != pedidas:
            problemas.append(f"el botón de la franja no abre la burbuja con cómo filtrar ({ultimo!r})")
        if franja.count():
            problemas.append("la franja de Explorar se queda después de usar su botón")
        otra.reload()
        otra.get_by_test_id("catalogo-busqueda").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(800)
        if otra.get_by_test_id("franja-nia").count():
            problemas.append("la franja de Explorar vuelve a salir el mismo día")
    finally:
        contexto.close()

    # La × la cierra.
    contexto = contexto_nuevo()
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/explorar")
        otra.get_by_test_id("franja-nia-cerrar").click()
        try:
            # Sin zona, el repintado va después del clic: se espera, no se cuenta al instante.
            otra.get_by_test_id("franja-nia").wait_for(state="detached", timeout=5000)
        except TiempoAgotado:
            problemas.append("la × no cierra la franja de Nia")
    finally:
        contexto.close()

    # Comparar: con un juego no hay nada que resumir; con dos sale, bajo el encabezado.
    contexto = contexto_nuevo()
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/comparar?appids=1145360")
        otra.get_by_test_id("comparar-columnas").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(600)
        if otra.get_by_test_id("franja-nia").count():
            problemas.append("la franja de Comparar sale con un solo juego")
        _abrir(otra, f"{base}/comparar?appids=1145360,367520")
        franja = otra.get_by_test_id("franja-nia")
        franja.wait_for(state="visible", timeout=_TIMEOUT_MS)
        texto = " ".join(franja.inner_text().split())
        encabezado = otra.locator(".encabezado").bounding_box()
        capsulas = otra.get_by_test_id("capsulas-comparar").bounding_box()
        caja = franja.bounding_box()
        if "estos 2" not in texto or not (encabezado["y"] + encabezado["height"] <= caja["y"] < capsulas["y"]):
            problemas.append(f"la franja de Comparar no va entre el encabezado y los juegos ({texto!r})")
        otra.screenshot(path=destino / "franja-comparar.png")
    finally:
        contexto.close()

    # Perfil: sin perfil no sale (ni gasta la vez del día); al guardarlo, sale arriba de las
    # sugerencias.
    contexto = contexto_nuevo()
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/perfil")
        otra.get_by_test_id("perfil").wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(600)
        if otra.get_by_test_id("franja-nia").count():
            problemas.append("la franja de Perfil sale sin perfil creado")
        _llenar_perfil(otra)
        franja = otra.get_by_test_id("franja-nia")
        franja.wait_for(state="visible", timeout=_TIMEOUT_MS)
        texto = " ".join(franja.inner_text().split())
        if "Ver sugerencias" not in texto or franja.bounding_box()["y"] > otra.get_by_test_id("sugerencias").bounding_box()["y"]:
            problemas.append(f"la franja de Perfil no va arriba de las sugerencias ({texto!r})")
        franja.scroll_into_view_if_needed()
        otra.screenshot(path=destino / "franja-perfil.png")
    finally:
        contexto.close()

    # En el teléfono, la franja apila el texto y el botón.
    contexto = contexto_nuevo(390, 844)
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/comparar?appids=1145360,367520")
        franja = otra.get_by_test_id("franja-nia")
        franja.wait_for(state="visible", timeout=_TIMEOUT_MS)
        franja.scroll_into_view_if_needed()
        otra.screenshot(path=destino / "franja-comparar-movil.png")
    finally:
        contexto.close()

    if not problemas:
        print("franja:   Explorar, Comparar (con 2+) y Perfil (con perfil) llevan la franja de Nia en la página; "
              "la × la cierra, su botón abre la burbuja y no vuelve el mismo día "
              f"({(destino / 'franja-comparar.png').relative_to(_RAIZ)})")
    return problemas


def _burbuja_no_tapa(pagina: Page, url: str, destino: Path) -> list[str]:
    """Al final de cada vista la burbuja cae sobre espacio vacío, en escritorio y en el
    teléfono; en el teléfono se esconde al bajar y vuelve al subir."""
    problemas = []
    base = url.rstrip("/")
    navegador = pagina.context.browser
    for ancho, alto in ((1440, 900), (390, 844)):
        contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
        _sin_consultas_a_nia(contexto)
        try:
            otra = contexto.new_page()
            for ruta in _VISTAS_CON_BURBUJA:
                _abrir(otra, f"{base}{ruta}")
                otra.get_by_test_id("nia-flotante-burbuja").wait_for(state="visible", timeout=_TIMEOUT_MS)
                _esperar_quietud(otra)
                _al_final(otra)
                tapados = otra.evaluate(_JS_TEXTO_BAJO_LA_BURBUJA)
                if tapados:
                    problemas.append(f"a {ancho} px, al final de {ruta} la burbuja tapa: {tapados[:3]}")
            otra.screenshot(path=destino / f"burbuja-final-{ancho}.png")

            if ancho == 390:
                _abrir(otra, f"{base}/explorar")
                flotante = otra.get_by_test_id("nia-flotante")
                flotante.wait_for(state="visible", timeout=_TIMEOUT_MS)
                _esperar_quietud(otra)
                otra.mouse.move(195, 400)
                for _ in range(4):
                    otra.mouse.wheel(0, 120)
                    otra.wait_for_timeout(120)
                otra.wait_for_timeout(500)
                al_bajar = flotante.get_attribute("data-oculta")
                otra.screenshot(path=destino / "burbuja-al-bajar-390.png")
                otra.mouse.wheel(0, -200)
                otra.wait_for_timeout(600)
                al_subir = flotante.get_attribute("data-oculta")
                otra.screenshot(path=destino / "burbuja-al-subir-390.png")
                if (al_bajar, al_subir) != ("true", "false"):
                    problemas.append(f"a 390 px la burbuja no se esconde al bajar y vuelve al subir ({al_bajar}, {al_subir})")
        finally:
            contexto.close()
    if not problemas:
        print(f"burbuja:  al final de {len(_VISTAS_CON_BURBUJA)} vistas, a 1440 y 390 px, no tapa texto ni controles; "
              "a 390 px se esconde al bajar y vuelve al subir "
              f"({(destino / 'burbuja-al-bajar-390.png').relative_to(_RAIZ)})")
    return problemas


def _zonas_de_toque(pagina: Page, url: str) -> list[str]:
    """Todo lo que se toca mide 44 px o más en el teléfono (390×844)."""
    problemas = []
    base = url.rstrip("/")
    contexto = pagina.context.browser.new_context(viewport={"width": 390, "height": 844})
    _sin_consultas_a_nia(contexto)
    try:
        otra = contexto.new_page()
        for ruta in ("/", "/explorar", f"/juego/{_APPID_FICHA}", "/nia", "/comparar?appids=1145360,367520", "/perfil"):
            _abrir(otra, f"{base}{ruta}")
            otra.locator("main.contenido > :not(router-outlet)").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
            _esperar_quietud(otra)
            chicas = otra.evaluate(_JS_ZONAS_CHICAS)
            if chicas:
                problemas.append(f"en {ruta} hay zonas de toque de menos de 44 px: {chicas[:6]}")
    finally:
        contexto.close()
    if not problemas:
        print("toque:    en las 5 vistas y la ficha, a 390 px, todo lo que se toca mide 44 px o más")
    return problemas


def _tema_dice_su_destino(pagina: Page, url: str, destino: Path) -> list[str]:
    problemas = []
    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    contexto.add_init_script("if (!sessionStorage.getItem('tema-puesto')) { localStorage.setItem('nexplay.tema.v1', 'oscuro'); sessionStorage.setItem('tema-puesto', '1'); }")
    try:
        otra = contexto.new_page()
        _abrir(otra, url)
        boton = otra.get_by_test_id("cambiar-tema")
        boton.wait_for(state="visible", timeout=_TIMEOUT_MS)
        en_oscuro = (" ".join(boton.inner_text().split()), boton.get_attribute("aria-label"), boton.get_attribute("role"))
        otra.locator(".pie-riel").screenshot(path=destino / "tema-en-oscuro.png")
        boton.click()
        otra.wait_for_timeout(300)
        en_claro = (" ".join(boton.inner_text().split()), boton.get_attribute("aria-label"), boton.get_attribute("role"))
        otra.locator(".pie-riel").screenshot(path=destino / "tema-en-claro.png")
        if en_oscuro != ("Modo claro", "Cambiar a modo claro", None) or en_claro != ("Modo oscuro", "Cambiar a modo oscuro", None):
            problemas.append(f"el botón de tema no dice el modo al que cambia ({en_oscuro}, {en_claro})")
        else:
            print("tema:     en oscuro dice «Modo claro» y en claro «Modo oscuro», con su ícono; ya no es un switch")
    finally:
        contexto.close()
    return problemas


def _ficha_lateral(pagina: Page, url: str, destino: Path) -> list[str]:
    """La ficha técnica sin scroll propio y el chat pegado, con el alto de la pantalla."""
    problemas = []
    base = url.rstrip("/")
    for ancho, alto in ((1440, 900), (1366, 674), (390, 844)):
        contexto = pagina.context.browser.new_context(viewport={"width": ancho, "height": alto})
        _sin_consultas_a_nia(contexto)
        try:
            otra = contexto.new_page()
            _abrir(otra, f"{base}/juego/{_APPID_FICHA}")
            metadatos = otra.locator("app-metadatos-juego")
            metadatos.wait_for(state="visible", timeout=_TIMEOUT_MS)
            _esperar_quietud(otra)
            recorte = metadatos.evaluate("m => [m.scrollHeight - m.clientHeight, getComputedStyle(m).overflowY]")
            # En mayúsculas: los títulos de bloque llevan text-transform.
            textos = " ".join(metadatos.inner_text().split()).upper()
            if recorte[0] > 1 or recorte[1] in ("auto", "scroll"):
                problemas.append(f"a {ancho}×{alto} la ficha técnica se desplaza por dentro ({recorte})")
            if "HORAS TÍPICAS" not in textos or "CRÍTICA Y PÚBLICO" not in textos:
                problemas.append(f"a {ancho}×{alto} faltan «Horas típicas» o «Crítica y público» en la ficha técnica")
            chat = otra.locator(".lateral > app-nia")
            alto_chat = chat.bounding_box()["height"]
            minimo = 460 if ancho < 900 else 520
            if alto_chat < minimo:
                problemas.append(f"a {ancho}×{alto} el chat de Nia mide {round(alto_chat)} px (mínimo {minimo})")
            if ancho >= 900:
                otra.evaluate("() => scrollTo(0, 1400)")
                otra.wait_for_timeout(500)
                caja = chat.bounding_box()
                boton = otra.get_by_test_id("nia-enviar").bounding_box()
                if not (8 <= caja["y"] <= 24) or boton["y"] + boton["height"] > alto:
                    problemas.append(f"a {ancho}×{alto} el chat no se queda pegado con «Preguntar» a la vista ({caja}, {boton})")
                otra.evaluate("() => scrollTo(0, 0)")
            otra.screenshot(path=destino / f"ficha-lateral-{ancho}x{alto}.png", full_page=ancho < 900)
            if ancho == 1440:
                metadatos.screenshot(path=destino / "ficha-tecnica-entera.png")
        finally:
            contexto.close()
    if not problemas:
        print("ficha:    la ficha técnica va entera, sin scroll propio, y el chat mide la pantalla y se queda pegado "
              f"({(destino / 'ficha-lateral-1440x900.png').relative_to(_RAIZ)})")
    return problemas


def _trailer_cargando(pagina: Page, url: str, destino: Path) -> list[str]:
    """Mientras carga el tráiler de Explorar se ve la portada del juego en color."""
    problemas = []
    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    # El video no llega mientras se mira: la captura se queda en el «mientras carga».
    detenidas = []
    contexto.route("**/*.m3u8*", lambda ruta: detenidas.append(ruta))
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{url.rstrip('/')}/explorar")
        marco = otra.locator("[data-testid=trailers] [data-testid=portada-ancha]")
        marco.wait_for(state="visible", timeout=_TIMEOUT_MS)
        otra.wait_for_timeout(1500)
        fondo, filtro = marco.evaluate(
            "m => [getComputedStyle(m).backgroundImage, getComputedStyle(m.querySelector('img')).filter]"
        )
        marco.screenshot(path=destino / "trailer-cargando.png")
        for ruta in detenidas:
            ruta.abort()
        if "url(" not in fondo or filtro != "none":
            problemas.append(f"mientras carga el tráiler de Explorar no se ve la portada en color ({fondo[:60]}, {filtro})")
        else:
            print("trailer:  mientras carga, Explorar muestra la portada del juego en color "
                  f"({(destino / 'trailer-cargando.png').relative_to(_RAIZ)})")
    finally:
        contexto.close()
    return problemas


def _comparar_sin_comentarios_citados(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Comparar dice cuánto se valoró y comentó en NexPlay sin citar ningún comentario (son
    públicos y anónimos), y no dice «Sin crítica especializada» de un juego con Metacritic."""
    problemas = []
    usuario = "capturas-comparar-01"
    texto = "Comentario de prueba del recorrido, que no debe citarse en Comparar"
    peticion = urllib.request.Request(
        f"{api}/comentarios/1145360", method="POST", headers={"Content-Type": "application/json"},
        data=json.dumps({"usuario": usuario, "texto": texto}).encode(),
    )
    with urllib.request.urlopen(peticion, timeout=10) as respuesta:
        hilo = json.load(respuesta)
    propio = next((c["id"] for c in reversed(hilo) if c["texto"] == texto), None)
    contexto = pagina.context.browser.new_context(viewport=_VIEWPORT)
    _sin_consultas_a_nia(contexto)
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{url.rstrip('/')}/comparar?appids=1145360,367520")
        columna = otra.locator("[data-testid=columna-comparar][data-appid='1145360']")
        bloque = columna.get_by_test_id("critica-nexplay")
        bloque.wait_for(state="visible", timeout=_TIMEOUT_MS)
        contenido = " ".join(bloque.inner_text().split())
        if texto in contenido or bloque.locator("blockquote").count():
            problemas.append("Comparar cita un comentario público de NexPlay")
        if "Sin crítica especializada" in contenido:
            problemas.append(f"Comparar dice «Sin crítica especializada» de Hades, que tiene Metacritic ({contenido!r})")
        columna.get_by_test_id("critica-publico").screenshot(path=destino / "comparar-en-nexplay.png")
        if not problemas:
            print(f"comparar: «En NexPlay» dice «{contenido}» sin citar comentarios "
                  f"({(destino / 'comparar-en-nexplay.png').relative_to(_RAIZ)})")
    finally:
        contexto.close()
        if propio is not None:
            borrar = urllib.request.Request(
                f"{api}/comentarios/1145360/{propio}?usuario={usuario}", method="DELETE"
            )
            urllib.request.urlopen(borrar, timeout=10).close()
    return problemas


def _bloque4(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """El bloque 4 de las correcciones: la lista de comentarios sin scroll propio, Enter en el
    buscador del chat, el campo de la burbuja a la vista, «Verlos en Comparar» que pregunta
    antes de pisar, «Borrar perfil» con confirmación, «Tu actividad» con los rangos y la
    aclaración de Nia, el aviso del tope y el velo del cajón en el teléfono."""
    problemas = []
    base = url.rstrip("/")
    navegador = pagina.context.browser

    def contexto_nuevo(ancho: int = 1440, alto: int = 900, comparar: list[int] | None = None):
        contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
        _sin_consultas_a_nia(contexto)
        if comparar is not None:
            contexto.add_init_script(f"localStorage.setItem('nexplay.comparar.v1', '{json.dumps(comparar)}')")
        return contexto

    # La lista de comentarios se lee con el scroll de la página.
    usuario, texto = "capturas-bloque4-01", "Comentario de prueba del recorrido del bloque 4"
    peticion = urllib.request.Request(
        f"{api}/comentarios/1145360", method="POST", headers={"Content-Type": "application/json"},
        data=json.dumps({"usuario": usuario, "texto": texto}).encode(),
    )
    with urllib.request.urlopen(peticion, timeout=10) as respuesta:
        propio = next((c["id"] for c in reversed(json.load(respuesta)) if c["texto"] == texto), None)
    contexto = contexto_nuevo()
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/juego/1145360")
        lista = otra.get_by_test_id("lista-comentarios")
        lista.wait_for(state="visible", timeout=_TIMEOUT_MS)
        desborde = lista.evaluate("l => getComputedStyle(l).overflowY")
        if desborde in ("auto", "scroll"):
            problemas.append(f"la lista de comentarios todavía tiene scroll propio ({desborde})")
    finally:
        contexto.close()
        if propio is not None:
            urllib.request.urlopen(urllib.request.Request(
                f"{api}/comentarios/1145360/{propio}?usuario={usuario}", method="DELETE"), timeout=10).close()

    # Enter en el buscador del chat elige el primer resultado.
    contexto = contexto_nuevo()
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/nia")
        otra.get_by_test_id("nia-pregunta").wait_for(state="visible", timeout=_TIMEOUT_MS)
        _preguntar_en_chat(otra, "¿Por qué tiene ese riesgo?")
        buscar = otra.get_by_test_id("nia-elegir-buscar")
        buscar.fill("hades")
        buscar.press("Enter")
        try:
            otra.get_by_test_id("nia-juego").wait_for(state="visible", timeout=_TIMEOUT_MS)
        except TiempoAgotado:
            problemas.append("Enter en el buscador del chat no elige el primer resultado")
    finally:
        contexto.close()

    # La burbuja: con la conversación larga, el campo de escribir sigue a la vista.
    contexto = contexto_nuevo(390, 844)
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/explorar")
        otra.get_by_test_id("nia-flotante-burbuja").click()
        panel = otra.get_by_test_id("nia-flotante-panel")
        panel.wait_for(state="visible", timeout=_TIMEOUT_MS)
        for n in range(6):
            panel.get_by_test_id("nia-pregunta").fill(f"Pregunta de prueba {n + 1} para alargar la conversación")
            panel.get_by_test_id("nia-enviar").click()
            otra.wait_for_function(
                "() => !document.querySelector(\"[data-testid='nia-escribiendo']\")", timeout=_TIMEOUT_MS
            )
            otra.wait_for_timeout(200)
        campo = panel.get_by_test_id("nia-pregunta").bounding_box()
        caja = panel.bounding_box()
        if not campo or campo["y"] + campo["height"] > min(caja["y"] + caja["height"], 844) + 1:
            problemas.append(f"en la burbuja, el campo de escribir se sale de la vista ({campo}, {caja})")
        otra.screenshot(path=destino / "burbuja-campo-visible-390.png")
    finally:
        contexto.close()

    # «Verlos en Comparar» con otros juegos ya elegidos: pregunta; «Agregar» junta, «Reemplazarlos» pisa.
    for accion, esperado in (("agregar", "1938010,1091500,1145360,367520"), ("reemplazar", "1145360,367520")):
        contexto = contexto_nuevo(comparar=[1938010, 1091500])
        try:
            otra = contexto.new_page()
            _abrir(otra, f"{base}/nia")
            otra.get_by_test_id("nia-pregunta").wait_for(state="visible", timeout=_TIMEOUT_MS)
            _preguntar_en_chat(otra, "Compara Hades y Hollow Knight")
            otra.get_by_test_id("nia-comparar").click()
            eleccion = otra.get_by_test_id("nia-comparar-elegir")
            try:
                eleccion.wait_for(state="visible", timeout=5000)
            except TiempoAgotado:
                problemas.append(f"«Verlos en Comparar» no preguntó antes de pisar la comparación ({otra.url})")
                continue
            if accion == "agregar":
                eleccion.screenshot(path=destino / "nia-comparar-elegir.png")
            otra.get_by_test_id(f"nia-comparar-{accion}").click()
            otra.wait_for_url("**/comparar**", timeout=_TIMEOUT_MS)
            if f"appids={esperado.replace(',', '%2C')}" not in otra.url and f"appids={esperado}" not in otra.url:
                problemas.append(f"«{accion}» en Comparar llevó a {otra.url} y se esperaba {esperado}")
        finally:
            contexto.close()

    # Perfil: «Borrar perfil» confirma, «Tu actividad» nombra los rangos y aclara lo de Nia, y
    # la ficha avisa del tope.
    contexto = contexto_nuevo()
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/perfil")
        otra.get_by_test_id("perfil").wait_for(state="visible", timeout=_TIMEOUT_MS)
        _llenar_perfil(otra)
        _abrir(otra, f"{base}/juego/1938010")
        historia = otra.get_by_test_id("historia-texto")
        historia.wait_for(state="visible", timeout=_TIMEOUT_MS)
        if "pasa tu tope de $500" not in " ".join(historia.inner_text().split()):
            problemas.append(f"con tope de $500, WILD HEARTS no avisa que lo pasa ({historia.inner_text()!r})")
        otra.get_by_test_id("historia-perfil").screenshot(path=destino / "historia-tope.png")
        _abrir(otra, f"{base}/perfil#actividad")
        actividad = otra.get_by_test_id("perfil-actividad")
        actividad.wait_for(state="visible", timeout=_TIMEOUT_MS)
        leido = " ".join(actividad.inner_text().split())
        if "Las preguntas a Nia sí se envían" not in leido:
            problemas.append("«Tu actividad» no aclara que las preguntas a Nia sí se envían")
        if "3–6 compras al año · 4 a 9 h por semana · fricción media" not in leido:
            problemas.append(f"«Tu actividad» no resume el perfil con los rangos elegidos ({leido[:200]!r})")
        actividad.screenshot(path=destino / "tu-actividad.png")
        otra.get_by_test_id("borrar-perfil").click()
        # Se espera a que la confirmación se pinte: contarla justo después del clic a veces la
        # leía antes de que Angular la dibujara y reportaba un falso «borra sin confirmar».
        try:
            otra.get_by_test_id("perfil-confirmar-borrado").wait_for(state="visible", timeout=5_000)
        except TiempoAgotado:
            pass
        if not otra.get_by_test_id("perfil-confirmar-borrado").count() or not otra.get_by_test_id("perfil-activo").count():
            problemas.append("«Borrar perfil» borra sin pedir confirmación")
        otra.get_by_test_id("barra-guardar").screenshot(path=destino / "borrar-perfil-confirmacion.png")
        otra.get_by_test_id("perfil-confirmar-borrar").click()
        otra.get_by_test_id("perfil-inactivo").wait_for(state="visible", timeout=_TIMEOUT_MS)
    finally:
        contexto.close()

    # El cajón del menú en el teléfono: velo oscuro detrás y tocarlo lo cierra.
    contexto = contexto_nuevo(390, 844)
    try:
        otra = contexto.new_page()
        _abrir(otra, f"{base}/")
        otra.get_by_test_id("abrir-menu").click()
        velo = otra.get_by_test_id("velo-menu")
        velo.wait_for(state="visible", timeout=_TIMEOUT_MS)
        alfa = _rgb(velo.evaluate("v => getComputedStyle(v).backgroundColor"))[1]
        otra.screenshot(path=destino / "cajon-velo-390.png")
        velo.click(position={"x": 370, "y": 400})
        otra.wait_for_timeout(400)
        if alfa < 0.3 or otra.get_by_test_id("velo-menu").count():
            problemas.append(f"el cajón del teléfono no tiene velo oscuro (alfa {alfa}) o tocarlo no lo cierra")
    finally:
        contexto.close()

    if not problemas:
        print("bloque 4: comentarios sin scroll, Enter elige en el chat, el campo de la burbuja a la vista, "
              "«Verlos en Comparar» pregunta (agregar/reemplazar), «Borrar perfil» confirma, «Tu actividad» "
              "con rangos y lo de Nia, aviso del tope y velo del cajón "
              f"({(destino / 'nia-comparar-elegir.png').relative_to(_RAIZ)})")
    return problemas


def _angular_correcciones(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Lo que salió de probar el sitio en producción: Explorar sin resultados, la franja de
    Nia, la burbuja que no tapa, la ficha técnica entera, el tema, el tráiler cargando y las
    zonas de toque. (Precio, la nota del histograma y la metodología repetida se revisan en
    _angular_5_vistas; los controles del video, en _controles_del_video.)"""
    return (
        _explorar_sin_resultados(pagina, url, destino, api)
        + _franja_nia(pagina, url, destino)
        + _burbuja_no_tapa(pagina, url, destino)
        + _ficha_lateral(pagina, url, destino)
        + _tema_dice_su_destino(pagina, url, destino)
        + _trailer_cargando(pagina, url, destino)
        + _zonas_de_toque(pagina, url)
        + _comparar_sin_comentarios_citados(pagina, url, destino, api)
        + _bloque4(pagina, url, destino, api)
    )


def _capturar_angular(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    return (
        _angular_catalogo(pagina, url, destino, api)
        + _angular_ficha(pagina, url, destino)
        + _angular_descripcion(pagina, url, api)
        + _angular_video(pagina, url, destino, api)
        + _angular_6b(pagina, url, destino, api)
        + _angular_como_funciona(pagina, url, destino)
        + _angular_estrellas(pagina, url, destino)
        + _angular_panel_nia(pagina, url, destino)
        + _angular_voto_nia(pagina, url, destino)
        + _angular_nia_catalogo(pagina, url, destino)
        + _angular_campo_nia(pagina, url)
        + _angular_carrusel(pagina, url, destino, api)
        + _angular_hilo(pagina, url, destino)
        + _angular_perfil(pagina, url, destino, api)
        + _angular_6c(pagina, url, destino, api)
        + _angular_comparar(pagina, url, destino)
        + _angular_6d(pagina, url, destino, api)
        + _angular_5_vistas(pagina, url, destino, api)
        + _angular_6f(pagina, url, destino, api)
        + _angular_nia_flotante(pagina, url, destino)
        + _angular_movimiento(pagina, url)
        + _angular_barra_y_tema(pagina, url, destino)
        + _angular_letra_y_vocabulario(pagina, url)
        + _angular_correcciones(pagina, url, destino, api)
    )


# Respuesta fija para /nia. El script NUNCA habla con el modelo de lenguaje: con una
# clave con crédito en .env, cada corrida gastaría consultas de OpenAI, y lo que se
# verifica aquí es la interfaz (que el chat muestre la respuesta y su aviso de modo),
# no lo que responde el modelo. Las pruebas con OpenAI real se hacen a mano.
_ID_RESPUESTA_FALSA = "00000000-0000-4000-8000-000000000000"
_NIA_FALSA = json.dumps({
    "respuesta": "Respuesta de prueba del script de capturas: no se consultó ningún modelo.",
    "modo": "demostracion",
    "modelo": None,
    "aviso": "Respuesta simulada por calidad/capturar_ui.py; la API no recibió la pregunta.",
    # Con id se puede recorrer el voto sin gastar una consulta. El PUT del voto también se
    # intercepta: esta respuesta no existe en la base de la API y daría 404, y lo que se
    # revisa aquí es la interfaz. El almacén de verdad lo prueba verificar_nia.py.
    "id": _ID_RESPUESTA_FALSA,
    "version_prompt": "reglas",
    "pasos": [],
    "juegos": [],
    "sugerencias": [],
    "pide_juego": False,
    "pide_perfil": False,
})
# Lo que la interfaz mandó a /nia, para revisar que el perfil no viaje y que vaya el hilo.
_NIA_CUERPOS: list[dict] = []


def _respuesta_falsa(cuerpo: dict) -> str:
    """La respuesta fija, salvo en los casos que la interfaz pinta distinto: una pregunta de
    un juego sin juego fijado (pide el juego), una fuera de tema (trae los avisos) y «¿Qué
    me recomiendas?» con sugerencias."""
    respuesta = json.loads(_NIA_FALSA)
    pregunta = next((m["contenido"] for m in reversed(cuerpo.get("mensajes", [])) if m.get("rol") == "usuario"), "")
    if "appid" not in cuerpo and "ese riesgo" in pregunta.lower():
        respuesta.update(respuesta="¿De qué juego hablamos? 👀 Búscalo aquí y te lo explico.", pide_juego=True)
    elif "clima" in pregunta.lower():
        respuesta.update(
            respuesta="Eso no lo sé con estos datos 🙈 Puedo filtrar el catálogo por género, precio o riesgo. ¿Qué se te antoja?",
            fuera_de_tema=True,
        )
    elif pregunta.lower().startswith("compara"):
        respuesta.update(
            respuesta="Hades y Hollow Knight tienen riesgo bajo 📊 ¿Los abro lado a lado en Comparar?",
            juegos=[1145360, 367520],
        )
    elif "recomiendas" in pregunta.lower():
        sugeridas = [s["appid"] for s in cuerpo.get("sugerencias", [])][:3]
        respuesta.update(
            respuesta="Sugerencias de prueba del script de capturas ✨ ¿Te explico alguna?",
            sugerencias=sugeridas,
            pide_perfil=not sugeridas,
        )
    return json.dumps(respuesta)


# Cuántas veces la interfaz pidió /nia y cuántas respondió la intercepción. Si las dos
# cifras coinciden, ninguna llegó a la API (ni, por tanto, al modelo de lenguaje).
_NIA_PEDIDAS: list[str] = []
_NIA_INTERCEPTADAS: list[str] = []


# El globito de Nia sale una vez por vista y por día: en el recorrido se da por visto, para
# que no tape nada en las capturas. Solo la comprobación del globito lo deja salir.
_GLOBITO_YA_VISTO = """(() => { try {
  const d = new Date(); const dos = (n) => String(n).padStart(2, '0');
  const hoy = `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
  localStorage.setItem('nexplay.globito-nia.v1', JSON.stringify({ explorar: hoy, perfil: hoy, comparar: hoy }));
} catch (e) {} })();"""


def _sin_consultas_a_nia(contexto, con_globito: bool = False) -> None:
    """Intercepta /nia en todo el contexto del navegador, antes de cualquier paso."""
    if not con_globito:
        contexto.add_init_script(_GLOBITO_YA_VISTO)

    def anotar(peticion) -> None:
        # Solo el POST de la API: /nia también es una ruta del sitio, y su documento
        # es un GET que no tiene nada que ver con el modelo de lenguaje.
        if peticion.method == "POST" and peticion.url.split("?")[0].rstrip("/").endswith("/nia"):
            _NIA_PEDIDAS.append(peticion.url)

    def responder(ruta) -> None:
        if ruta.request.method != "POST":
            ruta.fallback()
            return
        _NIA_INTERCEPTADAS.append(ruta.request.url)
        cuerpo = ruta.request.post_data_json or {}
        _NIA_CUERPOS.append(cuerpo)
        ruta.fulfill(status=200, content_type="application/json", body=_respuesta_falsa(cuerpo))

    def responder_voto(ruta) -> None:
        """El voto de una respuesta que solo existió en el navegador: se contesta con lo
        que se mandó, que es lo que haría la API si la respuesta fuera suya."""
        if ruta.request.method == "DELETE":
            cuerpo = {"id_respuesta": _ID_RESPUESTA_FALSA, "voto": None, "motivo": None}
        else:
            enviado = ruta.request.post_data_json or {}
            motivo = enviado.get("motivo")
            cuerpo = {
                "id_respuesta": _ID_RESPUESTA_FALSA,
                "voto": enviado.get("voto"),
                "motivo": motivo if enviado.get("voto") == -1 else None,
            }
        ruta.fulfill(status=200, content_type="application/json", body=json.dumps(cuerpo))

    contexto.on("request", anotar)
    contexto.route("**/nia", responder)
    contexto.route("**/nia/valoracion/**", responder_voto)


def capturar(url: str, api: str) -> int:
    destino = _DESTINO
    destino.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            contexto = navegador.new_context(viewport=_VIEWPORT)
            # Desde que el tema sale de prefers-color-scheme, un Chromium sin preferencia
            # declarada abre en claro y las capturas de referencia cambiaban de tema de una
            # corrida a otra. El recorrido general va en oscuro; _angular_barra_y_tema es
            # quien recorre los dos temas a propósito.
            contexto.add_init_script("localStorage.setItem('nexplay.tema.v1', 'oscuro')")
            _sin_consultas_a_nia(contexto)
            pagina = contexto.new_page()
            problemas = _capturar_angular(pagina, url, destino, api)
        finally:
            navegador.close()
    print(f"nia:      la interfaz pidió /nia {len(_NIA_PEDIDAS)} veces; interceptadas {len(_NIA_INTERCEPTADAS)}, "
          f"llegaron a la API {len(_NIA_PEDIDAS) - len(_NIA_INTERCEPTADAS)}")
    if len(_NIA_PEDIDAS) != len(_NIA_INTERCEPTADAS):
        problemas.append("alguna consulta a /nia no pasó por la intercepción")
    for problema in problemas:
        print(f"PROBLEMA: {problema}")
    return 1 if problemas else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captura la UI de NexPlay (Angular).")
    parser.add_argument("--url", default=_URL, help="URL del frontend (por defecto %(default)s)")
    parser.add_argument("--api", default="http://localhost:8000", help="API con la que comparar (por defecto %(default)s)")
    args = parser.parse_args()
    sys.exit(capturar(args.url, args.api))
