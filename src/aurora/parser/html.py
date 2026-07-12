"""Deterministic static HTML parser with replayable DOM locators."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from bs4 import BeautifulSoup, Tag

from aurora.collector.base import CollectedInput
from aurora.core.models.common import SourceLocator
from aurora.core.models.enums import ContentUnitType, ParseStatus
from aurora.ingestion.contracts import ParserDescriptor
from aurora.ingestion.errors import HtmlParseError, WebEmptyMainContentError
from aurora.ingestion.hashing import semantic_units_hash, sha256_hex

from .base import ParsedDocument, ParsedUnit, Parser
from .config import ParserConfig

_BLOCK_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "li",
    "blockquote",
    "pre",
    "table",
}
_REMOVE_TAGS = {"script", "style", "noscript", "template", "form", "nav", "footer", "aside"}
_WS = re.compile(r"\s+")


class HtmlDocumentParser(Parser):
    name = "html"
    version = "1.0.0"

    def __init__(self, *, content_selector: str | None = None) -> None:
        self.content_selector = content_selector

    def parse(self, collected: CollectedInput) -> ParsedDocument:
        if not collected.text.strip():
            raise WebEmptyMainContentError("HTML input contains no text")
        try:
            soup = BeautifulSoup(collected.text, "lxml")
        except Exception as exc:  # pragma: no cover - defensive parser boundary.
            raise HtmlParseError(
                "HTML could not be parsed",
                context={"exception_type": type(exc).__name__},
            ) from exc

        warnings: list[str] = []
        root = self._select_root(soup, warnings)
        for node in list(root.find_all(_REMOVE_TAGS)):
            node.decompose()

        inferred_title = self._title(soup, root)
        metadata = self._metadata(soup)
        units = self._extract_units(root)
        if not units:
            raise WebEmptyMainContentError(
                "HTML main content contains no supported blocks",
                context={"content_selector": self.content_selector},
            )

        config = ParserConfig(
            name=self.name,
            version=self.version,
            options={"content_selector": self.content_selector},
        )
        semantic = semantic_units_hash(
            [
                {
                    "sequence_no": unit.sequence_no,
                    "unit_type": unit.unit_type.value,
                    "text": unit.text,
                    "parent_sequence_no": unit.parent_sequence_no,
                }
                for unit in units
            ]
        )
        raw_hash = sha256_hex(
            collected.raw_bytes or collected.text.encode("utf-8")
        )
        parse_status = (
            ParseStatus.PARTIALLY_PARSED if warnings else ParseStatus.PARSED
        )
        metrics = {
            "html_element_count": len(units),
            "table_count": sum(unit.unit_type == ContentUnitType.TABLE for unit in units),
            "table_row_count": sum(
                unit.unit_type == ContentUnitType.TABLE_ROW for unit in units
            ),
            "input_bytes": collected.size_bytes,
        }
        return ParsedDocument(
            parser=ParserDescriptor(name=self.name, version=self.version),
            content_hash=semantic,
            units=tuple(units),
            inferred_title=inferred_title,
            raw_content_hash=raw_hash,
            parser_config_hash=config.hash,
            parse_status=parse_status,
            warnings=tuple(warnings),
            metrics=metrics,
            document_metadata=metadata,
        )

    def _select_root(self, soup: BeautifulSoup, warnings: list[str]) -> Tag:
        if self.content_selector:
            try:
                explicit = soup.select_one(self.content_selector)
            except Exception as exc:
                raise HtmlParseError(
                    "invalid HTML content selector",
                    context={"selector": self.content_selector},
                ) from exc
            if explicit is not None:
                return explicit
            warnings.append("HTML_SELECTOR_NOT_FOUND")
        article = soup.find("article")
        if isinstance(article, Tag):
            return article
        main = soup.find("main")
        if isinstance(main, Tag):
            return main
        body = soup.body
        if isinstance(body, Tag):
            warnings.append("HTML_FALLBACK_TO_BODY")
            return body
        warnings.append("HTML_FALLBACK_TO_DOCUMENT")
        return soup  # type: ignore[return-value]

    @staticmethod
    def _title(soup: BeautifulSoup, root: Tag) -> str | None:
        og = soup.find("meta", attrs={"property": "og:title"})
        if isinstance(og, Tag) and og.get("content"):
            return _clean_text(str(og.get("content")))
        if soup.title and soup.title.string:
            title = _clean_text(soup.title.string)
            if title:
                return title
        heading = root.find(["h1", "h2"])
        if isinstance(heading, Tag):
            return _clean_text(heading.get_text(" ", strip=True)) or None
        return None

    @staticmethod
    def _metadata(soup: BeautifulSoup) -> dict[str, Any]:
        result: dict[str, Any] = {}
        canonical = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
        if isinstance(canonical, Tag) and canonical.get("href"):
            result["canonical_url"] = str(canonical.get("href"))
        mapping = {
            "site_name": ("property", "og:site_name"),
            "published_at": ("property", "article:published_time"),
            "author": ("name", "author"),
        }
        for key, (attr, value) in mapping.items():
            node = soup.find("meta", attrs={attr: value})
            if isinstance(node, Tag) and node.get("content"):
                result[key] = _clean_text(str(node.get("content")))
        html = soup.find("html")
        if isinstance(html, Tag) and html.get("lang"):
            result["language"] = str(html.get("lang")).strip()
        return result

    def _extract_units(self, root: Tag) -> list[ParsedUnit]:
        units: list[ParsedUnit] = []
        heading_path: list[str] = []
        candidates: Iterable[Tag] = root.find_all(list(_BLOCK_TAGS))
        for node in candidates:
            if node.name != "table" and node.find_parent("table") is not None:
                continue
            if node.name != "table" and self._has_block_parent(node, root):
                continue
            if node.name == "table":
                self._append_table(units, node, root, tuple(heading_path))
                continue

            text = _clean_text(node.get_text(" ", strip=True))
            if not text:
                continue
            if node.name and node.name.startswith("h") and len(node.name) == 2:
                level = int(node.name[1])
                heading_path = heading_path[: level - 1]
                heading_path.append(text)
                unit_type = ContentUnitType.HEADING
            elif node.name == "p":
                unit_type = ContentUnitType.PARAGRAPH
            elif node.name == "li":
                unit_type = ContentUnitType.LIST_ITEM
            elif node.name == "blockquote":
                unit_type = ContentUnitType.QUOTE
            elif node.name == "pre":
                unit_type = ContentUnitType.CODE_BLOCK
                text = node.get_text("\n", strip=False).strip("\n")
            else:
                continue
            sequence_no = len(units)
            units.append(
                ParsedUnit(
                    sequence_no=sequence_no,
                    unit_type=unit_type,
                    text=text,
                    locator=SourceLocator(
                        block_no=sequence_no + 1,
                        paragraph_no=(
                            sum(u.unit_type == ContentUnitType.PARAGRAPH for u in units)
                            + 1
                            if unit_type == ContentUnitType.PARAGRAPH
                            else None
                        ),
                        heading_path=list(heading_path),
                        css_selector=_css_path(node, root),
                        xpath=_xpath(node, root),
                    ),
                )
            )
        return units

    @staticmethod
    def _has_block_parent(node: Tag, root: Tag) -> bool:
        parent = node.parent
        while isinstance(parent, Tag) and parent is not root:
            if parent.name in _BLOCK_TAGS:
                return True
            parent = parent.parent
        return False

    @staticmethod
    def _append_table(
        units: list[ParsedUnit],
        table: Tag,
        root: Tag,
        heading_path: tuple[str, ...],
    ) -> None:
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            cells = [
                _clean_text(cell.get_text(" ", strip=True))
                for cell in tr.find_all(["th", "td"], recursive=False)
            ]
            if any(cells):
                rows.append(cells)
        if not rows:
            text = _clean_text(table.get_text(" ", strip=True))
            if not text:
                return
            rows = [[text]]
        parent_sequence = len(units)
        caption = table.find("caption")
        caption_text = (
            _clean_text(caption.get_text(" ", strip=True))
            if isinstance(caption, Tag)
            else ""
        )
        table_text = "\n".join(" | ".join(row) for row in rows)
        if caption_text:
            table_text = f"{caption_text}\n{table_text}"
        units.append(
            ParsedUnit(
                sequence_no=parent_sequence,
                unit_type=ContentUnitType.TABLE,
                text=table_text,
                locator=SourceLocator(
                    block_no=parent_sequence + 1,
                    heading_path=list(heading_path),
                    css_selector=_css_path(table, root),
                    xpath=_xpath(table, root),
                ),
            )
        )
        table_selector = _css_path(table, root)
        table_xpath = _xpath(table, root)
        for row_no, cells in enumerate(rows, start=1):
            sequence_no = len(units)
            units.append(
                ParsedUnit(
                    sequence_no=sequence_no,
                    unit_type=ContentUnitType.TABLE_ROW,
                    text=" | ".join(cells),
                    locator=SourceLocator(
                        block_no=sequence_no + 1,
                        row_no=row_no,
                        heading_path=list(heading_path),
                        css_selector=f"{table_selector} tr:nth-of-type({row_no})",
                        xpath=f"{table_xpath}//tr[{row_no}]",
                    ),
                    parent_sequence_no=parent_sequence,
                )
            )


def _clean_text(value: str) -> str:
    return _WS.sub(" ", value).strip()


def _css_path(node: Tag, root: Tag) -> str:
    parts: list[str] = []
    current: Tag | None = node
    while isinstance(current, Tag):
        name = current.name or "node"
        if current.get("id"):
            parts.append(f"{name}#{current.get('id')}")
        else:
            siblings = [
                child
                for child in current.parent.children
                if isinstance(child, Tag) and child.name == current.name
            ] if isinstance(current.parent, Tag) else [current]
            index = siblings.index(current) + 1 if current in siblings else 1
            parts.append(f"{name}:nth-of-type({index})")
        if current is root:
            break
        current = current.parent if isinstance(current.parent, Tag) else None
    return " > ".join(reversed(parts))


def _xpath(node: Tag, root: Tag) -> str:
    parts: list[str] = []
    current: Tag | None = node
    while isinstance(current, Tag):
        siblings = [
            child
            for child in current.parent.children
            if isinstance(child, Tag) and child.name == current.name
        ] if isinstance(current.parent, Tag) else [current]
        index = siblings.index(current) + 1 if current in siblings else 1
        parts.append(f"{current.name}[{index}]")
        if current is root:
            break
        current = current.parent if isinstance(current.parent, Tag) else None
    return "/" + "/".join(reversed(parts))
