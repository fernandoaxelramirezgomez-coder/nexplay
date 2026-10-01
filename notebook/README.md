# notebook/

Los notebooks de entrega, ejecutables en Colab. Cada uno clona un tag fijo de código y baja
los datos de releases con sha256, así que no depende de las rutas de este repo.

- `00_exploracion.ipynb`: validación, limpieza y exploración, antes del modelo.
- `nexplay.ipynb`: la narrativa del modelo de riesgo.

Los dos clonan el tag `codigo-v3`, que trae la partición congelada
(`referencias/particion_gkf_data-v1.csv`): sus cifras no dependen de la versión de scikit-learn de Colab.

No va aquí: lógica que se copie en el notebook; vive en `analisis/` o `modelado/` y se importa.
