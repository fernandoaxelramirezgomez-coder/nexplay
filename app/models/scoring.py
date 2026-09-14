from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskScoreRequest(BaseModel):
    user_id: str = Field(..., description="Identificador único del usuario/jugador")
    session_id: Optional[str] = Field(None, description="Identificador de la sesión de juego")
    transaction_amount: Optional[float] = Field(
        None, ge=0, description="Monto de la transacción a evaluar, si aplica"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Datos adicionales de contexto (device_id, ip, game_id, etc.)",
    )


class RiskFactor(BaseModel):
    name: str = Field(..., description="Nombre del factor de riesgo evaluado")
    weight: float = Field(..., description="Peso/contribución del factor al score final (0-1)")
    description: str = Field(..., description="Explicación legible del factor")


class RiskScoreResponse(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    risk_score: float = Field(..., ge=0, le=100, description="Score de riesgo, 0 (sin riesgo) a 100 (riesgo máximo)")
    risk_level: RiskLevel
    factors: list[RiskFactor] = Field(default_factory=list)
    model_version: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
