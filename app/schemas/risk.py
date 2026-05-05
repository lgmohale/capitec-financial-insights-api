from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RiskBand = Literal["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK", "NO_DATA"]


class RiskFactors(BaseModel):
    monthly_income_average: float
    monthly_expense_average: float
    debt_repayment_ratio: float
    gambling_transaction_count: int
    gambling_expense_total: float
    month_count: int
    salary_month_count: int
    salary_consistency: float
    negative_cashflow_months: int
    triggered_rules: list[str]


class RiskResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "cached": False,
                "risk_score": 45,
                "risk_band": "MEDIUM_RISK",
                "risk_factors": {
                    "monthly_income_average": 46579.0,
                    "monthly_expense_average": 15790.5,
                    "debt_repayment_ratio": 0.0,
                    "gambling_transaction_count": 1,
                    "gambling_expense_total": 500.0,
                    "month_count": 1,
                    "salary_month_count": 1,
                    "salary_consistency": 1.0,
                    "negative_cashflow_months": 0,
                    "triggered_rules": ["Gambling transaction detected."],
                },
                "recommendation": (
                    "Medium lending risk. Consider lower exposure or additional checks."
                ),
                "output_file_path": (
                    "data/output/550e8400-e29b-41d4-a716-446655440000_risk.json"
                ),
            }
        }
    )

    account_uuid: UUID
    cached: bool
    risk_score: int
    risk_band: RiskBand
    risk_factors: RiskFactors
    recommendation: str
    output_file_path: str
