from contextlib import suppress
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import BankStatement, User
from app.db.session import engine
from app.storage.object_storage import (
    delete_object,
    object_exists,
    read_json_object,
    upload_json_object,
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
    user_id = uuid4()
    statement_id = uuid4()
    file_url = f"input/{user_id}/{statement_id}.pdf"

    with Session(engine) as db:
        db.add(User(id=user_id, name="Integration Test User"))
        db.flush()
        db.add(
            BankStatement(
                id=statement_id,
                user_id=user_id,
                bank_name="Integration Test Statement",
                file_url=file_url,
            )
        )
        db.commit()

        saved_statement = db.scalar(
            select(BankStatement).where(BankStatement.id == statement_id)
        )

        assert saved_statement is not None
        assert saved_statement.user_id == user_id
        assert saved_statement.file_url == file_url

        db.execute(delete(BankStatement).where(BankStatement.id == statement_id))
        db.execute(delete(User).where(User.id == user_id))
        db.commit()


def test_integration_uses_docker_service_settings() -> None:
    settings = get_settings()

    assert settings.minio_endpoint == "minio"
    assert "postgres" in settings.database_url
