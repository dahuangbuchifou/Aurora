"""Abstract base for extraction providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from aurora.extraction.context_window import ContextWindow
from aurora.extraction.envelope import ExtractionEnvelope


class ExtractionProvider(ABC):
    """Base class for content extraction providers.

    Implementations produce an ExtractionEnvelope from a ContextWindow.
    """

    name: str
    version: str

    @abstractmethod
    def extract(self, window: ContextWindow) -> ExtractionEnvelope:
        """Extract candidates from the given context window."""
        raise NotImplementedError
