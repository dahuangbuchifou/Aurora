"""ReviewDecision — human review decisions for extraction candidates.

Separate from ReviewBundle to preserve immutability.
Decisions are stored independently and matched by run_id + bundle_sha256.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class ReviewDecisionDecision(StrEnum):
    """Human decision on an extraction candidate."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVISE_AND_APPROVE = "REVISE_AND_APPROVE"


@dataclass
class ReviewDecision:
    """A single human review decision for a candidate.

    Mutable by design — intended for human editing.
    Stored independently from the immutable ReviewBundle.
    """

    run_id: str
    bundle_sha256: str
    candidate_id: str
    decision: ReviewDecisionDecision
    reviewer: str = ""
    reviewer_role: str = ""
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revised_statement: str | None = None
    note: str | None = None

    def validate(self) -> list[str]:
        """Validate the decision's integrity.

        Returns list of validation error messages (empty = valid).
        """
        errors: list[str] = []

        if not self.run_id:
            errors.append("run_id is required")
        if not self.bundle_sha256 or len(self.bundle_sha256) != 64:
            errors.append("bundle_sha256 must be a 64-char hex string")
        if not self.candidate_id:
            errors.append("candidate_id is required")
        if not self.reviewer:
            errors.append("reviewer is required")

        if self.decision not in ReviewDecisionDecision:
            errors.append(f"invalid decision: {self.decision}")

        if self.decision == ReviewDecisionDecision.REVISE_AND_APPROVE:
            if not self.revised_statement:
                errors.append(
                    "revised_statement is required when decision is REVISE_AND_APPROVE"
                )

        return errors

    def is_valid(self) -> bool:
        """Check if the decision is valid."""
        return len(self.validate()) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-serializable dict."""
        return {
            "run_id": self.run_id,
            "bundle_sha256": self.bundle_sha256,
            "candidate_id": self.candidate_id,
            "decision": self.decision.value,
            "reviewer": self.reviewer,
            "reviewer_role": self.reviewer_role,
            "reviewed_at": self.reviewed_at.isoformat(),
            "revised_statement": self.revised_statement,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewDecision":
        """Deserialize from a dict."""
        reviewed_at = data.get("reviewed_at")
        if isinstance(reviewed_at, str):
            reviewed_at = datetime.fromisoformat(reviewed_at)
        return cls(
            run_id=data["run_id"],
            bundle_sha256=data["bundle_sha256"],
            candidate_id=data["candidate_id"],
            decision=ReviewDecisionDecision(data["decision"]),
            reviewer=data.get("reviewer", ""),
            reviewer_role=data.get("reviewer_role", ""),
            reviewed_at=reviewed_at or datetime.now(timezone.utc),
            revised_statement=data.get("revised_statement"),
            note=data.get("note"),
        )
