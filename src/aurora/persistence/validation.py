"""Validation — ReviewBundle preflight checks before draft persistence.

R2-B01: Bundle Hash and ContextWindow Hash are truly recomputed and matched.
R2-B02: Full preflight including workspace, Provider, Profile, dependency checks.
"""

from __future__ import annotations

import hashlib
import json

from aurora.extraction.findings import FindingSeverity
from aurora.extraction.review_bundle import ReviewBundle


class PreflightError(Exception):
    """Bundle failed preflight validation."""


def validate_bundle_preflight(bundle: ReviewBundle) -> list[str]:
    """R2-B01 + R2-B02: Full preflight checks.

    Returns list of warnings (non-fatal). Raises PreflightError on failure.
    """
    warnings: list[str] = []

    # ── R2-B01: Bundle Hash re‑computation ──────────────────────────────
    if not bundle.bundle_sha256 or len(bundle.bundle_sha256) < 16:
        raise PreflightError("ReviewBundle has no valid bundle_sha256")

    recomputed = bundle._compute_hash()
    if recomputed != bundle.bundle_sha256:
        raise PreflightError(
            f"Bundle SHA-256 mismatch: expected {bundle.bundle_sha256[:16]}..., "
            f"computed {recomputed[:16]}..."
        )

    # ── R2-B01: ContextWindow Hash re‑computation ───────────────────────
    ctx_hashes = getattr(bundle, "context_hashes", {}) or {}
    stored_window_sha = ctx_hashes.get("window_sha256", "")
    if not stored_window_sha or len(stored_window_sha) < 16:
        raise PreflightError("ContextWindow hash missing or too short in context_hashes")

    # Recompute from content_unit_window using ContentUnitRef.to_hash_dict
    cu_window = bundle.content_unit_window or ()
    # Use ContentUnitRef's own to_hash_dict() for correct hash computation
    hash_dict = {
        "context_schema_version": "1.0",
        "document_id": getattr(bundle, "document_id", ""),
        "units": [u.to_hash_dict() for u in cu_window],
    }
    canonical = json.dumps(hash_dict, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    recomputed_window_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if recomputed_window_sha != stored_window_sha:
        raise PreflightError(
            f"ContextWindow hash mismatch: stored {stored_window_sha[:16]}..., "
            f"recomputed {recomputed_window_sha[:16]}..."
        )

    # ── FactCandidate exclusion ─────────────────────────────────────────
    for c in bundle.candidates:
        if c.__class__.__name__ == "FactCandidate":
            warnings.append(
                f"FactCandidate {getattr(c, 'candidate_id', '?')} "
                f"present but will not be persisted (G3-2)"
            )

    # ── ERROR findings → candidate must be rejected ─────────────────────
    error_findings_by_cid: dict[str, list] = {}
    for f in bundle.validation_findings or ():
        if f.is_error():
            error_findings_by_cid.setdefault(f.candidate_id, []).append(f)

    for c in bundle.candidates:
        cid = getattr(c, "candidate_id", "")
        if cid in error_findings_by_cid and cid not in bundle.rejected_candidate_ids:
            raise PreflightError(
                f"Candidate {cid} has ERROR findings but is not in rejected"
            )

    # ── Rejected must not be in accepted ────────────────────────────────
    for cid in bundle.rejected_candidate_ids:
        if cid in bundle.accepted_candidate_ids:
            raise PreflightError(f"Candidate {cid} is in both accepted and rejected")

    # ── Provider forbidden fields in accepted ───────────────────────────
    for f in bundle.validation_findings or ():
        if f.code == "PROVIDER_OVERRIDE_FIELD" and f.is_error():
            if f.candidate_id in bundle.accepted_candidate_ids:
                raise PreflightError(
                    f"Candidate {f.candidate_id} is accepted but has "
                    f"PROVIDER_OVERRIDE_FIELD: {f.details.get('field')}"
                )

    # ── Source unit IDs exist in content_unit_window ────────────────────
    cu_ids = {u.unit_id for u in cu_window}
    for c in bundle.candidates:
        suid = getattr(c, "source_unit_id", "")
        if suid and suid not in cu_ids:
            raise PreflightError(
                f"Candidate {getattr(c, 'candidate_id', '?')} references "
                f"non-existent source_unit_id: {suid}"
            )

    # ── Document consistency ────────────────────────────────────────────
    doc_id = getattr(bundle, "document_id", "")
    if doc_id:
        for c in bundle.candidates:
            c_doc_id = getattr(c, "document_id", "")
            if c_doc_id and c_doc_id != doc_id:
                raise PreflightError(
                    f"Candidate {getattr(c, 'candidate_id', '?')} has "
                    f"document_id={c_doc_id} but bundle is for {doc_id}"
                )

    # ── R2-B02: Workspace consistency ───────────────────────────────────
    bundle_ws = getattr(bundle, "workspace_id", None)
    if bundle_ws:
        for u in cu_window:
            u_ws = getattr(u, "workspace_id", None)
            if u_ws and u_ws != bundle_ws:
                raise PreflightError(
                    f"ContentUnit {u.unit_id} workspace={u_ws} != bundle workspace={bundle_ws}"
                )

    # ── R2-B02: Candidate references resolvable ─────────────────────────
    accepted_ids = set(bundle.accepted_candidate_ids)
    candidate_ids = {getattr(c, "candidate_id", "") for c in bundle.candidates}
    for cid in accepted_ids:
        if cid not in candidate_ids:
            raise PreflightError(f"Accepted candidate {cid} not found in bundle candidates")

    # ── R2-B02: Evidence target_object_id references ────────────────────
    for c in bundle.candidates:
        cid = getattr(c, "candidate_id", "")
        if cid not in accepted_ids:
            continue
        if c.__class__.__name__ == "EvidenceCandidate":
            target = getattr(c, "target_object_id", "")
            if not target:
                raise PreflightError(f"Evidence {cid} has empty target_object_id")
            if target not in accepted_ids and target not in candidate_ids:
                raise PreflightError(
                    f"Evidence {cid} targets {target} which is "
                    f"neither accepted nor present as a candidate"
                )

    # ── R2-B02: DataPoint entity_id references ───────────────────────────
    for c in bundle.candidates:
        cid = getattr(c, "candidate_id", "")
        if cid not in accepted_ids:
            continue
        if c.__class__.__name__ == "DataPointCandidate":
            eid = getattr(c, "entity_id", "")
            if not eid:
                raise PreflightError(f"DataPoint {cid} has empty entity_id")
            # entity_id should reference an EntityCandidate or pre-existing Entity
            if eid not in candidate_ids:
                # May reference entity from another bundle — warn but proceed
                warnings.append(
                    f"DataPoint {cid} references entity_id={eid} "
                    f"not in current bundle candidates (cross-bundle ref)"
                )

    return warnings
