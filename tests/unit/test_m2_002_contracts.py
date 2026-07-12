from pathlib import Path

import pytest
from pydantic import ValidationError

from aurora.core.models.enums import SourceType
from aurora.ingestion.contracts import (
    IngestionInputType,
    IngestionRequest,
    PdfTableMode,
)
from aurora.ingestion.hashing import parser_config_hash
from aurora.ingestion.identity import document_dedupe_key


def test_url_request_requires_url_and_forbids_path(tmp_path: Path):
    request = IngestionRequest(
        url="https://example.com/article",
        input_type=IngestionInputType.URL,
        source_name="Example",
        source_type=SourceType.OFFICIAL_WEBSITE,
    )
    assert request.path is None
    with pytest.raises(ValidationError):
        IngestionRequest(
            path=tmp_path / "x.html",
            url="https://example.com",
            input_type=IngestionInputType.URL,
            source_name="Example",
            source_type=SourceType.OFFICIAL_WEBSITE,
        )


def test_pdf_options_are_rejected_for_non_pdf(tmp_path: Path):
    with pytest.raises(ValidationError):
        IngestionRequest(
            path=tmp_path / "x.txt",
            input_type=IngestionInputType.TEXT,
            source_name="Local",
            source_type=SourceType.LOCAL_FILE,
            page_selection="1-2",
        )


def test_pdf_request_accepts_page_and_table_options(tmp_path: Path):
    request = IngestionRequest(
        path=tmp_path / "x.pdf",
        input_type=IngestionInputType.PDF,
        source_name="Report",
        source_type=SourceType.LOCAL_FILE,
        page_selection="1-2",
        table_mode=PdfTableMode.OFF,
        max_pages=20,
    )
    assert request.page_selection == "1-2"
    assert request.table_mode == PdfTableMode.OFF


def test_parser_config_hash_is_order_independent():
    assert parser_config_hash({"b": 2, "a": 1}) == parser_config_hash(
        {"a": 1, "b": 2}
    )


def test_parser_config_hash_changes_document_identity():
    left = document_dedupe_key(
        source_id="src",
        content_hash="content",
        parser_name="pdf",
        parser_version="1",
        parser_config_hash="config-a",
    )
    right = document_dedupe_key(
        source_id="src",
        content_hash="content",
        parser_name="pdf",
        parser_version="1",
        parser_config_hash="config-b",
    )
    assert left != right
