"""SourceGraphResolver — computes independence_group from source derivation graph.

B04: independence_group must be derived from ContentUnit → Document → Source → Root Source.

R2-B03: No fallback. Resolution failure → SourceGraphError → transaction rollback.

Rules:
- Same root Source → same group
- Different root Source → different group
- Cycle → failure
- Dangling (unresolvable root) → failure
- Cross-Workspace → failure
- ContentUnit/Document/Source not in DB → failure (must have DB fixture)
"""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

NAMESPACE = "aurora/v1"


class SourceGraphError(Exception):
    """Source graph resolution failed — must halt the transaction."""


def resolve_root_source(
    session: Session,
    content_unit_id: str,
    workspace_id: str,
) -> str:
    """Resolve ContentUnit → Document → Source → Root Source.

    Returns the root Source ID.
    Raises SourceGraphError on any failure — no fallback.
    """
    from aurora.db.models import ObjectRecord
    from sqlalchemy import select as sql_select

    stmt = sql_select(ObjectRecord).where(
        ObjectRecord.id == content_unit_id,
        ObjectRecord.workspace_id == workspace_id,
        ObjectRecord.deleted_at.is_(None),
    )
    cu_rec = session.scalars(stmt).first()
    if cu_rec is None:
        raise SourceGraphError(f"ContentUnit not found: {content_unit_id}")

    cu_payload = cu_rec.payload
    document_id = cu_payload.get("document_id", "")
    if not document_id:
        raise SourceGraphError(f"ContentUnit {content_unit_id} has no document_id")

    stmt = sql_select(ObjectRecord).where(
        ObjectRecord.id == document_id,
        ObjectRecord.workspace_id == workspace_id,
        ObjectRecord.deleted_at.is_(None),
    )
    doc_rec = session.scalars(stmt).first()
    if doc_rec is None:
        raise SourceGraphError(f"Document not found: {document_id}")

    doc_payload = doc_rec.payload
    source_id = doc_payload.get("source_id", "")
    if not source_id:
        raise SourceGraphError(f"Document {document_id} has no source_id")

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
        ObjectRecord.deleted_at.is_(None),
    )
    src_rec = session.scalars(stmt).first()
    if src_rec is None:
        raise SourceGraphError(f"Source not found: {source_id}")

    src_payload = src_rec.payload

    src_ws = src_payload.get("workspace_id", workspace_id)
    if src_ws != workspace_id:
        raise SourceGraphError(
            f"Cross-workspace Source: {source_id} in {src_ws}, expected {workspace_id}"
        )

    provenance = src_payload.get("provenance", {})
    derivation_links = provenance.get("derivation_links", []) if provenance else []

    parent_source_id = src_payload.get("parent_source_id", "")

    if parent_source_id:
        return _trace_root_source(session, parent_source_id, workspace_id, visited)

    for link in derivation_links:
        link_obj_id = link.get("object_id", "") if isinstance(link, dict) else getattr(link, "object_id", "")
        if link_obj_id and link_obj_id.startswith("src_"):
            return _trace_root_source(session, link_obj_id, workspace_id, visited)

    return source_id  # root reached


def compute_independence_group(
    session: Session,
    content_unit_id: str,
    workspace_id: str,
) -> str:
    """R2-B03: Compute independence_group. Raises SourceGraphError on failure.

    No fallback — if source graph resolution fails, the entire transaction fails.
    """
    root_source_id = resolve_root_source(session, content_unit_id, workspace_id)
    payload = f"{NAMESPACE}|independence_group|{root_source_id}|{workspace_id}"
    return hashlib.sha256(payload.encode()).hexdigest()
