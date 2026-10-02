# analisis/

Las cuentas de la exploración y del texto de las reseñas. Las importa `notebooks/00_exploracion.ipynb`,
que pone `analisis/` y `modelado/` en `sys.path`; ninguna cuenta se copia dentro del notebook.

- `exploracion.py`: chequeos de validación que devuelven tablas, la partición congelada y las cuentas de la
  exploración. También configura las gráficas del 00.
- `limpieza.py`: una función por regla de limpieza, su bitácora y la firma del conjunto limpio.
- `idioma.py`: el idioma real de cada reseña, con lingua.
- `motivos.py`: las palabras clave de los motivos. **Es el único de esta carpeta que entra a la imagen de
  Render**: `api/scoring.py` lo usa para `/explicacion`, así que cambiarlo cambia lo que ve la gente.
- `antes_del_reembolso.py`: las pruebas A y B de la mejora 01, contra criterios fijados antes de correrlas
  (resultado en `docs/evidencia/antes-del-reembolso.md`).
- `texto.py`: la Parte A de los modelos de texto (¿el texto distingue las negativas tempranas de las tardías?),
  contra la regla de `docs/evidencia/modelos-texto-prerregistro.md`. La importa `notebooks/02_modelos_texto.ipynb`;
  como script escribe `docs/evidencia/modelos-texto.json`. Ningún modelo de aquí entra al score ni a Render.

No va aquí: el entrenamiento del modelo de riesgo (`modelado/`) ni valores fijos de referencia
(`referencias/`).
