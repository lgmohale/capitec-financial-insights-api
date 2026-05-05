import json
from pathlib import Path
from uuid import UUID

from app.core.cache import get_cache, set_cache
from app.schemas.aggregation import AggregationResponse
from app.services.categorisation_service import (
    CATEGORIES,
    categorise_transaction,
    read_transactions,
)
from app.storage.transactions import OUTPUT_DIR


def aggregate_account_transactions(
    account_uuid: UUID,
    force_refresh: bool = False,
) -> AggregationResponse:
    cache_key = f"aggregation:{account_uuid}"
    if not force_refresh:
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return AggregationResponse(**cached_result)

    transactions = read_transactions(account_uuid)
    aggregation = build_aggregation(transactions)
    output_file_path = write_aggregation_output(account_uuid, aggregation)
    result = AggregationResponse(
        account_uuid=account_uuid,
        cached=False,
        output_file_path=str(output_file_path),
        **aggregation,
    )

    set_cache(cache_key, result.model_dump(mode="json"))

    return result


def build_aggregation(transactions: list[dict]) -> dict:
    category_breakdown = {
        category: {"transaction_count": 0, "income": 0.0, "expenses": 0.0}
        for category in CATEGORIES
    }
    monthly_summary: dict[str, dict] = {}
    total_income = 0.0
    total_expenses = 0.0

    for transaction in transactions:
        amount = float(transaction.get("amount", 0.0))
        month = str(transaction.get("date", ""))[:7]
        category = categorise_transaction(transaction)
        income = amount if amount > 0 else 0.0
        expenses = abs(amount) if amount < 0 else 0.0

        total_income += income
        total_expenses += expenses

        category_breakdown[category]["transaction_count"] += 1
        category_breakdown[category]["income"] += income
        category_breakdown[category]["expenses"] += expenses

        monthly_values = monthly_summary.setdefault(
            month,
            {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_cashflow": 0.0,
                "transaction_count": 0,
            },
        )
        monthly_values["total_income"] += income
        monthly_values["total_expenses"] += expenses
        monthly_values["net_cashflow"] += amount
        monthly_values["transaction_count"] += 1

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_cashflow": total_income - total_expenses,
        "transaction_count": len(transactions),
        "month_count": len(monthly_summary),
        "category_breakdown": category_breakdown,
        "monthly_summary": monthly_summary,
    }


def write_aggregation_output(account_uuid: UUID, aggregation: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file_path = OUTPUT_DIR / f"{account_uuid}_aggregation.json"
    output_file_path.write_text(
        json.dumps(
            {
                "account_uuid": str(account_uuid),
                **aggregation,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_file_path
