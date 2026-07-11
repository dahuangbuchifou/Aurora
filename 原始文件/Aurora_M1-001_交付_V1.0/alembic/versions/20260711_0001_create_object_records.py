"""create object_records table

Revision ID: 20260711_0001
Revises:
Create Date: 2026-07-11
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260711_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "object_records",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("object_type", sa.String(length=40), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False),
        sa.Column("workspace_id", sa.String(length=80), nullable=False),
        sa.Column("privacy_level", sa.String(length=30), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_object_records_object_type",
        "object_records",
        ["object_type"],
        unique=False,
    )
    op.create_index(
        "ix_object_records_lifecycle_status",
        "object_records",
        ["lifecycle_status"],
        unique=False,
    )
    op.create_index(
        "ix_object_records_workspace_id",
        "object_records",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_object_records_updated_at",
        "object_records",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_object_records_workspace_type_status",
        "object_records",
        ["workspace_id", "object_type", "lifecycle_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_object_records_workspace_type_status",
        table_name="object_records",
    )
    op.drop_index("ix_object_records_updated_at", table_name="object_records")
    op.drop_index("ix_object_records_workspace_id", table_name="object_records")
    op.drop_index(
        "ix_object_records_lifecycle_status",
        table_name="object_records",
    )
    op.drop_index("ix_object_records_object_type", table_name="object_records")
    op.drop_table("object_records")
