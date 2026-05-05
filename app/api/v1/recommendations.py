from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.recommendations import RecommendationsResponse
from app.services.recommendation_service import build_account_recommendations

router = APIRouter(prefix="/api/v1/accounts", tags=["recommendations"])


@router.get(
    "/{account_uuid}/recommendations",
    response_model=RecommendationsResponse,
    summary="Generate financial recommendations",
    description=(
        "Uses aggregation, risk scoring, and categorised transaction signals to "
        "produce a financial health score, recommendations, priority actions, "
        "and positive observations. Writes "
        "`data/output/{account_uuid}_recommendations.json` and caches the response "
        "with Redis key `recommendations:{account_uuid}`."
    ),
)
def get_account_recommendations(
    account_uuid: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild recommendations from existing services.",
    ),
) -> RecommendationsResponse:
    return build_account_recommendations(
        account_uuid=account_uuid,
        force_refresh=force_refresh,
    )
