from fastapi import FastAPI

from app.api.v1.aggregation import router as aggregation_router
from app.api.v1.bank_statements import router as bank_statements_router
from app.api.v1.categories import router as categories_router
from app.api.v1.financial_insights import router as financial_insights_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.risk import router as risk_router
from app.schemas.health import HealthResponse

app = FastAPI(
    title="Capitec Financial Insights API",
    version="0.1.0",
    description=(
        "FastAPI backend for MinIO PDF statement uploads, metadata-only "
        "PostgreSQL storage, local S3-style transaction files, Redis-backed "
        "insight caching, and rule-based financial insights."
    ),
    contact={"name": "Capitec Financial Insights API Submission"},
    openapi_tags=[
        {
            "name": "health",
            "description": "Service health and readiness checks.",
        },
        {
            "name": "bank statements",
            "description": (
                "MinIO-backed PDF statement uploads and statement metadata creation."
            ),
        },
        {
            "name": "categories",
            "description": "Keyword-based transaction categorisation.",
        },
        {
            "name": "aggregation",
            "description": (
                "Income, expense, cashflow, category, and monthly summaries."
            ),
        },
        {
            "name": "risk",
            "description": "Explainable lending risk scoring.",
        },
        {
            "name": "recommendations",
            "description": "Rule-based financial recommendations and priority actions.",
        },
        {
            "name": "financial insights",
            "description": (
                "Combined user, statement, aggregation, risk, and recommendation view."
            ),
        },
    ],
)

app.include_router(aggregation_router)
app.include_router(bank_statements_router)
app.include_router(categories_router)
app.include_router(financial_insights_router)
app.include_router(recommendations_router)
app.include_router(risk_router)


@app.get(
    "/health",
    tags=["health"],
    response_model=HealthResponse,
    summary="Check API health",
    description="Returns a lightweight health response for the API service.",
)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
