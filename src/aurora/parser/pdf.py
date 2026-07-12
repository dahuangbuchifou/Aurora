"""Machine-generated PDF parser with page locators and best-effort tables."""

from __future__ import annotations

import io
import re
from typing import Any

import pdfplumber

from aurora.collector.base import CollectedInput
from aurora.core.models.common import SourceLocator
from aurora.core.models.enums import ContentUnitType, ParseStatus
from aurora.ingestion.contracts import ParserDescriptor, PdfTableMode
from aurora.ingestion.errors import (
    PdfEncryptedError,
    PdfInvalidPageRangeError,
    PdfNoExtractableTextError,
    PdfParseError,
    PdfTooManyPagesError,
)
from aurora.ingestion.hashing import semantic_units_hash, sha256_hex

from .base import ParsedDocument, ParsedUnit, Parser
from .config import ParserConfig

_WS = re.compile(r"\s+")
_PAGE_PART = re.compile(r"^(\d+)(?:-(\d+))?$")


def parse_page_selection(value: str | None, page_count: int) -> tuple[int, ...]:
    """Parse 1-based page expressions such as ``1,3,5-7``."""

    if page_count < 1:
        return ()
    if value is None or not value.strip():
        return tuple(range(1, page_count + 1))
    selected: list[int] = []
    seen: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        match = _PAGE_PART.fullmatch(part)
        if not match:
            raise PdfInvalidPageRangeError(
                "invalid PDF page selection",
                context={"page_selection": value, "invalid_part": part},
            )
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < start or end > page_count:
            raise PdfInvalidPageRangeError(
                "PDF page selection is outside the document",
                context={
                    "page_selection": value,
                    "page_count": page_count,
                    "invalid_part": part,
                },
            )
        for page_no in range(start, end + 1):
            if page_no not in seen:
                selected.append(page_no)
                seen.add(page_no)
    return tuple(selected)


