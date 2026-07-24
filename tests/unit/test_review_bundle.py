"""Unit tests for ReviewBundle V2 — immutability, canonicalized JSON hash, validation_findings."""

import dataclasses
import hashlib
import json

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


def _make_subject_hash_claim(
    subject_entity_ids: list[str] | None = None,
) -> ClaimCandidate:
    payload: dict[str, object] = {
        "candidate_id": "cl_cand_subject_hash_001",
        "statement": "Revenue increased year over year.",
        "claim_type": "interpretation",
        "claim_dimension": "financial_performance",
        "asserted_by": "issuer",
        "source_quote": "Revenue increased year over year.",
        "source_unit_id": "cu_doc_subject_hash_0",
    }
    if subject_entity_ids is not None:
        payload["subject_entity_ids"] = subject_entity_ids
    return ClaimCandidate(**payload)


def _make_subject_hash_bundle(candidate: ClaimCandidate) -> ReviewBundle:
    return ReviewBundle.create(
        document_id="doc_subject_hash",
        provider_name="fixture",
        provider_version="2.0",
        deterministic_mode=True,
        candidates=(candidate,),
        content_unit_window=_make_window_units("doc_subject_hash"),
        run_id="run_subject_hash",
        case_id="case_subject_hash",
    )


def test_empty_claim_subject_preserves_legacy_bundle_hash() -> None:
    candidate = _make_subject_hash_claim()
    bundle = _make_subject_hash_bundle(candidate)
    legacy_candidate = candidate.model_dump()
    assert legacy_candidate.pop("subject_entity_ids") == []

    legacy_payload = {
        "run_id": bundle.run_id,
        "document_id": bundle.document_id,
        "provider_name": bundle.provider_name,
        "provider_version": bundle.provider_version,
        "deterministic_mode": bundle.deterministic_mode,
        "schema_version": bundle.schema_version,
        "case_id": bundle.case_id,
        "prompt_version": bundle.prompt_version,
        "profile_version": bundle.profile_version,
        "provider_response_hash": bundle.provider_response_hash,
        "candidates": [legacy_candidate],
        "validation_findings": [],
        "context_hashes": {},
        "content_unit_ids": sorted(
            unit.unit_id for unit in bundle.content_unit_window
        ),
        "errors": [],
    }
    legacy_bytes = json.dumps(
        legacy_payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    legacy_hash = hashlib.sha256(legacy_bytes).hexdigest()

    assert bundle.bundle_sha256 == legacy_hash


def test_missing_and_explicit_empty_claim_subject_have_same_bundle_hash() -> None:
    omitted = _make_subject_hash_bundle(_make_subject_hash_claim())
    explicit_empty = _make_subject_hash_bundle(_make_subject_hash_claim([]))

    assert omitted.bundle_sha256 == explicit_empty.bundle_sha256


def test_nonempty_claim_subject_changes_bundle_hash() -> None:
    empty = _make_subject_hash_bundle(_make_subject_hash_claim())
    nonempty = _make_subject_hash_bundle(
        _make_subject_hash_claim(["ent_cand_a"])
    )

    assert empty.bundle_sha256 != nonempty.bundle_sha256


def test_claim_subject_order_changes_bundle_hash() -> None:
    first = _make_subject_hash_bundle(
        _make_subject_hash_claim(["ent_cand_a", "ent_cand_b"])
    )
    reversed_order = _make_subject_hash_bundle(
        _make_subject_hash_claim(["ent_cand_b", "ent_cand_a"])
    )

    assert first.bundle_sha256 != reversed_order.bundle_sha256


def test_claim_subject_duplicates_change_bundle_hash() -> None:
    unique = _make_subject_hash_bundle(
        _make_subject_hash_claim(["ent_cand_a"])
    )
    duplicated = _make_subject_hash_bundle(
        _make_subject_hash_claim(["ent_cand_a", "ent_cand_a"])
    )

    assert unique.bundle_sha256 != duplicated.bundle_sha256
