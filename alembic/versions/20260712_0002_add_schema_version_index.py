"""add schema_version index

Revision ID: 20260712_0002
Revises: 20260711_0001
Create Date: 2026-07-12
"""

from typing import Sequence

from alembic import op

revision: str = "20260712_0002"
down_revision: str | Sequence[str] | None = "20260711_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_object_records_schema_version",
        "object_records",
        ["schema_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_object_records_schema_version",
        table_name="object_records",
    )
