"""Integration test: complete M2-003B vertical slice.

Path: ContentUnit → ContextWindow → FixtureProvider → ExtractionEnvelope
      → Quote Gate → ReviewBundle (with deterministic SHA-256)

Covers G1-1 through G1-7 pre-checks.
"""

import json
from pathlib import Path

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
from aurora.extraction.providers.fixture_provider import FixtureProvider
from aurora.extraction.quote_gate import QuoteGate
from aurora.extraction.review_bundle import ExtractionError, ReviewBundle


FIXTURES = Path(__file__).parents[1] / "fixtures" / "m2_003" / "expected"


def _load_expected(case_id: str) -> dict:
    file_name = {
        "case_a_web": "case_a_web_expected.json",
        "case_b_video": "case_b_video_expected.json",
        "case_c_pdf": "case_c_pdf_expected.json",
    }[case_id]
    with open(FIXTURES / file_name, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_context_window(case_id: str, doc_id: str = "doc_test") -> ContextWindow:
    """Build a ContextWindow from golden set source_quotes."""
    expected = _load_expected(case_id)

    quotes = set()
    for section in ["expected_claims", "expected_evidence", "expected_data_points", "expected_rejects"]:
        for item in expected.get(section, []):
            sq = item.get("source_quote", "")
            if sq:
                quotes.add(sq)

    units = [
        ContentUnit(
            id=f"cu_{case_id}_{i:04d}",
            document_id=doc_id,
            unit_type=ContentUnitType.PARAGRAPH,
            sequence_no=i,
            text=quote,
            locator=SourceLocator(block_no=i + 1),
        )
        for i, quote in enumerate(sorted(quotes))
    ]

    if not units:
        units = [
            ContentUnit(
                id=f"cu_{case_id}_0000",
                document_id=doc_id,
                unit_type=ContentUnitType.PARAGRAPH,
                sequence_no=0,
                text="placeholder",
                locator=SourceLocator(block_no=1),
            )
        ]

    return ContextWindow.from_content_units(doc_id, units)


class TestVerticalSliceCaseA:
    """Complete extraction cycle for Case A (web)."""

    def test_full_vertical_slice(self):
        # Step 1: Build ContextWindow
        window = _build_context_window("case_a_web")
        assert len(window) > 0

        # Step 2: Extract candidates
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_a_web", window)
        assert len(envelope.candidates) == 9
        assert envelope.provider_metadata.name == "fixture"
        assert envelope.provider_metadata.deterministic_mode is True

        # Step 3: Quote Gate validation
        gate = QuoteGate(window)
        report = gate.validate(envelope.candidates)
        assert report.all_passed, f"Quote failures: {[f.candidate_id for f in report.failures]}"

        # Step 4: Build ReviewBundle
        errors: list[ExtractionError] = [
            ExtractionError(code=f.code if hasattr(f, 'code') else "QUOTE_GATE_FAILURE", 
                          message=f.reason, candidate_id=f.candidate_id)
            for f in report.failures
        ]
        bundle = ReviewBundle.create(
            document_id=window.document_id,
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=envelope.candidates,
            content_unit_window=window.units,
            errors=tuple(errors),
            case_id="case_a_web",
        )

        # Verify bundle properties
        assert bundle.candidate_count == 9
        assert bundle.error_count == 0
        assert len(bundle.bundle_sha256) == 64

    def test_deterministic_sha256(self):
        """G1-5: Two runs must produce identical SHA-256 (with same UUIDs)."""
        from datetime import datetime

        window = _build_context_window("case_a_web")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_a_web", window)

        fixed_time = datetime(2026, 7, 13, 0, 0, 0)

        # Use fixed UUIDs for deterministic SHA comparison
        bundle1 = ReviewBundle(
            review_bundle_id="bundle_fixed_1",
            run_id="run_fixed_1",
            document_id=window.document_id,
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=envelope.candidates,
            content_unit_window=window.units,
            errors=(),
            schema_version="1.1",
            case_id="case_a_web",
        )
        bundle2 = ReviewBundle(
            review_bundle_id="bundle_fixed_1",
            run_id="run_fixed_1",
            document_id=window.document_id,
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=envelope.candidates,
            content_unit_window=window.units,
            errors=(),
            schema_version="1.1",
            case_id="case_a_web",
        )
        assert bundle1.bundle_sha256 == bundle2.bundle_sha256

        bundle3 = ReviewBundle(
            review_bundle_id="bundle_fixed_2",
            run_id="run_fixed_2",
            document_id=window.document_id,
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=envelope.candidates,
            content_unit_window=window.units,
            errors=(),
            schema_version="1.1",
            case_id="case_a_web",
        )
        # Different UUIDs should NOT affect SHA-256 (data-only hash)
        assert bundle1.bundle_sha256 == bundle3.bundle_sha256, (
            "Same data with different UUIDs should produce same SHA-256"
        )

    def test_original_unit_not_modified(self):
        """G1-4: ContentUnit originals must not be modified by the pipeline."""
        unit = ContentUnit(
            id="cu_original",
            document_id="doc_test",
            unit_type=ContentUnitType.PARAGRAPH,
            sequence_no=0,
            text="original text",
            locator=SourceLocator(block_no=1),
        )
        original_text = unit.text
        original_id = unit.id

        window = ContextWindow.from_content_units("doc_test", [unit])
        provider = FixtureProvider()
        provider.extract(window)

        assert unit.text == original_text
        assert unit.id == original_id


class TestVerticalSliceAllThreeCases:
    """Verify the complete vertical slice works for all three cases."""

    @pytest.mark.parametrize("case_id", ["case_a_web", "case_b_video", "case_c_pdf"])
    def test_complete_pipeline(self, case_id):
        window = _build_context_window(case_id)
        provider = FixtureProvider()
        envelope = provider.extract_for_case(case_id, window)

        # Quote Gate
        gate = QuoteGate(window)
        report = gate.validate(envelope.candidates)
        assert report.all_passed, (
            f"{case_id}: Quote Gate failures: "
            f"{[(f.candidate_id, f.reason[:60]) for f in report.failures]}"
        )

        # Build bundle
        bundle = ReviewBundle.create(
            document_id=window.document_id,
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=envelope.candidates,
            content_unit_window=window.units,
            case_id=case_id,
        )

        assert bundle.candidate_count > 0
        assert len(bundle.bundle_sha256) == 64

    @pytest.mark.parametrize("case_id", ["case_a_web", "case_b_video", "case_c_pdf"])
    def test_candidate_order_stable(self, case_id):
        """G1-6: Candidate ordering must be stable across runs."""
        window1 = _build_context_window(case_id)
        window2 = _build_context_window(case_id)

        provider = FixtureProvider()
        e1 = provider.extract_for_case(case_id, window1)
        e2 = provider.extract_for_case(case_id, window2)

        ids1 = [getattr(c, "id", "") for c in e1.candidates]
        ids2 = [getattr(c, "id", "") for c in e2.candidates]
        assert ids1 == ids2, f"{case_id}: ordering drift"

    @pytest.mark.parametrize("case_id", ["case_a_web", "case_b_video", "case_c_pdf"])
    def test_candidate_core_fields_stable(self, case_id):
        """G1-7: Core fields must be stable across runs."""
        window1 = _build_context_window(case_id)
        window2 = _build_context_window(case_id)

        provider = FixtureProvider()
        e1 = provider.extract_for_case(case_id, window1)
        e2 = provider.extract_for_case(case_id, window2)

        for c1, c2 in zip(e1.candidates, e2.candidates):
            assert type(c1) == type(c2), f"{case_id}: type drift"
            # Core fields that must not drift
            for field in ["id", "statement", "claim_type", "claim_dimension",
                          "metric", "value", "unit", "entity_id",
                          "canonical_name", "entity_type", "promotable"]:
                v1 = getattr(c1, field, None)
                v2 = getattr(c2, field, None)
                assert v1 == v2, f"{case_id} candidate {getattr(c1,'id','?')}: field '{field}' drifted: {v1} != {v2}"


class TestNoAutoFactPromotion:
    """G1-3: No code path should auto-set promotable=True on FactCandidates."""

    def test_fact_promotion_matches_golden_only(self):
        for case_id in ["case_a_web", "case_b_video", "case_c_pdf"]:
            expected = _load_expected(case_id)
            golden_fcs = {
                fc["id"]: fc["promotable"]
                for fc in expected.get("expected_fact_candidates", [])
            }

            window = _build_context_window(case_id)
            provider = FixtureProvider()
            envelope = provider.extract_for_case(case_id, window)
            extracted_fcs = {fc.id: fc.promotable for fc in envelope.fact_candidates}

            assert extracted_fcs == golden_fcs, (
                f"{case_id}: promotable mismatch. "
                f"Golden: {golden_fcs}, Extracted: {extracted_fcs}"
            )
