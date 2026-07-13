"""Unit tests for QuoteGate V2 — source_unit_id enforcement, token_set, NFKC."""

import pytest

from aurora.core.models.common import SourceLocator
from aurora.core.models.document import ContentUnit
from aurora.core.models.enums import ContentUnitType
from aurora.extraction.candidates import (
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import ContextWindow
from aurora.extraction.quote_gate import QuoteGate, QuoteGateError, QuoteGateFailure


def _make_unit(
    unit_id: str,
    sequence_no: int,
    text: str,
    doc_id: str = "doc_1",
    unit_type: ContentUnitType = ContentUnitType.PARAGRAPH,
) -> ContentUnit:
    return ContentUnit(
        id=unit_id,
        document_id=doc_id,
        unit_type=unit_type,
        sequence_no=sequence_no,
        text=text,
        locator=SourceLocator(block_no=sequence_no + 1),
    )


class TestQuoteGateLiteralMatching:
    """V2: literal mode requires quote be a continuous substring within specific source_unit_id."""

    def test_exact_match_with_source_unit_id_passes(self):
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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert report.all_passed
        assert report.passed_count == 1
        assert report.failed_count == 0

    def test_substring_match_within_source_unit_passes(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [
                _make_unit("cu_0", 0, "The company reported that 营业收入 673.23亿元 for fiscal year."),
                _make_unit("cu_1", 1, "unrelated text"),
            ],
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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert report.all_passed

    def test_quote_not_in_specific_unit_fails(self):
        """Quote exists in another unit but not in the specified source_unit_id."""
        window = ContextWindow.from_content_units(
            "doc_1",
            [
                _make_unit("cu_0", 0, "completely different text"),
                _make_unit("cu_1", 1, "target text here"),
            ],
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
            source_quote="target text",
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert not report.all_passed
        assert report.failed_count == 1

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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert not report.all_passed
        assert report.failed_count == 1
        assert len(report.failures) == 1


class TestQuoteGateSourceUnitIdEnforcement:
    """V2: Must reject missing units, wrong-document units, empty source_unit_id."""

    def test_missing_source_unit_id_fails(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "hello")],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="test",
            value=1,
            unit="x",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "count"},
            source_quote="hello",
            source_unit_id="",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert not report.all_passed
        assert any("empty source_unit_id" in f.message.lower() for f in report.findings)

    def test_unit_not_in_window_fails(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "hello")],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="test",
            value=1,
            unit="x",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "count"},
            source_quote="hello",
            source_unit_id="cu_nonexistent",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert not report.all_passed
        assert any("not found in ContextWindow" in f.message for f in report.findings)

    def test_empty_source_quote_fails(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "hello")],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="test",
            value=1,
            unit="x",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "count"},
            source_quote="",
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert not report.all_passed


class TestQuoteGateTokenSet:
    """V2: token_set only allowed for TABLE and TABLE_ROW unit types."""

    def test_token_set_on_table_row_passes(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "营业收入 673.23亿元", unit_type=ContentUnitType.TABLE_ROW)],
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
            source_unit_id="cu_0",
            quote_match_mode="token_set",
        )
        report = gate.validate([candidate])
        assert report.all_passed

    def test_token_set_100_percent_match_required(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "Revenue 67.323 bn 2025", unit_type=ContentUnitType.TABLE_ROW)],
        )
        gate = QuoteGate(window)
        # All tokens present
        candidate_ok = DataPointCandidate(
            id="dp_ok",
            metric="r",
            value=67.323,
            unit="bn",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="Revenue 67.323 bn",
            source_unit_id="cu_0",
            quote_match_mode="token_set",
        )
        # Missing token
        candidate_bad = DataPointCandidate(
            id="dp_bad",
            metric="r",
            value=100,
            unit="bn",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="Revenue 100.0 bn",
            source_unit_id="cu_0",
            quote_match_mode="token_set",
        )
        report = gate.validate([candidate_ok, candidate_bad])
        assert report.passed_count == 1
        assert report.failed_count == 1

    def test_token_set_on_non_table_fails(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "营业收入 673.23亿元", unit_type=ContentUnitType.PARAGRAPH)],
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
            source_quote="营业收入",
            source_unit_id="cu_0",
            quote_match_mode="token_set",
        )
        report = gate.validate([candidate])
        assert not report.all_passed
        assert any("TOKEN_SET_ON_NON_TABLE" in f.code for f in report.findings)

    def test_token_set_empty_tokens_fails(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "text", unit_type=ContentUnitType.TABLE_ROW)],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="test",
            value=1,
            unit="x",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "count"},
            source_quote="   ",
            source_unit_id="cu_0",
            quote_match_mode="token_set",
        )
        report = gate.validate([candidate])
        assert not report.all_passed

    def test_token_set_on_table_passes(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [_make_unit("cu_0", 0, "Revenue 67 bn", unit_type=ContentUnitType.TABLE)],
        )
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            id="dp_1",
            metric="r",
            value=67,
            unit="bn",
            entity_id="e1",
            period="2025",
            measurement_context={"measurement_kind": "monetary"},
            source_quote="Revenue 67 bn",
            source_unit_id="cu_0",
            quote_match_mode="token_set",
        )
        report = gate.validate([candidate])
        assert report.all_passed


class TestQuoteGateUnicodeNormalization:
    """NFKC normalization ensures matching across different representations."""

    def test_fullwidth_halfwidth_normalization(self):
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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert report.all_passed, "NFKC normalization should match fullwidth/halfwidth"


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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert len(report.failures) == 1
        failure = report.failures[0]
        assert failure.candidate_id == "cl_fail"
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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        with pytest.raises(QuoteGateError):
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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate_or_raise([candidate])
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
            source_unit_id="cu_0",
            quote_match_mode="literal",
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
            source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([good, bad])
        assert report.passed_count == 1
        assert report.failed_count == 1
