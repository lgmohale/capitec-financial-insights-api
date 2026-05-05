from functools import lru_cache
from os import getenv


class Settings:
    app_name: str = getenv("APP_NAME", "capitec-financial-insights-api")
    app_env: str = getenv("APP_ENV", "development")
    database_url: str = getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/financial_insights",
    )
    redis_url: str = getenv("REDIS_URL", "redis://localhost:6379/0")
    minio_endpoint: str = getenv("MINIO_ENDPOINT", "localhost")
    minio_port: str = getenv("MINIO_PORT", "9000")
    minio_access_key: str = getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = getenv("MINIO_BUCKET", "bank-statements")
    minio_use_ssl: bool = getenv("MINIO_USE_SSL", "false").lower() == "true"

    @property
    def minio_server(self) -> str:
        return f"{self.minio_endpoint}:{self.minio_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
