"""Independent-evidence grouping rules for Aurora V1.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from aurora.core.models import Evidence
from aurora.core.models.enums import EvidenceRole


@dataclass(frozen=True)
class EvidenceGroupKey:
    target_object_id: str
    evidence_role: EvidenceRole
    independence_group: str


@dataclass
class IndependenceValidationReport:
    empty_group_evidence_ids: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.empty_group_evidence_ids


def effective_independence_group(evidence: Evidence) -> str:
    """Return a stable group key; blank legacy values become unique groups."""

    group = evidence.independence_group.strip()
    return group if group else f"__evidence__:{evidence.id}"


def group_independent_evidence(
    evidence_items: Iterable[Evidence],
) -> dict[EvidenceGroupKey, list[Evidence]]:
    groups: dict[EvidenceGroupKey, list[Evidence]] = {}
    for evidence in evidence_items:
        key = EvidenceGroupKey(
            target_object_id=evidence.target_object_id,
            evidence_role=evidence.evidence_role,
            independence_group=effective_independence_group(evidence),
        )
        groups.setdefault(key, []).append(evidence)
    return groups


def count_independent_evidence(
    evidence_items: Iterable[Evidence],
    *,
    target_object_id: str | None = None,
    evidence_role: EvidenceRole | None = None,
) -> int:
    filtered = (
        evidence
        for evidence in evidence_items
        if (target_object_id is None or evidence.target_object_id == target_object_id)
        and (evidence_role is None or evidence.evidence_role == evidence_role)
    )
    return len(group_independent_evidence(filtered))


def validate_independence_groups(
    evidence_items: Iterable[Evidence],
) -> IndependenceValidationReport:
    return IndependenceValidationReport(
        empty_group_evidence_ids=[
            evidence.id
            for evidence in evidence_items
            if not evidence.independence_group.strip()
        ]
    )
