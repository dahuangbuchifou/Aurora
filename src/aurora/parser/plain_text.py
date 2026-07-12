"""Deterministic plain-text paragraph parser."""

from __future__ import annotations

from aurora.collector.base import CollectedInput
from aurora.core.models.common import SourceLocator
from aurora.core.models.enums import ContentUnitType
from aurora.ingestion.contracts import ParserDescriptor
from aurora.ingestion.errors import EmptyInputError
from aurora.ingestion.hashing import content_hash_for_text

from .base import ParsedDocument, ParsedUnit, Parser


class PlainTextParser(Parser):
    name = "plain_text"
    version = "1.0.0"

    def parse(self, collected: CollectedInput) -> ParsedDocument:
        lines = collected.text.split("\n")
        units: list[ParsedUnit] = []
        buffer: list[str] = []
        start_line: int | None = None

        def flush(end_line: int) -> None:
            nonlocal buffer, start_line
            if not buffer or start_line is None:
                buffer = []
                start_line = None
                return
            text = "\n".join(buffer)
            if text.strip():
                units.append(
                    ParsedUnit(
                        sequence_no=len(units),
                        unit_type=ContentUnitType.PARAGRAPH,
                        text=text,
                        locator=SourceLocator(
                            line_start=start_line,
                            line_end=end_line,
                            paragraph_no=len(units) + 1,
                        ),
                    )
                )
            buffer = []
            start_line = None

        for index, line in enumerate(lines, start=1):
            if line.strip():
                if start_line is None:
                    start_line = index
                buffer.append(line)
            else:
                flush(index - 1)
        flush(len(lines))

        if not units:
            raise EmptyInputError("plain text produced no content units")

        return ParsedDocument(
            parser=ParserDescriptor(name=self.name, version=self.version),
            content_hash=content_hash_for_text(collected.text),
            units=tuple(units),
            inferred_title=None,
        )
