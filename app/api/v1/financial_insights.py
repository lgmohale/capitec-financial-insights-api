from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.v1.download_links import bank_statement_pdf_download_url
from app.schemas.financial_insights import FinancialInsightsResponse
from app.services.financial_insights_service import build_financial_insights

router = APIRouter(prefix="/api/v1/accounts", tags=["financial insights"])


@router.get(
    "/{account_id}/financial-insights",
    response_model=FinancialInsightsResponse,
    summary="Get combined financial insights",
    description=(
        "Returns user metadata, bank statement metadata, aggregation, risk, "
        "recommendations, and generation timestamp. This endpoint reuses the "
        "existing services and their normal cache behavior."
    ),
)
def get_financial_insights(
    request: Request,
    account_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> FinancialInsightsResponse:
    response = build_financial_insights(account_id=account_id, db=db)
    download_url = bank_statement_pdf_download_url(request, account_id)
    response.aggregation.bank_statement_pdf_download_url = download_url
    response.risk.bank_statement_pdf_download_url = download_url
    response.recommendations.bank_statement_pdf_download_url = download_url
    return response
