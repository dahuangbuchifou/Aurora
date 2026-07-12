"""Small deterministic Markdown block parser for M2-001.

It deliberately covers only the frozen MVP block types: headings, paragraphs,
list items, quotes and fenced code blocks. It is not a full CommonMark parser.
"""

from __future__ import annotations

import re

from aurora.collector.base import CollectedInput
from aurora.core.models.common import SourceLocator
from aurora.core.models.enums import ContentUnitType
from aurora.ingestion.contracts import ParserDescriptor
from aurora.ingestion.errors import EmptyInputError
from aurora.ingestion.hashing import content_hash_for_text

from .base import ParsedDocument, ParsedUnit, Parser

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST_ITEM = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+(.+?)\s*$")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_QUOTE = re.compile(r"^\s*>\s?(.*)$")


class MarkdownParser(Parser):
    name = "markdown"
    version = "1.0.0"

    def parse(self, collected: CollectedInput) -> ParsedDocument:
        lines = collected.text.split("\n")
        units: list[ParsedUnit] = []
        heading_path: list[str] = []
        inferred_title: str | None = None
        paragraph_lines: list[str] = []
        paragraph_start: int | None = None
        quote_lines: list[str] = []
        quote_start: int | None = None
        in_fence = False
        fence_token = ""
        code_lines: list[str] = []
        code_start: int | None = None

        def add_unit(
            unit_type: ContentUnitType,
            text: str,
            start: int,
            end: int,
            *,
            path: list[str] | None = None,
        ) -> None:
            if not text.strip():
                return
            units.append(
                ParsedUnit(
                    sequence_no=len(units),
                    unit_type=unit_type,
                    text=text,
                    locator=SourceLocator(
                        line_start=start,
                        line_end=end,
                        block_no=len(units) + 1,
                        heading_path=list(path if path is not None else heading_path),
                    ),
                )
            )

        def flush_paragraph(end: int) -> None:
            nonlocal paragraph_lines, paragraph_start
            if paragraph_lines and paragraph_start is not None:
                add_unit(
                    ContentUnitType.PARAGRAPH,
                    "\n".join(paragraph_lines),
                    paragraph_start,
                    end,
                )
            paragraph_lines = []
            paragraph_start = None

        def flush_quote(end: int) -> None:
            nonlocal quote_lines, quote_start
            if quote_lines and quote_start is not None:
                add_unit(
                    ContentUnitType.QUOTE,
                    "\n".join(quote_lines),
                    quote_start,
                    end,
                )
            quote_lines = []
            quote_start = None

        for line_no, line in enumerate(lines, start=1):
            if in_fence:
                if line.lstrip().startswith(fence_token):
                    add_unit(
                        ContentUnitType.CODE_BLOCK,
                        "\n".join(code_lines),
                        code_start or line_no,
                        line_no,
                    )
                    in_fence = False
                    fence_token = ""
                    code_lines = []
                    code_start = None
                else:
                    code_lines.append(line)
                continue

            fence_match = _FENCE.match(line)
            if fence_match:
                flush_paragraph(line_no - 1)
                flush_quote(line_no - 1)
                in_fence = True
                fence_token = fence_match.group(1)[0] * len(fence_match.group(1))
                code_start = line_no
                code_lines = []
                continue

            heading_match = _HEADING.match(line)
            if heading_match:
                flush_paragraph(line_no - 1)
                flush_quote(line_no - 1)
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                heading_path = heading_path[: level - 1]
                heading_path.append(title)
                if inferred_title is None:
                    inferred_title = title
                add_unit(
                    ContentUnitType.HEADING,
                    title,
                    line_no,
                    line_no,
                    path=heading_path,
                )
                continue

            quote_match = _QUOTE.match(line)
            if quote_match:
                flush_paragraph(line_no - 1)
                if quote_start is None:
                    quote_start = line_no
                quote_lines.append(quote_match.group(1))
                continue
            flush_quote(line_no - 1)

            list_match = _LIST_ITEM.match(line)
            if list_match:
                flush_paragraph(line_no - 1)
                add_unit(
                    ContentUnitType.LIST_ITEM,
                    list_match.group(1),
                    line_no,
                    line_no,
                )
                continue

            if not line.strip():
                flush_paragraph(line_no - 1)
                continue

            if paragraph_start is None:
                paragraph_start = line_no
            paragraph_lines.append(line)

        if in_fence and code_start is not None:
            add_unit(
                ContentUnitType.CODE_BLOCK,
                "\n".join(code_lines),
                code_start,
                len(lines),
            )
        flush_quote(len(lines))
        flush_paragraph(len(lines))

        if not units:
            raise EmptyInputError("markdown produced no content units")

        return ParsedDocument(
            parser=ParserDescriptor(name=self.name, version=self.version),
            content_hash=content_hash_for_text(collected.text),
            units=tuple(units),
            inferred_title=inferred_title,
        )
