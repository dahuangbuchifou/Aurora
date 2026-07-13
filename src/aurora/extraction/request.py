"""ExtractionRequest — minimal contract for triggering extraction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractionRequest:
    """Minimal immutable contract for an extraction run.

    Carries only the identifiers needed to start extraction.
    The ContextWindow, provider selection, and runtime config are
    injected by the orchestrator, not embedded in the request.
    """

    document_id: str
    case_id: str = ""
    run_id: str | None = None
    provider_name: str = "fixture"
    provider_version: str = "2.0"
    deterministic_mode: bool = True
    schema_version: str = "2.0"
    extra: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"ExtractionRequest(document_id={self.document_id!r}, "
            f"provider={self.provider_name}, "
            f"case={self.case_id!r})"
        )
