# Capitec Transaction Aggregation API

FastAPI backend for a transaction aggregation and lending-risk assessment system. The API uploads PDF bank statements to MinIO, simulates OCR processing and transaction extraction, stores generated transaction JSON and processed outputs in MinIO, stores only uploaded statement metadata in PostgreSQL, and caches processing results in Redis.

## Project Overview

This project covers the core flow of taking a bank statement, simulating extracted transaction data, categorising it, and producing useful financial summaries and risk signals.

The main flow is:

1. Upload a PDF bank statement to MinIO.
2. Simulate OCR processing by generating a random transaction history for that uploaded statement.
3. Store the uploaded PDF and generated raw transactions in MinIO object storage.
4. Store only uploaded statement metadata in PostgreSQL.
5. Categorise transactions with rule-based keyword matching.
6. Aggregate income, expenses, cashflow, category, and monthly summaries.
7. Score lending risk using explainable rules.
8. Download the uploaded PDF bank statement from MinIO through the API.

## Architecture

- FastAPI API service
- PostgreSQL for metadata only
- MinIO as S3-compatible object storage
- Redis for processing-result caching
- Docker Compose for local API, PostgreSQL, Redis, MinIO, and Prometheus services
- Alembic for database migrations
- Pytest, Ruff, SonarCloud, pre-commit, and GitHub Actions for quality checks

## Prerequisites

- Docker and Docker Compose

## Environment Variables

Docker Compose is intended for local development. Staging and production should use managed PostgreSQL, object storage, and cache services by setting environment-specific values.

Example local configuration:

```env
APP_NAME=capitec-financial-insights-api
APP_ENV=local
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/financial_insights
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio
MINIO_PORT=9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=bank-statements
MINIO_USE_SSL=false
```

## Storage Design

PostgreSQL stores metadata only. It does not store raw transactions or processed outputs.

MinIO stores object data:

```text
input/{statement_id}/statement.pdf
input/{statement_id}/transactions.json
output/{statement_id}/categories.json
output/{statement_id}/aggregation.json
output/{statement_id}/risk.json
```

No local `data/input` or `data/output` folder is used.

## Database Table

`bank_statements`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `bank_name` | string | Bank or statement name |
| `object_key` | string | MinIO key for the uploaded PDF statement |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

## Redis Caching

Redis caches processed results as JSON for 3600 seconds by default.

Cache keys:

- `categorisation:{statement_id}`
- `aggregation:{statement_id}`
- `risk:{statement_id}`

Each processing endpoint supports `force_refresh=false`. Set `force_refresh=true` to bypass Redis and rebuild the result from MinIO data.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/bank-statement/uplaod` | Upload a PDF statement to MinIO and simulate OCR processing |
| `GET` | `/api/v1/bank-statement/{statement_id}/download` | Download uploaded PDF bank statement |
| `GET` | `/api/v1/accounts/{statement_id}/categories` | Categorise transactions |
| `GET` | `/api/v1/accounts/{statement_id}/aggregation` | Aggregate transaction metrics |
| `GET` | `/api/v1/accounts/{statement_id}/risk` | Generate lending risk score |

Swagger UI is available at:

```text
http://localhost:8000/docs
```

Reviewers can test all endpoints directly from Swagger UI.

## Example Request and Response

Upload a bank statement:

```bash
curl -X POST http://localhost:8000/api/v1/bank-statement/uplaod \
  -F "bank_name=Capitec" \
  -F "file=@statement.pdf;type=application/pdf"
```

Example response:

```json
{
  "uploaded_statement": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "bank_name": "Capitec",
    "object_key": "input/550e8400-e29b-41d4-a716-446655440000/statement.pdf",
    "created_at": "2026-05-05T10:00:00Z",
    "updated_at": "2026-05-05T10:00:00Z"
  },
  "download_url": "http://localhost:8000/api/v1/bank-statement/550e8400-e29b-41d4-a716-446655440000/download",
  "message": "Bank statement uploaded successfully and processed with simulated OCR."
}
```

Download uploaded PDF statement:

```bash
curl http://localhost:8000/api/v1/bank-statement/{statement_id}/download
```

Get aggregation:

```bash
curl http://localhost:8000/api/v1/accounts/{statement_id}/aggregation
```

Example aggregation fields:

```json
{
  "statement_id": "550e8400-e29b-41d4-a716-446655440000",
  "cached": false,
  "total_income": 170528.22,
  "total_expenses": 97019.68,
  "net_cashflow": 73508.54,
  "transaction_count": 102,
  "month_count": 4,
  "average_monthly_income": 42632.05,
  "average_monthly_expenses": 24254.92,
  "average_monthly_net_cashflow": 18377.13,
  "savings_rate": 43.11
}
```

## Run With Docker

Start the API, PostgreSQL, Redis, MinIO, and Prometheus:

```bash
docker compose up --build -d
```

The API startup script runs Alembic migrations automatically.

Useful URLs:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001`
- Prometheus: `http://localhost:9090`

Default MinIO credentials:

```text
minioadmin / minioadmin
```

Open PostgreSQL from the terminal:

```bash
docker compose exec postgres psql -U postgres -d financial_insights
```

Stop services:

```bash
docker compose down -v
```

## Observability

Prometheus scrapes API metrics from `/metrics`.

Metrics include:

- `api_requests_total`
- `api_request_duration_seconds`
- `minio_uploads_total`
- `minio_upload_failures_total`
- `transaction_generation_completed_total`
- `transaction_generation_failures_total`
- `aggregation_completed_total`
- `aggregation_failures_total`
- `cache_hits_total`
- `cache_misses_total`

API logs are structured JSON and include request IDs for correlation. API responses include `X-Request-ID`.

## Run Tests

Run unit tests locally or inside Docker:

```bash
pytest tests/unit -q --cov=app --cov-report=term-missing --cov-report=xml
docker compose exec api pytest tests/unit -q --cov=app --cov-report=term-missing --cov-report=xml
```

Run integration tests with Docker Compose services:

```bash
docker compose up -d --wait postgres redis minio
docker compose run --rm api alembic upgrade head
docker compose run --rm api pytest tests/integration -q
docker compose down -v
```

Quality checks:

```bash
ruff check .
ruff format --check .
```

## CI/CD

CI runs on pull requests and pushes to `dev`, `staging`, and `main`.

It includes branch flow validation, Ruff lint and format checks, unit tests with coverage XML, Docker Compose validation, Docker image build validation, Docker-backed integration tests, advisory dependency security scanning, and SonarCloud static analysis.

Expected branch flow:

```text
feature branch -> dev -> staging -> main
```

CD runs on pushes to `staging` and `main` and validates Docker image builds.

## SonarCloud Analysis

SonarCloud static analysis is configured with `sonar-project.properties`.

CI generates `coverage.xml` from pytest and uses it in the SonarCloud scan.

## Assumptions

- Bank statement upload stores the PDF in MinIO and simulates OCR processing rather than extracting text from the PDF.
- Transaction histories are randomly generated and include more than 3 months of data, salary, deposits, withdrawals, and at least 7 transactions per week.
- Categorisation and risk scoring are rule-based.
- MinIO simulates S3-compatible object storage.
- Redis is used only for processed result caching.
- PostgreSQL stores metadata only.
