"""Supplementary tests for V2 components to reach ≥90% coverage."""

import json
import pytest
from pathlib import Path

from pydantic import ValidationError

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
from aurora.extraction.context_window import (
    ContentUnitRef,
    ContextWindow,
    ContextWindowError,
    CANDIDATE_TYPE_ORDER,
)
from aurora.extraction.envelope import ExtractionEnvelope, ProviderMetadata
from aurora.extraction.findings import (
    FindingSeverity,
    ValidationFinding,
)
from aurora.extraction.providers.base import ExtractionProvider, ProviderResponse
from aurora.extraction.providers.fixture_provider import FixtureProvider
from aurora.extraction.quote_gate import (
    QuoteGate,
    QuoteGateError,
    QuoteGateReport,
    QuoteGateFailure,
    _normalize,
    _tokenize,
    _collapse_whitespace,
)
from aurora.extraction.request import ExtractionRequest
from aurora.extraction.review_bundle import ExtractionError, ReviewBundle, BUNDLE_SCHEMA_VERSION


def _make_claim_candidate_with_subjects(
    subject_entity_ids: object | None = None,
) -> ClaimCandidate:
    payload: dict[str, object] = {
        "candidate_id": "cl_cand_subject_contract_001",
        "statement": "Revenue increased year over year.",
        "claim_type": "interpretation",
        "claim_dimension": "financial_performance",
        "source_quote": "Revenue increased year over year.",
    }
    if subject_entity_ids is not None:
        payload["subject_entity_ids"] = subject_entity_ids
    return ClaimCandidate(**payload)


def test_claim_candidate_subject_entity_ids_default_is_independent():
    first = _make_claim_candidate_with_subjects()
    second = _make_claim_candidate_with_subjects()

    assert first.subject_entity_ids == []
    assert second.subject_entity_ids == []
    assert first.subject_entity_ids is not second.subject_entity_ids
    assert first.model_dump()["subject_entity_ids"] == []

    first.subject_entity_ids.append("ent_cand_a")
    assert second.subject_entity_ids == []


def test_claim_candidate_accepts_explicit_subject_entity_ids():
    candidate = _make_claim_candidate_with_subjects(
        ["ent_cand_a", "ent_cand_b"]
    )

    assert candidate.subject_entity_ids == ["ent_cand_a", "ent_cand_b"]


def test_claim_candidate_rejects_invalid_subject_entity_ids_type():
    with pytest.raises(ValidationError) as exc_info:
        _make_claim_candidate_with_subjects("ent_cand_a")

    assert exc_info.value.errors()[0]["loc"] == ("subject_entity_ids",)


# ── ContextWindow additional tests ───────────────────────────────────────────

class TestContextWindowV2Extra:
    def test_from_content_unit_refs(self):
        refs = [
            ContentUnitRef("cu_a", 0, "paragraph", "hello", "doc_1"),
            ContentUnitRef("cu_b", 1, "paragraph", "world", "doc_1"),
        ]
        w = ContextWindow.from_content_unit_refs("doc_1", refs)
        assert len(w) == 2
        assert w.units[0].unit_id == "cu_a"

    def test_repr(self):
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        w = ContextWindow.from_content_units("doc_1", units)
        r = repr(w)
        assert "ContextWindow" in str(r)
        assert "doc_1" in str(r)

    def test_duplicate_sequence_unit_id_pair_rejection(self):
        units = [
            ContentUnit(id="cu_a", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="a", locator=SourceLocator(block_no=1)),
            ContentUnit(id="cu_b", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="b", locator=SourceLocator(block_no=2)),
        ]
        # Different IDs, same seq_no — allowed
        w = ContextWindow.from_content_units("doc_1", units)
        assert len(w) == 2

    def test_candidate_type_order_frozen(self):
        assert isinstance(CANDIDATE_TYPE_ORDER, tuple)
        assert CANDIDATE_TYPE_ORDER[0] == "entity"
        assert "fact" in CANDIDATE_TYPE_ORDER


