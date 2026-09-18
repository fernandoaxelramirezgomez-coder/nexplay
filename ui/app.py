"""UI en Gradio. Consume la API de NexPlay por HTTP (NEXPLAY_API_URL, por
defecto http://localhost:8000) — nunca importa api/scoring.py ni ningún otro
módulo de api/, para respetar el contrato HTTP como única frontera."""

import logging
import os
from pathlib import Path

import gradio as gr
import requests

import theme

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = os.environ.get("NEXPLAY_API_URL", "http://localhost:8000")
TIMEOUT = 10

_PLATAFORMAS = ["pc", "playstation", "xbox", "nintendo"]

_COLOR_BANDA = theme.COLOR_BANDA
_MAX_COMPARAR = 4
# logo-header.png: derivado de assets/logo.png con el fondo blanco vuelto
# transparente (recortado a su bounding box) — el original es opaco y se
# veía como un cuadro blanco sobre el fondo casi negro del tema.
_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo-header.png"
# SVG inline, sin depender de un servicio externo: si header.jpg no carga,
# el navegador la reemplaza sola (onerror), sin tocar Python ni bloquear el arranque.
# Comillas del SVG percent-encoded (%27): el onerror ya lo asigna con
# this.src='...' en JS de comillas simples -una comilla simple literal ahí
# adentro cerraría ese string a medias y rompería el atributo.
_PORTADA_FALLBACK = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns=%27http://www.w3.org/2000/svg%27 width=%27460%27 height=%27215%27>"
    "<rect width=%27100%25%27 height=%27100%25%27 fill=%27%23333%27/>"
    "<text x=%2750%25%27 y=%2750%25%27 fill=%27%23ccc%27 font-family=%27sans-serif%27 font-size=%2720%27 "
    "text-anchor=%27middle%27 dominant-baseline=%27middle%27>Sin portada</text></svg>"
)

# Perfil de respaldo cuando alguien pide "Ver segunda opinión" sin haber
# creado un perfil: se manda a /perfil (misma derivación que un perfil real,
# no una heurística duplicada aquí) para que el flujo funcione igual de bien
# con o sin perfil declarado.
_FORMULARIO_NEUTRO = {
    "compras_al_anio": 5,
    "horas_por_semana": 8,
    "tolerancia_friccion": 3,
    "plataforma": "pc",
}

_METODOLOGIA_MD = (
    "NexPlay estima el riesgo de **arrepentimiento temprano** al comprar un videojuego, antes "
    "de la compra. Es una señal *proxy*: se construye con reseñas donde el autor jugó poco "
    "(menos de 120 minutos, la ventana de reembolso de Steam) y calificó negativo — Steam no "
    "pregunta directamente si alguien se arrepintió.\n\n"
    "El modelo se valida con `GroupKFold` agrupando por juego, así que el riesgo mide "
    "generalización a juegos que el modelo no vio, no memorización. La métrica es PR-AUC: la "
    "clase está muy desbalanceada (~2.2% de las reseñas), así que accuracy no sirve.\n\n"
    "El riesgo ordena riesgo relativo, no es una probabilidad calibrada — por eso se muestra "
    "como nivel (bajo/medio/alto), nunca como porcentaje."
)


