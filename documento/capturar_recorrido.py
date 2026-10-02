"""Las capturas del recorrido del documento: alguien duda entre PAYDAY 3 y Dead Space.

Son provisionales: las finales se regeneran desde el tag de entrega. Cada una recorta un bloque
de la interfaz, no la página entera, para que se lea en papel. Tema claro, 1440 px de ancho y
escala 2.

Usa el frontend local (ng serve, 4200), pero desvía sus llamadas a la API (8000) hacia una API
de captura (--api), para no anotar nada en la backend/datos/valoraciones.db del dueño. La API de captura
se levanta aparte, desde la raíz:

  OPENAI_API_KEY=sin-llamadas NEXPLAY_MODELO_NIA=sin-llamadas OPENAI_BASE_URL=http://127.0.0.1:9 \\
  NEXPLAY_VALORACIONES_DB=/tmp/val-captura.db .venv/bin/uvicorn api.main:app --port 8030

Con esa clave falsa y la salida a OpenAI apuntando a un puerto cerrado, lo que va por reglas
aunque haya modelo («¿Por qué tiene ese riesgo?» con el juego abierto) se ve como en producción.
Cualquier otra pregunta falla sin salir de la máquina.

Guarda en docs/capturas/documento/. documento/generar_figuras.py las copia a
documento/figures/capturas/.

Uso:
  .venv/bin/python documento/capturar_recorrido.py [--front URL] [--api URL]
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend" / "calidad"))

from capturar_ui import _abrir, _esperar_quietud, _preguntar_en_chat  # noqa: E402

DESTINO = RAIZ / "docs" / "capturas" / "documento"
PAYDAY, DEAD_SPACE = 1272080, 1693980
API_DEL_FRONT = "http://localhost:8000"
TIMEOUT_MS = 60_000
MARGEN = 12
# Lo que flota encima de la página (la burbuja de Nia y su franja) no es parte de ningún bloque.
SIN_FLOTANTES = "[data-testid='nia-flotante'], [data-testid='franja-nia'] { display: none !important; }"


def _union(cajas: list[dict]) -> dict:
    x0, y0 = min(c["x"] for c in cajas), min(c["y"] for c in cajas)
    x1 = max(c["x"] + c["width"] for c in cajas)
    y1 = max(c["y"] + c["height"] for c in cajas)
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def _cajas(pagina: Page, selectores: tuple[str, ...], nombre: str) -> list[dict]:
    cajas = [pagina.locator(s).first.bounding_box() for s in selectores]
    if any(c is None for c in cajas):
        sys.exit(f"{nombre}: no se ve alguno de {selectores}")
    return cajas


def _recortar(pagina: Page, nombre: str, *selectores: str, medir=None) -> Path:
    """Captura la unión de los bloques con un margen. Si se sale de la ventana, desplaza la
    página para que empiece arriba; tiene que caber entera. `medir` sustituye a los selectores
    cuando la caja se calcula aparte (las tarjetas completas de un estante)."""
    pagina.locator(selectores[0]).first.scroll_into_view_if_needed()
    _esperar_quietud(pagina)
    caja = _union(medir() if medir else _cajas(pagina, selectores, nombre))
    alto = pagina.viewport_size["height"]
    if caja["y"] < MARGEN or caja["y"] + caja["height"] + MARGEN > alto:
        pagina.evaluate(f"window.scrollBy(0, {caja['y'] - 2 * MARGEN})")
        _esperar_quietud(pagina)
        caja = _union(medir() if medir else _cajas(pagina, selectores, nombre))
    if caja["height"] + 2 * MARGEN > alto:
        sys.exit(f"{nombre}: el recorte mide {caja['height']:.0f} px y la ventana {alto}")
    x0, y0 = max(0, caja["x"] - MARGEN), max(0, caja["y"] - MARGEN)
    ruta = DESTINO / nombre
    pagina.screenshot(path=ruta, clip={"x": x0, "y": y0, "width": caja["width"] + 2 * MARGEN,
                                        "height": caja["height"] + 2 * MARGEN})
    return ruta


def _tarjetas_completas(pagina: Page, estante: str) -> list[dict]:
    """La cabecera del estante y las tarjetas que se ven enteras dentro de su carril."""
    return pagina.evaluate(
        """estante => {
            const raiz = document.querySelector(estante);
            const tarjetas = [...raiz.querySelectorAll("[data-testid='tarjeta-juego']")];
            let contenedor = tarjetas[0].parentElement;
            while (contenedor && !["auto", "scroll", "hidden"].includes(getComputedStyle(contenedor).overflowX)) {
                contenedor = contenedor.parentElement;
            }
            const carril = (contenedor ?? raiz).getBoundingClientRect();
            const caja = r => ({x: r.x, y: r.y, width: r.width, height: r.height});
            const enteras = tarjetas.map(t => t.getBoundingClientRect())
                .filter(r => r.left >= carril.left - 1 && r.right <= carril.right + 1);
            // El título y sus flechas, no la cabecera entera: ocupa todo el ancho del carril.
            const cabecera = [...raiz.querySelectorAll("header .titulo, header .controles")].map(e => caja(e.getBoundingClientRect()));
            return [...cabecera, ...enteras.map(caja)];
        }""",
        estante,
    )


def _desde_la_pregunta(pagina: Page, chat: str) -> list[dict]:
    """Del inicio de la última pregunta al pie del chat. La conversación no alcanza a desplazarse
    hasta dejar la pregunta arriba, y lo de encima (el saludo) quedaría cortado a la mitad."""
    return [pagina.evaluate(
        """chat => {
            const caja = document.querySelector(chat).getBoundingClientRect();
            const preguntas = document.querySelectorAll(chat + " li.mensaje[data-rol='usuario']");
            // +2: con el margen del recorte, arranca 10 px arriba, dentro del hueco entre burbujas.
            const arriba = preguntas[preguntas.length - 1].getBoundingClientRect().top + 2;
            return {x: caja.x, y: arriba, width: caja.width, height: caja.bottom - arriba};
        }""",
        chat,
    )]


def _subir_a_la_pregunta(pagina: Page, chat: str) -> None:
    """La lista del chat baja sola hasta el final, y arriba de ella va fijo qué es la señal: sin subirla, la
    pregunta queda debajo de ese texto y el recorte la corta."""
    pagina.evaluate(
        """chat => {
            const preguntas = document.querySelectorAll(chat + " li.mensaje[data-rol='usuario']");
            const pregunta = preguntas[preguntas.length - 1];
            let caja = pregunta.parentElement;
            while (caja && !(caja.scrollHeight > caja.clientHeight && /auto|scroll/.test(getComputedStyle(caja).overflowY))) {
                caja = caja.parentElement;
            }
            if (caja) caja.scrollTop += pregunta.getBoundingClientRect().top - caja.getBoundingClientRect().top - 8;
        }""",
        chat,
    )
    _esperar_quietud(pagina)


def _texto(pagina: Page, selector: str) -> str:
    return " ".join(pagina.locator(selector).first.inner_text().split())


def _ficha(pagina: Page, front: str, appid: int, prefijo: str) -> list[str]:
    _abrir(pagina, f"{front}/juego/{appid}")
    pagina.wait_for_selector("[data-testid='factor']", timeout=TIMEOUT_MS)
    pagina.wait_for_selector("app-motivos-barras", timeout=TIMEOUT_MS)
    pagina.add_style_tag(content=SIN_FLOTANTES)
    rutas = [
        _recortar(pagina, f"{prefijo}-veredicto.png", "header.titulos", "[data-testid='ficha-resumen']"),
        _recortar(pagina, f"{prefijo}-factores.png", "[data-testid='factores']"),
        _recortar(pagina, f"{prefijo}-motivos.png", "app-motivos-barras"),
        _recortar(pagina, f"{prefijo}-ficha-tecnica.png", "app-metadatos-juego"),
    ]
    return [
        f"{r.name}: " + _texto(pagina, s)[:140]
        for r, s in zip(rutas, ("[data-testid='ficha-veredicto']", "[data-testid='factores']", "app-motivos-barras",
                                "app-metadatos-juego"))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--front", default="http://localhost:4200")
    parser.add_argument("--api", default="http://localhost:8030", help="la API de captura, no la de desarrollo")
    args = parser.parse_args()
    DESTINO.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        contexto = navegador.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=2,
                                         color_scheme="light", locale="es-MX")
        contexto.add_init_script("localStorage.setItem('nexplay.tema.v1', 'claro')")
        contexto.route(f"{API_DEL_FRONT}/**",
                       lambda ruta: ruta.continue_(url=ruta.request.url.replace(API_DEL_FRONT, args.api, 1)))
        pagina = contexto.new_page()
        pagina.set_default_timeout(TIMEOUT_MS)
        lineas = []

        # 1. Inicio: antes de entrar a una ficha, el buscador ya dice el riesgo.
        _abrir(pagina, f"{args.front}/")
        pagina.add_style_tag(content=SIN_FLOTANTES)
        pagina.locator("app-buscador [data-testid='filtro-texto']").first.fill("payday")
        pagina.wait_for_selector("[data-testid='buscador-panel'] [data-testid='sugerencias']")
        _recortar(pagina, "01-inicio-buscar.png", "app-buscador", "[data-testid='buscador-panel']")
        lineas.append("01-inicio-buscar.png: " + _texto(pagina, "[data-testid='buscador-panel']")[:140])
        pagina.locator("app-buscador [data-testid='filtro-texto']").first.fill("")

        # 2 y 3. Las dos fichas; en la de PAYDAY 3, además, la pregunta a Nia.
        lineas += _ficha(pagina, args.front, PAYDAY, "02-payday")
        _preguntar_en_chat(pagina, "¿Por qué tiene ese riesgo?")
        _subir_a_la_pregunta(pagina, "aside.lateral app-nia")
        _recortar(pagina, "03-payday-nia.png", "aside.lateral app-nia",
                  medir=lambda: _desde_la_pregunta(pagina, "aside.lateral app-nia"))
        lineas.append("03-payday-nia.png: modo " + _texto(pagina, "[data-testid='nia-modo']")
                      + " · " + _texto(pagina, "aside.lateral app-nia")[-160:])
        lineas += _ficha(pagina, args.front, DEAD_SPACE, "04-deadspace")

        # 4. Comparar las dos lado a lado.
        _abrir(pagina, f"{args.front}/comparar?appids={PAYDAY},{DEAD_SPACE}")
        pagina.wait_for_selector("[data-testid='tabla-comparar']")
        pagina.add_style_tag(content=SIN_FLOTANTES)
        _recortar(pagina, "05-comparar.png", "[data-testid='tabla-comparar']")
        lineas.append("05-comparar.png: " + _texto(pagina, "[data-testid='tabla-comparar']")[:140])

        # 5. Alternativas del mismo género con riesgo bajo.
        _abrir(pagina, f"{args.front}/explorar?genero=Acción")
        pagina.wait_for_selector("[data-testid='estante-bajo'] [data-testid='tarjeta-juego']")
        pagina.add_style_tag(content=SIN_FLOTANTES)
        _recortar(pagina, "06-explorar-accion-bajo.png", "[data-testid='estante-bajo']",
                  medir=lambda: _tarjetas_completas(pagina, "[data-testid='estante-bajo']"))
        lineas.append("06-explorar-accion-bajo.png: " + _texto(pagina, "[data-testid='estante-bajo']")[:140])

        # 6. La ventana de reembolso de Steam, en el Inicio.
        _abrir(pagina, f"{args.front}/")
        pagina.wait_for_selector("[data-testid='antes-reembolso']")
        pagina.add_style_tag(content=SIN_FLOTANTES)
        _recortar(pagina, "07-inicio-reembolso.png", "[data-testid='antes-motivos']")
        lineas.append("07-inicio-reembolso.png: " + _texto(pagina, "[data-testid='antes-reembolso']")[:140])

        navegador.close()

    for linea in lineas:
        print(linea)
    print(f"capturas en {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
