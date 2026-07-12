from pathlib import Path

import pytest

from aurora.collector import LocalBinaryFileCollector
from aurora.core.models.enums import ContentUnitType, ParseStatus
from aurora.ingestion.contracts import PdfTableMode
from aurora.ingestion.errors import (
    PdfInvalidPageRangeError,
    PdfNoExtractableTextError,
    PdfTooManyPagesError,
)
from aurora.parser import PdfDocumentParser, parse_page_selection


FIXTURES = Path(__file__).parents[1] / "fixtures" / "m2_002"


def _collect(name: str):
    return LocalBinaryFileCollector().collect(
        FIXTURES / name, max_bytes=10 * 1024 * 1024
    )


def test_page_selection_parser():
    assert parse_page_selection("1,2,4-5", 5) == (1, 2, 4, 5)
    assert parse_page_selection(None, 3) == (1, 2, 3)
    with pytest.raises(PdfInvalidPageRangeError):
        parse_page_selection("2-1", 3)
    with pytest.raises(PdfInvalidPageRangeError):
        parse_page_selection("4", 3)


def test_pdf_parser_extracts_page_text_and_table():
    parsed = PdfDocumentParser().parse(_collect("case_c_report.pdf"))
    assert parsed.parse_status in {ParseStatus.PARSED, ParseStatus.PARTIALLY_PARSED}
    assert parsed.metrics["page_count"] == 2
    assert parsed.metrics["selected_page_count"] == 2
    assert parsed.raw_content_hash
    assert parsed.parser_config_hash != "default"
    assert any(unit.locator.page_no == 1 for unit in parsed.units)
    assert any(unit.locator.page_no == 2 for unit in parsed.units)
    assert any(unit.unit_type == ContentUnitType.TABLE for unit in parsed.units)
    rows = [unit for unit in parsed.units if unit.unit_type == ContentUnitType.TABLE_ROW]
    assert rows
    assert all(row.parent_sequence_no is not None for row in rows)


def test_pdf_page_range_is_partial_and_changes_config_hash():
    collected = _collect("case_c_report.pdf")
    page_one = PdfDocumentParser(page_selection="1").parse(collected)
    page_two = PdfDocumentParser(page_selection="2").parse(collected)
    assert page_one.parse_status == ParseStatus.PARTIALLY_PARSED
    assert page_two.parse_status == ParseStatus.PARTIALLY_PARSED
    assert page_one.parser_config_hash != page_two.parser_config_hash
    assert {unit.locator.page_no for unit in page_one.units} == {1}
    assert {unit.locator.page_no for unit in page_two.units} == {2}


def test_pdf_table_mode_changes_config_hash():
    collected = _collect("case_c_report.pdf")
    on = PdfDocumentParser(table_mode=PdfTableMode.BEST_EFFORT).parse(collected)
    off = PdfDocumentParser(table_mode=PdfTableMode.OFF).parse(collected)
    assert on.parser_config_hash != off.parser_config_hash
    assert any(unit.unit_type == ContentUnitType.TABLE for unit in on.units)
    assert all(unit.unit_type != ContentUnitType.TABLE for unit in off.units)


def test_pdf_max_pages_limit_is_enforced():
    with pytest.raises(PdfTooManyPagesError):
        PdfDocumentParser(max_pages=1).parse(_collect("case_c_report.pdf"))


def test_blank_pdf_has_no_extractable_units():
    with pytest.raises(PdfNoExtractableTextError):
        PdfDocumentParser().parse(_collect("blank.pdf"))


def test_pdf_rejects_non_pdf_bytes(tmp_path: Path):
    from aurora.collector.base import CollectedInput
    from aurora.ingestion.errors import PdfParseError

    collected = CollectedInput(
        path=tmp_path / "x.pdf",
        input_uri=(tmp_path / "x.pdf").resolve().as_uri(),
        file_name="x.pdf",
        suffix=".pdf",
        size_bytes=4,
        text="",
        raw_bytes=b"nope",
    )
    with pytest.raises(PdfParseError):
        PdfDocumentParser().parse(collected)


