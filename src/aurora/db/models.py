"""Persistence model for versioned Aurora objects.

M1 stores stable indexed metadata in columns and the complete validated domain
object in JSON. This avoids premature normalization while the object model is
still being validated. High-frequency domain fields can be normalized later
through Alembic without changing the Pydantic contract.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ObjectRecord(Base):
    __tablename__ = "object_records"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    object_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    privacy_level: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "ix_object_records_workspace_type_status",
            "workspace_id",
            "object_type",
            "lifecycle_status",
        ),
        Index("ix_object_records_updated_at", "updated_at"),
    )
