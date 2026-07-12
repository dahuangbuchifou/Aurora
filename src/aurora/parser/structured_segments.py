"""Parser for the deterministic Structured Segments JSON contract."""

from __future__ import annotations

import json

from pydantic import ValidationError

from aurora.collector.base import CollectedInput
from aurora.ingestion.contracts import (
    ParserDescriptor,
    StructuredSegmentsManifest,
)
from aurora.ingestion.errors import InvalidStructuredSegmentsError
from aurora.ingestion.hashing import canonical_json_bytes, sha256_hex

from .base import ParsedDocument, ParsedUnit, Parser


class StructuredSegmentsParser(Parser):
    name = "structured_segments"
    version = "1.0.0"

    def parse(self, collected: CollectedInput) -> ParsedDocument:
        try:
            payload = json.loads(collected.text)
        except json.JSONDecodeError as exc:
            raise InvalidStructuredSegmentsError(
                f"invalid JSON at line {exc.lineno}, column {exc.colno}",
                context={"path": str(collected.path)},
            ) from exc

        try:
            manifest = StructuredSegmentsManifest.model_validate(payload)
        except ValidationError as exc:
            raise InvalidStructuredSegmentsError(
                "structured segments manifest failed validation",
                context={"errors": exc.errors(include_url=False)},
            ) from exc

        semantic_segments = [
            segment.model_dump(mode="json") for segment in manifest.segments
        ]
        content_hash = sha256_hex(canonical_json_bytes(semantic_segments))
        units = tuple(
            ParsedUnit(
                sequence_no=segment.sequence_no,
                unit_type=segment.unit_type,
                text=segment.text,
                locator=segment.locator,
                speaker=segment.speaker,
            )
            for segment in manifest.segments
        )
        return ParsedDocument(
            parser=ParserDescriptor(name=self.name, version=self.version),
            content_hash=content_hash,
            units=units,
            inferred_title=manifest.document.title,
            structured_manifest=manifest,
        )
