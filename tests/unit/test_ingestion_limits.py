import pytest

from aurora.ingestion.limits import (
    DEFAULT_MAX_INGEST_BYTES,
    MAX_INGEST_BYTES_ENV,
    resolve_max_bytes,
)


def test_limit_default_explicit_and_environment(monkeypatch):
    monkeypatch.delenv(MAX_INGEST_BYTES_ENV, raising=False)
    assert resolve_max_bytes() == DEFAULT_MAX_INGEST_BYTES
    assert resolve_max_bytes(123) == 123
    monkeypatch.setenv(MAX_INGEST_BYTES_ENV, "456")
    assert resolve_max_bytes() == 456
    with pytest.raises(ValueError):
        resolve_max_bytes(0)
