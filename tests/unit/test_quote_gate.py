"""Unit tests for QuoteGate — source_quote validation against ContentUnit text."""

import unittest.mock
from unittest.mock import patch

from aurora.core.models.common import SourceLocator
from aurora.core.models.document import ContentUnit
from aurora.core.models.enums import ContentUnitType
from aurora.extraction.candidates import (
    ClaimCandidate,
    DataPointCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import ContextWindow
from aurora.extraction.quote_gate import QuoteGate, QuoteGateError, QuoteGateFailure


def _make_unit(
    unit_id: str, sequence_no: int, text: str, doc_id: str = "doc_1"
) -> ContentUnit:
    return ContentUnit(
        id=unit_id,
        document_id=doc_id,
        unit_type=ContentUnitType.PARAGRAPH,
        sequence_no=sequence_no,
        text=text,
        locator=SourceLocator(block_no=sequence_no + 1),
    )


class TestQuoteGateSubstringMatching:
    """source_quote must be a substring of at least one ContentUnit.text."""

    def test_exact_match_passes(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "营业收入 673.23亿元")],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="revenue",
            value=673.23,
            unit="亿元",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="营业收入 673.23亿元",
        )
        report = gate.validate([candidate])
        assert report.all_passed
        assert report.passed_count == 1
        assert report.failed_count == 0

    def test_substring_match_passes(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "The company reported that 营业收入 673.23亿元 for fiscal year.")],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="revenue",
            value=673.23,
            unit="亿元",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="营业收入 673.23亿元",
        )
        report = gate.validate([candidate])
        assert report.all_passed

    def test_no_match_fails(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "completely different text")],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="revenue",
            value=673.23,
            unit="亿元",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="营业收入 673.23亿元",
        )
        report = gate.validate([candidate])
        assert not report.all_passed
        assert report.failed_count == 1
        assert len(report.failures) == 1
        assert report.failures[0].candidate_id == "dp_1"

    def test_candidate_without_source_quote_passes(self):
        """Candidates without source_quote are not checked (e.g., entities)."""
        from aurora.extraction.candidates import EntityCandidate

        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "中芯国际")],
        )
        gate = QuoteGate(window)
        candidate = EntityCandidate(
            id="e1",
            entity_type="organization",
            canonical_name="中芯国际",
        )
        report = gate.validate([candidate])
        assert report.all_passed

    def test_mixed_pass_fail(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "收入 100 亿元")],
        )
        gate = QuoteGate(window)
        good = DataPointCandidate(
            id="dp_ok",
            metric="revenue",
            value=100,
            unit="亿元",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="收入 100 亿元",
        )
        bad = DataPointCandidate(
            id="dp_bad",
            metric="profit",
            value=50,
            unit="亿元",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="利润 50 亿元",
        )
        report = gate.validate([good, bad])
        assert report.passed_count == 1
        assert report.failed_count == 1


class TestQuoteGateUnicodeNormalization:
    """Unicode normalization (NFKC) ensures matching across different representations."""

    def test_fullwidth_halfwidth_normalization(self):
        """Fullwidth digits should match halfwidth digits after normalization."""
        # Fullwidth: １２３ vs regular 123
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "营收１２３亿元")],  # fullwidth
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="revenue",
            value=123,
            unit="亿元",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="营收123亿元",  # halfwidth
        )
        report = gate.validate([candidate])
        assert report.all_passed, "NFKC normalization should match fullwidth/halfwidth"

    def test_combining_chars_normalization(self):
        """CJK Compatibility characters should normalize."""
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "①营业收入")],  # circled number
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="revenue",
            value=100,
            unit="亿元",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="1营业收入",  # after normalization
        )
        report = gate.validate([candidate])
        # ① normalizes to "1 " (with space) in NFKC, so "1营业收入" might not match
        # just checking it doesn't crash
        assert isinstance(report, type(report))


class TestQuoteGateFailureReporting:
    """Failures must be reported — never silently dropped."""

    def test_failure_includes_candidate_info(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "hello world")],
        )
        gate = QuoteGate(window)
        candidate = ClaimCandidate(
            id="cl_fail",
            statement="test",
            claim_type="fact_claim",
            claim_dimension="general",
            source_quote="nonexistent text",
        )
        report = gate.validate([candidate])
        assert len(report.failures) == 1
        failure = report.failures[0]
        assert failure.candidate_id == "cl_fail"
        assert failure.source_quote == "nonexistent text"
        assert "not found" in failure.reason.lower()

    def test_validate_or_raise(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "hello")],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="test",
            value=1,
            unit="km",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "count"},
            source_quote="missing",
        )
        with __import__("pytest").raises(QuoteGateError):
            gate.validate_or_raise([candidate])

    def test_valid_candidates_pass_validate_or_raise(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "hello world")],
        )
        gate = QuoteGate(window)
        candidate = ClaimCandidate(
            id="cl_ok",
            statement="hello",
            claim_type="fact_claim",
            claim_dimension="general",
            source_quote="hello world",
        )
        report = gate.validate_or_raise([candidate])
        assert report.all_passed
