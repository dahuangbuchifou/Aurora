"""Public exports for Aurora core domain objects."""

from .application import Feedback, OutputArtifact, ProcessingRun
from .atoms import Claim, DataPoint, Entity, Event, Evidence, Fact
from .cognition import Insight, PersonalOpinion
from .common import (
    AuroraModel,
    BaseObject,
    HumanReview,
    ProcessorInfo,
    Provenance,
    QualityAssessment,
    SourceLocator,
    TimeRange,
    ValidityWindow,
    new_id,
    utc_now,
)
from .document import ContentUnit, Document
from .enums import *
from .knowledge import KnowledgeObject, Relation, TimelineEntry
from .source import Source

AuroraObject = (
    Source
    | Document
    | ContentUnit
    | Entity
    | Event
    | DataPoint
    | Claim
    | Evidence
    | Fact
    | KnowledgeObject
    | Relation
    | TimelineEntry
    | Insight
    | PersonalOpinion
    | OutputArtifact
    | Feedback
    | ProcessingRun
)

__all__ = [
    "Source",
    "Document",
    "ContentUnit",
    "Entity",
    "Event",
    "DataPoint",
    "Claim",
    "Evidence",
    "Fact",
    "KnowledgeObject",
    "Relation",
    "TimelineEntry",
    "Insight",
    "PersonalOpinion",
    "OutputArtifact",
    "Feedback",
    "ProcessingRun",
    "AuroraObject",
    "AuroraModel",
    "BaseObject",
    "HumanReview",
    "ProcessorInfo",
    "Provenance",
    "QualityAssessment",
    "SourceLocator",
    "TimeRange",
    "ValidityWindow",
    "new_id",
    "utc_now",
]
