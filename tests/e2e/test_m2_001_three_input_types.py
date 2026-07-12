from pathlib import Path

from aurora.core.models import ContentUnit, Document, ProcessingRun, Source
from aurora.core.models.enums import ObjectType, SourceType
from aurora.db.base import Base
from aurora.db.session import create_db_engine, create_session_factory
from aurora.ingestion import IngestionInputType, IngestionRequest
from aurora.repository import ObjectRepository
from aurora.workflow import IngestionService


def test_three_m1_002_materials_enter_the_same_offline_object_chain(tmp_path: Path):
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "m2_001"
    engine = create_db_engine(f"sqlite:///{tmp_path / 'm2_001_e2e.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    service = IngestionService(factory)
    try:
        case_a = service.ingest(
            IngestionRequest(
                path=fixture_root / "case_a_web.md",
                input_type=IngestionInputType.MARKDOWN,
                source_name="中芯国际官网",
                source_type=SourceType.OFFICIAL_WEBSITE,
                source_key="smic-official",
                title="中芯国际2025年报PR稿测试材料",
            )
        )
        case_b = service.ingest(
            IngestionRequest(
                path=fixture_root / "case_b_video.txt",
                input_type=IngestionInputType.TEXT,
                source_name="半导体观察日记",
                source_type=SourceType.VIDEO_CHANNEL,
                source_key="semiconductor-observation-diary",
                title="Case B 视频人工转写",
            )
        )
        case_c = service.ingest(
            IngestionRequest(
                path=fixture_root / "case_c_pdf_segments.json",
                input_type=IngestionInputType.STRUCTURED_SEGMENTS,
            )
        )

        assert case_a.content_unit_count == 5
        assert case_b.content_unit_count == 4
        assert case_c.content_unit_count == 5

        session = factory()
        repository = ObjectRepository(session)
        assert repository.count(object_type=ObjectType.SOURCE) == 3
        assert repository.count(object_type=ObjectType.DOCUMENT) == 3
        assert repository.count(object_type=ObjectType.CONTENT_UNIT) == 14
        assert repository.count(object_type=ObjectType.PROCESSING_RUN) == 3

        for result in (case_a, case_b, case_c):
            source = repository.get_required(result.source_id)
            document = repository.get_required(result.document_id)
            run = repository.get_required(result.processing_run_id)
            units = repository.find_by_payload_field(
                object_type=ObjectType.CONTENT_UNIT,
                field_name="document_id",
                value=result.document_id,
                workspace_id="default",
            )
            assert isinstance(source, Source)
            assert isinstance(document, Document)
            assert isinstance(run, ProcessingRun)
            assert all(isinstance(unit, ContentUnit) for unit in units)
            assert document.source_id == source.id
            assert run.output_object_ids[0] == source.id
            assert all(unit.document_id == document.id for unit in units)
            assert all(unit.provenance.processing_run_id == run.id for unit in units)
        session.close()
    finally:
        engine.dispose()
