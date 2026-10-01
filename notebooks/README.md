# notebooks/

Los notebooks de la entrega. Corren en Colab sin el resto del repositorio: cada uno clona el tag
`codigo-v3` y baja los datos de releases con tag fijo, verificados con su sha256. Por eso no dependen de
las rutas de tu checkout.

| Notebook | Qué hace | Abrir |
|---|---|---|
| `00_exploracion.ipynb` | Valida, limpia y explora los datos antes del modelo. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/00_exploracion.ipynb) [![Ver en nbviewer](https://img.shields.io/badge/ver%20en-nbviewer-orange)](https://nbviewer.org/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/00_exploracion.ipynb) |
| `01_modelo_riesgo.ipynb` | Construye y mide el modelo de riesgo: variables, GroupKFold por `appid`, experimento de privacidad y prueba externa. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/01_modelo_riesgo.ipynb) [![Ver en nbviewer](https://img.shields.io/badge/ver%20en-nbviewer-orange)](https://nbviewer.org/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/01_modelo_riesgo.ipynb) |
| `02_modelos_texto.ipynb` | Reservado para los modelos de texto. Todavía no existe. | |

Cada uno abre con una ficha: objetivo, entradas (releases y sha256), salidas, cómo correrlo y tiempo
estimado.

## Ruta de ejecución

Primero el 00 y después el 01. El 00 revisa los datos y deja fijas las decisiones que el 01 da por
hechas. El 01 no lee nada de lo que el 00 deja en disco, así que también corre solo.

**En Colab.** Abre el notebook con su botón y usa *Entorno de ejecución → Ejecutar todas*. No pide
credenciales ni Google Drive, y no reinstala los paquetes que Colab ya trae.

**En local**, desde la raíz del repositorio y después de `make setup`:

```bash
make notebooks
```

Instala `backend/requirements-notebooks.txt` y `backend/requirements-dev.txt` y ejecuta los dos notebooks
en una carpeta temporal, con el último commit de tu checkout en lugar del tag, y compara cada salida con la
guardada. Si alguna difiere, la lista con su diff sin hacer fallar el comando; falla solo si un notebook no
termina. Las copias ejecutadas quedan ahí y los notebooks del repositorio no cambian: el 01 guarda las salidas
de la corrida en Colab, y el 00, las de una corrida local con PNG (su versión de Colab está en
`docs/evidencia/colab/`). Si kaleido encuentra un Chrome (`plotly_get_chrome`, o la variable
`BROWSER_PATH` apuntando a uno), el 00 guarda cada gráfica también como PNG. Si no lo encuentra, o en Colab,
lo avisa y deja las gráficas solo interactivas.

Los dos validan con la partición congelada de `backend/referencias/particion_gkf_data-v1.csv`. Así, los
folds no dependen de cómo desempata cada versión de scikit-learn, y el PR-AUC del modelo de producción
sale 0.0694 ± 0.0415.

No va aquí: lógica copiada dentro de un notebook. Vive en `backend/analisis/` o `backend/modelado/` y se
importa.
