from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API requests.",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds",
    "API request latency in seconds.",
    ["method", "path"],
)

BANK_STATEMENT_UPLOADS = Counter(
    "bank_statement_uploads_total",
    "Successful bank statement uploads.",
    ["event"],
)

BANK_STATEMENT_UPLOAD_FAILURES = Counter(
    "bank_statement_upload_failures_total",
    "Failed bank statement uploads.",
    ["event"],
)

MINIO_UPLOADS = Counter(
    "minio_uploads_total",
    "Completed MinIO uploads.",
    ["event"],
)

MINIO_UPLOAD_FAILURES = Counter(
    "minio_upload_failures_total",
    "Failed MinIO uploads.",
    ["event"],
)

TRANSACTION_GENERATION_COMPLETED = Counter(
    "transaction_generation_completed_total",
    "Completed transaction generation events.",
    ["event"],
)

TRANSACTION_GENERATION_FAILURES = Counter(
    "transaction_generation_failures_total",
    "Failed transaction generation events.",
    ["event"],
)

AGGREGATION_COMPLETED = Counter(
    "aggregation_completed_total",
    "Completed aggregation events.",
    ["event"],
)

AGGREGATION_FAILURES = Counter(
    "aggregation_failures_total",
    "Failed aggregation events.",
    ["event"],
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Cache hit events.",
    ["event"],
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Cache miss events.",
    ["event"],
)

PROCESSING_FAILURES = Counter(
    "processing_failures_total",
    "Processing failure events.",
    ["event"],
)
