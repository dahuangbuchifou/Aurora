"""Stable identity generation for draft persistence (M-C3-01).

Produces deterministic SHA-256 hashes for bundle operation keys and
object natural keys. Excludes all provider-owned epistemic fields.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aurora.extraction.candidates import (
    Candidate,
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
    FactCandidate,
)

NAMESPACE = "aurora/v1"


def _stable_provider_payload(candidate: Candidate) -> str:
    """Normalised semantic payload for stable identity computation.

    Deliberately EXCLUDES:
    - confidence
    - independence_group
    - promotable / promotable_to_fact
    - verification_status
    - epistemic_status
    - provider metadata
    - timestamps
    """
    parts: list[str] = []

    if isinstance(candidate, EntityCandidate):
        parts.append(candidate.entity_type or "")
        parts.append(candidate.canonical_name or "")
    elif isinstance(candidate, DataPointCandidate):
        parts.append(candidate.metric or "")
        parts.append(str(candidate.value))
        parts.append(candidate.unit or "")
        parts.append(candidate.entity_id or "")
        parts.append(candidate.period or "")
    elif isinstance(candidate, ClaimCandidate):
        parts.append(candidate.claim_type or "")
        parts.append(candidate.claim_dimension or "")
        parts.append(candidate.statement or "")
        parts.append(candidate.asserted_by or "")
        subject_entity_ids = sorted(set(candidate.subject_entity_ids))
        if subject_entity_ids:
            canonical_subject_ids = json.dumps(
                subject_entity_ids,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            parts.append(f"subject_entity_ids={canonical_subject_ids}")
    elif isinstance(candidate, EvidenceCandidate):
        parts.append(candidate.evidence_type or "")
        parts.append(candidate.evidence_role or "")
        parts.append(candidate.target_object_id or "")
    elif isinstance(candidate, FactCandidate):
        parts.append(candidate.statement or "")
    else:
        parts.append("unknown")

    # source context (common to all)
    suid = getattr(candidate, "source_unit_id", "") or ""
    parts.append(suid)
    sq = getattr(candidate, "source_quote", "") or ""
    parts.append(sq)

    return "|".join(parts)


def compute_bundle_operation_key(
    workspace_id: str,
    review_bundle_sha256: str,
) -> str:
    """Compute stable bundle operation key.

    SHA256(namespace + workspace_id + review_bundle_sha256)
    """
    payload = f"{NAMESPACE}|{workspace_id}|{review_bundle_sha256}"
    return hashlib.sha256(payload.encode()).hexdigest()


def compute_draft_natural_key(
    workspace_id: str,
    object_type: str,
    candidate: Candidate,
) -> str:
    """Compute stable draft object natural key.

    SHA256(namespace + workspace_id + object_type + candidate_stable_identity)
    """
    csi = _stable_provider_payload(candidate)
    cid = getattr(candidate, "candidate_id", "") or ""
    payload = f"{NAMESPACE}|{workspace_id}|{object_type}|{cid}|{csi}"
    return hashlib.sha256(payload.encode()).hexdigest()
