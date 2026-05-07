# Capitec Transaction Aggregation API

FastAPI backend for a transaction aggregation system. The API uploads PDF bank statements to MinIO, generates sample transaction data, stores metadata in PostgreSQL, and provides categorisation, aggregation, and simple rule-based risk analysis.

## Project Overview

This project demonstrates a simplified transaction-processing workflow:

1. Upload a PDF bank statement to MinIO.
2. Generate sample transaction data for the uploaded statement.
3. Store uploaded files and generated transaction JSON in MinIO.
4. Store only statement metadata in PostgreSQL.
5. Categorise transactions using keyword rules.
6. Aggregate income, expenses, and monthly summaries.
7. Generate a simple rule-based lending-risk score.
8. Download uploaded statements through the API.

## Architecture

- FastAPI API service
- PostgreSQL for metadata storage
- MinIO for object storage
- Redis for caching
- Docker Compose for local development
- Alembic for database migrations

## Prerequisites

- Docker
- Docker Compose

## Environment Variables

Create a `.env` file using `.env.example`.

Example local configuration:

```env
APP_NAME=capitec-transaction-aggregation-api
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

PostgreSQL stores metadata only. Raw transaction data and processed outputs are stored in MinIO.

Example object structure:

```text
input/{statement_id}/statement.pdf
input/{statement_id}/transactions.json
output/{statement_id}/categories.json
output/{statement_id}/aggregation.json
output/{statement_id}/risk.json
```

## Database Design

### `bank_statements`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `bank_name` | string | Bank or statement name |
| `object_key` | string | MinIO object path for uploaded PDF |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

## Redis Caching

Redis caches processed results for 3600 seconds by default.

Cache keys:

```text
categorisation:{statement_id}
aggregation:{statement_id}
risk:{statement_id}
```

Each processing endpoint supports:

```text
force_refresh=false
```

Set `force_refresh=true` to bypass cache and rebuild results.

---

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/bank-statement/upload` | Upload PDF statement |
| `GET` | `/api/v1/bank-statement/{statement_id}/download` | Download uploaded PDF |
| `GET` | `/api/v1/accounts/{statement_id}/categories` | Categorise transactions |
| `GET` | `/api/v1/accounts/{statement_id}/aggregation` | Aggregate transaction metrics |
| `GET` | `/api/v1/accounts/{statement_id}/risk` | Generate risk analysis |

## Swagger Documentation

Swagger UI is available at:

```text
http://localhost:8000/docs
```

Reviewers can test all endpoints directly from Swagger UI.

## Example Request and Response

### Upload a bank statement

```bash
curl -X POST http://127.0.0.1:8000/api/v1/bank-statement/upload \
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
  "message": "Statement uploaded successfully."
}
```

### Get aggregation summary

```bash
curl http://127.0.0.1:8000/api/v1/accounts/{statement_id}/aggregation
```

Example response:

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

| Service | URL |
| --- | --- |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| Prometheus | http://localhost:9090 |

Default MinIO credentials:

```text
minioadmin / minioadmin
```

Open PostgreSQL terminal:

```bash
docker compose exec postgres psql -U postgres -d financial_insights
```

Stop services:

```bash
docker compose down -v
```

## Run Locally Without Docker

Create virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy environment file:

```bash
cp .env.example .env
```

Run migrations:

```bash
alembic upgrade head
```

Start API:

```bash
uvicorn app.main:app --reload
```

PostgreSQL, Redis, and MinIO must already be running locally.

## Observability

Prometheus metrics are exposed through:

```text
/metrics
```

The API also includes:

- request logging
- request IDs
- cache hit/miss metrics
- aggregation and processing metrics

## Run Tests

Run unit tests:

```bash
pytest tests/unit -q --cov=app --cov-report=term-missing --cov-report=xml
```

Run integration tests:

```bash
docker compose up -d --wait postgres redis minio

docker compose run --rm api alembic upgrade head

docker compose run --rm api pytest tests/integration -q

docker compose down -v
```

---

## Code Quality

Run linting:

```bash
ruff check .
```

Run format checks:

```bash
ruff format --check .
```

Install pre-commit hooks:

```bash
pre-commit install
```

## CI

GitHub Actions runs:

- Ruff linting
- Ruff format checks
- Unit tests
- Integration tests
- SonarCloud static analysis

Branch flow used during development:

```text
feature -> dev -> staging -> main
```

## SonarCloud Analysis

SonarCloud uses:

- pytest coverage reports
- static analysis checks
- maintainability checks

Coverage is generated during CI using:

```text
coverage.xml
```

## Assumptions

- Uploaded PDFs are stored in MinIO.
- Transaction histories are generated sample data.
- Categorisation and risk analysis are rule-based.
- MinIO simulates S3-compatible object storage.
- Redis is used for caching processed results.
- PostgreSQL stores metadata only.
