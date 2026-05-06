from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategorySummaryItem(BaseModel):
    category: str
    total_amount: float
    transaction_count: int


class CategoriesResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "cached": False,
                "category_summary": [
                    {
                        "category": "groceries",
                        "total_amount": 4500.0,
                        "transaction_count": 12,
                    }
                ],
                "bank_statement_pdf_download_url": (
                    "http://localhost:8000/api/v1/bank-statements/"
                    "550e8400-e29b-41d4-a716-446655440000/download"
                ),
            }
        }
    )

    account_id: UUID
    cached: bool
    category_summary: list[CategorySummaryItem]
    bank_statement_pdf_download_url: str = ""
