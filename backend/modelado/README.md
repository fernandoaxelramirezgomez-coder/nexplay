# modelado/

El modelo de riesgo y su validación. Solo tres archivos:

- `entrenar_baseline.py`: variables, pipeline, la partición congelada (`splits_congelados`, que lee
  `referencias/particion_gkf_data-v1.csv`) y `evaluar_gkf`, que la usa. El 01 importa de aquí.
- `entrenar_modelo.py`: entrena el modelo de producción con data-v1 y guarda `modelo/nexplay.pkl`
  (`make train`).
- `verificar_bandas.py`: compara las bandas del catálogo contra `referencias/bandas_referencia.json`. El
  build de Render falla si difieren.

Entra entera a la imagen de Render. No va aquí: análisis exploratorio ni del texto (`analisis/`), valores
de referencia (`referencias/`) ni artefactos entrenados (`modelo/`, que no se versiona).
