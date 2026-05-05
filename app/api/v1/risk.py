from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.risk import RiskResponse
from app.services.risk_service import score_account_risk

router = APIRouter(prefix="/api/v1/accounts", tags=["risk"])


@router.get(
    "/{account_id}/risk",
    response_model=RiskResponse,
    summary="Score lending risk",
    description=(
        "Uses aggregation and categorised transactions to calculate an explainable "
        "rule-based lending risk score and band. Writes "
        "`data/output/{account_id}_risk.json` and caches the response with "
        "Redis key `risk:{account_id}`."
    ),
)
def get_account_risk(
    account_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild risk scoring from source data.",
    ),
) -> RiskResponse:
    return score_account_risk(
        account_id=account_id,
        force_refresh=force_refresh,
    )
