from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoriesResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "cached": False,
                "category_summary": {
                    "salary": 1,
                    "groceries": 1,
                    "fuel": 1,
                    "rent_or_home_loan": 1,
                    "gambling": 1,
                    "unknown": 0,
                },
                "output_file_path": (
                    "data/output/550e8400-e29b-41d4-a716-446655440000_categories.json"
                ),
            }
        }
    )

    account_uuid: UUID
    cached: bool
    category_summary: dict[str, int]
    output_file_path: str
