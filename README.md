# Capitec Financial Insights API

FastAPI backend for a transaction aggregation and financial insights system. The API accepts PDF bank statement uploads, stores PDFs and generated JSON outputs in MinIO, stores only metadata in PostgreSQL, and produces cached financial insights using rule-based processing.

## Project Overview

This project combines two assessment ideas:

1. Transaction Aggregation API as the main assessment brief.
2. Secure File Statement Delivery concepts through PDF upload, MinIO storage, and secure statement handling.

The system supports a simple financial insights workflow:

1. Upload a PDF bank statement for a user.
2. Store the PDF in MinIO.
3. Simulate OCR by generating transactions from the uploaded statement.
4. Store the generated transaction JSON in MinIO.
5. Store only user and bank statement metadata in PostgreSQL.
6. Categorise transactions.
7. Aggregate income, expenses, cashflow, category, and monthly summaries.
8. Score lending risk using explainable rules.
9. Generate financial recommendations.
10. Return a combined financial insights response.

## Architecture

- FastAPI API service
- PostgreSQL for metadata only
- Redis to simulate AWS ElastiCache
- MinIO to simulate S3-style object storage for statement PDFs and generated JSON outputs
- Environment-specific configuration for `local`, `staging`, and `production`
- Docker Compose for local API, PostgreSQL, Redis, and MinIO services only
- Prometheus for local API metrics scraping
- Alembic for database migrations
- Pytest, Ruff, pre-commit, and GitHub Actions for quality checks

## Prerequisites

- Docker and Docker Compose

## Environment Variables

The API uses `APP_ENV` to select environment behaviour. Supported values are:

- `local`
- `staging`
- `production`

Docker Compose is intended for local development only and provides local PostgreSQL, Redis, and MinIO services. Staging and production should use managed PostgreSQL, managed cache, and managed object storage by setting explicit environment variables.

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

Example files are included for each environment:

- `.env.local.example`
- `.env.staging.example`
- `.env.production.example`

For `staging` and `production`, the app fails fast if local Docker Compose defaults such as `localhost`, `minio`, or `minioadmin` credentials are used.

## MinIO Object Storage

MinIO simulates S3-compatible storage for uploaded PDF bank statements, generated transaction JSON, and processed insight outputs. Docker Compose starts MinIO with:

- API endpoint: `http://localhost:9000`
- Console URL: `http://localhost:9001`
- Default access key: `minioadmin`
- Default secret key: `minioadmin`
- Default bucket: `bank-statements`

The API checks for the configured bucket before upload and creates it when needed. Files are stored in the configured bucket using object keys.

Object key examples:

```text
input/{user_id}/{statement_id}.pdf
output/{statement_id}/transactions.json
output/{statement_id}/categories.json
output/{statement_id}/aggregation.json
output/{statement_id}/risk.json
output/{statement_id}/recommendations.json
```

Uploaded PDFs and generated JSON files are not written to project folders.

## Storage Design

Raw transactions are intentionally stored as JSON objects in MinIO instead of PostgreSQL rows. This keeps the database focused on relational metadata while allowing transaction payloads to remain object based, similar to storing bank extracts in S3.

This design is useful because transaction payloads can be large, schema-flexible, and better suited to object storage. PostgreSQL stores only the metadata required to locate and relate the file.

## PostgreSQL Metadata-Only Design

PostgreSQL does not store full transactions. It stores only users and uploaded bank statement metadata.

### Tables

`users`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `name` | string | User name |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

`bank_statement`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key, uploaded statement and transaction file ID |
| `user_id` | UUID | Foreign key to `users.id` |
| `bank_name` | string | Uploaded bank statement name or bank name |
| `file_url` | string | MinIO object key for the uploaded PDF |
| `created_at` | datetime | Creation timestamp |

## Redis Caching

Redis simulates AWS ElastiCache. Processed results are cached as JSON for 3600 seconds by default.

Cache keys:

- `categorisation:{account_id}`
- `aggregation:{account_id}`
- `risk:{account_id}`
- `recommendations:{account_id}`

Each processing endpoint supports `force_refresh=false`. Set `force_refresh=true` to bypass Redis and rebuild the result.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/bank-statements/upload` | Upload a PDF statement to MinIO and simulate OCR processing |
| `GET` | `/api/v1/accounts/{account_id}/categories` | Categorise transactions |
| `GET` | `/api/v1/accounts/{account_id}/aggregation` | Aggregate transaction metrics |
| `GET` | `/api/v1/accounts/{account_id}/risk` | Generate lending risk score |
| `GET` | `/api/v1/accounts/{account_id}/recommendations` | Generate financial recommendations |
| `GET` | `/api/v1/accounts/{account_id}/financial-insights` | Return combined insights |

The categories endpoint returns one summary item per category with:

- `category`
- `total_amount`
- `transaction_count`

The aggregation endpoint returns rounded monetary values and includes:

- top-level totals, average monthly values, savings rate, transaction count, and month count
- category income, expenses, net amount, and income or expense percentages
- monthly income, expenses, net cashflow, transaction count, and savings rate
- simple risk flags and deterministic human-readable insights

## Example Request and Response

Upload a PDF bank statement:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/bank-statements/upload \
  -F "user_names=Lucas George" \
  -F "bank_name=FNB Statement April 2026" \
  -F "file=@statement.pdf;type=application/pdf"
```

