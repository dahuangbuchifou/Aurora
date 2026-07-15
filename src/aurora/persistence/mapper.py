"""Mapper — strict candidate-to-core-object mapping (G3-4).

R2-B04: No defaults — enum or field missing → None → upstream validation fails.
R2-B05: Evidence independence_group set to placeholder; resolved later via SourceGraph.
"""

from __future__ import annotations

from typing import Any, Callable

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
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
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


def _parse_period_string(s: str) -> Any | None:
    """R2-B04: Parse fiscal period strings like '2025Q3', '2025H1', '2025' → TimeRange."""
    import re
    from calendar import monthrange
    from datetime import datetime

    m = re.match(r'^(\d{4})Q([1-4])$', s)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        start_m = (q - 1) * 3 + 1
        end_m = q * 3
        end_d = monthrange(y, end_m)[1]
        return TimeRange(start=datetime(y, start_m, 1), end=datetime(y, end_m, end_d))
    m = re.match(r'^(\d{4})H([12])$', s)
    if m:
        y, h = int(m.group(1)), int(m.group(2))
        start_m = 1 if h == 1 else 7
        end_m = 6 if h == 1 else 12
        end_d = monthrange(y, end_m)[1]
        return TimeRange(start=datetime(y, start_m, 1), end=datetime(y, end_m, end_d))
    m = re.match(r'^(\d{4})$', s)
    if m:
        y = int(m.group(1))
        return TimeRange(start=datetime(y, 1, 1), end=datetime(y, 12, 31))
    return None


def map_entity(cid: str, candidate: EntityCandidate) -> Entity:
    """R2-B04: entity_type=None when unrecognized (upstream validation fails)."""
    return Entity(
        entity_type=_safe_enum(EntityType, candidate.entity_type),
        canonical_name=candidate.canonical_name or "",
    )


def map_data_point(cid: str, candidate: DataPointCandidate) -> DataPoint:
    """R2-B04: period from candidate only — no default current time."""
    # R2-B04: Try to convert period from candidate
    period = None
    if hasattr(candidate, "period_time_range") and candidate.period_time_range:
        period = candidate.period_time_range
    elif hasattr(candidate, "period") and candidate.period:
        period = candidate.period
    # Convert str period → TimeRange if needed
    if isinstance(period, str):
        period = _parse_period_string(period)

    kwargs = {
        "metric": candidate.metric or "",
        "value": candidate.value,
        "unit": candidate.unit or "",
        "entity_id": candidate.entity_id or "",
        "source_ref": f"candidate:{cid}",
        "period": period,
    }
    if candidate.measurement_context:
        kwargs["measurement_context"] = candidate.measurement_context
    return DataPoint(**kwargs)


def map_claim(cid: str, candidate: ClaimCandidate) -> Claim:
    """R2-B04: claim_type=None when unrecognized (upstream validation fails).
    time_horizon from candidate only — no empty default for prediction claims.
    """
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
    independence_group: str = "",
) -> Evidence:
    """R2-B05: target_object_id resolved via candidate_id→core_object_id map.

    R3-03: independence_group can be passed from caller (resolved via SourceGraph).
    Falls back to "pending_source_graph" placeholder when not provided — validation
    in draft_service blocks this from reaching DB when policy.require_source_graph is True.
    evidence_role/evidence_type=None when unrecognized (upstream fails).
    """
    target = ""
    if candidate_to_core and candidate.target_object_id:
        target = candidate_to_core.get(candidate.target_object_id, candidate.target_object_id)
    elif candidate.target_object_id:
        target = candidate.target_object_id

    er = _safe_enum(EvidenceRole, candidate.evidence_role)
    et = _safe_enum(EvidenceType, candidate.evidence_type)

    ig = independence_group if independence_group else "pending_source_graph"

    return Evidence(
        evidence_role=er,
        evidence_type=et,
        target_object_id=target,
        source_ref=f"candidate:{cid}",
        summary=candidate.source_quote or candidate.note or "pending_summary",
        independence_group=ig,
        directness=EvidenceDirectness.UNKNOWN,
        source_quality_tier=SourceQualityTier.S5,
        evidence_strength=EvidenceStrength.E1,
    )


