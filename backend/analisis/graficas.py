"""La paleta y la configuración de las gráficas de los notebooks.

Viven aparte de exploracion.py para que el 01 las use sin importar limpieza.py (que trae lingua). El mismo
color significa lo mismo en los tres notebooks; exploracion.py las reexporta para el 00."""

import sys

import plotly.graph_objects as go
import plotly.io as pio

PALETA = {"VERDE_OSC": "#2e8b57", "VERDE_CLA": "#90ee90", "ROJO": "#e53935", "GRIS": "#90a4ae", "AZUL": "#1976d2"}
# El mismo color para lo mismo en todas las figuras.
COLOR_GRUPO = {"positiva": PALETA["VERDE_OSC"], "negativa tardía": PALETA["GRIS"], "negativa temprana": PALETA["ROJO"]}
COLOR_RELEASE = {"data-v1 (83)": PALETA["AZUL"], "externos (40)": PALETA["VERDE_CLA"]}


# --- Gráficas -------------------------------------------------------------------------------

def configurar_graficas(exportar_estatico: bool) -> bool:
    """La plantilla con la paleta fija. Con `exportar_estatico`, cada figura se guarda también
    como PNG, para que se vea en GitHub. Eso pide kaleido y un Chrome: en Colab, o donde kaleido
    no logra exportar, se apaga con un aviso y las gráficas quedan solo interactivas. Devuelve si
    la exportación quedó encendida."""
    pio.templates["nexplay"] = go.layout.Template(
        layout=go.Layout(
            colorway=[PALETA["AZUL"], PALETA["ROJO"], PALETA["VERDE_OSC"], PALETA["GRIS"], PALETA["VERDE_CLA"]],
            font={"family": "Arial, sans-serif", "size": 13},
            title={"font": {"size": 16}},
            margin={"l": 60, "r": 30, "t": 60, "b": 50},
        )
    )
    pio.templates.default = "plotly_white+nexplay"
    if exportar_estatico:
        motivo = _por_que_no_exportar()
        if motivo:
            print(f"Exportación estática apagada: {motivo}. Las gráficas se ven interactivas, sin PNG.")
            return False
        pio.renderers.default = "notebook_connected+png"
        pio.renderers["png"].width, pio.renderers["png"].height = 900, 480
    return exportar_estatico


def _por_que_no_exportar() -> str | None:
    """None si kaleido puede guardar un PNG; si no, el motivo en una frase."""
    if "google.colab" in sys.modules:
        return "en Colab no hace falta"
    try:
        go.Figure().to_image(format="png", width=20, height=20)
    except Exception as exc:  # kaleido lanza tipos distintos según lo que falte: el paquete o Chrome
        detalle = str(exc).strip().splitlines()
        return f"kaleido no pudo exportar una figura de prueba ({detalle[0].rstrip('.') if detalle else type(exc).__name__})"
    return None