Example response:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "650e8400-e29b-41d4-a716-446655440000",
  "bank_name": "FNB Statement April 2026",
  "file_url": "input/650e8400-e29b-41d4-a716-446655440000/550e8400-e29b-41d4-a716-446655440000.pdf",
  "bank_statement_pdf_download_url": "http://localhost:8000/api/v1/bank-statements/550e8400-e29b-41d4-a716-446655440000/download",
  "message": "Bank statement uploaded successfully and queued for processing."
}
```

The PDF is stored in MinIO, OCR processing is simulated, and the API creates statement metadata plus generated transaction JSON in MinIO. Internal local file paths are not exposed in the API response.
The `bank_statement_pdf_download_url` field points to an API download route that streams the uploaded PDF from MinIO.

The upload flow is:

1. Store the PDF in MinIO.
2. Create user metadata.
3. Reuse the transaction generation logic to simulate extracted transactions.
4. Create the `bank_statement` metadata row with the MinIO object key.

Get combined financial insights:

```bash
curl http://127.0.0.1:8000/api/v1/accounts/{account_id}/financial-insights
```

Response includes:

- `account_id`
- `user`
- `bank_statement`
- `aggregation`
- `risk`
- `recommendations`
- `generated_at`

Get aggregation metrics:

```bash
curl http://127.0.0.1:8000/api/v1/accounts/{account_id}/aggregation
```

Example aggregation fields:

```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "cached": false,
  "total_income": 170528.22,
  "total_expenses": 97019.68,
  "net_cashflow": 73508.54,
  "transaction_count": 102,
  "month_count": 4,
  "average_monthly_income": 42632.05,
  "average_monthly_expenses": 24254.92,
  "average_monthly_net_cashflow": 18377.13,
  "savings_rate": 43.11,
  "category_breakdown": {
    "salary": {
      "transaction_count": 4,
      "income": 154318.96,
      "expenses": 0.0,
      "net_amount": 154318.96,
      "income_percentage": 90.5
    },
    "rent_or_home_loan": {
      "transaction_count": 3,
      "income": 0.0,
      "expenses": 39450.0,
      "net_amount": -39450.0,
      "expense_percentage": 40.66
    }
  },
  "monthly_summary": {
    "2026-01": {
      "total_income": 35796.55,
      "total_expenses": 22435.96,
      "net_cashflow": 13360.59,
      "transaction_count": 13,
      "savings_rate": 37.32
    }
  },
  "risk_flags": {
    "salary_detected": true,
    "has_gambling_spend": true,
    "has_negative_cashflow_month": false,
    "has_unknown_income": true
  },
  "insights": [
    "Salary income appears consistent across the analysed period.",
    "Rent or home loan is the largest expense category.",
    "Net cashflow remained positive across all analysed months.",
    "Gambling spend was detected in the analysed period.",
    "Some income transactions could not be categorised and may require review."
  ],
  "bank_statement_pdf_download_url": "http://localhost:8000/api/v1/bank-statements/550e8400-e29b-41d4-a716-446655440000/download"
}
```

## Run With Docker

Build and start the API, PostgreSQL, Redis, and MinIO:

```bash
docker compose up --build -d
```

The API container waits for PostgreSQL and runs `alembic upgrade head` automatically on startup, so the database tables are created when the stack starts.

Check the API health endpoint:

```bash
curl http://localhost:8000/health
```

Open the API docs:

```text
http://localhost:8000/docs
```

Swagger UI is available at `http://localhost:8000/docs`. It includes route tags, summaries, descriptions, request models, response models, and examples. Reviewers can test all endpoints directly from Swagger UI without reading the code first.

Open the MinIO console:

```text
http://localhost:9001
```

Use `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` from `.env.example`. The default bucket is `bank-statements` and is created by the API when the first PDF or JSON output is uploaded.

Open Prometheus:

```text
http://localhost:9090
```

Prometheus scrapes the API `/metrics` endpoint using `observability/prometheus.yml`.

Stop the stack:

```bash
docker compose down
```

Open PostgreSQL from the terminal:

```bash
docker compose exec postgres psql -U postgres -d financial_insights
```

## Observability

The local Docker Compose stack includes Prometheus only. Grafana is intentionally out of scope for this assessment.

Available observability features:

- `GET /metrics` exposes Prometheus metrics.
- Prometheus UI is available at `http://localhost:9090`.
- API responses include `X-Request-ID`.
- Incoming `X-Request-ID` headers are reused; otherwise the API generates a UUID request ID.
- Application logs are structured JSON and include request correlation fields where available.

Metrics include:

