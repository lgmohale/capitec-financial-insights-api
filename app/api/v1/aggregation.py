from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.v1.download_links import bank_statement_pdf_download_url
from app.schemas.aggregation import AggregationResponse
from app.services.aggregation_service import aggregate_account_transactions

router = APIRouter(prefix="/api/v1/accounts", tags=["aggregation"])


@router.get(
    "/{account_id}/aggregation",
    response_model=AggregationResponse,
    summary="Aggregate account transactions",
    description=(
        "Reuses categorisation rules to calculate income, expenses, net cashflow, "
        "transaction count, average monthly values, savings rates, category "
        "breakdown, simple risk flags, deterministic insights, and monthly "
        "summaries. Writes `output/{account_id}/aggregation.json` to MinIO and "
        "caches the response with Redis key `aggregation:{account_id}`."
    ),
)
def get_account_aggregation(
    request: Request,
    account_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild aggregation from MinIO transaction JSON.",
    ),
) -> AggregationResponse:
    response = aggregate_account_transactions(
        account_id=account_id,
        force_refresh=force_refresh,
    )
    response.bank_statement_pdf_download_url = bank_statement_pdf_download_url(
        request,
        account_id,
    )
    return response
