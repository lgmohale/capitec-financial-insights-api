import pytest

from app.config import Settings


def test_local_environment_allows_docker_compose_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/financial_insights",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")

    settings = Settings()

    assert settings.is_local is True
    assert settings.app_env == "local"


def test_staging_rejects_local_service_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/financial_insights",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("MINIO_ENDPOINT", "minio")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")

    with pytest.raises(ValueError, match="staging configuration is invalid"):
        Settings()


def test_production_accepts_managed_service_configuration(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app:secret@managed-postgres.example.com:5432/app",
    )
    monkeypatch.setenv("REDIS_URL", "rediss://managed-cache.example.com:6379/0")
    monkeypatch.setenv("MINIO_ENDPOINT", "object-storage.example.com")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "production-access-key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "production-secret-key")

    settings = Settings()

    assert settings.app_env == "production"
    assert settings.is_local is False