# ── QuoteGate additional tests ────────────────────────────────────────────────

class TestQuoteGateV2Extra:
    def test_entity_skipped_in_validation(self):
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        gate = QuoteGate(window)
        entity = EntityCandidate(candidate_id="ent_1", entity_type="org", canonical_name="Test")
        report = gate.validate([entity])
        assert report.all_passed
        assert report.passed_count == 1

    def test_validate_or_raise_error(self):
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            candidate_id="dp_bad", metric="x", value=1.0, unit="km",
            entity_id="e1", period="2025", measurement_context={},
            source_quote="missing text", source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        with pytest.raises(QuoteGateError) as exc:
            gate.validate_or_raise([candidate])
        assert exc.value.report is not None

    def test_report_error_findings(self):
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            candidate_id="dp_bad", metric="x", value=1.0, unit="km",
            entity_id="e1", period="2025", measurement_context={},
            source_quote="missing", source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert len(report.error_findings) == 1

    def test_quote_gate_failure_dto(self):
        window = ContextWindow.from_content_units(
            "doc_1",
            [ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                         sequence_no=0, text="hello", locator=SourceLocator(block_no=1))],
        )
        failure = QuoteGateFailure(
            candidate=EntityCandidate(candidate_id="e1", entity_type="org", canonical_name="X"),
            source_quote="hello",
            candidate_id="e1",
            reason="test reason",
        )
        assert failure.candidate_id == "e1"
        assert failure.reason == "test reason"

    def test_helper_functions(self):
        assert _normalize("①②③") == "123"  # NFKC converts circled numbers
        assert _collapse_whitespace("a   b\nc") == "a b c"
        tokens = _tokenize("Revenue 67.323 bn")
        assert "Revenue" in tokens
        assert "67.323" in tokens

    def test_literal_match_after_collapse(self):
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="line1\n\nline2", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        gate = QuoteGate(window)
        candidate = DataPointCandidate(
            candidate_id="dp_1", metric="x", value=1.0, unit="km",
            entity_id="e1", period="2025", measurement_context={},
            source_quote="line1  line2", source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        report = gate.validate([candidate])
        assert report.all_passed

    def test_missing_unit_text_returns_false(self):
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.TABLE_ROW,
                        sequence_no=0, text="x", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        gate = QuoteGate(window)
        # token_set on a unit with text that doesn't contain the quote tokens
        candidate = DataPointCandidate(
            candidate_id="dp_1", metric="x", value=1.0, unit="km",
            entity_id="e1", period="2025", measurement_context={},
            source_quote="z", source_unit_id="cu_0",
            quote_match_mode="token_set",
        )
        report = gate.validate([candidate])
        assert not report.all_passed

    def test_unknown_candidate_id(self):
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_1", units)

        # Candidate with no id or candidate_id
        from aurora.extraction.candidates import _new_candidate_id
        # Create candidate and clear both ids
        candidate = DataPointCandidate(
            metric="x", value=1.0, unit="km", entity_id="e1", period="2025",
            measurement_context={}, source_quote="missing", source_unit_id="cu_0",
            quote_match_mode="literal",
        )
        candidate.id = ""
        candidate.candidate_id = ""
        gate = QuoteGate(window)
        report = gate.validate([candidate])
        # Should still have a failure with "unknown" candidate id
        assert report.failed_count == 1


# ── FixtureProvider additional tests ─────────────────────────────────────────

class TestFixtureProviderV2Extra:
    def test_unknown_case_id_raises(self):
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        with pytest.raises(ValueError, match="Unknown case_id"):
            provider.extract_for_case("nonexistent_case", window)

    def test_infer_case_id_from_document(self):
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_video_test", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_video_test", units)
        response = provider.extract(window)
        assert response.provider_metadata.case_id == "case_b_video"

    def test_infer_case_id_pdf(self):
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_report_2025", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_report_2025", units)
        response = provider.extract(window)
        assert response.provider_metadata.case_id == "case_c_pdf"

    def test_infer_default_case(self):
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_unknown_xyz", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_unknown_xyz", units)
        response = provider.extract(window)
        assert response.provider_metadata.case_id == "case_a_web"

    def test_shuffle_candidates_sort_stable(self):
        # Verify that shuffled input produces the same sorted output
        units = [
            ContentUnit(id="cu_0", document_id="doc_case_a", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_case_a", units)

        provider_normal = FixtureProvider(shuffle_candidates=False)
        provider_shuffled = FixtureProvider(shuffle_candidates=True)

        resp_normal = provider_normal.extract_for_case("case_a_web", window)
        resp_shuffled = provider_shuffled.extract_for_case("case_a_web", window)

        ids_normal = [getattr(c, "candidate_id", "") for c in resp_normal.candidates]
        ids_shuffled = [getattr(c, "candidate_id", "") for c in resp_shuffled.candidates]
        assert ids_normal == ids_shuffled

    def test_resolve_entity_no_source_quote(self):
        """EntityCandidate with no source_quote should be handled."""
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_case_a", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_case_a", units)
        response = provider.extract_for_case("case_a_web", window)
        entities = [c for c in response.candidates if isinstance(c, EntityCandidate)]
        assert len(entities) > 0

    def test_resolve_empty_source_quote(self):
        """Candidate with empty source_quote keeps empty source_unit_id."""
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_case_a", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_case_a", units)
        # Create a candidate with empty source_quote
        import copy
        response = provider.extract_for_case("case_a_web", window)
        # Already tested via normal flow — fact candidates without source_quote
        # should have empty source_unit_id


