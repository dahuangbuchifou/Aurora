"""Insight and personal-opinion objects."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from .common import BaseObject, ValidityWindow, new_id
from .enums import InsightStatus, ObjectType, OpinionStatus, QualityLevel


class Insight(BaseObject):
    id: str = Field(default_factory=lambda: new_id("ins"))
    object_type: Literal[ObjectType.INSIGHT] = ObjectType.INSIGHT
    title: str = Field(min_length=1, max_length=1000)
    statement: str = Field(min_length=1)
    supporting_object_ids: list[str] = Field(min_length=1)
    counter_evidence_ids: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(min_length=1)
    alternative_explanations: list[str] = Field(default_factory=list)
    confidence_level: QualityLevel = QualityLevel.MEDIUM
    validity: ValidityWindow
    insight_status: InsightStatus = InsightStatus.DRAFT


class PersonalOpinion(BaseObject):
    id: str = Field(default_factory=lambda: new_id("opn"))
    object_type: Literal[ObjectType.PERSONAL_OPINION] = ObjectType.PERSONAL_OPINION
    title: str = Field(min_length=1, max_length=1000)
    statement: str = Field(min_length=1)
    topic_ids: list[str] = Field(default_factory=list)
    supporting_ids: list[str] = Field(default_factory=list)
    counter_evidence_ids: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    unknown_variables: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)
    confidence_level: QualityLevel = QualityLevel.MEDIUM
    opinion_status: OpinionStatus = OpinionStatus.DRAFT
    confirmed_by_user: bool = False
    confirmed_at: datetime | None = None
    as_of_date: date
    review_due_at: date | datetime | None = None
    version_no: int = Field(default=1, ge=1)
    previous_version_id: str | None = None
    revision_reason: str | None = None

    @model_validator(mode="after")
    def validate_activation(self) -> "PersonalOpinion":
        if self.confirmed_by_user and self.confirmed_at is None:
            raise ValueError("confirmed_at is required after user confirmation")
        if self.opinion_status == OpinionStatus.ACTIVE:
            missing: list[str] = []
            if not self.confirmed_by_user:
                missing.append("confirmed_by_user")
            if not self.supporting_ids:
                missing.append("supporting_ids")
            if not self.key_assumptions:
                missing.append("key_assumptions")
            if not self.invalidation_conditions:
                missing.append("invalidation_conditions")
            if self.review_due_at is None:
                missing.append("review_due_at")
            if missing:
                raise ValueError(
                    "active opinion missing required fields: " + ", ".join(missing)
                )
        return self
