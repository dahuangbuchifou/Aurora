"""Deterministic offline and multi-carrier parsers."""

from .base import ParseReport, ParsedDocument, ParsedUnit, Parser
from .config import ParserConfig
from .html import HtmlDocumentParser
from .markdown import MarkdownParser
from .pdf import PdfDocumentParser, parse_page_selection
from .plain_text import PlainTextParser
from .structured_segments import StructuredSegmentsParser
from .transcript import TranscriptParser

__all__ = [
    "ParseReport",
    "ParsedDocument",
    "ParsedUnit",
    "Parser",
    "ParserConfig",
    "MarkdownParser",
    "PlainTextParser",
    "StructuredSegmentsParser",
    "HtmlDocumentParser",
    "PdfDocumentParser",
    "parse_page_selection",
    "TranscriptParser",
]
