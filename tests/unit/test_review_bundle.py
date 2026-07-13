"""Unit tests for ReviewBundle V2 — immutability, canonicalized JSON hash, validation_findings."""

import dataclasses

from aurora.core.models.common import SourceLocator
from aurora.core.models.document import ContentUnit
from aurora.core.models.enums import ContentUnitType
from aurora.extraction.candidates import ClaimCandidate, EntityCandidate
from aurora.extraction.context_window import ContentUnitRef, ContextWindow
from aurora.extraction.findings import ValidationFinding
from aurora.extraction.review_bundle import ExtractionError, ReviewBundle, BUNDLE_SCHEMA_VERSION


def _make_window_units(doc_id: str = "doc_1") -> tuple[ContentUnitRef, ...]:
    units = [
        ContentUnit(
            id=f"cu_{doc_id}_0",
            document_id=doc_id,
            unit_type=ContentUnitType.PARAGRAPH,
            sequence_no=0,
            text="hello world",
            locator=SourceLocator(block_no=1),
        ),
    ]
    window = ContextWindow.from_content_units(doc_id, units)
    return window.units


def _make_errors() -> tuple[str, ...]:
    return ("TEST_ERROR: Test error message",)


class TestReviewBundleImmutability:
    """ReviewBundle must be frozen — G1-4: no in-place modification after creation."""

    def test_bundle_is_frozen(self):
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="2.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
        )
        assert hasattr(bundle, "review_bundle_id")
        try:
            bundle.document_id = "modified"
            assert False, "Should have raised FrozenInstanceError"
        except dataclasses.FrozenInstanceError:
            pass

    def test_original_units_not_modified_by_window_creation(self):
        """G1-4: original ContentUnits must not be modified by the extraction pipeline."""
        unit = ContentUnit(
            id="cu_test",
            document_id="doc_test",
            unit_type=ContentUnitType.PARAGRAPH,
            sequence_no=0,
            text="original text",
            locator=SourceLocator(block_no=1),
        )
        original_id = unit.id
        original_text = unit.text

        window = ContextWindow.from_content_units("doc_test", [unit])
        bundle = ReviewBundle.create(
            document_id="doc_test",
            provider_name="fixture",
            provider_version="2.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window.units,
        )

        assert unit.id == original_id
        assert unit.text == original_text


