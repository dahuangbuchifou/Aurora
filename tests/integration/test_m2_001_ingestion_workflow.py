import json
from pathlib import Path

import pytest

from aurora.core.models import ContentUnit, Document, ProcessingRun, Source
from aurora.core.models.enums import ObjectType, RunStatus, SourceType
from aurora.db.base import Base
from aurora.db.session import create_db_engine, create_session_factory
from aurora.ingestion import (
    DuplicateIngestionError,
    DuplicateStrategy,
    IngestionInputType,
    IngestionRequest,
)
from aurora.parser import MarkdownParser
from aurora.repository import ObjectRepository
from aurora.workflow import IngestionService


def _service(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'ingestion.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    return engine, factory, IngestionService(factory)


def _request(path: Path, **updates):
    values = {
        "path": path,
        "input_type": IngestionInputType.MARKDOWN,
        "source_name": "SMIC Official",
        "source_type": SourceType.OFFICIAL_WEBSITE,
        "source_key": "smic-official",
        "created_by": "qa",
    }
    values.update(updates)
    return IngestionRequest(**values)


def test_new_ingestion_and_reuse_are_idempotent(tmp_path: Path):
    path = tmp_path / "report.md"
    path.write_text("# Report\n\nParagraph", encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        first = service.ingest(_request(path))
        second = service.ingest(_request(path))
        assert first.reused is False
        assert second.reused is True
        assert second.document_id == first.document_id
        assert second.content_unit_ids == first.content_unit_ids
        assert second.processing_run_id != first.processing_run_id

        session = factory()
        repository = ObjectRepository(session)
        assert repository.count(object_type=ObjectType.SOURCE) == 1
        assert repository.count(object_type=ObjectType.DOCUMENT) == 1
        assert repository.count(object_type=ObjectType.CONTENT_UNIT) == 2
        assert repository.count(object_type=ObjectType.PROCESSING_RUN) == 2
        runs = repository.list(
            object_type=ObjectType.PROCESSING_RUN,
            workspace_id="default",
            limit=10,
        )
        assert all(isinstance(run, ProcessingRun) for run in runs)
        assert all(run.run_status == RunStatus.SUCCESS for run in runs)
        session.close()
    finally:
        engine.dispose()


def test_same_source_different_content_reuses_source_and_versions_document(tmp_path: Path):
    path = tmp_path / "news.md"
    path.write_text("# First\n\nA", encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        first = service.ingest(_request(path))
        path.write_text("# Second\n\nB", encoding="utf-8")
        second = service.ingest(_request(path))
        assert second.source_id == first.source_id
        assert second.document_id != first.document_id

        session = factory()
        repository = ObjectRepository(session)
        second_doc = repository.get_required(second.document_id)
        assert isinstance(second_doc, Document)
        assert second_doc.parent_document_id == first.document_id
        assert repository.count(object_type=ObjectType.SOURCE) == 1
        assert repository.count(object_type=ObjectType.DOCUMENT) == 2
        session.close()
    finally:
        engine.dispose()


def test_parser_version_change_creates_new_document_version(tmp_path: Path):
    class MarkdownParserV2(MarkdownParser):
        version = "2.0.0"

    path = tmp_path / "same.md"
    path.write_text("# Same\n\nA", encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        first = service.ingest(_request(path))
        v2_service = IngestionService(
            factory,
            parsers={IngestionInputType.MARKDOWN: MarkdownParserV2()},
        )
        second = v2_service.ingest(_request(path))
        assert second.document_id != first.document_id
        session = factory()
        second_doc = ObjectRepository(session).get_required(second.document_id)
        assert isinstance(second_doc, Document)
        assert second_doc.parent_document_id == first.document_id
        session.close()
    finally:
        engine.dispose()


def test_duplicate_strategies_reject_and_new_version(tmp_path: Path):
    path = tmp_path / "duplicate.md"
    path.write_text("# Duplicate", encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        first = service.ingest(_request(path))
        with pytest.raises(DuplicateIngestionError):
            service.ingest(
                _request(path, duplicate_strategy=DuplicateStrategy.REJECT)
            )
        forced = service.ingest(
            _request(path, duplicate_strategy=DuplicateStrategy.NEW_VERSION)
        )
        assert forced.document_id != first.document_id
        assert forced.reused is False

        session = factory()
        repository = ObjectRepository(session)
        runs = repository.list(
            object_type=ObjectType.PROCESSING_RUN,
            workspace_id="default",
            limit=20,
        )
        assert sorted(run.run_status.value for run in runs) == [
            "failed",
            "success",
            "success",
        ]
        session.close()
    finally:
        engine.dispose()


def test_dry_run_reads_database_but_writes_nothing(tmp_path: Path):
    path = tmp_path / "dry.md"
    path.write_text("# Dry\n\nContent", encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        result = service.ingest(_request(path, dry_run=True))
        assert result.dry_run is True
        assert result.reused is False
        session = factory()
        assert ObjectRepository(session).count(include_deleted=True) == 0
        session.close()
    finally:
        engine.dispose()


def test_structured_manifest_supplies_source_and_workspace(tmp_path: Path):
    path = tmp_path / "segments.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "workspace_id": "research",
                "source": {
                    "name": "Research Desk",
                    "source_type": "research_institution",
                    "canonical_key": "desk",
                },
                "document": {
                    "title": "Structured",
                    "document_type": "text",
                    "language": "zh-CN",
                },
                "segments": [
                    {
                        "sequence_no": 0,
                        "unit_type": "paragraph",
                        "text": "segment",
                        "locator": {"paragraph_no": 1},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    engine, factory, service = _service(tmp_path)
    try:
        result = service.ingest(
            IngestionRequest(
                path=path,
                input_type=IngestionInputType.STRUCTURED_SEGMENTS,
            )
        )
        session = factory()
        repository = ObjectRepository(session)
        source = repository.get_required(result.source_id)
        run = repository.get_required(result.processing_run_id)
        assert isinstance(source, Source)
        assert source.workspace_id == "research"
        assert isinstance(run, ProcessingRun)
        assert run.workspace_id == "research"
        session.close()
    finally:
        engine.dispose()


def test_same_content_different_paths_reuses_document_within_same_source(tmp_path: Path):
    first_path = tmp_path / "a.md"
    second_path = tmp_path / "b.md"
    content = "# Same\n\nIdentical content"
    first_path.write_text(content, encoding="utf-8")
    second_path.write_text(content, encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        first = service.ingest(_request(first_path))
        second = service.ingest(_request(second_path))
        assert second.reused is True
        assert second.document_id == first.document_id
        session = factory()
        repository = ObjectRepository(session)
        assert repository.count(object_type=ObjectType.DOCUMENT) == 1
        assert repository.count(object_type=ObjectType.PROCESSING_RUN) == 2
        session.close()
    finally:
        engine.dispose()


def test_dry_run_of_existing_document_reports_reuse_without_new_run(tmp_path: Path):
    path = tmp_path / "existing.md"
    path.write_text("# Existing\n\nContent", encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        first = service.ingest(_request(path))
        dry = service.ingest(_request(path, dry_run=True))
        assert dry.reused is True
        assert dry.document_id == first.document_id
        session = factory()
        repository = ObjectRepository(session)
        assert repository.count(object_type=ObjectType.PROCESSING_RUN) == 1
        session.close()
    finally:
        engine.dispose()


def test_source_identity_includes_source_type_and_workspace(tmp_path: Path):
    first_path = tmp_path / "official.md"
    second_path = tmp_path / "local.md"
    first_path.write_text("# Official", encoding="utf-8")
    second_path.write_text("# Local", encoding="utf-8")
    engine, factory, service = _service(tmp_path)
    try:
        official = service.ingest(_request(first_path, source_key="shared-key"))
        local = service.ingest(
            _request(
                second_path,
                source_key="shared-key",
                source_type=SourceType.LOCAL_FILE,
            )
        )
        other_workspace = service.ingest(
            _request(
                first_path,
                source_key="shared-key",
                workspace_id="other",
            )
        )
        assert len({official.source_id, local.source_id, other_workspace.source_id}) == 3
        session = factory()
        assert ObjectRepository(session).count(object_type=ObjectType.SOURCE) == 3
        session.close()
    finally:
        engine.dispose()
