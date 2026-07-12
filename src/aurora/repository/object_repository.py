"""Repository for validated Aurora domain objects."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aurora.core.models.common import BaseObject, utc_now
from aurora.core.models.enums import LifecycleStatus, ObjectType
from aurora.core.schema_registry import parse_object
from aurora.db.models import ObjectRecord


class ObjectNotFoundError(LookupError):
    pass


class DuplicateObjectError(ValueError):
    pass


class ConcurrentUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class RawObjectRecord:
    """Immutable audit snapshot of an ObjectRecord."""

    id: str
    object_type: str
    schema_version: str
    lifecycle_status: str
    workspace_id: str
    privacy_level: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
    payload: dict[str, Any]

    @classmethod
    def from_record(cls, record: ObjectRecord) -> "RawObjectRecord":
        return cls(
            id=record.id,
            object_type=record.object_type,
            schema_version=record.schema_version,
            lifecycle_status=record.lifecycle_status,
            workspace_id=record.workspace_id,
            privacy_level=record.privacy_level,
            created_by=record.created_by,
            created_at=record.created_at,
            updated_at=record.updated_at,
            deleted_at=record.deleted_at,
            version=record.version,
            payload=deepcopy(record.payload),
        )


class ObjectRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _record_from_object(obj: BaseObject) -> ObjectRecord:
        payload = obj.model_dump(mode="json")
        return ObjectRecord(
            id=obj.id,
            object_type=obj.object_type.value,
            schema_version=obj.schema_version,
            lifecycle_status=obj.status.value,
            workspace_id=obj.workspace_id,
            privacy_level=obj.privacy_level.value,
            created_by=obj.created_by,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            deleted_at=obj.deleted_at,
            version=1,
            payload=payload,
        )

    def create(self, obj: BaseObject) -> BaseObject:
        record = self._record_from_object(obj)
        self.session.add(record)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateObjectError(f"object already exists: {obj.id}") from exc
        return obj

    def get(
        self,
        object_id: str,
        *,
        include_deleted: bool = False,
    ) -> BaseObject | None:
        record = self.session.get(ObjectRecord, object_id)
        if record is None:
            return None
        if record.deleted_at is not None and not include_deleted:
            return None
        return parse_object(record.payload)

    def get_required(
        self,
        object_id: str,
        *,
        include_deleted: bool = False,
    ) -> BaseObject:
        obj = self.get(object_id, include_deleted=include_deleted)
        if obj is None:
            raise ObjectNotFoundError(f"object not found: {object_id}")
        return obj

    def get_raw_record(self, object_id: str) -> RawObjectRecord | None:
        record = self.session.get(ObjectRecord, object_id)
        if record is None:
            return None
        return RawObjectRecord.from_record(record)

    def list_by_schema_version(
        self,
        schema_version: str,
        *,
        workspace_id: str | None = None,
        include_deleted: bool = True,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[RawObjectRecord]:
        if not schema_version:
            raise ValueError("schema_version is required")
        if limit < 1 or limit > 10000:
            raise ValueError("limit must be between 1 and 10000")
        if offset < 0:
            raise ValueError("offset cannot be negative")

        statement: Select[tuple[ObjectRecord]] = select(ObjectRecord).where(
            ObjectRecord.schema_version == schema_version
        )
        if workspace_id is not None:
            statement = statement.where(ObjectRecord.workspace_id == workspace_id)
        if not include_deleted:
            statement = statement.where(ObjectRecord.deleted_at.is_(None))
        statement = (
            statement.order_by(ObjectRecord.created_at, ObjectRecord.id)
            .limit(limit)
            .offset(offset)
        )
        records: Sequence[ObjectRecord] = self.session.scalars(statement).all()
        return [RawObjectRecord.from_record(record) for record in records]

    def list(
        self,
        *,
        object_type: ObjectType | None = None,
        workspace_id: str | None = "default",
        lifecycle_status: LifecycleStatus | None = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BaseObject]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset cannot be negative")

        statement: Select[tuple[ObjectRecord]] = select(ObjectRecord)
        if object_type is not None:
            statement = statement.where(ObjectRecord.object_type == object_type.value)
        if workspace_id is not None:
            statement = statement.where(ObjectRecord.workspace_id == workspace_id)
        if lifecycle_status is not None:
            statement = statement.where(
                ObjectRecord.lifecycle_status == lifecycle_status.value
            )
        if not include_deleted:
            statement = statement.where(ObjectRecord.deleted_at.is_(None))
        statement = (
            statement.order_by(ObjectRecord.created_at, ObjectRecord.id)
            .limit(limit)
            .offset(offset)
        )
        records: Sequence[ObjectRecord] = self.session.scalars(statement).all()
        return [parse_object(record.payload) for record in records]

    def update(
        self,
        obj: BaseObject,
        *,
        expected_version: int | None = None,
    ) -> BaseObject:
        record = self.session.get(ObjectRecord, obj.id)
        if record is None:
            raise ObjectNotFoundError(f"object not found: {obj.id}")
        if expected_version is not None and record.version != expected_version:
            raise ConcurrentUpdateError(
                f"version mismatch for {obj.id}: "
                f"expected {expected_version}, actual {record.version}"
            )

        payload = obj.model_dump(mode="json")
        payload["updated_at"] = utc_now().isoformat()
        validated = parse_object(payload)

        record.object_type = validated.object_type.value
        record.schema_version = validated.schema_version
        record.lifecycle_status = validated.status.value
        record.workspace_id = validated.workspace_id
        record.privacy_level = validated.privacy_level.value
        record.created_by = validated.created_by
        record.updated_at = validated.updated_at
        record.deleted_at = validated.deleted_at
        record.version += 1
        record.payload = validated.model_dump(mode="json")
        self.session.flush()
        return validated

    def soft_delete(self, object_id: str) -> BaseObject:
        record = self.session.get(ObjectRecord, object_id)
        if record is None:
            raise ObjectNotFoundError(f"object not found: {object_id}")
        payload = deepcopy(record.payload)
        deleted_at = utc_now()
        payload["status"] = LifecycleStatus.DELETED.value
        payload["deleted_at"] = deleted_at.isoformat()
        payload["updated_at"] = deleted_at.isoformat()
        validated = parse_object(payload)
        record.schema_version = validated.schema_version
        record.lifecycle_status = LifecycleStatus.DELETED.value
        record.deleted_at = deleted_at
        record.updated_at = deleted_at
        record.version += 1
        record.payload = validated.model_dump(mode="json")
        self.session.flush()
        return validated

    def restore(self, object_id: str) -> BaseObject:
        record = self.session.get(ObjectRecord, object_id)
        if record is None:
            raise ObjectNotFoundError(f"object not found: {object_id}")
        payload = deepcopy(record.payload)
        updated_at = utc_now()
        payload["status"] = LifecycleStatus.ACTIVE.value
        payload["deleted_at"] = None
        payload["updated_at"] = updated_at.isoformat()
        validated = parse_object(payload)
        record.schema_version = validated.schema_version
        record.lifecycle_status = LifecycleStatus.ACTIVE.value
        record.deleted_at = None
        record.updated_at = updated_at
        record.version += 1
        record.payload = validated.model_dump(mode="json")
        self.session.flush()
        return validated

    def count(
        self,
        *,
        object_type: ObjectType | None = None,
        include_deleted: bool = False,
    ) -> int:
        statement = select(func.count()).select_from(ObjectRecord)
        if object_type is not None:
            statement = statement.where(ObjectRecord.object_type == object_type.value)
        if not include_deleted:
            statement = statement.where(ObjectRecord.deleted_at.is_(None))
        return int(self.session.scalar(statement) or 0)

    def record_version(self, object_id: str) -> int:
        record = self.session.get(ObjectRecord, object_id)
        if record is None:
            raise ObjectNotFoundError(f"object not found: {object_id}")
        return record.version
