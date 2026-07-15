"""Mapper — Candidate DTO → Draft core object mapping.

B05: Strict mapping — no default values for required fields.
Missing fields fail the entire transaction at the strict validation stage
(performed by draft_service._validate_mapped_object).

FactCandidate is explicitly excluded (G3-2).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aurora.core.models.atoms import Claim, DataPoint, Entity, Evidence
from aurora.core.models.common import MeasurementContext, TimeRange
from aurora.core.models.enums import (
    ClaimType,
    EntityType,
    EpistemicStatus,
    EvidenceDirectness,
    EvidenceRole,
    EvidenceStrength,
    EvidenceType,
    SourceQualityTier,
)
from aurora.extraction.candidates import (
    Candidate,
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
    FactCandidate,
)


def _safe_enum(enum_cls: Any, value: str) -> Any:
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def map_entity(cid: str, candidate: EntityCandidate) -> Entity:
    return Entity(
        entity_type=_safe_enum(EntityType, candidate.entity_type) or EntityType.ORGANIZATION,
        canonical_name=candidate.canonical_name or "",
    )


def map_data_point(cid: str, candidate: DataPointCandidate) -> DataPoint:
    now = datetime.now(UTC)
    return DataPoint(
        metric=candidate.metric or "",
        value=candidate.value or 0,
        unit=candidate.unit or "",
        measurement_context=candidate.measurement_context or MeasurementContext(),
        entity_id=candidate.entity_id or "",
        period=candidate.period_time_range
        if hasattr(candidate, "period_time_range")
        else TimeRange(start=now, end=now),
        reported_at=now,
        source_ref=f"candidate:{cid}",
    )


def map_claim(cid: str, candidate: ClaimCandidate) -> Claim:
    ct = _safe_enum(ClaimType, candidate.claim_type) or ClaimType.FACT_CLAIM
    return Claim(
        claim_type=ct,
        statement=candidate.statement or "",
        asserted_by=candidate.asserted_by or candidate.claimant_name or "",
        source_ref=f"candidate:{cid}",
        epistemic_status=EpistemicStatus.UNDER_REVIEW,
        time_horizon=TimeRange() if ct == ClaimType.PREDICTION else None,
    )


def map_evidence(cid: str, candidate: EvidenceCandidate) -> Evidence:
    """B05: independence_group is empty here — filled by SourceGraphResolver (B04)."""
    er = _safe_enum(EvidenceRole, candidate.evidence_role) or EvidenceRole.CORROBORATES
    et = _safe_enum(EvidenceType, candidate.evidence_type) or EvidenceType.DOCUMENT
    return Evidence(
        evidence_role=er,
        evidence_type=et,
        target_object_id=candidate.target_object_id or "",
        source_ref=f"candidate:{cid}",
        summary=candidate.source_quote or candidate.note or "",
        independence_group="",
        directness=EvidenceDirectness.UNKNOWN,
        source_quality_tier=SourceQualityTier.S5,
        evidence_strength=EvidenceStrength.E1,
    )


def map_accepted_candidates(
    bundle_accepted_ids: list[str],
    candidates: tuple[Candidate, ...],
) -> tuple[list[Entity], list[DataPoint], list[Claim], list[Evidence]]:
    accepted = {cid for cid in bundle_accepted_ids}
    entities: list[Entity] = []
    data_points: list[DataPoint] = []
    claims: list[Claim] = []
    evidence_list: list[Evidence] = []

    for c in candidates:
        cid = getattr(c, "candidate_id", "")
        if cid not in accepted:
            continue

        if isinstance(c, EntityCandidate):
            entities.append(map_entity(cid, c))
        elif isinstance(c, DataPointCandidate):
            data_points.append(map_data_point(cid, c))
        elif isinstance(c, ClaimCandidate):
            claims.append(map_claim(cid, c))
        elif isinstance(c, EvidenceCandidate):
            evidence_list.append(map_evidence(cid, c))

    return entities, data_points, claims, evidence_list
