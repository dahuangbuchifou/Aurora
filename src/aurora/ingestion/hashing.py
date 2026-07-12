"""Deterministic normalization and hashing helpers for ingestion."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

_LINE_ENDINGS = re.compile(r"\r\n?|\u2028|\u2029")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize representation without trimming meaningful content.

    The normalization removes a leading UTF-8 BOM and canonicalizes line
    endings to LF. It intentionally does not strip trailing spaces or blank
    lines because those may be meaningful in Markdown/code blocks.
    """

    if text.startswith("\ufeff"):
        text = text[1:]
    return _LINE_ENDINGS.sub("\n", text)


def normalized_text_bytes(text: str) -> bytes:
    # EOF line-ending differences are representation details, not content.
    return normalize_text(text).rstrip("\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash_for_text(text: str) -> str:
    return sha256_hex(normalized_text_bytes(text))


def canonical_json_bytes(value: Any) -> bytes:
    """Encode semantic JSON deterministically for hashing."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def normalize_identity_text(value: str) -> str:
    """Normalize a human-provided identity token for stable comparison."""

    normalized = unicodedata.normalize("NFKC", value).strip()
    return _WHITESPACE.sub(" ", normalized).casefold()


def stable_id(prefix: str, *parts: object, digest_length: int = 40) -> str:
    """Build a stable object id from typed string parts."""

    encoded = "\x1f".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:digest_length]
    return f"{prefix}_{digest}"
