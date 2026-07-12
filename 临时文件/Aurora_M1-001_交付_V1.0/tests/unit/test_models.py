from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from aurora.core.models import (
    Claim,
    ClaimType,
    ContentUnit,
    ContentUnitType,
    Evidence,
    EvidenceRole,
    EvidenceType,
    Fact,
    Insight,
    KnowledgeObject,
    KnowledgeType,
    ObjectType,
    OpinionStatus,
    PersonalOpinion,
    Provenance,
    Source,
    SourceLocator,
    SourceType,
    TimeRange,
    ValidityWindow,
)
from aurora.core.models.enums import OriginType
from aurora.core.schema_registry import MODEL_REGISTRY, parse_object


def test_all_seventeen_object_types_are_registered():
    assert len(MODEL_REGISTRY) == 17
    assert set(MODEL_REGISTRY) == set(ObjectType)


def test_prediction_requires_time_horizon():
    with pytest.raises(ValidationError):
        Claim(
            claim_type=ClaimType.PREDICTION,
            statement="未来三年行业需求将增长。",
            asserted_by="ent_expert",
            source_ref="cu_001",
        )


def test_fact_requires_evidence():
    with pytest.raises(ValidationError):
        Fact(
            statement="公司发布年度报告。",
            valid_time=TimeRange(start=date(2026, 1, 1)),
            evidence_ids=[],
        )


def test_active_opinion_requires_user_confirmation_and_review_fields():
    with pytest.raises(ValidationError):
        PersonalOpinion(
            title="半导体行业观点",
            statement="长期看好，短期审慎。",
            as_of_date=date(2026, 7, 11),
            opinion_status=OpinionStatus.ACTIVE,
        )


def test_valid_active_opinion():
    now = datetime.now(UTC)
    opinion = PersonalOpinion(
        title="半导体行业观点",
        statement="长期看好，短期关注库存周期。",
        as_of_date=date(2026, 7, 11),
        opinion_status=OpinionStatus.ACTIVE,
        confirmed_by_user=True,
        confirmed_at=now,
        supporting_ids=["ins_001"],
        key_assumptions=["需求逐步修复"],
        invalidation_conditions=["库存连续两个季度恶化"],
        review_due_at=now + timedelta(days=90),
    )
    assert opinion.confirmed_by_user is True


def test_content_unit_requires_locator():
    unit = ContentUnit(
        document_id="doc_001",
        unit_type=ContentUnitType.PARAGRAPH,
        sequence_no=1,
        text="正文段落。",
        locator=SourceLocator(paragraph_no=1),
    )
    assert unit.locator.paragraph_no == 1


def test_derived_provenance_requires_origin():
    with pytest.raises(ValidationError):
        Provenance(origin_type=OriginType.DERIVED)


def test_registry_roundtrip():
    source = Source(name="交易所公告", source_type=SourceType.COMPANY_ANNOUNCEMENT)
    payload = source.model_dump(mode="json")
    restored = parse_object(payload)
    assert isinstance(restored, Source)
    assert restored.id == source.id


def test_knowledge_and_insight_minimum_references():
    knowledge = KnowledgeObject(
        knowledge_type=KnowledgeType.INDUSTRY_CARD,
        title="半导体产业知识卡",
        summary="行业受库存周期与资本开支影响。",
        claim_ids=["clm_001"],
        validity=ValidityWindow(as_of_date=date(2026, 7, 11)),
    )
    insight = Insight(
        title="行业周期可能进入修复阶段",
        statement="多项数据共同指向库存压力缓解。",
        supporting_object_ids=[knowledge.id],
        reasoning_steps=["库存同比改善", "订单边际恢复"],
        validity=ValidityWindow(as_of_date=date(2026, 7, 11)),
    )
    assert insight.supporting_object_ids == [knowledge.id]
