from uuid import UUID

from app.services import recommendation_service

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_build_account_recommendations_creates_output_and_cache(
    monkeypatch,
) -> None:
    cached_values = {}
    uploaded_objects = {}

    monkeypatch.setattr(
        recommendation_service,
        "upload_json_object",
        lambda object_key, value: uploaded_objects.setdefault(object_key, value)
        and object_key,
    )
    monkeypatch.setattr(recommendation_service, "get_cache", cached_values.get)
    monkeypatch.setattr(
        recommendation_service,
        "set_cache",
        lambda key, value: cached_values.update({key: value}),
    )
    monkeypatch.setattr(
        recommendation_service,
        "aggregate_account_transactions",
        lambda account_id, force_refresh=False: FakeModel(
            {
                "account_id": str(account_id),
                "cached": False,
                "total_income": 10000.0,
                "total_expenses": 8000.0,
                "net_cashflow": 2000.0,
                "transaction_count": 4,
                "month_count": 1,
                "average_monthly_income": 10000.0,
                "average_monthly_expenses": 8000.0,
                "average_monthly_net_cashflow": 2000.0,
                "savings_rate": 20.0,
                "category_breakdown": {
                    "gambling": {
                        "transaction_count": 1,
                        "income": 0.0,
                        "expenses": 500.0,
                        "net_amount": -500.0,
                        "expense_percentage": 6.25,
                    },
                    "entertainment": {
                        "transaction_count": 1,
                        "income": 0.0,
                        "expenses": 1500.0,
                        "net_amount": -1500.0,
                        "expense_percentage": 18.75,
                    },
                },
                "monthly_summary": {},
                "risk_flags": {
                    "salary_detected": True,
                    "has_gambling_spend": True,
                    "has_negative_cashflow_month": False,
                    "has_unknown_income": False,
                },
                "insights": [
                    "Salary income appears consistent across the analysed period.",
                    "Entertainment is the largest expense category.",
                    "Gambling spend was detected in the analysed period.",
                ],
                "bank_statement_pdf_download_url": (
                    f"http://testserver/api/v1/bank-statements/{account_id}/download"
                ),
            }
        ),
    )
    monkeypatch.setattr(
        recommendation_service,
        "score_account_risk",
        lambda account_id, force_refresh=False: FakeModel(
            {
                "account_id": str(account_id),
                "cached": False,
                "risk_score": 45,
                "risk_band": "MEDIUM_RISK",
                "risk_factors": {
                    "monthly_income_average": 10000.0,
                    "monthly_expense_average": 8000.0,
                    "debt_repayment_ratio": 0.5,
                    "gambling_transaction_count": 1,
                    "gambling_expense_total": 500.0,
                    "month_count": 1,
                    "salary_month_count": 1,
                    "salary_consistency": 1.0,
                    "negative_cashflow_months": 0,
                    "triggered_rules": [],
                },
                "recommendation": "Medium lending risk.",
                "bank_statement_pdf_download_url": (
                    f"http://testserver/api/v1/bank-statements/{account_id}/download"
                ),
            }
        ),
    )

    response = recommendation_service.build_account_recommendations(ACCOUNT_ID)

    assert response.cached is False
    assert response.financial_health_score == 35
    assert "Reduce gambling spend." in response.recommendations
    assert "Reduce entertainment spend." in response.recommendations
    assert "Debt repayments are high." in response.recommendations
    assert "Expenses are above 70% of income." in response.recommendations
    assert "Salary appears consistent." in response.positive_observations
    assert "Cashflow is positive." in response.positive_observations
    assert cached_values[f"recommendations:{ACCOUNT_ID}"]["cached"] is False

    output_key = f"output/{ACCOUNT_ID}/recommendations.json"
    assert response.bank_statement_pdf_download_url == ""
    assert output_key in uploaded_objects


def test_build_account_recommendations_returns_cached_result(monkeypatch) -> None:
    monkeypatch.setattr(
        recommendation_service,
        "get_cache",
        lambda key: {
            "account_id": str(ACCOUNT_ID),
            "cached": False,
            "financial_health_score": 82,
            "recommendations": ["Build emergency savings."],
            "priority_actions": ["Keep monitoring spending and savings monthly."],
            "positive_observations": ["Cashflow is positive."],
            "bank_statement_pdf_download_url": (
                f"http://testserver/api/v1/bank-statements/{ACCOUNT_ID}/download"
            ),
        },
    )

    response = recommendation_service.build_account_recommendations(ACCOUNT_ID)

    assert response.cached is True
    assert response.financial_health_score == 82
    assert response.recommendations == ["Build emergency savings."]
    assert response.bank_statement_pdf_download_url == (
        f"http://testserver/api/v1/bank-statements/{ACCOUNT_ID}/download"
    )


class FakeModel:
    def __init__(self, value: dict) -> None:
        self.value = value

    def model_dump(self, mode: str = "python") -> dict:
        return self.value
