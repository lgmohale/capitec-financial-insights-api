from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.categories import CategoriesResponse
from app.services.categorisation_service import categorise_account_transactions

router = APIRouter(prefix="/api/v1/accounts", tags=["categories"])


@router.get(
    "/{account_id}/categories",
    response_model=CategoriesResponse,
    summary="Categorise account transactions",
    description=(
        "Reads raw transactions from `data/input/{account_id}.json`, applies "
        "keyword-based category rules, writes "
        "`data/output/{account_id}_categories.json`, and caches the response "
        "with Redis key `categorisation:{account_id}`."
    ),
)
def get_account_categories(
    account_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description="Bypass Redis and rebuild categorisation from the input JSON file.",
    ),
) -> CategoriesResponse:
    return categorise_account_transactions(
        account_id=account_id,
        force_refresh=force_refresh,
    )
