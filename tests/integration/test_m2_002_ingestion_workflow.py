from pathlib import Path

import httpx

from aurora.collector.static_url import StaticUrlCollector
from aurora.core.models import ContentUnit, Document, ProcessingRun, Source
from aurora.core.models.enums import (
    ObjectType,
    ParseStatus,
    RunStatus,
    SourceType,
)
from aurora.db import Base, create_db_engine, create_session_factory
from aurora.ingestion.contracts import IngestionInputType, IngestionRequest
from aurora.repository import ObjectRepository
from aurora.workflow import IngestionService


FIXTURES = Path(__file__).parents[1] / "fixtures" / "m2_002"


def _service(tmp_path: Path, *, url_collector=None):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'm2_002.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    return engine, factory, IngestionService(factory, url_collector=url_collector)


def test_html_import_persists_parent_units_and_parse_audit(tmp_path: Path):
    engine, factory, service = _service(tmp_path)
    try:
        result = service.ingest(
            IngestionRequest(
                path=FIXTURES / "case_a_web.html",
                input_type=IngestionInputType.HTML,
                source_name="SMIC",
                source_type=SourceType.OFFICIAL_WEBSITE,
                source_homepage_url="https://www.smics.com/",
            )
        )
        assert result.parse_status == ParseStatus.PARSED
        assert result.raw_content_hash
        assert result.parser_config_hash
        session = factory()
        try:
            repository = ObjectRepository(session)
            document = repository.get_required(result.document_id)
            assert isinstance(document, Document)
            assert document.parse_status == ParseStatus.PARSED
            assert document.external_ids["raw_content_hash"] == result.raw_content_hash
            assert document.external_ids["parser_config_hash"] == result.parser_config_hash
            units = [
                item
                for item in repository.find_by_payload_field(
                    object_type=ObjectType.CONTENT_UNIT,
                    field_name="document_id",
                    value=document.id,
                )
                if isinstance(item, ContentUnit)
            ]
            table = next(unit for unit in units if unit.unit_type.value == "table")
            rows = [unit for unit in units if unit.unit_type.value == "table_row"]
            assert rows
            assert all(row.parent_unit_id == table.id for row in rows)
        finally:
            session.close()
    finally:
        engine.dispose()


def test_html_selector_change_creates_document_version(tmp_path: Path):
    path = tmp_path / "multi.html"
    path.write_text(
        "<html><body><main><p>Main</p></main><article><p>Article</p></article></body></html>",
        encoding="utf-8",
    )
    engine, factory, service = _service(tmp_path)
    try:
        common = dict(
            path=path,
            input_type=IngestionInputType.HTML,
            source_name="Example",
            source_type=SourceType.LOCAL_FILE,
        )
        first = service.ingest(IngestionRequest(**common, content_selector="main"))
        second = service.ingest(IngestionRequest(**common, content_selector="article"))
        assert first.document_id != second.document_id
        session = factory()
        try:
            second_doc = ObjectRepository(session).get_required(second.document_id)
            assert isinstance(second_doc, Document)
            assert second_doc.parent_document_id == first.document_id
        finally:
            session.close()
    finally:
        engine.dispose()


def test_pdf_page_range_participates_in_document_identity(tmp_path: Path):
    engine, factory, service = _service(tmp_path)
    try:
        common = dict(
            path=FIXTURES / "case_c_report.pdf",
            input_type=IngestionInputType.PDF,
            source_name="SMIC Annual Report",
            source_type=SourceType.LOCAL_FILE,
        )
        first = service.ingest(IngestionRequest(**common, page_selection="1"))
        second = service.ingest(IngestionRequest(**common, page_selection="2"))
        assert first.document_id != second.document_id
        assert first.parse_status == ParseStatus.PARTIALLY_PARSED
        assert second.parse_status == ParseStatus.PARTIALLY_PARSED
        session = factory()
        try:
            second_doc = ObjectRepository(session).get_required(second.document_id)
            assert isinstance(second_doc, Document)
            assert second_doc.parent_document_id == first.document_id
        finally:
            session.close()
    finally:
        engine.dispose()


def test_partial_transcript_sets_partial_run_and_document(tmp_path: Path):
    engine, factory, service = _service(tmp_path)
    try:
        result = service.ingest(
            IngestionRequest(
                path=FIXTURES / "case_b_video.srt",
                input_type=IngestionInputType.SRT,
                source_name="Video Channel",
                source_type=SourceType.VIDEO_CHANNEL,
            )
        )
        assert result.parse_status == ParseStatus.PARTIALLY_PARSED
        assert "TRANSCRIPT_OVERLAP" in result.warnings
        session = factory()
        try:
            repository = ObjectRepository(session)
            run = repository.get_required(result.processing_run_id)
            document = repository.get_required(result.document_id)
            assert isinstance(run, ProcessingRun)
            assert isinstance(document, Document)
            assert run.run_status == RunStatus.PARTIAL_SUCCESS
            assert run.quality_flags == ["TRANSCRIPT_OVERLAP"]
            assert document.parse_status == ParseStatus.PARTIALLY_PARSED
        finally:
            session.close()
    finally:
        engine.dispose()


def test_static_url_import_uses_origin_as_source_homepage(tmp_path: Path):
    html = b"<html><head><title>Article</title></head><body><article><p>Hello</p></article></body></html>"
    collector = StaticUrlCollector(
        resolver=lambda host, port: ["93.184.216.34"],
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=html,
            )
        ),
    )
    engine, factory, service = _service(tmp_path, url_collector=collector)
    try:
        result = service.ingest(
            IngestionRequest(
                url="https://example.com/research/article",
                input_type=IngestionInputType.URL,
                source_name="Example Research",
                source_type=SourceType.RESEARCH_INSTITUTION,
            )
        )
        session = factory()
        try:
            source = ObjectRepository(session).get_required(result.source_id)
            assert isinstance(source, Source)
            assert str(source.homepage_url) == "https://example.com/"
        finally:
            session.close()
    finally:
        engine.dispose()


def test_url_dry_run_does_not_write_database(tmp_path: Path):
    collector = StaticUrlCollector(
        resolver=lambda host, port: ["93.184.216.34"],
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><body><article><p>Dry</p></article></body></html>",
            )
        ),
    )
    engine, factory, service = _service(tmp_path, url_collector=collector)
    try:
        result = service.ingest(
            IngestionRequest(
                url="https://example.com/dry",
                input_type=IngestionInputType.URL,
                source_name="Example",
                source_type=SourceType.OFFICIAL_WEBSITE,
                dry_run=True,
            )
        )
        assert result.dry_run is True
        session = factory()
        try:
            assert ObjectRepository(session).count(include_deleted=True) == 0
        finally:
            session.close()
    finally:
        engine.dispose()
