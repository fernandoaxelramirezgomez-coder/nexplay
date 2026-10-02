# analisis/

Las cuentas de la exploración y del texto de las reseñas. Las importan los tres notebooks, que ponen
`analisis/` y `modelado/` en `sys.path`; ninguna cuenta se copia dentro de un notebook.

- `exploracion.py`: chequeos de validación que devuelven tablas, la partición congelada y las cuentas de la
  exploración. Reexporta la paleta y la configuración de `graficas.py`.
- `limpieza.py`: una función por regla de limpieza, su bitácora y la firma del conjunto limpio.
- `idioma.py`: el idioma real de cada reseña, con lingua.
- `graficas.py`: la paleta y la configuración de las gráficas (PNG para GitHub), aparte para que el 01 las use
  sin lingua. `exploracion.py` las reexporta.
- `diccionario.py`: qué es cada columna de las bases y cada variable del modelo. Lo usan el esquema del 00 y la
  tabla de variables del 01.
- `lectura_riesgo.py` y `lectura_texto.py`: las tablas y gráficas para negocio del 01 y del 02. Son descriptivas;
  las del 02 van después de la decisión y no la cambian.
- `motivos.py`: las palabras clave de los motivos. **Es el único de esta carpeta que entra a la imagen de
  Render**: `api/scoring.py` lo usa para `/explicacion`, así que cambiarlo cambia lo que ve la gente.
- `antes_del_reembolso.py`: las pruebas A y B de la mejora 01, contra criterios fijados antes de correrlas
  (resultado en `docs/evidencia/antes-del-reembolso.md`).
- `texto.py`: la Parte A de los modelos de texto (¿el texto distingue las negativas tempranas de las tardías?),
  contra la regla de `docs/evidencia/modelos-texto-prerregistro.md`. La importa `notebooks/02_modelos_texto.ipynb`;
  como script escribe `docs/evidencia/modelos-texto.json`. Ningún modelo de aquí entra al score ni a Render.

No va aquí: el entrenamiento del modelo de riesgo (`modelado/`) ni valores fijos de referencia
(`referencias/`).
