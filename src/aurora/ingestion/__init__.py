"""Offline ingestion contracts and helpers."""

from .contracts import (
    DuplicateStrategy,
    IngestionInputType,
    IngestionRequest,
    IngestionResult,
    ParserDescriptor,
    StructuredDocumentMetadata,
    StructuredSegment,
    StructuredSegmentsManifest,
    StructuredSourceMetadata,
)
from .errors import (
    DuplicateIngestionError,
    EmptyInputError,
    FileTooLargeError,
    IngestionError,
    InvalidEncodingError,
    InvalidStructuredSegmentsError,
    PersistenceIngestionError,
    UnsupportedInputError,
)

__all__ = [
    "DuplicateStrategy",
    "IngestionInputType",
    "IngestionRequest",
    "IngestionResult",
    "ParserDescriptor",
    "StructuredDocumentMetadata",
    "StructuredSegment",
    "StructuredSegmentsManifest",
    "StructuredSourceMetadata",
    "IngestionError",
    "FileTooLargeError",
    "EmptyInputError",
    "UnsupportedInputError",
    "InvalidEncodingError",
    "InvalidStructuredSegmentsError",
    "DuplicateIngestionError",
    "PersistenceIngestionError",
]