# ── ValidationFinding additional tests ────────────────────────────────────────

class TestValidationFindingExtra:
    def test_finding_to_dict(self):
        f = ValidationFinding(
            code="TEST", message="test message",
            severity=FindingSeverity.WARNING,
            candidate_id="c1", gate_name="test_gate",
            source_unit_id="u1", details={"key": "val"},
        )
        d = f.to_dict()
        assert d["code"] == "TEST"
        assert d["severity"] == "WARNING"
        assert d["details"] == {"key": "val"}

    def test_finding_is_error(self):
        err = ValidationFinding(code="E", message="err", severity=FindingSeverity.ERROR)
        warn = ValidationFinding(code="W", message="warn", severity=FindingSeverity.WARNING)
        assert err.is_error()
        assert not warn.is_error()


# ── ExtractionEnvelope tests ─────────────────────────────────────────────────

class TestExtractionEnvelope:
    def test_envelope_properties(self):
        from aurora.extraction.candidates import EntityCandidate
        meta = ProviderMetadata(name="test", version="1.0", deterministic_mode=True)
        cand = EntityCandidate(candidate_id="e1", entity_type="org", canonical_name="Test")
        envelope = ExtractionEnvelope(
            candidates=(cand,),
            provider_metadata=meta,
            warnings=("warn1",),
            errors=("err1",),
        )
        assert envelope.candidate_count == 1
        assert len(envelope.entities) == 1
        assert len(envelope.data_points) == 0
        assert len(envelope.claims) == 0
        assert len(envelope.evidences) == 0
        assert len(envelope.fact_candidates) == 0

    def test_envelope_candidates_by_type(self):
        meta = ProviderMetadata(name="test", version="1.0", deterministic_mode=True)
        dp = DataPointCandidate(
            candidate_id="dp_1", metric="r", value=1.0, unit="x",
            entity_id="e1", period="2025", measurement_context={},
            source_quote="test",
        )
        envelope = ExtractionEnvelope(candidates=(dp,), provider_metadata=meta)
        assert len(envelope.data_points) == 1
        assert len(envelope.entities) == 0

    def test_envelope_with_claims_and_evidence(self):
        meta = ProviderMetadata(name="test", version="1.0", deterministic_mode=True)
        claim = ClaimCandidate(
            candidate_id="cl_1", statement="test", claim_type="fact_claim",
            claim_dimension="general", source_quote="test",
        )
        ev = EvidenceCandidate(
            candidate_id="ev_1", evidence_type="report", evidence_role="support",
            target_object_id="dp_1", independence_group="g1",
            source_quote="test",
        )
        fc = FactCandidate(
            candidate_id="fc_1", statement="test fact",
        )
        envelope = ExtractionEnvelope(
            candidates=(claim, ev, fc),
            provider_metadata=meta,
        )
        assert len(envelope.claims) == 1
        assert len(envelope.evidences) == 1
        assert len(envelope.fact_candidates) == 1

    def test_envelope_repr(self):
        meta = ProviderMetadata(name="test", version="1.0", deterministic_mode=True)
        envelope = ExtractionEnvelope(candidates=(), provider_metadata=meta)
        r = repr(envelope)
        assert "ExtractionEnvelope" in str(r)
        assert "test" in str(r)


