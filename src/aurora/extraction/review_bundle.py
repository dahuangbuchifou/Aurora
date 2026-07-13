"""ReviewBundle — immutable audit trail for extraction runs.

Generated once per extraction run. Immutable after creation.
Human decisions are stored separately in review_decisions.json.
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


@dataclass(frozen=True)
class ExtractionError:
    """Record of an extraction error with context."""

    code: str
    message: str
    candidate_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewBundle:
    """Immutable bundle of extraction results for human review.

    Once created, the SHA-256 hash and all fields are fixed.
    Human decisions are stored in ReviewDecision objects and
    matched by (run_id, bundle_sha256).
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
    errors: tuple[ExtractionError, ...]
    schema_version: str = "1.1"
    case_id: str = ""
    bundle_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        sha = hashlib.sha256()
        # Include only data-content fields in hash computation (NOT UUIDs)
        # This ensures deterministic SHA-256 for same extraction results
        sha.update(self.document_id.encode("utf-8"))
        sha.update(self.provider_name.encode("utf-8"))
        sha.update(self.provider_version.encode("utf-8"))
        sha.update(str(self.deterministic_mode).encode("utf-8"))
        sha.update(self.schema_version.encode("utf-8"))
        sha.update(self.case_id.encode("utf-8"))

        # Hash candidates deterministically by converting to sorted JSON
        # Exclude candidate_id (UUID) for deterministic hash
        candidate_dicts = []
        for c in self.candidates:
            d = self._candidate_to_dict(c)
            d.pop("candidate_id", None)
            candidate_dicts.append(d)
        candidates_json = json.dumps(
            candidate_dicts,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        sha.update(candidates_json.encode("utf-8"))

        # Hash ContentUnit refs (text + sequence only, exclude unit_id)
        for unit in self.content_unit_window:
            sha.update(str(unit.sequence_no).encode("utf-8"))
            sha.update(unit.text.encode("utf-8"))

        # Hash errors
        for err in self.errors:
            sha.update(err.code.encode("utf-8"))
            sha.update(err.message.encode("utf-8"))
            sha.update(err.candidate_id.encode("utf-8"))

        object.__setattr__(self, "bundle_sha256", sha.hexdigest())

    @staticmethod
    def _candidate_to_dict(candidate: Candidate) -> dict[str, Any]:
        """Serialize a candidate to a dict for hash computation."""
        return candidate.model_dump() if hasattr(candidate, "model_dump") else str(candidate)

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
        errors: tuple[ExtractionError, ...] = (),
        schema_version: str = "1.1",
        case_id: str = "",
    ) -> "ReviewBundle":
        """Create a new ReviewBundle with generated IDs."""
        return cls(
            review_bundle_id=f"bundle_{uuid4()}",
            run_id=f"run_{uuid4()}",
            document_id=document_id,
            provider_name=provider_name,
            provider_version=provider_version,
            deterministic_mode=deterministic_mode,
            created_at=datetime.now(timezone.utc),
            candidates=candidates,
            content_unit_window=content_unit_window,
            errors=errors,
            schema_version=schema_version,
            case_id=case_id,
        )

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-serializable dict."""
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
            "error_count": self.error_count,
            "bundle_sha256": self.bundle_sha256,
        }

    def __repr__(self) -> str:
        return (
            f"ReviewBundle(id={self.review_bundle_id}, "
            f"provider={self.provider_name}, "
            f"candidates={self.candidate_count}, "
            f"sha256={self.bundle_sha256[:12]}…)"
        )
