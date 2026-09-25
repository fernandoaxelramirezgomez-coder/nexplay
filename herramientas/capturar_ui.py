"""Captura la UI de NexPlay con Chromium headless, para revisar los cambios
visuales sin abrir un navegador a mano.

Guarda en docs/capturas/angular/:
  catalogo.png, catalogo-inicio.png, catalogo-filtrado.png
  ficha-wild-hearts.png, perfil.png, ficha-con-perfil.png, comparar.png
y verifica contra la API (--api): total de tarjetas, conteo y orden de cada
estante, filtro reactivo, factores de la ficha, entrada directa por URL, appid
inexistente, perfil que sobrevive a la recarga, la historia del perfil sin que
cambie el nivel de riesgo, y la comparación sincronizada con ?appids=.

docs/capturas/ está ignorada por git; la captura del README es otra,
docs/captura-interfaz.png, y este script no la toca. Revisa además que no
aparezca "abandono" ni un score de riesgo con decimales.

Requiere la API y el frontend corriendo (uvicorn api.main:app y npx ng serve en
frontend/). Una sola vez:
  pip install -r requirements-dev.txt
  playwright install chromium
  sudo playwright install-deps chromium   # librerías del sistema (Linux/WSL)

Uso:
  python herramientas/capturar_ui.py [--url URL]
"""

import argparse
import json
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
    _abrir(pagina, url)
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
    pagina.wait_for_function(
        "() => (document.querySelector(\"[data-testid='segunda-opinion'] p\")?.textContent || '').trim().length > 20",
        timeout=_TIMEOUT_MS,
    )
    factores = pagina.get_by_test_id("factores").inner_text()
    if "nota de Metacritic" in factores:
        problemas.append("ficha de Wild Hearts: muestra 'nota de Metacritic' aunque el juego no tiene nota")
    plano = " ".join(factores.lower().split())
    if "cobertura de crítica especializada" not in plano or "aumenta el riesgo" not in plano:
        problemas.append(f"ficha de Wild Hearts: falta el factor de cobertura de crítica ({plano[:120]})")
    _esperar_portadas(pagina, "[data-testid='ficha'] img")
    _esperar_quietud(pagina)
    ruta = destino / "ficha-wild-hearts.png"
    pagina.screenshot(path=ruta, full_page=True)
    print(f"ficha:    {ruta.relative_to(_RAIZ)} ({pagina.get_by_test_id('ficha-nombre').inner_text()})")
    problemas += _revisar_vocabulario(pagina, "ficha")

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


