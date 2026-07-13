"""ReviewBundle V2 — immutable audit trail for extraction runs.

V2 changes:
- bundle_sha256 computed via canonicalized JSON (excludes hash field, then computes)
- Includes validation_findings and context_hashes
- Fully immutable frozen dataclass
- Hash covers: run_id, candidates, validation_findings, context_hashes, metadata
- Same input → same hash; any field change → hash change
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aurora.extraction.candidates import Candidate
from aurora.extraction.context_window import ContentUnitRef
from aurora.extraction.findings import ValidationFinding

BUNDLE_SCHEMA_VERSION = "2.0"


@dataclass(frozen=True)
class ExtractionError:
    """Record of an extraction error with context (backward-compatible)."""

    code: str
    message: str
    candidate_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)


def _candidate_to_serializable(c: Candidate) -> dict[str, Any]:
    """Serialize a candidate to a JSON-safe dict for hash computation."""
    if hasattr(c, "model_dump"):
        return c.model_dump()
    return dict(c.__dict__)


def _finding_to_serializable(f: ValidationFinding) -> dict[str, Any]:
    return f.to_dict()


def _canonical_json(obj: Any) -> bytes:
    """Produce canonical UTF-8 JSON bytes with sort_keys, compact separators."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


@dataclass(frozen=True)
class ReviewBundle:
    """Immutable bundle of extraction results for human review.

    V2: bundle_sha256 is computed from canonicalized JSON of all data fields
    (excluding the hash itself). Any change to candidates, findings, context,
    or metadata produces a different hash.
    """

    review_bundle_id: str
    run_id: str
    document_id: str
    provider_name: str
    provider_version: str
    deterministic_mode: bool
    created_at: datetime
    candidates: tuple[Candidate, ...]
    content_unit_window: tuple[ContentUnitRef, ...]
    validation_findings: tuple[ValidationFinding, ...] = ()
    context_hashes: dict[str, str] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    schema_version: str = BUNDLE_SCHEMA_VERSION
    case_id: str = ""
    prompt_version: str = "placeholder"
    profile_version: str = "placeholder"
    provider_response_hash: str = ""
    bundle_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        sha = self._compute_hash()
        object.__setattr__(self, "bundle_sha256", sha)

    def _compute_hash(self) -> str:
        """Compute SHA-256 from canonicalized JSON of all data fields.

        Excludes bundle_sha256 itself. Includes: run_id, document_id, provider,
        candidates, validation_findings, context_hashes, content_unit_window,
        errors, schema_version, case_id, prompt_version, profile_version,
        provider_response_hash, deterministic_mode.
        """
        payload = self._to_hash_dict()
        return hashlib.sha256(_canonical_json(payload)).hexdigest()

    def _to_hash_dict(self) -> dict[str, Any]:
        """Build the dict used for bundle hash computation."""
        return {
            "run_id": self.run_id,
            "document_id": self.document_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "deterministic_mode": self.deterministic_mode,
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "prompt_version": self.prompt_version,
            "profile_version": self.profile_version,
            "provider_response_hash": self.provider_response_hash,
            "candidates": [
                _candidate_to_serializable(c) for c in self.candidates
            ],
            "validation_findings": [
                _finding_to_serializable(f) for f in self.validation_findings
            ],
            "context_hashes": dict(sorted(self.context_hashes.items())),
            "content_unit_ids": sorted(
                [u.unit_id for u in self.content_unit_window]
            ),
            "errors": sorted(self.errors),
        }

    @classmethod
    def create(
        cls,
        *,
        document_id: str,
        provider_name: str,
        provider_version: str,
        deterministic_mode: bool,
        candidates: tuple[Candidate, ...],
        content_unit_window: tuple[ContentUnitRef, ...],
        validation_findings: tuple[ValidationFinding, ...] = (),
        context_hashes: dict[str, str] | None = None,
        errors: tuple[str, ...] = (),
        schema_version: str = BUNDLE_SCHEMA_VERSION,
        case_id: str = "",
        run_id: str | None = None,
        prompt_version: str = "placeholder",
        profile_version: str = "placeholder",
        provider_response_hash: str = "",
    ) -> "ReviewBundle":
        return cls(
            review_bundle_id=f"bundle_{uuid4()}",
            run_id=run_id or f"run_{uuid4()}",
            document_id=document_id,
            provider_name=provider_name,
            provider_version=provider_version,
            deterministic_mode=deterministic_mode,
            created_at=datetime.now(timezone.utc),
            candidates=candidates,
            content_unit_window=content_unit_window,
            validation_findings=validation_findings,
            context_hashes=context_hashes or {},
            errors=errors,
            schema_version=schema_version,
            case_id=case_id,
            prompt_version=prompt_version,
            profile_version=profile_version,
            provider_response_hash=provider_response_hash,
        )

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def accepted_count(self) -> int:
        """Count of candidates that passed QuoteGate (no error findings)."""
        failed_ids = {
            f.candidate_id
            for f in self.validation_findings
            if f.is_error() and f.candidate_id
        }
        return sum(
            1
            for c in self.candidates
            if getattr(c, "candidate_id", "") not in failed_ids
        )

    @property
    def rejected_count(self) -> int:
        """Count of candidates with validation errors."""
        return self.candidate_count - self.accepted_count

    @property
    def accepted_candidate_ids(self) -> tuple[str, ...]:
        failed_ids = {
            f.candidate_id
            for f in self.validation_findings
            if f.is_error() and f.candidate_id
        }
        return tuple(
            getattr(c, "candidate_id", "")
            for c in self.candidates
            if getattr(c, "candidate_id", "") not in failed_ids
        )

    @property
    def rejected_candidate_ids(self) -> tuple[str, ...]:
        failed_ids = {
            f.candidate_id
            for f in self.validation_findings
            if f.is_error() and f.candidate_id
        }
        return tuple(
            getattr(c, "candidate_id", "")
            for c in self.candidates
            if getattr(c, "candidate_id", "") in failed_ids
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "review_bundle_id": self.review_bundle_id,
            "run_id": self.run_id,
            "document_id": self.document_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "deterministic_mode": self.deterministic_mode,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "candidate_count": self.candidate_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "validation_finding_count": len(self.validation_findings),
            "error_count": self.error_count,
            "bundle_sha256": self.bundle_sha256,
            "context_hashes": self.context_hashes,
        }

    def __repr__(self) -> str:
        return (
            f"ReviewBundle(id={self.review_bundle_id}, "
            f"provider={self.provider_name}, "
            f"candidates={self.candidate_count}, "
            f"accepted={self.accepted_count}, "
            f"rejected={self.rejected_count}, "
            f"sha256={self.bundle_sha256[:12]}…)"
        )
