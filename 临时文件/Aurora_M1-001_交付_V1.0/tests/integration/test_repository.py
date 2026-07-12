from aurora.core.models import Source, SourceType
from aurora.core.models.enums import ObjectType
from aurora.repository import ConcurrentUpdateError, ObjectRepository


def test_repository_crud_and_soft_delete(db_session):
    repository = ObjectRepository(db_session)
    source = Source(name="公司公告", source_type=SourceType.COMPANY_ANNOUNCEMENT)

    repository.create(source)
    db_session.commit()

    loaded = repository.get_required(source.id)
    assert loaded.id == source.id
    assert repository.count(object_type=ObjectType.SOURCE) == 1

    version = repository.record_version(source.id)
    updated = source.model_copy(update={"name": "交易所公司公告"})
    repository.update(updated, expected_version=version)
    db_session.commit()

    assert repository.get_required(source.id).name == "交易所公司公告"

    deleted = repository.soft_delete(source.id)
    db_session.commit()
    assert deleted.status.value == "deleted"
    assert repository.get(source.id) is None
    assert repository.get(source.id, include_deleted=True) is not None

    restored = repository.restore(source.id)
    db_session.commit()
    assert restored.status.value == "active"
    assert repository.get(source.id) is not None


def test_repository_optimistic_version_check(db_session):
    repository = ObjectRepository(db_session)
    source = Source(name="研究机构", source_type=SourceType.RESEARCH_INSTITUTION)
    repository.create(source)
    db_session.commit()

    updated = source.model_copy(update={"name": "专业研究机构"})
    try:
        repository.update(updated, expected_version=999)
    except ConcurrentUpdateError:
        pass
    else:
        raise AssertionError("expected ConcurrentUpdateError")
