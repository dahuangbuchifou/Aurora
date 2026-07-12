"""Application-level ingestion DTOs.

These contracts are not Aurora core knowledge objects and are deliberately not
registered in the 17-object core schema registry.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, HttpUrl, model_validator

from aurora.core.models.common import AuroraModel, SourceLocator
from aurora.core.models.enums import (
    ContentUnitType,
    DocumentType,
    ParseStatus,
    SourceType,
)


class IngestionInputType(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    STRUCTURED_SEGMENTS = "structured_segments"
    HTML = "html"
    URL = "url"
    PDF = "pdf"
    SRT = "srt"
    VTT = "vtt"


class DuplicateStrategy(StrEnum):
    REUSE = "reuse"
    REJECT = "reject"
    NEW_VERSION = "new_version"


class PdfTableMode(StrEnum):
    OFF = "off"
    BEST_EFFORT = "best_effort"


class ParserDescriptor(AuroraModel):
    name: str
    version: str


class IngestionRequest(AuroraModel):
    path: Path | None = None
    url: HttpUrl | None = None
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
    max_pages: int | None = Field(default=None, ge=1)
    page_selection: str | None = None
    table_mode: PdfTableMode = PdfTableMode.BEST_EFFORT
    content_selector: str | None = None
    allow_private_network: bool = False
    dry_run: bool = False
    created_by: str = "system"

    @model_validator(mode="after")
    def validate_input_and_source_metadata(self) -> "IngestionRequest":
        if self.input_type == IngestionInputType.URL:
            if self.url is None or self.path is not None:
                raise ValueError("url input requires url and forbids path")
        else:
            if self.path is None or self.url is not None:
                raise ValueError("file input requires path and forbids url")

        if self.input_type != IngestionInputType.STRUCTURED_SEGMENTS:
            if not self.source_name or self.source_type is None:
                raise ValueError(
                    "source_name and source_type are required for ingestion"
                )

        if self.input_type != IngestionInputType.PDF:
            if self.page_selection is not None:
                raise ValueError("page_selection is only valid for PDF input")
            if self.max_pages is not None:
                raise ValueError("max_pages is only valid for PDF input")
            if self.table_mode != PdfTableMode.BEST_EFFORT:
                raise ValueError("table_mode is only valid for PDF input")

        if self.input_type not in {IngestionInputType.HTML, IngestionInputType.URL}:
            if self.content_selector is not None:
                raise ValueError("content_selector is only valid for HTML or URL input")
            if self.allow_private_network:
                raise ValueError("allow_private_network is only valid for URL input")
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
    raw_content_hash: str | None = None
    parser_config_hash: str | None = None
    parse_status: ParseStatus = ParseStatus.PARSED
    idempotency_key: str
    reused: bool = False
    dry_run: bool = False
    parser: ParserDescriptor
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_count(self) -> "IngestionResult":
        if self.content_unit_count != len(self.content_unit_ids):
            raise ValueError("content_unit_count must equal len(content_unit_ids)")
        return self
