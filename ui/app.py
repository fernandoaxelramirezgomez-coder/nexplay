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


def _evaluar_riesgo(perfil, appid):
    if appid is None:
        return "⚠️ Elige un juego en Explorar.", ""

    if perfil is None:
        perfil = _perfil_neutro()
        if perfil is None:
            return "⚠️ No se pudo evaluar (falló el perfil neutro de respaldo; ¿está la API corriendo?).", ""

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
        "**Una segunda opinión antes de comprar tu próximo juego**\n\n"
        "Explora, compara y descubre qué dicen los datos y los jugadores antes de decidir."
    )

    perfil_state = gr.State(None)
    appid_state = gr.State(None)
    comparar_state = gr.State([])

    with gr.Tabs() as tabs:
        with gr.Tab("Explorar", id="explorar"):
            with gr.Group():
                gr.Markdown("### Resultado")
                resultado_riesgo = gr.Markdown()
                motivos_md = gr.Markdown()

            with gr.Group():
                gr.Markdown(
                    "_\"Ver segunda opinión\" evalúa ese juego con tu perfil — si no creaste uno en "
                    "\"Tu perfil\", usa uno neutro — y actualiza el resultado, arriba. \"Comparar\" "
                    "solo junta candidatos por ahora (la comparación en sí es una fase futura)._"
                )
                if not _CATALOGO_VISUAL:
                    gr.Markdown("_No se pudo cargar el catálogo — revisa que la API esté corriendo._")
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
    demo.launch()
