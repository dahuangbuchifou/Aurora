"""Deterministic local file collectors."""

from __future__ import annotations

from pathlib import Path

from aurora.ingestion.errors import (
    EmptyInputError,
    FileTooLargeError,
    InvalidEncodingError,
    UnsupportedInputError,
)
from aurora.ingestion.hashing import normalize_text
from aurora.ingestion.identity import normalized_file_uri

from .base import CollectedInput, Collector


class LocalFileCollector(Collector):
    """Read a UTF-8 local text file after size and binary checks."""

    def collect(self, path: Path, *, max_bytes: int) -> CollectedInput:
        resolved, raw = _read_local_bytes(path, max_bytes=max_bytes)
        if b"\x00" in raw:
            raise UnsupportedInputError(
                "binary content is not supported for this input type",
                context={"path": str(resolved)},
            )
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidEncodingError(
                "input must be valid UTF-8 text",
                context={"path": str(resolved), "encoding": "utf-8"},
            ) from exc
        text = normalize_text(text)
        if not text.strip():
            raise EmptyInputError(
                "input file is empty or contains only whitespace",
                context={"path": str(resolved)},
            )
        return CollectedInput(
            path=resolved,
            input_uri=normalized_file_uri(resolved),
            file_name=resolved.name,
            suffix=resolved.suffix.lower(),
            size_bytes=len(raw),
            text=text,
            raw_bytes=raw,
        )


class LocalBinaryFileCollector(Collector):
    """Read a local binary artifact while enforcing size limits."""

    def collect(self, path: Path, *, max_bytes: int) -> CollectedInput:
        resolved, raw = _read_local_bytes(path, max_bytes=max_bytes)
        if not raw:
            raise EmptyInputError(
                "input file is empty",
                context={"path": str(resolved)},
            )
        return CollectedInput(
            path=resolved,
            input_uri=normalized_file_uri(resolved),
            file_name=resolved.name,
            suffix=resolved.suffix.lower(),
            size_bytes=len(raw),
            text="",
            raw_bytes=raw,
            media_type="application/pdf" if resolved.suffix.lower() == ".pdf" else None,
        )


def _read_local_bytes(path: Path, *, max_bytes: int) -> tuple[Path, bytes]:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise UnsupportedInputError(
            f"input file does not exist: {path}",
            context={"path": str(path)},
        ) from exc
    if not resolved.is_file():
        raise UnsupportedInputError(
            f"input path is not a regular file: {resolved}",
            context={"path": str(resolved)},
        )
    size_bytes = resolved.stat().st_size
    if size_bytes > max_bytes:
        raise FileTooLargeError(
            f"input file is {size_bytes} bytes; limit is {max_bytes} bytes",
            context={
                "path": str(resolved),
                "size_bytes": size_bytes,
                "max_bytes": max_bytes,
            },
        )
    return resolved, resolved.read_bytes()
