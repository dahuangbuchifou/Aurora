"""Context Window — deterministic ordered snapshot of ContentUnits for extraction.

V2: Canonicalized JSON hash (context_schema_version, document_id, units with
unit_id/seq_no/unit_type/text_sha256/locator_sha256).
UTF-8, sort_keys=true, separators=(",", ":"), SHA-256.
"""

from __future__ import annotations

import hashlib
import json
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

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def locator_sha256(self) -> str:
        """Stable SHA-256 of the locator representation."""
        locator_data = json.dumps(
            self._locator_dict(),
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(locator_data.encode("utf-8")).hexdigest()

    def _locator_dict(self) -> dict[str, Any]:
        """Build deterministic locator dict for hashing."""
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "document_id": self.document_id,
        }

    def to_hash_dict(self) -> dict[str, Any]:
        """Return canonical dict for context hash computation (V2 format)."""
        return {
            "unit_id": self.unit_id,
            "sequence_no": self.sequence_no,
            "unit_type": self.unit_type,
            "text_sha256": self.text_sha256,
            "locator_sha256": self.locator_sha256,
        }


# Frozen candidate type ordering for G1-6/G1-7 stability
CANDIDATE_TYPE_ORDER: tuple[str, ...] = (
    "entity",
    "data_point",
    "claim",
    "evidence",
    "fact",
)


@dataclass(frozen=True)
class ContextWindow:
    """Deterministic ordered window of ContentUnits for extraction.

    V2 changes:
    - Hash uses canonicalized JSON (context_schema_version, document_id, units)
    - Rejects empty windows
    - Rejects duplicate unit_ids
    - Rejects duplicate (sequence_no, unit_id) pairs
    - Input order changes do not affect output order
    """

    document_id: str
    units: tuple[ContentUnitRef, ...]
    window_sha256: str = field(init=False)
    context_schema_version: str = field(default="1.0")

    def __post_init__(self) -> None:
        # --- Validation ---
        if not self.units:
            raise ContextWindowError("ContextWindow must contain at least one unit")

        seen_ids: set[str] = set()
        seen_pairs: set[tuple[int, str]] = set()
        for unit in self.units:
            if unit.document_id != self.document_id:
                raise ContextWindowError(
                    f"ContentUnit {unit.unit_id} has document_id='{unit.document_id}' "
                    f"but ContextWindow expects document_id='{self.document_id}'"
                )
            if unit.unit_id in seen_ids:
                raise ContextWindowError(
                    f"Duplicate unit_id in ContextWindow: {unit.unit_id}"
                )
            seen_ids.add(unit.unit_id)
            pair = (unit.sequence_no, unit.unit_id)
            if pair in seen_pairs:
                raise ContextWindowError(
                    f"Duplicate (sequence_no, unit_id) pair: ({unit.sequence_no}, {unit.unit_id})"
                )
            seen_pairs.add(pair)

        # --- Canonicalized JSON hash (V2) ---
        hash_dict = self._to_hash_dict()
        canonical_json = json.dumps(
            hash_dict,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        sha = hashlib.sha256(canonical_json.encode("utf-8"))
        object.__setattr__(self, "window_sha256", sha.hexdigest())

    def _to_hash_dict(self) -> dict[str, Any]:
        return {
            "context_schema_version": self.context_schema_version,
            "document_id": self.document_id,
            "units": [u.to_hash_dict() for u in self.units],
        }

    @classmethod
    def from_content_units(
        cls, document_id: str, units: Sequence[ContentUnit]
    ) -> "ContextWindow":
        """Build a ContextWindow from a list of ContentUnits.

        Units are sorted deterministically by sequence_no ascending.
        Ties broken by unit_id for absolute stability.
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

    @classmethod
    def from_content_unit_refs(
        cls, document_id: str, refs: Sequence[ContentUnitRef]
    ) -> "ContextWindow":
        """Build from ContentUnitRefs (already sorted)."""
        sorted_refs = sorted(refs, key=lambda r: (r.sequence_no, r.unit_id))
        return cls(document_id=document_id, units=tuple(sorted_refs))

    @property
    def unit_ids(self) -> FrozenSet[str]:
        return frozenset(u.unit_id for u in self.units)

    def get_unit_by_id(self, unit_id: str) -> ContentUnitRef | None:
        for unit in self.units:
            if unit.unit_id == unit_id:
                return unit
        return None

    def get_unit_text(self, unit_id: str) -> str | None:
        unit = self.get_unit_by_id(unit_id)
        return unit.text if unit else None

    def has_unit(self, unit_id: str) -> bool:
        return any(u.unit_id == unit_id for u in self.units)

    def all_text(self) -> str:
        return "\n".join(u.text for u in self.units)

    def __len__(self) -> int:
        return len(self.units)

    def __repr__(self) -> str:
        return (
            f"ContextWindow(document_id={self.document_id!r}, "
            f"units={len(self.units)}, "
            f"sha256={self.window_sha256[:12]}…)"
        )
