"""Parser interfaces and immutable parse results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from aurora.collector.base import CollectedInput
from aurora.core.models.common import SourceLocator
from aurora.core.models.enums import ContentUnitType, ParseStatus
from aurora.ingestion.contracts import ParserDescriptor, StructuredSegmentsManifest


@dataclass(frozen=True)
class ParseReport:
    status: ParseStatus = ParseStatus.PARSED
    raw_content_hash: str | None = None
    semantic_content_hash: str | None = None
    parser_config_hash: str = "default"
    warning_codes: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedUnit:
    sequence_no: int
    unit_type: ContentUnitType
    text: str
    locator: SourceLocator
    speaker: str | None = None
    parent_sequence_no: int | None = None
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParsedDocument:
    parser: ParserDescriptor
    content_hash: str
    units: tuple[ParsedUnit, ...]
    inferred_title: str | None = None
    structured_manifest: StructuredSegmentsManifest | None = None
    raw_content_hash: str | None = None
    parser_config_hash: str = "default"
    parse_status: ParseStatus = ParseStatus.PARSED
    warnings: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)
    document_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def report(self) -> ParseReport:
        return ParseReport(
            status=self.parse_status,
            raw_content_hash=self.raw_content_hash,
            semantic_content_hash=self.content_hash,
            parser_config_hash=self.parser_config_hash,
            warning_codes=self.warnings,
            metrics=self.metrics,
        )


class Parser(ABC):
    name: str
    version: str

    @abstractmethod
    def parse(self, collected: CollectedInput) -> ParsedDocument:
        raise NotImplementedError
