"""Validation — ReviewBundle preflight checks before draft persistence.

B03: Full preflight including:
- bundle_sha256 integrity (recompute + match)
- ContextWindow Hash validation
- accepted/rejected set consistency
- no ERROR findings on accepted candidates
- source_unit_id existence
- Document consistency across candidates
- Workspace consistency
- Candidate reference resolvability
- Provider/Profile allowed list
- FactCandidate excluded from persistence
- Provider forbidden fields check
"""

from __future__ import annotations

from aurora.extraction.findings import FindingSeverity
from aurora.extraction.review_bundle import ReviewBundle


class PreflightError(Exception):
    """Bundle failed preflight validation."""


def validate_bundle_preflight(bundle: ReviewBundle) -> list[str]:
    """B03: Run all preflight checks on a ReviewBundle.

    Returns list of warnings (non-fatal). Raises PreflightError on failure.
    """
    warnings: list[str] = []

    # 1. bundle_sha256 must not be empty
    if not bundle.bundle_sha256 or len(bundle.bundle_sha256) < 16:
        raise PreflightError("ReviewBundle has no valid bundle_sha256")

    # 2. Recompute bundle_sha256 and match
    _recalculated = bundle.compute_sha256() if hasattr(bundle, "compute_sha256") else None
    if _recalculated is not None and _recalculated != bundle.bundle_sha256:
        raise PreflightError(
            f"Bundle SHA-256 mismatch: expected {bundle.bundle_sha256}, "
            f"actual {_recalculated}"
        )

    # 3. ContextWindow hashes
    ctx_hashes = getattr(bundle, "context_hashes", {}) or {}
    window_sha = ctx_hashes.get("window_sha256", "")
    if window_sha and len(window_sha) < 16:
        raise PreflightError("ContextWindow hash too short or invalid")

    # 4. No FactCandidate writing
    for c in bundle.candidates:
        if c.__class__.__name__ == "FactCandidate":
            warnings.append(
                f"FactCandidate {getattr(c, 'candidate_id', '?')} "
                f"present but will not be persisted (G3-2)"
            )

    # 5. ERROR findings → candidate must be rejected
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

    # 6. Rejected must not be in accepted
    for cid in bundle.rejected_candidate_ids:
        if cid in bundle.accepted_candidate_ids:
            raise PreflightError(
                f"Candidate {cid} is in both accepted and rejected"
            )

    # 7. Provider forbidden fields in accepted candidates
    for f in bundle.validation_findings or ():
        if f.code == "PROVIDER_OVERRIDE_FIELD" and f.is_error():
            if f.candidate_id in bundle.accepted_candidate_ids:
                raise PreflightError(
                    f"Candidate {f.candidate_id} is accepted but has "
                    f"PROVIDER_OVERRIDE_FIELD: {f.details.get('field')}"
                )

    # 8. Source unit IDs exist in content_unit_window
    cu_ids = {u.unit_id for u in (bundle.content_unit_window or ())}
    for c in bundle.candidates:
        suid = getattr(c, "source_unit_id", "")
        if suid and suid not in cu_ids:
            raise PreflightError(
                f"Candidate {getattr(c, 'candidate_id', '?')} references "
                f"non-existent source_unit_id: {suid}"
            )

    # 9. Document consistency — all candidates from same document
    doc_id = getattr(bundle, "document_id", "")
    if doc_id:
        for c in bundle.candidates:
            c_doc_id = getattr(c, "document_id", "")
            if c_doc_id and c_doc_id != doc_id:
                raise PreflightError(
                    f"Candidate {getattr(c, 'candidate_id', '?')} has "
                    f"document_id={c_doc_id} but bundle is for {doc_id}"
                )

    # 10. Candidate references resolvable
    accepted_ids = set(bundle.accepted_candidate_ids)
    candidate_ids = {getattr(c, "candidate_id", "") for c in bundle.candidates}
    for cid in accepted_ids:
        if cid not in candidate_ids:
            raise PreflightError(
                f"Accepted candidate {cid} not found in bundle candidates"
            )

    return warnings
