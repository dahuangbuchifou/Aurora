"""Atomic cognition objects: entities, events, data, claims, evidence and facts."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .common import BaseObject, MeasurementContext, TimeRange, new_id
from .enums import (
    CalculationMethod,
    ClaimDimension,
    ClaimType,
    EntityType,
    EpistemicStatus,
    EventStatus,
    EvidenceDirectness,
    EvidenceRole,
    EvidenceStrength,
    EvidenceType,
    ObjectType,
    SourceQualityTier,
    VerificationStatus,
)


class Entity(BaseObject):
    id: str = Field(default_factory=lambda: new_id("ent"))
    object_type: Literal[ObjectType.ENTITY] = ObjectType.ENTITY
    entity_type: EntityType
    canonical_name: str = Field(min_length=1, max_length=500)
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, object] = Field(default_factory=dict)
    possible_same_as: list[str] = Field(default_factory=list)


class Event(BaseObject):
    id: str = Field(default_factory=lambda: new_id("evt"))
    object_type: Literal[ObjectType.EVENT] = ObjectType.EVENT
    event_type: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=1000)
    event_time: TimeRange
    entity_ids: list[str] = Field(min_length=1)
    location: str | None = None
    description: str | None = None
    event_status: EventStatus = EventStatus.REPORTED


class DataPoint(BaseObject):
    id: str = Field(default_factory=lambda: new_id("dat"))
    object_type: Literal[ObjectType.DATA_POINT] = ObjectType.DATA_POINT
    metric: str = Field(min_length=1)
    value: int | float
    unit: str = Field(min_length=1)
    measurement_context: MeasurementContext = Field(
        default_factory=MeasurementContext
    )
    entity_id: str
    period: TimeRange
    reported_at: datetime | None = None
    calculation_method: CalculationMethod = CalculationMethod.REPORTED
    calculation_expression: str | None = None
    source_ref: str
    audited: bool | None = None


class Claim(BaseObject):
    id: str = Field(default_factory=lambda: new_id("clm"))
    object_type: Literal[ObjectType.CLAIM] = ObjectType.CLAIM
    claim_type: ClaimType
    claim_dimension: ClaimDimension = ClaimDimension.GENERAL
    statement: str = Field(min_length=1)
    subject_entity_ids: list[str] = Field(default_factory=list)
    asserted_by: str = Field(min_length=1)
    asserted_at: datetime | None = None
    time_horizon: TimeRange | None = None
    conditions: list[str] = Field(default_factory=list)
    source_ref: str
    direct_quote: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.ASSERTED

    @model_validator(mode="after")
    def validate_prediction(self) -> "Claim":
        if self.claim_type == ClaimType.PREDICTION and self.time_horizon is None:
            raise ValueError("prediction claim requires time_horizon")
        return self


class Evidence(BaseObject):
    id: str = Field(default_factory=lambda: new_id("evi"))
    object_type: Literal[ObjectType.EVIDENCE] = ObjectType.EVIDENCE
    evidence_role: EvidenceRole
    evidence_type: EvidenceType
    target_object_id: str
    source_ref: str
    summary: str = Field(min_length=1)
    independence_group: str = Field(min_length=1)
    directness: EvidenceDirectness = EvidenceDirectness.UNKNOWN
    source_quality_tier: SourceQualityTier = SourceQualityTier.S5
    evidence_strength: EvidenceStrength = EvidenceStrength.E1


class Fact(BaseObject):
    id: str = Field(default_factory=lambda: new_id("fac"))
    object_type: Literal[ObjectType.FACT] = ObjectType.FACT
    statement: str = Field(min_length=1)
    subject_entity_ids: list[str] = Field(default_factory=list)
    valid_time: TimeRange
    evidence_ids: list[str] = Field(min_length=1)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    reviewed_by: str | None = None
