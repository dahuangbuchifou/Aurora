"""Coverage gap tests for validation.py — target 72% → 90%+.

Tests each uncovered branch via mocked ReviewBundle + direct call to
validate_bundle_preflight().
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from aurora.extraction.candidates import (
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
)
from aurora.extraction.context_window import ContentUnitRef
from aurora.extraction.findings import FindingSeverity, ValidationFinding
from aurora.persistence.validation import PreflightError, validate_bundle_preflight


# ── helpers ─────────────────────────────────────────────────────────────────

import hashlib as _hashlib
import json as _json


def _compute_context_hash(cu_window, document_id):
    """Compute valid context window hash for the given window."""
    hash_dict = {
        "context_schema_version": "1.0",
        "document_id": document_id or "",
        "units": [u.to_hash_dict() for u in cu_window] if cu_window else [],
    }
    canonical = _json.dumps(hash_dict, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _make_bundle(**overrides):
    """Create a mocked ReviewBundle with sensible defaults."""
    # Create ContentUnitRef objects
    cu1 = ContentUnitRef(unit_id="cu_1", sequence_no=1, unit_type="paragraph",
                         text="text1", document_id="doc_1")
    cu2 = ContentUnitRef(unit_id="cu_2", sequence_no=2, unit_type="paragraph",
                         text="text2", document_id="doc_1")
    content_unit_window = overrides.pop("content_unit_window", (cu1, cu2))
    doc_id = overrides.get("document_id", "doc_1")
    window_sha = _compute_context_hash(content_unit_window, doc_id)
    context_hashes = overrides.pop("context_hashes", {
        "window_sha256": window_sha,
    })

    # Compute a valid hash
    from aurora.extraction.review_bundle import ReviewBundle
    # We use a real bundle to get a valid hash, then mock attributes
    real = ReviewBundle.create(
        document_id="doc_1",
        provider_name="test",
        provider_version="1.0",
        deterministic_mode=True,
        candidates=(),
        content_unit_window=content_unit_window,
        context_hashes=context_hashes,
    )
    default_hash = real.bundle_sha256

    defaults = {
        "bundle_sha256": default_hash,
        "context_hashes": context_hashes,
        "content_unit_window": content_unit_window,
        "candidates": (),
        "document_id": "doc_1",
        "validation_findings": (),
        "accepted_candidate_ids": (),
        "rejected_candidate_ids": (),
        "workspace_id": "ws_test",
        "_compute_hash": lambda: default_hash,
        # R3-02: Required non-empty provider fields
        "provider_name": "test_provider",
        "provider_version": "1.0.0",
        "profile_version": "1.0.0",
        "provider_metadata": None,
    }
    defaults.update(overrides)

    bundle = MagicMock()
    for k, v in defaults.items():
        setattr(bundle, k, v)

    return bundle


# ── R2-B01: Bundle Hash checks ──────────────────────────────────────────────


class TestBundleHash:
    def test_missing_bundle_sha256(self):
        """Line 45: No bundle_sha256 → PreflightError."""
        bundle = _make_bundle(bundle_sha256="")
        with pytest.raises(PreflightError, match="no valid bundle_sha256"):
            validate_bundle_preflight(bundle)

    def test_short_bundle_sha256(self):
        """Line 45: bundle_sha256 too short → PreflightError."""
        bundle = _make_bundle(bundle_sha256="abc123")
        with pytest.raises(PreflightError, match="no valid bundle_sha256"):
            validate_bundle_preflight(bundle)

    def test_hash_mismatch(self):
        """Line 49: Computed hash doesn't match stored → PreflightError."""
        bundle = _make_bundle(
            bundle_sha256="a" * 64,
            _compute_hash=lambda: "b" * 64,
        )
        with pytest.raises(PreflightError, match="SHA-256 mismatch"):
            validate_bundle_preflight(bundle)


