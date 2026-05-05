from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.aggregation import AggregationResponse
from app.services.aggregation_service import aggregate_account_transactions

router = APIRouter(prefix="/api/v1/accounts", tags=["aggregation"])


@router.get(
    "/{account_id}/aggregation",
    response_model=AggregationResponse,
    summary="Aggregate account transactions",
    description=(
        "Reuses categorisation rules to calculate income, expenses, net cashflow, "
        "transaction count, category breakdown, and monthly summaries. Writes "
        "`data/output/{account_id}_aggregation.json` and caches the response "
        "with Redis key `aggregation:{account_id}`."
    ),
)
def get_account_aggregation(
    account_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild aggregation from the input JSON file.",
    ),
) -> AggregationResponse:
    return aggregate_account_transactions(
        account_id=account_id,
        force_refresh=force_refresh,
    )
