"""Draft service — transactional persistence with in-memory store.

Uses in-memory dict as draft store (no SQLite/SQLAlchemy dependency).
Supports atomic transaction, idempotent reuse, ProcessingRun audit.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from aurora.core.models.application import ProcessingRun
from aurora.core.models.atoms import Claim, DataPoint, Entity, Evidence
from aurora.core.models.common import ProcessorInfo
from aurora.core.models.enums import RunStatus
from aurora.persistence.contracts import DraftAction, DraftRecord, DraftTransaction
from aurora.persistence.identity import (
    compute_bundle_operation_key,
    compute_draft_natural_key,
)
from aurora.persistence.mapper import map_accepted_candidates
from aurora.persistence.validation import validate_bundle_preflight


@dataclass
class DraftStore:
    """In-memory draft store with stable identity index."""

    entities: dict[str, Entity] = field(default_factory=dict)
    data_points: dict[str, DataPoint] = field(default_factory=dict)
    claims: dict[str, Claim] = field(default_factory=dict)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    processing_runs: list[ProcessingRun] = field(default_factory=list)
    bundle_operation_keys: set[str] = field(default_factory=set)


def _make_processing_run(
    task_type: str, run_status: RunStatus, note: str = ""
) -> ProcessingRun:
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    return ProcessingRun(
        task_type=task_type,
        processor=ProcessorInfo(module="draft_service", code_version="1.0"),
        run_status=run_status,
        started_at=now,
        finished_at=now,
        error_message=note if run_status == RunStatus.FAILED else None,
    )


def persist_drafts(
    store: DraftStore,
    bundle,
    workspace_id: str,
    engine_independence_group: str = "",
    dry_run: bool = False,
) -> DraftTransaction:
    """Persist accepted draft objects from a ReviewBundle.

    Args:
        store: In-memory DraftStore (or replace with DB session later)
        bundle: Validated ReviewBundle
        workspace_id: Unique workspace identifier
        engine_independence_group: independence_group computed by Aurora engine
        dry_run: If True, validate but do not persist

    Returns:
        DraftTransaction with per-object DraftRecords
    """
    # 1. Preflight
    warnings = validate_bundle_preflight(bundle)

    # 2. Bundle operation key for idempotency
    op_key = compute_bundle_operation_key(workspace_id, bundle.bundle_sha256)
    if op_key in store.bundle_operation_keys:
        # Already processed — idempotent return
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id=f"run_replay_{op_key[:16]}",
            succeeded=True,
        )

    # 3. Map candidates → draft objects
    entities, data_points, claims, evidence_list = map_accepted_candidates(
        bundle.accepted_candidate_ids,
        bundle.candidates,
        engine_independence_group,
    )

    all_mapped: list[tuple[str, object]] = []
    all_mapped.extend(("entity", e) for e in entities)
    all_mapped.extend(("data_point", dp) for dp in data_points)
    all_mapped.extend(("claim", c) for c in claims)
    all_mapped.extend(("evidence", ev) for ev in evidence_list)

    records: list[DraftRecord] = []
    created = 0
    reused = 0

    # Build candidate map for natural key computation
    candidate_map = {getattr(c, "candidate_id", ""): c for c in bundle.candidates}

    for obj_type, obj in all_mapped:
        # Find candidate for stable identity
        cid = getattr(obj, "source_ref", "").replace("candidate:", "")
        candidate = candidate_map.get(cid)

        if candidate is not None:
            natural_key = compute_draft_natural_key(workspace_id, obj_type, candidate)
        else:
            natural_key = hashlib.sha256(
                f"{workspace_id}|{obj_type}|{cid}".encode()
            ).hexdigest()

        action = DraftAction.CREATED
        object_id = getattr(obj, "id", f"{obj_type}_draft_{natural_key[:12]}")

        if not dry_run:
            store_map = {
                "entity": store.entities,
                "data_point": store.data_points,
                "claim": store.claims,
                "evidence": store.evidence,
            }.get(obj_type, {})

            if natural_key in store_map:
                action = DraftAction.REUSED
                reused += 1
            else:
                store_map[natural_key] = obj
                created += 1
        else:
            created += 1  # Dry run: count as if created

        records.append(DraftRecord(
            object_type=obj_type,
            object_id=object_id,
            stable_identity_hash=natural_key,
            action=action,
            candidate_id=cid,
        ))

    # 4. Mark bundle as processed
    if not dry_run:
        store.bundle_operation_keys.add(op_key)

    # 5. ProcessingRun
    run = _make_processing_run(
        task_type="draft_persistence",
        run_status=RunStatus.SUCCESS,
        note=f"Created {created}, reused {reused}, "
             f"warnings: {len(warnings)}, dry_run={dry_run}",
    )
    if not dry_run:
        store.processing_runs.append(run)

    return DraftTransaction(
        records=tuple(records),
        total_objects=created + reused,
        created_count=created,
        reused_count=reused,
        processing_run_id=run.id,
        succeeded=True,
    )


def fail_transaction(
    store: DraftStore,
    task_type: str,
    error_message: str,
) -> DraftTransaction:
    """Record a failed ProcessingRun without persisting any objects."""
    run = _make_processing_run(
        task_type=task_type,
        run_status=RunStatus.FAILED,
    )
    store.processing_runs.append(run)
    return DraftTransaction(
        records=(),
        total_objects=0,
        created_count=0,
        reused_count=0,
        processing_run_id=run.id,
        succeeded=False,
        error_message=error_message,
    )
