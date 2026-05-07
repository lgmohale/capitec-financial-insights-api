from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.aggregation import AggregationResponse
from app.services.aggregation_service import aggregate_statement_transactions

router = APIRouter(prefix="/api/v1/accounts", tags=["aggregation"])


@router.get(
    "/{statement_id}/aggregation",
    response_model=AggregationResponse,
    summary="Aggregate statement transactions",
    description=(
        "Reuses categorisation rules to calculate income, expenses, net cashflow, "
        "transaction count, average monthly values, savings rates, category "
        "breakdown, simple risk flags, deterministic insights, and monthly "
        "summaries."
    ),
)
def get_statement_aggregation(
    statement_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild aggregation from MinIO transaction JSON.",
    ),
) -> AggregationResponse:
    return aggregate_statement_transactions(
        statement_id=statement_id,
        force_refresh=force_refresh,
    )