class TestContextWindowHash:
    def test_missing_window_sha(self):
        """Line 58: window_sha256 missing → PreflightError."""
        bundle = _make_bundle(context_hashes={})
        with pytest.raises(PreflightError, match="ContextWindow hash missing"):
            validate_bundle_preflight(bundle)

    def test_short_window_sha(self):
        """Line 58: window_sha256 too short → PreflightError."""
        bundle = _make_bundle(context_hashes={"window_sha256": "short"})
        with pytest.raises(PreflightError, match="ContextWindow hash missing"):
            validate_bundle_preflight(bundle)

    def test_window_sha_mismatch(self):
        """Hash mismatch for ContextWindow."""
        # Use a real ContentUnitRef so to_hash_dict() works
        cu1 = ContentUnitRef(unit_id="cu_1", sequence_no=1, unit_type="paragraph",
                             text="text1", document_id="doc_1")
        bundle = _make_bundle(
            content_unit_window=(cu1,),
            document_id="doc_1",
            context_hashes={"window_sha256": "b" * 64},
        )
        with pytest.raises(PreflightError, match="ContextWindow hash mismatch"):
            validate_bundle_preflight(bundle)


# ── FactCandidate warning ────────────────────────────────────────────────────


class TestFactCandidateWarning:
    def test_fact_candidate_emits_warning(self):
        """Line 69: FactCandidate in candidates → warning."""
        from aurora.extraction.candidates import FactCandidate

        fc = MagicMock()
        fc.__class__.__name__ = "FactCandidate"
        fc.candidate_id = "fc_1"
        fc.source_unit_id = ""  # avoid source unit not found check
        fc.document_id = ""  # avoid document consistency check
        fc.workspace_id = ""  # avoid workspace check

        bundle = _make_bundle(candidates=(fc,))
        warnings = validate_bundle_preflight(bundle)
        assert any("FactCandidate" in w for w in warnings)


# ── ERROR findings not rejected ──────────────────────────────────────────────


class TestErrorFindings:
    def test_error_finding_not_rejected(self):
        """Line 91: ERROR finding but candidate not in rejected → PreflightError."""
        ec = EntityCandidate(canonical_name="Test", entity_type="company")
        f = ValidationFinding(
            code="FAKE_QUOTE", message="bad", severity=FindingSeverity.ERROR,
            candidate_id=ec.candidate_id
        )
        bundle = _make_bundle(
            candidates=(ec,),
            validation_findings=(f,),
            accepted_candidate_ids=(ec.candidate_id,),
            rejected_candidate_ids=(),
        )
        with pytest.raises(PreflightError, match="ERROR findings but is not in rejected"):
            validate_bundle_preflight(bundle)

    def test_candidate_in_both_accepted_and_rejected(self):
        """Line 98: Same id in both accepted and rejected → PreflightError."""
        ec = EntityCandidate(canonical_name="Test", entity_type="company")
        f = ValidationFinding(
            code="FAKE_QUOTE", message="bad", severity=FindingSeverity.ERROR,
            candidate_id=ec.candidate_id
        )
        bundle = _make_bundle(
            candidates=(ec,),
            validation_findings=(f,),
            accepted_candidate_ids=(ec.candidate_id,),
            rejected_candidate_ids=(ec.candidate_id,),
        )
        with pytest.raises(PreflightError, match="in both accepted and rejected"):
            validate_bundle_preflight(bundle)

    # Line 104 (PROVIDER_OVERRIDE_FIELD ERROR on accepted) is dead code:
    # the earlier check at line 91 catches all ERROR findings where
    # candidate is not in rejected, and line 98 rejects candidates in
    # both accepted and rejected. Cannot be covered.

    def test_provider_override_field_warning_not_error(self):
        """Provider override field WARNING should not cause failure."""
        ec = EntityCandidate(canonical_name="Test", entity_type="company")
        f = ValidationFinding(
            code="PROVIDER_OVERRIDE_FIELD", message="warn",
            severity=FindingSeverity.WARNING, candidate_id=ec.candidate_id,
            details={"field": "confidence"},
        )
        bundle = _make_bundle(
            candidates=(ec,),
            validation_findings=(f,),
            accepted_candidate_ids=(ec.candidate_id,),
            rejected_candidate_ids=(),
        )
        # Should not raise
        validate_bundle_preflight(bundle)


# ── Source unit ID not in window ─────────────────────────────────────────────


