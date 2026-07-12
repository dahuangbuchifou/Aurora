from pathlib import Path

from aurora.core.models import ContentUnit, Document, ProcessingRun, Source
from aurora.core.models.enums import ObjectType, SourceType
from aurora.db import Base, create_db_engine, create_session_factory
from aurora.ingestion.contracts import IngestionInputType, IngestionRequest
from aurora.repository import ObjectRepository
from aurora.workflow import IngestionService


FIXTURES = Path(__file__).parents[1] / "fixtures" / "m2_002"


def test_web_pdf_and_transcript_enter_traceable_content_chain(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'e2e.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    service = IngestionService(factory)
    requests = [
        IngestionRequest(
            path=FIXTURES / "case_a_web.html",
            input_type=IngestionInputType.HTML,
            source_name="SMIC Website",
            source_type=SourceType.OFFICIAL_WEBSITE,
            source_homepage_url="https://www.smics.com/",
        ),
        IngestionRequest(
            path=FIXTURES / "case_b_video.vtt",
            input_type=IngestionInputType.VTT,
            source_name="Semiconductor Video",
            source_type=SourceType.VIDEO_CHANNEL,
        ),
        IngestionRequest(
            path=FIXTURES / "case_c_report.pdf",
            input_type=IngestionInputType.PDF,
            source_name="SMIC Annual Report",
            source_type=SourceType.COMPANY_ANNOUNCEMENT,
            page_selection="1-2",
        ),
    ]
    try:
        results = [service.ingest(request) for request in requests]
        assert len({result.source_id for result in results}) == 3
        assert all(result.content_unit_count > 0 for result in results)
        session = factory()
        try:
            repository = ObjectRepository(session)
            for result in results:
                source = repository.get_required(result.source_id)
                document = repository.get_required(result.document_id)
                run = repository.get_required(result.processing_run_id)
                assert isinstance(source, Source)
                assert isinstance(document, Document)
                assert isinstance(run, ProcessingRun)
                assert document.source_id == source.id
                units = repository.find_by_payload_field(
                    object_type=ObjectType.CONTENT_UNIT,
                    field_name="document_id",
                    value=document.id,
                )
                assert len(units) == result.content_unit_count
                assert all(isinstance(unit, ContentUnit) for unit in units)
                assert all(unit.provenance.processing_run_id == run.id for unit in units)
        finally:
            session.close()
    finally:
        engine.dispose()
