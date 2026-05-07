from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.api.v1.aggregation import router as aggregation_router
from app.api.v1.bank_statements import router as bank_statements_router
from app.api.v1.categories import router as categories_router
from app.api.v1.risk import router as risk_router
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.schemas.health import HealthResponse

configure_logging()

app = FastAPI(
    title="Capitec Financial Insights API",
    version="0.1.0",
    description=(
        "FastAPI backend for bank statement upload simulation, metadata-only "
        "PostgreSQL storage, MinIO-backed transaction JSON, Redis-backed "
        "processing caches, and rule-based transaction insights."
    ),
    contact={"name": "Capitec Financial Insights API Submission"},
    openapi_tags=[
        {
            "name": "health",
            "description": "Service health and readiness checks.",
        },
        {
            "name": "bank statements",
            "description": "Bank statement upload simulation and metadata creation.",
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
    ],
)

app.add_middleware(RequestContextMiddleware)

app.include_router(aggregation_router)
app.include_router(bank_statements_router)
app.include_router(categories_router)
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


@app.get(
    "/metrics",
    tags=["health"],
    summary="Expose Prometheus metrics",
    description="Returns Prometheus metrics for API requests and processing events.",
)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
