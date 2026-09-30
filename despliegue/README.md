# despliegue/

Cómo se levanta el proyecto.

- `preparar_entorno.py`: la entrada del proyecto. Baja data-v3 y data-v1 con su sha256,
  entrena el modelo y comprueba que la API responda. `python despliegue/preparar_entorno.py`.
- `utilidades.py`: `descargar_verificado`, que también usan los notebooks.
- `Dockerfile`: la imagen de la API que Render construye desde master (`docker build -f
  despliegue/Dockerfile .`). Copia solo lo que la API necesita y falla si llega torch.

El frontend se despliega en Vercel con `frontend/vercel.json`. No va aquí: herramientas de
revisión (`calidad/`) ni de moderación (`operacion/`).
