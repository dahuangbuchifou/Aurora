"""Public exports for Aurora core domain objects."""

from .application import Feedback, OutputArtifact, ProcessingRun
from .atoms import Claim, DataPoint, Entity, Event, Evidence, Fact
from .cognition import Insight, PersonalOpinion
from .common import (
    AuroraModel,
    BaseObject,
    DerivationLink,
    ExternalReference,
    HumanReview,
    LEGACY_SCHEMA_VERSION,
    MeasurementContext,
    ProcessorInfo,
    Provenance,
    QualityAssessment,
    SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
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
    "DerivationLink",
    "ExternalReference",
    "HumanReview",
    "MeasurementContext",
    "ProcessorInfo",
    "Provenance",
    "QualityAssessment",
    "SourceLocator",
    "TimeRange",
    "ValidityWindow",
    "LEGACY_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SUPPORTED_SCHEMA_VERSIONS",
    "new_id",
    "utc_now",
]