def test_pdf_parser_marks_page_without_text_partial(monkeypatch):
    from contextlib import nullcontext
    from aurora.collector.base import CollectedInput

    class FakePage:
        def extract_tables(self):
            return []

        def extract_text(self):
            return ""

    class FakePdf:
        pages = [FakePage(), FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("aurora.parser.pdf.pdfplumber.open", lambda value: FakePdf())
    collected = CollectedInput(
        path=None,
        input_uri="file:///fake.pdf",
        file_name="fake.pdf",
        suffix=".pdf",
        size_bytes=10,
        text="",
        raw_bytes=b"%PDF-fake",
    )
    with pytest.raises(PdfNoExtractableTextError):
        PdfDocumentParser().parse(collected)


def test_pdf_table_failure_keeps_text_and_warns(monkeypatch):
    from aurora.collector.base import CollectedInput

    class FakePage:
        def extract_tables(self):
            raise RuntimeError("table")

        def extract_text(self):
            return "1 Heading\nBody"

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("aurora.parser.pdf.pdfplumber.open", lambda value: FakePdf())
    collected = CollectedInput(
        path=None,
        input_uri="file:///fake.pdf",
        file_name="fake.pdf",
        suffix=".pdf",
        size_bytes=10,
        text="",
        raw_bytes=b"%PDF-fake",
    )
    parsed = PdfDocumentParser().parse(collected)
    assert parsed.parse_status == ParseStatus.PARTIALLY_PARSED
    assert "PDF_TABLE_EXTRACTION_PARTIAL" in parsed.warnings
    assert parsed.units[0].unit_type == ContentUnitType.HEADING


def test_page_selection_invalid_token_and_empty_document():
    assert parse_page_selection(None, 0) == ()
    with pytest.raises(PdfInvalidPageRangeError):
        parse_page_selection("x", 2)


def test_pdf_encrypted_and_generic_open_errors_are_classified(monkeypatch):
    from aurora.collector.base import CollectedInput
    from aurora.ingestion.errors import PdfEncryptedError, PdfParseError

    collected = CollectedInput(
        path=None,
        input_uri="file:///fake.pdf",
        file_name="fake.pdf",
        suffix=".pdf",
        size_bytes=10,
        text="",
        raw_bytes=b"%PDF-fake",
    )
    monkeypatch.setattr(
        "aurora.parser.pdf.pdfplumber.open",
        lambda value: (_ for _ in ()).throw(RuntimeError("password required")),
    )
    with pytest.raises(PdfEncryptedError):
        PdfDocumentParser().parse(collected)

    monkeypatch.setattr(
        "aurora.parser.pdf.pdfplumber.open",
        lambda value: (_ for _ in ()).throw(RuntimeError("broken xref")),
    )
    with pytest.raises(PdfParseError):
        PdfDocumentParser().parse(collected)


def test_pdf_empty_table_is_skipped_and_text_survives(monkeypatch):
    from aurora.collector.base import CollectedInput

    class FakePage:
        def extract_tables(self):
            return [[[None, ""]]]

        def extract_text(self):
            return "Body"

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("aurora.parser.pdf.pdfplumber.open", lambda value: FakePdf())
    collected = CollectedInput(
        path=None,
        input_uri="file:///fake.pdf",
        file_name="fake.pdf",
        suffix=".pdf",
        size_bytes=10,
        text="",
        raw_bytes=b"%PDF-fake",
    )
    parsed = PdfDocumentParser().parse(collected)
    assert [unit.text for unit in parsed.units] == ["Body"]


def test_pdf_text_failure_with_table_is_partial(monkeypatch):
    from aurora.collector.base import CollectedInput

    class FakePage:
        def extract_tables(self):
            return [[['A', 'B']]]

        def extract_text(self):
            raise RuntimeError("layout")

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("aurora.parser.pdf.pdfplumber.open", lambda value: FakePdf())
    collected = CollectedInput(
        path=None,
        input_uri="file:///fake.pdf",
        file_name="fake.pdf",
        suffix=".pdf",
        size_bytes=10,
        text="",
        raw_bytes=b"%PDF-fake",
    )
    parsed = PdfDocumentParser().parse(collected)
    assert parsed.parse_status == ParseStatus.PARTIALLY_PARSED
    assert "PDF_READING_ORDER_UNCERTAIN" in parsed.warnings
    assert parsed.metrics["pages_without_text"] == 1


def test_pdf_helpers_cover_long_heading_and_null_cell():
    from aurora.parser.pdf import _clean_cell, _looks_like_heading

    assert _clean_cell(None) == ""
    assert _looks_like_heading("x" * 81) is False
