from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LinkedAccount, User
from app.schemas.bank_accounts import LinkedAccountMetadata, UserMetadata
from app.schemas.financial_insights import FinancialInsightsResponse
from app.services.aggregation_service import aggregate_account_transactions
from app.services.recommendation_service import build_account_recommendations
from app.services.risk_service import score_account_risk


def build_financial_insights(
    account_id: UUID,
    db: Session,
) -> FinancialInsightsResponse:
    linked_account = db.scalar(
        select(LinkedAccount).where(LinkedAccount.id == account_id)
    )
    if linked_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Linked account not found: {account_id}",
        )

    user = db.scalar(select(User).where(User.id == linked_account.user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found for linked account: {account_id}",
        )

    aggregation = aggregate_account_transactions(account_id=account_id)
    risk = score_account_risk(account_id=account_id)
    recommendations = build_account_recommendations(account_id=account_id)

    return FinancialInsightsResponse(
        account_id=account_id,
        user=UserMetadata.model_validate(user),
        linked_account=LinkedAccountMetadata.model_validate(linked_account),
        aggregation=aggregation,
        risk=risk,
        recommendations=recommendations,
        generated_at=datetime.now(timezone.utc),  # noqa: UP017
    )
