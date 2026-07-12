import json

import pytest

from aurora.core.models import Source, SourceType
from aurora.db.base import Base
from aurora.db.models import ObjectRecord
from aurora.db.payload_migration import migrate_payloads, restore_payloads
from aurora.db.session import create_db_engine, create_session_factory


def _database_with_legacy_source(tmp_path):
    db_path = tmp_path / "migration_payload.db"
    url = f"sqlite:///{db_path}"
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    session = factory()
    source = Source(
        id="src_legacy_payload",
        name="Legacy Payload",
        source_type=SourceType.OFFICIAL_WEBSITE,
    )
    payload = source.model_dump(mode="json")
    payload["schema_version"] = "1.0"
    payload["provenance"].pop("derivation_links", None)
    session.add(
        ObjectRecord(
            id=source.id,
            object_type="source",
            schema_version="1.0",
            lifecycle_status="active",
            workspace_id="default",
            privacy_level="internal",
            created_by="system",
            created_at=source.created_at,
            updated_at=source.updated_at,
            deleted_at=None,
            version=1,
            payload=payload,
        )
    )
    session.commit()
    session.close()
    engine.dispose()
    return url


def _raw_version(url):
    engine = create_db_engine(url)
    factory = create_session_factory(engine)
    session = factory()
    record = session.get(ObjectRecord, "src_legacy_payload")
    result = (record.schema_version, record.payload["schema_version"])
    session.close()
    engine.dispose()
    return result


def test_dry_run_validates_without_writing(tmp_path):
    url = _database_with_legacy_source(tmp_path)
    report = migrate_payloads(database_url=url, dry_run=True)
    assert report.selected_count == 1
    assert report.migrated_count == 1
    assert report.failed_count == 0
    assert _raw_version(url) == ("1.0", "1.0")


def test_real_migration_backup_and_restore(tmp_path):
    url = _database_with_legacy_source(tmp_path)
    backup_dir = tmp_path / "backup"
    report_path = tmp_path / "migration_report.json"
    report = migrate_payloads(
        database_url=url,
        dry_run=False,
        backup_dir=backup_dir,
        report_path=report_path,
    )
    assert report.migrated_count == 1
    assert report.failed_count == 0
    assert _raw_version(url) == ("1.1", "1.1")
    manifest = backup_dir / "manifest.json"
    assert manifest.exists()
    assert json.loads(report_path.read_text())["migrated_count"] == 1

    restore = restore_payloads(
        database_url=url,
        manifest_path=manifest,
        backup_current_dir=tmp_path / "pre_restore",
    )
    assert restore["restored_count"] == 1
    assert restore["failed_count"] == 0
    assert _raw_version(url) == ("1.0", "1.0")


def test_real_migration_requires_backup(tmp_path):
    url = _database_with_legacy_source(tmp_path)
    with pytest.raises(ValueError, match="backup_dir is required"):
        migrate_payloads(database_url=url, dry_run=False)


def test_restore_rejects_tampered_backup(tmp_path):
    url = _database_with_legacy_source(tmp_path)
    backup_dir = tmp_path / "backup"
    migrate_payloads(database_url=url, dry_run=False, backup_dir=backup_dir)
    data_file = backup_dir / "objects_v1_0.jsonl"
    data_file.write_text(data_file.read_text() + "tampered\n")
    with pytest.raises(ValueError, match="SHA-256"):
        restore_payloads(database_url=url, manifest_path=backup_dir / "manifest.json")


def test_migration_argument_validation_and_filters(tmp_path):
    url = _database_with_legacy_source(tmp_path)
    with pytest.raises(ValueError, match="batch_size"):
        migrate_payloads(database_url=url, batch_size=0)
    with pytest.raises(ValueError, match="must differ"):
        migrate_payloads(database_url=url, from_version="1.1", to_version="1.1")
    report = migrate_payloads(
        database_url=url,
        dry_run=True,
        object_type="claim",
        workspace_id="other",
    )
    assert report.selected_count == 0


def test_invalid_payload_is_reported_and_fail_fast_can_raise(tmp_path):
    url = _database_with_legacy_source(tmp_path)
    engine = create_db_engine(url)
    factory = create_session_factory(engine)
    session = factory()
    record = session.get(ObjectRecord, "src_legacy_payload")
    record.payload = {"schema_version": "1.0", "object_type": "not_real"}
    session.commit()
    session.close()
    engine.dispose()

    report = migrate_payloads(database_url=url, dry_run=True)
    assert report.failed_count == 1
    assert report.errors[0].object_id == "src_legacy_payload"
    with pytest.raises(ValueError):
        migrate_payloads(database_url=url, dry_run=True, fail_fast=True)


def test_restore_reports_missing_object(tmp_path):
    url = _database_with_legacy_source(tmp_path)
    backup_dir = tmp_path / "backup_missing"
    migrate_payloads(database_url=url, dry_run=False, backup_dir=backup_dir)

    engine = create_db_engine(url)
    factory = create_session_factory(engine)
    session = factory()
    record = session.get(ObjectRecord, "src_legacy_payload")
    session.delete(record)
    session.commit()
    session.close()
    engine.dispose()

    report_path = tmp_path / "restore_report.json"
    result = restore_payloads(
        database_url=url,
        manifest_path=backup_dir / "manifest.json",
        report_path=report_path,
    )
    assert result["restored_count"] == 0
    assert result["failed_count"] == 1
    assert report_path.exists()
