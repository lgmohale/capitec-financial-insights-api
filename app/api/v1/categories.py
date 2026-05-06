from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.v1.download_links import bank_statement_pdf_download_url
from app.schemas.categories import CategoriesResponse
from app.services.categorisation_service import categorise_account_transactions

router = APIRouter(prefix="/api/v1/accounts", tags=["categories"])


@router.get(
    "/{account_id}/categories",
    response_model=CategoriesResponse,
    summary="Categorise account transactions",
    description=(
        "Reads generated transaction JSON from MinIO object storage, applies "
        "keyword-based category rules, writes "
        "`output/{account_id}/categories.json`, and caches the response with "
        "Redis key `categorisation:{account_id}`."
    ),
)
def get_account_categories(
    request: Request,
    account_id: UUID,
    force_refresh: bool = Query(
        default=False,
        description=(
            "Bypass Redis and rebuild categorisation from MinIO transaction JSON."
        ),
    ),
) -> CategoriesResponse:
    response = categorise_account_transactions(
        account_id=account_id,
        force_refresh=force_refresh,
    )
    response.bank_statement_pdf_download_url = bank_statement_pdf_download_url(
        request,
        account_id,
    )
    return response
