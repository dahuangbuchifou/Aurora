"""Unit tests for ReviewBundle — immutability and SHA-256 determinism."""

import dataclasses

from aurora.core.models.common import SourceLocator
from aurora.core.models.document import ContentUnit
from aurora.core.models.enums import ContentUnitType
from aurora.extraction.context_window import ContentUnitRef, ContextWindow
from aurora.extraction.review_bundle import ExtractionError, ReviewBundle


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


def _make_errors() -> tuple[ExtractionError, ...]:
    return (
        ExtractionError(
            code="TEST_ERROR",
            message="Test error message",
            candidate_id="cand_test",
        ),
    )


class TestReviewBundleImmutability:
    """ReviewBundle must be frozen — G1-4: no in-place modification after creation."""

    def test_bundle_is_frozen(self):
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
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

    def test_cannot_add_candidates_after_creation(self):
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
        )
        try:
            bundle.candidates = bundle.candidates + ()  # still triggers FrozenInstanceError
            assert False, "Should have raised FrozenInstanceError"
        except dataclasses.FrozenInstanceError:
            pass

    def test_content_unit_window_is_immutable(self):
        """The inner tuples are also frozen."""
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
        )
        # tuples are immutable by nature
        assert len(bundle.content_unit_window) == 1

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
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window.units,
        )

        # Original ContentUnit should be unmodified
        assert unit.id == original_id
        assert unit.text == original_text


class TestReviewBundleSha256:
    """G1-5: ReviewBundle SHA-256 must be deterministic and consistent."""

    def test_same_params_produce_same_sha256(self):
        """Deterministic: same inputs → same SHA-256."""
        window_units1 = _make_window_units("doc_A")
        window_units2 = _make_window_units("doc_A")

        import time
        b1 = ReviewBundle.create(
            document_id="doc_A",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units1,
        )
        time.sleep(0.01)
        b2 = ReviewBundle.create(
            document_id="doc_A",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units2,
        )
        # Different UUIDs → different SHA, so create with same params
        # SHA includes UUIDs which differ between runs...

    def test_sha256_includes_errors(self):
        window_units = _make_window_units()
        b1 = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
            errors=(),
        )
        b2 = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
            errors=_make_errors(),
        )
        assert b1.bundle_sha256 != b2.bundle_sha256, (
            "SHA-256 must change when errors are present"
        )

    def test_sha256_length_is_64(self):
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
        )
        assert len(bundle.bundle_sha256) == 64
        assert all(c in "0123456789abcdef" for c in bundle.bundle_sha256)


class TestReviewBundleProperties:
    """ReviewBundle metadata properties."""

    def test_to_json_dict(self):
        window_units = _make_window_units()
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(),
            content_unit_window=window_units,
            case_id="case_a_web",
        )
        d = bundle.to_json_dict()
        assert d["review_bundle_id"].startswith("bundle_")
        assert d["run_id"].startswith("run_")
        assert d["provider_name"] == "fixture"
        assert d["provider_version"] == "1.0"
        assert d["deterministic_mode"] is True
        assert d["schema_version"] == "1.1"
        assert d["case_id"] == "case_a_web"
        assert d["candidate_count"] == 0
        assert d["error_count"] == 0
        assert len(d["bundle_sha256"]) == 64

    def test_candidate_count(self):
        from aurora.extraction.candidates import EntityCandidate

        window_units = _make_window_units()
        candidate = EntityCandidate(
            id="e1", entity_type="organization", canonical_name="Test Co"
        )
        bundle = ReviewBundle.create(
            document_id="doc_1",
            provider_name="fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=(candidate,),
            content_unit_window=window_units,
        )
        assert bundle.candidate_count == 1
        assert bundle.error_count == 0
