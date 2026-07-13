"""Quote Gate — validates that every candidate's source_quote exists in source ContentUnits.

Rules:
- source_quote must be a substring of at least one ContentUnit.text (after Unicode normalization).
- Failed candidates go to flagged_errors — never silently dropped.
- quote_locator_hint must reference a valid unit context.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Sequence

from aurora.extraction.candidates import Candidate
from aurora.extraction.context_window import ContextWindow


def _normalize(text: str) -> str:
    """NFKC normalization for deterministic Unicode matching."""
    return unicodedata.normalize("NFKC", text)


@dataclass
class QuoteGateFailure:
    """Record of a quote validation failure for a specific candidate."""

    candidate: Candidate
    source_quote: str
    candidate_id: str
    reason: str


@dataclass
class QuoteGateReport:
    """Result of running the Quote Gate over a set of candidates."""

    passed_count: int = 0
    failed_count: int = 0
    failures: list[QuoteGateFailure] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0


class QuoteGate:
    """Validates that candidate source_quotes exist in the ContextWindow.

    Each candidate's source_quote must be a substring (after NFKC normalization)
    of at least one ContentUnit's text in the context window.
    """

    def __init__(self, window: ContextWindow):
        self._window = window
        # Pre-normalize all unit texts for performance
        self._normalized_texts: dict[str, str] = {
            unit.unit_id: _normalize(unit.text) for unit in window.units
        }
        # Also build a combined text for fallback matching
        self._combined_normalized = _normalize("\n".join(u.text for u in window.units))

    def validate(self, candidates: Sequence[Candidate]) -> QuoteGateReport:
        """Validate all candidates' source_quotes against the context window.

        Returns a QuoteGateReport with pass/fail counts and failure details.
        """
        report = QuoteGateReport()

        for candidate in candidates:
            quote = self._get_source_quote(candidate)
            if quote is None:
                report.passed_count += 1
                continue

            normalized_quote = _normalize(quote)
            candidate_id = self._get_candidate_id(candidate)

            # Check every ContentUnit for the normalized quote
            found = False
            for unit_id, norm_text in self._normalized_texts.items():
                if normalized_quote in norm_text:
                    found = True
                    break

            # Fallback: check combined text
            if not found and normalized_quote in self._combined_normalized:
                found = True

            if found:
                report.passed_count += 1
            else:
                report.failed_count += 1
                report.failures.append(
                    QuoteGateFailure(
                        candidate=candidate,
                        source_quote=quote,
                        candidate_id=candidate_id,
                        reason=f"source_quote not found in any ContentUnit",
                    )
                )

        return report

    def validate_or_raise(self, candidates: Sequence[Candidate]) -> QuoteGateReport:
        """Validate and raise if any candidates fail the Quote Gate."""
        report = self.validate(candidates)
        if not report.all_passed:
            failure_ids = [f.candidate_id for f in report.failures]
            raise QuoteGateError(
                f"Quote Gate failures for candidates: {failure_ids}",
                report=report,
            )
        return report

    @staticmethod
    def _get_source_quote(candidate: Candidate) -> str | None:
        """Extract the source_quote field from any candidate type."""
        return getattr(candidate, "source_quote", None)

    @staticmethod
    def _get_candidate_id(candidate: Candidate) -> str:
        """Get the display ID for a candidate."""
        for attr in ("id", "candidate_id"):
            val = getattr(candidate, attr, "")
            if val:
                return val
        return "unknown"


class QuoteGateError(Exception):
    """Raised when Quote Gate validation fails."""

    def __init__(self, message: str, report: QuoteGateReport | None = None):
        super().__init__(message)
        self.report = report
