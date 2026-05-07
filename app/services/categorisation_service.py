from uuid import UUID

from fastapi import HTTPException, status

from app.core.cache import get_cache, set_cache
from app.schemas.categories import CategoriesResponse
from app.storage.object_storage import upload_json_object
from app.storage.transactions import (
    processed_output_object_key,
    read_starter_transactions,
)

CATEGORY_KEYWORDS = {
    "salary": ["salary", "wage", "payroll", "employer"],
    "groceries": ["checkers", "shoprite", "woolworths", "pick n pay", "grocer"],
    "fuel": ["shell", "bp", "engen", "sasol", "fuel", "garage"],
    "rent_or_home_loan": ["rent", "home loan", "bond", "mortgage"],
    "insurance": ["insurance", "insure", "policy", "premium"],
    "education": ["school", "university", "tuition", "education", "college"],
    "debt_repayment": ["loan repayment", "credit card", "debt", "repayment"],
    "gambling": ["hollywoodbets", "betway", "bet", "casino", "lotto"],
    "entertainment": ["netflix", "spotify", "cinema", "showmax", "entertainment"],
    "utilities": ["electricity", "water", "municipality", "rates", "utility"],
    "transfer": ["transfer", "eft", "payment to", "send money"],
    "bank_fees": ["bank fee", "service fee", "monthly fee", "charges"],
}

CATEGORIES = [
    "salary",
    "groceries",
    "fuel",
    "rent_or_home_loan",
    "insurance",
    "education",
    "debt_repayment",
    "gambling",
    "entertainment",
    "utilities",
    "transfer",
    "bank_fees",
    "unknown",
]


def categorise_statement_transactions(
    statement_id: UUID,
    force_refresh: bool = False,
) -> CategoriesResponse:
    cache_key = f"categorisation:{statement_id}"
    if not force_refresh:
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return CategoriesResponse(**cached_result)

    transactions = read_transactions(statement_id)
    category_summary = build_category_summary(transactions)
    write_category_output(statement_id, category_summary)
    result = CategoriesResponse(
        statement_id=statement_id,
        cached=False,
        category_summary=category_summary,
    )

    set_cache(cache_key, result.model_dump(mode="json"))

    return result


def read_transactions(statement_id: UUID) -> list[dict]:
    try:
        return read_starter_transactions(statement_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction object not found for bank statement: {statement_id}",
        ) from exc


def build_category_summary(transactions: list[dict]) -> list[dict]:
    category_summary = {
        category: {
            "category": category,
            "total_amount": 0.0,
            "transaction_count": 0,
        }
        for category in CATEGORIES
    }
    for transaction in transactions:
        category = categorise_transaction(transaction)
        amount = abs(float(transaction.get("amount", 0.0)))
        category_summary[category]["total_amount"] += amount
        category_summary[category]["transaction_count"] += 1

    return [
        {
            "category": values["category"],
            "total_amount": round(values["total_amount"], 2),
            "transaction_count": values["transaction_count"],
        }
        for values in category_summary.values()
    ]


def categorise_transaction(transaction: dict) -> str:
    searchable_text = " ".join(
        [
            str(transaction.get("description", "")),
            str(transaction.get("merchant", "")),
        ]
    ).lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in searchable_text for keyword in keywords):
            return category

    return "unknown"


def write_category_output(
    statement_id: UUID,
    category_summary: list[dict],
) -> str:
    object_key = processed_output_object_key(statement_id, "categories")
    return upload_json_object(
        object_key=object_key,
        value={
            "statement_id": str(statement_id),
            "category_summary": category_summary,
        },
    )
