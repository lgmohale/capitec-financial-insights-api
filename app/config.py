from functools import lru_cache
from os import getenv

LOCAL_ENV = "local"
STAGING_ENV = "staging"
PRODUCTION_ENV = "production"
VALID_ENVIRONMENTS = {LOCAL_ENV, STAGING_ENV, PRODUCTION_ENV}

LOCAL_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/financial_insights"
)
LOCAL_REDIS_URL = "redis://localhost:6379/0"
LOCAL_MINIO_ENDPOINTS = {"localhost", "minio"}


class Settings:
    def __init__(self) -> None:
        self.app_name = getenv("APP_NAME", "capitec-financial-insights-api")
        self.app_env = getenv("APP_ENV", LOCAL_ENV)
        self.database_url = getenv("DATABASE_URL", LOCAL_DATABASE_URL)
        self.redis_url = getenv("REDIS_URL", LOCAL_REDIS_URL)
        self.minio_endpoint = getenv("MINIO_ENDPOINT", "localhost")
        self.minio_port = getenv("MINIO_PORT", "9000")
        self.minio_access_key = getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = getenv("MINIO_SECRET_KEY", "minioadmin")
        self.minio_bucket = getenv("MINIO_BUCKET", "bank-statements")
        self.minio_use_ssl = getenv("MINIO_USE_SSL", "false").lower() == "true"
        self.validate_environment()

    @property
    def minio_server(self) -> str:
        return f"{self.minio_endpoint}:{self.minio_port}"

    @property
    def is_local(self) -> bool:
        return self.app_env == LOCAL_ENV

    def validate_environment(self) -> None:
        if self.app_env not in VALID_ENVIRONMENTS:
            valid_values = ", ".join(sorted(VALID_ENVIRONMENTS))
            raise ValueError(f"APP_ENV must be one of: {valid_values}.")

        if self.is_local:
            return

        local_config_errors = []
        if (
            self.database_url == LOCAL_DATABASE_URL
            or "@localhost:" in self.database_url
        ):
            local_config_errors.append("DATABASE_URL must point to managed PostgreSQL")
        if self.redis_url == LOCAL_REDIS_URL or "localhost:" in self.redis_url:
            local_config_errors.append("REDIS_URL must point to managed cache")
        if self.minio_endpoint in LOCAL_MINIO_ENDPOINTS:
            local_config_errors.append(
                "MINIO_ENDPOINT must point to managed object storage"
            )
        if (
            self.minio_access_key == "minioadmin"
            or self.minio_secret_key == "minioadmin"
        ):
            local_config_errors.append("MinIO credentials must not use local defaults")

        if local_config_errors:
            details = "; ".join(local_config_errors)
            raise ValueError(f"{self.app_env} configuration is invalid: {details}.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
