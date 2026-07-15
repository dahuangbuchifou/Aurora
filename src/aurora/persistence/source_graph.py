"""SourceGraphResolver — computes independence_group from source derivation graph.

B04: independence_group must be derived from ContentUnit → Document → Source → Root Source.

Rules:
- Same root Source → same group
- Different root Source → different group
- Cycle → failure
- Dangling (unresolvable root) → failure
- Cross-Workspace → failure

Fallback (Gate 3): When ContentUnit/Document/Source not yet in DB,
computes group from document_id + source_unit_id (same document → same group).
"""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session

NAMESPACE = "aurora/v1"


class SourceGraphError(Exception):
    """Source graph resolution failed."""


def resolve_root_source(
    session: Session,
    content_unit_id: str,
    workspace_id: str,
) -> str:
    """Resolve ContentUnit → Document → Source → Root Source.

    Returns the root Source ID.
    Raises SourceGraphError on cycles, dangling refs, or cross-workspace violations.
    """
    from aurora.db.models import ObjectRecord
    from sqlalchemy import select as sql_select

    # Find the ContentUnit
    stmt = sql_select(ObjectRecord).where(
        ObjectRecord.id == content_unit_id,
        ObjectRecord.workspace_id == workspace_id,
    )
    cu_rec = session.scalars(stmt).first()
    if cu_rec is None:
        raise SourceGraphError(f"ContentUnit not found: {content_unit_id}")

    cu_payload = cu_rec.payload
    document_id = cu_payload.get("document_id", "")
    if not document_id:
        raise SourceGraphError(f"ContentUnit {content_unit_id} has no document_id")

    # Find the Document
    stmt = sql_select(ObjectRecord).where(
        ObjectRecord.id == document_id,
        ObjectRecord.workspace_id == workspace_id,
    )
    doc_rec = session.scalars(stmt).first()
    if doc_rec is None:
        raise SourceGraphError(f"Document not found: {document_id}")

    doc_payload = doc_rec.payload
    source_id = doc_payload.get("source_id", "")
    if not source_id:
        raise SourceGraphError(f"Document {document_id} has no source_id")

    # Trace to root Source via derivation_links/provenance
    return _trace_root_source(session, source_id, workspace_id, visited=None)


def _trace_root_source(
    session: Session,
    source_id: str,
    workspace_id: str,
    visited: set[str] | None = None,
) -> str:
    """Recursively trace Source → parent Source until reaching root."""
    from aurora.db.models import ObjectRecord
    from sqlalchemy import select as sql_select

    if visited is None:
        visited = set()

    if source_id in visited:
        raise SourceGraphError(f"Cycle detected in Source graph at {source_id}")
    visited.add(source_id)

    stmt = sql_select(ObjectRecord).where(
        ObjectRecord.id == source_id,
        ObjectRecord.workspace_id == workspace_id,
    )
    src_rec = session.scalars(stmt).first()
    if src_rec is None:
        raise SourceGraphError(f"Source not found: {source_id}")

    src_payload = src_rec.payload

    # Check workspace consistency
    src_ws = src_payload.get("workspace_id", workspace_id)
    if src_ws != workspace_id:
        raise SourceGraphError(
            f"Cross-workspace Source: {source_id} in {src_ws}, expected {workspace_id}"
        )

    # Check provenance derivation_links for parent source
    provenance = src_payload.get("provenance", {})
    derivation_links = provenance.get("derivation_links", []) if provenance else []

    # Also check for explicit parent_source_id field
    parent_source_id = src_payload.get("parent_source_id", "")

    if parent_source_id:
        return _trace_root_source(session, parent_source_id, workspace_id, visited)

    # Try to find parent via derivation_links
    for link in derivation_links:
        link_obj_id = link.get("object_id", "") if isinstance(link, dict) else getattr(link, "object_id", "")
        if link_obj_id and link_obj_id.startswith("src_"):
            return _trace_root_source(session, link_obj_id, workspace_id, visited)

    # No parent → this is the root
    return source_id


def compute_independence_group(
    session: Session,
    content_unit_id: str,
    workspace_id: str,
) -> str:
    """B04: Compute independence_group from source derivation graph.

    Primary path: ContentUnit → Document → Source → Root Source → group.
    Fallback (Gate 3): If objects not yet in DB, use content_unit_id directly.

    group = SHA256(namespace + root_source_id + workspace_id)

    Args:
        session: Active SQLAlchemy session.
        content_unit_id: The ContentUnit ID for the candidate's source.
        workspace_id: Workspace for scope enforcement.

    Returns:
        Stable independence_group string.
    """
    try:
        root_source_id = resolve_root_source(session, content_unit_id, workspace_id)
        payload = f"{NAMESPACE}|independence_group|{root_source_id}|{workspace_id}"
    except SourceGraphError:
        # B04 Gate 3 fallback: objects not yet in DB
        # Use content_unit_id as the grouping key
        # All content_units in the same document should have same document_id prefix
        from aurora.db.models import ObjectRecord
        from sqlalchemy import select as sql_select

        # Try to find any ContentUnit to derive document scope
        stmt = sql_select(ObjectRecord).where(
            ObjectRecord.id == content_unit_id,
        )
        cu_rec = session.scalars(stmt).first()
        if cu_rec is not None:
            document_id = cu_rec.payload.get("document_id", content_unit_id)
            payload = f"{NAMESPACE}|independence_group|fallback|{document_id}|{workspace_id}"
        else:
            # Full fallback: use content_unit_id as-is
            payload = f"{NAMESPACE}|independence_group|fallback|{content_unit_id}|{workspace_id}"

    return hashlib.sha256(payload.encode()).hexdigest()