def _crear_perfil(biblioteca, horas_por_semana, tolerancia_friccion, plataforma):
    formulario = {
        "compras_al_anio": int(biblioteca),
        "horas_por_semana": float(horas_por_semana),
        "tolerancia_friccion": int(tolerancia_friccion),
        "plataforma": plataforma,
    }
    try:
        resp = requests.post(f"{API_URL}/perfil", json=formulario, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("fallo al crear perfil: %s", exc)
        return None, f"⚠️ No se pudo crear el perfil: {exc}"

    perfil = resp.json()
    resumen = (
        f"**Segmento:** {perfil['segmento']}  \n"
        f"**Disponibilidad:** {perfil['disponibilidad']}  \n"
        f"**Tolerancia a la fricción:** {perfil['tolerancia_friccion']}  \n"
        f"**Plataforma:** {perfil['plataforma']}"
    )
    return perfil, resumen


def _perfil_neutro() -> dict | None:
    try:
        resp = requests.post(f"{API_URL}/perfil", json=_FORMULARIO_NEUTRO, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("no se pudo derivar el perfil neutro de respaldo: %s", exc)
        return None


_FRASES_BANDA = {
    "bajo": "Comparado con el resto del catálogo, este juego tiende a generar **menos** arrepentimiento temprano.",
    "medio": "Comparado con el resto del catálogo, este juego no se distingue particularmente en arrepentimiento temprano.",
    "alto": "Comparado con el resto del catálogo, este juego tiende a generar **más** arrepentimiento temprano.",
}


def _ficha_portada_html(juego: dict) -> str:
    return (
        "<div style='text-align:center;'>"
        "<div class='nexplay-card-wrap' style='display:inline-block; max-width:460px;'>"
        "<div class='nexplay-card-inner'>"
        f"<img src='{juego['portada_url']}' loading='lazy' "
        f"onerror=\"this.onerror=null;this.src='{_PORTADA_FALLBACK}';\">"
        "</div></div>"
        f"<div class='nexplay-ficha-nombre'>{juego['nombre']}</div>"
        "</div>"
    )


def _ficha_skeleton_html() -> str:
    return "<div class='nexplay-skeleton'></div>"


def _ficha_metadata_md(juego: dict) -> str:
    metacritic = juego.get("metacritic")
    metacritic_txt = f"**Metacritic:** {metacritic}" if metacritic is not None else "**Metacritic:** sin nota"
    generos_txt = ", ".join(juego.get("generos") or []) or "sin género registrado"

    if juego.get("es_gratis"):
        precio_txt = "**Precio:** Gratis"
    elif juego.get("precio_final") is not None:
        precio_txt = f"**Precio:** ${juego['precio_final']:.2f} {juego.get('moneda') or ''}".strip()
    else:
        precio_txt = "**Precio:** no disponible"

    fecha_txt = (
        f"**Lanzamiento:** {juego['fecha_lanzamiento']}"
        if juego.get("fecha_lanzamiento")
        else "**Lanzamiento:** sin fecha registrada"
    )

    return (
        "<div class='nexplay-ficha-meta'>\n\n"
        f"{metacritic_txt}  \n"
        f"**Géneros:** {generos_txt}  \n"
        f"{precio_txt}  \n"
        f"{fecha_txt}  \n"
        f"[Ver en Steam]({juego['tienda_url']})"
        "\n\n</div>"
    )


def _ficha_motivos_md(explicacion: dict | None) -> str:
    if explicacion and explicacion.get("motivos"):
        lineas = "\n".join(f"- {m['motivo']}: {m['frecuencia']:.0%}" for m in explicacion["motivos"])
        contexto = (
            f"_{explicacion['n_casos']} reseñas de arrepentimiento temprano analizadas, "
            f"{explicacion['pct_clasificados']:.0%} mencionan alguno de estos motivos "
            f"— porcentajes sobre las clasificadas, no sobre el total._"
        )
        return f"### Motivos de insatisfacción más frecuentes\n{lineas}\n\n{contexto}"
    return (
        "### Motivos de insatisfacción más frecuentes\n"
        "_Sin motivos disponibles: muy pocas reseñas de arrepentimiento temprano para este juego._"
    )


def _ficha_factores_md(factores: list[dict]) -> str:
    if not factores:
        return ""
    lineas = "\n".join(
        f"- {f['etiqueta']}, {'por encima' if f['valor_relativo'] == 'alto' else 'por debajo'} "
        f"del promedio del catálogo — {f['direccion']} el riesgo estimado."
        for f in factores
    )
    return f"### Principales factores del modelo\n{lineas}"


def _segunda_opinion_md(nivel: str | None, motivos: list[dict], metacritic) -> str:
    """Síntesis por reglas (riesgo + motivo dominante + Metacritic), sin modelo de
    lenguaje y sin recomendar comprar o no comprar — solo describe lo que dicen los
    datos, la decisión queda del lado de quien lee."""
    if nivel is None:
        return "### Segunda opinión\n_No se pudo calcular (falló la predicción de riesgo)._"

    frases = [_FRASES_BANDA.get(nivel, "")]

    if motivos:
        top = motivos[0]
        frases.append(
            f"Entre quienes se arrepintieron pronto, el motivo más mencionado es **{top['motivo']}** "
            f"({top['frecuencia']:.0%} de las reseñas clasificadas)."
        )
    else:
        frases.append(
            "No hay suficientes reseñas de arrepentimiento temprano de este juego para identificar un motivo dominante."
        )

    if metacritic is not None:
        if metacritic >= 75:
            frases.append(f"La crítica especializada lo calificó bien (Metacritic {metacritic}).")
        elif metacritic >= 50:
            frases.append(f"La crítica especializada lo calificó de forma mixta (Metacritic {metacritic}).")
        else:
            frases.append(f"La crítica especializada lo calificó mal (Metacritic {metacritic}).")
    else:
        frases.append("No tiene cobertura de crítica especializada (sin nota de Metacritic).")

    return "### Segunda opinión\n" + " ".join(frases)


def _mostrar_carga_ficha():
    """Primer paso del click: cambia de panel al instante (se siente como
    abrir el juego) y deja un estado de carga visible, antes de que
    _abrir_ficha() termine sus llamadas a la API."""
    return (
        _ficha_skeleton_html(),
        "Cargando…",
        "",
        "",
        "",
        "",
        gr.update(visible=False),  # panel_catalogo
        gr.update(visible=True),  # panel_ficha
    )


def _abrir_ficha(perfil, appid):
    juego = next((j for j in _CATALOGO_VISUAL if j["appid"] == appid), None)
    if juego is None:
        sin_cambio = gr.update()
        return (
            sin_cambio, sin_cambio, sin_cambio, sin_cambio, sin_cambio, sin_cambio,
            gr.update(visible=True), gr.update(visible=False),
        )

    if perfil is None:
        perfil = _perfil_neutro()

    nivel, factores = None, []
    if perfil is not None:
        try:
            resp = requests.post(
                f"{API_URL}/prediccion", json={"perfil": perfil, "appid": int(appid)}, timeout=TIMEOUT
            )
            resp.raise_for_status()
            prediccion = resp.json()
            nivel = prediccion["nivel"]
            color_banda = _COLOR_BANDA.get(nivel, "#666")
            frase_riesgo = (
                f"<span class='nexplay-pill nexplay-pill-lg' style='background:{color_banda};'>"
                f"Riesgo {nivel.upper()}</span>\n\n{_FRASES_BANDA.get(nivel, '')}"
            )
            if prediccion.get("nota_plataforma"):
                frase_riesgo += f"\n\n_{prediccion['nota_plataforma']}_"
            factores = prediccion.get("factores") or []
        except requests.RequestException as exc:
            logger.warning("fallo al predecir en la ficha: %s", exc)
            frase_riesgo = "⚠️ No se pudo obtener el riesgo."
    else:
        frase_riesgo = "⚠️ No se pudo obtener el riesgo (falló el perfil neutro de respaldo)."

    try:
        resp_exp = requests.get(f"{API_URL}/explicacion/{int(appid)}", timeout=TIMEOUT)
        resp_exp.raise_for_status()
        explicacion = resp_exp.json()
    except requests.RequestException as exc:
        logger.warning("fallo al obtener explicación en la ficha: %s", exc)
        explicacion = None
    motivos = (explicacion or {}).get("motivos") or []

    return (
        _ficha_portada_html(juego),
        frase_riesgo,
        _ficha_metadata_md(juego),
        _ficha_motivos_md(explicacion),
        _ficha_factores_md(factores),
        _segunda_opinion_md(nivel, motivos, juego.get("metacritic")),
        gr.update(visible=False),  # panel_catalogo
        gr.update(visible=True),  # panel_ficha
    )


def _cargar_catalogo_visual() -> list[dict]:
    try:
        resp = requests.get(f"{API_URL}/catalogo", timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("no se pudo cargar el catálogo visual: %s", exc)
        return []


def _tarjeta_html(juego: dict) -> str:
    metacritic = juego.get("metacritic")
    metacritic_txt = f"Metacritic: {metacritic}" if metacritic is not None else "Metacritic: sin nota"
    banda = juego["banda_riesgo"]
    color = _COLOR_BANDA.get(banda, "#666")
    return (
        "<div class='nexplay-card-wrap'><div class='nexplay-card-inner'>"
        f"<a href='{juego['tienda_url']}' target='_blank' rel='noopener'>"
        f"<img src='{juego['portada_url']}' loading='lazy' "
        f"onerror=\"this.onerror=null;this.src='{_PORTADA_FALLBACK}';\">"
        "</a>"
        "<div class='nexplay-card-body'>"
        f"<div class='nexplay-card-nombre'>{juego['nombre']}</div>"
        f"<div class='nexplay-card-meta'>{metacritic_txt}</div>"
        f"<span class='nexplay-pill' style='background:{color};'>Riesgo {banda.upper()}</span>"
        "</div></div></div>"
    )


def _filtrar_catalogo_visual(genero, texto):
    """Filtra por género/nombre sobre los tres estantes (bajo/medio/alto). No
    hay filtro de banda de riesgo: la estructura en estantes ya separa por
    eso — filtrar además sería redundante con lo que la página ya muestra."""
    texto_norm = (texto or "").strip().lower()
    genero_sel = genero if genero and genero != "Todos" else None

    visibilidades = []
    conteos = {banda: 0 for banda in _ORDEN_BANDAS}
    for juego in _CATALOGO_ORDENADO:
        visible = True
        if texto_norm and texto_norm not in juego["nombre"].lower():
            visible = False
        if genero_sel and genero_sel not in juego["generos"]:
            visible = False
        visibilidades.append(gr.update(visible=visible))
        if visible:
            conteos[juego["banda_riesgo"]] += 1

    titulos = [f"### Riesgo {banda} ({conteos[banda]})" for banda in _ORDEN_BANDAS]
    return titulos + visibilidades


def _agregar_a_comparar(actuales, appid, nombre):
    actuales = list(actuales or [])
    ya_esta = any(ap == appid for ap, _ in actuales)
    if not ya_esta:
        if len(actuales) >= _MAX_COMPARAR:
            texto = ", ".join(n for _, n in actuales)
            return actuales, f"**En comparación ({_MAX_COMPARAR} máx.):** {texto}  \n_Quita uno antes de agregar otro._"
        actuales.append((appid, nombre))

    texto = ", ".join(n for _, n in actuales) if actuales else "_ninguno todavía_"
    return actuales, f"**En comparación:** {texto}"


# Catálogo visual: cargado una sola vez al arrancar la UI (no en cada
# request), igual que api/catalogo.py. Las tarjetas se construyen aquí
# mismo, abajo, con este catálogo fijo — Gradio arma sus componentes al
# construir la app, no puede agregar tarjetas nuevas dinámicamente después.
_CATALOGO_VISUAL = _cargar_catalogo_visual()
_GENEROS_DISPONIBLES = sorted({g for j in _CATALOGO_VISUAL for g in j["generos"]})

# Estantes por banda de riesgo (bajo -> medio -> alto), por score y no
# alfabético — pero el sentido del "extremo" cambia con la banda: en "bajo"
# el extremo es el más seguro (score más bajo primero); en "medio" y "alto",
# el extremo es el score más alto.
_ORDEN_BANDAS = ["bajo", "medio", "alto"]
_DESCENDENTE_POR_BANDA = {"bajo": False, "medio": True, "alto": True}
_CATALOGO_POR_BANDA = {
    banda: sorted(
        (j for j in _CATALOGO_VISUAL if j["banda_riesgo"] == banda),
        key=lambda j: j["riesgo"],
        reverse=_DESCENDENTE_POR_BANDA[banda],
    )
    for banda in _ORDEN_BANDAS
}
_CATALOGO_ORDENADO = [j for banda in _ORDEN_BANDAS for j in _CATALOGO_POR_BANDA[banda]]


with gr.Blocks(title="NexPlay") as demo:
    with gr.Column(elem_classes=["nexplay-header"]):
        if _LOGO_PATH.exists():
            # El logo ya incluye el nombre "NexPlay" (wordmark) — sin <h1> de
            # texto al lado, sería un duplicado. buttons=[] quita los
            # controles nativos de Gradio (descargar/compartir/pantalla
            # completa) que no tienen sentido sobre un logo estático.
            gr.Image(
                value=str(_LOGO_PATH),
                show_label=False,
                container=False,
                interactive=False,
                height=100,
                width=116,
                buttons=[],
            )
        else:
            gr.Markdown("<h1 class='nexplay-titulo'>NexPlay</h1>")
        gr.Markdown(
            "<div class='nexplay-tagline'><strong>Una segunda opinión antes de comprar tu próximo juego</strong></div>"
            "<div class='nexplay-tagline'>Explora, compara y descubre qué dicen los datos y los jugadores antes de decidir.</div>"
        )

    perfil_state = gr.State(None)
    comparar_state = gr.State([])

    with gr.Tabs() as tabs:
        with gr.Tab("Explorar", id="explorar"):
            with gr.Column(visible=False, elem_classes=["nexplay-panel"]) as panel_ficha:
                boton_volver = gr.Button("← Volver al catálogo")
                ficha_portada = gr.HTML()
                ficha_riesgo = gr.Markdown()
                ficha_metadata = gr.Markdown()
                ficha_motivos = gr.Markdown()
                ficha_factores = gr.Markdown()
                ficha_opinion = gr.Markdown()

            with gr.Column(visible=True, elem_classes=["nexplay-panel"]) as panel_catalogo:
                if not _CATALOGO_VISUAL:
                    gr.Markdown("_No se pudo cargar el catálogo — revisa que la API esté corriendo._")
                else:
                    with gr.Row():
                        filtro_genero = gr.Dropdown(
                            label="Género", choices=["Todos"] + _GENEROS_DISPONIBLES, value="Todos"
                        )
                        filtro_texto = gr.Textbox(label="Buscar por nombre", placeholder="half-life")
                        boton_filtrar = gr.Button("Filtrar")

                    comparar_md = gr.Markdown("**En comparación:** _ninguno todavía_")

                    titulos_banda = {}
                    columnas_catalogo = []
                    for banda in _ORDEN_BANDAS:
                        juegos_banda = _CATALOGO_POR_BANDA[banda]
                        titulos_banda[banda] = gr.Markdown(f"### Riesgo {banda} ({len(juegos_banda)})")
                        for i in range(0, len(juegos_banda), 4):
                            with gr.Row():
                                for juego in juegos_banda[i : i + 4]:
                                    with gr.Column(min_width=200) as columna:
                                        gr.HTML(_tarjeta_html(juego))
                                        with gr.Row():
                                            boton_opinion = gr.Button("Ver segunda opinión", size="sm")
                                            boton_comparar = gr.Button("Comparar", size="sm")

                                        boton_opinion.click(
                                            _mostrar_carga_ficha,
                                            outputs=[
                                                ficha_portada,
                                                ficha_riesgo,
                                                ficha_metadata,
                                                ficha_motivos,
                                                ficha_factores,
                                                ficha_opinion,
                                                panel_catalogo,
                                                panel_ficha,
                                            ],
                                        ).then(
                                            lambda perfil, ap=juego["appid"]: _abrir_ficha(perfil, ap)[:6],
                                            inputs=[perfil_state],
                                            outputs=[
                                                ficha_portada,
                                                ficha_riesgo,
                                                ficha_metadata,
                                                ficha_motivos,
                                                ficha_factores,
                                                ficha_opinion,
                                            ],
                                        )
                                        boton_comparar.click(
                                            lambda actuales, ap=juego["appid"], nombre=juego["nombre"]: _agregar_a_comparar(
                                                actuales, ap, nombre
                                            ),
                                            inputs=[comparar_state],
                                            outputs=[comparar_state, comparar_md],
                                        )
                                    columnas_catalogo.append(columna)

                    boton_filtrar.click(
                        _filtrar_catalogo_visual,
                        inputs=[filtro_genero, filtro_texto],
                        outputs=[titulos_banda[b] for b in _ORDEN_BANDAS] + columnas_catalogo,
                    )

            boton_volver.click(
                lambda: (gr.update(visible=True), gr.update(visible=False)),
                outputs=[panel_catalogo, panel_ficha],
            )

        with gr.Tab("Tu perfil", id="tu_perfil"):
            gr.Markdown(
                "Declarás cómo jugás para afinar el riesgo estimado. **Es opcional:** sin perfil, "
                "\"Ver segunda opinión\" en Explorar usa un perfil neutro."
            )
            biblioteca = gr.Radio(
                label="Biblioteca de Steam",
                choices=[
                    ("Estoy empezando (0–10 juegos)", 5),
                    ("Pequeña (11–30 juegos)", 20),
                    ("Mediana (31–100 juegos)", 60),
                    ("Grande (más de 100 juegos)", 150),
                ],
                value=20,
            )
            horas_por_semana = gr.Radio(
                label="Horas por semana disponibles para jugar",
                choices=[("Poca (menos de 4h)", 2), ("Media (4–9h)", 6), ("Alta (10h o más)", 15)],
                value=6,
            )
            tolerancia_friccion = gr.Radio(
                label="Tolerancia a la fricción (bugs, curva de aprendizaje, dificultad)",
                choices=[("Nula", 1), ("Baja", 2), ("Media", 3), ("Alta", 4), ("Muy alta", 5)],
                value=3,
            )
            plataforma = gr.Radio(label="Plataforma", choices=_PLATAFORMAS, value="pc")
            gr.Markdown(
                "_El catálogo de NexPlay es solo de juegos de Steam. En otra plataforma, el lado del "
                "juego transfiere, pero no hay una fuente de entrenamiento propia — el resultado lo "
                "aclara._"
            )

            with gr.Row():
                boton_perfil = gr.Button("Crear perfil", variant="primary")
                boton_saltar = gr.Button("Saltar y explorar juegos")
            resumen_perfil = gr.Markdown()

            boton_perfil.click(
                _crear_perfil,
                inputs=[biblioteca, horas_por_semana, tolerancia_friccion, plataforma],
                outputs=[perfil_state, resumen_perfil],
            ).then(lambda: gr.Tabs(selected="explorar"), outputs=tabs)

            boton_saltar.click(lambda: gr.Tabs(selected="explorar"), outputs=tabs)

    with gr.Accordion("Metodología", open=False):
        gr.Markdown(_METODOLOGIA_MD)


if __name__ == "__main__":
    demo.launch(theme=theme.construir_tema(), css=theme.CSS)