def _make_mock_candidate(class_name, candidate_id, **attrs):
    """Create a MagicMock-based candidate with specified class name and attrs."""
    c = MagicMock()
    c.__class__.__name__ = class_name
    c.candidate_id = candidate_id
    for k, v in attrs.items():
        setattr(c, k, v)
    return c


class TestSourceUnitId:
    def test_source_unit_id_not_in_window(self):
        """Line 121: source_unit_id not in content_unit_window → PreflightError."""
        c = _make_mock_candidate("EntityCandidate", "ec_1", source_unit_id="cu_nonexistent")
        bundle = _make_bundle(candidates=(c,))
        with pytest.raises(PreflightError, match="non-existent source_unit_id"):
            validate_bundle_preflight(bundle)

    def test_empty_source_unit_id_ok(self):
        """Empty source_unit_id should pass through (suid is falsy)."""
        c = _make_mock_candidate("EntityCandidate", "ec_1",
            source_unit_id="", document_id="", workspace_id="")
        bundle = _make_bundle(candidates=(c,))
        validate_bundle_preflight(bundle)  # no error


# ── Document ID mismatch ─────────────────────────────────────────────────────


class TestDocumentConsistency:
    def test_document_id_mismatch(self):
        """Line 125: candidate.document_id != bundle.document_id → PreflightError."""
        c = _make_mock_candidate("EntityCandidate", "ec_1", source_unit_id="", document_id="doc_other")
        bundle = _make_bundle(candidates=(c,), document_id="doc_1")
        with pytest.raises(PreflightError, match="document_id="):
            validate_bundle_preflight(bundle)


# ── Workspace mismatch ───────────────────────────────────────────────────────


class TestWorkspaceConsistency:
    def test_cu_workspace_mismatch(self):
        """Line 136: ContentUnit workspace != bundle workspace → PreflightError."""
        # Use MagicMock for ContentUnitRef since it's frozen
        cu1 = MagicMock()
        cu1.unit_id = "cu_wsm"
        cu1.workspace_id = "ws_other"
        cu1.to_hash_dict = lambda: {"unit_id": "cu_wsm", "sequence_no": 1, "unit_type": "p", "text_sha256": "a" * 64, "locator_sha256": "b" * 64}
        bundle = _make_bundle(
            content_unit_window=(cu1,),
            workspace_id="ws_test",
        )
        with pytest.raises(PreflightError, match="workspace="):
            validate_bundle_preflight(bundle, workspace_id="ws_test")

    def test_candidate_workspace_mismatch(self):
        """Line 142: candidate workspace != bundle workspace → PreflightError."""
        c = _make_mock_candidate("EntityCandidate", "ec_1",
            source_unit_id="", document_id="", workspace_id="ws_other")
        bundle = _make_bundle(
            candidates=(c,),
            workspace_id="ws_test",
        )
        with pytest.raises(PreflightError, match="workspace="):
            validate_bundle_preflight(bundle, workspace_id="ws_test")


# ── Provider / Profile allow-list ────────────────────────────────────────────


class TestAllowLists:
    def test_disallowed_provider(self):
        """Line 152: provider_id not in allowed → PreflightError."""
        c = _make_mock_candidate("EntityCandidate", "ec_1",
            source_unit_id="", document_id="", workspace_id="", provider_id="bad_provider")
        bundle = _make_bundle(candidates=(c,))
        with pytest.raises(PreflightError, match="disallowed provider_id"):
            validate_bundle_preflight(bundle, allowed_providers=frozenset({"good"}))

    def test_disallowed_profile(self):
        """Line 162: profile_id not in allowed → PreflightError."""
        c = _make_mock_candidate("EntityCandidate", "ec_1",
            source_unit_id="", document_id="", workspace_id="", profile_id="bad_profile")
        bundle = _make_bundle(candidates=(c,))
        with pytest.raises(PreflightError, match="disallowed profile_id"):
            validate_bundle_preflight(bundle, allowed_profiles=frozenset({"good"}))

    def test_non_restricted_provider_passes(self):
        """Allowed_providers=None should not check."""
        c = _make_mock_candidate("EntityCandidate", "ec_1",
            source_unit_id="", document_id="", workspace_id="", provider_id="any_provider")
        bundle = _make_bundle(candidates=(c,))
        validate_bundle_preflight(bundle, allowed_providers=None)  # no error

    def test_non_restricted_profile_passes(self):
        """Allowed_profiles=None should not check."""
        c = _make_mock_candidate("EntityCandidate", "ec_1",
            source_unit_id="", document_id="", workspace_id="", profile_id="any_profile")
        bundle = _make_bundle(candidates=(c,))
        validate_bundle_preflight(bundle, allowed_profiles=None)  # no error


