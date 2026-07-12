from pathlib import Path

import pytest
from pydantic import ValidationError

from aurora.core.models.enums import SourceType
from aurora.ingestion.contracts import (
    IngestionInputType,
    IngestionRequest,
    IngestionResult,
    ParserDescriptor,
    StructuredSegmentsManifest,
)


def test_file_request_requires_source_metadata(tmp_path: Path):
    with pytest.raises(ValidationError):
        IngestionRequest(
            path=tmp_path / "a.md",
            input_type=IngestionInputType.MARKDOWN,
        )


def test_structured_request_can_take_metadata_from_manifest(tmp_path: Path):
    request = IngestionRequest(
        path=tmp_path / "a.json",
        input_type=IngestionInputType.STRUCTURED_SEGMENTS,
    )
    assert request.source_name is None


def test_ingestion_result_count_is_consistent():
    with pytest.raises(ValidationError):
        IngestionResult(
            processing_run_id="run_1",
            source_id="src_1",
            document_id="doc_1",
            content_unit_ids=["cu_1"],
            content_unit_count=0,
            content_hash="abc",
            idempotency_key="key",
            parser=ParserDescriptor(name="text", version="1"),
        )


def test_structured_manifest_requires_zero_based_order():
    with pytest.raises(ValidationError):
        StructuredSegmentsManifest.model_validate(
            {
                "source": {"name": "s", "source_type": "local_file"},
                "document": {"title": "d"},
                "segments": [
                    {
                        "sequence_no": 1,
                        "unit_type": "paragraph",
                        "text": "x",
                        "locator": {"paragraph_no": 1},
                    }
                ],
            }
        )
