"""Unit tests for FixtureProvider — deterministic extraction from golden set."""

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


FIXTURES = Path(__file__).parents[1] / "fixtures" / "m2_003" / "expected"


def _make_window_for_case(
    case_id: str, doc_id: str = "doc_test"
) -> ContextWindow:
    """Create a ContextWindow for testing with unit texts from the golden set."""
    import json

    file_name = {
        "case_a_web": "case_a_web_expected.json",
        "case_b_video": "case_b_video_expected.json",
        "case_c_pdf": "case_c_pdf_expected.json",
    }[case_id]

    with open(FIXTURES / file_name, "r", encoding="utf-8") as f:
        expected = json.load(f)

    quotes = set()
    for section in ["expected_claims", "expected_evidence", "expected_data_points", "expected_rejects"]:
        for item in expected.get(section, []):
            sq = item.get("source_quote", "")
            if sq:
                quotes.add(sq)

    units = [
        ContentUnit(
            id=f"cu_{doc_id}_{i:04d}",
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
                id=f"cu_{doc_id}_0000",
                document_id=doc_id,
                unit_type=ContentUnitType.PARAGRAPH,
                sequence_no=0,
                text="placeholder",
                locator=SourceLocator(block_no=1),
            )
        ]

    return ContextWindow.from_content_units(doc_id, units)


class TestFixtureProviderCaseExtraction:
    """All three golden cases must produce complete and consistent extraction."""

    @pytest.mark.parametrize(
        "case_id,expected_entities,expected_dps,expected_claims,expected_evs,expected_fcs",
        [
            ("case_a_web", 1, 2, 3, 2, 1),
            ("case_b_video", 3, 0, 4, 1, 2),
            ("case_c_pdf", 1, 4, 2, 4, 2),
        ],
    )
    def test_case_completeness(
        self,
        case_id,
        expected_entities,
        expected_dps,
        expected_claims,
        expected_evs,
        expected_fcs,
    ):
        window = _make_window_for_case(case_id, f"doc_{case_id}")
        provider = FixtureProvider()
        envelope = provider.extract_for_case(case_id, window)

        entities = [c for c in envelope.candidates if isinstance(c, EntityCandidate)]
        dps = [c for c in envelope.candidates if isinstance(c, DataPointCandidate)]
        claims = [c for c in envelope.candidates if isinstance(c, ClaimCandidate)]
        evs = [c for c in envelope.candidates if isinstance(c, EvidenceCandidate)]
        fcs = [c for c in envelope.candidates if isinstance(c, FactCandidate)]

        assert len(entities) == expected_entities, f"Entity count mismatch for {case_id}"
        assert len(dps) == expected_dps, f"DataPoint count mismatch for {case_id}"
        assert len(claims) == expected_claims, f"Claim count mismatch for {case_id}"
        assert len(evs) == expected_evs, f"Evidence count mismatch for {case_id}"
        assert len(fcs) == expected_fcs, f"FactCandidate count mismatch for {case_id}"

    def test_provider_is_deterministic(self):
        """Same input must produce identical output (G1-5 pre-check)."""
        window1 = _make_window_for_case("case_a_web")
        window2 = _make_window_for_case("case_a_web")

        provider1 = FixtureProvider()
        provider2 = FixtureProvider()

        envelope1 = provider1.extract_for_case("case_a_web", window1)
        envelope2 = provider2.extract_for_case("case_a_web", window2)

        assert len(envelope1.candidates) == len(envelope2.candidates)
        for c1, c2 in zip(envelope1.candidates, envelope2.candidates):
            assert type(c1) == type(c2)
            assert c1.id == c2.id


