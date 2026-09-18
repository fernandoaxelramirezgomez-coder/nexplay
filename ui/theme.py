"""Identidad visual de NexPlay: tema nativo de Gradio (gr.themes) + el CSS
mínimo que el sistema de temas no cubra (bordes con degradado de marca,
tarjetas, animaciones de entrada/carga). Los componentes nativos (botones,
radios, inputs) se tiñen vía el tema, no vía CSS suelto.

Paleta:
- Fondo casi negro, texto blanco roto (nunca blanco puro).
- Degradado violeta (#5B2E9D) -> azul eléctrico (#2B6FE8) para encabezados
  y elementos de marca (título, botones primarios, opción seleccionada).
- Cian (#3BA9F5) como acento de interacción: foco, hover, bordes activos.
- Bandas de riesgo con semántica de semáforo pero tonos que conversan con
  la paleta: teal (bajo), ámbar (medio), coral (alto) — visibles sobre
  fondo oscuro.
"""

import gradio as gr

VIOLETA = "#5B2E9D"
AZUL = "#2B6FE8"
CIAN = "#3BA9F5"

RADIO = "16px"  # radio de esquina único, usado en el tema y en el CSS propio

COLOR_BANDA = {
    "bajo": "#16C79A",  # verde teal
    "medio": "#F5A623",  # ámbar
    "alto": "#FF6F91",  # rosa coral
}

_CIAN_HUE = gr.themes.Color(
    c50="#EAF6FF", c100="#D2ECFF", c200="#A6DBFF", c300="#79C9FE", c400="#57B7FA",
    c500="#3BA9F5", c600="#2C8ED6", c700="#2171AE", c800="#185786", c900="#113F61",
    c950="#0A283D", name="nexplay_cian",
)

_VIOLETA_HUE = gr.themes.Color(
    c50="#F4EEFC", c100="#E6D9F8", c200="#CDB4EF", c300="#B48FE6", c400="#8E62D2",
    c500="#7141B8", c600="#5B2E9D", c700="#46237A", c800="#331A59", c900="#22123C",
    c950="#140A24", name="nexplay_violeta",
)

_NEUTRO_HUE = gr.themes.Color(
    c50="#F2F0F7", c100="#DAD7E3", c200="#B7B2C6", c300="#928CA8", c400="#6E6885",
    c500="#524D69", c600="#3C384E", c700="#2A273A", c800="#1C1A28", c900="#121018",
    c950="#0B0A12", name="nexplay_neutro",
)


