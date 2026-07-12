import pytest

from aurora.core.models import LifecycleStatus, ObjectType, Source, SourceType
from aurora.repository import (
    ConcurrentUpdateError,
    DuplicateObjectError,
    ObjectNotFoundError,
    ObjectRepository,
)


def test_repository_not_found_and_duplicate_paths(db_session):
    repo = ObjectRepository(db_session)
    assert repo.get("src_missing") is None
    assert repo.get_raw_record("src_missing") is None
    with pytest.raises(ObjectNotFoundError):
        repo.get_required("src_missing")
    with pytest.raises(ObjectNotFoundError):
        repo.update(Source(id="src_missing", name="x", source_type=SourceType.BLOG))
    with pytest.raises(ObjectNotFoundError):
        repo.soft_delete("src_missing")
    with pytest.raises(ObjectNotFoundError):
        repo.restore("src_missing")
    with pytest.raises(ObjectNotFoundError):
        repo.record_version("src_missing")

    source = Source(id="src_dup", name="A", source_type=SourceType.BLOG)
    repo.create(source)
    db_session.commit()
    with pytest.raises(DuplicateObjectError):
        repo.create(source)


def test_repository_validation_and_filters(db_session):
    repo = ObjectRepository(db_session)
    a = Source(name="A", source_type=SourceType.BLOG, workspace_id="a")
    b = Source(name="B", source_type=SourceType.NEWS_MEDIA, workspace_id="b")
    repo.create(a)
    repo.create(b)
    db_session.commit()

    with pytest.raises(ValueError):
        repo.list(limit=0)
    with pytest.raises(ValueError):
        repo.list(offset=-1)
    with pytest.raises(ValueError):
        repo.list_by_schema_version("")
    with pytest.raises(ValueError):
        repo.list_by_schema_version("1.1", limit=10001)
    with pytest.raises(ValueError):
        repo.list_by_schema_version("1.1", offset=-1)

    assert repo.count(object_type=ObjectType.SOURCE) == 2
    assert [item.id for item in repo.list(workspace_id="a")] == [a.id]
    assert len(repo.list_by_schema_version("1.1", workspace_id="b")) == 1

    version = repo.record_version(a.id)
    with pytest.raises(ConcurrentUpdateError):
        repo.update(a, expected_version=version + 1)

    repo.soft_delete(a.id)
    db_session.commit()
    assert repo.get(a.id) is None
    assert repo.get(a.id, include_deleted=True) is not None
    assert repo.list(
        workspace_id="a",
        lifecycle_status=LifecycleStatus.DELETED,
        include_deleted=True,
    )