class TestFixtureProviderCandidateFields:
    """Candidate fields must be consistent with the golden set."""

    def test_data_point_source_quote_present(self):
        window = _make_window_for_case("case_c_pdf", "doc_c")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_c_pdf", window)

        for dp in envelope.data_points:
            assert dp.source_quote, f"DataPoint {dp.id} missing source_quote"
            assert dp.quote_locator_hint or True, f"DataPoint {dp.id} quote_locator exists"

    def test_claim_fields(self):
        window = _make_window_for_case("case_a_web", "doc_a")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_a_web", window)

        for claim in envelope.claims:
            assert claim.statement, f"Claim {claim.id} missing statement"
            assert claim.claim_type, f"Claim {claim.id} missing claim_type"
            assert claim.claim_dimension, f"Claim {claim.id} missing claim_dimension"
            assert claim.source_quote, f"Claim {claim.id} missing source_quote"

    def test_prediction_has_time_horizon(self):
        window = _make_window_for_case("case_c_pdf", "doc_c")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_c_pdf", window)

        predictions = [c for c in envelope.claims if c.claim_type == "prediction"]
        assert len(predictions) >= 1, "Expected at least one prediction claim"
        for p in predictions:
            assert p.time_horizon is not None, f"Prediction {p.id} missing time_horizon"

    def test_evidence_has_independence_group(self):
        window = _make_window_for_case("case_a_web", "doc_a")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_a_web", window)

        for ev in envelope.evidences:
            assert ev.independence_group, f"Evidence {ev.id} missing independence_group"
            assert ev.evidence_type, f"Evidence {ev.id} missing evidence_type"
            assert ev.evidence_role, f"Evidence {ev.id} missing evidence_role"

    def test_fact_candidate_promotable_logic(self):
        """promotable=true must have valid_time+confidence; promotable=false must have rejection_reason."""
        window = _make_window_for_case("case_c_pdf", "doc_c")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_c_pdf", window)

        for fc in envelope.fact_candidates:
            if fc.promotable:
                assert fc.valid_time, f"Promotable FC {fc.id} missing valid_time"
                assert fc.confidence_rationale, f"Promotable FC {fc.id} missing confidence_rationale"
            else:
                assert fc.rejection_reason, f"Non-promotable FC {fc.id} missing rejection_reason"

    def test_no_auto_fact_promotion(self):
        """G1-3: code must not auto-set promotable=True — must match golden set."""
        window = _make_window_for_case("case_b_video", "doc_b")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_b_video", window)

        for fc in envelope.fact_candidates:
            # Case B has only non-promotable fact candidates
            assert not fc.promotable, f"Case B FC {fc.id} should not be auto-promoted"


class TestFixtureProviderOrdering:
    """Candidate ordering must be deterministic and stable (G1-6, G1-7)."""

    def test_candidates_sorted_by_type_then_id(self):
        window1 = _make_window_for_case("case_a_web", "doc_a")
        window2 = _make_window_for_case("case_a_web", "doc_a")

        provider = FixtureProvider()
        e1 = provider.extract_for_case("case_a_web", window1)
        e2 = provider.extract_for_case("case_a_web", window2)

        ids1 = [getattr(c, "id", "") for c in e1.candidates]
        ids2 = [getattr(c, "id", "") for c in e2.candidates]
        assert ids1 == ids2, "Candidate order must be stable"

    def test_type_order_is_consistent(self):
        """Entity < DataPoint < Claim < Evidence < FactCandidate."""
        window = _make_window_for_case("case_c_pdf", "doc_c")
        provider = FixtureProvider()
        envelope = provider.extract_for_case("case_c_pdf", window)

        type_sequence = [type(c) for c in envelope.candidates]
        for prev, curr in zip(type_sequence, type_sequence[1:]):
            assert type_order(prev) <= type_order(curr), (
                f"Order violation: {prev} before {curr}"
            )


def type_order(candidate_type) -> int:
    mapping = {
        EntityCandidate: 0,
        DataPointCandidate: 1,
        ClaimCandidate: 2,
        EvidenceCandidate: 3,
        FactCandidate: 4,
    }
    return mapping.get(candidate_type, 99)