# ── Accepted not in candidates ───────────────────────────────────────────────


class TestAcceptedInCandidates:
    def test_accepted_not_found_in_candidates(self):
        """Line 172: Accepted candidate id not in any candidate → PreflightError."""
        c = _make_mock_candidate("EntityCandidate", "ec_real",
            source_unit_id="", document_id="", workspace_id="")
        bundle = _make_bundle(
            candidates=(c,),
            accepted_candidate_ids=("nonexistent_id",),
        )
        with pytest.raises(PreflightError, match="not found in bundle candidates"):
            validate_bundle_preflight(bundle)


# ── Evidence target validation ───────────────────────────────────────────────


class TestEvidenceTargets:
    def test_evidence_empty_target(self):
        """Line 180-182: Evidence accepted with empty target_object_id → error."""
        ev = _make_mock_accepted("EvidenceCandidate", "ev_1", target_object_id="")

        bundle = _make_bundle(
            candidates=(ev,),
            accepted_candidate_ids=("ev_1",),
        )
        with pytest.raises(PreflightError, match="empty target_object_id"):
            validate_bundle_preflight(bundle)

    def test_evidence_target_unresolvable(self):
        """Line 182-186: Evidence target not in accepted, candidates, or resolver."""
        ev = _make_mock_accepted("EvidenceCandidate", "ev_1", target_object_id="nonexistent")

        bundle = _make_bundle(
            candidates=(ev,),
            accepted_candidate_ids=("ev_1",),
        )
        with pytest.raises(PreflightError, match="neither accepted, present as candidate"):
            validate_bundle_preflight(bundle)

    def test_evidence_target_found_in_candidates(self):
        """Evidence target exists as another candidate → passes."""
        ev = _make_mock_accepted("EvidenceCandidate", "ev_1", target_object_id="ent_1_cand")

        ent = EntityCandidate(canonical_name="Target", entity_type="company")
        # Override candidate_id to match target
        ent.candidate_id = "ent_1_cand"

        bundle = _make_bundle(
            candidates=(ev, ent),
            accepted_candidate_ids=("ev_1", "ent_1_cand"),  # target must also be accepted
        )
        validate_bundle_preflight(bundle)

    def test_evidence_target_resolved_by_existing_object_resolver(self):
        """Line 203: existing_object_resolver finds target → passes."""
        ev = _make_mock_accepted("EvidenceCandidate", "ev_1", target_object_id="core_obj_1")

        bundle = _make_bundle(
            candidates=(ev,),
            accepted_candidate_ids=("ev_1",),
        )
        resolver = lambda oid: {"id": oid} if oid == "core_obj_1" else None
        # Should not raise
        warnings = validate_bundle_preflight(bundle, existing_object_resolver=resolver)
        assert isinstance(warnings, list)


# ── DataPoint entity_id validation ───────────────────────────────────────────


