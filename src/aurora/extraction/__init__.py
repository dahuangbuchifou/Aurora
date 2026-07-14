"""Aurora Extraction Pipeline.

V2 components:
- ExtractionRequest: minimal contract for triggering extraction
- ContextWindow: deterministic ordered ContentUnit snapshot with V2 JSON hash
- Candidates: lightweight DTOs (Entity, DataPoint, Claim, Evidence, Fact)
- FixtureProvider: reads from independent provider_responses fixtures
- ExtractionEnvelope: container for extraction results + provider metadata
- QuoteGate: validates source_quotes with strict source_unit_id enforcement
- ValidationFinding: error/warning records for gate validation
- ReviewBundle: immutable audit trail with canonicalized JSON hash
"""

from aurora.extraction.candidates import (
    Candidate,
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import (
    CANDIDATE_TYPE_ORDER,
    ContentUnitRef,
    ContextWindow,
    ContextWindowError,
)
from aurora.extraction.envelope import ExtractionEnvelope, ProviderMetadata
from aurora.extraction.findings import FindingSeverity, ValidationFinding
from aurora.extraction.providers.base import ExtractionProvider, ProviderResponse
from aurora.extraction.providers.fixture_provider import FixtureProvider
from aurora.extraction.quote_gate import QuoteGate, QuoteGateError, QuoteGateReport
from aurora.extraction.request import ExtractionRequest
from aurora.extraction.review_bundle import BUNDLE_SCHEMA_VERSION, ReviewBundle
from aurora.extraction.safety_gate import SafetyGate, SafetyGateReport

__all__ = [
    # Request
    "ExtractionRequest",
    # Context
    "ContentUnitRef",
    "ContextWindow",
    "ContextWindowError",
    "CANDIDATE_TYPE_ORDER",
    # Candidates
    "Candidate",
    "EntityCandidate",
    "DataPointCandidate",
    "ClaimCandidate",
    "EvidenceCandidate",
    "FactCandidate",
    # Provider
    "ExtractionProvider",
    "ProviderResponse",
    "FixtureProvider",
    # Envelope
    "ExtractionEnvelope",
    "ProviderMetadata",
    # Quote Gate
    "QuoteGate",
    "QuoteGateReport",
    "QuoteGateError",
    # Validation
    "ValidationFinding",
    "FindingSeverity",
    # Review
    "ReviewBundle",
    "BUNDLE_SCHEMA_VERSION",
    # Safety Gate (M2-003B Gate 2)
    "SafetyGate",
    "SafetyGateReport",
]
