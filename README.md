# NexPlay — API

Estima el riesgo de **arrepentimiento temprano** al comprar un videojuego, antes de la
compra. `Y = 1` si `playtime_at_review < 120` minutos (ventana de reembolso de Steam) y
`voted_up == 0`. Es una señal proxy: Steam no observa arrepentimiento real.

Contexto completo del proyecto (datos, validación, qué no hacer) en [CLAUDE.md](CLAUDE.md).

Narrativa completa (Problema → Datos → EDA → Calidad de datos → Ingeniería de variables →
Modelo → Experimento de privacidad → Conclusiones) en `notebook/nexplay.ipynb`, ejecutable de
punta a punta en un Colab limpio:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/data-v1/notebook/nexplay.ipynb)

## Estructura

```
api/
  main.py       endpoints
  schemas.py    contratos Pydantic de entrada y salida
  scoring.py    predicción de riesgo (hoy simulada, firma estable)
  catalogo.py   búsqueda de juegos (catálogo real, cargado una vez al arrancar)
modelo/         artefactos entrenados (.pkl) — no versionado, no existe todavía
datos/          nexplay.db (SQLite, ingesta de Steam) — no versionado
ui/             Gradio — no implementado todavía
```

`api/catalogo.py` lee `datos/nexplay.db` (ingerido con `ingesta_steam.py` desde la API
pública de Steam) una sola vez, al importar el módulo — no vuelve a tocar la base en
cada request. Como Steam es la única fuente, el catálogo declara todos los juegos en
`pc`: no hay forma de confirmar disponibilidad en PlayStation/Xbox/Nintendo desde esta
ingesta.

`scoring.py::predecir` devuelve hoy un riesgo simulado (determinista, derivado del hash
de `appid` + perfil — no aleatorio), pero respeta el contrato final: cuando el modelo
real esté entrenado (GroupKFold por `appid`, optimizado a PR-AUC), esa función carga el
`.pkl` y predice con las mismas entradas y salida. Nada fuera de `scoring.py` debe
cambiar cuando eso pase.

## Requisitos

- Python 3.10+

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuración

- `NEXPLAY_CORS_ORIGENES`: orígenes adicionales permitidos por CORS, separados por
  coma (p. ej. `https://nexplay.example.com,https://otra.example.com`).
  `http://localhost:7860` (Gradio) y `http://localhost:4200` (Angular) están siempre
  permitidos para desarrollo local.

## Levantar la API

```bash
uvicorn api.main:app --reload
```

Queda disponible en `http://127.0.0.1:8000` y la documentación interactiva (Swagger UI)
en `http://127.0.0.1:8000/docs`.

## Endpoints

### `GET /catalogo?q=`

Busca juegos por nombre. Sin `q`, devuelve el catálogo completo.

### `POST /perfil`

Recibe el formulario de alta declarado por el jugador y devuelve el perfil derivado.

**Request** (`FormularioAlta`):

```json
{
  "compras_al_anio": 3,
  "horas_por_semana": 6,
  "tolerancia_friccion": 3,
  "tags_preferidos": ["roguelike", "singleplayer"],
  "tags_rechazados": ["pvp", "pay to win"],
  "plataforma": "pc"
}
```

`tolerancia_friccion` es una escala 1 (nula tolerancia) a 5 (muy alta).

**Response** (`PerfilJugador`): `tolerancia_friccion` normalizada a `baja`/`media`/`alta`,
más `segmento` (`novato`/`veterano`) y `disponibilidad` (`baja`/`media`/`alta`) —
todas derivadas por heurística.

### `POST /prediccion`

Recibe el perfil derivado (el que devolvió `/perfil`) más un `appid`, y devuelve el
riesgo.

**Request** (`SolicitudPrediccion`): `{ "perfil": {...}, "appid": 1245620 }`

**Response** (`PrediccionRiesgo`):

```json
{
  "appid": 1245620,
  "riesgo": 0.42,
  "nivel": "medio",
  "modelo_version": "simulado-0.1",
  "nota_plataforma": null
}
```

`nota_plataforma` viene poblada cuando el perfil declara una plataforma distinta de
`pc`, aclarando que no existe fuente de entrenamiento propia para PlayStation/Xbox/
Nintendo (el lado del juego transfiere, pero la señal viene de reseñas de Steam).

### `GET /explicacion/{appid}`

Motivos de insatisfacción más frecuentes de ese juego (agregado de reseñas negativas
tempranas; hoy simulado).

## Próximos pasos

- Reemplazar `api/scoring.py::predecir` y `motivos_frecuentes` por la carga del modelo
  entrenado en `modelo/` y el cálculo real sobre las reseñas de `datos/`, manteniendo el
  contrato de `PerfilJugador` + `appid` → `PrediccionRiesgo`.
- Construir `ui/` en Gradio, consumiendo estos cuatro endpoints.