def construir_tema() -> gr.themes.Base:
    return gr.themes.Base(
        primary_hue=_CIAN_HUE,
        secondary_hue=_VIOLETA_HUE,
        neutral_hue=_NEUTRO_HUE,
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
        radius_size=gr.themes.sizes.radius_lg,
    ).set(
        # Fondo y texto: mismo valor en claro/oscuro -> siempre oscuro, sin
        # depender de la preferencia del sistema de quien visita.
        body_background_fill="*neutral_950",
        body_background_fill_dark="*neutral_950",
        body_text_color="*neutral_50",
        body_text_color_dark="*neutral_50",
        body_text_color_subdued="*neutral_400",
        body_text_color_subdued_dark="*neutral_400",
        background_fill_primary="*neutral_900",
        background_fill_primary_dark="*neutral_900",
        background_fill_secondary="*neutral_950",
        background_fill_secondary_dark="*neutral_950",
        border_color_primary="*neutral_700",
        border_color_primary_dark="*neutral_700",
        border_color_accent=CIAN,
        border_color_accent_dark=CIAN,
        color_accent=CIAN,
        color_accent_soft="*primary_800",
        color_accent_soft_dark="*primary_800",
        link_text_color=CIAN,
        link_text_color_dark=CIAN,
        link_text_color_hover="*primary_300",
        link_text_color_hover_dark="*primary_300",
        link_text_color_active=CIAN,
        link_text_color_active_dark=CIAN,
        # Bloques (Group, Column con borde, etc.)
        block_background_fill="*neutral_900",
        block_background_fill_dark="*neutral_900",
        block_border_color="*neutral_700",
        block_border_color_dark="*neutral_700",
        block_label_background_fill="*neutral_800",
        block_label_background_fill_dark="*neutral_800",
        block_label_text_color="*neutral_300",
        block_label_text_color_dark="*neutral_300",
        block_title_text_color="*neutral_50",
        block_title_text_color_dark="*neutral_50",
        block_info_text_color="*neutral_400",
        block_info_text_color_dark="*neutral_400",
        block_radius=RADIO,
        panel_background_fill="*neutral_950",
        panel_background_fill_dark="*neutral_950",
        panel_border_color="*neutral_700",
        panel_border_color_dark="*neutral_700",
        # Botones: degradado violeta->azul de marca; hover pasa por cian.
        button_primary_background_fill=f"linear-gradient(90deg, {VIOLETA}, {AZUL})",
        button_primary_background_fill_dark=f"linear-gradient(90deg, {VIOLETA}, {AZUL})",
        button_primary_background_fill_hover=f"linear-gradient(90deg, {AZUL}, {CIAN})",
        button_primary_background_fill_hover_dark=f"linear-gradient(90deg, {AZUL}, {CIAN})",
        button_primary_border_color="transparent",
        button_primary_border_color_dark="transparent",
        button_primary_text_color="*neutral_50",
        button_primary_text_color_dark="*neutral_50",
        button_secondary_background_fill="*neutral_800",
        button_secondary_background_fill_dark="*neutral_800",
        button_secondary_background_fill_hover="*neutral_700",
        button_secondary_background_fill_hover_dark="*neutral_700",
        button_secondary_border_color="*neutral_600",
        button_secondary_border_color_dark="*neutral_600",
        button_secondary_border_color_hover=CIAN,
        button_secondary_border_color_hover_dark=CIAN,
        button_secondary_text_color="*neutral_50",
        button_secondary_text_color_dark="*neutral_50",
        button_large_radius=RADIO,
        button_small_radius=RADIO,
        button_medium_radius=RADIO,
        # Inputs: foco en cian.
        input_background_fill="*neutral_900",
        input_background_fill_dark="*neutral_900",
        input_background_fill_focus="*neutral_800",
        input_background_fill_focus_dark="*neutral_800",
        input_border_color="*neutral_700",
        input_border_color_dark="*neutral_700",
        input_border_color_focus=CIAN,
        input_border_color_focus_dark=CIAN,
        input_radius=RADIO,
        # Radio/Checkbox: son las "tarjetas de opción" del perfil — se
        # tiñen para que de verdad parezcan tarjetas, no cajas de sistema.
        checkbox_background_color="*neutral_800",
        checkbox_background_color_dark="*neutral_800",
        checkbox_background_color_selected=CIAN,
        checkbox_background_color_selected_dark=CIAN,
        checkbox_border_color="*neutral_600",
        checkbox_border_color_dark="*neutral_600",
        checkbox_border_color_focus=CIAN,
        checkbox_border_color_focus_dark=CIAN,
        checkbox_border_color_selected=CIAN,
        checkbox_border_color_selected_dark=CIAN,
        checkbox_border_radius=RADIO,
        checkbox_label_background_fill="*neutral_800",
        checkbox_label_background_fill_dark="*neutral_800",
        checkbox_label_background_fill_hover="*neutral_700",
        checkbox_label_background_fill_hover_dark="*neutral_700",
        checkbox_label_background_fill_selected=f"linear-gradient(90deg, {VIOLETA}, {AZUL})",
        checkbox_label_background_fill_selected_dark=f"linear-gradient(90deg, {VIOLETA}, {AZUL})",
        checkbox_label_border_color="*neutral_600",
        checkbox_label_border_color_dark="*neutral_600",
        checkbox_label_border_color_selected=CIAN,
        checkbox_label_border_color_selected_dark=CIAN,
        checkbox_label_text_color="*neutral_100",
        checkbox_label_text_color_dark="*neutral_100",
        checkbox_label_text_color_selected="*neutral_50",
        checkbox_label_text_color_selected_dark="*neutral_50",
        slider_color=CIAN,
        slider_color_dark=CIAN,
    )


