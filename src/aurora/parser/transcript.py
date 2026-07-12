"""Deterministic SRT and WebVTT transcript parsers."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from aurora.collector.base import CollectedInput
from aurora.core.models.common import SourceLocator
from aurora.core.models.enums import ContentUnitType, ParseStatus
from aurora.ingestion.contracts import ParserDescriptor
from aurora.ingestion.errors import (
    TranscriptEmptyError,
    TranscriptInvalidTimestampError,
    TranscriptNonMonotonicError,
    TranscriptParseError,
)
from aurora.ingestion.hashing import semantic_units_hash, sha256_hex

from .base import ParsedDocument, ParsedUnit, Parser
from .config import ParserConfig

_TIMING = re.compile(
    r"^(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3}|\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3}|\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
)
_VOICE = re.compile(r"^<v(?:\.[^ >]+)*\s+([^>]+)>(.*)$", re.IGNORECASE | re.DOTALL)
_TAGS = re.compile(r"<[^>]+>")
_SPEAKER = re.compile(r"^([\w\u4e00-\u9fff ._-]{1,80}):\s+(.+)$", re.DOTALL)


@dataclass(frozen=True)
class _Cue:
    start_seconds: float
    end_seconds: float
    text: str
    speaker: str | None


class TranscriptParser(Parser):
    version = "1.0.0"

    def __init__(self, *, transcript_format: str) -> None:
        normalized = transcript_format.lower().lstrip(".")
        if normalized not in {"srt", "vtt"}:
            raise ValueError("transcript_format must be srt or vtt")
        self.transcript_format = normalized
        self.name = normalized

    def parse(self, collected: CollectedInput) -> ParsedDocument:
        cues, warnings = self._parse_cues(collected.text)
        if not cues:
            raise TranscriptEmptyError(
                "transcript contains no valid cues",
                context={"file_name": collected.file_name},
            )
        units = tuple(
            ParsedUnit(
                sequence_no=index,
                unit_type=ContentUnitType.TRANSCRIPT_SEGMENT,
                text=cue.text,
                locator=SourceLocator(
                    start_seconds=cue.start_seconds,
                    end_seconds=cue.end_seconds,
                    block_no=index + 1,
                ),
                speaker=cue.speaker,
                quality_flags=("TRANSCRIPT_OVERLAP",)
                if index > 0 and cue.start_seconds < cues[index - 1].end_seconds
                else (),
            )
            for index, cue in enumerate(cues)
        )
        config = ParserConfig(
            name=self.name,
            version=self.version,
            options={"format": self.transcript_format, "cue_granularity": "one_cue"},
        )
        semantic = semantic_units_hash(
            [
                {
                    "start_ms": round(cue.start_seconds * 1000),
                    "end_ms": round(cue.end_seconds * 1000),
                    "speaker": cue.speaker,
                    "text": cue.text,
                }
                for cue in cues
            ]
        )
        return ParsedDocument(
            parser=ParserDescriptor(name=self.name, version=self.version),
            content_hash=semantic,
            units=units,
            inferred_title=collected.path.stem if collected.path else None,
            raw_content_hash=sha256_hex(
                collected.raw_bytes or collected.text.encode("utf-8")
            ),
            parser_config_hash=config.hash,
            parse_status=(
                ParseStatus.PARTIALLY_PARSED if warnings else ParseStatus.PARSED
            ),
            warnings=tuple(dict.fromkeys(warnings)),
            metrics={
                "caption_count": len(cues),
                "overlap_count": sum(
                    cue.start_seconds < cues[index - 1].end_seconds
                    for index, cue in enumerate(cues)
                    if index > 0
                ),
                "input_bytes": collected.size_bytes,
            },
        )

    def _parse_cues(self, text: str) -> tuple[list[_Cue], list[str]]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
        if self.transcript_format == "vtt":
            lines = normalized.splitlines()
            if lines and lines[0].strip().startswith("WEBVTT"):
                normalized = "\n".join(lines[1:])
        blocks = re.split(r"\n\s*\n", normalized.strip())
        cues: list[_Cue] = []
        warnings: list[str] = []
        previous_start = -1.0
        previous_end = -1.0
        for block_no, block in enumerate(blocks, start=1):
            lines = [line.rstrip() for line in block.splitlines()]
            if not lines:
                continue
            if self.transcript_format == "vtt" and lines[0].strip().upper().startswith(("NOTE", "STYLE", "REGION")):
                continue
            timing_index = next(
                (index for index, line in enumerate(lines[:3]) if "-->" in line),
                None,
            )
            if timing_index is None:
                if all(not line.strip() for line in lines):
                    continue
                raise TranscriptParseError(
                    "transcript cue is missing a timing line",
                    context={"block_no": block_no},
                )
            match = _TIMING.match(lines[timing_index].strip())
            if not match:
                raise TranscriptInvalidTimestampError(
                    "transcript cue has an invalid timestamp",
                    context={"block_no": block_no, "timing": lines[timing_index]},
                )
            start = _timestamp_seconds(match.group("start"))
            end = _timestamp_seconds(match.group("end"))
            if end < start:
                raise TranscriptInvalidTimestampError(
                    "transcript cue end is earlier than start",
                    context={"block_no": block_no},
                )
            if start < previous_start:
                raise TranscriptNonMonotonicError(
                    "transcript cues are not ordered by start time",
                    context={"block_no": block_no, "start_seconds": start},
                )
            raw_text = "\n".join(lines[timing_index + 1 :]).strip()
            speaker, cleaned = _speaker_and_text(raw_text)
            if not cleaned:
                warnings.append("TRANSCRIPT_EMPTY_CUE_DROPPED")
                continue
            if start < previous_end:
                warnings.append("TRANSCRIPT_OVERLAP")
            cues.append(
                _Cue(
                    start_seconds=start,
                    end_seconds=end,
                    text=cleaned,
                    speaker=speaker,
                )
            )
            previous_start = start
            previous_end = end
        return cues, warnings


def _timestamp_seconds(value: str) -> float:
    normalized = value.replace(",", ".")
    parts = normalized.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = parts
        elif len(parts) == 2:
            hours = "0"
            minutes, seconds = parts
        else:
            raise ValueError
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError as exc:
        raise TranscriptInvalidTimestampError(
            "invalid timestamp",
            context={"timestamp": value},
        ) from exc


def _speaker_and_text(raw: str) -> tuple[str | None, str]:
    voice = _VOICE.match(raw)
    speaker: str | None = None
    text = raw
    if voice:
        speaker = voice.group(1).strip()
        text = voice.group(2)
    text = html.unescape(_TAGS.sub("", text)).strip()
    prefix = _SPEAKER.match(text)
    if speaker is None and prefix:
        speaker = prefix.group(1).strip()
        text = prefix.group(2).strip()
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return speaker or None, text