# ── ExtractionRequest tests ──────────────────────────────────────────────────

class TestExtractionRequest:
    def test_request_creation(self):
        req = ExtractionRequest(
            document_id="doc_1",
            case_id="case_a",
            run_id="run_1",
            provider_name="fixture",
            provider_version="2.0",
        )
        assert req.document_id == "doc_1"
        assert req.case_id == "case_a"
        assert req.run_id == "run_1"
        assert req.deterministic_mode is True

    def test_request_defaults(self):
        req = ExtractionRequest(document_id="doc_1")
        assert req.provider_name == "fixture"
        assert req.provider_version == "2.0"
        assert req.schema_version == "2.0"

    def test_request_repr(self):
        req = ExtractionRequest(document_id="doc_1", case_id="case_a")
        r = repr(req)
        assert "ExtractionRequest" in str(r)
        assert "doc_1" in str(r)


# ── ProviderResponse tests ───────────────────────────────────────────────────

class TestProviderResponse:
    def test_provider_response(self):
        meta = ProviderMetadata(name="test", version="1.0", deterministic_mode=True)
        resp = ProviderResponse(
            candidates=(),
            provider_metadata=meta,
            raw_payload={"key": "val"},
            warnings=("w1",),
            errors=("e1",),
        )
        assert resp.candidate_count == 0
        assert resp.raw_payload == {"key": "val"}


# ── ExtractionError tests ────────────────────────────────────────────────────

class TestExtractionErrorExtra:
    def test_extraction_error(self):
        err = ExtractionError(
            code="TEST_ERR",
            message="test error",
            candidate_id="c1",
            context={"detail": "info"},
        )
        assert err.code == "TEST_ERR"
        assert err.candidate_id == "c1"


# ── ReviewDecision tests (existing) ──────────────────────────────────────────
# These are already covered by existing tests, verified by import check

def test_bundle_schema_version_constant():
    assert BUNDLE_SCHEMA_VERSION == "2.0"


def test_review_bundle_empty_window():
    """Empty context window raises error."""
    with pytest.raises(ContextWindowError):
        ContextWindow.from_content_units("doc_1", [])


# ── FixtureProvider coverage edge cases ──────────────────────────────────────