def map_accepted_candidates(
    accepted_candidate_ids: list[str],
    candidates: list[Any],
    existing_object_resolver: Callable[..., Any] | None = None,
) -> tuple[list[Entity], list[DataPoint], list[Claim], list[Evidence], dict[str, str]]:
    """R2-B05: Map accepted candidates in dependency order.

    Build order: Entity → DataPoint → Claim → Evidence.
    Returns (entities, data_points, claims, evidence_list, candidate_to_core).

    candidate_to_core maps candidate_id → deterministic core object ID
    for reference resolution in Evidence.target_object_id.

    R3-04: Final consistency check ensures all cross-references are resolvable.
    """
    entities: list[Entity] = []
    data_points: list[DataPoint] = []
    claims: list[Claim] = []
    evidence_list: list[Evidence] = []
    candidate_to_core: dict[str, str] = {}

    accepted = set(accepted_candidate_ids)
    cand_by_id = {getattr(c, "candidate_id", ""): c for c in candidates}
    cand_by_type: dict[str, list[tuple[str, Any]]] = {
        "entity": [], "data_point": [], "claim": [], "evidence": [],
    }
    for c in candidates:
        cid = getattr(c, "candidate_id", "")
        if cid not in accepted:
            continue
        cls_name = c.__class__.__name__
        if cls_name == "EntityCandidate":
            cand_by_type["entity"].append((cid, c))
        elif cls_name == "DataPointCandidate":
            cand_by_type["data_point"].append((cid, c))
        elif cls_name == "ClaimCandidate":
            cand_by_type["claim"].append((cid, c))
        elif cls_name == "EvidenceCandidate":
            cand_by_type["evidence"].append((cid, c))

    # Phase 1: Entity first
    for cid, c in cand_by_type["entity"]:
        e = map_entity(cid, c)
        candidate_to_core[cid] = e.id
        entities.append(e)

    # Phase 2: DataPoint (depends on Entity)
    for cid, c in cand_by_type["data_point"]:
        dp = map_data_point(cid, c)
        candidate_to_core[cid] = dp.id
        data_points.append(dp)

    # Phase 3: Claim
    for cid, c in cand_by_type["claim"]:
        cl = map_claim(cid, c)
        candidate_to_core[cid] = cl.id
        claims.append(cl)

    # Phase 4: Evidence (depends on all above)
    for cid, c in cand_by_type["evidence"]:
        ev = map_evidence(cid, c, candidate_to_core)
        candidate_to_core[cid] = ev.id
        evidence_list.append(ev)

    # ── R3-04: Final consistency check for core ID references ──────────
    # Collect all known core IDs + candidate IDs
    known_ids: set[str] = set(candidate_to_core.values()) | set(candidate_to_core.keys())

    # Check DataPoint.entity_id
    for dp in data_points:
        eid = getattr(dp, "entity_id", "")
        if eid and eid not in known_ids:
            if existing_object_resolver is None or existing_object_resolver(eid) is None:
                raise ValueError(
                    f"DataPoint {dp.id} references entity_id={eid} "
                    f"which cannot be resolved to a core object"
                )

    # Check Evidence.target_object_id
    for ev in evidence_list:
        toid = getattr(ev, "target_object_id", "")
        if toid and toid not in known_ids:
            if existing_object_resolver is None or existing_object_resolver(toid) is None:
                raise ValueError(
                    f"Evidence {ev.id} references target_object_id={toid} "
                    f"which cannot be resolved to a core object"
                )

    # Check Claim.subject_entity_ids
    for cl in claims:
        seids = getattr(cl, "subject_entity_ids", None) or []
        for seid in seids:
            if seid not in known_ids:
                if existing_object_resolver is None or existing_object_resolver(seid) is None:
                    raise ValueError(
                        f"Claim {cl.id} references subject_entity_id={seid} "
                        f"which cannot be resolved to a core object"
                    )

    return entities, data_points, claims, evidence_list, candidate_to_core
