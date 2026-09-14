import random

from app.core.config import settings
from app.models.scoring import RiskFactor, RiskLevel, RiskScoreRequest, RiskScoreResponse

# TODO: reemplazar esta simulación por la llamada al modelo de riesgo real.
# El contrato de entrada/salida (RiskScoreRequest / RiskScoreResponse) es el
# definitivo: el modelo real debe poblar los mismos campos.

_SIMULATED_FACTORS = [
    ("transaction_velocity", "Frecuencia de transacciones en la última hora"),
    ("device_reputation", "Reputación del dispositivo utilizado"),
    ("geo_mismatch", "Discrepancia entre ubicación habitual y actual"),
    ("session_behavior", "Patrones anómalos de comportamiento en la sesión"),
]


def _risk_level_for(score: float) -> RiskLevel:
    if score < 25:
        return RiskLevel.LOW
    if score < 50:
        return RiskLevel.MEDIUM
    if score < 75:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def calculate_risk(request: RiskScoreRequest) -> RiskScoreResponse:
    score = round(random.uniform(0, 100), 2)

    sampled_factors = random.sample(_SIMULATED_FACTORS, k=random.randint(1, len(_SIMULATED_FACTORS)))
    factors = [
        RiskFactor(
            name=name,
            weight=round(random.uniform(0.1, 1.0), 2),
            description=description,
        )
        for name, description in sampled_factors
    ]

    return RiskScoreResponse(
        user_id=request.user_id,
        session_id=request.session_id,
        risk_score=score,
        risk_level=_risk_level_for(score),
        factors=factors,
        model_version=settings.model_version,
    )
