from __future__ import annotations

import hashlib

from aurora.extraction.candidates import ClaimCandidate, EvidenceCandidate
from aurora.extraction.safety_gate import PROVIDER_FORBIDDEN_FIELDS
from aurora.persistence.identity import (
    compute_bundle_operation_key,
    compute_draft_natural_key,
)


def test_identity_fixed_input_has_frozen_digest() -> None:
    candidate = EvidenceCandidate(
        candidate_id="ev_cand_identity_001",
        evidence_type="direct_quote",
        evidence_role="support",
        target_object_id="cl_identity_001",
        independence_group="",
        source_quote="Revenue increased year over year.",
        source_unit_id="cu_identity_001",
        confidence=0.10,
    )

    bundle_operation_key = compute_bundle_operation_key(
        "ws_identity_freeze",
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )
    draft_natural_key = compute_draft_natural_key(
        "ws_identity_freeze", "evidence", candidate
    )

    assert bundle_operation_key == (
        "51c0045373f02188bddd200ee88392e911df798ff673b37d805365388762be44"
    )
    assert draft_natural_key == (
        "068e722ec268caa0d4c1ca421ed7ab8e47bb655fe75de685583e9a9e808f0a2e"
    )

def test_provider_semantic_fields_do_not_change_identity() -> None:
    assert "independence_group" in PROVIDER_FORBIDDEN_FIELDS

    # Provider raw input may not set independence_group. The DTO keeps the field for
    # Aurora's internally controlled value, which must remain outside stable identity.
    evidence_base = EvidenceCandidate(
        candidate_id="ev_cand_identity_001",
        evidence_type="direct_quote",
        evidence_role="support",
        target_object_id="cl_identity_001",
        independence_group="",
        source_quote="Revenue increased year over year.",
        source_unit_id="cu_identity_001",
        confidence=0.10,
    )
    evidence_provider_semantic_variant = EvidenceCandidate(
        candidate_id="ev_cand_identity_001",
        evidence_type="direct_quote",
        evidence_role="support",
        target_object_id="cl_identity_001",
        independence_group="provider-supplied-group",
        source_quote="Revenue increased year over year.",
        source_unit_id="cu_identity_001",
        confidence=0.99,
    )
    evidence_business_variant = EvidenceCandidate(
        candidate_id="ev_cand_identity_001",
        evidence_type="direct_quote",
        evidence_role="support",
        target_object_id="cl_identity_002",
        independence_group="",
        source_quote="Revenue increased year over year.",
        source_unit_id="cu_identity_001",
        confidence=0.10,
    )

    evidence_key = compute_draft_natural_key(
        "ws_identity_freeze", "evidence", evidence_base
    )
    assert evidence_key == compute_draft_natural_key(
        "ws_identity_freeze", "evidence", evidence_provider_semantic_variant
    )
    assert evidence_key != compute_draft_natural_key(
        "ws_identity_freeze", "evidence", evidence_business_variant
    )

    claim_base = ClaimCandidate(
        candidate_id="cl_cand_identity_001",
        statement="Revenue increased year over year.",
        claim_type="interpretation",
        claim_dimension="financial_performance",
        asserted_by="issuer",
        promotable_to_fact=False,
        source_quote="Revenue increased year over year.",
        source_unit_id="cu_identity_001",
        confidence=0.10,
    )
    claim_provider_semantic_variant = ClaimCandidate(
        candidate_id="cl_cand_identity_001",
        statement="Revenue increased year over year.",
        claim_type="interpretation",
        claim_dimension="financial_performance",
        asserted_by="issuer",
        promotable_to_fact=True,
        source_quote="Revenue increased year over year.",
        source_unit_id="cu_identity_001",
        confidence=0.99,
    )
    claim_business_variant = ClaimCandidate(
        candidate_id="cl_cand_identity_001",
        statement="Revenue decreased year over year.",
        claim_type="interpretation",
        claim_dimension="financial_performance",
        asserted_by="issuer",
        promotable_to_fact=False,
        source_quote="Revenue increased year over year.",
        source_unit_id="cu_identity_001",
        confidence=0.10,
    )

    claim_key = compute_draft_natural_key(
        "ws_identity_freeze", "claim", claim_base
    )
    assert claim_key == compute_draft_natural_key(
        "ws_identity_freeze", "claim", claim_provider_semantic_variant
    )
    assert claim_key != compute_draft_natural_key(
        "ws_identity_freeze", "claim", claim_business_variant
    )


def _make_subject_claim_candidate(
    subject_entity_ids: list[str] | None = None,
) -> ClaimCandidate:
    payload: dict[str, object] = {
        "candidate_id": "cl_cand_subject_identity_001",
        "statement": "Revenue increased year over year.",
        "claim_type": "interpretation",
        "claim_dimension": "financial_performance",
        "asserted_by": "issuer",
        "source_quote": "Revenue increased year over year.",
        "source_unit_id": "cu_identity_001",
    }
    if subject_entity_ids is not None:
        payload["subject_entity_ids"] = subject_entity_ids
    return ClaimCandidate(**payload)


def _claim_natural_key(candidate: ClaimCandidate) -> str:
    return compute_draft_natural_key(
        "ws_identity_freeze",
        "claim",
        candidate,
    )


def test_empty_claim_subject_preserves_legacy_natural_key() -> None:
    candidate = _make_subject_claim_candidate()
    legacy_stable_payload = "|".join(
        [
            candidate.claim_type,
            candidate.claim_dimension,
            candidate.statement,
            candidate.asserted_by,
            candidate.source_unit_id,
            candidate.source_quote,
        ]
    )
    legacy_payload = (
        "aurora/v1|ws_identity_freeze|claim|"
        f"{candidate.candidate_id}|{legacy_stable_payload}"
    )
    legacy_key = hashlib.sha256(legacy_payload.encode()).hexdigest()

    assert _claim_natural_key(candidate) == legacy_key


def test_missing_and_explicit_empty_claim_subject_have_same_key() -> None:
    omitted = _make_subject_claim_candidate()
    explicit_empty = _make_subject_claim_candidate([])

    assert _claim_natural_key(omitted) == _claim_natural_key(explicit_empty)


def test_claim_subject_order_and_duplicates_do_not_change_key() -> None:
    ordered = _make_subject_claim_candidate(["ent_cand_a", "ent_cand_b"])
    reversed_order = _make_subject_claim_candidate(
        ["ent_cand_b", "ent_cand_a"]
    )
    duplicated = _make_subject_claim_candidate(
        ["ent_cand_a", "ent_cand_b", "ent_cand_a"]
    )

    expected = _claim_natural_key(ordered)
    assert _claim_natural_key(reversed_order) == expected
    assert _claim_natural_key(duplicated) == expected


def test_different_claim_subject_sets_change_key() -> None:
    first = _make_subject_claim_candidate(["ent_cand_a"])
    second = _make_subject_claim_candidate(["ent_cand_b"])

    assert _claim_natural_key(first) != _claim_natural_key(second)
