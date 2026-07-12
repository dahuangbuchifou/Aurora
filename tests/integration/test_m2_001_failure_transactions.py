from pathlib import Path

import pytest

from aurora.core.models import ContentUnit, ProcessingRun
from aurora.core.models.enums import ObjectType, RunStatus, SourceType
from aurora.db.base import Base
from aurora.db.session import create_db_engine, create_session_factory
from aurora.ingestion import (
    FileTooLargeError,
    IngestionInputType,
    IngestionRequest,
    PersistenceIngestionError,
)
from aurora.repository import ObjectRepository
from aurora.workflow import IngestionService


def _setup(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'failure.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    return engine, factory, IngestionService(factory)


def _request(path: Path, **kwargs):
    values = {
        "path": path,
        "input_type": IngestionInputType.MARKDOWN,
        "source_name": "Local",
        "source_type": SourceType.LOCAL_FILE,
    }
    values.update(kwargs)
    return IngestionRequest(**values)


def test_file_size_failure_persists_failed_run_only(tmp_path: Path):
    path = tmp_path / "large.md"
    path.write_text("12345", encoding="utf-8")
    engine, factory, service = _setup(tmp_path)
    try:
        with pytest.raises(FileTooLargeError):
            service.ingest(_request(path, max_bytes=4))
        session = factory()
        repository = ObjectRepository(session)
        assert repository.count(object_type=ObjectType.PROCESSING_RUN) == 1
        assert repository.count(object_type=ObjectType.DOCUMENT) == 0
        runs = repository.list(
            object_type=ObjectType.PROCESSING_RUN,
            workspace_id="default",
        )
        run = runs[0]
        assert isinstance(run, ProcessingRun)
        assert run.run_status == RunStatus.FAILED
        assert run.error_code == "INGEST_FILE_TOO_LARGE"
        session.close()
    finally:
        engine.dispose()


def test_document_and_units_rollback_as_one_business_transaction(
    tmp_path: Path,
    monkeypatch,
):
    path = tmp_path / "rollback.md"
    path.write_text("# Heading\n\nParagraph", encoding="utf-8")
    engine, factory, service = _setup(tmp_path)
    original_create = ObjectRepository.create

    def fail_on_unit(self, obj):
        if isinstance(obj, ContentUnit):
            raise RuntimeError("simulated unit failure")
        return original_create(self, obj)

    monkeypatch.setattr(ObjectRepository, "create", fail_on_unit)
    try:
        with pytest.raises(PersistenceIngestionError):
            service.ingest(_request(path))
        session = factory()
        repository = ObjectRepository(session)
        assert repository.count(object_type=ObjectType.SOURCE) == 1
        assert repository.count(object_type=ObjectType.DOCUMENT) == 0
        assert repository.count(object_type=ObjectType.CONTENT_UNIT) == 0
        runs = repository.list(
            object_type=ObjectType.PROCESSING_RUN,
            workspace_id="default",
        )
        assert len(runs) == 1
        assert runs[0].run_status == RunStatus.FAILED
        assert runs[0].error_code == "INGEST_PERSISTENCE_ERROR"
        session.close()
    finally:
        engine.dispose()
