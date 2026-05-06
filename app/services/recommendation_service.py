from uuid import UUID

from app.core.cache import get_cache, set_cache
from app.schemas.recommendations import RecommendationsResponse
from app.services.aggregation_service import aggregate_account_transactions
from app.services.risk_service import score_account_risk
from app.storage.object_storage import upload_json_object
from app.storage.transactions import processed_output_object_key


def build_account_recommendations(
    account_id: UUID,
    force_refresh: bool = False,
) -> RecommendationsResponse:
    cache_key = f"recommendations:{account_id}"
    if not force_refresh:
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return RecommendationsResponse(**cached_result)

    aggregation = aggregate_account_transactions(
        account_id=account_id,
        force_refresh=force_refresh,
    )
    risk = score_account_risk(account_id=account_id, force_refresh=force_refresh)
    recommendation_result = build_recommendation_result(
        aggregation=aggregation.model_dump(mode="json"),
        risk=risk.model_dump(mode="json"),
    )
    write_recommendations_output(account_id, recommendation_result)
    result = RecommendationsResponse(
        account_id=account_id,
        cached=False,
        **recommendation_result,
    )

    set_cache(cache_key, result.model_dump(mode="json"))

    return result


def build_recommendation_result(aggregation: dict, risk: dict) -> dict:
    if aggregation["transaction_count"] == 0:
        return {
            "financial_health_score": 0,
            "recommendations": ["Link an account with transaction history."],
            "priority_actions": ["Provide transaction data before making decisions."],
            "positive_observations": [],
        }

    total_income = float(aggregation["total_income"])
    total_expenses = float(aggregation["total_expenses"])
    expense_ratio = safe_ratio(total_expenses, total_income)
    category_breakdown = aggregation["category_breakdown"]
    risk_factors = risk["risk_factors"]

    recommendations = []
    priority_actions = []
    positive_observations = []

    gambling_expense_total = category_breakdown.get("gambling", {}).get(
        "expenses",
        0.0,
    )
    entertainment_expense_total = category_breakdown.get("entertainment", {}).get(
        "expenses",
        0.0,
    )
    debt_repayment_ratio = float(risk_factors["debt_repayment_ratio"])

    if gambling_expense_total > 0:
        recommendations.append("Reduce gambling spend.")
        priority_actions.append(
            "Pause gambling transactions and redirect funds to savings."
        )

    if entertainment_expense_total > total_income * 0.1:
        recommendations.append("Reduce entertainment spend.")

    if debt_repayment_ratio > 0.4:
        recommendations.append("Debt repayments are high.")
        priority_actions.append("Review debt obligations before taking new credit.")
    elif debt_repayment_ratio > 0.25:
        recommendations.append("Debt repayments are elevated.")

    if expense_ratio > 0.7:
        recommendations.append("Expenses are above 70% of income.")
        priority_actions.append(
            "Reduce discretionary spending to improve affordability."
        )

    if risk_factors["negative_cashflow_months"] > 0:
        priority_actions.append(
            "Stabilise monthly cashflow before increasing commitments."
        )

    if expense_ratio < 0.7 and risk_factors["negative_cashflow_months"] == 0:
        recommendations.append("Build emergency savings.")

    if risk_factors["salary_consistency"] >= 1.0:
        positive_observations.append("Salary appears consistent.")

    if aggregation["net_cashflow"] > 0:
        positive_observations.append("Cashflow is positive.")

    if debt_repayment_ratio <= 0.25:
        positive_observations.append("Debt repayment pressure appears manageable.")

    if not recommendations:
        recommendations.append("Maintain current spending discipline.")

    if not priority_actions:
        priority_actions.append("Keep monitoring spending and savings monthly.")

    financial_health_score = calculate_financial_health_score(
        risk_score=int(risk["risk_score"]),
        expense_ratio=expense_ratio,
        debt_repayment_ratio=debt_repayment_ratio,
        gambling_expense_total=gambling_expense_total,
        salary_consistency=float(risk_factors["salary_consistency"]),
        negative_cashflow_months=int(risk_factors["negative_cashflow_months"]),
    )

    return {
        "financial_health_score": financial_health_score,
        "recommendations": recommendations,
        "priority_actions": priority_actions,
        "positive_observations": positive_observations,
    }


def calculate_financial_health_score(
    risk_score: int,
    expense_ratio: float,
    debt_repayment_ratio: float,
    gambling_expense_total: float,
    salary_consistency: float,
    negative_cashflow_months: int,
) -> int:
    score = 100 - risk_score

    if expense_ratio > 0.7:
        score -= 10
    if debt_repayment_ratio > 0.25:
        score -= 10
    if gambling_expense_total > 0:
        score -= 10
    if salary_consistency >= 1.0:
        score += 5
    if negative_cashflow_months == 0:
        score += 5

    return max(0, min(100, score))


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def write_recommendations_output(
    account_id: UUID,
    recommendation_result: dict,
) -> str:
    object_key = processed_output_object_key(account_id, "recommendations")
    return upload_json_object(
        object_key=object_key,
        value={
            "account_id": str(account_id),
            **recommendation_result,
        },
    )
