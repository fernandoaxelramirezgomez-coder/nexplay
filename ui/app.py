"""UI en Gradio. Consume la API de NexPlay por HTTP (NEXPLAY_API_URL, por
defecto http://localhost:8000) — nunca importa api/scoring.py ni ningún otro
módulo de api/, para respetar el contrato HTTP como única frontera."""

import logging
import os

import gradio as gr
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = os.environ.get("NEXPLAY_API_URL", "http://localhost:8000")
TIMEOUT = 10

_PLATAFORMAS = ["pc", "playstation", "xbox", "nintendo"]

_COLOR_BANDA = {"bajo": "#2e7d32", "medio": "#f9a825", "alto": "#c62828"}
_MAX_COMPARAR = 4
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


def _parse_tags(texto: str) -> list[str]:
    if not texto:
        return []
    return [t.strip() for t in texto.split(",") if t.strip()]


def _crear_perfil(compras_al_anio, horas_por_semana, tolerancia_friccion, tags_preferidos, tags_rechazados, plataforma):
    formulario = {
        "compras_al_anio": int(compras_al_anio),
        "horas_por_semana": float(horas_por_semana),
        "tolerancia_friccion": int(tolerancia_friccion),
        "tags_preferidos": _parse_tags(tags_preferidos),
        "tags_rechazados": _parse_tags(tags_rechazados),
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


def _buscar_juegos(query):
    try:
        resp = requests.get(f"{API_URL}/catalogo", params={"q": query or ""}, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("fallo al buscar catálogo: %s", exc)
        return gr.Dropdown(choices=[], value=None), f"⚠️ No se pudo buscar: {exc}"

    juegos = resp.json()
    choices = [(f"{j['nombre']} ({j['appid']})", j["appid"]) for j in juegos]
    estado = f"{len(choices)} juego(s) encontrados." if choices else "Sin resultados."
    return gr.Dropdown(choices=choices, value=choices[0][1] if choices else None), estado


def _evaluar_riesgo(perfil, appid):
    if perfil is None:
        return "⚠️ Primero crea el perfil (paso 1).", ""
    if appid is None:
        return "⚠️ Primero elige un juego (paso 2).", ""

    try:
        resp = requests.post(
            f"{API_URL}/prediccion", json={"perfil": perfil, "appid": int(appid)}, timeout=TIMEOUT
        )
        resp.raise_for_status()
        prediccion = resp.json()
    except requests.RequestException as exc:
        logger.warning("fallo al predecir: %s", exc)
        return f"⚠️ No se pudo obtener la predicción: {exc}", ""

    try:
        resp_exp = requests.get(f"{API_URL}/explicacion/{int(appid)}", timeout=TIMEOUT)
        resp_exp.raise_for_status()
        explicacion = resp_exp.json()
    except requests.RequestException as exc:
        logger.warning("fallo al obtener explicación: %s", exc)
        explicacion = None

    nota = f"\n\n*{prediccion['nota_plataforma']}*" if prediccion.get("nota_plataforma") else ""
    resultado = (
        f"## Riesgo de arrepentimiento temprano: **{prediccion['nivel'].upper()}**\n"
        f"comparado con el resto del catálogo — señal proxy, no observada directamente.  \n"
        f"Modelo: `{prediccion['modelo_version']}`{nota}"
    )

    factores = prediccion.get("factores")
    if factores:
        lineas_factores = "\n".join(
            f"- {f['etiqueta']}, {'por encima' if f['valor_relativo'] == 'alto' else 'por debajo'} "
            f"del promedio del catálogo — {f['direccion']} el riesgo estimado."
            for f in factores
        )
        resultado += f"\n\n**Principales factores:**\n{lineas_factores}"

    if explicacion and explicacion.get("motivos"):
        lineas = "\n".join(f"- {m['motivo']}: {m['frecuencia']:.0%}" for m in explicacion["motivos"])
        contexto = (
            f"_{explicacion['n_casos']} reseñas de arrepentimiento temprano analizadas, "
            f"{explicacion['pct_clasificados']:.0%} mencionan alguno de estos motivos "
            f"— porcentajes sobre las clasificadas, no sobre el total._"
        )
        motivos_md = (
            f"### Motivos de insatisfacción más frecuentes en *{explicacion['nombre']}*\n"
            f"{lineas}\n\n{contexto}"
        )
    else:
        motivos_md = "_Sin motivos disponibles para este juego._"

    return resultado, motivos_md


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
        "<div style='border:1px solid #444; border-radius:10px; padding:10px;'>"
        f"<a href='{juego['tienda_url']}' target='_blank' rel='noopener'>"
        f"<img src='{juego['portada_url']}' loading='lazy' "
        f"onerror=\"this.onerror=null;this.src='{_PORTADA_FALLBACK}';\" "
        "style='width:100%; border-radius:6px; display:block;'></a>"
        f"<div style='font-weight:600; margin-top:8px;'>{juego['nombre']}</div>"
        f"<div style='font-size:0.9em; opacity:0.85;'>{metacritic_txt}</div>"
        "<div style='margin-top:4px;'>"
        f"<span style='background:{color}; color:white; padding:2px 8px; border-radius:12px; font-size:0.85em;'>"
        f"Riesgo {banda.upper()}</span></div></div>"
    )


def _filtrar_catalogo_visual(genero, banda, texto):
    texto_norm = (texto or "").strip().lower()
    genero_sel = genero if genero and genero != "Todos" else None
    banda_sel = banda if banda and banda != "Todas" else None

    visibilidades = []
    for juego in _CATALOGO_VISUAL:
        visible = True
        if texto_norm and texto_norm not in juego["nombre"].lower():
            visible = False
        if genero_sel and genero_sel not in juego["generos"]:
            visible = False
        if banda_sel and juego["banda_riesgo"] != banda_sel:
            visible = False
        visibilidades.append(gr.update(visible=visible))
    return visibilidades


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


with gr.Blocks(title="NexPlay") as demo:
    gr.Markdown(
        "# NexPlay\n"
        "Estima el riesgo de **arrepentimiento temprano** al comprar un videojuego, "
        "antes de la compra. Es una señal proxy: Steam no observa arrepentimiento real."
    )

    perfil_state = gr.State(None)
    appid_state = gr.State(None)

    with gr.Group():
        gr.Markdown("## 1. Perfil del jugador")
        with gr.Row():
            compras_al_anio = gr.Number(label="Compras al año", value=3, precision=0, minimum=0, maximum=365)
            horas_por_semana = gr.Number(label="Horas por semana disponibles", value=6, minimum=0, maximum=168)
            tolerancia_friccion = gr.Slider(
                label="Tolerancia a la fricción (1 nula, 5 muy alta)", minimum=1, maximum=5, step=1, value=3
            )
        with gr.Row():
            tags_preferidos = gr.Textbox(
                label="Tags preferidos (separados por coma, vocabulario de Steam)",
                placeholder="roguelike, singleplayer",
            )
            tags_rechazados = gr.Textbox(
                label="Tags rechazados (separados por coma)", placeholder="pvp, pay to win"
            )
        plataforma = gr.Radio(label="Plataforma", choices=_PLATAFORMAS, value="pc")
        boton_perfil = gr.Button("Crear perfil")
        resumen_perfil = gr.Markdown()

    boton_perfil.click(
        _crear_perfil,
        inputs=[compras_al_anio, horas_por_semana, tolerancia_friccion, tags_preferidos, tags_rechazados, plataforma],
        outputs=[perfil_state, resumen_perfil],
    )

    with gr.Group():
        gr.Markdown("## 2. Buscar juego")
        with gr.Row():
            busqueda = gr.Textbox(label="Nombre del juego", placeholder="half-life")
            boton_buscar = gr.Button("Buscar")
        resultados = gr.Dropdown(label="Resultados")
        estado_busqueda = gr.Markdown()

    boton_buscar.click(_buscar_juegos, inputs=[busqueda], outputs=[resultados, estado_busqueda])
    resultados.change(lambda appid: appid, inputs=[resultados], outputs=[appid_state])

    with gr.Group():
        gr.Markdown("## 3. Riesgo estimado")
        boton_evaluar = gr.Button("Evaluar riesgo")
        resultado_riesgo = gr.Markdown()
        motivos_md = gr.Markdown()

    boton_evaluar.click(_evaluar_riesgo, inputs=[perfil_state, appid_state], outputs=[resultado_riesgo, motivos_md])

    with gr.Group():
        gr.Markdown(
            "## 4. Catálogo visual\n"
            "_\"Ver segunda opinión\" evalúa ese juego con el perfil del paso 1 y actualiza el "
            "resultado en la sección 3, arriba. \"Comparar\" solo junta candidatos por ahora "
            "(la comparación en sí es una fase futura)._"
        )
        if not _CATALOGO_VISUAL:
            gr.Markdown("_No se pudo cargar el catálogo visual — revisa que la API esté corriendo._")
        else:
            with gr.Row():
                filtro_genero = gr.Dropdown(
                    label="Género", choices=["Todos"] + _GENEROS_DISPONIBLES, value="Todos"
                )
                filtro_riesgo = gr.Dropdown(
                    label="Banda de riesgo", choices=["Todas", "bajo", "medio", "alto"], value="Todas"
                )
                filtro_texto = gr.Textbox(label="Buscar por nombre", placeholder="half-life")
                boton_filtrar = gr.Button("Filtrar")

            comparar_state = gr.State([])
            comparar_md = gr.Markdown("**En comparación:** _ninguno todavía_")

            columnas_catalogo = []
            for i in range(0, len(_CATALOGO_VISUAL), 4):
                with gr.Row():
                    for juego in _CATALOGO_VISUAL[i : i + 4]:
                        with gr.Column(min_width=200) as columna:
                            gr.HTML(_tarjeta_html(juego))
                            with gr.Row():
                                boton_opinion = gr.Button("Ver segunda opinión", size="sm")
                                boton_comparar = gr.Button("Comparar", size="sm")

                            boton_opinion.click(
                                lambda perfil, ap=juego["appid"]: (ap,) + _evaluar_riesgo(perfil, ap),
                                inputs=[perfil_state],
                                outputs=[appid_state, resultado_riesgo, motivos_md],
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
                inputs=[filtro_genero, filtro_riesgo, filtro_texto],
                outputs=columnas_catalogo,
            )


if __name__ == "__main__":
    demo.launch()