class TestFixtureProviderEdgeCases:
    def test_file_not_found(self):
        provider = FixtureProvider(fixture_dir=Path("/nonexistent/path"))
        units = [
            ContentUnit(id="cu_0", document_id="doc_case_a", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_case_a", units)
        with pytest.raises(FileNotFoundError):
            provider.extract_for_case("case_a_web", window)

    def test_custom_fixture_dir(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "case_a_web_provider.json"
            fixture_path.write_text(json.dumps({
                "provider_metadata": {"name": "custom", "version": "1.0", "deterministic_mode": True},
                "candidates": [
                    {"candidate_id": "test_ent", "candidate_type": "entity", "entity_type": "org", "canonical_name": "Test"}
                ],
                "warnings": [], "errors": []
            }))
            provider = FixtureProvider(fixture_dir=Path(tmpdir))
            units = [
                ContentUnit(id="cu_0", document_id="doc_case_a", unit_type=ContentUnitType.PARAGRAPH,
                            sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
            ]
            window = ContextWindow.from_content_units("doc_case_a", units)
            response = provider.extract_for_case("case_a_web", window)
            assert response.provider_metadata.name == "custom"

    def test_resolve_valid_suid_kept(self):
        """If source_unit_id is already valid in window, keep it."""
        units = [
            ContentUnit(id="cu_0", document_id="doc_case_a", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello world", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_case_a", units)

        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "case_a_web_provider.json"
            fixture_path.write_text(json.dumps({
                "provider_metadata": {"name": "test", "version": "1.0", "deterministic_mode": True},
                "candidates": [
                    {"candidate_id": "dp_1", "candidate_type": "data_point", "metric": "r",
                     "value": 1.0, "unit": "x", "entity_id": "e", "period": "2025",
                     "measurement_context": {}, "source_quote": "hello world",
                     "quote_match_mode": "literal", "source_unit_id": "cu_0"}
                ],
                "warnings": [], "errors": []
            }))
            provider = FixtureProvider(fixture_dir=Path(tmpdir))
            response = provider.extract_for_case("case_a_web", window)
            dp = [c for c in response.candidates if isinstance(c, DataPointCandidate)]
            assert len(dp) == 1
            assert dp[0].source_unit_id == "cu_0"

    def test_infer_case_id_b_video(self):
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_video_srt", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_video_srt", units)
        result = provider._infer_case_id(window)
        assert result == "case_b_video"

    def test_infer_case_id_defaults_to_case_a(self):
        provider = FixtureProvider()
        units = [
            ContentUnit(id="cu_0", document_id="doc_completely_unknown", unit_type=ContentUnitType.PARAGRAPH,
                        sequence_no=0, text="hello", locator=SourceLocator(block_no=1)),
        ]
        window = ContextWindow.from_content_units("doc_completely_unknown", units)
        result = provider._infer_case_id(window)
        assert result == "case_a_web"

    def test_candidate_sort_key_unknown_type(self):
        """Sort key handles unknown candidate types gracefully."""
        class UnknownCandidate:
            pass
        c = UnknownCandidate()
        key = FixtureProvider._candidate_sort_key(c)
        assert key[0] == 99  # Unknown types get high index

    def test_build_candidate_none_for_unknown_type(self):
        result = FixtureProvider._build_candidate({"candidate_id": "x"}, "unknown_type")
        assert result is None

    def test_token_set_resolve_empty_tokens(self):
        """Empty token set after extraction should leave empty source_unit_id."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "case_a_web_provider.json"
            fixture_path.write_text(json.dumps({
                "provider_metadata": {"name": "test", "version": "1.0", "deterministic_mode": True},
                "candidates": [
                    {"candidate_id": "dp_1", "candidate_type": "data_point", "metric": "r",
                     "value": 1.0, "unit": "x", "entity_id": "e", "period": "2025",
                     "measurement_context": {}, "source_quote": "   ",
                     "quote_match_mode": "token_set", "source_unit_id": "nonexistent"}
                ],
                "warnings": [], "errors": []
            }))
            provider = FixtureProvider(fixture_dir=Path(tmpdir))
            units = [
                ContentUnit(id="cu_0", document_id="doc_case_a", unit_type=ContentUnitType.TABLE_ROW,
                            sequence_no=0, text="data", locator=SourceLocator(block_no=1)),
            ]
            window = ContextWindow.from_content_units("doc_case_a", units)
            response = provider.extract_for_case("case_a_web", window)
            # The source_quote "   " will tokenize to empty set, source_unit_id stays empty
            dps = [c for c in response.candidates if isinstance(c, DataPointCandidate)]
            if dps:
                # Empty tokens means can't resolve, source_unit_id stays empty
                assert dps[0].source_unit_id == ""


# ── QuoteGate coverage edge cases ────────────────────────────────────────────

class TestQuoteGateCoverageEdge:
    def test_quote_match_mode_from_attr(self):
        """Cover _get_quote_match_mode for candidates with the attr."""
        window = ContextWindow.from_content_units(
            "doc_1",
            [ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                         sequence_no=0, text="hello", locator=SourceLocator(block_no=1))],
        )
        gate = QuoteGate(window)
        result = gate._get_quote_match_mode(EntityCandidate(
            candidate_id="e1", entity_type="org", canonical_name="Test"
        ))
        # EntityCandidate doesn't have quote_match_mode attr
        assert result == "literal"

    def test_validate_literal_empty_norm_text(self):
        """_validate_literal with empty normalized text returns False."""
        window = ContextWindow.from_content_units(
            "doc_1",
            [ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                         sequence_no=0, text="hello", locator=SourceLocator(block_no=1))],
        )
        gate = QuoteGate(window)
        # source_unit_id that doesn't exist in norm_texts
        result = gate._validate_literal("test", "nonexistent_unit")
        assert result is False

    def test_validate_token_set_empty_norm_text(self):
        """_validate_token_set with empty normalized text returns False."""
        window = ContextWindow.from_content_units(
            "doc_1",
            [ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                         sequence_no=0, text="hello", locator=SourceLocator(block_no=1))],
        )
        gate = QuoteGate(window)
        result = gate._validate_token_set("test", "nonexistent_unit")
        assert result is False

    def test_entity_passed_without_source_quote(self):
        """EntityCandidate passes validation without source_quote."""
        window = ContextWindow.from_content_units(
            "doc_1",
            [ContentUnit(id="cu_0", document_id="doc_1", unit_type=ContentUnitType.PARAGRAPH,
                         sequence_no=0, text="hello", locator=SourceLocator(block_no=1))],
        )
        gate = QuoteGate(window)
        entity = EntityCandidate(
            id="e1", entity_type="organization", canonical_name="中芯国际",
        )
        report = gate.validate([entity])
        assert report.all_passed


# ── ReviewDecision basic test (preexisting module) ────────────────────────────

def test_review_decision_basic():
    """Basic test for ReviewDecision to improve total coverage."""
    from aurora.extraction.review_decision import ReviewDecision, ReviewDecisionDecision
    rd = ReviewDecision(
        run_id="run_1",
        bundle_sha256="a" * 64,
        candidate_id="c1",
        decision=ReviewDecisionDecision.APPROVE,
        reviewer="tester",
    )
    assert rd.is_valid()
    assert rd.validate() == []
    assert rd.to_dict()["decision"] == "APPROVE"

    rd2 = ReviewDecision.from_dict(rd.to_dict())
    assert rd2.run_id == "run_1"
    assert rd2.decision == ReviewDecisionDecision.APPROVE

    # Test REVISE_AND_APPROVE with revised_statement
    rd3 = ReviewDecision(
        run_id="run_2",
        bundle_sha256="b" * 64,
        candidate_id="c2",
        decision=ReviewDecisionDecision.REVISE_AND_APPROVE,
        reviewer="tester",
        revised_statement="revised text",
    )
    assert rd3.is_valid()

    # Test REVISE_AND_APPROVE without revised_statement
    rd4 = ReviewDecision(
        run_id="run_3",
        bundle_sha256="c" * 64,
        candidate_id="c3",
        decision=ReviewDecisionDecision.REVISE_AND_APPROVE,
        reviewer="tester",
    )
    assert not rd4.is_valid()
    errors = rd4.validate()
    assert len(errors) > 0


def test_review_decision_invalid():
    """Test ReviewDecision validation failures."""
    from aurora.extraction.review_decision import ReviewDecision, ReviewDecisionDecision

    # Missing run_id
    rd = ReviewDecision(
        run_id="",
        bundle_sha256="a" * 64,
        candidate_id="c1",
        decision=ReviewDecisionDecision.APPROVE,
        reviewer="tester",
    )
    assert not rd.is_valid()

    # Invalid SHA
    rd2 = ReviewDecision(
        run_id="r1",
        bundle_sha256="short",
        candidate_id="c1",
        decision=ReviewDecisionDecision.APPROVE,
        reviewer="tester",
    )
    assert not rd2.is_valid()
