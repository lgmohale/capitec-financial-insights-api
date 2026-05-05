from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.financial_insights import FinancialInsightsResponse
from app.services.financial_insights_service import build_financial_insights

router = APIRouter(prefix="/api/v1/accounts", tags=["financial insights"])


@router.get(
    "/{account_id}/financial-insights",
    response_model=FinancialInsightsResponse,
    summary="Get combined financial insights",
    description=(
        "Returns user metadata, linked account metadata, aggregation, risk, "
        "recommendations, and generation timestamp. This endpoint reuses the "
        "existing services and their normal cache behavior."
    ),
)
def get_financial_insights(
    account_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> FinancialInsightsResponse:
    return build_financial_insights(account_id=account_id, db=db)
