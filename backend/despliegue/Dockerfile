# La API de NexPlay en un contenedor. El contexto del build es backend/:
#   docker build -f backend/despliegue/Dockerfile backend
FROM python:3.14-slim

# Sin root: datos/ es del usuario que corre la API, para que pueda escribir valoraciones.db.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR $HOME/app

COPY --chown=user requirements.txt requirements-modelo.txt ./
# pyarrow solo lo usan publicacion/ y el notebook.
RUN grep -v '^pyarrow' requirements-modelo.txt > /tmp/modelo.txt \
 && pip install --user -r requirements.txt -r /tmp/modelo.txt
# Ningún modelo de texto llega aquí: se precalculan fuera y viajan como tabla en un release.
RUN python -c "import importlib.util as u; assert not (u.find_spec('torch') or u.find_spec('sentence_transformers')), 'torch o sentence-transformers en la imagen de la API'"

# Copia explícita: .env, datos/ y modelo/ locales nunca entran a la imagen.
COPY --chown=user api/ api/
COPY --chown=user modelado/ modelado/
# De analisis/ solo entra motivos.py: api/scoring.py lo usa para /explicacion.
COPY --chown=user analisis/motivos.py analisis/
COPY --chown=user despliegue/utilidades.py despliegue/preparar_entorno.py despliegue/
# Las bandas validadas y la partición congelada: entrenar_modelo.py saca los umbrales con ella.
COPY --chown=user referencias/bandas_referencia.json referencias/particion_gkf_data-v1.csv referencias/

# Baja data-v3 y data-v1 con su sha256, entrena y prueba la API. Si una banda difiere, el build falla.
RUN python despliegue/preparar_entorno.py \
 && python modelado/verificar_bandas.py \
 && rm -rf datos/entrenamiento

# Render define PORT; detrás de su proxy, la IP real llega en X-Forwarded-For.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
