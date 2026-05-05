from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategorySummaryItem(BaseModel):
    category: str
    total_amount: float
    transaction_count: int
    month_count: int


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
                        "month_count": 3,
                    }
                ],
                "output_file_path": (
                    "data/output/550e8400-e29b-41d4-a716-446655440000_categories.json"
                ),
            }
        }
    )

    account_id: UUID
    cached: bool
    category_summary: list[CategorySummaryItem]
    output_file_path: str
