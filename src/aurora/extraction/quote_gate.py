"""Quote Gate V2 — validates candidate source_quotes with strict source_unit_id enforcement.

V2 changes:
- NFKC normalization for all text comparison
- literal: supporting_quote must be a continuous substring within the specific source_unit_id
- token_set: 100% token overlap within specific source_unit_id (only TABLE/TABLE_ROW)
- Rejects: missing units, wrong-document units, empty quotes, token_set on non-table cells
- Does NOT search full window — only checks source_unit_id
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Sequence

from aurora.extraction.candidates import (
    Candidate,
    ClaimCandidate,
    DataPointCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import ContentUnitRef, ContextWindow
from aurora.extraction.findings import ValidationFinding

# Tokenization: split on whitespace, keep numbers, units, currency symbols
_TOKEN_RE = re.compile(r"\S+")


def _normalize(text: str) -> str:
    """NFKC normalization for deterministic Unicode matching."""
    return unicodedata.normalize("NFKC", text)


def _collapse_whitespace(text: str) -> str:
    """Collapse consecutive whitespace into single space."""
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> set[str]:
    """Tokenize text into a set of normalized tokens."""
    normalized = _normalize(text)
    tokens = _TOKEN_RE.findall(normalized)
    return set(tokens)


_ALLOWED_TOKEN_SET_TYPES = frozenset({"table", "table_row"})


@dataclass
class QuoteGateFailure:
    """Backward-compatible record of a quote validation failure."""

    candidate: Any
    source_quote: str
    candidate_id: str
    reason: str


@dataclass
class QuoteGateReport:
    """Result of running the Quote Gate over a set of candidates."""

    passed_count: int = 0
    failed_count: int = 0
    findings: list[ValidationFinding] = field(default_factory=list)
    failures: list[QuoteGateFailure] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    @property
    def error_findings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.is_error()]


class QuoteGate:
    """V2: Validates candidates' source_quotes with strict source_unit_id enforcement.

    - literal: NFKC → collapse whitespace → must be continuous substring within
      the specific source_unit_id's text
    - token_set: 100% token overlap within specific source_unit_id
      (only allowed for TABLE and TABLE_ROW unit types)
    - Rejects: missing units, wrong-document units, empty quotes
    """

    def __init__(self, window: ContextWindow):
        self._window = window
        # Pre-normalize all unit texts
        self._norm_texts: dict[str, str] = {
            u.unit_id: _normalize(u.text) for u in window.units
        }
        self._unit_types: dict[str, str] = {
            u.unit_id: u.unit_type for u in window.units
        }

    def validate(self, candidates: Sequence[Candidate]) -> QuoteGateReport:
        """Validate all candidates against the context window.

        Returns QuoteGateReport with pass/fail counts and ValidationFindings.
        """
        report = QuoteGateReport()

        for candidate in candidates:
            findings = self._validate_candidate(candidate)
            if findings:
                report.failed_count += 1
                report.findings.extend(findings)
                # Backward-compatible: also populate failures
                for f in findings:
                    if f.is_error():
                        report.failures.append(
                            QuoteGateFailure(
                                candidate=candidate,
                                source_quote=self._get_source_quote(candidate),
                                candidate_id=self._get_candidate_id(candidate),
                                reason=f.message,
                            )
                        )
            else:
                report.passed_count += 1

        return report

    def validate_or_raise(
        self, candidates: Sequence[Candidate]
    ) -> QuoteGateReport:
        """Validate and raise if any candidates fail."""
        report = self.validate(candidates)
        if not report.all_passed:
            failed_ids = [
                f.candidate_id
                for f in report.findings
                if f.candidate_id and f.is_error()
            ]
            raise QuoteGateError(
                f"Quote Gate failures for candidates: {failed_ids}",
                report=report,
            )
        return report

    def _validate_candidate(self, candidate: Candidate) -> list[ValidationFinding]:
        """Validate a single candidate. Returns empty list if all checks pass."""
        findings: list[ValidationFinding] = []

        cid = self._get_candidate_id(candidate)

        # EntityCandidates do not have source_unit_id — skip validation
        from aurora.extraction.candidates import EntityCandidate
        if isinstance(candidate, EntityCandidate):
            return findings

        quote = self._get_source_quote(candidate)
        source_unit_id = self._get_source_unit_id(candidate)
        match_mode = self._get_quote_match_mode(candidate)

        # Check 1: Non-empty source_unit_id
        if not source_unit_id:
            findings.append(
                ValidationFinding.illegal_unit_reference(
                    cid, "", "empty source_unit_id"
                )
            )
            return findings

        # Check 2: Unit exists in window
        unit = self._window.get_unit_by_id(source_unit_id)
        if unit is None:
            findings.append(
                ValidationFinding.unit_not_in_window(cid, source_unit_id)
            )
            return findings

        # Check 3: Unit belongs to same document
        if unit.document_id != self._window.document_id:
            findings.append(
                ValidationFinding.cross_document_unit(
                    cid, source_unit_id, unit.document_id, self._window.document_id
                )
            )
            return findings

        # Check 4: Non-empty quote
        if not quote or not quote.strip():
            findings.append(ValidationFinding.empty_quote(cid))
            return findings

        # Check 5: Validate quote based on match_mode
        unit_type = self._unit_types.get(source_unit_id, "").lower()

        if match_mode == "token_set":
            if unit_type not in _ALLOWED_TOKEN_SET_TYPES:
                findings.append(
                    ValidationFinding.token_set_on_non_table(
                        cid, source_unit_id, unit_type
                    )
                )
                return findings
            if not self._validate_token_set(quote, source_unit_id):
                findings.append(
                    ValidationFinding.quote_not_found(
                        cid, quote, source_unit_id,
                        f"token_set match failed on {unit_type} unit"
                    )
                )
        else:
            # literal mode (default)
            if not self._validate_literal(quote, source_unit_id):
                findings.append(
                    ValidationFinding.quote_not_found(
                        cid, quote, source_unit_id,
                        "literal substring not found in unit text"
                    )
                )

        return findings

    def _validate_literal(self, quote: str, source_unit_id: str) -> bool:
        """Check if normalized+whitespace-collapsed quote is a substring
        of the normalized+whitespace-collapsed unit text."""
        norm_text = self._norm_texts.get(source_unit_id, "")
        if not norm_text:
            return False

        norm_quote = _collapse_whitespace(_normalize(quote))
        norm_text_collapsed = _collapse_whitespace(norm_text)

        return norm_quote in norm_text_collapsed

    def _validate_token_set(self, quote: str, source_unit_id: str) -> bool:
        """Check that 100% of quote tokens are present in the unit text.

        All tokens from the quote must be found in the unit text.
        No cross-unit token matching.
        """
        norm_text = self._norm_texts.get(source_unit_id, "")
        if not norm_text:
            return False

        quote_tokens = _tokenize(quote)
        unit_tokens = _tokenize(norm_text)

        if not quote_tokens:
            return False  # empty token set

        return quote_tokens.issubset(unit_tokens)

    @staticmethod
    def _get_source_quote(candidate: Candidate) -> str:
        return getattr(candidate, "source_quote", "") or ""

    @staticmethod
    def _get_source_unit_id(candidate: Candidate) -> str:
        return getattr(candidate, "source_unit_id", "") or ""

    @staticmethod
    def _get_quote_match_mode(candidate: Candidate) -> str:
        mode = getattr(candidate, "quote_match_mode", None)
        if mode:
            return mode
        # Infer from candidate type
        if hasattr(candidate, "quote_match_mode"):
            return "literal"
        return "literal"

    @staticmethod
    def _get_candidate_id(candidate: Candidate) -> str:
        for attr in ("id", "candidate_id"):
            val = getattr(candidate, attr, None)
            if val:
                return str(val)
        return "unknown"


class QuoteGateError(Exception):
    """Raised when Quote Gate validation fails."""

    def __init__(self, message: str, report: QuoteGateReport | None = None):
        super().__init__(message)
        self.report = report
