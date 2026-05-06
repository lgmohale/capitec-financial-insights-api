from uuid import UUID

from app.services import aggregation_service, risk_service

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_score_account_risk_builds_explainable_result_and_cache(
    monkeypatch,
) -> None:
    test_transactions = [
        {
            "id": "txn-001",
            "date": "2026-04-25",
            "type": "credit",
            "description": "SALARY PAYMENT EMPLOYER",
            "amount": 10000.0,
            "currency": "ZAR",
            "balance": 10000.0,
            "merchant": "Employer",
        },
        {
            "id": "txn-002",
            "date": "2026-04-26",
            "type": "debit",
            "description": "LOAN REPAYMENT",
            "amount": -5000.0,
            "currency": "ZAR",
            "balance": 5000.0,
            "merchant": "Personal Loan",
        },
        {
            "id": "txn-003",
            "date": "2026-04-27",
            "type": "debit",
            "description": "HOLLYWOODBETS ONLINE",
            "amount": -500.0,
            "currency": "ZAR",
            "balance": 4500.0,
            "merchant": "Hollywoodbets",
        },
    ]
    cached_values = {}
    uploaded_objects = {}

    monkeypatch.setattr(
        risk_service, "read_transactions", lambda account_id: test_transactions
    )
    monkeypatch.setattr(
        aggregation_service,
        "read_transactions",
        lambda account_id: test_transactions,
    )
    for service in (aggregation_service, risk_service):
        monkeypatch.setattr(
            service,
            "upload_json_object",
            lambda object_key, value: uploaded_objects.setdefault(object_key, value)
            and object_key,
        )
    monkeypatch.setattr(aggregation_service, "get_cache", lambda key: None)
    monkeypatch.setattr(
        aggregation_service,
        "set_cache",
        lambda key, value: None,
    )
    monkeypatch.setattr(risk_service, "get_cache", cached_values.get)
    monkeypatch.setattr(
        risk_service,
        "set_cache",
        lambda key, value: cached_values.update({key: value}),
    )

    response = risk_service.score_account_risk(ACCOUNT_ID)

    assert response.cached is False
    assert response.risk_score == 45
    assert response.risk_band == "MEDIUM_RISK"
    assert response.risk_factors.monthly_income_average == 10000.0
    assert response.risk_factors.monthly_expense_average == 5500.0
    assert response.risk_factors.debt_repayment_ratio == 0.5
    assert response.risk_factors.gambling_transaction_count == 1
    assert response.risk_factors.month_count == 1
    assert "Debt repayments exceed 40% of monthly income." in (
        response.risk_factors.triggered_rules
    )
    assert cached_values[f"risk:{ACCOUNT_ID}"]["cached"] is False

    output_key = f"output/{ACCOUNT_ID}/risk.json"
    assert response.bank_statement_pdf_download_url == ""
    assert output_key in uploaded_objects


def test_score_account_risk_returns_cached_result(monkeypatch) -> None:
    monkeypatch.setattr(
        risk_service,
        "get_cache",
        lambda key: {
            "account_id": str(ACCOUNT_ID),
            "cached": False,
            "risk_score": 80,
            "risk_band": "HIGH_RISK",
            "risk_factors": {
                "monthly_income_average": 1000.0,
                "monthly_expense_average": 1200.0,
                "debt_repayment_ratio": 0.3,
                "gambling_transaction_count": 3,
                "gambling_expense_total": 400.0,
                "month_count": 2,
                "salary_month_count": 1,
                "salary_consistency": 0.5,
                "negative_cashflow_months": 1,
                "triggered_rules": ["Cached risk result."],
            },
            "recommendation": "Review manually.",
            "bank_statement_pdf_download_url": (
                f"http://testserver/api/v1/bank-statements/{ACCOUNT_ID}/download"
            ),
        },
    )

    response = risk_service.score_account_risk(ACCOUNT_ID)

    assert response.cached is True
    assert response.risk_score == 80
    assert response.risk_band == "HIGH_RISK"
    assert response.bank_statement_pdf_download_url == (
        f"http://testserver/api/v1/bank-statements/{ACCOUNT_ID}/download"
    )
