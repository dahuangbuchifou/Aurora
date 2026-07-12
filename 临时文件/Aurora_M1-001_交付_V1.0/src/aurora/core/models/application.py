"""Application, feedback and processing-audit objects."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from .common import BaseObject, ProcessorInfo, new_id, utc_now
from .enums import (
    FeedbackAction,
    FeedbackEffect,
    FeedbackType,
    ObjectType,
    OutputReviewStatus,
    OutputType,
    RunStatus,
)


class OutputArtifact(BaseObject):
    id: str = Field(default_factory=lambda: new_id("out"))
    object_type: Literal[ObjectType.OUTPUT_ARTIFACT] = ObjectType.OUTPUT_ARTIFACT
    output_type: OutputType
    title: str = Field(min_length=1, max_length=1000)
    purpose: str = Field(min_length=1)
    audience: str = "user"
    content_uri: str | None = None
    content: str | None = None
    knowledge_refs: list[str] = Field(default_factory=list)
    insight_refs: list[str] = Field(default_factory=list)
    opinion_refs: list[str] = Field(default_factory=list)
    as_of_date: date
    review_status: OutputReviewStatus = OutputReviewStatus.NOT_REVIEWED

    @model_validator(mode="after")
    def validate_output(self) -> "OutputArtifact":
        if not self.content_uri and not self.content:
            raise ValueError("output requires content_uri or inline content")
        if not (self.knowledge_refs or self.insight_refs or self.opinion_refs):
            raise ValueError("output requires at least one knowledge reference")
        return self


class Feedback(BaseObject):
    id: str = Field(default_factory=lambda: new_id("fbk"))
    object_type: Literal[ObjectType.FEEDBACK] = ObjectType.FEEDBACK
    feedback_type: FeedbackType
    target_object_id: str
    content: str = Field(min_length=1)
    effect: FeedbackEffect
    recommended_action: FeedbackAction = FeedbackAction.REVIEW_REQUIRED


class ProcessingRun(BaseObject):
    id: str = Field(default_factory=lambda: new_id("run"))
    object_type: Literal[ObjectType.PROCESSING_RUN] = ObjectType.PROCESSING_RUN
    task_type: str = Field(min_length=1)
    input_object_ids: list[str] = Field(default_factory=list)
    output_object_ids: list[str] = Field(default_factory=list)
    processor: ProcessorInfo
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    run_status: RunStatus = RunStatus.PENDING
    quality_flags: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_run(self) -> "ProcessingRun":
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.run_status in {
            RunStatus.SUCCESS,
            RunStatus.PARTIAL_SUCCESS,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        } and self.finished_at is None:
            raise ValueError("terminal processing run requires finished_at")
        if self.run_status == RunStatus.FAILED and not self.error_message:
            raise ValueError("failed processing run requires error_message")
        return self
