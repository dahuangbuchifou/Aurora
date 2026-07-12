"""EvidenceRole scope-compatibility rules."""

from __future__ import annotations

from dataclasses import dataclass

from aurora.core.models.enums import ClaimDimension, EvidenceRole


@dataclass(frozen=True)
class EvidenceScope:
    subject_ids: frozenset[str] = frozenset()
    time_scope: str | None = None
    claim_dimension: ClaimDimension = ClaimDimension.GENERAL
    conditions: frozenset[str] = frozenset()


@dataclass(frozen=True)
class EvidenceRoleAssessment:
    compatible: bool
    suggested_role: EvidenceRole
    reason: str


def assess_evidence_role(
    requested_role: EvidenceRole,
    *,
    target_scope: EvidenceScope,
    evidence_scope: EvidenceScope,
) -> EvidenceRoleAssessment:
    """Assess whether a role is direct enough for the compared scopes."""

    same_subject = (
        not target_scope.subject_ids
        or not evidence_scope.subject_ids
        or target_scope.subject_ids == evidence_scope.subject_ids
    )
    same_time = (
        target_scope.time_scope is None
        or evidence_scope.time_scope is None
        or target_scope.time_scope == evidence_scope.time_scope
    )
    same_dimension = (
        target_scope.claim_dimension == ClaimDimension.GENERAL
        or evidence_scope.claim_dimension == ClaimDimension.GENERAL
        or target_scope.claim_dimension == evidence_scope.claim_dimension
    )
    same_conditions = (
        not target_scope.conditions
        or not evidence_scope.conditions
        or target_scope.conditions == evidence_scope.conditions
    )

    if requested_role in {EvidenceRole.SUPPORT, EvidenceRole.REFUTE}:
        if not same_dimension:
            return EvidenceRoleAssessment(
                compatible=False,
                suggested_role=EvidenceRole.QUALIFY,
                reason="analysis dimensions differ; direct support/refute is not justified",
            )
        if not (same_subject and same_time):
            return EvidenceRoleAssessment(
                compatible=False,
                suggested_role=EvidenceRole.CONTEXT,
                reason="subject or time scope differs",
            )
        if not same_conditions:
            return EvidenceRoleAssessment(
                compatible=False,
                suggested_role=EvidenceRole.QUALIFY,
                reason="conditions differ and narrow the claim scope",
            )

    return EvidenceRoleAssessment(
        compatible=True,
        suggested_role=requested_role,
        reason="role is compatible with the compared scopes",
    )
