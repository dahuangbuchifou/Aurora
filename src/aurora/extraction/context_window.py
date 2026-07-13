"""Context Window — deterministic ordered snapshot of ContentUnits for extraction.

From M2-002 ContentUnit list → ContextWindow with SHA-256 identity.
All candidates must reference units within the window.

V1.2c: Added document_id cross-verification — every unit must belong
to the declared document. Units from other documents are rejected.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, FrozenSet, Sequence

from aurora.core.models.document import ContentUnit


class ContextWindowError(ValueError):
    """Raised when ContentUnits violate document boundary invariants."""
    pass


@dataclass(frozen=True)
class ContentUnitRef:
    """Immutable lightweight reference to a ContentUnit within ContextWindow."""

    unit_id: str
    sequence_no: int
    unit_type: str
    text: str
    document_id: str

    @classmethod
    def from_content_unit(cls, unit: ContentUnit) -> "ContentUnitRef":
        return cls(
            unit_id=unit.id,
            sequence_no=unit.sequence_no,
            unit_type=unit.unit_type.value,
            text=unit.text,
            document_id=unit.document_id,
        )


@dataclass(frozen=True)
class ContextWindow:
    """Deterministic ordered window of ContentUnits for extraction.

    Immutable after construction. All extraction candidates MUST reference
    ContentUnits within this window (enforced by QuoteGate).
    """

    document_id: str
    units: tuple[ContentUnitRef, ...]
    window_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        sha = hashlib.sha256()
        for unit in self.units:
            # Hash only content (text + sequence), not UUID
            sha.update(str(unit.sequence_no).encode("utf-8"))
            sha.update(unit.text.encode("utf-8"))
        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(self, "window_sha256", sha.hexdigest())

    @classmethod
    def from_content_units(
        cls, document_id: str, units: Sequence[ContentUnit]
    ) -> "ContextWindow":
        """Build a ContextWindow from a list of ContentUnits.

        Units are sorted deterministically by sequence_no ascending.
        Ties are broken by unit_id for absolute stability.
        
        Raises:
            ContextWindowError: If any unit's document_id doesn't match.
        """
        for unit in units:
            if unit.document_id != document_id:
                raise ContextWindowError(
                    f"ContentUnit {unit.id} has document_id='{unit.document_id}' "
                    f"but ContextWindow expects document_id='{document_id}'"
                )
        refs = [ContentUnitRef.from_content_unit(u) for u in units]
        refs.sort(key=lambda r: (r.sequence_no, r.unit_id))
        return cls(document_id=document_id, units=tuple(refs))

    @property
    def unit_ids(self) -> FrozenSet[str]:
        """Return the set of all ContentUnit IDs in this window."""
        return frozenset(u.unit_id for u in self.units)

    def get_unit_by_id(self, unit_id: str) -> ContentUnitRef | None:
        """Look up a ContentUnitRef by unit_id."""
        for unit in self.units:
            if unit.unit_id == unit_id:
                return unit
        return None

    def get_unit_text(self, unit_id: str) -> str | None:
        """Get the normalized text of a ContentUnit by ID."""
        unit = self.get_unit_by_id(unit_id)
        return unit.text if unit else None

    def all_text(self) -> str:
        """Concatenated text of all units in order (for quote matching)."""
        return "\n".join(u.text for u in self.units)

    def __len__(self) -> int:
        return len(self.units)

    def __repr__(self) -> str:
        return (
            f"ContextWindow(document_id={self.document_id!r}, "
            f"units={len(self.units)}, "
            f"sha256={self.window_sha256[:12]}…)"
        )
