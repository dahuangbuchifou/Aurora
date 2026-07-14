"""Mapper — Candidate DTO → Draft core object mapping.

Converts accepted ExtractionCandidates into draft Entity/DataPoint/Claim/Evidence.
FactCandidate is explicitly excluded (G3-2).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aurora.core.models.atoms import Claim, DataPoint, Entity, Evidence
from aurora.core.models.common import (
    HumanReview,
    MeasurementContext,
    Provenance,
    TimeRange,
)
from aurora.core.models.enums import (
    ClaimType,
    EntityType,
    EpistemicStatus,
    EvidenceDirectness,
    EvidenceRole,
    EvidenceStrength,
    EvidenceType,
    HumanReviewStatus,
    ObjectType,
    OriginType,
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
    """Parse enum value, falling back gracefully."""
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def map_entity(cid: str, candidate: EntityCandidate) -> Entity:
    """Create a draft Entity from an EntityCandidate."""
    et = _safe_enum(EntityType, candidate.entity_type) or EntityType.ORGANIZATION
    return Entity(
        entity_type=et,
        canonical_name=candidate.canonical_name or candidate.candidate_id,
        provenance=Provenance(
            origin_type=OriginType.ORIGINAL,
            human_review=HumanReview(status=HumanReviewStatus.NOT_REVIEWED),
            derivation_note=f"Draft from candidate {cid}",
        ),
    )


def map_data_point(cid: str, candidate: DataPointCandidate) -> DataPoint:
    """Create a draft DataPoint from a DataPointCandidate."""
    now = datetime.now(UTC)
    return DataPoint(
        metric=candidate.metric or "unknown",
        value=candidate.value or 0,
        unit=candidate.unit or "unknown",
        measurement_context=candidate.measurement_context or MeasurementContext(),
        entity_id=candidate.entity_id or "",
        period=candidate.period_time_range
        if hasattr(candidate, "period_time_range")
        else TimeRange(start=now, end=now),
        reported_at=now,
        source_ref=f"candidate:{cid}",
        provenance=Provenance(
            origin_type=OriginType.ORIGINAL,
            human_review=HumanReview(status=HumanReviewStatus.NOT_REVIEWED),
            derivation_note=f"Draft from candidate {cid}",
        ),
    )


def map_claim(cid: str, candidate: ClaimCandidate) -> Claim:
    """Create a draft Claim from a ClaimCandidate.

    Epistemic status defaults to UNDER_REVIEW, not VERIFIED.
    Only fact_claim type passes through; other types are blocked upstream.
    If claim_type is prediction and no time_horizon in candidate, provide a default.
    """
    ct = _safe_enum(ClaimType, candidate.claim_type) or ClaimType.FACT_CLAIM
    return Claim(
        claim_type=ct,
        statement=candidate.statement or "",
        asserted_by=candidate.asserted_by or candidate.claimant_name or "unknown",
        source_ref=f"candidate:{cid}",
        epistemic_status=EpistemicStatus.UNDER_REVIEW,  # G3-3: not confirmed
        time_horizon=TimeRange() if ct == ClaimType.PREDICTION else None,
        provenance=Provenance(
            origin_type=OriginType.ORIGINAL,
            human_review=HumanReview(status=HumanReviewStatus.NOT_REVIEWED),
            derivation_note=f"Draft from candidate {cid}",
        ),
    )


def map_evidence(
    cid: str, candidate: EvidenceCandidate, engine_independence_group: str = ""
) -> Evidence:
    """Create a draft Evidence from an EvidenceCandidate.

    independence_group is computed by the engine, NOT from Provider.
    """
    er = _safe_enum(EvidenceRole, candidate.evidence_role) or EvidenceRole.CORROBORATES
    et = _safe_enum(EvidenceType, candidate.evidence_type) or EvidenceType.DOCUMENT
    return Evidence(
        evidence_role=er,
        evidence_type=et,
        target_object_id=candidate.target_object_id or "",
        source_ref=f"candidate:{cid}",
        summary=candidate.source_quote or candidate.note or f"Evidence from {cid}",
        independence_group=engine_independence_group or f"group_{cid}",
        directness=EvidenceDirectness.UNKNOWN,
        source_quality_tier=SourceQualityTier.S5,
        evidence_strength=EvidenceStrength.E1,
        provenance=Provenance(
            origin_type=OriginType.ORIGINAL,
            human_review=HumanReview(status=HumanReviewStatus.NOT_REVIEWED),
            derivation_note=f"Draft from candidate {cid}",
        ),
    )


_CANDIDATE_TYPE_ORDER: tuple[str, ...] = (
    "entity", "data_point", "claim", "evidence",
)


def map_accepted_candidates(
    bundle_accepted_ids: list[str],
    candidates: tuple[Candidate, ...],
    engine_independence_group: str = "",
) -> tuple[list[Entity], list[DataPoint], list[Claim], list[Evidence]]:
    """Map all accepted candidates to draft core objects.

    Returns four parallel lists in deterministic type order.
    FactCandidate is skipped (G3-2).
    """
    accepted = {cid for cid in bundle_accepted_ids}
    entities: list[Entity] = []
    data_points: list[DataPoint] = []
    claims: list[Claim] = []
    evidence_list: list[Evidence] = []

    # Process in type order for determinism
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
            evidence_list.append(map_evidence(cid, c, engine_independence_group))
        # FactCandidate: intentionally skipped (G3-2)

    return entities, data_points, claims, evidence_list
