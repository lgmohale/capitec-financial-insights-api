from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from uuid import UUID

from app.core.cache import get_cache, set_cache
from app.core.logging import get_logger
from app.core.metrics import AGGREGATION_COMPLETED, AGGREGATION_FAILURES
from app.schemas.aggregation import AggregationResponse
from app.services.categorisation_service import (
    CATEGORIES,
    categorise_transaction,
    read_transactions,
)
from app.storage.object_storage import upload_json_object
from app.storage.transactions import processed_output_object_key

MONEY_QUANTIZER = Decimal("0.01")
logger = get_logger(__name__)


def aggregate_statement_transactions(
    statement_id: UUID,
    force_refresh: bool = False,
) -> AggregationResponse:
    try:
        logger.info(
            "Aggregation started",
            extra={
                "statement_id": str(statement_id),
                "event_name": "aggregation_started",
            },
        )
        cache_key = f"aggregation:{statement_id}"
        if not force_refresh:
            cached_result = get_cache(cache_key)
            if cached_result is not None:
                cached_result["cached"] = True
                AGGREGATION_COMPLETED.labels("aggregation_cache_hit").inc()
                return AggregationResponse(**cached_result)

        transactions = read_transactions(statement_id)
        aggregation = build_aggregation(transactions)
        write_aggregation_output(statement_id, aggregation)
        result = AggregationResponse(
            statement_id=statement_id,
            cached=False,
            **aggregation,
        )

        set_cache(cache_key, result.model_dump(mode="json"))
        AGGREGATION_COMPLETED.labels("aggregation_completed").inc()
        logger.info(
            "Aggregation completed",
            extra={
                "statement_id": str(statement_id),
                "event_name": "aggregation_completed",
            },
        )
        return result
    except Exception:
        AGGREGATION_FAILURES.labels("aggregation_failed").inc()
        logger.exception(
            "Aggregation failed",
            extra={
                "statement_id": str(statement_id),
                "event_name": "aggregation_failed",
            },
        )
        raise


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

    net_cashflow = total_income - total_expenses
    month_count = len(monthly_summary)
    category_breakdown = enrich_category_breakdown(
        category_breakdown=category_breakdown,
        total_income=total_income,
        total_expenses=total_expenses,
    )
    monthly_summary = enrich_monthly_summary(monthly_summary)
    risk_flags = build_risk_flags(category_breakdown, monthly_summary)

    return {
        "total_income": round_metric(total_income),
        "total_expenses": round_metric(total_expenses),
        "net_cashflow": round_metric(net_cashflow),
        "transaction_count": len(transactions),
        "month_count": month_count,
        "average_monthly_income": safe_average(total_income, month_count),
        "average_monthly_expenses": safe_average(total_expenses, month_count),
        "average_monthly_net_cashflow": safe_average(net_cashflow, month_count),
        "savings_rate": safe_percentage(net_cashflow, total_income),
        "category_breakdown": category_breakdown,
        "monthly_summary": monthly_summary,
        "risk_flags": risk_flags,
        "insights": build_insights(category_breakdown, monthly_summary, risk_flags),
    }


def enrich_category_breakdown(
    category_breakdown: dict[str, dict],
    total_income: float,
    total_expenses: float,
) -> dict[str, dict]:
    enriched_breakdown = {}
    for category, values in category_breakdown.items():
        income = round_metric(values["income"])
        expenses = round_metric(values["expenses"])
        category_values = {
            "transaction_count": values["transaction_count"],
            "income": income,
            "expenses": expenses,
            "net_amount": round_metric(income - expenses),
        }
        if income > 0:
            category_values["income_percentage"] = safe_percentage(income, total_income)
        if expenses > 0:
            category_values["expense_percentage"] = safe_percentage(
                expenses,
                total_expenses,
            )
        enriched_breakdown[category] = category_values
    return enriched_breakdown


def enrich_monthly_summary(monthly_summary: dict[str, dict]) -> dict[str, dict]:
    enriched_summary = {}
    for month, values in monthly_summary.items():
        total_income = round_metric(values["total_income"])
        total_expenses = round_metric(values["total_expenses"])
        net_cashflow = round_metric(values["net_cashflow"])
        enriched_summary[month] = {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_cashflow": net_cashflow,
            "transaction_count": values["transaction_count"],
            "savings_rate": safe_percentage(net_cashflow, total_income),
        }
    return enriched_summary


def build_risk_flags(
    category_breakdown: dict[str, dict],
    monthly_summary: dict[str, dict],
) -> dict[str, bool]:
    return {
        "salary_detected": category_breakdown["salary"]["income"] > 0,
        "has_gambling_spend": category_breakdown["gambling"]["expenses"] > 0,
        "has_negative_cashflow_month": any(
            month_values["net_cashflow"] < 0
            for month_values in monthly_summary.values()
        ),
        "has_unknown_income": category_breakdown["unknown"]["income"] > 0,
    }


def build_insights(
    category_breakdown: dict[str, dict],
    monthly_summary: dict[str, dict],
    risk_flags: dict[str, bool],
) -> list[str]:
    insights = []
    if risk_flags["salary_detected"]:
        insights.append("Salary income appears consistent across the analysed period.")

    largest_expense_category = get_largest_expense_category(category_breakdown)
    if largest_expense_category is not None:
        category_name = humanise_category(largest_expense_category)
        insights.append(f"{category_name} is the largest expense category.")

    if risk_flags["has_negative_cashflow_month"]:
        insights.append("At least one month had negative net cashflow.")
    elif monthly_summary:
        insights.append("Net cashflow remained positive across all analysed months.")

    if risk_flags["has_gambling_spend"]:
        insights.append("Gambling spend was detected in the analysed period.")
    if risk_flags["has_unknown_income"]:
        insights.append(
            "Some income transactions could not be categorised and may require review."
        )

    return insights


def get_largest_expense_category(
    category_breakdown: dict[str, dict],
) -> Optional[str]:  # noqa: UP007
    expense_categories = {
        category: values["expenses"]
        for category, values in category_breakdown.items()
        if values["expenses"] > 0
    }
    if not expense_categories:
        return None
    return max(expense_categories, key=expense_categories.get)


def humanise_category(category: str) -> str:
    return category.replace("_", " ").capitalize()


def safe_average(total: float, count: int) -> float:
    if count <= 0:
        return 0.0
    return round_metric(total / count)


def safe_percentage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round_metric((numerator / denominator) * 100)


def round_metric(value: float) -> float:
    return float(
        Decimal(str(value)).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP),
    )


def write_aggregation_output(statement_id: UUID, aggregation: dict) -> str:
    object_key = processed_output_object_key(statement_id, "aggregation")
    return upload_json_object(
        object_key=object_key,
        value={
            "statement_id": str(statement_id),
            **aggregation,
        },
    )
