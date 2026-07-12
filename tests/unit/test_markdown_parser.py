from pathlib import Path

from aurora.collector import LocalFileCollector
from aurora.core.models.enums import ContentUnitType
from aurora.parser import MarkdownParser


def test_markdown_minimum_block_types_and_locators(tmp_path: Path):
    path = tmp_path / "sample.md"
    path.write_text(
        "# 标题\n\n正文第一行\n正文第二行\n\n"
        "- 条目一\n2. 条目二\n\n> 引用一\n> 引用二\n\n"
        "```python\nprint('x')\n```\n",
        encoding="utf-8",
    )
    parsed = MarkdownParser().parse(
        LocalFileCollector().collect(path, max_bytes=10000)
    )
    assert parsed.inferred_title == "标题"
    assert [unit.unit_type for unit in parsed.units] == [
        ContentUnitType.HEADING,
        ContentUnitType.PARAGRAPH,
        ContentUnitType.LIST_ITEM,
        ContentUnitType.LIST_ITEM,
        ContentUnitType.QUOTE,
        ContentUnitType.CODE_BLOCK,
    ]
    assert [unit.sequence_no for unit in parsed.units] == list(range(6))
    assert parsed.units[1].locator.line_start == 3
    assert parsed.units[1].locator.heading_path == ["标题"]
    assert parsed.units[-1].text == "print('x')"


def test_markdown_parsing_is_deterministic(tmp_path: Path):
    path = tmp_path / "same.md"
    path.write_text("## A\n\nText", encoding="utf-8")
    collected = LocalFileCollector().collect(path, max_bytes=1000)
    first = MarkdownParser().parse(collected)
    second = MarkdownParser().parse(collected)
    assert first == second


def test_unclosed_code_fence_is_preserved(tmp_path: Path):
    path = tmp_path / "code.md"
    path.write_text("```\nabc", encoding="utf-8")
    parsed = MarkdownParser().parse(
        LocalFileCollector().collect(path, max_bytes=1000)
    )
    assert len(parsed.units) == 1
    assert parsed.units[0].unit_type == ContentUnitType.CODE_BLOCK
    assert parsed.units[0].text == "abc"


def test_skipped_heading_levels_do_not_create_empty_path_entries(tmp_path: Path):
    path = tmp_path / "heading.md"
    path.write_text("## Nested\n\nText", encoding="utf-8")
    parsed = MarkdownParser().parse(
        LocalFileCollector().collect(path, max_bytes=1000)
    )
    assert parsed.units[0].locator.heading_path == ["Nested"]
    assert parsed.units[1].locator.heading_path == ["Nested"]


def test_empty_code_block_does_not_create_invalid_content_unit(tmp_path: Path):
    path = tmp_path / "empty-code.md"
    path.write_text("# Title\n\n```\n```", encoding="utf-8")
    parsed = MarkdownParser().parse(
        LocalFileCollector().collect(path, max_bytes=1000)
    )
    assert [unit.unit_type for unit in parsed.units] == [ContentUnitType.HEADING]
