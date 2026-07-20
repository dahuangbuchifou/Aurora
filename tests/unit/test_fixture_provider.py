"""Unit tests for FixtureProvider V2 — reads from independent provider_responses fixtures."""

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


def _make_window(case_id: str, doc_id: str = "doc_test") -> ContextWindow:
    """Create a minimal ContextWindow that the provider can infer case_id from."""
    units = [
        ContentUnit(
            id=f"cu_{case_id}_0000",
            document_id=doc_id,
            unit_type=ContentUnitType.PARAGRAPH,
            sequence_no=0,
            text="placeholder text for window construction",
            locator=SourceLocator(block_no=1),
        ),
    ]
    return ContextWindow.from_content_units(doc_id, units)


class TestFixtureProviderV2:
    """The V2 FixtureProvider reads from provider_responses, not expected_results."""

    @pytest.mark.parametrize(
        "case_id,expected_entities,expected_dps,expected_claims,expected_evs,expected_fcs",
        [
            # V2 provider fixture counts (independent from expected_results)
            ("case_a_web", 1, 2, 3, 2, 1),
            ("case_b_video", 3, 0, 4, 1, 0),
            ("case_c_pdf", 1, 2, 2, 2, 1),
        ],
    )
    def test_case_completeness(
        self, case_id, expected_entities, expected_dps,
        expected_claims, expected_evs, expected_fcs,
    ):
        window = _make_window(case_id, f"doc_{case_id}")
        provider = FixtureProvider()
        response = provider.extract_for_case(case_id, window)

        entities = [c for c in response.candidates if isinstance(c, EntityCandidate)]
        dps = [c for c in response.candidates if isinstance(c, DataPointCandidate)]
        claims = [c for c in response.candidates if isinstance(c, ClaimCandidate)]
        evs = [c for c in response.candidates if isinstance(c, EvidenceCandidate)]
        fcs = [c for c in response.candidates if isinstance(c, FactCandidate)]

        assert len(entities) == expected_entities, f"Entity count mismatch for {case_id}"
        assert len(dps) == expected_dps, f"DataPoint count mismatch for {case_id}"
        assert len(claims) == expected_claims, f"Claim count mismatch for {case_id}"
        assert len(evs) == expected_evs, f"Evidence count mismatch for {case_id}"
        assert len(fcs) == expected_fcs, f"FactCandidate count mismatch for {case_id}"

    def test_provider_is_deterministic(self):
        """Same input must produce identical output (G1-5 pre-check)."""
        window1 = _make_window("case_a_web", "doc_a1")
        window2 = _make_window("case_a_web", "doc_a2")

        provider1 = FixtureProvider()
        provider2 = FixtureProvider()

        resp1 = provider1.extract_for_case("case_a_web", window1)
        resp2 = provider2.extract_for_case("case_a_web", window2)

        assert len(resp1.candidates) == len(resp2.candidates)
        for c1, c2 in zip(resp1.candidates, resp2.candidates):
            assert type(c1) == type(c2)
            assert getattr(c1, "candidate_id", "") == getattr(c2, "candidate_id", "")

    def test_provider_response_has_metadata(self):
        window = _make_window("case_a_web")
        provider = FixtureProvider()
        response = provider.extract_for_case("case_a_web", window)

        assert response.provider_metadata.name == "fixture"
        assert response.provider_metadata.version == "2.0"
        assert response.provider_metadata.deterministic_mode is True
        assert response.provider_metadata.case_id == "case_a_web"

    def test_source_unit_id_present(self):
        """All quote-bearing candidates must have source_unit_id."""
        window = _make_window("case_c_pdf")
        provider = FixtureProvider()
        response = provider.extract_for_case("case_c_pdf", window)

        for c in response.candidates:
            if isinstance(c, (DataPointCandidate, ClaimCandidate, EvidenceCandidate)):
                assert c.source_unit_id, (
                    f"{c.candidate_id}: source_unit_id should be set"
                )

    def test_no_auto_fact_promotion(self):
        """OPT-069: FactCandidate.promotable is NEVER set from Provider.

        FixtureProvider drops promotable at DTO construction.
        SafetyGate catches it in raw_payload as PROVIDER_OVERRIDE_FIELD.
        Only ReviewDecision can set promotable=True.
        """
        window = _make_window("case_a_web")
        provider = FixtureProvider()
        response = provider.extract_for_case("case_a_web", window)

        for fc in response.candidates:
            if isinstance(fc, FactCandidate):
                assert fc.promotable is False, (
                    f"{fc.candidate_id}: OPT-069 — Provider must not set promotable"
                )

    def test_independent_from_expected_results(self):
        """Provider fixture dir is independent — not reading from expected/."""
        provider = FixtureProvider()
        assert "provider_responses" in str(provider._fixture_dir)


class TestFixtureProviderOrdering:
    """Candidate ordering must be deterministic and stable (G1-6, G1-7)."""

    def test_candidates_sorted_deterministically(self):
        window1 = _make_window("case_a_web")
        window2 = _make_window("case_a_web")

        provider = FixtureProvider()
        e1 = provider.extract_for_case("case_a_web", window1)
        e2 = provider.extract_for_case("case_a_web", window2)

        ids1 = [getattr(c, "candidate_id", "") for c in e1.candidates]
        ids2 = [getattr(c, "candidate_id", "") for c in e2.candidates]
        assert ids1 == ids2, "Candidate order must be stable"

    def test_type_order_is_consistent(self):
        window = _make_window("case_a_web")
        provider = FixtureProvider()
        response = provider.extract_for_case("case_a_web", window)

        type_sequence = [type(c) for c in response.candidates]
        for prev, curr in zip(type_sequence, type_sequence[1:]):
            assert _type_order(prev) <= _type_order(curr), (
                f"Order violation: {prev} before {curr}"
            )


def _type_order(candidate_type) -> int:
    mapping = {
        EntityCandidate: 0,
        DataPointCandidate: 1,
        ClaimCandidate: 2,
        EvidenceCandidate: 3,
        FactCandidate: 4,
    }
    return mapping.get(candidate_type, 99)
