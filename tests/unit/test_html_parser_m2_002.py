from pathlib import Path

import pytest

from aurora.collector import LocalFileCollector
from aurora.core.models.enums import ContentUnitType, ParseStatus
from aurora.ingestion.errors import WebEmptyMainContentError
from aurora.parser import HtmlDocumentParser


FIXTURE = Path(__file__).parents[1] / "fixtures" / "m2_002" / "case_a_web.html"


def test_html_parser_extracts_supported_blocks_and_locators():
    collected = LocalFileCollector().collect(FIXTURE, max_bytes=1024 * 1024)
    parsed = HtmlDocumentParser().parse(collected)

    assert parsed.inferred_title == "中芯国际2025年度业绩摘要"
    assert parsed.parse_status == ParseStatus.PARSED
    assert parsed.raw_content_hash
    assert parsed.parser_config_hash != "default"
    assert parsed.metrics["table_count"] == 1
    assert parsed.metrics["table_row_count"] == 3

    types = [unit.unit_type for unit in parsed.units]
    assert ContentUnitType.HEADING in types
    assert ContentUnitType.PARAGRAPH in types
    assert ContentUnitType.TABLE in types
    assert ContentUnitType.TABLE_ROW in types
    assert ContentUnitType.QUOTE in types
    assert ContentUnitType.CODE_BLOCK in types
    assert all("导航内容" not in unit.text for unit in parsed.units)
    assert all("版权信息" not in unit.text for unit in parsed.units)
    assert all(unit.locator.css_selector for unit in parsed.units)
    assert all(unit.locator.xpath for unit in parsed.units)

    table = next(unit for unit in parsed.units if unit.unit_type == ContentUnitType.TABLE)
    rows = [
        unit
        for unit in parsed.units
        if unit.unit_type == ContentUnitType.TABLE_ROW
    ]
    assert all(row.parent_sequence_no == table.sequence_no for row in rows)


def test_html_selector_changes_parser_config_hash(tmp_path: Path):
    path = tmp_path / "article.html"
    path.write_text(
        "<html><body><main><p>Main</p></main><article><p>Article</p></article></body></html>",
        encoding="utf-8",
    )
    collected = LocalFileCollector().collect(path, max_bytes=1024)
    main = HtmlDocumentParser(content_selector="main").parse(collected)
    article = HtmlDocumentParser(content_selector="article").parse(collected)
    assert main.parser_config_hash != article.parser_config_hash
    assert main.content_hash != article.content_hash
    assert main.units[0].text == "Main"
    assert article.units[0].text == "Article"


def test_html_missing_selector_falls_back_and_is_partial(tmp_path: Path):
    path = tmp_path / "fallback.html"
    path.write_text("<html><body><p>Fallback</p></body></html>", encoding="utf-8")
    collected = LocalFileCollector().collect(path, max_bytes=1024)
    parsed = HtmlDocumentParser(content_selector="#missing").parse(collected)
    assert parsed.parse_status == ParseStatus.PARTIALLY_PARSED
    assert "HTML_SELECTOR_NOT_FOUND" in parsed.warnings
    assert "HTML_FALLBACK_TO_BODY" in parsed.warnings


def test_html_semantic_hash_ignores_script_noise(tmp_path: Path):
    one = tmp_path / "one.html"
    two = tmp_path / "two.html"
    one.write_text(
        "<html><body><article><p>Stable</p><script>id=1</script></article></body></html>",
        encoding="utf-8",
    )
    two.write_text(
        "<html><body><article><p>Stable</p><script>id=999</script></article></body></html>",
        encoding="utf-8",
    )
    parser = HtmlDocumentParser()
    left = parser.parse(LocalFileCollector().collect(one, max_bytes=1024))
    right = parser.parse(LocalFileCollector().collect(two, max_bytes=1024))
    assert left.raw_content_hash != right.raw_content_hash
    assert left.content_hash == right.content_hash


def test_html_empty_supported_content_fails(tmp_path: Path):
    path = tmp_path / "empty.html"
    path.write_text("<html><body><script>x=1</script></body></html>", encoding="utf-8")
    with pytest.raises(WebEmptyMainContentError):
        HtmlDocumentParser().parse(
            LocalFileCollector().collect(path, max_bytes=1024)
        )


def test_html_invalid_selector_is_rejected(tmp_path: Path):
    from aurora.ingestion.errors import HtmlParseError

    path = tmp_path / "bad-selector.html"
    path.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    with pytest.raises(HtmlParseError):
        HtmlDocumentParser(content_selector="[").parse(
            LocalFileCollector().collect(path, max_bytes=1024)
        )


def test_html_main_root_and_id_locator_and_metadata(tmp_path: Path):
    path = tmp_path / "main.html"
    path.write_text(
        '<html lang="en"><head><meta name="author" content="A">'
        '<link rel="canonical" href="https://example.com/a"></head>'
        '<body><main id="content"><h1>Title</h1><p>Body</p></main></body></html>',
        encoding="utf-8",
    )
    parsed = HtmlDocumentParser().parse(
        LocalFileCollector().collect(path, max_bytes=4096)
    )
    assert parsed.inferred_title == "Title"
    assert parsed.document_metadata["author"] == "A"
    assert parsed.document_metadata["canonical_url"] == "https://example.com/a"
    assert parsed.document_metadata["language"] == "en"
    assert parsed.units[0].locator.css_selector.startswith("main#content")


def test_html_table_without_rows_falls_back_to_text(tmp_path: Path):
    path = tmp_path / "table.html"
    path.write_text(
        "<html><body><article><table><caption>Only text</caption></table></article></body></html>",
        encoding="utf-8",
    )
    parsed = HtmlDocumentParser().parse(
        LocalFileCollector().collect(path, max_bytes=4096)
    )
    table = next(unit for unit in parsed.units if unit.unit_type == ContentUnitType.TABLE)
    assert "Only text" in table.text


def test_nested_paragraph_is_not_duplicated(tmp_path: Path):
    path = tmp_path / "nested.html"
    path.write_text(
        "<html><body><article><blockquote><p>Nested quote</p></blockquote></article></body></html>",
        encoding="utf-8",
    )
    parsed = HtmlDocumentParser().parse(
        LocalFileCollector().collect(path, max_bytes=4096)
    )
    assert len(parsed.units) == 1
    assert parsed.units[0].unit_type == ContentUnitType.QUOTE
