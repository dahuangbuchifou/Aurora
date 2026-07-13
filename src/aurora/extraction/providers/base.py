"""Abstract base for extraction providers with ProviderResponse contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from aurora.extraction.candidates import Candidate
from aurora.extraction.context_window import ContextWindow
from aurora.extraction.envelope import ExtractionEnvelope, ProviderMetadata


@dataclass(frozen=True)
class ProviderResponse:
    """Immutable response from an ExtractionProvider.

    Contains raw candidate data and metadata. This is the provider's output
    before QuoteGate validation and ReviewBundle construction.
    """

    candidates: tuple[Candidate, ...]
    provider_metadata: ProviderMetadata
    raw_payload: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)


class ExtractionProvider(ABC):
    """Base class for content extraction providers.

    V2: extract() now returns ProviderResponse (pre-envelope contract).
    The envelope conversion is handled by the orchestration layer.
    """

    name: str
    version: str

    @abstractmethod
    def extract(self, window: ContextWindow) -> ProviderResponse:
        """Extract candidates from the given context window.

        Returns raw ProviderResponse — NOT an ExtractionEnvelope.
        The orchestration layer wraps this into an ExtractionEnvelope
        after QuoteGate validation.
        """
        raise NotImplementedError