# CSS que el sistema de temas no cubre: el título con degradado de marca, el
# borde-degradado y el hover de las tarjetas, las bandas de riesgo como
# "pill", y las animaciones de apertura de la ficha y de carga.
CSS = f"""
:root {{
    --nexplay-violeta: {VIOLETA};
    --nexplay-azul: {AZUL};
    --nexplay-cian: {CIAN};
    --nexplay-radio: {RADIO};
}}

.nexplay-titulo {{
    background: linear-gradient(90deg, var(--nexplay-violeta), var(--nexplay-azul));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    font-weight: 800;
    margin: 0;
}}

.nexplay-tagline {{
    color: #F2F0F7;
    font-size: 1.1em;
}}

/* Tarjetas del catálogo: borde con degradado sutil de marca (truco del
padding: el fondo del wrapper ES el borde), portada pegada al borde
superior sin margen, y hover con elevación + borde que pasa a cian. */
.nexplay-card-wrap {{
    padding: 1px;
    border-radius: var(--nexplay-radio);
    background: linear-gradient(135deg, var(--nexplay-violeta), var(--nexplay-azul));
    transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}}
.nexplay-card-wrap:hover {{
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(59, 169, 245, 0.35);
    background: linear-gradient(135deg, var(--nexplay-cian), var(--nexplay-azul));
}}
.nexplay-card-inner {{
    background: #121018;
    border-radius: calc(var(--nexplay-radio) - 1px);
    overflow: hidden;
}}
.nexplay-card-inner img {{
    display: block;
    width: 100%;
    margin: 0;
    border: 0;
}}
.nexplay-card-body {{
    padding: 10px 12px 12px;
}}
.nexplay-card-nombre {{
    font-weight: 700;
    color: #F2F0F7;
    font-size: 1em;
}}
.nexplay-card-meta {{
    font-size: 0.85em;
    color: #928CA8;
    margin-top: 2px;
}}

.nexplay-pill {{
    display: inline-block;
    padding: 2px 12px;
    border-radius: 999px;
    font-weight: 700;
    color: white;
    margin-top: 6px;
}}
.nexplay-pill-lg {{
    padding: 6px 18px;
    font-size: 1.1em;
    letter-spacing: .02em;
}}

/* Ficha: jerarquia tipografica marcada */
.nexplay-ficha-nombre {{
    font-size: 1.9em;
    font-weight: 800;
    color: #F2F0F7;
    margin: 14px 0 4px;
}}
.nexplay-ficha-meta {{
    font-size: 0.92em;
    color: #928CA8;
    line-height: 1.7;
}}

/* Paneles (catalogo / ficha): entrada suave al mostrarse, en vez de
aparecer de golpe. animation (no transition) porque display:none -> block
no es transicionable con transition puro. */
.nexplay-panel {{
    animation: nexplay-fade-in 0.35s ease;
}}
@keyframes nexplay-fade-in {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

/* Estado de carga: skeleton con brillo, para que la ficha no se sienta
congelada mientras llegan riesgo/motivos/factores. */
.nexplay-skeleton {{
    height: 260px;
    border-radius: var(--nexplay-radio);
    background: linear-gradient(90deg, #1C1A28 25%, #2A273A 37%, #1C1A28 63%);
    background-size: 400% 100%;
    animation: nexplay-shimmer 1.4s ease infinite;
}}
@keyframes nexplay-shimmer {{
    0% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0 50%; }}
}}
"""
