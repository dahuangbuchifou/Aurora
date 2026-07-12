"""Ingestion resource limits."""

from __future__ import annotations

import os

DEFAULT_MAX_INGEST_BYTES = 10 * 1024 * 1024
MAX_INGEST_BYTES_ENV = "AURORA_INGEST_MAX_BYTES"


def resolve_max_bytes(explicit: int | None = None) -> int:
    """Resolve the maximum input size from an explicit value or environment."""

    if explicit is not None:
        value = int(explicit)
    else:
        raw = os.getenv(MAX_INGEST_BYTES_ENV)
        value = int(raw) if raw is not None else DEFAULT_MAX_INGEST_BYTES
    if value < 1:
        raise ValueError("maximum ingestion size must be positive")
    return value
