"""Extraction candidate DTOs — lightweight representations for the extraction pipeline.

V2 additions: quote_match_mode on quote-bearing candidates, confidence field,
supporting_quote for FactCandidate.

These are NOT the core V1.1 knowledge objects. They are intermediate
representations used during extraction before human review and Fact promotion.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aurora.core.models.common import AuroraModel


def _new_candidate_id(prefix: str) -> str:
    return f"{prefix}_{uuid4()}"


class EntityCandidate(AuroraModel):
    """Extracted entity candidate."""

    candidate_id: str = Field(default_factory=lambda: _new_candidate_id("ent_cand"))
    id: str = ""
    entity_type: str
    canonical_name: str
    confidence: float = 0.0


class DataPointCandidate(AuroraModel):
    """Extracted data point candidate."""

    candidate_id: str = Field(default_factory=lambda: _new_candidate_id("dp_cand"))
    id: str = ""
    metric: str
    value: float
    unit: str
    entity_id: str
    period: str
    measurement_context: dict[str, Any]
    source_quote: str
    quote_locator_hint: str = ""
    quote_match_mode: str = "literal"
    source_unit_id: str = ""
    note: str = ""
    confidence: float = 0.0
    supporting_quote: str = ""


class ClaimCandidate(AuroraModel):
    """Extracted claim candidate."""

    candidate_id: str = Field(default_factory=lambda: _new_candidate_id("cl_cand"))
    id: str = ""
    statement: str
    claim_type: str
    claim_dimension: str
    claimant_id: str | None = None
    claimant_name: str = ""
    asserted_by: str = ""
    time_horizon: dict[str, Any] | None = None
    promotable_to_fact: bool = False
    source_quote: str
    quote_locator_hint: str = ""
    quote_match_mode: str = "literal"
    source_unit_id: str = ""
    note: str = ""
    confidence: float = 0.0
    supporting_quote: str = ""


class EvidenceCandidate(AuroraModel):
    """Extracted evidence candidate."""

    candidate_id: str = Field(default_factory=lambda: _new_candidate_id("ev_cand"))
    id: str = ""
    evidence_type: str
    evidence_role: str
    target_object_id: str
    independence_group: str = ""
    source_quote: str
    quote_match_mode: str = "literal"
    source_unit_id: str = ""
    note: str = ""
    confidence: float = 0.0
    supporting_quote: str = ""


class FactCandidate(AuroraModel):
    """Fact promotion candidate."""

    candidate_id: str = Field(default_factory=lambda: _new_candidate_id("fc_cand"))
    id: str = ""
    target_data_point_id: str | None = None
    target_claim_id: str | None = None
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    statement: str
    valid_time: dict[str, Any] | None = None
    confidence_rationale: str | None = None
    promotable: bool = False
    rejection_reason: str = ""
    source_quote: str = ""
    quote_match_mode: str = "literal"
    source_unit_id: str = ""
    confidence: float = 0.0
    supporting_quote: str = ""


Candidate = (
    EntityCandidate
    | DataPointCandidate
    | ClaimCandidate
    | EvidenceCandidate
    | FactCandidate
)
