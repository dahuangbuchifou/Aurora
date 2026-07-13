"""ValidationFinding — lightweight error/warning record for QuoteGate and reference-gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FindingSeverity(StrEnum):
    """Severity level for validation findings."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class ValidationFinding:
    """Immutable record of a validation issue found by QuoteGate or reference-gate.

    These are lightweight DTOs — they do not modify candidates or the bundle.
    They are collected into ReviewBundle.validation_findings for audit.
    """

    code: str
    message: str
    severity: FindingSeverity = FindingSeverity.ERROR
    candidate_id: str = ""
    gate_name: str = "quote_gate"
    source_unit_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def quote_not_found(
        cls, candidate_id: str, source_quote: str, source_unit_id: str, reason: str = ""
    ) -> "ValidationFinding":
        return cls(
            code="QUOTE_NOT_FOUND",
            message=f"source_quote '{source_quote[:80]}' not found in unit {source_unit_id}",
            severity=FindingSeverity.ERROR,
            candidate_id=candidate_id,
            gate_name="quote_gate",
            source_unit_id=source_unit_id,
            details={"source_quote": source_quote, "reason": reason},
        )

    @classmethod
    def unit_not_in_window(
        cls, candidate_id: str, source_unit_id: str
    ) -> "ValidationFinding":
        return cls(
            code="UNIT_NOT_IN_WINDOW",
            message=f"source_unit_id {source_unit_id} not found in ContextWindow",
            severity=FindingSeverity.ERROR,
            candidate_id=candidate_id,
            gate_name="quote_gate",
            source_unit_id=source_unit_id,
        )

    @classmethod
    def cross_document_unit(
        cls, candidate_id: str, source_unit_id: str, unit_doc_id: str, window_doc_id: str
    ) -> "ValidationFinding":
        return cls(
            code="CROSS_DOCUMENT_UNIT",
            message=f"Unit {source_unit_id} belongs to document '{unit_doc_id}' "
            f"but window expects '{window_doc_id}'",
            severity=FindingSeverity.ERROR,
            candidate_id=candidate_id,
            gate_name="quote_gate",
            source_unit_id=source_unit_id,
            details={"unit_doc_id": unit_doc_id, "window_doc_id": window_doc_id},
        )

    @classmethod
    def empty_quote(cls, candidate_id: str) -> "ValidationFinding":
        return cls(
            code="EMPTY_QUOTE",
            message="Candidate has empty source_quote",
            severity=FindingSeverity.ERROR,
            candidate_id=candidate_id,
            gate_name="quote_gate",
        )

    @classmethod
    def token_set_on_non_table(
        cls, candidate_id: str, source_unit_id: str, unit_type: str
    ) -> "ValidationFinding":
        return cls(
            code="TOKEN_SET_ON_NON_TABLE",
            message=f"token_set quote_match_mode on non-TABLE/TABLE_ROW unit "
            f"({unit_type}) for unit {source_unit_id}",
            severity=FindingSeverity.ERROR,
            candidate_id=candidate_id,
            gate_name="quote_gate",
            source_unit_id=source_unit_id,
            details={"unit_type": unit_type},
        )

    @classmethod
    def duplicate_unit(cls, unit_id: str) -> "ValidationFinding":
        return cls(
            code="DUPLICATE_UNIT",
            message=f"Duplicate unit_id in ContextWindow: {unit_id}",
            severity=FindingSeverity.ERROR,
            gate_name="context_window",
            source_unit_id=unit_id,
        )

    @classmethod
    def empty_window(cls) -> "ValidationFinding":
        return cls(
            code="EMPTY_WINDOW",
            message="ContextWindow has no units",
            severity=FindingSeverity.ERROR,
            gate_name="context_window",
        )

    @classmethod
    def illegal_unit_reference(
        cls, candidate_id: str, source_unit_id: str, reason: str = ""
    ) -> "ValidationFinding":
        return cls(
            code="ILLEGAL_UNIT_REFERENCE",
            message=f"Illegal unit reference: {reason}",
            severity=FindingSeverity.ERROR,
            candidate_id=candidate_id,
            gate_name="reference_gate",
            source_unit_id=source_unit_id,
            details={"reason": reason},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "candidate_id": self.candidate_id,
            "gate_name": self.gate_name,
            "source_unit_id": self.source_unit_id,
            "details": self.details,
        }

    def is_error(self) -> bool:
        return self.severity == FindingSeverity.ERROR
