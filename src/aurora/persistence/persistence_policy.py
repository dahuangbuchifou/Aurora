"""PersistencePolicy — formal entry guard for draft persistence.

R3-01: Policy must be provided for real writes (non-dry-run).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class PersistencePolicy:
    """Policy controlling draft persistence behavior.

    Attributes:
        allowed_providers: Set of allowed provider IDs.
        allowed_profiles: Set of allowed profile IDs.
        workspace_id: Target workspace identifier.
        existing_object_resolver: Resolves pre-existing core object IDs
            for cross-bundle reference validation. Optional.
        dry_run: If True, validate + map but do not write to DB.
        require_source_graph: If True, raise when independence_group
            is "pending_source_graph" (i.e., unresolved). Default True.
    """

    allowed_providers: frozenset[str]
    allowed_profiles: frozenset[str]
    workspace_id: str
    existing_object_resolver: Callable[[str], dict | None] | None = None
    dry_run: bool = False
    require_source_graph: bool = True
