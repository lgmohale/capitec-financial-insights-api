# Capitec Financial Insights API

FastAPI backend for a transaction aggregation and financial insights system. The API simulates linking a user's bank account, stores raw transaction data as JSON files, stores only account metadata in PostgreSQL, and produces cached financial insights using rule-based processing.

## Project Overview

The system supports a simple financial insights workflow:

1. Link a simulated bank account for a user.
2. Store the raw transaction payload in local S3-style storage.
3. Store only user and linked account metadata in PostgreSQL.
4. Categorise transactions.
5. Aggregate income, expenses, cashflow, category, and monthly summaries.
6. Score lending risk using explainable rules.
7. Generate financial recommendations.
8. Return a combined financial insights response.

## Architecture

- FastAPI API service
- PostgreSQL for metadata only
- Redis to simulate AWS ElastiCache
- `data/input` as a local S3 input bucket simulation
- `data/output` as a local S3 output bucket simulation
- Docker Compose for local API, PostgreSQL, and Redis services
- Alembic for database migrations
- Pytest, Ruff, pre-commit, and GitHub Actions for quality checks

## Prerequisites

- Docker and Docker Compose

## Environment Variables

Docker Compose provides the required service connection values for the API container. A `.env` file can still be created from `.env.example` for local configuration overrides, but no local PostgreSQL or Redis setup is required when using Docker.

Example:

```env
APP_NAME=capitec-financial-insights-api
APP_ENV=development
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/financial_insights
REDIS_URL=redis://redis:6379/0
```

## Storage Design

Raw transactions are intentionally stored as JSON files instead of PostgreSQL rows. This keeps the database focused on relational metadata while allowing transaction payloads to remain file/object based, similar to storing bank extracts in S3.

This design is useful because transaction payloads can be large, schema-flexible, and better suited to object storage. PostgreSQL stores only the metadata required to locate and relate the file.

## Local S3 Folders

- `data/input`: stores raw transaction files using `{linked_account_id}.json`
- `data/output`: stores processed outputs, such as categorisation, aggregation, risk, and recommendation results

Example input file:

```text
data/input/550e8400-e29b-41d4-a716-446655440000.json
```

Example output files:

```text
data/output/{account_id}_categories.json
data/output/{account_id}_aggregation.json
data/output/{account_id}_risk.json
data/output/{account_id}_recommendations.json
```

## PostgreSQL Metadata-Only Design

PostgreSQL does not store full transactions. It stores only users and linked account metadata.

### Tables

`users`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `name` | string | User name |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

`linked_account`

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | UUID | Primary key, foreign key to `users.id` |
| `id` | UUID | Transaction file ID |
| `bank_name` | string | Linked bank name |
| `created_at` | datetime | Creation timestamp |

The linked account `id` is also the JSON file name in `data/input`.

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
| `POST` | `/api/v1/bank-accounts/link` | Simulate linking a bank account |
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

Link a bank account:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/bank-accounts/link \
  -H "Content-Type: application/json" \
  -d '{"name":"Lucas George","bank_name":"Capitec"}'
```

Example response:

```json
{
  "user": {
    "id": "650e8400-e29b-41d4-a716-446655440000",
    "name": "Lucas George",
    "created_at": "2026-05-05T10:00:00Z",
    "updated_at": "2026-05-05T10:00:00Z"
  },
  "linked_account": {
    "user_id": "650e8400-e29b-41d4-a716-446655440000",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "bank_name": "Capitec",
    "created_at": "2026-05-05T10:00:00Z"
  }
}
```

Get combined financial insights:

```bash
curl http://127.0.0.1:8000/api/v1/accounts/{account_id}/financial-insights
```

Response includes:

- `account_id`
- `user`
- `linked_account`
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
  "output_file_path": "data/output/550e8400-e29b-41d4-a716-446655440000_aggregation.json"
}
```

## Run With Docker

Build and start the API, PostgreSQL, and Redis:

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

Stop the stack:

```bash
docker compose down
```

Open PostgreSQL from the terminal:

```bash
docker compose exec postgres psql -U postgres -d financial_insights
```

Troubleshooting:

- Check that Docker Desktop is running.
- Check that ports `8000`, `5432`, and `6379` are available.
- Check API logs with `docker compose logs api` if migrations fail during startup.

## Run Tests

```bash
docker compose exec api pytest
```

Quality checks:

```bash
docker compose exec api ruff check .
docker compose exec api ruff format --check .
```

The API flow tests use temporary data folders, a test database, and fake cache hooks. They do not depend on existing local JSON files or a running Redis service.

## Git Hooks

Install pre-commit hooks on the host machine:

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

The pre-push hook runs:

```bash
docker compose run --rm api pytest
```

If tests fail, `git push` is blocked. Keep Docker running before pushing.

## Assumptions

- Bank linking is simulated and does not call a real banking API.
- Linked account transaction histories are randomly generated and include more than 3 months of data, salary, deposits, withdrawals, and at least 7 transactions per week.
- Categorisation, risk scoring, and recommendations are rule-based.
- Local `data/input` and `data/output` folders simulate S3 buckets.
- Redis is used only for processed insight caching.
- PostgreSQL stores metadata only, never full transaction payloads.

## Production Improvements

- Replace local folders with S3 buckets and object lifecycle policies.
- Add authentication, authorization, and tenant isolation.
- Add request validation for duplicate linked accounts and idempotency.
- Add database constraints and indexes for lookup patterns.
- Use managed PostgreSQL and ElastiCache.
- Add structured logging, tracing, metrics, and alerting.
- Move long-running processing to background jobs or event-driven workers.
- Encrypt sensitive data at rest and in transit.
- Add CI database migration checks and contract tests.
- Replace simple rules with versioned models or configurable rule engines.
