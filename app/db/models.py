from datetime import datetime
from uuid import UUID as PythonUUID
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[PythonUUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LinkedAccount(Base):
    __tablename__ = "linked_account"

    user_id: Mapped[PythonUUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        primary_key=True,
    )
    id: Mapped[PythonUUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    bank_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
