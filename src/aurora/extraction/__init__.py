"""Aurora Extraction Engine — ContentUnit → Candidates vertical slice."""

from .candidates import Candidate, ClaimCandidate, DataPointCandidate, EntityCandidate, EvidenceCandidate, FactCandidate
from .context_window import ContentUnitRef, ContextWindow
from .envelope import ExtractionEnvelope
from .quote_gate import QuoteGate, QuoteGateFailure
from .review_bundle import ReviewBundle
from .review_decision import ReviewDecisionDecision, ReviewDecision

__all__ = [
    "Candidate",
    "ClaimCandidate",
    "DataPointCandidate",
    "EntityCandidate",
    "EvidenceCandidate",
    "FactCandidate",
    "ContentUnitRef",
    "ContextWindow",
    "ExtractionEnvelope",
    "QuoteGate",
    "QuoteGateFailure",
    "ReviewBundle",
    "ReviewDecision",
    "ReviewDecisionDecision",
]
