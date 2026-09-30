# notebook/

Los notebooks de entrega, ejecutables en Colab. Cada uno clona un tag fijo de código y baja
los datos de releases con sha256, así que no depende de las rutas de este repo.

- `00_exploracion.ipynb`: validación, limpieza y exploración, antes del modelo
  (tag `codigo-eda-v2`).
- `nexplay.ipynb`: la narrativa del modelo de riesgo (tag `data-v2`).

No va aquí: lógica que se copie en el notebook; vive en `analisis/` o `modelado/` y se importa.
