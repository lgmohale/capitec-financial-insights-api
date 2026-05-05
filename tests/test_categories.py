import json
from uuid import UUID

from app.services import categorisation_service

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_categorise_account_transactions_builds_output_and_cache(
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
    monkeypatch.setattr(categorisation_service, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(categorisation_service, "get_cache", cached_values.get)
    monkeypatch.setattr(
        categorisation_service,
        "set_cache",
        lambda key, value: cached_values.update({key: value}),
    )

    response = categorisation_service.categorise_account_transactions(ACCOUNT_ID)
    summary_by_category = {item.category: item for item in response.category_summary}

    assert response.cached is False
    assert summary_by_category["salary"].transaction_count == 1
    assert summary_by_category["salary"].total_amount == 46579.0
    assert summary_by_category["salary"].month_count == 1
    assert summary_by_category["groceries"].transaction_count == 1
    assert summary_by_category["groceries"].total_amount == 1240.5
    assert summary_by_category["groceries"].month_count == 1
    assert cached_values[f"categorisation:{ACCOUNT_ID}"]["cached"] is False

    output_file = output_dir / f"{ACCOUNT_ID}_categories.json"
    assert response.output_file_path == str(output_file)
    assert output_file.exists()


def test_categorise_account_transactions_returns_cached_result(monkeypatch) -> None:
    monkeypatch.setattr(
        categorisation_service,
        "get_cache",
        lambda key: {
            "account_id": str(ACCOUNT_ID),
            "cached": False,
            "category_summary": [
                {
                    "category": "salary",
                    "total_amount": 100.0,
                    "transaction_count": 1,
                    "month_count": 1,
                }
            ],
            "output_file_path": "data/output/result.json",
        },
    )

    response = categorisation_service.categorise_account_transactions(ACCOUNT_ID)

    assert response.cached is True
    assert response.category_summary[0].category == "salary"
    assert response.category_summary[0].month_count == 1
    assert response.output_file_path == "data/output/result.json"
