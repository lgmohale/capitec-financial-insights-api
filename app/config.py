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


@lru_cache
def get_settings() -> Settings:
    return Settings()
