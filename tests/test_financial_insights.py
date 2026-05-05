from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.db.models import BankStatement, User
from app.schemas.aggregation import AggregationResponse
from app.schemas.recommendations import RecommendationsResponse
from app.schemas.risk import RiskResponse
from app.services import financial_insights_service

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
USER_ID = UUID("650e8400-e29b-41d4-a716-446655440000")


def test_build_financial_insights_reuses_existing_services(monkeypatch) -> None:
    user = User(
        id=USER_ID,
        name="Lucas George",
        created_at=datetime(2026, 5, 5, tzinfo=timezone.utc),  # noqa: UP017
        updated_at=datetime(2026, 5, 5, tzinfo=timezone.utc),  # noqa: UP017
    )
    bank_statement = BankStatement(
        user_id=USER_ID,
        id=ACCOUNT_ID,
        bank_name="FNB Statement April 2026",
        file_url=f"bank-statements/{USER_ID}/{ACCOUNT_ID}.pdf",
        created_at=datetime(2026, 5, 5, tzinfo=timezone.utc),  # noqa: UP017
    )
    db = FakeSession([bank_statement, user])

    monkeypatch.setattr(
        financial_insights_service,
        "aggregate_account_transactions",
        lambda account_id: AggregationResponse(
            account_id=account_id,
            cached=True,
            total_income=100.0,
            total_expenses=25.0,
            net_cashflow=75.0,
            transaction_count=2,
            month_count=1,
            average_monthly_income=100.0,
            average_monthly_expenses=25.0,
            average_monthly_net_cashflow=75.0,
            savings_rate=75.0,
            category_breakdown={},
            monthly_summary={},
            risk_flags={
                "salary_detected": True,
                "has_gambling_spend": False,
                "has_negative_cashflow_month": False,
                "has_unknown_income": False,
            },
            insights=[
                "Salary income appears consistent across the analysed period.",
            ],
            output_file_path="data/output/aggregation.json",
        ),
    )
    monkeypatch.setattr(
        financial_insights_service,
        "score_account_risk",
        lambda account_id: RiskResponse(
            account_id=account_id,
            cached=True,
            risk_score=20,
            risk_band="LOW_RISK",
            risk_factors={
                "monthly_income_average": 100.0,
                "monthly_expense_average": 25.0,
                "debt_repayment_ratio": 0.0,
                "gambling_transaction_count": 0,
                "gambling_expense_total": 0.0,
                "month_count": 1,
                "salary_month_count": 1,
                "salary_consistency": 1.0,
                "negative_cashflow_months": 0,
                "triggered_rules": [],
            },
            recommendation="Low risk.",
            output_file_path="data/output/risk.json",
        ),
    )
    monkeypatch.setattr(
        financial_insights_service,
        "build_account_recommendations",
        lambda account_id: RecommendationsResponse(
            account_id=account_id,
            cached=True,
            financial_health_score=90,
            recommendations=["Build emergency savings."],
            priority_actions=["Keep monitoring spending monthly."],
            positive_observations=["Cashflow is positive."],
            output_file_path="data/output/recommendations.json",
        ),
    )

    response = financial_insights_service.build_financial_insights(
        account_id=ACCOUNT_ID,
        db=db,
    )

    assert response.account_id == ACCOUNT_ID
    assert response.user.id == USER_ID
    assert response.bank_statement.id == ACCOUNT_ID
    assert response.aggregation.cached is True
    assert response.risk.risk_band == "LOW_RISK"
    assert response.recommendations.financial_health_score == 90
    assert response.generated_at.tzinfo is not None


class FakeSession:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def scalar(self, statement: object) -> object | None:
        return self.values.pop(0)
