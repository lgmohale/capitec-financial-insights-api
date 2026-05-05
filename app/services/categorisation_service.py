import json
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status

from app.core.cache import get_cache, set_cache
from app.schemas.categories import CategoriesResponse
from app.storage.transactions import INPUT_DIR, OUTPUT_DIR

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


def categorise_account_transactions(
    account_id: UUID,
    force_refresh: bool = False,
) -> CategoriesResponse:
    cache_key = f"categorisation:{account_id}"
    if not force_refresh:
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return CategoriesResponse(**cached_result)

    transactions = read_transactions(account_id)
    category_summary = build_category_summary(transactions)
    output_file_path = write_category_output(account_id, category_summary)
    result = CategoriesResponse(
        account_id=account_id,
        cached=False,
        category_summary=category_summary,
        output_file_path=str(output_file_path),
    )

    set_cache(cache_key, result.model_dump(mode="json"))

    return result


def read_transactions(account_id: UUID) -> list[dict]:
    input_file_path = INPUT_DIR / f"{account_id}.json"
    if not input_file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction file not found: {input_file_path}",
        )

    return json.loads(input_file_path.read_text(encoding="utf-8"))


def build_category_summary(transactions: list[dict]) -> list[dict]:
    category_summary = {
        category: {
            "category": category,
            "total_amount": 0.0,
            "transaction_count": 0,
            "months": set(),
        }
        for category in CATEGORIES
    }
    for transaction in transactions:
        category = categorise_transaction(transaction)
        amount = abs(float(transaction.get("amount", 0.0)))
        month = str(transaction.get("date", ""))[:7]
        category_summary[category]["total_amount"] += amount
        category_summary[category]["transaction_count"] += 1
        category_summary[category]["months"].add(month)

    return [
        {
            "category": values["category"],
            "total_amount": round(values["total_amount"], 2),
            "transaction_count": values["transaction_count"],
            "month_count": len(values["months"]),
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
    account_id: UUID,
    category_summary: list[dict],
) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file_path = OUTPUT_DIR / f"{account_id}_categories.json"
    output_file_path.write_text(
        json.dumps(
            {
                "account_id": str(account_id),
                "category_summary": category_summary,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_file_path
