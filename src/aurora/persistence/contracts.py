"""Persistence contracts for Gate 3 draft persistence.

Defines DraftRecord (immutable result of persisting a single draft object),
DraftTransaction (atomic batch result), and contract protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class DraftAction(Enum):
    CREATED = auto()
    REUSED = auto()  # Idempotent: pre-existing, returned without re-creation


@dataclass(frozen=True)
class DraftRecord:
    """Result of persisting a single draft object."""

    object_type: str  # entity | data_point | claim | evidence
    object_id: str
    stable_identity_hash: str
    action: DraftAction
    candidate_id: str | None = None


@dataclass(frozen=True)
class DraftTransaction:
    """Result of an atomic draft persistence batch."""

    records: tuple[DraftRecord, ...]
    total_objects: int
    created_count: int
    reused_count: int
    processing_run_id: str
    succeeded: bool = True
    error_message: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.total_objects == 0