class TestDataPointEntityId:
    def test_datapoint_empty_entity_id(self):
        """Line 199: DataPoint accepted with empty entity_id → error."""
        dp = _make_mock_accepted("DataPointCandidate", "dp_1", entity_id="")

        bundle = _make_bundle(
            candidates=(dp,),
            accepted_candidate_ids=("dp_1",),
        )
        with pytest.raises(PreflightError, match="empty entity_id"):
            validate_bundle_preflight(bundle)

    def test_datapoint_entity_id_unresolvable(self):
        """Line 201→192: DataPoint entity_id not found anywhere."""
        dp = _make_mock_accepted("DataPointCandidate", "dp_1", entity_id="nonexistent_ent")

        bundle = _make_bundle(
            candidates=(dp,),
            accepted_candidate_ids=("dp_1",),
        )
        with pytest.raises(PreflightError, match="references entity_id="):
            validate_bundle_preflight(bundle)

    def test_datapoint_entity_id_resolved_by_existing_object_resolver(self):
        """Line 203: DataPoint entity_id found via resolver → passes."""
        dp = _make_mock_accepted("DataPointCandidate", "dp_1", entity_id="core_ent_1")

        bundle = _make_bundle(
            candidates=(dp,),
            accepted_candidate_ids=("dp_1",),
        )
        resolver = lambda oid: {"id": oid} if oid == "core_ent_1" else None
        validate_bundle_preflight(bundle, existing_object_resolver=resolver)

    def test_datapoint_entity_id_found_in_candidates(self):
        """DataPoint entity_id matches another candidate → passes."""
        dp = _make_mock_accepted("DataPointCandidate", "dp_1", entity_id="ent_cand_1")

        ent = EntityCandidate(canonical_name="Parent", entity_type="company")
        ent.candidate_id = "ent_cand_1"

        bundle = _make_bundle(
            candidates=(dp, ent),
            accepted_candidate_ids=("dp_1", "ent_cand_1"),  # entity must also be accepted
        )
        validate_bundle_preflight(bundle)  # no error


# ── Claim subject_entity_ids ─────────────────────────────────────────────────


class TestClaimSubjectEntities:
    def test_claim_subject_unresolvable(self):
        """Line 216-218: Claim subject_entity_id not found anywhere."""
        cl = _make_mock_accepted("ClaimCandidate", "cl_1", subject_entity_ids=["nonexistent_se"])

        bundle = _make_bundle(
            candidates=(cl,),
            accepted_candidate_ids=("cl_1",),
        )
        with pytest.raises(PreflightError, match="references subject_entity_id="):
            validate_bundle_preflight(bundle)

    def test_claim_subject_found_in_candidates(self):
        """Claim subject_entity_id matches a candidate → passes."""
        cl = _make_mock_accepted("ClaimCandidate", "cl_1", subject_entity_ids=["ent_cand_1"])

        ent = EntityCandidate(canonical_name="Subject", entity_type="company")
        ent.candidate_id = "ent_cand_1"

        bundle = _make_bundle(
            candidates=(cl, ent),
            accepted_candidate_ids=("cl_1",),
        )
        validate_bundle_preflight(bundle)

    def test_claim_subject_resolved_by_existing_object_resolver(self):
        """Claim subject resolved via existing_object_resolver → passes."""
        cl = _make_mock_accepted("ClaimCandidate", "cl_1", subject_entity_ids=["core_ent_1"])

        bundle = _make_bundle(
            candidates=(cl,),
            accepted_candidate_ids=("cl_1",),
        )
        resolver = lambda oid: {"id": oid} if oid == "core_ent_1" else None
        validate_bundle_preflight(bundle, existing_object_resolver=resolver)

    def test_claim_no_subject_entity_ids(self):
        """Claim with empty subject_entity_ids → passes."""
        cl = _make_mock_accepted("ClaimCandidate", "cl_1", subject_entity_ids=[])

        bundle = _make_bundle(
            candidates=(cl,),
            accepted_candidate_ids=("cl_1",),
        )
        validate_bundle_preflight(bundle)


# ── Dependency checks (accepted dependencies) ───────────────────────────────


def _make_mock_accepted(class_name, candidate_id, **attrs):
    """Create a MagicMock that passes all checks except specific ones."""
    defaults = {"source_unit_id": "", "document_id": "", "workspace_id": ""}
    defaults.update(attrs)
    return _make_mock_candidate(class_name, candidate_id, **defaults)


