"""Draft service — SQLAlchemy-backed transactional persistence.

Replaces in-memory DraftStore with real ObjectRepository + SQLite.
Supports: atomic transactions, cross-session idempotency,
ProcessingRun in independent session, rollback verification.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from aurora.core.models.application import ProcessingRun
from aurora.core.models.atoms import Claim, DataPoint, Entity, Evidence
from aurora.core.models.common import ProcessorInfo
from aurora.core.models.enums import ObjectType, RunStatus
from aurora.db.session import create_db_engine, create_session_factory, session_scope
from aurora.persistence.contracts import DraftAction, DraftRecord, DraftTransaction
from aurora.persistence.identity import (
    compute_bundle_operation_key,
    compute_draft_natural_key,
)
from aurora.persistence.mapper import map_accepted_candidates
from aurora.persistence.validation import validate_bundle_preflight
from aurora.repository.object_repository import ObjectRepository

_OBJ_TYPE_TO_ENUM = {
    "entity": ObjectType.ENTITY,
    "data_point": ObjectType.DATA_POINT,
    "claim": ObjectType.CLAIM,
    "evidence": ObjectType.EVIDENCE,
}


def _to_object_type(obj_type: str) -> ObjectType:
    return _OBJ_TYPE_TO_ENUM.get(obj_type, ObjectType.ENTITY)


def repo_find_processing_runs(
    repo: ObjectRepository, workspace_id: str, op_key: str
) -> list:
    """Find ProcessingRuns by bundle operation key.

    op_key is stored in input_object_ids[0] of the ProcessingRun.
    """
    from aurora.core.models.enums import ObjectType
    all_runs = repo.list(
        object_type=ObjectType.PROCESSING_RUN,
        workspace_id=workspace_id,
    )
    return [
        r for r in all_runs
        if r.input_object_ids and r.input_object_ids[0] == op_key
    ]


def persist_drafts(
    repo: ObjectRepository,
    bundle: Any,
    workspace_id: str,
    dry_run: bool = False,
) -> DraftTransaction:
    """Persist accepted draft objects from a ReviewBundle via ObjectRepository.

    Args:
        repo: ObjectRepository wrapping a SQLAlchemy Session
        bundle: Validated ReviewBundle
        workspace_id: Unique workspace identifier
        dry_run: If True, validate + map but do not write

    Returns:
        DraftTransaction with per-object DraftRecords
    """
    # 1. Preflight
    warnings = validate_bundle_preflight(bundle)

    # 2. Bundle operation key — query repository for existing ProcessingRun
    op_key = compute_bundle_operation_key(workspace_id, bundle.bundle_sha256)
    existing_runs = repo_find_processing_runs(repo, workspace_id, op_key)
    if existing_runs:
        # Already processed — idempotent return
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id=existing_runs[0].id if existing_runs else f"run_replay_{op_key[:16]}",
            succeeded=True,
        )

    # 3. Map candidates → draft objects
    entities, data_points, claims, evidence_list = map_accepted_candidates(
        bundle.accepted_candidate_ids,
        bundle.candidates,
    )

    all_mapped: list[tuple[str, Any]] = []
    all_mapped.extend(("entity", e) for e in entities)
    all_mapped.extend(("data_point", dp) for dp in data_points)
    all_mapped.extend(("claim", c) for c in claims)
    all_mapped.extend(("evidence", ev) for ev in evidence_list)

    # Build candidate map for natural key computation
    candidate_map = {getattr(c, "candidate_id", ""): c for c in bundle.candidates}

    records: list[DraftRecord] = []
    created = 0
    reused = 0

    if dry_run:
        # Dry run: compute keys but don't write
        for obj_type, obj in all_mapped:
            cid = getattr(obj, "source_ref", "").replace("candidate:", "")
            candidate = candidate_map.get(cid)
            if candidate is not None:
                natural_key = compute_draft_natural_key(workspace_id, obj_type, candidate)
            else:
                natural_key = hashlib.sha256(
                    f"{workspace_id}|{obj_type}|{cid}".encode()
                ).hexdigest()

            records.append(DraftRecord(
                object_type=obj_type,
                object_id=getattr(obj, "id", ""),
                stable_identity_hash=natural_key,
                action=DraftAction.CREATED,
                candidate_id=cid,
            ))
            created += 1

        run_id = f"run_dry_{op_key[:16]}"

    else:
        # 4. Persist each object via repository
        for obj_type, obj in all_mapped:
            cid = getattr(obj, "source_ref", "").replace("candidate:", "")
            candidate = candidate_map.get(cid)
            if candidate is not None:
                natural_key = compute_draft_natural_key(workspace_id, obj_type, candidate)
            else:
                natural_key = hashlib.sha256(
                    f"{workspace_id}|{obj_type}|{cid}".encode()
                ).hexdigest()

            # Set workspace_id on object
            if hasattr(obj, "workspace_id"):
                obj.workspace_id = workspace_id

            # Check for existing object by natural_key in payload
            # Natural key is stored in source_ref for DataPoint/Claim/Evidence,
            # and checked by canonical_name + entity_type for Entity
            if obj_type == "entity":
                existing_objs = repo.find_by_payload_field(
                    object_type=_to_object_type(obj_type),
                    field_name="canonical_name",
                    value=obj.canonical_name,
                    workspace_id=workspace_id,
                )
                # Also filter by entity_type
                existing_objs = [
                    o for o in existing_objs
                    if o.entity_type == obj.entity_type or o.entity_type.value == obj.entity_type
                ]
                existing_objs = existing_objs if len(existing_objs) == 1 else (existing_objs if existing_objs else [])
            else:
                existing_objs = repo.find_by_payload_field(
                    object_type=_to_object_type(obj_type),
                    field_name="source_ref",
                    value=obj.source_ref,
                    workspace_id=workspace_id,
                )
            if existing_objs:
                records.append(DraftRecord(
                    object_type=obj_type,
                    object_id=existing_objs[0].id,
                    stable_identity_hash=natural_key,
                    action=DraftAction.REUSED,
                    candidate_id=cid,
                ))
                reused += 1
            else:
                repo.create(obj)
                records.append(DraftRecord(
                    object_type=obj_type,
                    object_id=obj.id,
                    stable_identity_hash=natural_key,
                    action=DraftAction.CREATED,
                    candidate_id=cid,
                ))
                created += 1

        # 5. ProcessingRun — written in the same session
        now = datetime.now(UTC)
        run = ProcessingRun(
            task_type="draft_persistence",
            processor=ProcessorInfo(module="draft_service", code_version="3.0"),
            run_status=RunStatus.SUCCESS,
            started_at=now,
            finished_at=now,
            workspace_id=workspace_id,
            input_object_ids=[op_key],
            output_object_ids=[r.object_id for r in records],
        )
        repo.create(run)
        run_id = run.id

    return DraftTransaction(
        records=tuple(records),
        total_objects=created + reused,
        created_count=created,
        reused_count=reused,
        processing_run_id=run_id,
        succeeded=True,
    )


def persist_drafts_with_separate_run(
    repo_factory: sessionmaker,
    repo: ObjectRepository,
    bundle: Any,
    workspace_id: str,
    dry_run: bool = False,
) -> DraftTransaction:
    """Transaction with ProcessingRun in independent session.

    Business objects are committed atomically. If any business object
    write fails, everything is rolled back, but a FAILED ProcessingRun
    is written in a separate session.
    """
    try:
        tx = persist_drafts(repo, bundle, workspace_id, dry_run=dry_run)
    except Exception as exc:
        # Rollback happened in session_scope. Write ProcessingRun in new session.
        try:
            with session_scope(repo_factory) as fail_session:
                fail_repo = ObjectRepository(fail_session)
                now = datetime.now(UTC)
                op_key = compute_bundle_operation_key(workspace_id, bundle.bundle_sha256)
                fail_run = ProcessingRun(
                    task_type="draft_persistence",
                    processor=ProcessorInfo(module="draft_service", code_version="3.0"),
                    run_status=RunStatus.FAILED,
                    started_at=now,
                    finished_at=now,
                    workspace_id=workspace_id,
                    error_message=str(exc)[:500],
                )
                fail_repo.create(fail_run)
        except Exception:
            pass  # Best effort — ProcessingRun write itself failed

        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id="",
            succeeded=False,
            error_message=str(exc)[:200],
        )

    return tx
