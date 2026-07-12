import json
from pathlib import Path

import pytest

from aurora.collector import LocalFileCollector
from aurora.ingestion.errors import InvalidStructuredSegmentsError
from aurora.parser import StructuredSegmentsParser


def _manifest():
    return {
        "schema_version": "1.0",
        "workspace_id": "research",
        "source": {
            "name": "SMIC",
            "source_type": "official_website",
            "canonical_key": "smic-official",
        },
        "document": {
            "title": "Sample",
            "document_type": "text",
            "language": "zh-CN",
        },
        "segments": [
            {
                "sequence_no": 0,
                "unit_type": "paragraph",
                "text": "A",
                "locator": {"paragraph_no": 1},
            },
            {
                "sequence_no": 1,
                "unit_type": "quote",
                "text": "B",
                "locator": {"paragraph_no": 2},
                "speaker": "analyst",
            },
        ],
    }


def test_structured_segments_parse_and_canonical_hash(tmp_path: Path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    payload = _manifest()
    first_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    second_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4, sort_keys=True),
        encoding="utf-8",
    )
    parser = StructuredSegmentsParser()
    first = parser.parse(LocalFileCollector().collect(first_path, max_bytes=10000))
    second = parser.parse(LocalFileCollector().collect(second_path, max_bytes=10000))
    assert first.content_hash == second.content_hash
    assert first.structured_manifest.workspace_id == "research"
    assert first.units[1].speaker == "analyst"


def test_structured_segments_require_contiguous_sequences(tmp_path: Path):
    payload = _manifest()
    payload["segments"][1]["sequence_no"] = 3
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InvalidStructuredSegmentsError):
        StructuredSegmentsParser().parse(
            LocalFileCollector().collect(path, max_bytes=10000)
        )


def test_invalid_json_is_wrapped(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(InvalidStructuredSegmentsError):
        StructuredSegmentsParser().parse(
            LocalFileCollector().collect(path, max_bytes=10000)
        )
