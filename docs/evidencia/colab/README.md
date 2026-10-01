# La corrida final en Colab, 2026-09-30

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
