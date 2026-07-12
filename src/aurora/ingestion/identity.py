"""Source identity, document idempotency, and deterministic object ids."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from aurora.core.models.enums import ContentUnitType, SourceType

from .hashing import normalize_identity_text, sha256_hex, stable_id


def normalize_http_url(value: str) -> str:
    """Return a conservative normalized HTTP(S) URL."""

    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source URL must be an absolute HTTP(S) URL")

    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    path = quote(unquote(parsed.path or "/"), safe="/%:@")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, host, path, parsed.query, ""))


def canonical_source_key(
    *,
    source_name: str,
    source_type: SourceType,
    explicit_key: str | None = None,
    homepage_url: str | None = None,
) -> str:
    """Build a source-level identity independent of document content."""

    if explicit_key:
        return f"key:{normalize_identity_text(explicit_key)}"
    if homepage_url:
        return f"url:{normalize_http_url(homepage_url)}"
    return f"name:{source_type.value}:{normalize_identity_text(source_name)}"


def source_object_id(
    *,
    workspace_id: str,
    source_type: SourceType,
    canonical_key: str,
) -> str:
    return stable_id("src", workspace_id, source_type.value, canonical_key)


def normalized_file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def document_dedupe_key(
    *,
    source_id: str,
    content_hash: str,
    parser_name: str,
    parser_version: str,
    parser_config_hash: str = "default",
) -> str:
    """Return exact-document identity including parsing configuration."""

    parts = [source_id, content_hash, parser_name, parser_version]
    # Preserve the exact M2-001 identity for historical/default parsers.
    if parser_config_hash not in {"", "default"}:
        parts.append(parser_config_hash)
    return sha256_hex("\x1f".join(parts).encode("utf-8"))


def document_series_key(
    *,
    source_id: str,
    input_uri: str,
    idempotency_key: str | None,
) -> str:
    logical_input = (
        f"explicit:{normalize_identity_text(idempotency_key)}"
        if idempotency_key
        else f"uri:{input_uri}"
    )
    return sha256_hex(f"{source_id}\x1f{logical_input}".encode("utf-8"))


def document_object_id(
    *,
    dedupe_key: str,
    series_key: str,
    version_no: int,
) -> str:
    return stable_id("doc", dedupe_key, series_key, version_no)


def content_unit_object_id(
    *,
    document_id: str,
    unit_type: ContentUnitType,
    sequence_no: int,
    normalized_text_hash: str,
) -> str:
    return stable_id(
        "cu",
        document_id,
        unit_type.value,
        sequence_no,
        normalized_text_hash,
    )