class TestDependencyChecks:
    def test_datapoint_depends_on_non_accepted_entity(self):
        """Line 233→239: DataPoint entity_id not accepted, not pre-existing."""
        dp = _make_mock_accepted("DataPointCandidate", "dp_1", entity_id="ent_cand_1")

        ent = EntityCandidate(canonical_name="Dep", entity_type="company")
        ent.candidate_id = "ent_cand_1"

        # DataPoint is accepted but Entity is NOT
        bundle = _make_bundle(
            candidates=(dp, ent),
            accepted_candidate_ids=("dp_1",),  # entity NOT accepted
        )
        with pytest.raises(PreflightError, match="depends on entity_id="):
            validate_bundle_preflight(bundle)

    def test_datapoint_depends_on_accepted_entity(self):
        """DataPoint entity_id is also accepted → passes."""
        dp = _make_mock_accepted("DataPointCandidate", "dp_1", entity_id="ent_cand_1")

        ent = EntityCandidate(canonical_name="Dep", entity_type="company")
        ent.candidate_id = "ent_cand_1"

        bundle = _make_bundle(
            candidates=(dp, ent),
            accepted_candidate_ids=("dp_1", "ent_cand_1"),
        )
        validate_bundle_preflight(bundle)  # no error

    def test_datapoint_depends_on_pre_existing_entity(self):
        """DataPoint depends on entity resolved via existing_object_resolver."""
        dp = _make_mock_accepted("DataPointCandidate", "dp_1", entity_id="core_ent_pre")

        bundle = _make_bundle(
            candidates=(dp,),
            accepted_candidate_ids=("dp_1",),
        )
        resolver = lambda oid: {"id": oid} if oid == "core_ent_pre" else None
        validate_bundle_preflight(bundle, existing_object_resolver=resolver)

    def test_evidence_depends_on_non_accepted_target(self):
        """Line 240: Evidence target not accepted, not pre-existing."""
        ev = _make_mock_accepted("EvidenceCandidate", "ev_1", target_object_id="cl_cand_1")

        cl = _make_mock_candidate("ClaimCandidate", "cl_cand_1", source_unit_id="", document_id="", workspace_id="")

        # Evidence is accepted but Claim is NOT
        bundle = _make_bundle(
            candidates=(ev, cl),
            accepted_candidate_ids=("ev_1",),  # claim NOT accepted
        )
        with pytest.raises(PreflightError, match="depends on target="):
            validate_bundle_preflight(bundle)

    def test_evidence_depends_on_pre_existing_target(self):
        """Evidence target resolved via existing_object_resolver."""
        ev = _make_mock_accepted("EvidenceCandidate", "ev_1", target_object_id="core_obj_pre")

        bundle = _make_bundle(
            candidates=(ev,),
            accepted_candidate_ids=("ev_1",),
        )
        resolver = lambda oid: {"id": oid} if oid == "core_obj_pre" else None
        validate_bundle_preflight(bundle, existing_object_resolver=resolver)


# ── R3-02: Provider name/version/profile ─────────────────────────────────────


class TestR302ProviderValidation:
    def test_empty_provider_version_fails(self):
        """R3-02: Empty provider_version → PreflightError."""
        bundle = _make_bundle(provider_version="")
        with pytest.raises(PreflightError, match="provider_version is empty"):
            validate_bundle_preflight(bundle)

    def test_empty_profile_version_fails(self):
        """R3-02: Empty profile_version → PreflightError."""
        bundle = _make_bundle(profile_version="")
        with pytest.raises(PreflightError, match="profile_version is empty"):
            validate_bundle_preflight(bundle)

    def test_provider_metadata_name_mismatch(self):
        """R3-02: provider_name differs from provider_metadata.name → warning."""
        meta = MagicMock()
        meta.name = "other_provider"
        bundle = _make_bundle(
            provider_name="test_provider",
            provider_metadata=meta,
        )
        warnings = validate_bundle_preflight(bundle)
        assert any("provider_name" in w and "differs" in w for w in warnings)


# ── All allowed ──────────────────────────────────────────────────────────────


class TestAllAllowed:
    def test_all_allowed_providers_and_profiles(self):
        """Test with restricted allowed sets that match."""
        c = _make_mock_candidate("EntityCandidate", "ec_allowed",
            source_unit_id="", document_id="", workspace_id="",
            provider_id="p1", profile_id="pf1")

        bundle = _make_bundle(
            candidates=(c,),
            accepted_candidate_ids=("ec_allowed",),
            workspace_id="ws_test",
        )
        validate_bundle_preflight(
            bundle,
            workspace_id="ws_test",
            allowed_providers=frozenset({"p1"}),
            allowed_profiles=frozenset({"pf1"}),
        )
