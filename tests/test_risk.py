import json
from uuid import UUID

from app.services import aggregation_service, categorisation_service, risk_service

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_score_account_risk_builds_explainable_result_and_cache(
    tmp_path,
    monkeypatch,
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    input_file = input_dir / f"{ACCOUNT_ID}.json"
    input_file.write_text(
        json.dumps(
            [
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
        ),
        encoding="utf-8",
    )
    cached_values = {}

    monkeypatch.setattr(categorisation_service, "INPUT_DIR", input_dir)
    monkeypatch.setattr(aggregation_service, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(risk_service, "OUTPUT_DIR", output_dir)
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

    output_file = output_dir / f"{ACCOUNT_ID}_risk.json"
    assert response.output_file_path == str(output_file)
    assert output_file.exists()


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
            "output_file_path": "data/output/result.json",
        },
    )

    response = risk_service.score_account_risk(ACCOUNT_ID)

    assert response.cached is True
    assert response.risk_score == 80
    assert response.risk_band == "HIGH_RISK"
    assert response.output_file_path == "data/output/result.json"
