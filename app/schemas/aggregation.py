from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryBreakdownItem(BaseModel):
    transaction_count: int
    income: float
    expenses: float
    net_amount: float
    income_percentage: Optional[float] = None  # noqa: UP007
    expense_percentage: Optional[float] = None  # noqa: UP007


class MonthlySummaryItem(BaseModel):
    total_income: float
    total_expenses: float
    net_cashflow: float
    transaction_count: int
    savings_rate: float


class AggregationRiskFlags(BaseModel):
    salary_detected: bool
    has_gambling_spend: bool
    has_negative_cashflow_month: bool
    has_unknown_income: bool


class AggregationResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "statement_id": "550e8400-e29b-41d4-a716-446655440000",
                "cached": False,
                "total_income": 46579.0,
                "total_expenses": 15790.5,
                "net_cashflow": 30788.5,
                "transaction_count": 5,
                "month_count": 1,
                "average_monthly_income": 46579.0,
                "average_monthly_expenses": 15790.5,
                "average_monthly_net_cashflow": 30788.5,
                "savings_rate": 66.1,
                "category_breakdown": {
                    "salary": {
                        "transaction_count": 1,
                        "income": 46579.0,
                        "expenses": 0.0,
                        "net_amount": 46579.0,
                        "income_percentage": 100.0,
                    },
                    "gambling": {
                        "transaction_count": 1,
                        "income": 0.0,
                        "expenses": 500.0,
                        "net_amount": -500.0,
                        "expense_percentage": 3.17,
                    },
                },
                "monthly_summary": {
                    "2026-04": {
                        "total_income": 46579.0,
                        "total_expenses": 15790.5,
                        "net_cashflow": 30788.5,
                        "transaction_count": 5,
                        "savings_rate": 66.1,
                    }
                },
                "risk_flags": {
                    "salary_detected": True,
                    "has_gambling_spend": True,
                    "has_negative_cashflow_month": False,
                    "has_unknown_income": False,
                },
                "insights": [
                    "Salary income appears consistent across the analysed period.",
                    "Rent or home loan is the largest expense category.",
                    "Net cashflow remained positive across all analysed months.",
                    "Gambling spend was detected in the analysed period.",
                ],
            }
        }
    )

    statement_id: UUID
    cached: bool
    total_income: float
    total_expenses: float
    net_cashflow: float
    transaction_count: int
    month_count: int
    average_monthly_income: float
    average_monthly_expenses: float
    average_monthly_net_cashflow: float
    savings_rate: float
    category_breakdown: dict[str, CategoryBreakdownItem]
    monthly_summary: dict[str, MonthlySummaryItem]
    risk_flags: AggregationRiskFlags
    insights: list[str]
