import json
from uuid import UUID

from app.services import aggregation_service, categorisation_service

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_aggregate_account_transactions_builds_output_and_cache(
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
                    "amount": 46579.0,
                    "currency": "ZAR",
                    "balance": 46579.0,
                    "merchant": "Employer",
                },
                {
                    "id": "txn-002",
                    "date": "2026-04-26",
                    "type": "debit",
                    "description": "CHECKERS HYPER GROCERIES",
                    "amount": -1240.5,
                    "currency": "ZAR",
                    "balance": 45338.5,
                    "merchant": "Checkers",
                },
            ]
        ),
        encoding="utf-8",
    )
    cached_values = {}

    monkeypatch.setattr(categorisation_service, "INPUT_DIR", input_dir)
    monkeypatch.setattr(aggregation_service, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(aggregation_service, "get_cache", cached_values.get)
    monkeypatch.setattr(
        aggregation_service,
        "set_cache",
        lambda key, value: cached_values.update({key: value}),
    )

    response = aggregation_service.aggregate_account_transactions(ACCOUNT_ID)

    assert response.cached is False
    assert response.total_income == 46579.0
    assert response.total_expenses == 1240.5
    assert response.net_cashflow == 45338.5
    assert response.transaction_count == 2
    assert response.month_count == 1
    assert response.average_monthly_income == 46579.0
    assert response.average_monthly_expenses == 1240.5
    assert response.average_monthly_net_cashflow == 45338.5
    assert response.savings_rate == 97.34
    assert response.category_breakdown["salary"].transaction_count == 1
    assert response.category_breakdown["salary"].net_amount == 46579.0
    assert response.category_breakdown["salary"].income_percentage == 100.0
    assert response.category_breakdown["groceries"].expenses == 1240.5
    assert response.category_breakdown["groceries"].net_amount == -1240.5
    assert response.category_breakdown["groceries"].expense_percentage == 100.0
    assert response.monthly_summary["2026-04"].transaction_count == 2
    assert response.monthly_summary["2026-04"].savings_rate == 97.34
    assert response.risk_flags.salary_detected is True
    assert response.risk_flags.has_gambling_spend is False
    assert response.risk_flags.has_negative_cashflow_month is False
    assert response.risk_flags.has_unknown_income is False
    assert response.insights == [
        "Salary income appears consistent across the analysed period.",
        "Groceries is the largest expense category.",
        "Net cashflow remained positive across all analysed months.",
    ]
    assert cached_values[f"aggregation:{ACCOUNT_ID}"]["cached"] is False

    output_file = output_dir / f"{ACCOUNT_ID}_aggregation.json"
    assert response.output_file_path == str(output_file)
    assert output_file.exists()


def test_aggregate_account_transactions_returns_cached_result(monkeypatch) -> None:
    monkeypatch.setattr(
        aggregation_service,
        "get_cache",
        lambda key: {
            "account_id": str(ACCOUNT_ID),
            "cached": False,
            "total_income": 100.0,
            "total_expenses": 25.0,
            "net_cashflow": 75.0,
            "transaction_count": 2,
            "month_count": 1,
            "average_monthly_income": 100.0,
            "average_monthly_expenses": 25.0,
            "average_monthly_net_cashflow": 75.0,
            "savings_rate": 75.0,
            "category_breakdown": {
                "salary": {
                    "transaction_count": 1,
                    "income": 100.0,
                    "expenses": 0.0,
                    "net_amount": 100.0,
                    "income_percentage": 100.0,
                }
            },
            "monthly_summary": {
                "2026-04": {
                    "total_income": 100.0,
                    "total_expenses": 25.0,
                    "net_cashflow": 75.0,
                    "transaction_count": 2,
                    "savings_rate": 75.0,
                }
            },
            "risk_flags": {
                "salary_detected": True,
                "has_gambling_spend": False,
                "has_negative_cashflow_month": False,
                "has_unknown_income": False,
            },
            "insights": [
                "Salary income appears consistent across the analysed period.",
                "Net cashflow remained positive across all analysed months.",
            ],
            "output_file_path": "data/output/result.json",
        },
    )

    response = aggregation_service.aggregate_account_transactions(ACCOUNT_ID)

    assert response.cached is True
    assert response.total_income == 100.0
    assert response.output_file_path == "data/output/result.json"
