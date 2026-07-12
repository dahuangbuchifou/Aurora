from pathlib import Path

from aurora.core.models.enums import ContentUnitType, SourceType
from aurora.ingestion.hashing import (
    content_hash_for_text,
    normalize_identity_text,
    normalize_text,
    stable_id,
)
from aurora.ingestion.identity import (
    canonical_source_key,
    content_unit_object_id,
    document_dedupe_key,
    document_object_id,
    document_series_key,
    normalize_http_url,
    source_object_id,
)


def test_text_hash_normalizes_bom_and_line_endings():
    left = "\ufeffa\r\nb\rc"
    right = "a\nb\nc"
    assert normalize_text(left) == right
    assert content_hash_for_text(left) == content_hash_for_text(right)
    assert content_hash_for_text(right) == content_hash_for_text(right + "\n\n")


def test_identity_text_and_ids_are_stable():
    assert normalize_identity_text("  中芯  国际 ") == "中芯 国际"
    assert stable_id("x", "a", 1) == stable_id("x", "a", 1)
    assert stable_id("x", "a", 1) != stable_id("x", "a", 2)


def test_source_identity_is_document_independent():
    key = canonical_source_key(
        source_name="SMIC",
        source_type=SourceType.OFFICIAL_WEBSITE,
        homepage_url="HTTPS://WWW.SMICS.COM/",
    )
    assert key == "url:https://www.smics.com/"
    source_id = source_object_id(
        workspace_id="default",
        source_type=SourceType.OFFICIAL_WEBSITE,
        canonical_key=key,
    )
    assert source_id.startswith("src_")


def test_explicit_source_key_has_priority():
    key = canonical_source_key(
        source_name="Different Name",
        source_type=SourceType.LOCAL_FILE,
        explicit_key="  My Publisher ",
        homepage_url="https://example.com",
    )
    assert key == "key:my publisher"


def test_document_and_content_unit_ids_are_deterministic(tmp_path: Path):
    dedupe = document_dedupe_key(
        source_id="src_1",
        content_hash="abc",
        parser_name="markdown",
        parser_version="1.0.0",
    )
    series = document_series_key(
        source_id="src_1",
        input_uri=(tmp_path / "a.md").resolve().as_uri(),
        idempotency_key=None,
    )
    doc_id = document_object_id(
        dedupe_key=dedupe,
        series_key=series,
        version_no=1,
    )
    assert doc_id == document_object_id(
        dedupe_key=dedupe,
        series_key=series,
        version_no=1,
    )
    unit_id = content_unit_object_id(
        document_id=doc_id,
        unit_type=ContentUnitType.PARAGRAPH,
        sequence_no=0,
        normalized_text_hash="def",
    )
    assert unit_id.startswith("cu_")


def test_http_url_normalization_removes_default_port_and_fragment():
    assert (
        normalize_http_url("HTTPS://Example.COM:443/research/#part")
        == "https://example.com/research"
    )
