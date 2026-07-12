from pathlib import Path

import pytest

from aurora.collector import LocalFileCollector
from aurora.ingestion.errors import (
    EmptyInputError,
    FileTooLargeError,
    InvalidEncodingError,
    UnsupportedInputError,
)


def test_collect_utf8_and_normalize_line_endings(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_bytes(b"\xef\xbb\xbfhello\r\nworld")
    collected = LocalFileCollector().collect(path, max_bytes=100)
    assert collected.text == "hello\nworld"
    assert collected.input_uri.startswith("file://")
    assert collected.size_bytes == path.stat().st_size


def test_file_too_large_is_checked_before_read(tmp_path: Path):
    path = tmp_path / "large.txt"
    path.write_text("12345", encoding="utf-8")
    with pytest.raises(FileTooLargeError) as error:
        LocalFileCollector().collect(path, max_bytes=4)
    assert error.value.code == "INGEST_FILE_TOO_LARGE"


@pytest.mark.parametrize(
    ("name", "data", "error_type"),
    [
        ("empty.txt", b" \n\t", EmptyInputError),
        ("binary.txt", b"a\x00b", UnsupportedInputError),
        ("bad.txt", b"\xff\xfe", InvalidEncodingError),
    ],
)
def test_invalid_file_content(tmp_path: Path, name: str, data: bytes, error_type):
    path = tmp_path / name
    path.write_bytes(data)
    with pytest.raises(error_type):
        LocalFileCollector().collect(path, max_bytes=100)


def test_missing_and_directory_paths_are_rejected(tmp_path: Path):
    collector = LocalFileCollector()
    with pytest.raises(UnsupportedInputError):
        collector.collect(tmp_path / "missing.txt", max_bytes=100)
    with pytest.raises(UnsupportedInputError):
        collector.collect(tmp_path, max_bytes=100)
