from contextlib import suppress
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import UploadedStatement
from app.db.session import engine
from app.storage.object_storage import (
    delete_object,
    object_exists,
    read_json_object,
    upload_json_object,
)

pytestmark = pytest.mark.skipif(
    get_settings().minio_endpoint != "minio",
    reason="Docker Compose integration services are not configured.",
)


def test_minio_json_object_round_trip() -> None:
    object_key = f"integration-tests/{uuid4()}.json"
    payload = {"status": "ok", "source": "integration"}

    try:
        uploaded_key = upload_json_object(object_key=object_key, value=payload)

        assert uploaded_key == object_key
        assert object_exists(object_key) is True
        assert read_json_object(object_key) == payload
    finally:
        with suppress(Exception):
            delete_object(object_key)


def test_postgres_metadata_tables_are_available() -> None:
    statement_id = uuid4()
    object_key = f"input/{statement_id}/statement.pdf"

    with Session(engine) as db:
        db.add(
            UploadedStatement(
                id=statement_id,
                bank_name="Integration Test Statement",
                object_key=object_key,
            )
        )
        db.commit()

        saved_statement = db.scalar(
            select(UploadedStatement).where(UploadedStatement.id == statement_id)
        )

        assert saved_statement is not None
        assert saved_statement.bank_name == "Integration Test Statement"
        assert saved_statement.object_key == object_key

        db.execute(
            delete(UploadedStatement).where(UploadedStatement.id == statement_id)
        )
        db.commit()


def test_integration_uses_docker_service_settings() -> None:
    settings = get_settings()

    assert settings.minio_endpoint == "minio"
    assert "postgres" in settings.database_url
