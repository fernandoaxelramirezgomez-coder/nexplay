# Nexplay Scoring API

API en FastAPI que expone un endpoint de scoring de riesgo. Por ahora `scoring.py`
devuelve un riesgo **simulado** (aleatorio), pero respetando el contrato final de
request/response, de modo que el modelo real pueda conectarse sin cambiar la API.

## Estructura

```
app/
  main.py                 # instancia de FastAPI y montaje de routers
  api/routes/
    health.py              # GET /api/v1/health
    scoring.py              # POST /api/v1/scoring/risk
  models/scoring.py       # contratos Pydantic (request/response)
  services/scoring.py     # lógica de scoring (hoy simulada)
  core/config.py          # configuración de la app
```

## Requisitos

- Python 3.10+

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Levantar la API

```bash
uvicorn app.main:app --reload
```

La API queda disponible en `http://127.0.0.1:8000`.

Documentación interactiva (Swagger UI): `http://127.0.0.1:8000/docs`

## Endpoints

### `GET /api/v1/health`

Chequeo de salud del servicio.

### `POST /api/v1/scoring/risk`

Calcula el riesgo asociado a un usuario/sesión.

**Request:**

```json
{
  "user_id": "user-123",
  "session_id": "session-abc",
  "transaction_amount": 150.0,
  "metadata": { "device_id": "dev-1", "ip": "1.2.3.4" }
}
```

**Response:**

```json
{
  "user_id": "user-123",
  "session_id": "session-abc",
  "risk_score": 42.5,
  "risk_level": "medium",
  "factors": [
    { "name": "device_reputation", "weight": 0.6, "description": "Reputación del dispositivo utilizado" }
  ],
  "model_version": "sim-0.1.0",
  "evaluated_at": "2026-09-13T18:20:00Z"
}
```

`risk_score` va de 0 (sin riesgo) a 100 (riesgo máximo); `risk_level` es uno de
`low`, `medium`, `high`, `critical`.

## Próximos pasos

- Reemplazar `app/services/scoring.py::calculate_risk` por la llamada al modelo
  real, manteniendo el contrato de `RiskScoreRequest` / `RiskScoreResponse`.
