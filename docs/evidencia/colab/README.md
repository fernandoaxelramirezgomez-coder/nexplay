# Corridas en Colab

Dos corridas: el 00 y el 01 el 2026-09-30 con `codigo-v3`, y el 02 el 2026-10-01 con `codigo-v4` (más abajo).
Con `codigo-v6`, que agrega las gráficas para negocio, las nubes con forma de control y la conclusión para negocio
del 02, los tres están pendientes de correr en Colab.

## 00 y 01: 2026-09-30, `codigo-v3`

Cada notebook se ejecutó entero en un Colab limpio (*Entorno de ejecución → Ejecutar todas*) y clonó el
código del tag `codigo-v3`. Las dos descargas están aquí, con la metadata corregida:

- `00_exploracion-colab.ipynb`. `notebooks/00_exploracion.ipynb` no usa estas salidas: guarda las de una
  corrida local, donde cada gráfica queda también como PNG para que se vea en GitHub. En Colab la
  exportación se apaga y las 18 gráficas quedan solo como HTML interactivo. El código de las celdas es el
  mismo en los dos.
- `01_modelo_riesgo-colab.ipynb`. El 01 no tiene gráficas, así que `notebooks/01_modelo_riesgo.ipynb` guarda
  estas mismas salidas.

| | 00_exploracion | 01_modelo_riesgo |
|---|---|---|
| Celdas de código ejecutadas | 69 de 69 | 23 de 23 |
| Errores | 0 | 0 |
| Salidas a stderr (avisos) | 0 | 0 |
| Cifra principal | `GroupKFold por appid 0.0694 0.0415` | `PR-AUC GroupKFold del modelo de produccion ('juego'): 0.0694 +/- 0.0415 (3.2 veces el trivial)` |
| Tiempo, medido con las mismas versiones de Colab, no en Colab | 229 s | 26 s |

Todo sale de las dos descargas: las cuentas de celdas, errores y stderr, y las cifras que imprimen. El
tiempo no: Colab no lo guarda en el `.ipynb`, así que es el de una corrida en esta máquina con las mismas
versiones de Colab.

Lo que dicen sus propias salidas sobre el entorno:

- **Versiones** (01, celda 5): Python 3.13.15, numpy 2.1.3, pandas 2.2.3, scikit-learn 1.6.1, pyarrow 23.0.1
  y requests 2.32.4.
- **Código** (01, celda 8): `Note: switching to '9b647957dbddbcdff5ac5bbbc550c24ebb732fa0'`, que es `codigo-v3`.
- **Gráficas** (00, celda 7): `Exportación estática apagada: en Colab no hace falta. Las gráficas se ven
  interactivas, sin PNG.` Por eso las gráficas del 00 quedan como HTML interactivo, sin PNG.

En la metadata de los dos archivos, `colab.name` dice `00_exploracion.ipynb` y `01_modelo_riesgo.ipynb`, el
nombre de cada notebook en el repo, y `language_info.version` es 3.13.15, la versión de Colab. Se quitó la
metadata `execution` de cada celda: eran fechas de una corrida local anterior que Colab conservó, no las de
esta.

## Contra una corrida local

`make-notebooks.txt` es la salida de `make notebooks` cuando las salidas de Colab estaban guardadas en los
dos notebooks de `notebooks/`, antes de que el 00 volviera a sus salidas locales. Corrió en local, con
Python 3.14, pandas 3.0.6 y scikit-learn 1.9.1, y el código de `9b64795`. En esa salida solo se cambiaron la
ruta de la carpeta temporal y la del entorno de Python, y se quitaron los avisos de transporte de ipykernel.

Sale con 0. Aparte de las celdas de entorno (el clon, las versiones y la configuración de las gráficas),
cinco celdas se escriben distinto sin que cambie ninguna cifra:

| Celda | Qué cambia |
|---|---|
| 00, 16 y 17 | pandas 2.2.3 escribe el tipo de las columnas de texto como `object` y pandas 3 como `str`. Con eso unificado, las tablas son idénticas. |
| 00, 34 | Con scikit-learn 1.6.1, el GroupKFold reparte los juegos de otra forma (coincide en 12 de 83) y el notebook lo avisa; con la 1.9.1 coincide con la partición congelada. Las dos corridas evalúan con el CSV congelado. |
| 00, 46 | Dos idiomas empatados en 59 reseñas salen en otro orden. Al ordenar, las filas son las mismas. |
| 01, 22 | Los mismos dos juegos (GTA V Legacy y New World: Aeternum), escritos como `array([...], dtype=object)` o como `<ArrowStringArray>`. |

## 02: 2026-10-01, `codigo-v4`

`02_modelos_texto-colab.ipynb` es la descarga tal cual, byte por byte, sin corregir la metadata. Su sha256 es
`6834e2966d0c23836c187970dedf1e7d14c653022009f2fcf163ae838cde6d58`. Corrió entero en un Colab con GPU T4
disponible (*Entorno de ejecución → Ejecutar todas*) y clonó `codigo-v4`.

| | 02_modelos_texto |
|---|---|
| Celdas de código ejecutadas | 16 de 16 |
| Errores | 0 |
| Salidas a stderr (avisos) | 0 |
| Cifra principal (celda 28) | `Rama 3: se guarda TF-IDF + LR` y `Coincide con docs/evidencia/modelos-texto.json (código 59694a6).` |
| Tiempo, medido con las mismas versiones de Colab, no en Colab | 506 s (en CPU, con torch 2.14.1 y sentence-transformers 6.1.0) |

Lo que dicen sus salidas y su metadata:

- **Versiones** (celda 7): Python 3.13.15, numpy 2.1.3, pandas 2.2.3, scikit-learn 1.6.1, torch 2.11.0+cu130 y
  sentence-transformers 5.7.0.
- **GPU sin uso.** La metadata trae `accelerator: GPU` y `gpuType: T4`, pero los embeddings corren en CPU:
  `texto.embeddings` fija `device="cpu"` (§4 del prerregistro). La T4 estaba disponible y no intervino.
- **Dos datos de la metadata no son de esta corrida:**
  - `language_info.version` dice 3.14.4, aunque la celda 7 imprime 3.13.15;
  - las 16 celdas de código traen la metadata `execution` con fechas del 2026-10-02 (UTC).
  Las dos cosas vienen de la corrida local guardada en `notebooks/02_modelos_texto.ipynb`: Colab las conserva
  al abrir el notebook y no las reescribe. En el 00 y el 01 se corrigieron. Aquí se dejan para que el archivo
  sea idéntico a la descarga.
- **Código:** la celda de clon es silenciosa (`subprocess` con la salida capturada). Así que lo que muestra el
  código usado es la comparación de la celda 28 contra `modelos-texto.json`. Esa comparación solo pasa con
  el `texto.py` de `59694a6`, que es el de `codigo-v4`.
