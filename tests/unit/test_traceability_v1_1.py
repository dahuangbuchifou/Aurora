from aurora.core.models import (
    DerivationLink,
    DerivationRelationType,
    Document,
    DocumentType,
    OriginType,
    Provenance,
    Source,
    SourceType,
)
from aurora.repository import extract_reference_edges, validate_object_graph


def test_missing_processing_run_is_advisory_not_dangling():
    source = Source(
        id="src_001",
        name="官方来源",
        source_type=SourceType.OFFICIAL_WEBSITE,
        provenance=Provenance(processing_run_id="run_missing"),
    )
    report = validate_object_graph([source])
    assert report.ok is True
    assert report.dangling_references == []
    assert [edge.target_id for edge in report.advisory_references] == ["run_missing"]


def test_missing_strong_dependency_is_dangling():
    document = Document(
        id="doc_001",
        source_id="src_missing",
        document_type=DocumentType.WEB_ARTICLE,
        title="测试文档",
    )
    report = validate_object_graph([document])
    assert report.ok is False
    assert report.dangling_references[0].target_id == "src_missing"


def test_structured_derivation_link_is_dependency_and_satisfies_derived_origin():
    source = Source(
        id="src_001",
        name="原始来源",
        source_type=SourceType.OFFICIAL_WEBSITE,
    )
    document = Document(
        id="doc_001",
        source_id=source.id,
        document_type=DocumentType.WEB_ARTICLE,
        title="摘要",
        provenance=Provenance(
            origin_type=OriginType.DERIVED,
            derivation_links=[
                DerivationLink(
                    object_id=source.id,
                    relation_type=DerivationRelationType.SUMMARIZES,
                )
            ],
        ),
    )
    edges = extract_reference_edges(document)
    assert any(
        edge.target_id == source.id and "summarizes" in edge.field_name
        for edge in edges
    )
    report = validate_object_graph([source, document])
    assert report.derived_without_origins == []
    assert report.ok is True
