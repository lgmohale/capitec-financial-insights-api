from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.aggregation import AggregationResponse
from app.schemas.bank_accounts import LinkedAccountMetadata, UserMetadata
from app.schemas.recommendations import RecommendationsResponse
from app.schemas.risk import RiskResponse


class FinancialInsightsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "user": {
                    "id": "650e8400-e29b-41d4-a716-446655440000",
                    "name": "Lucas George",
                    "created_at": "2026-05-05T10:00:00Z",
                    "updated_at": "2026-05-05T10:00:00Z",
                },
                "linked_account": {
                    "user_id": "650e8400-e29b-41d4-a716-446655440000",
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "bank_name": "Capitec",
                    "created_at": "2026-05-05T10:00:00Z",
                },
                "aggregation": {
                    "account_id": "550e8400-e29b-41d4-a716-446655440000",
                    "cached": True,
                    "total_income": 46579.0,
                    "total_expenses": 15790.5,
                    "net_cashflow": 30788.5,
                    "transaction_count": 5,
                    "month_count": 1,
                    "category_breakdown": {},
                    "monthly_summary": {},
                    "output_file_path": "data/output/example_aggregation.json",
                },
                "risk": {
                    "account_id": "550e8400-e29b-41d4-a716-446655440000",
                    "cached": True,
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
                        "Medium lending risk. Consider lower exposure or "
                        "additional checks."
                    ),
                    "output_file_path": "data/output/example_risk.json",
                },
                "recommendations": {
                    "account_id": "550e8400-e29b-41d4-a716-446655440000",
                    "cached": True,
                    "financial_health_score": 70,
                    "recommendations": ["Reduce gambling spend."],
                    "priority_actions": [
                        "Pause gambling transactions and redirect funds to savings."
                    ],
                    "positive_observations": ["Cashflow is positive."],
                    "output_file_path": "data/output/example_recommendations.json",
                },
                "generated_at": "2026-05-05T10:05:00Z",
            }
        }
    )

    account_id: UUID
    user: UserMetadata
    linked_account: LinkedAccountMetadata
    aggregation: AggregationResponse
    risk: RiskResponse
    recommendations: RecommendationsResponse
    generated_at: datetime
