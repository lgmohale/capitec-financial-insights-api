"""rename uuid columns to id

Revision ID: 20260505_0002
Revises: 20260505_0001
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260505_0002"
down_revision: str | None = "20260505_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "linked_account_user_id_fkey",
        "linked_account",
        type_="foreignkey",
    )
    op.alter_column("users", "uuid", new_column_name="id")
    op.alter_column("linked_account", "uuid", new_column_name="id")
    op.create_foreign_key(
        "linked_account_user_id_fkey",
        "linked_account",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "linked_account_user_id_fkey",
        "linked_account",
        type_="foreignkey",
    )
    op.alter_column("linked_account", "id", new_column_name="uuid")
    op.alter_column("users", "id", new_column_name="uuid")
    op.create_foreign_key(
        "linked_account_user_id_fkey",
        "linked_account",
        "users",
        ["user_id"],
        ["uuid"],
    )
