from pathlib import Path

import pytest

from aurora.collector import LocalFileCollector
from aurora.core.models.enums import ContentUnitType, ParseStatus
from aurora.ingestion.errors import (
    TranscriptInvalidTimestampError,
    TranscriptNonMonotonicError,
)
from aurora.parser import TranscriptParser


FIXTURES = Path(__file__).parents[1] / "fixtures" / "m2_002"


def test_srt_parser_preserves_time_speaker_and_overlap_warning():
    collected = LocalFileCollector().collect(
        FIXTURES / "case_b_video.srt", max_bytes=1024 * 1024
    )
    parsed = TranscriptParser(transcript_format="srt").parse(collected)
    assert parsed.parse_status == ParseStatus.PARTIALLY_PARSED
    assert parsed.warnings == ("TRANSCRIPT_OVERLAP",)
    assert len(parsed.units) == 3
    assert all(
        unit.unit_type == ContentUnitType.TRANSCRIPT_SEGMENT
        for unit in parsed.units
    )
    assert parsed.units[0].speaker == "UP主"
    assert parsed.units[0].locator.start_seconds == 1.0
    assert parsed.units[0].locator.end_seconds == 4.0
    assert parsed.metrics["overlap_count"] == 1


def test_vtt_voice_span_is_preserved():
    collected = LocalFileCollector().collect(
        FIXTURES / "case_b_video.vtt", max_bytes=1024 * 1024
    )
    parsed = TranscriptParser(transcript_format="vtt").parse(collected)
    assert parsed.parse_status == ParseStatus.PARSED
    assert parsed.units[0].speaker == "UP主"
    assert "成熟制程" in parsed.units[0].text


def test_timestamp_change_changes_semantic_hash(tmp_path: Path):
    left = tmp_path / "left.srt"
    right = tmp_path / "right.srt"
    left.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nSame\n", encoding="utf-8"
    )
    right.write_text(
        "1\n00:00:02,000 --> 00:00:03,000\nSame\n", encoding="utf-8"
    )
    parser = TranscriptParser(transcript_format="srt")
    left_parsed = parser.parse(LocalFileCollector().collect(left, max_bytes=1024))
    right_parsed = parser.parse(LocalFileCollector().collect(right, max_bytes=1024))
    assert left_parsed.content_hash != right_parsed.content_hash


def test_invalid_timestamp_order_is_rejected(tmp_path: Path):
    path = tmp_path / "bad.srt"
    path.write_text(
        "1\n00:00:03,000 --> 00:00:02,000\nBad\n", encoding="utf-8"
    )
    with pytest.raises(TranscriptInvalidTimestampError):
        TranscriptParser(transcript_format="srt").parse(
            LocalFileCollector().collect(path, max_bytes=1024)
        )


def test_non_monotonic_cues_are_rejected(tmp_path: Path):
    path = tmp_path / "bad.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:05.000 --> 00:00:06.000\nLater\n\n"
        "00:00:04.000 --> 00:00:05.000\nEarlier\n",
        encoding="utf-8",
    )
    with pytest.raises(TranscriptNonMonotonicError):
        TranscriptParser(transcript_format="vtt").parse(
            LocalFileCollector().collect(path, max_bytes=1024)
        )


def test_transcript_constructor_rejects_unknown_format():
    with pytest.raises(ValueError):
        TranscriptParser(transcript_format="ass")


def test_vtt_note_block_is_ignored_and_two_part_timestamp_is_supported(tmp_path: Path):
    path = tmp_path / "note.vtt"
    path.write_text(
        "WEBVTT\n\nNOTE metadata\nignored\n\n00:01.000 --> 00:02.000\nHello\n",
        encoding="utf-8",
    )
    parsed = TranscriptParser(transcript_format="vtt").parse(
        LocalFileCollector().collect(path, max_bytes=4096)
    )
    assert len(parsed.units) == 1
    assert parsed.units[0].locator.start_seconds == 1.0


def test_missing_timing_line_is_rejected(tmp_path: Path):
    from aurora.ingestion.errors import TranscriptParseError

    path = tmp_path / "missing.srt"
    path.write_text("1\nNo timing\nText\n", encoding="utf-8")
    with pytest.raises(TranscriptParseError):
        TranscriptParser(transcript_format="srt").parse(
            LocalFileCollector().collect(path, max_bytes=4096)
        )


def test_malformed_timing_line_is_rejected(tmp_path: Path):
    path = tmp_path / "malformed.srt"
    path.write_text("1\nBAD --> WORSE\nText\n", encoding="utf-8")
    with pytest.raises(TranscriptInvalidTimestampError):
        TranscriptParser(transcript_format="srt").parse(
            LocalFileCollector().collect(path, max_bytes=4096)
        )


def test_empty_cue_is_dropped_and_can_make_transcript_empty(tmp_path: Path):
    from aurora.ingestion.errors import TranscriptEmptyError

    path = tmp_path / "empty.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<i></i>\n",
        encoding="utf-8",
    )
    with pytest.raises(TranscriptEmptyError):
        TranscriptParser(transcript_format="vtt").parse(
            LocalFileCollector().collect(path, max_bytes=4096)
        )