- `api_requests_total`
- `api_request_duration_seconds`
- `bank_statement_uploads_total`
- `bank_statement_upload_failures_total`
- `minio_uploads_total`
- `minio_upload_failures_total`
- `transaction_generation_completed_total`
- `transaction_generation_failures_total`
- `aggregation_completed_total`
- `aggregation_failures_total`
- `cache_hits_total`
- `cache_misses_total`
- `processing_failures_total`

Structured logs are emitted for request start/completion, PDF uploads, MinIO uploads, simulated processing, transaction generation, aggregation, cache hit/miss events, and safe error handling. Logs do not include raw file contents, MinIO credentials, database URLs, tokens, or secrets.

Troubleshooting:

- Check that Docker Desktop is running.
- Check that ports `8000`, `5432`, `6379`, `9000`, and `9001` are available.
- Check API logs with `docker compose logs api` if migrations fail during startup.

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

Quality checks inside Docker:

```bash
docker compose exec api ruff check .
docker compose exec api ruff format --check .
```

The API flow tests use a test database plus fake object storage and cache hooks. They do not depend on existing local JSON files, MinIO, or a running Redis service.

## Git Hooks

Install pre-commit hooks on the host machine:

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

The pre-push hook starts the required Docker services, runs migrations, and runs:

```bash
docker compose run --rm api pytest tests/unit tests/integration -q
```

If tests fail, `git push` is blocked. Keep Docker running before pushing.

## Branching Workflow

GitHub Actions runs on pushes and pull requests for `dev`, `staging`, and `main`.

Expected branch flow:

- Feature branches merge into `dev`.
- `dev` merges into `staging`.
- `staging` merges into `main`.

The CI branch-flow validation fails pull requests when:

- The target branch is `main` and the source branch is not `staging`.
- The target branch is `staging` and the source branch is not `dev`.
- `main` is being merged into `dev`.

After branch-flow validation passes, CI runs separate jobs:

```bash
ruff check .
ruff format --check .
pytest tests/unit -q --cov=app --cov-report=term-missing --cov-report=xml
docker compose config
docker build -t transaction-aggregation-api:test .
docker compose run --rm api pytest tests/integration -q
pip-audit -r requirements.txt --cache-dir .cache/pip-audit
```

## CI/CD

CI runs on pull requests and pushes to `dev`, `staging`, and `main`. It validates the branch flow and runs practical quality checks:

- Branch flow validation.
- Ruff lint and format checks.
- Unit tests with coverage reporting.
- Docker Compose configuration validation.
- `.env.example` required-variable validation.
- Docker image build validation.
- Docker-backed integration tests with PostgreSQL, Redis, and MinIO.
- Advisory dependency security scanning with `pip-audit`.
- SonarCloud static analysis using the Python coverage XML report.

The expected branch flow is:

```text
feature branch -> dev -> staging -> main
```

CD runs on pushes to `staging` and `main`.

- `staging` builds and validates `transaction-aggregation-api:staging`.
- `main` builds and validates `transaction-aggregation-api:latest` and `transaction-aggregation-api:production`.

The CD workflow validates the Docker image and runs unit tests inside the built container. Actual cloud deployment is intentionally out of scope for this assessment.

Docker Compose remains local-only. Staging and production image builds are validated in CI/CD, but a real deployment would inject managed service configuration through the target runtime.

## SonarCloud Analysis

SonarCloud static analysis is configured with `sonar-project.properties` for the Python API code in `app` and tests in `tests`. The scan excludes local virtual environments, migration files, local data folders, and Python cache folders.

To enable analysis in GitHub Actions:

1. Create or connect the project in SonarCloud.
2. Add a repository secret named `SONAR_TOKEN` in GitHub under `Settings > Secrets and variables > Actions`.
3. Use a token generated from SonarCloud with permission to analyse the project.

CI generates `coverage.xml` from pytest, uploads it as an artifact, then runs the SonarCloud scan automatically after linting, formatting, unit tests, and integration tests pass. Reports are available in the SonarCloud dashboard for the `lgmohale/capitec-financial-insights-api` project.

## Assumptions

- PDF statement upload stores the original file in MinIO and simulates OCR; no real PDF parsing is performed.
- Statement transaction histories are randomly generated and include more than 3 months of data, salary, deposits, withdrawals, and at least 7 transactions per week.
- Categorisation, risk scoring, and recommendations are rule-based.
- MinIO simulates S3 storage for uploaded PDF bank statements and generated JSON outputs.
- Redis is used only for processed insight caching.
- PostgreSQL stores metadata only, never full transaction payloads.

## Possible Improvements

This project focuses on the assessment requirements: transaction aggregation, categorisation, financial summaries, and secure statement file handling using MinIO as S3-compatible storage.

Given more time, the following improvements could be added:

- Add authentication so users can only access their own statements and summaries.
- Add time-limited pre-signed download links for uploaded PDF statements.
- Improve transaction categorisation with configurable rules instead of hardcoded categories.
- Add duplicate statement detection to avoid processing the same file more than once.
- Move statement processing to a background job for larger files.
- Add more detailed API filtering, for example by date range, category, or transaction type.
- Add more test coverage for edge cases such as empty statements, invalid files, and zero-income months.
- Add basic monitoring and structured logs for easier debugging.
