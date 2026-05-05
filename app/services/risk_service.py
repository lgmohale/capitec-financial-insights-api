import json
from pathlib import Path
from uuid import UUID

from app.core.cache import get_cache, set_cache
from app.schemas.risk import RiskResponse
from app.services.aggregation_service import aggregate_account_transactions
from app.services.categorisation_service import (
    categorise_transaction,
    read_transactions,
)
from app.storage.transactions import OUTPUT_DIR


def score_account_risk(
    account_uuid: UUID,
    force_refresh: bool = False,
) -> RiskResponse:
    cache_key = f"risk:{account_uuid}"
    if not force_refresh:
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return RiskResponse(**cached_result)

    transactions = read_transactions(account_uuid)
    aggregation = aggregate_account_transactions(
        account_uuid=account_uuid,
        force_refresh=force_refresh,
    )
    risk_result = build_risk_result(transactions, aggregation.model_dump(mode="json"))
    output_file_path = write_risk_output(account_uuid, risk_result)
    result = RiskResponse(
        account_uuid=account_uuid,
        cached=False,
        output_file_path=str(output_file_path),
        **risk_result,
    )

    set_cache(cache_key, result.model_dump(mode="json"))

    return result


def build_risk_result(transactions: list[dict], aggregation: dict) -> dict:
    transaction_count = int(aggregation["transaction_count"])
    if transaction_count == 0:
        return build_no_data_result()

    month_count = max(len(aggregation["monthly_summary"]), 1)
    monthly_income_average = aggregation["total_income"] / month_count
    monthly_expense_average = aggregation["total_expenses"] / month_count
    debt_expense_total = (
        aggregation["category_breakdown"]
        .get(
            "debt_repayment",
            {},
        )
        .get("expenses", 0.0)
    )
    debt_repayment_ratio = safe_ratio(debt_expense_total, monthly_income_average)
    gambling_breakdown = aggregation["category_breakdown"].get("gambling", {})
    gambling_transaction_count = int(gambling_breakdown.get("transaction_count", 0))
    gambling_expense_total = float(gambling_breakdown.get("expenses", 0.0))
    salary_month_count = count_salary_months(transactions)
    salary_consistency = safe_ratio(salary_month_count, month_count)
    negative_cashflow_months = sum(
        1
        for monthly_values in aggregation["monthly_summary"].values()
        if monthly_values["net_cashflow"] < 0
    )

    risk_score, triggered_rules = calculate_risk_score(
        monthly_income_average=monthly_income_average,
        monthly_expense_average=monthly_expense_average,
        debt_repayment_ratio=debt_repayment_ratio,
        gambling_transaction_count=gambling_transaction_count,
        salary_consistency=salary_consistency,
        negative_cashflow_months=negative_cashflow_months,
        month_count=month_count,
    )

    return {
        "risk_score": risk_score,
        "risk_band": get_risk_band(risk_score),
        "risk_factors": {
            "monthly_income_average": round(monthly_income_average, 2),
            "monthly_expense_average": round(monthly_expense_average, 2),
            "debt_repayment_ratio": round(debt_repayment_ratio, 4),
            "gambling_transaction_count": gambling_transaction_count,
            "gambling_expense_total": round(gambling_expense_total, 2),
            "month_count": month_count,
            "salary_month_count": salary_month_count,
            "salary_consistency": round(salary_consistency, 4),
            "negative_cashflow_months": negative_cashflow_months,
            "triggered_rules": triggered_rules,
        },
        "recommendation": get_recommendation(risk_score),
    }


def build_no_data_result() -> dict:
    return {
        "risk_score": 0,
        "risk_band": "NO_DATA",
        "risk_factors": {
            "monthly_income_average": 0.0,
            "monthly_expense_average": 0.0,
            "debt_repayment_ratio": 0.0,
            "gambling_transaction_count": 0,
            "gambling_expense_total": 0.0,
            "month_count": 0,
            "salary_month_count": 0,
            "salary_consistency": 0.0,
            "negative_cashflow_months": 0,
            "triggered_rules": ["No transaction data available."],
        },
        "recommendation": "Insufficient transaction data to assess lending risk.",
    }


def calculate_risk_score(
    monthly_income_average: float,
    monthly_expense_average: float,
    debt_repayment_ratio: float,
    gambling_transaction_count: int,
    salary_consistency: float,
    negative_cashflow_months: int,
    month_count: int,
) -> tuple[int, list[str]]:
    score = 10
    triggered_rules = ["Base risk score starts at 10 for available transaction data."]
    expense_ratio = safe_ratio(monthly_expense_average, monthly_income_average)

    if monthly_income_average <= 0:
        score += 35
        triggered_rules.append("No monthly income detected.")
    if expense_ratio > 0.9:
        score += 20
        triggered_rules.append("Monthly expenses exceed 90% of monthly income.")
    elif expense_ratio > 0.75:
        score += 10
        triggered_rules.append("Monthly expenses exceed 75% of monthly income.")

    if debt_repayment_ratio > 0.4:
        score += 25
        triggered_rules.append("Debt repayments exceed 40% of monthly income.")
    elif debt_repayment_ratio > 0.25:
        score += 15
        triggered_rules.append("Debt repayments exceed 25% of monthly income.")

    if gambling_transaction_count >= 3:
        score += 20
        triggered_rules.append("Repeated gambling transactions detected.")
    elif gambling_transaction_count > 0:
        score += 10
        triggered_rules.append("Gambling transaction detected.")

    if salary_consistency < 0.5:
        score += 20
        triggered_rules.append("Salary appears in fewer than half of observed months.")
    elif salary_consistency < 1.0 and month_count > 1:
        score += 10
        triggered_rules.append("Salary is not present in every observed month.")

    if negative_cashflow_months > 0:
        score += min(25, negative_cashflow_months * 10)
        triggered_rules.append("One or more months have negative cashflow.")

    return min(score, 100), triggered_rules


def count_salary_months(transactions: list[dict]) -> int:
    salary_months = {
        str(transaction.get("date", ""))[:7]
        for transaction in transactions
        if categorise_transaction(transaction) == "salary"
    }
    return len(salary_months)


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def get_risk_band(risk_score: int) -> str:
    if risk_score >= 70:
        return "HIGH_RISK"
    if risk_score >= 40:
        return "MEDIUM_RISK"
    return "LOW_RISK"


def get_recommendation(risk_score: int) -> str:
    if risk_score >= 70:
        return "High lending risk. Review affordability and risk factors manually."
    if risk_score >= 40:
        return "Medium lending risk. Consider lower exposure or additional checks."
    return "Low lending risk based on available transaction behaviour."


def write_risk_output(account_uuid: UUID, risk_result: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file_path = OUTPUT_DIR / f"{account_uuid}_risk.json"
    output_file_path.write_text(
        json.dumps(
            {
                "account_uuid": str(account_uuid),
                **risk_result,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_file_path
