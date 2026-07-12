from aurora.core.models import ClaimDimension, EvidenceRole
from aurora.repository import EvidenceScope, assess_evidence_role


def test_same_dimension_can_directly_refute():
    scope = EvidenceScope(
        subject_ids=frozenset({"ent_smic"}),
        time_scope="FY2026",
        claim_dimension=ClaimDimension.BUSINESS_GROWTH,
    )
    result = assess_evidence_role(
        EvidenceRole.REFUTE,
        target_scope=scope,
        evidence_scope=scope,
    )
    assert result.compatible is True
    assert result.suggested_role == EvidenceRole.REFUTE


def test_growth_and_valuation_are_not_direct_refutation():
    result = assess_evidence_role(
        EvidenceRole.REFUTE,
        target_scope=EvidenceScope(
            subject_ids=frozenset({"ent_smic"}),
            claim_dimension=ClaimDimension.BUSINESS_GROWTH,
        ),
        evidence_scope=EvidenceScope(
            subject_ids=frozenset({"ent_smic"}),
            claim_dimension=ClaimDimension.VALUATION,
        ),
    )
    assert result.compatible is False
    assert result.suggested_role == EvidenceRole.QUALIFY


def test_different_subject_suggests_context():
    result = assess_evidence_role(
        EvidenceRole.SUPPORT,
        target_scope=EvidenceScope(subject_ids=frozenset({"ent_smic"})),
        evidence_scope=EvidenceScope(subject_ids=frozenset({"ent_tsmc"})),
    )
    assert result.compatible is False
    assert result.suggested_role == EvidenceRole.CONTEXT
