# api/

La API en FastAPI: contrato estable, lógica delgada. `uvicorn api.main:app` desde la raíz.

- `main.py` (endpoints), `schemas.py` (entradas y salidas Pydantic), `scoring.py` (el modelo y
  los motivos), `catalogo.py`, `panorama.py`, `valoraciones.py`, `config.py`, `limites.py`.
- `nia/`: el chat de Nia. `agente.py` arma el contexto y habla con el modelo de lenguaje;
  `reglas.py` responde por reglas (con o sin modelo); `herramientas.py` es lo que el modelo
  puede consultar del catálogo.

No va aquí: entrenamiento (`modelado/`), análisis (`analisis/`) ni scripts de revisión
(`calidad/`).
