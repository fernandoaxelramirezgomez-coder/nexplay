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

    if explicacion and explicacion.get("motivos"):
        lineas = "\n".join(f"- {m['motivo']}: {m['frecuencia']:.0%}" for m in explicacion["motivos"])
        motivos_md = f"### Motivos de insatisfacción más frecuentes en *{explicacion['nombre']}*\n{lineas}"
    else:
        motivos_md = "_Sin motivos disponibles para este juego._"

    return resultado, motivos_md


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


if __name__ == "__main__":
    demo.launch()