def _angular_sugerencias(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Las sugerencias por afinidad de /perfil: solo con perfil declarado, cada una con el
    género que coincidió y su banda al lado, y sin mezclar afinidad con riesgo."""
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/perfil")
    seccion = pagina.get_by_test_id("sugerencias")
    try:
        seccion.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        return ["con perfil declarado no aparece la sección de sugerencias en /perfil"]

    declarados = {"acción", "rol"}  # los mismos que eligió el paso anterior
    catalogo = {j["appid"]: j for j in _catalogo_api(api)}
    tarjetas = pagina.get_by_test_id("sugerencia")
    if not tarjetas.count():
        return problemas + ["la sección de sugerencias no muestra ningún juego"]
    for i in range(tarjetas.count()):
        tarjeta = tarjetas.nth(i)
        appid = int(tarjeta.get_attribute("data-appid"))
        generos = {g.lower() for g in catalogo[appid]["generos"]}
        if not generos & declarados:
            problemas.append(f"sugiere {catalogo[appid]['nombre']}, que no comparte ningún género declarado")
        porque = tarjeta.get_by_test_id("sugerencia-porque").inner_text()
        if "coincide en" not in porque.lower():
            problemas.append(f"la sugerencia {appid} no explica qué coincidió ('{porque[:60]}')")
        if not tarjeta.get_by_test_id("pildora-banda").count():
            problemas.append(f"la sugerencia {appid} no muestra la banda de riesgo")
        # La nota que lleva a la segunda opinión es solo de la banda alta.
        nota = tarjeta.get_by_test_id("sugerencia-nota-alto")
        es_alto = catalogo[appid]["banda_riesgo"] == "alto"
        if es_alto and not nota.count():
            problemas.append(f"la sugerencia {appid} es de banda alta y no dice dónde están los motivos")
        if not es_alto and nota.count():
            problemas.append(f"la sugerencia {appid} no es de banda alta y aun así lleva la nota")
        if es_alto and "segunda opinión" not in nota.inner_text().lower():
            problemas.append(f"la nota de {appid} no menciona la segunda opinión")

    texto = " ".join(seccion.inner_text().split()).lower()
    for frase in ("recomendación de compra",):  # la entrada aclara justo lo que no es
        if frase not in texto:
            problemas.append(f"la sección de sugerencias no aclara que no es una {frase}")
    for frase in _PROMESA_DE_AJUSTE + ("te recomiendo", "deberías", "conviene", "vale la pena", "buena compra"):
        if frase in texto:
            problemas.append(f"las sugerencias usan una fórmula prohibida ('{frase}')")

    _esperar_portadas(pagina, "[data-testid='sugerencias'] img")
    _esperar_quietud(pagina)
    ruta = destino / "sugerencias-perfil.png"
    seccion.screenshot(path=ruta)
    altos = [t for t in (tarjetas.nth(i) for i in range(tarjetas.count()))
             if t.get_by_test_id("sugerencia-nota-alto").count()]
    if altos:
        ruta_alto = destino / "sugerencia-banda-alta.png"
        altos[0].screenshot(path=ruta_alto)
        print(f"afinidad: {len(altos)} de {tarjetas.count()} son de banda alta y dicen dónde están los motivos "
              f"({ruta_alto.relative_to(_RAIZ)})")
    print(f"afinidad: {tarjetas.count()} sugerencias, todas con género coincidente y banda "
          f"({ruta.relative_to(_RAIZ)})")
    return problemas


def _angular_perfil(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    problemas = []
    _abrir(pagina, f"{url.rstrip('/')}/perfil")
    pagina.get_by_test_id("perfil").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("chip-genero").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
    problemas += _revisar_vocabulario(pagina, "perfil")
    _esperar_quietud(pagina)
    pagina.screenshot(path=destino / "perfil.png", full_page=True)

    pagina.get_by_test_id("grupo-compras").get_by_text("Muchos (más de 15 al año)").click()
    for genero in ("Acción", "Rol"):
        pagina.locator(f"[data-testid='chip-genero'][data-genero='{genero}']").click()
    pagina.get_by_test_id("crear-perfil").click()

    pagina.get_by_test_id("perfil-activo").wait_for(state="visible", timeout=_TIMEOUT_MS)
    try:
        pagina.wait_for_url(lambda url: not url.rstrip("/").endswith("/perfil"), timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        problemas.append(f"tras crear el perfil no volvió al catálogo ({pagina.url})")
    pagina.reload()
    try:
        pagina.get_by_test_id("perfil-activo").wait_for(state="visible", timeout=_TIMEOUT_MS)
        print("perfil:   creado, y sigue activo después de recargar")
    except TiempoAgotado:
        problemas.append("el perfil no sobrevivió a la recarga")

    problemas += _angular_sugerencias(pagina, url, destino, api)

    _abrir(pagina, f"{url.rstrip('/')}/juego/{_APPID_FICHA}")
    pagina.get_by_test_id("ficha-nombre").wait_for(state="visible", timeout=_TIMEOUT_MS)
    veredicto = pagina.get_by_test_id("ficha-veredicto").inner_text()
    # Modelo de título: con o sin perfil, la banda es la misma y el rótulo también.
    if not veredicto.lower().startswith("riesgo general"):
        problemas.append(f"con perfil declarado, el veredicto cambió de rótulo: '{veredicto.splitlines()[0]}'")
    # La historia reemplaza a la línea suelta de afinidad: con perfil se cuenta entera.
    historia = pagina.get_by_test_id("historia-texto").inner_text()
    plano = " ".join(historia.split())
    if "dentro" not in plano.lower() or "Acción" not in plano:
        problemas.append(f"la historia no reconoce el género en común ('{plano[:120]}')")
    if "arrepentimiento temprano" not in plano.lower():
        problemas.append("la historia no usa el vocabulario del proyecto")
    if pagina.get_by_test_id("historia-sin-perfil").count():
        problemas.append("con perfil declarado, la historia sigue pidiendo crear uno")
    _esperar_portadas(pagina, "[data-testid='ficha'] img")
    _esperar_quietud(pagina)
    pagina.screenshot(path=destino / "ficha-con-perfil.png", full_page=True)
    print(f"ficha:    ficha-con-perfil.png ({veredicto.splitlines()[0]}; historia: {plano[:70]}…)")

    # Nia cuenta la misma historia con sus palabras, aunque sea en modo demostración.
    pagina.get_by_test_id("historia-pedir-nia").click()
    try:
        pagina.get_by_test_id("historia-nia").wait_for(state="visible", timeout=_TIMEOUT_MS)
        modo = "demostración" if pagina.get_by_test_id("historia-nia-demo").count() else "modelo"
        print(f"historia: Nia la cuenta con sus palabras ({modo})")
    except TiempoAgotado:
        problemas.append("el botón 'Que Nia lo cuente' no trajo respuesta")
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


def _angular_comparar(pagina: Page, url: str, destino: Path) -> list[str]:
    problemas = []
    elegidos = [_APPID_FICHA, 271590, 1091500]  # Wild Hearts, GTA V Legacy, Cyberpunk 2077

    _abrir(pagina, url)
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

    _abrir(pagina, f"{url.rstrip('/')}/comparar")
    try:
        pagina.get_by_test_id("comparar-vacio").wait_for(state="visible", timeout=_TIMEOUT_MS)
        print("vacío:    /comparar sin appids explica cómo elegir juegos")
    except TiempoAgotado:
        problemas.append("/comparar sin appids no muestra el estado vacío")
    return problemas


def _angular_nia_flotante(pagina: Page, url: str, destino: Path) -> list[str]:
    """La burbuja de la esquina: pide un juego antes de conversar, y no sale en la ficha."""
    problemas = []

    _abrir(pagina, url)
    pagina.get_by_test_id("nia-flotante-burbuja").wait_for(state="visible", timeout=_TIMEOUT_MS)
    pagina.get_by_test_id("nia-flotante-burbuja").click()
    pagina.get_by_test_id("nia-flotante-panel").wait_for(state="visible", timeout=_TIMEOUT_MS)

    # Sin juego elegido no hay chat todavía: primero hay que decir de cuál hablar.
    if pagina.get_by_test_id("nia").count():
        problemas.append("la burbuja abre el chat sin preguntar antes de qué juego")

    pagina.get_by_test_id("nia-flotante-buscar").fill("wild hearts")
    pagina.wait_for_function(
        "() => document.querySelectorAll(\"[data-testid='nia-flotante-sugerencia']\").length === 1",
        timeout=_TIMEOUT_MS,
    )
    _esperar_portadas(pagina, "[data-testid='nia-flotante-panel'] img")
    _esperar_quietud(pagina)
    ruta = destino / "nia-flotante-elegir.png"
    pagina.get_by_test_id("nia-flotante-panel").screenshot(path=ruta)
    print(f"burbuja:  {ruta.relative_to(_RAIZ)} (pide de qué juego hablar)")

    pagina.get_by_test_id("nia-flotante-sugerencia").first.click()
    pagina.get_by_test_id("nia").wait_for(state="visible", timeout=_TIMEOUT_MS)
    elegido = pagina.get_by_test_id("nia-flotante-juego").inner_text()
    if "WILD HEARTS" not in elegido.upper():
        problemas.append(f"la burbuja no abrió el chat del juego elegido ('{elegido}')")

    pagina.get_by_test_id("sugerencia-nia").first.click()
    try:
        pagina.get_by_test_id("mensaje-nia").first.wait_for(state="visible", timeout=_TIMEOUT_MS)
        pagina.wait_for_function(
            "() => !document.querySelector(\"[data-testid='nia-escribiendo']\")", timeout=_TIMEOUT_MS
        )
    except TiempoAgotado:
        problemas.append("la burbuja no obtuvo respuesta de Nia")
    _esperar_quietud(pagina)
    ruta = destino / "nia-flotante-chat.png"
    pagina.get_by_test_id("nia-flotante-panel").screenshot(path=ruta)
    print(f"burbuja:  {ruta.relative_to(_RAIZ)} ({elegido})")
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

    _abrir(pagina, url)
    pagina.get_by_test_id("nia-flotante-burbuja").wait_for(state="visible", timeout=_TIMEOUT_MS)
    return problemas


def _angular_movimiento(pagina: Page, url: str) -> list[str]:
    """El logo respira, pero se queda quieto si el sistema pide menos movimiento."""
    problemas = []
    navegador = pagina.context.browser
    if navegador is None:
        return ["no se pudo abrir un contexto con prefers-reduced-motion"]

    medir = """() => {
        const img = document.querySelector('.marca img');
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
        quieta.wait_for_selector(".marca img", timeout=_TIMEOUT_MS)
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


def _angular_carrusel(pagina: Page, url: str, destino: Path) -> list[str]:
    """El ejemplo del inicio: curados de las tres bandas, flechas, pausa y rotación."""
    problemas = []
    _abrir(pagina, url)
    carrusel = pagina.get_by_test_id("hero-carrusel")
    carrusel.wait_for(state="visible", timeout=_TIMEOUT_MS)
    if pagina.locator("[data-testid='hero-ejemplo'] .vistazo-lista li").count() != 3:
        problemas.append("la tarjeta del ejemplo perdió sus tres bullets")

    # Una vuelta completa con la flecha: qué juegos y qué bandas hay.
    pagina.get_by_test_id("hero-siguiente").focus()  # el foco también lo pausa
    vistos: dict[str, str] = {}
    for _ in range(6):
        appid = _ejemplo_actual(pagina)
        banda = pagina.locator("[data-testid='hero-ejemplo'] [data-testid='pildora-banda']").get_attribute("data-banda")
        vistos.setdefault(appid, banda)
        pagina.get_by_test_id("hero-siguiente").click()
        pagina.wait_for_function(
            "anterior => document.querySelector(\"[data-testid='hero-ejemplo']\")?.dataset.appid !== anterior",
            arg=appid, timeout=_TIMEOUT_MS,
        )
    if set(vistos.values()) != {"bajo", "medio", "alto"}:
        problemas.append(f"el carrusel no cubre las tres bandas: {vistos}")
    print(f"carrusel: {len(vistos)} ejemplos curados, bandas {sorted(set(vistos.values()))}")

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
    pagina.locator("[data-testid='hero-ejemplo'] .vistazo-cuerpo").hover()
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


def _avanza_el_video(pagina: Page) -> bool:
    antes = pagina.get_by_test_id("portada-video").evaluate("v => v.currentTime")
    pagina.wait_for_timeout(1500)
    despues = pagina.get_by_test_id("portada-video").evaluate("v => v.currentTime")
    return despues > antes


def _opacidad(localizador) -> float:
    return float(localizador.evaluate("b => getComputedStyle(b).opacity"))


def _pausa_del_video(pagina: Page, destino: Path) -> list[str]:
    """WCAG 2.2.2: un botón que pausa el tráiler, oculto hasta hover o foco de teclado."""
    problemas = []
    boton = pagina.get_by_test_id("portada-pausa")
    video = pagina.get_by_test_id("portada-video")
    pagina.mouse.move(0, 0)
    pagina.wait_for_timeout(400)
    if _opacidad(boton) > 0.05:
        problemas.append("el botón de pausa se ve sin hover ni foco")
    pagina.get_by_test_id("portada-ancha").hover()
    pagina.wait_for_timeout(400)
    if _opacidad(boton) < 0.95:
        problemas.append("el botón de pausa no aparece al pasar el ratón")
    pagina.mouse.move(0, 0)

    # Con teclado: foco visible, Enter pausa y el video deja de avanzar.
    # Un Tab antes: el navegador solo pinta :focus-visible si la última interacción fue
    # de teclado, y focus() por script no cuenta como tal.
    pagina.keyboard.press("Tab")
    boton.focus()
    pagina.wait_for_timeout(400)
    if _opacidad(boton) < 0.95:
        problemas.append("el botón de pausa no aparece con foco de teclado")
    ruta = destino / "video-pausa-foco.png"
    pagina.get_by_test_id("portada-ancha").screenshot(path=ruta)
    pagina.keyboard.press("Enter")
    pagina.wait_for_function("() => document.querySelector('[data-testid=portada-video]').dataset.estado === 'pausado'", timeout=_TIMEOUT_MS)
    etiqueta = boton.get_attribute("aria-label")
    quieto = video.evaluate("v => v.paused")
    if not quieto or _avanza_el_video(pagina) or etiqueta != "Reproducir el tráiler":
        problemas.append(f"Enter en el botón no pausa el tráiler (paused={quieto}, etiqueta={etiqueta!r})")
    pagina.keyboard.press("Enter")
    pagina.wait_for_timeout(300)
    if not _avanza_el_video(pagina) or boton.get_attribute("aria-label") != "Pausar el tráiler":
        problemas.append("Enter otra vez no reanuda el tráiler")
    if not problemas:
        print(f"video:    botón de pausa: oculto en reposo, aparece con hover y con foco; Enter pausa y reanuda ({ruta.relative_to(_RAIZ)})")
    pagina.locator("body").focus()
    return problemas


_APPID_SIN_VIDEO = 690790  # DiRT Rally 2.0, el único del catálogo sin tráiler


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
    if estado == "reproduciendo":
        problemas += _pausa_del_video(pagina, destino)
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
        else:
            print("video:    con prefers-reduced-motion no se pide el video; queda la portada en gris")
    finally:
        contexto.close()
    return problemas


def _angular_como_funciona(pagina: Page, url: str, destino: Path) -> list[str]:
    """La página central: nav, cuatro pasos y la metodología, que el pie ya no repite."""
    problemas = []
    base = url.rstrip("/")
    _abrir(pagina, base)
    # El saludo de Nia vive en el pie de la portada, antes del enlace, y en ningún otro lado.
    orden = pagina.evaluate(
        "() => [...document.querySelectorAll('footer [data-testid]')].map(e => e.dataset.testid)"
    )
    if pagina.locator(".hero [data-testid='nia-mascota']").count():
        problemas.append("el saludo de Nia sigue arriba, en la portada")
    if "nia-mascota" not in orden or orden.index("nia-mascota") > orden.index("enlace-metodologia"):
        problemas.append(f"el saludo de Nia no está en el pie antes del enlace de metodología ({orden})")
    else:
        print("saludo:   en el pie de la portada, antes del enlace de metodología")
    if pagina.locator("footer [data-testid='metodologia']").count():
        problemas.append("el pie sigue repitiendo el texto de la metodología")
    pagina.locator("footer [data-testid='enlace-metodologia']").click()
    metodologia = pagina.get_by_test_id("metodologia")
    try:
        metodologia.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        return problemas + ["el enlace del pie no lleva a la metodología"]
    pagina.wait_for_timeout(600)
    if not pagina.url.split("#")[0].endswith("/como-funciona"):
        problemas.append(f"el enlace del pie lleva a {pagina.url}")
    caja = metodologia.bounding_box()
    if not caja or caja["y"] > pagina.viewport_size["height"]:
        problemas.append("el enlace del pie no baja hasta la metodología")
    if pagina.get_by_test_id("nia-mascota").count():
        problemas.append("el saludo de Nia aparece fuera de la portada")
    if pagina.get_by_test_id("nav-como-funciona").get_attribute("aria-current") != "page":
        problemas.append("'Cómo funciona' no queda marcado en el nav")
    pasos = pagina.get_by_test_id("paso").count()
    if pasos != 4:
        problemas.append(f"'Cómo funciona' tiene {pasos} pasos, no 4")
    problemas += _revisar_vocabulario(pagina, "cómo funciona")
    pagina.evaluate("window.scrollTo(0, 0)")
    _esperar_quietud(pagina)
    ruta = destino / "como-funciona.png"
    pagina.screenshot(path=ruta, full_page=True)
    print(f"cómo funciona: nav, {pasos} pasos y la metodología; el pie solo enlaza ({ruta.relative_to(_RAIZ)})")

    # Sin perfil, la ficha ofrece crearlo con un botón de la misma jerarquía que "Comparar".
    _abrir(pagina, f"{base}/juego/{_APPID_FICHA}")
    boton = pagina.get_by_test_id("historia-crear-perfil")
    try:
        boton.wait_for(state="visible", timeout=_TIMEOUT_MS)
    except TiempoAgotado:
        return problemas + ["sin perfil, la ficha no muestra el botón 'Crear tu perfil'"]
    enlace = pagina.get_by_test_id("factores-como-calculamos")
    if not enlace.count() or "/como-funciona" not in (enlace.get_attribute("href") or ""):
        problemas.append("'Qué mueve esta estimación' no enlaza a /como-funciona")
    elif not pagina.get_by_test_id("factores").locator("app-factores-modelo").count():
        problemas.append("la sección de factores perdió su contenido al agregar el enlace")
    else:
        print("factores: la sección conserva los factores y enlaza a 'Cómo calculamos esta estimación'")
    clases = boton.get_attribute("class") or ""
    comparar = pagina.get_by_test_id("boton-comparar").get_attribute("class") or ""
    if "boton-fantasma" not in clases or "boton-fantasma" not in comparar:
        problemas.append(f"'Crear tu perfil' no tiene la jerarquía de 'Comparar' ({clases!r} vs {comparar!r})")
    ruta = destino / "historia-crear-perfil.png"
    pagina.get_by_test_id("historia-perfil").screenshot(path=ruta)
    boton.click()
    try:
        pagina.get_by_test_id("perfil").wait_for(state="visible", timeout=_TIMEOUT_MS)
        print(f"perfil:   sin perfil, la ficha ofrece 'Crear tu perfil' como botón y lleva a /perfil ({ruta.relative_to(_RAIZ)})")
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


def _preguntar_desde_el_globo(pagina: Page) -> list[str]:
    """El botón del globo deja el foco en el campo del chat, visible, sin consultar /nia."""
    consultas = []

    def anotar(peticion) -> None:
        if peticion.url.rstrip("/").endswith("/nia"):
            consultas.append(peticion.url)

    pagina.on("request", anotar)
    pagina.evaluate("window.scrollTo(0, 0)")
    pagina.get_by_test_id("nia-reaccion-preguntar").click()
    try:
        pagina.wait_for_function(
            "() => document.activeElement?.dataset?.testid === 'nia-pregunta'", timeout=_TIMEOUT_MS
        )
    except TiempoAgotado:
        return ["'Preguntarle a Nia' no deja el foco en el campo del chat"]
    finally:
        pagina.wait_for_timeout(800)  # el scroll es suave
        pagina.remove_listener("request", anotar)
    campo = pagina.get_by_test_id("nia-pregunta").bounding_box()
    alto = pagina.viewport_size["height"]
    if not campo or campo["y"] < 0 or campo["y"] + campo["height"] > alto:
        return [f"tras 'Preguntarle a Nia' el campo del chat queda fuera de pantalla ({campo})"]
    if consultas:
        return [f"'Preguntarle a Nia' consultó /nia por su cuenta ({len(consultas)} veces)"]
    print("nia v2:   'Preguntarle a Nia' lleva el foco al chat, a la vista, sin consultar /nia")
    return []


def _angular_nia_reaccion(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    """Nia v2 en la ficha: una emoción por banda, la misma banda que el veredicto."""
    problemas = []
    base = url.rstrip("/")
    elegidos = _un_juego_por_banda(api)
    if set(elegidos) != {"bajo", "medio", "alto"}:
        return [f"el catálogo no tiene juegos de las tres bandas ({sorted(elegidos)})"]

    for banda, appid in elegidos.items():
        _abrir(pagina, f"{base}/juego/{appid}")
        reaccion = pagina.get_by_test_id("nia-reaccion")
        try:
            reaccion.wait_for(state="visible", timeout=_TIMEOUT_MS)
        except TiempoAgotado:
            problemas.append(f"{banda} ({appid}): Nia no aparece en la ficha")
            continue

        # La única fuente de verdad es la banda que ya muestra el veredicto.
        veredicto = pagina.get_by_test_id("ficha-veredicto").get_attribute("data-banda")
        de_nia = reaccion.get_attribute("data-banda")
        if de_nia != veredicto:
            problemas.append(f"{appid}: Nia reacciona a '{de_nia}' y el veredicto dice '{veredicto}'")
        imagen = pagina.get_by_test_id("nia-reaccion-imagen").get_attribute("src") or ""
        if not imagen.endswith(f"nia/ficha-{veredicto}.png"):
            problemas.append(f"{appid}: banda {veredicto} con la imagen {imagen}")
        texto = " ".join(pagina.get_by_test_id("nia-reaccion-texto").inner_text().split())
        if _REACCION_ESPERADA[veredicto] not in texto:
            problemas.append(f"{appid}: el texto no corresponde a la banda {veredicto} ('{texto[:70]}')")

        for repetida in (veredicto, "arrepentimiento", "riesgo"):
            if re.search(rf"\b{repetida}\b", texto.lower()):
                problemas.append(f"{appid}: el globo repite '{repetida}' del veredicto ('{texto[:70]}')")

        _esperar_portadas(pagina, "[data-testid='ficha'] img")
        _esperar_quietud(pagina)
        ruta = destino / f"nia-reaccion-{banda}.png"
        pagina.get_by_test_id("segunda-opinion").screenshot(path=ruta)
        nombre = pagina.get_by_test_id("ficha-nombre").inner_text()
        print(f"nia v2:   {banda:5} {nombre} → {reaccion.get_attribute('data-emocion')} "
              f"({ruta.relative_to(_RAIZ)})")

    # "Preguntarle a Nia" solo lleva al campo del chat: no le pregunta nada.
    problemas += _preguntar_desde_el_globo(pagina)

    # Solo en la ficha.
    for ruta_app, donde in (("/", "catálogo"), ("/comparar", "comparar"), ("/perfil", "perfil")):
        _abrir(pagina, f"{base}{ruta_app}")
        pagina.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
        if pagina.get_by_test_id("nia-reaccion").count():
            problemas.append(f"Nia v2 aparece en {donde}, y solo debe estar en la ficha")
    print("nia v2:   ausente en el catálogo, /comparar y /perfil")

    # Si el PNG no carga, el globo con el texto se queda.
    pagina.route("**/nia/ficha-*.png", lambda ruta: ruta.abort())
    appid = elegidos["alto"]
    _abrir(pagina, f"{base}/juego/{appid}")
    try:
        pagina.get_by_test_id("nia-reaccion-texto").wait_for(state="visible", timeout=_TIMEOUT_MS)
        pagina.wait_for_function(
            "() => !document.querySelector(\"[data-testid='nia-reaccion-imagen']\")", timeout=_TIMEOUT_MS
        )
        _esperar_quietud(pagina)
        ruta = destino / "nia-reaccion-sin-imagen.png"
        pagina.get_by_test_id("segunda-opinion").screenshot(path=ruta)
        print(f"nia v2:   sin la imagen, el texto sigue ({ruta.relative_to(_RAIZ)})")
    except TiempoAgotado:
        problemas.append("si el PNG de Nia falla, la reacción no queda en pie solo con el texto")
    pagina.unroute("**/nia/ficha-*.png")

    # Con movimiento reducido, quieta; y a 390 px, sin desborde.
    navegador = pagina.context.browser
    if navegador is not None:
        for ajustes, que in (({"reduced_motion": "reduce"}, "movimiento"), ({}, "móvil")):
            vista = {"width": 390, "height": 844} if que == "móvil" else _VIEWPORT
            contexto = navegador.new_context(viewport=vista, **ajustes)
            _sin_consultas_a_nia(contexto)
            try:
                otra = contexto.new_page()
                _abrir(otra, f"{base}/juego/{elegidos['bajo']}")
                otra.get_by_test_id("nia-reaccion-imagen").wait_for(state="visible", timeout=_TIMEOUT_MS)
                if que == "movimiento":
                    animacion = otra.evaluate(
                        "() => getComputedStyle(document.querySelector(\"[data-testid='nia-reaccion-imagen']\"))"
                        ".animationName"
                    )
                    if animacion != "none":
                        problemas.append(f"con prefers-reduced-motion Nia sigue animada ({animacion})")
                    else:
                        print("nia v2:   con prefers-reduced-motion queda quieta")
                else:
                    medidas = otra.evaluate(
                        "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"
                    )
                    if medidas[0] > medidas[1]:
                        problemas.append(f"a 390 px la ficha desborda {medidas[0] - medidas[1]} px")
                    _esperar_quietud(otra)
                    ruta = destino / "nia-reaccion-movil.png"
                    otra.get_by_test_id("segunda-opinion").screenshot(path=ruta)
                    print(f"nia v2:   a 390 px sin desborde ({ruta.relative_to(_RAIZ)})")
            finally:
                contexto.close()

    _abrir(pagina, url)
    return problemas


# Qué pares de color tienen que pasar, y cuánto piden: 4.5:1 el texto, 3:1 los bordes y
# los controles (WCAG 1.4.3 y 1.4.11). Se miden sobre los tokens ya resueltos por el
# navegador, no sobre lo que dice la documentación.
_CONTRASTES = [
    ("--texto", "--superficie-lienzo", 4.5),
    ("--texto", "--superficie-tarjeta", 4.5),
    ("--texto-meta", "--superficie-lienzo", 4.5),
    ("--texto-meta", "--superficie-tarjeta", 4.5),
    ("--texto-meta", "--superficie-tarjeta-hover", 4.5),
    ("--neon", "--superficie-lienzo", 4.5),
    ("--neon", "--superficie-tarjeta", 4.5),
    ("--neon-hover", "--superficie-tarjeta", 4.5),
    ("--borde-control", "--superficie-lienzo", 3.0),
    ("--borde-control", "--superficie-tarjeta-hover", 3.0),
    ("--foco", "--superficie-lienzo", 3.0),
    ("--banda-bajo-texto", "--superficie-lienzo", 4.5),
    ("--banda-medio-texto", "--superficie-lienzo", 4.5),
    ("--banda-alto-texto", "--superficie-lienzo", 4.5),
    ("--banda-bajo-texto", "--superficie-tarjeta-hover", 4.5),
    ("--banda-medio-texto", "--superficie-tarjeta-hover", 4.5),
    ("--banda-alto-texto", "--superficie-tarjeta-hover", 4.5),
    ("--texto-sobre-banda", "--banda-bajo", 4.5),
    ("--texto-sobre-banda", "--banda-medio", 4.5),
    ("--texto-sobre-banda", "--banda-alto", 4.5),
    ("--cta-texto", "--cta-fondo", 4.5),
    # El filo es lo que separa el relleno cromático del fondo de la página.
    ("--cta-filo", "--superficie-lienzo", 3.0),
]

_JS_TOKENS = """
nombres => {
    const estilo = getComputedStyle(document.documentElement);
    const lienzo = document.createElement('canvas').getContext('2d');
    return Object.fromEntries(nombres.map(nombre => {
        lienzo.fillStyle = '#000';
        lienzo.fillStyle = estilo.getPropertyValue(nombre).trim();
        return [nombre, lienzo.fillStyle];
    }));
}
"""


def _luminancia(hexa: str) -> float:
    crudo = hexa.lstrip("#")
    canales = [int(crudo[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lineal = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]


def _contraste(uno: str, otro: str) -> float:
    a, b = _luminancia(uno), _luminancia(otro)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _revisar_contrastes(pagina: Page, tema: str) -> list[str]:
    nombres = sorted({nombre for par in _CONTRASTES for nombre in par[:2]})
    tokens = pagina.evaluate(_JS_TOKENS, nombres)
    faltan = [nombre for nombre, valor in tokens.items() if not valor.startswith("#")]
    if faltan:
        return [f"en tema {tema} no se resolvieron los tokens {faltan}"]
    problemas = []
    peor = ("", 99.0)
    for frente, fondo, minimo in _CONTRASTES:
        razon = _contraste(tokens[frente], tokens[fondo])
        if razon < minimo:
            problemas.append(
                f"en tema {tema}, {frente} sobre {fondo} da {razon:.2f}:1 y pide {minimo}:1"
            )
        elif razon < peor[1]:
            peor = (f"{frente} sobre {fondo}", razon)
    if not problemas:
        print(f"contraste: tema {tema}, {len(_CONTRASTES)} pares pasan; el más justo es {peor[0]} con {peor[1]:.2f}:1")
    return problemas


def _desborde(pagina: Page) -> int:
    ancho, visible = pagina.evaluate(
        "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"
    )
    return max(0, ancho - visible)


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

    # 2. Los dos temas, en escritorio y a 390 px: contrastes y desborde.
    rutas = ["/", f"/juego/{_APPID_FICHA}", "/comparar", "/perfil", "/como-funciona"]
    for tema in ("oscuro", "claro"):
        for vista, nombre in ((_VIEWPORT, "escritorio"), ({"width": 390, "height": 844}, "movil")):
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
                _abrir(otra, base)
                otra.get_by_test_id("shell").wait_for(state="visible", timeout=_TIMEOUT_MS)
                # La captura espera al catálogo: si no, sale la página con el centro vacío.
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
                print(f"tema:     {tema} en {nombre}, {len(rutas)} rutas sin desborde ({ruta.relative_to(_RAIZ)})")
                if nombre == "movil":
                    # El velo cubre toda la ventana, pero el cajón le tapa los 280 px
                    # de la izquierda: el toque va del lado del contenido.
                    otra.get_by_test_id("velo-menu").click(position={"x": 350, "y": 400})
                    otra.wait_for_timeout(500)
                    if otra.get_by_test_id("velo-menu").count():
                        problemas.append(f"tema {tema}: el velo no cierra el cajón")
                    elif otra.evaluate("() => document.activeElement?.dataset.testid") != "abrir-menu":
                        problemas.append(f"tema {tema}: al cerrar el cajón el foco no vuelve a la hamburguesa")
            finally:
                contexto.close()

    _abrir(pagina, url)
    return problemas


def _capturar_angular(pagina: Page, url: str, destino: Path, api: str) -> list[str]:
    return (
        _angular_catalogo(pagina, url, destino, api)
        + _angular_ficha(pagina, url, destino)
        + _angular_descripcion(pagina, url, api)
        + _angular_video(pagina, url, destino, api)
        + _angular_como_funciona(pagina, url, destino)
        + _angular_estrellas(pagina, url, destino)
        + _angular_panel_nia(pagina, url, destino)
        + _angular_carrusel(pagina, url, destino)
        + _angular_nia_reaccion(pagina, url, destino, api)
        + _angular_hilo(pagina, url, destino)
        + _angular_perfil(pagina, url, destino, api)
        + _angular_comparar(pagina, url, destino)
        + _angular_nia_flotante(pagina, url, destino)
        + _angular_movimiento(pagina, url)
        + _angular_barra_y_tema(pagina, url, destino)
    )


# Respuesta fija para /nia. El script NUNCA habla con el modelo de lenguaje: con una
# clave con crédito en .env, cada corrida gastaría consultas de OpenAI, y lo que se
# verifica aquí es la interfaz (que el chat muestre la respuesta y su aviso de modo),
# no lo que responde el modelo. Las pruebas con OpenAI real se hacen a mano.
_NIA_FALSA = json.dumps({
    "respuesta": "Respuesta de prueba del script de capturas: no se consultó ningún modelo.",
    "modo": "demostracion",
    "modelo": None,
    "aviso": "Respuesta simulada por herramientas/capturar_ui.py; la API no recibió la pregunta.",
})


# Cuántas veces la interfaz pidió /nia y cuántas respondió la intercepción. Si las dos
# cifras coinciden, ninguna llegó a la API (ni, por tanto, al modelo de lenguaje).
_NIA_PEDIDAS: list[str] = []
_NIA_INTERCEPTADAS: list[str] = []


def _sin_consultas_a_nia(contexto) -> None:
    """Intercepta /nia en todo el contexto del navegador, antes de cualquier paso."""

    def anotar(peticion) -> None:
        if peticion.url.split("?")[0].rstrip("/").endswith("/nia"):
            _NIA_PEDIDAS.append(peticion.url)

    def responder(ruta) -> None:
        _NIA_INTERCEPTADAS.append(ruta.request.url)
        ruta.fulfill(status=200, content_type="application/json", body=_NIA_FALSA)

    contexto.on("request", anotar)
    contexto.route("**/nia", responder)


def capturar(url: str, api: str) -> int:
    destino = _DESTINO
    destino.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            contexto = navegador.new_context(viewport=_VIEWPORT)
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
