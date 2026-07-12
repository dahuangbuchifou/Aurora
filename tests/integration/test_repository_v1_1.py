from copy import deepcopy

from aurora.core.models import Source, SourceType
from aurora.db.models import ObjectRecord
from aurora.repository import ObjectRepository


def _legacy_record() -> ObjectRecord:
    current = Source(
        id="src_legacy",
        name="Legacy Source",
        source_type=SourceType.OFFICIAL_WEBSITE,
    )
    payload = current.model_dump(mode="json")
    payload["schema_version"] = "1.0"
    payload["provenance"].pop("derivation_links", None)
    return ObjectRecord(
        id=current.id,
        object_type=current.object_type.value,
        schema_version="1.0",
        lifecycle_status=current.status.value,
        workspace_id=current.workspace_id,
        privacy_level=current.privacy_level.value,
        created_by=current.created_by,
        created_at=current.created_at,
        updated_at=current.updated_at,
        deleted_at=None,
        version=1,
        payload=payload,
    )


def test_repository_reads_mixed_versions_without_auto_writeback(db_session):
    legacy = _legacy_record()
    db_session.add(legacy)
    current = Source(name="Current Source", source_type=SourceType.NEWS_MEDIA)
    repo = ObjectRepository(db_session)
    repo.create(current)
    db_session.commit()

    loaded_legacy = repo.get_required("src_legacy")
    assert loaded_legacy.schema_version == "1.1"
    raw_legacy = repo.get_raw_record("src_legacy")
    assert raw_legacy is not None
    assert raw_legacy.schema_version == "1.0"
    assert raw_legacy.payload["schema_version"] == "1.0"

    objects = repo.list(workspace_id=None, limit=1000)
    assert {obj.schema_version for obj in objects} == {"1.1"}
    assert len(repo.list_by_schema_version("1.0")) == 1
    assert len(repo.list_by_schema_version("1.1")) == 1


def test_raw_record_is_a_defensive_copy(db_session):
    record = _legacy_record()
    db_session.add(record)
    db_session.commit()
    repo = ObjectRepository(db_session)
    snapshot = repo.get_raw_record(record.id)
    assert snapshot is not None
    snapshot.payload["name"] = "mutated outside repository"
    assert db_session.get(ObjectRecord, record.id).payload["name"] == "Legacy Source"


def test_updating_legacy_object_writes_v1_1(db_session):
    db_session.add(_legacy_record())
    db_session.commit()
    repo = ObjectRepository(db_session)
    loaded = repo.get_required("src_legacy")
    updated = loaded.model_copy(update={"name": "Updated Legacy Source"})
    repo.update(updated)
    db_session.commit()
    raw = repo.get_raw_record("src_legacy")
    assert raw is not None
    assert raw.schema_version == "1.1"
    assert raw.payload["schema_version"] == "1.1"
