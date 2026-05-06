from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.v1.download_links import bank_statement_pdf_download_url
from app.schemas.recommendations import RecommendationsResponse
from app.services.recommendation_service import build_account_recommendations

router = APIRouter(prefix="/api/v1/accounts", tags=["recommendations"])


@router.get(
    "/{account_id}/recommendations",
    response_model=RecommendationsResponse,
    summary="Generate financial recommendations",
    description=(
        "Uses aggregation, risk scoring, and categorised transaction signals to "
        "produce a financial health score, recommendations, priority actions, "
        "and positive observations. Writes "
        "`output/{account_id}/recommendations.json` to MinIO and caches the "
        "response with Redis key `recommendations:{account_id}`."
    ),
)
def get_account_recommendations(
    request: Request,
    account_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild recommendations from existing services.",
    ),
) -> RecommendationsResponse:
    response = build_account_recommendations(
        account_id=account_id,
        force_refresh=force_refresh,
    )
    response.bank_statement_pdf_download_url = bank_statement_pdf_download_url(
        request,
        account_id,
    )
    return response
