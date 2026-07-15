"""Validation — ReviewBundle preflight checks before draft persistence.

R2-B01: Bundle Hash and ContextWindow Hash are truly recomputed and matched.
R2-B02: Full preflight including workspace, Provider, Profile, dependency checks.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from aurora.extraction.review_bundle import ReviewBundle


class PreflightError(Exception):
    """Bundle failed preflight validation."""


def validate_bundle_preflight(
    bundle: ReviewBundle,
    workspace_id: str | None = None,
    allowed_providers: frozenset[str] | None = None,
    allowed_profiles: frozenset[str] | None = None,
    existing_object_resolver: Callable[[str], dict[str, Any] | None] | None = None,
) -> list[str]:
    """R2-B01 + R2-B02: Full preflight checks.

    Args:
        bundle: Validated ReviewBundle to check.
        workspace_id: The target workspace id — must match bundle and all refs.
        allowed_providers: Set of allowed provider ids. Any candidate with a
                          provider_id not in this set fails.
        allowed_profiles: Set of allowed profile ids. Any candidate with a
                         profile_id not in this set fails.
        existing_object_resolver: Resolves pre-existing core object ids for
                                  candidate-to-core dependency validation.

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

    cu_window = bundle.content_unit_window or ()
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
    bundle_ws = workspace_id or getattr(bundle, "workspace_id", None)
    if bundle_ws:
        for u in cu_window:
            u_ws = getattr(u, "workspace_id", None)
            if u_ws and u_ws != bundle_ws:
                raise PreflightError(
                    f"ContentUnit {u.unit_id} workspace={u_ws} != workspace={bundle_ws}"
                )
        for c in bundle.candidates:
            c_ws = getattr(c, "workspace_id", None)
            if c_ws and c_ws != bundle_ws:
                raise PreflightError(
                    f"Candidate {getattr(c, 'candidate_id', '?')} "
                    f"workspace={c_ws} != workspace={bundle_ws}"
                )

    # ── R2-B02: Provider allow-list ─────────────────────────────────────
    if allowed_providers is not None:
        for c in bundle.candidates:
            pid = getattr(c, "provider_id", None)
            if pid and pid not in allowed_providers:
                raise PreflightError(
                    f"Candidate {getattr(c, 'candidate_id', '?')} has "
                    f"disallowed provider_id={pid}"
                )

    # ── R2-B02: Profile allow-list ──────────────────────────────────────
    if allowed_profiles is not None:
        for c in bundle.candidates:
            pid = getattr(c, "profile_id", None)
            if pid and pid not in allowed_profiles:
                raise PreflightError(
                    f"Candidate {getattr(c, 'candidate_id', '?')} has "
                    f"disallowed profile_id={pid}"
                )

    # ── R2-B02: Candidate references within accepted set ─────────────────
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
            # Check in candidates AND in pre-existing objects
            if target not in accepted_ids and target not in candidate_ids:
                if existing_object_resolver is None or existing_object_resolver(target) is None:
                    raise PreflightError(
                        f"Evidence {cid} targets {target} which is "
                        f"neither accepted, present as candidate, nor a pre-existing object"
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
            # Must reference an accepted EntityCandidate or pre-existing Entity
            if eid not in accepted_ids and eid not in candidate_ids:
                if existing_object_resolver is None or existing_object_resolver(eid) is None:
                    raise PreflightError(
                        f"DataPoint {cid} references entity_id={eid} "
                        f"which is neither accepted, present as candidate, nor pre-existing"
                    )

    # ── R2-B02: Claim subject_entity references ─────────────────────────
    for c in bundle.candidates:
        cid = getattr(c, "candidate_id", "")
        if cid not in accepted_ids:
            continue
        if c.__class__.__name__ == "ClaimCandidate":
            subj = getattr(c, "subject_entity_ids", None) or []
            for seid in subj:
                if seid not in accepted_ids and seid not in candidate_ids:
                    if existing_object_resolver is None or existing_object_resolver(seid) is None:
                        raise PreflightError(
                            f"Claim {cid} references subject_entity_id={seid} "
                            f"which is neither accepted, present as candidate, nor pre-existing"
                        )

    # ── R2-B02: Accepted dependency check — all accepted must have
    #            their dependencies (entities for DataPoint/Evidence) accepted
    #            or already present as core objects
    for c in bundle.candidates:
        cid = getattr(c, "candidate_id", "")
        if cid not in accepted_ids:
            continue
        cls_name = c.__class__.__name__
        if cls_name in ("DataPointCandidate",):
            eid = getattr(c, "entity_id", "")
            if eid and eid not in accepted_ids:
                if existing_object_resolver is None or existing_object_resolver(eid) is None:
                    raise PreflightError(
                        f"DataPoint {cid} depends on entity_id={eid} "
                        f"which is not accepted and not pre-existing"
                    )
        if cls_name == "EvidenceCandidate":
            target = getattr(c, "target_object_id", "")
            if target and target not in accepted_ids:
                if existing_object_resolver is None or existing_object_resolver(target) is None:
                    raise PreflightError(
                        f"Evidence {cid} depends on target={target} "
                        f"which is not accepted and not pre-existing"
                    )

    return warnings
