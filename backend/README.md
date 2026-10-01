# backend/

Todo el Python de NexPlay: la API, el modelo de riesgo y las herramientas que los rodean. Cada carpeta es
un paso del flujo y tiene su propio README con lo que va ahí y lo que no.

| Carpeta | Qué hay |
|---|---|
| `api/` | La API en FastAPI y el chat de Nia (`api/nia/`). |
| `modelado/` | El entrenamiento del modelo y la comparación de sus bandas contra la referencia. |
| `analisis/` | Las cuentas de la exploración y del texto de las reseñas. La API usa `motivos.py`. |
| `referencias/` | Lo que se compara en cada build: las bandas validadas y la partición congelada. |
| `despliegue/` | `preparar_entorno.py`, que baja los datos y entrena, y el Dockerfile que construye Render. |
| `calidad/` | Los verificadores y los scripts que reproducen la evidencia de `docs/evidencia/`. |
| `ingesta/` | La ingesta original desde la API de Steam. No hace falta correrla. |
| `publicacion/` | Lo que se sube a un release de datos. |
| `operacion/` | Exportar y moderar lo que escriben quienes usan la app. |

Los comandos de Python corren desde esta carpeta, con el entorno de la raíz activado
(`source ../.venv/bin/activate`), o con `make` desde la raíz. Las rutas de los docstrings y comentarios
(`api/scoring.py`, `datos/nexplay.db`) son relativas a `backend/`.

## Requirements

| Archivo | Para qué | Dónde se instala |
|---|---|---|
| `requirements.txt` | La API: FastAPI, uvicorn, pydantic y openai. | Render y local (`make setup`) |
| `requirements-modelo.txt` | Datos y modelo: numpy, pandas, scikit-learn y pyarrow. | Render (sin pyarrow) y local (`make setup`) |
| `requirements-notebooks.txt` | plotly, lingua, sentence-transformers, nbclient, ipykernel y requests. | Solo para ejecutar los notebooks fuera de Colab (`make notebooks`). Nunca en Render: el build falla si llega torch. |
| `requirements-dev.txt` | Playwright, para las capturas de la UI, y kaleido, para las gráficas del 00 en PNG. | Solo local |

## Lo que no se versiona

Estas carpetas aparecen al correr el proyecto y están en `.gitignore`:

- `datos/`: `nexplay.db` (data-v3, lo que sirve la API), `entrenamiento/nexplay_data-v1.db` (con lo que se
  entrena) y `valoraciones.db` (calificaciones y comentarios de la app). `make data` reconstruye las dos
  primeras. `valoraciones.db` no sale de ningún release: es contenido de quienes usan la app.
- `modelo/`: `nexplay.pkl`, que deja `make train`.
- `extracto/`: lo que se prepara para publicar un release nuevo.
- `registros/`: el log y el candado que deja la ingesta.