class TestReviewBundleSha256:
    """G1-5: ReviewBundle SHA-256 must be deterministic via canonicalized JSON."""

    def test_sha256_length_is_64(self):
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="2.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
        )
        assert len(bundle.bundle_sha256) == 64
        assert all(c in "0123456789abcdef" for c in bundle.bundle_sha256)

    def test_same_data_same_sha256(self):
        """Same data inputs → same SHA-256, regardless of UUIDs."""
        from datetime import datetime, timezone
        window_units = _make_window_units("doc_A")
        fixed_time = datetime(2026, 7, 13, 0, 0, 0, tzinfo=timezone.utc)

        candidate = EntityCandidate(
            candidate_id="ent_001",
            entity_type="organization",
            canonical_name="Test Co",
        )

        b1 = ReviewBundle(
            review_bundle_id="bundle_fixed",
            run_id="run_fixed",
            document_id="doc_A",
            provider_name="fixture",
            provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(candidate,),
            content_unit_window=window_units,
            validation_findings=(),
            context_hashes={},
            errors=(),
            schema_version=BUNDLE_SCHEMA_VERSION,
            case_id="test",
        )
        b2 = ReviewBundle(
            review_bundle_id="bundle_fixed",
            run_id="run_fixed",
            document_id="doc_A",
            provider_name="fixture",
            provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(candidate,),
            content_unit_window=window_units,
            validation_findings=(),
            context_hashes={},
            errors=(),
            schema_version=BUNDLE_SCHEMA_VERSION,
            case_id="test",
        )
        assert b1.bundle_sha256 == b2.bundle_sha256

    def test_sha256_includes_errors(self):
        window_units = _make_window_units()
        fixed_time = __import__("datetime").datetime(2026, 7, 13, 0, 0, 0)

        b1 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(),
            content_unit_window=window_units,
            errors=(),
        )
        b2 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(),
            content_unit_window=window_units,
            errors=("ERROR_X",),
        )
        assert b1.bundle_sha256 != b2.bundle_sha256

    def test_sha256_includes_validation_findings(self):
        window_units = _make_window_units()
        fixed_time = __import__("datetime").datetime(2026, 7, 13, 0, 0, 0)

        finding = ValidationFinding(
            code="TEST", message="test finding", candidate_id="c1",
        )

        b1 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(),
            content_unit_window=window_units,
            validation_findings=(),
        )
        b2 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(),
            content_unit_window=window_units,
            validation_findings=(finding,),
        )
        assert b1.bundle_sha256 != b2.bundle_sha256

    def test_sha256_includes_candidates(self):
        window_units = _make_window_units()
        fixed_time = __import__("datetime").datetime(2026, 7, 13, 0, 0, 0)

        candidate = EntityCandidate(
            candidate_id="ent_001",
            entity_type="organization",
            canonical_name="Test Co",
        )

        b1 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(),
            content_unit_window=window_units,
        )
        b2 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(candidate,),
            content_unit_window=window_units,
        )
        assert b1.bundle_sha256 != b2.bundle_sha256

    def test_sha256_includes_context_hashes(self):
        window_units = _make_window_units()
        fixed_time = __import__("datetime").datetime(2026, 7, 13, 0, 0, 0)

        b1 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(),
            content_unit_window=window_units,
            context_hashes={},
        )
        b2 = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=fixed_time,
            candidates=(),
            content_unit_window=window_units,
            context_hashes={"window": "abc123"},
        )
        assert b1.bundle_sha256 != b2.bundle_sha256


class TestReviewBundleProperties:
    """ReviewBundle metadata and computed properties."""

    def test_to_json_dict(self):
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="2.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
            case_id="case_a_web",
        )
        d = bundle.to_json_dict()
        assert d["review_bundle_id"].startswith("bundle_")
        assert d["run_id"].startswith("run_")
        assert d["provider_name"] == "fixture"
        assert d["provider_version"] == "2.0"
        assert d["deterministic_mode"] is True
        assert d["schema_version"] == BUNDLE_SCHEMA_VERSION
        assert d["case_id"] == "case_a_web"
        assert d["candidate_count"] == 0
        assert d["error_count"] == 0
        assert len(d["bundle_sha256"]) == 64
        assert "context_hashes" in d

    def test_candidate_count(self):
        window_units = _make_window_units()
        candidate = EntityCandidate(
            candidate_id="e1", entity_type="organization", canonical_name="Test Co"
        )
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="2.0",
            deterministic_mode=True,
            candidates=(candidate,),
            content_unit_window=window_units,
        )
        assert bundle.candidate_count == 1

    def test_accepted_rejected_counts(self):
        window_units = _make_window_units()
        finding = ValidationFinding(
            code="TEST_ERR", message="test",
            candidate_id="bad_cand",
        )
        candidate_good = EntityCandidate(
            candidate_id="good_cand", entity_type="org", canonical_name="Good"
        )
        candidate_bad = EntityCandidate(
            candidate_id="bad_cand", entity_type="org", canonical_name="Bad"
        )
        bundle = ReviewBundle(
            review_bundle_id="b1", run_id="r1",
            document_id="doc_1",
            provider_name="fixture", provider_version="2.0",
            deterministic_mode=True,
            created_at=__import__("datetime").datetime(2026, 7, 13, 0, 0, 0),
            candidates=(candidate_good, candidate_bad),
            content_unit_window=window_units,
            validation_findings=(finding,),
        )
        assert bundle.accepted_count == 1
        assert bundle.rejected_count == 1
        assert bundle.accepted_candidate_ids == ("good_cand",)
        assert bundle.rejected_candidate_ids == ("bad_cand",)
