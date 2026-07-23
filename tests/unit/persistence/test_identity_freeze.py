from __future__ import annotations

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
