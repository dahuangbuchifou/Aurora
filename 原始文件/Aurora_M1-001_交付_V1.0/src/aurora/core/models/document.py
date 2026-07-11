"""Document and content-unit objects."""

from datetime import datetime
from typing import Literal

from pydantic import Field, HttpUrl

from .common import BaseObject, QualityAssessment, SourceLocator, new_id, utc_now
from .enums import ContentUnitType, DocumentType, ObjectType, ParseStatus


class Document(BaseObject):
    id: str = Field(default_factory=lambda: new_id("doc"))
    object_type: Literal[ObjectType.DOCUMENT] = ObjectType.DOCUMENT
    source_id: str
    document_type: DocumentType
    title: str = Field(min_length=1, max_length=1000)
    original_url: HttpUrl | None = None
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=utc_now)
    authors: list[str] = Field(default_factory=list)
    content_hash: str | None = None
    normalized_url: str | None = None
    mime_type: str | None = None
    raw_storage_uri: str | None = None
    parse_status: ParseStatus = ParseStatus.DISCOVERED
    copyright_note: str | None = None
    parent_document_id: str | None = None
    duplicate_of_document_id: str | None = None


class ContentUnit(BaseObject):
    id: str = Field(default_factory=lambda: new_id("cu"))
    object_type: Literal[ObjectType.CONTENT_UNIT] = ObjectType.CONTENT_UNIT
    document_id: str
    unit_type: ContentUnitType
    sequence_no: int = Field(ge=0)
    text: str = Field(min_length=1)
    locator: SourceLocator
    speaker: str | None = None
    quality: QualityAssessment = Field(default_factory=QualityAssessment)
    parent_unit_id: str | None = None
