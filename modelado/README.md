# modelado/

El modelo de riesgo y su validación. Solo tres archivos:

- `entrenar_baseline.py`: variables, pipeline y `evaluar_gkf` (GroupKFold por appid).
- `entrenar_modelo.py`: entrena el modelo de producción con data-v1 y guarda `modelo/nexplay.pkl`.
- `verificar_bandas.py`: compara las bandas del catálogo contra `referencias/bandas_referencia.json`;
  el build de Render falla si difieren.

Entra entera a la imagen de Render. No va aquí: análisis exploratorio ni del texto
(`analisis/`), valores de referencia (`referencias/`) ni artefactos entrenados (`modelo/`, no
versionado).
