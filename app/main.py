from fastapi import FastAPI

from app.api.routes import health, scoring
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(scoring.router, prefix=settings.api_prefix)
