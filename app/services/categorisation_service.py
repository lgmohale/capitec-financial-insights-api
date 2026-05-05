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
    account_uuid: UUID,
    force_refresh: bool = False,
) -> CategoriesResponse:
    cache_key = f"categorisation:{account_uuid}"
    if not force_refresh:
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return CategoriesResponse(**cached_result)

    transactions = read_transactions(account_uuid)
    category_summary = build_category_summary(transactions)
    output_file_path = write_category_output(account_uuid, category_summary)
    result = CategoriesResponse(
        account_uuid=account_uuid,
        cached=False,
        category_summary=category_summary,
        output_file_path=str(output_file_path),
    )

    set_cache(cache_key, result.model_dump(mode="json"))

    return result


def read_transactions(account_uuid: UUID) -> list[dict]:
    input_file_path = INPUT_DIR / f"{account_uuid}.json"
    if not input_file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction file not found: {input_file_path}",
        )

    return json.loads(input_file_path.read_text(encoding="utf-8"))


def build_category_summary(transactions: list[dict]) -> dict[str, int]:
    category_summary = {category: 0 for category in CATEGORIES}
    for transaction in transactions:
        category = categorise_transaction(transaction)
        category_summary[category] += 1

    return category_summary


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
    account_uuid: UUID,
    category_summary: dict[str, int],
) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file_path = OUTPUT_DIR / f"{account_uuid}_categories.json"
    output_file_path.write_text(
        json.dumps(
            {
                "account_uuid": str(account_uuid),
                "category_summary": category_summary,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_file_path
