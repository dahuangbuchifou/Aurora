"""Knowledge-level objects."""

from typing import Literal

from pydantic import Field, model_validator

from .common import BaseObject, TimeRange, ValidityWindow, new_id
from .enums import (
    KnowledgeStatus,
    KnowledgeType,
    ObjectType,
    RelationStatus,
)


class KnowledgeObject(BaseObject):
    id: str = Field(default_factory=lambda: new_id("knw"))
    object_type: Literal[ObjectType.KNOWLEDGE_OBJECT] = ObjectType.KNOWLEDGE_OBJECT
    knowledge_type: KnowledgeType
    title: str = Field(min_length=1, max_length=1000)
    topic_ids: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)
    fact_ids: list[str] = Field(default_factory=list)
    data_point_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    related_entity_ids: list[str] = Field(default_factory=list)
    validity: ValidityWindow
    knowledge_status: KnowledgeStatus = KnowledgeStatus.DRAFT

    @model_validator(mode="after")
    def validate_content_refs(self) -> "KnowledgeObject":
        refs = (
            self.fact_ids
            + self.data_point_ids
            + self.claim_ids
            + self.evidence_ids
            + self.related_entity_ids
        )
        if not refs:
            raise ValueError("knowledge object requires at least one referenced object")
        return self


class Relation(BaseObject):
    id: str = Field(default_factory=lambda: new_id("rel"))
    object_type: Literal[ObjectType.RELATION] = ObjectType.RELATION
    subject_id: str
    predicate: str = Field(min_length=1)
    object_id: str
    valid_time: TimeRange | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    relation_status: RelationStatus = RelationStatus.ASSERTED

    @model_validator(mode="after")
    def validate_relation(self) -> "Relation":
        if self.subject_id == self.object_id:
            raise ValueError("relation subject and object cannot be identical")
        if (
            self.relation_status != RelationStatus.HYPOTHESIZED
            and not self.evidence_ids
        ):
            raise ValueError("non-hypothesized relation requires evidence")
        return self


class TimelineEntry(BaseObject):
    id: str = Field(default_factory=lambda: new_id("tml"))
    object_type: Literal[ObjectType.TIMELINE_ENTRY] = ObjectType.TIMELINE_ENTRY
    target_object_id: str
    event_time: TimeRange
    title: str = Field(min_length=1)
    summary: str | None = None
    referenced_object_ids: list[str] = Field(default_factory=list)
    sequence_key: str | None = None
