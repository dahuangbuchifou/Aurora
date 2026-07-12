"""Explicit Aurora JSON-payload migration and restore utilities.

Alembic owns table/index DDL. Domain payload upgrades are deliberately handled
here so every object can be backed up, validated, reported, and restored.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import make_url

from aurora.core.models.common import SCHEMA_VERSION
from aurora.core.schema_migrations import upgrade_payload
from aurora.core.schema_registry import parse_object
from aurora.db.models import ObjectRecord
from aurora.db.session import create_db_engine, create_session_factory


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _redact_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "<unparseable-database-url>"


@dataclass
class ObjectMigrationError:
    object_id: str
    error_type: str
    message: str


@dataclass
class PayloadMigrationReport:
    migration_id: str
    from_version: str
    to_version: str
    dry_run: bool
    started_at: str
    finished_at: str | None = None
    selected_count: int = 0
    migrated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    backup_manifest: str | None = None
    errors: list[ObjectMigrationError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["errors"] = [asdict(error) for error in self.errors]
        return payload


@dataclass(frozen=True)
class BackupManifest:
    migration_id: str
    created_at: str
    database_url_redacted: str
    from_version: str
    to_version: str
    object_count: int
    data_file: str
    sha256: str


def create_payload_backup(
    *,
    database_url: str,
    records: list[ObjectRecord],
    backup_dir: Path,
    migration_id: str,
    from_version: str,
    to_version: str,
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    version_tag = from_version.replace(".", "_")
    data_path = backup_dir / f"objects_v{version_tag}.jsonl"
    with data_path.open("w", encoding="utf-8") as handle:
        for record in records:
            item = {
                "id": record.id,
                "schema_version": record.schema_version,
                "record_version": record.version,
                "payload": record.payload,
            }
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")

    checksum = _sha256(data_path)
    checksum_path = backup_dir / "objects_v1_0.sha256"
    checksum_path.write_text(f"{checksum}  {data_path.name}\n", encoding="utf-8")

    manifest = BackupManifest(
        migration_id=migration_id,
        created_at=_utc_iso(),
        database_url_redacted=_redact_database_url(database_url),
        from_version=from_version,
        to_version=to_version,
        object_count=len(records),
        data_file=data_path.name,
        sha256=checksum,
    )
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def migrate_payloads(
    *,
    database_url: str,
    from_version: str = "1.0",
    to_version: str = SCHEMA_VERSION,
    dry_run: bool = True,
    backup_dir: Path | None = None,
    batch_size: int = 100,
    object_type: str | None = None,
    workspace_id: str | None = None,
    fail_fast: bool = False,
    report_path: Path | None = None,
) -> PayloadMigrationReport:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if from_version == to_version:
        raise ValueError("from_version and to_version must differ")
    if not dry_run and backup_dir is None:
        raise ValueError("backup_dir is required for a real migration")

    migration_id = f"payload_{from_version.replace('.', '_')}_to_{to_version.replace('.', '_')}"
    report = PayloadMigrationReport(
        migration_id=migration_id,
        from_version=from_version,
        to_version=to_version,
        dry_run=dry_run,
        started_at=_utc_iso(),
    )

    engine = create_db_engine(database_url)
    factory = create_session_factory(engine)
    session = factory()
    try:
        statement = select(ObjectRecord).where(
            ObjectRecord.schema_version == from_version
        )
        if object_type is not None:
            statement = statement.where(ObjectRecord.object_type == object_type)
        if workspace_id is not None:
            statement = statement.where(ObjectRecord.workspace_id == workspace_id)
        statement = statement.order_by(ObjectRecord.id)
        records = list(session.scalars(statement).all())
        report.selected_count = len(records)

        if not dry_run:
            assert backup_dir is not None
            manifest_path = create_payload_backup(
                database_url=database_url,
                records=records,
                backup_dir=backup_dir,
                migration_id=migration_id,
                from_version=from_version,
                to_version=to_version,
            )
            report.backup_manifest = str(manifest_path)

        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            for record in batch:
                try:
                    upgraded_payload = upgrade_payload(
                        record.payload,
                        target_version=to_version,
                    )
                    validated = parse_object(upgraded_payload)
                    canonical_payload = validated.model_dump(mode="json")
                    if dry_run:
                        report.migrated_count += 1
                        continue

                    with session.begin_nested():
                        current = session.get(ObjectRecord, record.id)
                        if current is None:
                            raise LookupError(
                                f"object disappeared during migration: {record.id}"
                            )
                        if current.schema_version != from_version:
                            report.skipped_count += 1
                            continue
                        current.schema_version = to_version
                        current.payload = canonical_payload
                        session.flush()
                    report.migrated_count += 1
                except Exception as exc:  # reported per object by design
                    report.failed_count += 1
                    report.errors.append(
                        ObjectMigrationError(
                            object_id=record.id,
                            error_type=type(exc).__name__,
                            message=str(exc),
                        )
                    )
                    if fail_fast:
                        session.rollback()
                        raise
            if not dry_run:
                session.commit()

        report.finished_at = _utc_iso()
    finally:
        session.close()
        engine.dispose()

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def restore_payloads(
    *,
    database_url: str,
    manifest_path: Path,
    backup_current_dir: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data_path = manifest_path.parent / manifest["data_file"]
    actual_sha = _sha256(data_path)
    if actual_sha != manifest["sha256"]:
        raise ValueError("backup SHA-256 mismatch")

    backup_items = [
        json.loads(line)
        for line in data_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    engine = create_db_engine(database_url)
    factory = create_session_factory(engine)
    session = factory()
    restored = 0
    errors: list[dict[str, str]] = []
    try:
        if backup_current_dir is not None:
            current_records: list[ObjectRecord] = []
            for item in backup_items:
                record = session.get(ObjectRecord, item["id"])
                if record is not None:
                    current_records.append(record)
            create_payload_backup(
                database_url=database_url,
                records=current_records,
                backup_dir=backup_current_dir,
                migration_id=f"pre_restore_{manifest['migration_id']}",
                from_version=manifest["to_version"],
                to_version=manifest["from_version"],
            )

        for item in backup_items:
            try:
                with session.begin_nested():
                    record = session.get(ObjectRecord, item["id"])
                    if record is None:
                        raise LookupError(f"object not found: {item['id']}")
                    record.schema_version = item["schema_version"]
                    record.version = item["record_version"]
                    record.payload = item["payload"]
                    session.flush()
                restored += 1
            except Exception as exc:
                errors.append(
                    {
                        "object_id": item["id"],
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    result = {
        "manifest": str(manifest_path),
        "restored_count": restored,
        "failed_count": len(errors),
        "errors": errors,
        "finished_at": _utc_iso(),
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result
