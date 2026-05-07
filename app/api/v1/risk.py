from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.risk import RiskResponse
from app.services.risk_service import score_statement_risk

router = APIRouter(prefix="/api/v1/accounts", tags=["risk"])


@router.get(
    "/{statement_id}/risk",
    response_model=RiskResponse,
    summary="Score lending risk",
    description=(
        "Uses aggregation and categorised transactions to calculate an explainable "
        "rule-based lending risk score and band."
    ),
)
def get_statement_risk(
    statement_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild risk scoring from source data.",
    ),
) -> RiskResponse:
    return score_statement_risk(
        statement_id=statement_id,
        force_refresh=force_refresh,
    )
