from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.categories import CategoriesResponse
from app.services.categorisation_service import categorise_statement_transactions

router = APIRouter(prefix="/api/v1/accounts", tags=["categories"])


@router.get(
    "/{statement_id}/categories",
    response_model=CategoriesResponse,
    summary="Categorise statement transactions",
    description=(
        "Reads generated transaction JSON from MinIO object storage, applies "
        "keyword-based category rules."
    ),
)
def get_statement_categories(
    statement_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description=(
            "Bypass Redis and rebuild categorisation from MinIO transaction JSON."
        ),
    ),
) -> CategoriesResponse:
    return categorise_statement_transactions(
        statement_id=statement_id,
        force_refresh=force_refresh,
    )
