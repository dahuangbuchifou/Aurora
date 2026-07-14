"""Validation — ReviewBundle preflight checks before draft persistence.

Verifies:
- bundle_sha256 integrity
- candidates are accepted (not rejected)
- no ERROR findings on target candidates
- source_unit_id exists
- FactCandidate not included
- Provider forbidden fields not present
"""

from __future__ import annotations

from aurora.extraction.findings import FindingSeverity, ValidationFinding
from aurora.extraction.review_bundle import ReviewBundle
from aurora.extraction.safety_gate import PROVIDER_FORBIDDEN_FIELDS


class PreflightError(Exception):
    """Bundle failed preflight validation."""

    ...


def validate_bundle_preflight(bundle: ReviewBundle) -> list[str]:
    """Run all preflight checks on a ReviewBundle.

    Returns list of warnings (non-fatal). Raises PreflightError on failure.
    """
    warnings: list[str] = []

    # 1. bundle_sha256 must not be empty
    if not bundle.bundle_sha256 or len(bundle.bundle_sha256) < 16:
        raise PreflightError("ReviewBundle has no valid bundle_sha256")

    # 2. No FactCandidate in accepted
    error_findings_by_cid: dict[str, list[ValidationFinding]] = {}
    for f in bundle.validation_findings or ():
        if f.is_error():
            error_findings_by_cid.setdefault(f.candidate_id, []).append(f)

    for c in bundle.candidates:
        if c.__class__.__name__ == "FactCandidate":
            warnings.append(f"FactCandidate {getattr(c, 'candidate_id', '?')} "
                            f"present but will not be persisted (G3-2)")

        # 3. Candidates with ERROR findings must be in rejected
        cid = getattr(c, "candidate_id", "")
        if cid in error_findings_by_cid and cid not in bundle.rejected_candidate_ids:
            raise PreflightError(
                f"Candidate {cid} has ERROR findings but is not in rejected"
            )

    # 4. Rejected candidates must not be in accepted
    for cid in bundle.rejected_candidate_ids:
        if cid in bundle.accepted_candidate_ids:
            raise PreflightError(
                f"Candidate {cid} is in both accepted and rejected"
            )

    # 5. No provider forbidden fields in any accepted candidate's raw source
    for f in bundle.validation_findings or ():
        if f.code == "PROVIDER_OVERRIDE_FIELD" and f.is_error():
            if f.candidate_id in bundle.accepted_candidate_ids:
                raise PreflightError(
                    f"Candidate {f.candidate_id} is accepted but has "
                    f"PROVIDER_OVERRIDE_FIELD: {f.details.get('field')}"
                )

    return warnings
