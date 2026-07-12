"""Ingestion resource limits."""

from __future__ import annotations

import os

from .contracts import IngestionInputType

MIB = 1024 * 1024
DEFAULT_MAX_INGEST_BYTES = 10 * MIB
DEFAULT_MAX_PDF_BYTES = 50 * MIB
DEFAULT_MAX_PDF_PAGES = 500
MAX_INGEST_BYTES_ENV = "AURORA_INGEST_MAX_BYTES"
MAX_PDF_BYTES_ENV = "AURORA_PDF_MAX_BYTES"
MAX_PDF_PAGES_ENV = "AURORA_PDF_MAX_PAGES"
WEB_TIMEOUT_SECONDS_ENV = "AURORA_WEB_TIMEOUT_SECONDS"
WEB_MAX_REDIRECTS_ENV = "AURORA_WEB_MAX_REDIRECTS"
DEFAULT_WEB_TIMEOUT_SECONDS = 15.0
DEFAULT_WEB_MAX_REDIRECTS = 5


def resolve_max_bytes(explicit: int | None = None) -> int:
    """Resolve the legacy/default text ingestion size."""

    if explicit is not None:
        value = int(explicit)
    else:
        raw = os.getenv(MAX_INGEST_BYTES_ENV)
        value = int(raw) if raw is not None else DEFAULT_MAX_INGEST_BYTES
    if value < 1:
        raise ValueError("maximum ingestion size must be positive")
    return value


def resolve_max_bytes_for_input(
    input_type: IngestionInputType,
    explicit: int | None = None,
) -> int:
    if explicit is not None:
        value = int(explicit)
    elif input_type == IngestionInputType.PDF:
        value = int(os.getenv(MAX_PDF_BYTES_ENV, str(DEFAULT_MAX_PDF_BYTES)))
    else:
        value = resolve_max_bytes(None)
    if value < 1:
        raise ValueError("maximum ingestion size must be positive")
    return value


def resolve_max_pdf_pages(explicit: int | None = None) -> int:
    value = (
        int(explicit)
        if explicit is not None
        else int(os.getenv(MAX_PDF_PAGES_ENV, str(DEFAULT_MAX_PDF_PAGES)))
    )
    if value < 1:
        raise ValueError("maximum PDF pages must be positive")
    return value


def resolve_web_timeout_seconds() -> float:
    value = float(os.getenv(WEB_TIMEOUT_SECONDS_ENV, str(DEFAULT_WEB_TIMEOUT_SECONDS)))
    if value <= 0:
        raise ValueError("web timeout must be positive")
    return value


def resolve_web_max_redirects() -> int:
    value = int(os.getenv(WEB_MAX_REDIRECTS_ENV, str(DEFAULT_WEB_MAX_REDIRECTS)))
    if value < 0:
        raise ValueError("web redirect limit cannot be negative")
    return value
