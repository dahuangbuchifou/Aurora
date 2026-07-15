"""Mapper — Candidate DTO → Draft core object mapping.

R2-B04: No default values. Fields missing → None/empty → strict validation fails.
R2-B05: Evidence.target_object_id resolved via candidate_id→core_object_id map.
        independence_group set to empty (filled by SourceGraphResolver in draft_service).

FactCandidate is explicitly excluded (G3-2).
"""

from __future__ import annotations

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
    """R2-B04: If value is not a valid enum member, return None.
    No default fallback — upstream strict validation handles None.
    """
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def _convert_time_horizon(th: dict | None) -> Any | None:
    """R2-B04: Convert candidate time_horizon dict to TimeRange."""
    if th is None:
        return None
    from aurora.core.models.common import TimeRange
    from datetime import datetime
    def _parse_date(v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        s = str(v)
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None
    start = _parse_date(th.get("start"))
    end = _parse_date(th.get("end"))
    prec = th.get("precision") or th.get("granularity")
    kwargs = {"start": start, "end": end}
    if prec:
        kwargs["precision"] = prec
    return TimeRange(**kwargs)


def map_entity(cid: str, candidate: EntityCandidate) -> Entity:
    """R2-B04: entity_type=None when unrecognized (upstream validation fails)."""
    return Entity(
        entity_type=_safe_enum(EntityType, candidate.entity_type),
        canonical_name=candidate.canonical_name or "",
    )


def map_data_point(cid: str, candidate: DataPointCandidate) -> DataPoint:
    """R2-B04: metric/unit left as-is from candidate."""
    period = None
    if hasattr(candidate, "period_time_range"):
        period = candidate.period_time_range

    kwargs = {
        "metric": candidate.metric or "",
        "value": candidate.value,
        "unit": candidate.unit or "",
        "entity_id": candidate.entity_id or "",
        "source_ref": f"candidate:{cid}",
        "period": period or TimeRange(),
    }
    if candidate.measurement_context:
        kwargs["measurement_context"] = candidate.measurement_context
    return DataPoint(**kwargs)


def map_claim(cid: str, candidate: ClaimCandidate) -> Claim:
    """R2-B04: claim_type=None when unrecognized (upstream validation fails)."""
    ct = _safe_enum(ClaimType, candidate.claim_type)
    th = _convert_time_horizon(candidate.time_horizon) if candidate.time_horizon else None
    return Claim(
        claim_type=ct,
        statement=candidate.statement or "",
        asserted_by=candidate.asserted_by or candidate.claimant_name or "",
        source_ref=f"candidate:{cid}",
        epistemic_status=EpistemicStatus.UNDER_REVIEW,
        time_horizon=th,
    )


def map_evidence(
    cid: str,
    candidate: EvidenceCandidate,
    candidate_to_core: dict[str, str] | None = None,
) -> Evidence:
    """R2-B05: target_object_id resolved via candidate_id→core_object_id map.

    independence_group is empty here — filled by SourceGraphResolver.
    evidence_role/evidence_type=None when unrecognized (upstream fails).
    """
    target = ""
    if candidate_to_core and candidate.target_object_id:
        target = candidate_to_core.get(candidate.target_object_id, candidate.target_object_id)
    elif candidate.target_object_id:
        target = candidate.target_object_id

    er = _safe_enum(EvidenceRole, candidate.evidence_role)
    et = _safe_enum(EvidenceType, candidate.evidence_type)

    return Evidence(
        evidence_role=er,
        evidence_type=et,
        target_object_id=target,
        source_ref=f"candidate:{cid}",
        summary=candidate.source_quote or candidate.note or "",
        independence_group="pending_source_graph",
        directness=EvidenceDirectness.UNKNOWN,
        source_quality_tier=SourceQualityTier.S5,
        evidence_strength=EvidenceStrength.E1,
    )


def map_accepted_candidates(
    bundle_accepted_ids: list[str],
    candidates: tuple[Candidate, ...],
) -> tuple[list[Entity], list[DataPoint], list[Claim], list[Evidence], dict[str, str]]:
    """R2-B04 + R2-B05: Map candidates with candidate_id→core_object_id tracking.

    Returns:
        entities, data_points, claims, evidence_list, candidate_to_core_id
    """
    accepted = {cid for cid in bundle_accepted_ids}
    entities: list[Entity] = []
    data_points: list[DataPoint] = []
    claims: list[Claim] = []
    evidence_list: list[Evidence] = []
    # R2-B04: candidate_id → core_object_id mapping
    candidate_to_core: dict[str, str] = {}

    for c in candidates:
        cid = getattr(c, "candidate_id", "")
        if cid not in accepted:
            continue

        if isinstance(c, EntityCandidate):
            e = map_entity(cid, c)
            entities.append(e)
            candidate_to_core[cid] = e.id
        elif isinstance(c, DataPointCandidate):
            dp = map_data_point(cid, c)
            data_points.append(dp)
            candidate_to_core[cid] = dp.id
        elif isinstance(c, ClaimCandidate):
            cl = map_claim(cid, c)
            claims.append(cl)
            candidate_to_core[cid] = cl.id
        elif isinstance(c, EvidenceCandidate):
            ev = map_evidence(cid, c, candidate_to_core)
            evidence_list.append(ev)
            candidate_to_core[cid] = ev.id

    return entities, data_points, claims, evidence_list, candidate_to_core
