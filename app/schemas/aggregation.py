from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryBreakdownItem(BaseModel):
    transaction_count: int
    income: float
    expenses: float


class MonthlySummaryItem(BaseModel):
    total_income: float
    total_expenses: float
    net_cashflow: float
    transaction_count: int


class AggregationResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "cached": False,
                "total_income": 46579.0,
                "total_expenses": 15790.5,
                "net_cashflow": 30788.5,
                "transaction_count": 5,
                "month_count": 1,
                "category_breakdown": {
                    "salary": {
                        "transaction_count": 1,
                        "income": 46579.0,
                        "expenses": 0.0,
                    },
                    "gambling": {
                        "transaction_count": 1,
                        "income": 0.0,
                        "expenses": 500.0,
                    },
                },
                "monthly_summary": {
                    "2026-04": {
                        "total_income": 46579.0,
                        "total_expenses": 15790.5,
                        "net_cashflow": 30788.5,
                        "transaction_count": 5,
                    }
                },
                "output_file_path": (
                    "data/output/550e8400-e29b-41d4-a716-446655440000_aggregation.json"
                ),
            }
        }
    )

    account_uuid: UUID
    cached: bool
    total_income: float
    total_expenses: float
    net_cashflow: float
    transaction_count: int
    month_count: int
    category_breakdown: dict[str, CategoryBreakdownItem]
    monthly_summary: dict[str, MonthlySummaryItem]
    output_file_path: str