class PdfDocumentParser(Parser):
    name = "pdf"
    version = "1.0.0"

    def __init__(
        self,
        *,
        page_selection: str | None = None,
        table_mode: PdfTableMode = PdfTableMode.BEST_EFFORT,
        max_pages: int = 500,
    ) -> None:
        self.page_selection = page_selection
        self.table_mode = table_mode
        self.max_pages = max_pages

    def parse(self, collected: CollectedInput) -> ParsedDocument:
        raw = collected.raw_bytes
        if not raw.startswith(b"%PDF"):
            raise PdfParseError(
                "input is not a PDF file",
                context={"file_name": collected.file_name},
            )
        warnings: list[str] = []
        metrics: dict[str, Any] = {
            "input_bytes": collected.size_bytes,
            "pages_with_text": 0,
            "pages_without_text": 0,
            "table_count": 0,
            "table_row_count": 0,
        }
        units: list[ParsedUnit] = []
        try:
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                page_count = len(pdf.pages)
                metrics["page_count"] = page_count
                if page_count > self.max_pages:
                    raise PdfTooManyPagesError(
                        "PDF exceeds configured page limit",
                        context={"page_count": page_count, "max_pages": self.max_pages},
                    )
                selected = parse_page_selection(self.page_selection, page_count)
                metrics["selected_page_count"] = len(selected)
                if len(selected) != page_count:
                    warnings.append("PDF_PAGE_RANGE_SELECTED")
                for page_no in selected:
                    page = pdf.pages[page_no - 1]
                    self._extract_page(page, page_no, units, warnings, metrics)
        except PdfTooManyPagesError:
            raise
        except PdfInvalidPageRangeError:
            raise
        except Exception as exc:
            message = str(exc).lower()
            if "password" in message or "encrypted" in message:
                raise PdfEncryptedError(
                    "encrypted PDF is not supported",
                    context={"file_name": collected.file_name},
                ) from exc
            raise PdfParseError(
                "PDF parsing failed",
                context={
                    "file_name": collected.file_name,
                    "exception_type": type(exc).__name__,
                },
            ) from exc

        if not units:
            raise PdfNoExtractableTextError(
                "PDF contains no extractable text or table units",
                context={"file_name": collected.file_name},
            )

        config = ParserConfig(
            name=self.name,
            version=self.version,
            options={
                "page_selection": self.page_selection,
                "table_mode": self.table_mode.value,
                "max_pages": self.max_pages,
                "text_strategy": "line_v1",
                "table_strategy": "pdfplumber_default_v1",
            },
        )
        semantic = semantic_units_hash(
            [
                {
                    "sequence_no": unit.sequence_no,
                    "unit_type": unit.unit_type.value,
                    "text": unit.text,
                    "page_no": unit.locator.page_no,
                    "row_no": unit.locator.row_no,
                    "parent_sequence_no": unit.parent_sequence_no,
                }
                for unit in units
            ]
        )
        parse_status = (
            ParseStatus.PARTIALLY_PARSED if warnings else ParseStatus.PARSED
        )
        metrics["unit_count"] = len(units)
        return ParsedDocument(
            parser=ParserDescriptor(name=self.name, version=self.version),
            content_hash=semantic,
            units=tuple(units),
            inferred_title=collected.path.stem if collected.path else None,
            raw_content_hash=sha256_hex(raw),
            parser_config_hash=config.hash,
            parse_status=parse_status,
            warnings=tuple(dict.fromkeys(warnings)),
            metrics=metrics,
            document_metadata={"pdf_page_count": metrics.get("page_count")},
        )

    def _extract_page(
        self,
        page,
        page_no: int,
        units: list[ParsedUnit],
        warnings: list[str],
        metrics: dict[str, Any],
    ) -> None:
        table_line_texts: set[str] = set()
        if self.table_mode == PdfTableMode.BEST_EFFORT:
            try:
                tables = page.extract_tables() or []
            except Exception:
                tables = []
                warnings.append("PDF_TABLE_EXTRACTION_PARTIAL")
            for table_index, raw_table in enumerate(tables, start=1):
                rows = [
                    [_clean_cell(cell) for cell in row]
                    for row in raw_table
                    if row and any(_clean_cell(cell) for cell in row)
                ]
                if not rows:
                    continue
                parent_sequence = len(units)
                table_text = "\n".join(" | ".join(row) for row in rows)
                units.append(
                    ParsedUnit(
                        sequence_no=parent_sequence,
                        unit_type=ContentUnitType.TABLE,
                        text=table_text,
                        locator=SourceLocator(
                            page_no=page_no,
                            block_no=parent_sequence + 1,
                        ),
                    )
                )
                metrics["table_count"] += 1
                for row_no, row in enumerate(rows, start=1):
                    row_text = " | ".join(row)
                    table_line_texts.add(_normalize_line(row_text))
                    sequence_no = len(units)
                    units.append(
                        ParsedUnit(
                            sequence_no=sequence_no,
                            unit_type=ContentUnitType.TABLE_ROW,
                            text=row_text,
                            locator=SourceLocator(
                                page_no=page_no,
                                block_no=sequence_no + 1,
                                row_no=row_no,
                            ),
                            parent_sequence_no=parent_sequence,
                        )
                    )
                    metrics["table_row_count"] += 1

        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
            warnings.append("PDF_READING_ORDER_UNCERTAIN")
        lines = [
            _normalize_line(line)
            for line in text.splitlines()
            if _normalize_line(line)
        ]
        lines = [line for line in lines if line not in table_line_texts]
        if lines:
            metrics["pages_with_text"] += 1
            paragraph_no = 0
            for line in lines:
                paragraph_no += 1
                sequence_no = len(units)
                unit_type = (
                    ContentUnitType.HEADING
                    if _looks_like_heading(line)
                    else ContentUnitType.PARAGRAPH
                )
                units.append(
                    ParsedUnit(
                        sequence_no=sequence_no,
                        unit_type=unit_type,
                        text=line,
                        locator=SourceLocator(
                            page_no=page_no,
                            block_no=sequence_no + 1,
                            paragraph_no=(
                                paragraph_no
                                if unit_type == ContentUnitType.PARAGRAPH
                                else None
                            ),
                            heading_path=[line]
                            if unit_type == ContentUnitType.HEADING
                            else [],
                        ),
                    )
                )
        else:
            metrics["pages_without_text"] += 1
            if not any(unit.locator.page_no == page_no for unit in units):
                warnings.append("PDF_PAGE_NO_TEXT")


def _clean_cell(value: object) -> str:
    if value is None:
        return ""
    return _normalize_line(str(value))


def _normalize_line(value: str) -> str:
    return _WS.sub(" ", value).strip()


def _looks_like_heading(value: str) -> bool:
    if len(value) > 80:
        return False
    if re.match(r"^(第[一二三四五六七八九十百\d]+[章节部分]|\d+(?:\.\d+)*\s+)", value):
        return True
    ascii_letters = [character for character in value if character.isalpha() and character.isascii()]
    return bool(ascii_letters) and value.upper() == value and len(value.split()) <= 12
