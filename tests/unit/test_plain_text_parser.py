from pathlib import Path

from aurora.collector import LocalFileCollector
from aurora.parser import PlainTextParser


def test_plain_text_splits_on_blank_lines(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("one\nline\n\nsecond\n\n\nthird", encoding="utf-8")
    parsed = PlainTextParser().parse(
        LocalFileCollector().collect(path, max_bytes=1000)
    )
    assert [unit.text for unit in parsed.units] == [
        "one\nline",
        "second",
        "third",
    ]
    assert [unit.locator.paragraph_no for unit in parsed.units] == [1, 2, 3]
