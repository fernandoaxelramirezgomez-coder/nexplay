# NexPlay

Estima el riesgo de **arrepentimiento temprano** al comprar un videojuego, antes de la
compra. `Y = 1` si `playtime_at_review < 120` minutos (ventana de reembolso de Steam) y
`voted_up == 0`. Es una señal proxy: Steam no observa arrepentimiento real.

Proyecto del Módulo V del Diplomado en Ciencia de Datos, FES Acatlán (UNAM). Contexto
completo (datos, validación, qué no hacer) en [CLAUDE.md](CLAUDE.md).

Narrativa completa (Problema → Datos → EDA → Calidad de datos → Ingeniería de variables →
Modelo → Experimento de privacidad → Conclusiones) en `notebook/nexplay.ipynb`, ejecutable de
punta a punta en un Colab limpio:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebook/nexplay.ipynb)

Esta guía es la otra mitad: **cómo dejar el proyecto completo (API + modelo + UI)
funcionando en una máquina limpia**, no solo el notebook.

## Estructura

```
api/                módulos de la API
  main.py             endpoints
  schemas.py          contratos Pydantic de entrada y salida
  scoring.py          predicción de riesgo y explicación (carga modelo/nexplay.pkl)
  catalogo.py         búsqueda de juegos (cargado una vez al arrancar)
ui/                 UI en Gradio (consume la API por HTTP)
modelo/             artefactos entrenados (.pkl) — no versionado, lo genera preparar_entorno.py
datos/              nexplay.db (SQLite) — no versionado, lo reconstruye preparar_entorno.py
notebook/           narrativa completa, ejecutable en Colab
extracto/           extractos generados (Parquet para el notebook, DB para preparar_entorno.py) — no versionado
ingesta_steam.py       ingesta original desde la API pública de Steam (no hace falta correrla)
extracto_datos.py      genera el extracto mínimo en Parquet que consume el notebook
extracto_reproducible.py  genera la copia sanitizada de datos/nexplay.db que consume preparar_entorno.py
entrenar_baseline.py   pipeline compartido + comparación de conjuntos de features
entrenar_modelo.py     entrena el modelo de producción (el que sirve api/scoring.py)
preparar_entorno.py    deja el proyecto funcional de punta a punta en una máquina limpia
```

`datos/nexplay.db` y `modelo/nexplay.pkl` no están en el repo (son datos e artefactos
entrenados, no código). `preparar_entorno.py` los reconstruye sin necesidad de volver a
correr la ingesta de Steam.

## Puesta en marcha, de cero

Requisitos: Python 3.10+ y `git`. No hace falta cuenta ni credenciales de Steam ni de
GitHub — todo lo que se descarga es público.

```bash
git clone https://github.com/fernandoaxelramirezgomez-coder/nexplay.git
cd nexplay

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt -r requirements-modelo.txt

python preparar_entorno.py
```

`preparar_entorno.py` hace, en orden:

1. Verifica que las dependencias estén instaladas.
2. Descarga el asset de datos publicado en el [release `data-v1`](https://github.com/fernandoaxelramirezgomez-coder/nexplay/releases/tag/data-v1)
   y valida su SHA-256 antes de tocarlo (mismo patrón que el notebook).
3. Reconstruye `datos/nexplay.db` a partir de ese asset.
4. Corre `entrenar_modelo.py` para generar `modelo/nexplay.pkl`.
5. Levanta la API en un puerto de prueba y confirma que `/catalogo` responde, antes de
   apagarla.

Es idempotente: si `datos/nexplay.db` o `modelo/nexplay.pkl` ya existen, no los pisa
(usa `python preparar_entorno.py --force` para reconstruirlos de cero).

Con eso, el proyecto ya está funcional. Para usarlo:

```bash
# terminal 1
uvicorn api.main:app --reload

# terminal 2
pip install -r requirements-ui.txt
python ui/app.py
```

La API queda en `http://127.0.0.1:8000` (docs interactivas en `/docs`) y la UI de Gradio
en `http://127.0.0.1:7860`.

## Configuración

- `NEXPLAY_CORS_ORIGENES`: orígenes adicionales permitidos por CORS, separados por
  coma (p. ej. `https://nexplay.example.com,https://otra.example.com`).
  `http://localhost:7860` (Gradio) y `http://localhost:4200` (Angular) están siempre
  permitidos para desarrollo local.
- `NEXPLAY_API_URL`: URL de la API que consume `ui/app.py`. Por defecto
  `http://localhost:8000`.

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
riesgo con los tres factores que más lo movieron.

**Request** (`SolicitudPrediccion`): `{ "perfil": {...}, "appid": 1245620 }`

**Response** (`PrediccionRiesgo`):

```json
{
  "appid": 1245620,
  "riesgo": 0.42,
  "nivel": "medio",
  "modelo_version": "logreg-compra-2026-09-16",
  "nota_plataforma": null,
  "factores": [
    {
      "etiqueta": "cobertura de crítica especializada",
      "valor_relativo": "bajo",
      "contribucion": 1.33,
      "direccion": "aumenta"
    },
    {
      "etiqueta": "precio del juego",
      "valor_relativo": "alto",
      "contribucion": 0.2,
      "direccion": "aumenta"
    },
    {
      "etiqueta": "compras declaradas por año",
      "valor_relativo": "bajo",
      "contribucion": -0.07,
      "direccion": "reduce"
    }
  ]
}
```

`nivel` (`bajo`/`medio`/`alto`) viene de terciles de la distribución de scores de
validación, no de un umbral de probabilidad fijo: `class_weight="balanced"` hace que
`riesgo` ordene riesgo relativo, no sea una probabilidad calibrada.

`factores`: las tres variables del modelo con mayor contribución absoluta al score
(coeficiente × valor estandarizado), en lenguaje claro. `contribucion` está en unidades
de log-odds — no se traduce a probabilidad ni tiene una escala intuitiva; sirve para
comparar factores entre sí, no como número a mostrar suelto.

`nota_plataforma` viene poblada cuando el perfil declara una plataforma distinta de
`pc`, aclarando que no existe fuente de entrenamiento propia para PlayStation/Xbox/
Nintendo (el lado del juego transfiere, pero la señal viene de reseñas de Steam).

### `GET /explicacion/{appid}`

Motivos de insatisfacción más frecuentes en las reseñas de arrepentimiento temprano
(`Y=1`) de ese juego, por conteo de palabras clave por categoría (rendimiento, bugs,
dificultad, controles, contenido, precio) — sin modelo de lenguaje.

**Response** (`ExplicacionJuego`):

```json
{
  "appid": 1938010,
  "nombre": "WILD HEARTS™",
  "n_casos": 325,
  "pct_clasificados": 0.6554,
  "motivos": [
    { "motivo": "rendimiento", "frecuencia": 0.86 },
    { "motivo": "bugs", "frecuencia": 0.25 },
    { "motivo": "dificultad", "frecuencia": 0.09 }
  ]
}
```

`n_casos` es cuántas reseñas `Y=1` se analizaron; `pct_clasificados`, qué proporción de
esas menciona al menos una de las seis categorías. `frecuencia` se calcula sobre las
reseñas clasificadas, no sobre `n_casos` — con cobertura parcial, dividir sobre el total
se ve engañosamente bajo. Con menos de 5 casos `Y=1`, `motivos` viene vacío: no hay
muestra para decir algo confiable.

## Regenerar los datos publicados (mantenedores)

Solo hace falta si se vuelve a ingestar Steam o cambia el esquema. No es parte de la
puesta en marcha normal — `preparar_entorno.py` ya descarga estos assets, no los genera.

```bash
python ingesta_steam.py --catalogo
python ingesta_steam.py --resenas      # tarda horas; reanuda si se interrumpe

python extracto_datos.py               # extracto/nexplay_extracto.parquet (para el notebook)
python extracto_reproducible.py        # extracto/nexplay_reproducible.db.xz (para preparar_entorno.py)
```

`extracto_reproducible.py` copia `juegos` y `resenas` completas salvo la columna
`steamid` (identifica cuentas reales de Steam; nada en el proyecto la usa). Las tablas
`resumen_resenas` y `progreso` no se copian: son metadata de la ingesta, no las usa ni la
API ni el entrenamiento.

Subir el asset al release existente (mismo tag `data-v1` que usa el notebook):

```bash
gh release upload data-v1 extracto/nexplay_extracto.parquet extracto/nexplay_reproducible.db.xz --clobber
```

Y actualizar `PARQUET_SHA256` en `notebook/nexplay.ipynb` y `ASSET_SHA256` en
`preparar_entorno.py` con el sha256 que imprime cada script — si no coinciden, la
descarga se rechaza a propósito en vez de seguir con datos que pudieron cambiar.

## No versionado

`datos/`, `modelo/` y `extracto/` están en `.gitignore`. `datos/` y `modelo/` los
reconstruye `preparar_entorno.py`; `extracto/` solo hace falta para publicar un release
nuevo (sección anterior).
