"""Draft service — SQLAlchemy-backed transactional persistence.

Replaces in-memory DraftStore with real ObjectRepository + SQLite.
Supports: workflow-owned transactions, independent ProcessingRun sessions,
cross-session idempotency with persistent natural keys (B06).

B01: Workflow owns transaction — receives sessionmaker, creates/commits/rolls back internally.
B02: ProcessingRun in independent session — 3-phase transaction:
     (1) RUNNING commit, (2) business objects atomic, (3) SUCCEEDED/FAILED commit.
B03: Full ReviewBundle preflight via validation module.
B05: Strict mapper — no default values, missing required fields fail entire transaction.
B06: Persistent idempotency — operation_key + draft_natural_key stored via external_ids.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select as sql_select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session, sessionmaker

from aurora.core.models.application import ProcessingRun
from aurora.core.models.common import ProcessorInfo
from aurora.core.models.enums import LifecycleStatus, ObjectType, RunStatus
from aurora.db.models import ObjectRecord
from aurora.persistence.contracts import DraftAction, DraftRecord, DraftTransaction
from aurora.persistence.identity import (
    compute_bundle_operation_key,
    compute_draft_natural_key,
)
from aurora.persistence.mapper import map_accepted_candidates
from aurora.persistence.persistence_policy import PersistencePolicy
from aurora.persistence.source_graph import compute_independence_group, SourceGraphError
from aurora.persistence.validation import validate_bundle_preflight

logger = logging.getLogger(__name__)

_OBJ_TYPE_TO_ENUM: dict[str, ObjectType] = {
    "entity": ObjectType.ENTITY,
    "data_point": ObjectType.DATA_POINT,
    "claim": ObjectType.CLAIM,
    "evidence": ObjectType.EVIDENCE,
}

# ── B06: external_id keys for persistent idempotency ────────────────────────

EXT_ID_OPERATION_KEY = "draft_operation_key"
EXT_ID_NATURAL_KEY = "draft_natural_key"
EXT_ID_ORIGIN_CANDIDATE = "draft_origin_candidate_id"
EXT_ID_BUNDLE_SHA256 = "draft_bundle_sha256"


# ── R3-04: Core reference resolution ────────────────────────────────────────

def _resolve_core_references(
    evidence_list: list[Any],
    candidate_to_core: dict[str, str],
) -> list[Any]:
    """R3-04: Convert Evidence target_object_id from candidate ID to core object ID.

    For each Evidence object, if target_object_id is a candidate ID present
    in candidate_to_core, replace it with the corresponding core object ID.
    """
    result: list[Any] = []
    for ev in evidence_list:
        toid = getattr(ev, "target_object_id", "")
        if toid and toid in candidate_to_core:
            ev.target_object_id = candidate_to_core[toid]
        result.append(ev)
    return result


def _lookup_by_natural_key(
    session: Session,
    object_type: ObjectType,
    natural_key: str,
    workspace_id: str,
) -> list[ObjectRecord]:
    """B06: Persistent natural-key lookup via external_ids stored in payload.

    Scans all active records of the object_type in workspace and
    filters on payload.external_ids.draft_natural_key.
    """
    stmt = (
        sql_select(ObjectRecord)
        .where(
            ObjectRecord.object_type == object_type.value,
            ObjectRecord.workspace_id == workspace_id,
            ObjectRecord.deleted_at.is_(None),
        )
    )
    records: list[ObjectRecord] = list(session.scalars(stmt).all())
    result: list[ObjectRecord] = []
    for r in records:
        ext = r.payload.get("external_ids", {})
        if isinstance(ext, dict) and ext.get(EXT_ID_NATURAL_KEY) == natural_key:
            result.append(r)
    return result


def _lookup_by_operation_key(
    session: Session,
    op_key: str,
    workspace_id: str,
) -> tuple[list[ObjectRecord], str | None]:
    """R2-B07: Find ProcessingRun records by operation_key, return run_status.

    Checks external_ids.draft_operation_key and input_object_ids.
    Returns (records, current_status) where status is 'success'/'failed'/'running' or None.
    """
    stmt = sql_select(ObjectRecord).where(
        ObjectRecord.object_type == ObjectType.PROCESSING_RUN.value,
        ObjectRecord.workspace_id == workspace_id,
    )
    records: list[ObjectRecord] = list(session.scalars(stmt).all())
    result: list[ObjectRecord] = []
    current_status: str | None = None
    for r in records:
        ext = r.payload.get("external_ids", {})
        if isinstance(ext, dict) and ext.get(EXT_ID_OPERATION_KEY) == op_key:
            result.append(r)
            current_status = r.payload.get("run_status", "")
            continue
        ioids = r.payload.get("input_object_ids") or []
        if op_key in ioids:
            result.append(r)
            current_status = r.payload.get("run_status", "")
    return result, current_status


# ── B05: strict mapper validation ───────────────────────────────────────────

def _validate_mapped_object(
    obj: Any,
    obj_type: str,
    policy: PersistencePolicy | None = None,
) -> None:
    """R2-B04: Fail-closed on missing required fields — check for None/empty.

    R3-03: pending_source_graph is blocked only when policy.require_source_graph
    is True (strict mode) or when no policy is provided (retroactive strict).
    """
    if obj_type == "entity":
        if not getattr(obj, "canonical_name", None):
            raise ValueError(f"Entity missing canonical_name: {getattr(obj, 'id', '?')}")
        if getattr(obj, "entity_type", None) is None:
            raise ValueError(f"Entity has null entity_type (unrecognized enum): {getattr(obj, 'id', '?')}")
    elif obj_type == "data_point":
        if not getattr(obj, "metric", None):
            raise ValueError(f"DataPoint has empty metric: {getattr(obj, 'id', '?')}")
        if not getattr(obj, "unit", None):
            raise ValueError(f"DataPoint has empty unit: {getattr(obj, 'id', '?')}")
        if getattr(obj, "period", None) is None:
            raise ValueError(f"DataPoint has null period: {getattr(obj, 'id', '?')}")
    elif obj_type == "claim":
        if getattr(obj, "claim_type", None) is None:
            raise ValueError(f"Claim has null claim_type (unrecognized enum): {getattr(obj, 'id', '?')}")
        if not getattr(obj, "statement", None):
            raise ValueError(f"Claim has empty statement: {getattr(obj, 'id', '?')}")
        if not getattr(obj, "asserted_by", None):
            raise ValueError(f"Claim has empty asserted_by: {getattr(obj, 'id', '?')}")
    elif obj_type == "evidence":
        if getattr(obj, "evidence_role", None) is None:
            raise ValueError(f"Evidence has null evidence_role: {getattr(obj, 'id', '?')}")
        if getattr(obj, "evidence_type", None) is None:
            raise ValueError(f"Evidence has null evidence_type: {getattr(obj, 'id', '?')}")
        if not getattr(obj, "target_object_id", None):
            raise ValueError(f"Evidence has empty target_object_id: {getattr(obj, 'id', '?')}")
        # R3-03: pending_source_graph rejection gated on policy
        ig = getattr(obj, "independence_group", "")
        if ig == "pending_source_graph":
            if policy is None or policy.require_source_graph:
                raise ValueError(f"Evidence independence_group not resolved: {getattr(obj, 'id', '?')}")


def _dry_run_persist(bundle, workspace_id, op_key):
    """Dry run: validate + map, build DraftTransaction without DB writes."""
    validate_bundle_preflight(bundle, workspace_id=workspace_id)
    entities, data_points, claims, evidence_list, _c2c = map_accepted_candidates(
        bundle.accepted_candidate_ids, bundle.candidates
    )
    all_mapped = []
    all_mapped.extend(("entity", e) for e in entities)
    all_mapped.extend(("data_point", dp) for dp in data_points)
    all_mapped.extend(("claim", c) for c in claims)
    all_mapped.extend(("evidence", ev) for ev in evidence_list)

    candidate_map = {getattr(c, "candidate_id", ""): c for c in bundle.candidates}
    records = []
    created = 0
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

    return DraftTransaction(
        records=tuple(records),
        total_objects=created,
        created_count=created,
        reused_count=0,
        processing_run_id=op_key[:32],
        succeeded=True,
    )


# ── main entry point ────────────────────────────────────────────────────────

def persist_drafts(
    repo_factory: sessionmaker,
    bundle: Any,
    workspace_id: str,
    dry_run: bool = False,
    preflight_kwargs: dict[str, Any] | None = None,
    policy: PersistencePolicy | None = None,
) -> DraftTransaction:
    """B01+B02: Workflow-owned transaction with independent ProcessingRun sessions.

    Phase 1: Write ProcessingRun (RUNNING) in independent session → commit.
    Phase 2: Write business objects in own session → commit (or rollback).
    Phase 3: Update ProcessingRun (SUCCEEDED/FAILED) in independent session → commit.

    Args:
        repo_factory: sessionmaker for creating sessions (workflow-owned).
        bundle: Validated ReviewBundle.
        workspace_id: Unique workspace identifier.
        dry_run: If True, validate + map but do not write.
    """
    op_key = compute_bundle_operation_key(workspace_id, bundle.bundle_sha256)

    # R3-01: PersistencePolicy is required for real writes
    if policy is None and not dry_run:
        raise ValueError("PersistencePolicy is required for real writes")

    # Dry run: validate + map, no DB writes (no ProcessingRun)
    if dry_run:
        return _dry_run_persist(bundle, workspace_id, op_key)

    pk = preflight_kwargs or {}

    # ── Phase 1: ProcessingRun (RUNNING) in independent session ──────────
    now = datetime.now(UTC)
    try:
        with repo_factory() as run_session:
            existing, existing_status = _lookup_by_operation_key(run_session, op_key, workspace_id)
            if existing and existing_status == "success":
                # R2-B07: SUCCESS → idempotent return (no re-run)
                return DraftTransaction(
                    records=(),
                    total_objects=0,
                    created_count=0,
                    reused_count=0,
                    processing_run_id=existing[0].payload.get("id", ""),
                    succeeded=True,
                )
            if existing and existing_status == "running":
                # R2-B07: RUNNING → conflict, do NOT report success
                raise RuntimeError(
                    f"ProcessingRun {existing[0].id} is still RUNNING — "
                    f"concurrent conflict"
                )
            # R2-B07: FAILED → allow controlled retry (fall through to create new run)

            run_obj = ProcessingRun(
                task_type="draft_persistence",
                processor=ProcessorInfo(module="draft_service", code_version="3.0"),
                run_status=RunStatus.RUNNING,
                started_at=now,
                workspace_id=workspace_id,
                input_object_ids=[op_key],
            )
            run_payload = run_obj.model_dump(mode="json")
            run_payload.setdefault("external_ids", {})[EXT_ID_OPERATION_KEY] = op_key
            run_record = ObjectRecord(
                id=run_obj.id,
                object_type=ObjectType.PROCESSING_RUN.value,
                schema_version=run_obj.schema_version,
                lifecycle_status=LifecycleStatus.ACTIVE.value,
                workspace_id=workspace_id,
                privacy_level="private",
                created_by=run_obj.created_by,
                created_at=run_obj.created_at,
                updated_at=run_obj.updated_at,
                version=1,
                payload=run_payload,
            )
            run_session.add(run_record)
            run_session.commit()
            processing_run_id = run_obj.id
    except Exception as exc:
        logger.error("Phase 1 (RUNNING run) failed: %s", exc)
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id="",
            succeeded=False,
            error_message=f"Failed to create ProcessingRun: {exc!s}"[:200],
        )

    # ── B03: Preflight ──────────────────────────────────────────────────
    try:
        validate_bundle_preflight(bundle, workspace_id=workspace_id, **pk)
    except Exception as exc:
        _finalize_failed_run(repo_factory, processing_run_id, workspace_id, op_key, exc)
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id=processing_run_id,
            succeeded=False,
            error_message=f"Preflight failed: {exc!s}"[:200],
        )

    # ── B05: Map candidates with strict validation ──────────────────────
    try:
        entities, data_points, claims, evidence_list, candidate_to_core = map_accepted_candidates(
            bundle.accepted_candidate_ids,
            bundle.candidates,
            existing_object_resolver=policy.existing_object_resolver if policy else None,
        )
    except Exception as exc:
        _finalize_failed_run(repo_factory, processing_run_id, workspace_id, op_key, exc)
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id=processing_run_id,
            succeeded=False,
            error_message=f"Mapper failed: {exc!s}"[:200],
        )

    # ── R3-04: Resolve core references (candidate ID → core object ID) ─
    evidence_list = _resolve_core_references(evidence_list, candidate_to_core)

    all_mapped: list[tuple[str, Any]] = []
    all_mapped.extend(("entity", e) for e in entities)
    all_mapped.extend(("data_point", dp) for dp in data_points)
    all_mapped.extend(("claim", c) for c in claims)
    all_mapped.extend(("evidence", ev) for ev in evidence_list)

    candidate_map = {getattr(c, "candidate_id", ""): c for c in bundle.candidates}
    records: list[DraftRecord] = []
    created = 0
    reused = 0



    # ── B04: pre-compute independence_group from source graph ───────────
    cu_to_group: dict[str, str] = {}
    try:
        with repo_factory() as graph_session:
            for c in bundle.candidates:
                suid = getattr(c, "source_unit_id", "")
                if not suid or suid in cu_to_group:
                    continue
                try:
                    cu_to_group[suid] = compute_independence_group(
                        graph_session, suid, workspace_id
                    )
                except SourceGraphError as sge:
                    _finalize_failed_run(
                        repo_factory, processing_run_id, workspace_id, op_key, sge
                    )
                    return DraftTransaction(
                        records=(),
                        total_objects=0,
                        created_count=0,
                        reused_count=0,
                        processing_run_id=processing_run_id,
                        succeeded=False,
                        error_message=f"SourceGraphError: {sge!s}"[:200],
                    )
    except Exception as exc:
        _finalize_failed_run(repo_factory, processing_run_id, workspace_id, op_key, exc)
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id=processing_run_id,
            succeeded=False,
            error_message=f"Source graph resolution failed: {exc!s}"[:200],
        )

    # ── Phase 2: Atomic business object write ───────────────────────────
    try:
        with repo_factory() as biz_session:
            for obj_type, obj in all_mapped:
                # B05: strict validation (R3-03: pass policy for independence_group gating)
                _validate_mapped_object(obj, obj_type, policy=policy)

                cid = getattr(obj, "source_ref", "").replace("candidate:", "")
                candidate = candidate_map.get(cid)
                if candidate is not None:
                    natural_key = compute_draft_natural_key(workspace_id, obj_type, candidate)
                else:
                    natural_key = hashlib.sha256(
                        f"{workspace_id}|{obj_type}|{cid}".encode()
                    ).hexdigest()

                if hasattr(obj, "workspace_id"):
                    obj.workspace_id = workspace_id

                # M01: unknown object type fail-closed
                obj_type_enum = _OBJ_TYPE_TO_ENUM.get(obj_type)
                if obj_type_enum is None:
                    raise ValueError(f"Unknown object_type: {obj_type} (M01)")

                # B06: Persistent natural-key lookup
                existing = _lookup_by_natural_key(
                    biz_session, obj_type_enum, natural_key, workspace_id
                )
                if existing:
                    existing_id = existing[0].payload.get("id", existing[0].id)
                    records.append(DraftRecord(
                        object_type=obj_type,
                        object_id=existing_id,
                        stable_identity_hash=natural_key,
                        action=DraftAction.REUSED,
                        candidate_id=cid,
                    ))
                    reused += 1
                else:
                    # R2-B08: Deterministic object ID from natural key (PK collision blocker)
                    deterministic_id = natural_key[:32]
                    obj.id = deterministic_id

                    obj_payload = obj.model_dump(mode="json")
                    # B04: inject independence_group for evidence
                    if obj_type == "evidence":
                        c_candidate = candidate_map.get(cid)
                        if c_candidate is not None:
                            ev_suid = getattr(c_candidate, "source_unit_id", "")
                            ev_group = cu_to_group.get(ev_suid, "")
                            if ev_group:
                                obj_payload["independence_group"] = ev_group
                    obj_payload.setdefault("external_ids", {})
                    obj_payload["external_ids"][EXT_ID_OPERATION_KEY] = op_key
                    obj_payload["external_ids"][EXT_ID_NATURAL_KEY] = natural_key
                    obj_payload["external_ids"][EXT_ID_ORIGIN_CANDIDATE] = f"candidate:{cid}"
                    obj_payload["external_ids"][EXT_ID_BUNDLE_SHA256] = bundle.bundle_sha256

                    rec = ObjectRecord(
                        id=obj.id,
                        object_type=obj_type_enum.value,
                        schema_version=obj.schema_version,
                        lifecycle_status=LifecycleStatus.ACTIVE.value,
                        workspace_id=workspace_id,
                        privacy_level="private",
                        created_by=obj.created_by,
                        created_at=obj.created_at,
                        updated_at=obj.updated_at,
                        version=1,
                        payload=obj_payload,
                    )
                    # R3-06: Catch IntegrityError for concurrent PK collisions (R2-B08 race)
                    try:
                        biz_session.add(rec)
                    except IntegrityError as ie:
                        err_str = str(ie).lower()
                        if "unique" in err_str:
                            logger.warning(
                                "IntegrityError (PK collision) for %s id=%s: %s",
                                obj_type, obj.id, ie,
                            )
                            biz_session.rollback()
                            continue
                        raise

                    records.append(DraftRecord(
                        object_type=obj_type,
                        object_id=obj.id,
                        stable_identity_hash=natural_key,
                        action=DraftAction.CREATED,
                        candidate_id=cid,
                    ))
                    created += 1

            biz_session.commit()

    except Exception as exc:
        _finalize_failed_run(repo_factory, processing_run_id, workspace_id, op_key, exc)
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id=processing_run_id,
            succeeded=False,
            error_message=str(exc)[:200],
        )

    # ── Phase 3: ProcessingRun (SUCCEEDED) ──────────────────────────────
    if not _finalize_success_run(
        repo_factory, processing_run_id, workspace_id, op_key, records
    ):
        # R2-B06: Phase 3 audit update failed → main flow must not report success
        _finalize_failed_run(
            repo_factory, processing_run_id, workspace_id, op_key,
            RuntimeError("Phase 3 ProcessingRun update failed — audit integrity breach")
        )
        return DraftTransaction(
            records=(),
            total_objects=0,
            created_count=0,
            reused_count=0,
            processing_run_id=processing_run_id,
            succeeded=False,
            error_message="Phase 3 audit update failed"[:200],
        )

    return DraftTransaction(
        records=tuple(records),
        total_objects=created + reused,
        created_count=created,
        reused_count=reused,
        processing_run_id=processing_run_id,
        succeeded=True,
    )


def _finalize_failed_run(
    repo_factory: sessionmaker,
    processing_run_id: str,
    workspace_id: str,
    op_key: str,
    exc: Exception,
) -> bool:
    """B02: Write FAILED ProcessingRun in independent session.

    Returns True if the audit record was successfully written.
    """
    try:
        with repo_factory() as fail_session:
            stmt = sql_select(ObjectRecord).where(ObjectRecord.id == processing_run_id)
            rec = fail_session.scalars(stmt).first()
            now = datetime.now(UTC)
            if rec is None:
                fail_payload = ProcessingRun(
                    id=processing_run_id,
                    task_type="draft_persistence",
                    processor=ProcessorInfo(module="draft_service", code_version="3.0"),
                    run_status=RunStatus.FAILED,
                    started_at=now,
                    finished_at=now,
                    workspace_id=workspace_id,
                    error_message=str(exc)[:500],
                ).model_dump(mode="json")
                fail_payload.setdefault("external_ids", {})[EXT_ID_OPERATION_KEY] = op_key
                fail_rec = ObjectRecord(
                    id=processing_run_id,
                    object_type=ObjectType.PROCESSING_RUN.value,
                    schema_version="v1.1",
                    lifecycle_status=LifecycleStatus.ACTIVE.value,
                    workspace_id=workspace_id,
                    privacy_level="private",
                    created_by="draft_service",
                    created_at=now,
                    updated_at=now,
                    version=1,
                    payload=fail_payload,
                )
                fail_session.add(fail_rec)
            else:
                # R2-B06: Use RunStatus.FAILED.value = "failed" (not "failure")
                rec.payload["run_status"] = RunStatus.FAILED.value
                rec.payload["error_message"] = str(exc)[:500]
                rec.payload["finished_at"] = now.isoformat()
                rec.updated_at = now
                flag_modified(rec, "payload")
            fail_session.commit()
            return True
    except Exception as e:
        logger.error("Failed to write FAILED ProcessingRun: %s", e)
        return False


def _finalize_success_run(
    repo_factory: sessionmaker,
    processing_run_id: str,
    workspace_id: str,
    op_key: str,
    records: list[DraftRecord],
) -> bool:
    """B02: Write SUCCEEDED ProcessingRun in independent session.

    Returns True if the audit record was successfully written.
    """
    try:
        with repo_factory() as success_session:
            stmt = sql_select(ObjectRecord).where(ObjectRecord.id == processing_run_id)
            rec = success_session.scalars(stmt).first()
            now = datetime.now(UTC)
            if rec is not None:
                rec.payload["run_status"] = RunStatus.SUCCESS.value
                rec.payload["finished_at"] = now.isoformat()
                rec.payload["output_object_ids"] = [r.object_id for r in records]
                rec.updated_at = now
                flag_modified(rec, "payload")
            else:
                run_obj = ProcessingRun(
                    id=processing_run_id,
                    task_type="draft_persistence",
                    processor=ProcessorInfo(module="draft_service", code_version="3.0"),
                    run_status=RunStatus.SUCCESS,
                    started_at=now,
                    finished_at=now,
                    workspace_id=workspace_id,
                    input_object_ids=[op_key],
                    output_object_ids=[r.object_id for r in records],
                )
                run_payload = run_obj.model_dump(mode="json")
                run_payload.setdefault("external_ids", {})[EXT_ID_OPERATION_KEY] = op_key
                run_rec = ObjectRecord(
                    id=processing_run_id,
                    object_type=ObjectType.PROCESSING_RUN.value,
                    schema_version=run_obj.schema_version,
                    lifecycle_status=LifecycleStatus.ACTIVE.value,
                    workspace_id=workspace_id,
                    privacy_level="private",
                    created_by=run_obj.created_by,
                    created_at=run_obj.created_at,
                    updated_at=run_obj.updated_at,
                    version=1,
                    payload=run_payload,
                )
                success_session.add(run_rec)
            success_session.commit()
            return True
    except Exception as e:
        logger.error("Failed to write SUCCEEDED ProcessingRun: %s", e)
        return False


# ── Backward-compat wrapper ──────────────────────────────────────────────────

def persist_drafts_with_separate_run(
    repo_factory: sessionmaker,
    repo: Any,
    bundle: Any,
    workspace_id: str,
    dry_run: bool = False,
    policy: PersistencePolicy | None = None,
) -> DraftTransaction:
    """Backward-compatible wrapper: delegates to persist_drafts."""
    return persist_drafts(repo_factory, bundle, workspace_id, dry_run=dry_run, policy=policy)
