"""Stable ingestion errors used by services and CLI output."""

from __future__ import annotations

from typing import Any


class IngestionError(RuntimeError):
    """Base exception carrying a stable machine-readable error code."""

    code = "INGEST_ERROR"

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "error",
            "error_code": self.code,
            "error_message": self.message,
            "context": self.context,
        }


class FileTooLargeError(IngestionError):
    code = "INGEST_FILE_TOO_LARGE"


class EmptyInputError(IngestionError):
    code = "INGEST_EMPTY_FILE"


class UnsupportedInputError(IngestionError):
    code = "INGEST_UNSUPPORTED_CONTENT"


class InvalidEncodingError(IngestionError):
    code = "INGEST_INVALID_ENCODING"


class InvalidStructuredSegmentsError(IngestionError):
    code = "INGEST_INVALID_SEGMENTS"


class DuplicateIngestionError(IngestionError):
    code = "INGEST_DUPLICATE_DOCUMENT"


class PersistenceIngestionError(IngestionError):
    code = "INGEST_PERSISTENCE_ERROR"
