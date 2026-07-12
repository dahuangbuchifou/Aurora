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


def test_web_limits_use_environment(monkeypatch):
    from aurora.ingestion.limits import (
        resolve_web_max_redirects,
        resolve_web_timeout_seconds,
    )

    monkeypatch.setenv("AURORA_WEB_TIMEOUT_SECONDS", "7.5")
    monkeypatch.setenv("AURORA_WEB_MAX_REDIRECTS", "2")
    assert resolve_web_timeout_seconds() == 7.5
    assert resolve_web_max_redirects() == 2


def test_web_limits_reject_invalid_values(monkeypatch):
    from aurora.ingestion.limits import (
        resolve_web_max_redirects,
        resolve_web_timeout_seconds,
    )

    monkeypatch.setenv("AURORA_WEB_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValueError, match="timeout"):
        resolve_web_timeout_seconds()

    monkeypatch.setenv("AURORA_WEB_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("AURORA_WEB_MAX_REDIRECTS", "-1")
    with pytest.raises(ValueError, match="redirect"):
        resolve_web_max_redirects()
