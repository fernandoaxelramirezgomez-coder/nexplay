from fastapi import APIRouter

from app.models.scoring import RiskScoreRequest, RiskScoreResponse
from app.services.scoring import calculate_risk

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/risk", response_model=RiskScoreResponse)
def score_risk(request: RiskScoreRequest) -> RiskScoreResponse:
    return calculate_risk(request)
