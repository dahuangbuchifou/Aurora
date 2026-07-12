"""Application-level ingestion DTOs.

These contracts are not Aurora core knowledge objects and are deliberately not
registered in the 17-object core schema registry.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from aurora.core.models.common import AuroraModel, SourceLocator
from aurora.core.models.enums import (
    ContentUnitType,
    DocumentType,
    SourceType,
)


class IngestionInputType(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    STRUCTURED_SEGMENTS = "structured_segments"


class DuplicateStrategy(StrEnum):
    REUSE = "reuse"
    REJECT = "reject"
    NEW_VERSION = "new_version"


class ParserDescriptor(AuroraModel):
    name: str
    version: str


class IngestionRequest(AuroraModel):
    path: Path
    input_type: IngestionInputType
    workspace_id: str | None = None
    source_name: str | None = None
    source_type: SourceType | None = None
    source_key: str | None = None
    source_homepage_url: HttpUrl | None = None
    title: str | None = None
    document_type: DocumentType | None = None
    published_at: datetime | None = None
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None
    duplicate_strategy: DuplicateStrategy = DuplicateStrategy.REUSE
    max_bytes: int | None = Field(default=None, ge=1)
    dry_run: bool = False
    created_by: str = "system"

    @model_validator(mode="after")
    def validate_source_metadata(self) -> "IngestionRequest":
        if self.input_type != IngestionInputType.STRUCTURED_SEGMENTS:
            if not self.source_name or self.source_type is None:
                raise ValueError(
                    "source_name and source_type are required for file ingestion"
                )
        return self


class StructuredSourceMetadata(AuroraModel):
    name: str = Field(min_length=1, max_length=500)
    source_type: SourceType
    canonical_key: str | None = None
    homepage_url: HttpUrl | None = None


class StructuredDocumentMetadata(AuroraModel):
    title: str = Field(min_length=1, max_length=1000)
    document_type: DocumentType = DocumentType.TEXT
    published_at: datetime | None = None
    language: str = "zh-CN"
    tags: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None


class StructuredSegment(AuroraModel):
    sequence_no: int = Field(ge=0)
    unit_type: ContentUnitType
    text: str = Field(min_length=1)
    locator: SourceLocator
    speaker: str | None = None


class StructuredSegmentsManifest(AuroraModel):
    schema_version: Literal["1.0"] = "1.0"
    workspace_id: str = "default"
    source: StructuredSourceMetadata
    document: StructuredDocumentMetadata
    segments: list[StructuredSegment] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sequences(self) -> "StructuredSegmentsManifest":
        actual = [segment.sequence_no for segment in self.segments]
        expected = list(range(len(self.segments)))
        if actual != expected:
            raise ValueError(
                "structured segment sequence_no values must be contiguous "
                "and start at 0"
            )
        return self


class IngestionResult(AuroraModel):
    status: Literal["success"] = "success"
    processing_run_id: str
    source_id: str
    document_id: str
    content_unit_ids: list[str] = Field(default_factory=list)
    content_unit_count: int = Field(ge=0)
    content_hash: str
    idempotency_key: str
    reused: bool = False
    dry_run: bool = False
    parser: ParserDescriptor
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_count(self) -> "IngestionResult":
        if self.content_unit_count != len(self.content_unit_ids):
            raise ValueError("content_unit_count must equal len(content_unit_ids)")
        return self
