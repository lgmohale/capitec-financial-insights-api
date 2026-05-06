from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecommendationsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "cached": False,
                "financial_health_score": 70,
                "recommendations": [
                    "Reduce gambling spend.",
                    "Build emergency savings.",
                ],
                "priority_actions": [
                    "Pause gambling transactions and redirect funds to savings."
                ],
                "positive_observations": [
                    "Salary appears consistent.",
                    "Cashflow is positive.",
                ],
                "bank_statement_pdf_download_url": (
                    "http://localhost:8000/api/v1/bank-statements/"
                    "550e8400-e29b-41d4-a716-446655440000/download"
                ),
            }
        }
    )

    account_id: UUID
    cached: bool
    financial_health_score: int
    recommendations: list[str]
    priority_actions: list[str]
    positive_observations: list[str]
    bank_statement_pdf_download_url: str = ""
