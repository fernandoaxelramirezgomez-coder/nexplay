# analisis/

Las cuentas de la exploración y del texto de las reseñas. Las usan `notebook/00_exploracion.ipynb`
y los modelos de texto; se importan con `analisis/` y `modelado/` en `sys.path`, como hace el
notebook.

- `exploracion.py`: chequeos de validación que devuelven tablas, la partición congelada y las
  cuentas de la exploración.
- `limpieza.py`: una función por regla, su bitácora y la firma del conjunto limpio.
- `idioma.py`: el idioma real de cada reseña (lingua).
- `motivos.py`: las palabras clave de los motivos. **Es el único que entra a la imagen de
  Render**: `api/scoring.py` lo usa para `/explicacion`, así que cambiarlo cambia lo que ve la
  gente.

No va aquí: el entrenamiento del modelo de riesgo (`modelado/`) ni valores fijos de referencia
(`referencias/`).
