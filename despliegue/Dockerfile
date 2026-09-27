# La API de NexPlay en un contenedor. El contexto del build es la raíz del repo:
#   docker build -f despliegue/Dockerfile .
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

# Copia explícita: .env, datos/ y modelo/ locales nunca entran a la imagen.
COPY --chown=user api/ api/
COPY --chown=user modelado/ modelado/
COPY --chown=user herramientas/preparar_entorno.py herramientas/
COPY --chown=user docs/bandas_referencia.json docs/

# Baja data-v2 y data-v1 con su sha256, entrena y prueba la API. Si una banda difiere, el build falla.
RUN python herramientas/preparar_entorno.py \
 && python modelado/verificar_bandas.py \
 && rm -rf datos/entrenamiento

# Render define PORT; detrás de su proxy, la IP real llega en X-Forwarded-For.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
