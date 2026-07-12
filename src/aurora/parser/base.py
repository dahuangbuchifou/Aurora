"""Parser interfaces and immutable parse results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from aurora.collector.base import CollectedInput
from aurora.core.models.common import SourceLocator
from aurora.core.models.enums import ContentUnitType
from aurora.ingestion.contracts import ParserDescriptor, StructuredSegmentsManifest


@dataclass(frozen=True)
class ParsedUnit:
    sequence_no: int
    unit_type: ContentUnitType
    text: str
    locator: SourceLocator
    speaker: str | None = None


@dataclass(frozen=True)
class ParsedDocument:
    parser: ParserDescriptor
    content_hash: str
    units: tuple[ParsedUnit, ...]
    inferred_title: str | None = None
    structured_manifest: StructuredSegmentsManifest | None = None


class Parser(ABC):
    name: str
    version: str

    @abstractmethod
    def parse(self, collected: CollectedInput) -> ParsedDocument:
        raise NotImplementedError
