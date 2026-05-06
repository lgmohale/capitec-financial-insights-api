from uuid import UUID

from app.services import categorisation_service

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_categorise_account_transactions_builds_output_and_cache(
    monkeypatch,
) -> None:
    cached_values = {}
    uploaded_objects = {}

    monkeypatch.setattr(
        categorisation_service,
        "read_transactions",
        lambda account_id: [
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
        ],
    )
    monkeypatch.setattr(
        categorisation_service,
        "upload_json_object",
        lambda object_key, value: uploaded_objects.setdefault(object_key, value)
        and object_key,
    )
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
    assert summary_by_category["groceries"].transaction_count == 1
    assert summary_by_category["groceries"].total_amount == 1240.5
    assert cached_values[f"categorisation:{ACCOUNT_ID}"]["cached"] is False

    output_key = f"output/{ACCOUNT_ID}/categories.json"
    assert response.bank_statement_pdf_download_url == ""
    assert output_key in uploaded_objects


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
                }
            ],
            "bank_statement_pdf_download_url": (
                f"http://testserver/api/v1/bank-statements/{ACCOUNT_ID}/download"
            ),
        },
    )

    response = categorisation_service.categorise_account_transactions(ACCOUNT_ID)

    assert response.cached is True
    assert response.category_summary[0].category == "salary"
    assert response.bank_statement_pdf_download_url == (
        f"http://testserver/api/v1/bank-statements/{ACCOUNT_ID}/download"
    )
