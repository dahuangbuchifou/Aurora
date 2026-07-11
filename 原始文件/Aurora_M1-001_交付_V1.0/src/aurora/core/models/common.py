"""Shared Pydantic models and validation helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .enums import (
    HumanReviewStatus,
    LifecycleStatus,
    ObjectType,
    OriginType,
    PrivacyLevel,
    QualityLevel,
    SourceQualityTier,
    TimePrecision,
)

SCHEMA_VERSION = "1.0"


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4()}"


class AuroraModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class HumanReview(AuroraModel):
    status: HumanReviewStatus = HumanReviewStatus.NOT_REVIEWED
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_review(self) -> "HumanReview":
        if self.status != HumanReviewStatus.NOT_REVIEWED:
            if not self.reviewed_by or not self.reviewed_at:
                raise ValueError(
                    "reviewed_by and reviewed_at are required after review"
                )
        return self


class Provenance(AuroraModel):
    origin_type: OriginType = OriginType.ORIGINAL
    origin_object_ids: list[str] = Field(default_factory=list)
    processing_run_id: str | None = None
    human_review: HumanReview = Field(default_factory=HumanReview)
    derivation_note: str | None = None
    source_locator_required: bool = False

    @model_validator(mode="after")
    def validate_derived(self) -> "Provenance":
        if self.origin_type == OriginType.DERIVED and not self.origin_object_ids:
            raise ValueError("derived provenance requires origin_object_ids")
        return self


class SourceLocator(AuroraModel):
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    page_no: int | None = Field(default=None, ge=1)
    block_no: int | None = Field(default=None, ge=1)
    paragraph_no: int | None = Field(default=None, ge=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    heading_path: list[str] = Field(default_factory=list)
    sheet_name: str | None = None
    row_no: int | None = Field(default=None, ge=1)
    column_name: str | None = None
    css_selector: str | None = None
    xpath: str | None = None

    @model_validator(mode="after")
    def validate_locator(self) -> "SourceLocator":
        values = (
            self.start_seconds,
            self.end_seconds,
            self.page_no,
            self.block_no,
            self.paragraph_no,
            self.line_start,
            self.line_end,
            self.sheet_name,
            self.row_no,
            self.column_name,
            self.css_selector,
            self.xpath,
        )
        if not any(value is not None for value in values) and not self.heading_path:
            raise ValueError("at least one locator field is required")
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds < self.start_seconds
        ):
            raise ValueError("end_seconds cannot be earlier than start_seconds")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end cannot be earlier than line_start")
        return self


class QualityAssessment(AuroraModel):
    source_quality: SourceQualityTier | None = None
    parse_quality: QualityLevel | None = None
    extraction_confidence: QualityLevel | None = None
    evidence_strength: str | None = None
    reasoning_confidence: QualityLevel | None = None
    human_review_status: HumanReviewStatus = HumanReviewStatus.NOT_REVIEWED
    quality_flags: list[str] = Field(default_factory=list)


class TimeRange(AuroraModel):
    start: date | datetime | None = None
    end: date | datetime | None = None
    precision: TimePrecision = TimePrecision.UNKNOWN

    @model_validator(mode="after")
    def validate_order(self) -> "TimeRange":
        if self.start is not None and self.end is not None:
            start = (
                self.start.date()
                if isinstance(self.start, datetime)
                else self.start
            )
            end = self.end.date() if isinstance(self.end, datetime) else self.end
            if end < start:
                raise ValueError("time range end cannot be earlier than start")
        return self


class ValidityWindow(AuroraModel):
    as_of_date: date
    valid_from: date | datetime | None = None
    valid_to: date | datetime | None = None
    review_due_at: date | datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "ValidityWindow":
        if self.valid_from is not None and self.valid_to is not None:
            start = (
                self.valid_from.date()
                if isinstance(self.valid_from, datetime)
                else self.valid_from
            )
            end = (
                self.valid_to.date()
                if isinstance(self.valid_to, datetime)
                else self.valid_to
            )
            if end < start:
                raise ValueError("valid_to cannot be earlier than valid_from")
        return self


class ProcessorInfo(AuroraModel):
    module: str
    model_provider: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    code_version: str | None = None


class ExternalReference(AuroraModel):
    name: str
    value: str
    url: HttpUrl | None = None


class BaseObject(AuroraModel):
    id: str
    object_type: ObjectType
    schema_version: str = SCHEMA_VERSION
    status: LifecycleStatus = LifecycleStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str = "system"
    workspace_id: str = "default"
    language: str | None = "zh-CN"
    tags: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    deleted_at: datetime | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_common_state(self) -> "BaseObject":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        if self.status == LifecycleStatus.DELETED and self.deleted_at is None:
            raise ValueError("deleted_at is required when status is deleted")
        if self.status != LifecycleStatus.DELETED and self.deleted_at is not None:
            raise ValueError("deleted_at must be null unless status is deleted")
        return self
