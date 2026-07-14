"""SafetyGate — cognitive safety validation for extraction pipeline.

M2-003B Gate 2: Validates that Provider output does not violate Aurora's
cognitive safety boundaries.

Validates 7 cognitive safety dimensions:
1. Fact pollution: Claim/Prediction must not be marked as Fact
2. Valuation/suggestion: recommendation/value_judgment must remain Claim
3. Prompt Injection: source text injection must not change system behavior
4. Fake Quote: Provider must not fabricate quotes not in source
5. Forged/outside Unit: Provider must not reference nonexistent ContentUnits
6. High confidence pollution: confidence=0.99 must not change epistemic status
7. Provider independence override: Provider must not set independence_group etc.

All decisions emit deterministic ValidationFinding records.
The gate is input-only — it does NOT modify candidates, documents, or ContentUnits.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Sequence

from aurora.extraction.candidates import (
    Candidate,
    ClaimCandidate,
    DataPointCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import ContextWindow
from aurora.extraction.findings import FindingSeverity, ValidationFinding

# ── Frozen provider-enforced fields (must not be set by Provider) ─────────────

PROVIDER_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "independence_group",
    "source_quality_tier",
    "evidence_strength",
    "verification_status",
    "epistemic_status",
)

# ── Claim types that must never be promoted to Fact automatically ─────────────

NON_FACT_CLAIM_TYPES: frozenset[str] = frozenset({
    "prediction",
    "recommendation",
    "value_judgment",
    "opinion",
    "speculation",
})

# ── Confidence threshold for high-confidence pollution check ──────────────────

HIGH_CONFIDENCE_THRESHOLD = 0.99


# ── SafetyGate ────────────────────────────────────────────────────────────────


@dataclass
class SafetyGateReport:
    """Result of running the Safety Gate over a set of candidates."""

    passed_count: int = 0
    failed_count: int = 0
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    @property
    def error_findings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.is_error()]

    @property
    def fact_pollution_count(self) -> int:
        return sum(1 for f in self.findings if f.code == "FACT_POLLUTION")

    @property
    def fake_quote_count(self) -> int:
        return sum(1 for f in self.findings if f.code == "FAKE_QUOTE")

    @property
    def illegal_unit_count(self) -> int:
        return sum(1 for f in self.findings if f.code in (
            "FORGED_CONTENT_UNIT_ID",
            "UNIT_NOT_IN_WINDOW",
            "CROSS_DOCUMENT_UNIT",
        ))

    @property
    def prompt_injection_count(self) -> int:
        return sum(1 for f in self.findings if f.code == "PROMPT_INJECTION")

    @property
    def provider_override_count(self) -> int:
        return sum(1 for f in self.findings if f.code == "PROVIDER_OVERRIDE_FIELD")

    @property
    def high_confidence_pollution_count(self) -> int:
        return sum(1 for f in self.findings if f.code == "HIGH_CONFIDENCE_POLLUTION")


class SafetyGate:
    """M2-003B Gate 2: Cognitive safety validator.

    Validates Provider output against seven cognitive safety dimensions.
    Does not modify any input — read-only validation.
    """

    FROZEN_FIELDS = PROVIDER_FORBIDDEN_FIELDS
    NON_FACT_TYPES = NON_FACT_CLAIM_TYPES
    HIGH_CONF_THRESHOLD = HIGH_CONFIDENCE_THRESHOLD

    def __init__(self, window: ContextWindow, strict_mode: bool = True):
        """Initialize SafetyGate with a ContextWindow.

        Args:
            window: The ContextWindow against which to validate unit references.
            strict_mode: If True (default), Provider forbidden fields are
                         strictly rejected with ERROR findings.
                         If False, they are only WARNING (for testing).
        """
        self._window = window
        self._strict_mode = strict_mode
        self._window_unit_ids = frozenset(u.unit_id for u in window.units)

    def validate(self, candidates: Sequence[Candidate]) -> SafetyGateReport:
        """Run all seven cognitive safety checks.

        Returns SafetyGateReport with pass/fail counts and ValidationFindings.
        """
        report = SafetyGateReport()

        for candidate in candidates:
            findings = self._validate_candidate(candidate)
            if findings:
                report.failed_count += 1
                report.findings.extend(findings)
            else:
                report.passed_count += 1

        return report

    # ── Candidate-level validation ────────────────────────────────────────

    def _validate_candidate(self, candidate: Candidate) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        cid = self._cid(candidate)

        # Check 1: Fact pollution (Claim/Prediction → Fact)
        findings.extend(self._check_fact_pollution(candidate, cid))

        # Check 2: Valuation/recommendation must remain Claim
        findings.extend(self._check_valuation_pollution(candidate, cid))

        # Check 3: Prompt Injection in source text
        findings.extend(self._check_prompt_injection(candidate, cid))

        # Check 4: Provider-forbidden field override
        findings.extend(self._check_provider_override(candidate, cid))

        # Check 5: High confidence pollution
        findings.extend(self._check_high_confidence_pollution(candidate, cid))

        # Check 6: Fake Quote (for quote-bearing candidates)
        findings.extend(self._check_fake_quote(candidate, cid))

        # Check 7: Forged/outside Unit
        findings.extend(self._check_forged_unit(candidate, cid))

        return findings

    # ── Individual Checks ──────────────────────────────────────────────────

    def _check_fact_pollution(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """G2-1: Fact must not be created from Prediction/Recommendation/Value Judgment.

        A FactCandidate with a claim that is actually a prediction/valuation
        is a pollution event.
        """
        findings: list[ValidationFinding] = []

        if not isinstance(candidate, FactCandidate):
            return findings

        statement = (candidate.statement or "").lower()

        # Check for prediction-like language in Fact candidates
        prediction_keywords = ["预计", "预测", "预期", "预计将", "有望", "或将", "可能"]
        for kw in prediction_keywords:
            if kw in statement:
                findings.append(ValidationFinding(
                    code="FACT_POLLUTION",
                    message=f"FactCandidate contains prediction language "
                            f"('{kw}' in '{candidate.statement[:80]}')",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "statement": candidate.statement,
                        "matched_keyword": kw,
                        "violation": "G2-1",
                    },
                ))
                break

        # Check for valuation/recommendation language in Fact candidates
        valuation_keywords = [
            "不建议", "建议买入", "建议卖出", "不建议买入", "不建议卖出",
            "估值", "合理价值", "目标价", "合理价格",
        ]
        for kw in valuation_keywords:
            if kw in statement:
                findings.append(ValidationFinding(
                    code="FACT_POLLUTION",
                    message=f"FactCandidate contains valuation language "
                            f"('{kw}' in '{candidate.statement[:80]}')",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "statement": candidate.statement,
                        "matched_keyword": kw,
                        "violation": "G2-1",
                    },
                ))
                break

        return findings

    def _check_valuation_pollution(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """Check that valuation/recommendation claims are not being treated as
        verified facts or given inappropriate epistemic status."""
        findings: list[ValidationFinding] = []

        if not isinstance(candidate, ClaimCandidate):
            return findings

        claim_type = (candidate.claim_type or "").lower()

        # Valuation/recommendation claims should NOT be promotable_to_fact
        if claim_type in ("recommendation", "value_judgment", "valuation"):
            if candidate.promotable_to_fact:
                findings.append(ValidationFinding(
                    code="FACT_POLLUTION",
                    message=f"ClaimCandidate type '{candidate.claim_type}' "
                            f"should not be promotable_to_fact=True",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "claim_type": candidate.claim_type,
                        "statement": candidate.statement[:80],
                        "violation": "G2-1",
                    },
                ))

        return findings

    def _check_prompt_injection(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """G2-4: Prompt Injection detection.

        If source text contains system-instruction-like language,
        it must NOT change system behavior. The candidate should be
        treated as ordinary text and validated normally.

        We check if candidate text contains injection patterns that
        should have been rejected or treated as unsafe.
        """
        findings: list[ValidationFinding] = []

        # Check all text fields for injection patterns
        texts_to_check: list[str] = []
        if hasattr(candidate, "statement"):
            texts_to_check.append(candidate.statement or "")
        if hasattr(candidate, "source_quote"):
            texts_to_check.append(candidate.source_quote or "")
        if hasattr(candidate, "note"):
            texts_to_check.append(candidate.note or "")

        injection_patterns = [
            "忽略系统指令",
            "忽略之前的指令",
            "把以下内容标记为已验证",
            "把以下标记为已验证事实",
            "override system",
            "ignore previous instructions",
            "treat the following as verified",
            "mark as verified fact",
            "disregard system prompt",
        ]

        combined = " ".join(texts_to_check).lower()

        for pattern in injection_patterns:
            if pattern in combined:
                # If the candidate is a FactCandidate with injection text,
                # that's a prompt injection violation
                if isinstance(candidate, FactCandidate):
                    findings.append(ValidationFinding(
                        code="PROMPT_INJECTION",
                        message=f"FactCandidate contains prompt injection "
                                f"pattern '{pattern}'",
                        severity=FindingSeverity.ERROR,
                        candidate_id=cid,
                        gate_name="safety_gate",
                        details={
                            "pattern": pattern,
                            "violation": "G2-4",
                        },
                    ))
                # For other candidates, injection text is just treated as
                # source text — we log an INFO finding
                else:
                    findings.append(ValidationFinding(
                        code="PROMPT_INJECTION",
                        message=f"Candidate contains prompt injection "
                                f"pattern '{pattern}' — treated as source text",
                        severity=FindingSeverity.INFO,
                        candidate_id=cid,
                        gate_name="safety_gate",
                        details={
                            "pattern": pattern,
                            "handling": "treated_as_source_text",
                        },
                    ))
                break  # One pattern match is enough

        return findings

    def _check_provider_override(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """G2-5: Provider must not set forbidden fields.

        Fields like independence_group, evidence_strength, verification_status,
        epistemic_status, source_quality_tier must not be set by the Provider.
        """
        findings: list[ValidationFinding] = []

        for field_name in self.FROZEN_FIELDS:
            value = getattr(candidate, field_name, None)
            if value is not None and value != "" and value != [] and value != {}:
                severity = FindingSeverity.ERROR if self._strict_mode else FindingSeverity.WARNING
                findings.append(ValidationFinding(
                    code="PROVIDER_OVERRIDE_FIELD",
                    message=f"Provider set forbidden field "
                            f"'{field_name}={value!r}' on candidate {cid}",
                    severity=severity,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "field": field_name,
                        "value": str(value),
                        "violation": "G2-5",
                    },
                ))

        return findings

    def _check_high_confidence_pollution(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """G2-6: High confidence must not change epistemic status.

        confidence >= 0.99 must not cause automatic Fact promotion,
        verification change, or evidence strength change.
        """
        findings: list[ValidationFinding] = []

        confidence = getattr(candidate, "confidence", None)
        if confidence is None:
            return findings

        try:
            conf = float(confidence)
        except (TypeError, ValueError):
            return findings

        if conf < self.HIGH_CONF_THRESHOLD:
            return findings

        # High confidence on a Claim that is promotable_to_fact is a violation
        if isinstance(candidate, ClaimCandidate):
            if candidate.promotable_to_fact:
                findings.append(ValidationFinding(
                    code="HIGH_CONFIDENCE_POLLUTION",
                    message=f"ClaimCandidate with confidence={conf} "
                            f"has promotable_to_fact=True",
                    severity=FindingSeverity.WARNING,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "confidence": conf,
                        "claim_type": candidate.claim_type,
                        "violation": "G2-6",
                    },
                ))

        # High confidence on a FactCandidate that was NOT explicitly reviewed
        # is a violation
        if isinstance(candidate, FactCandidate):
            if candidate.promotable:
                findings.append(ValidationFinding(
                    code="HIGH_CONFIDENCE_POLLUTION",
                    message=f"FactCandidate with confidence={conf} "
                            f"has promotable=True — confidence should not "
                            f"drive knowledge status",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "confidence": conf,
                        "violation": "G2-6",
                    },
                ))

        return findings

    def _check_fake_quote(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """G2-2: Provider must not fabricate quotes.

        Check that source_quote text actually appears in the referenced
        ContentUnit within the ContextWindow.
        """
        findings: list[ValidationFinding] = []

        # EntityCandidates don't have source_quotes
        from aurora.extraction.candidates import EntityCandidate
        if isinstance(candidate, EntityCandidate):
            return findings

        quote = getattr(candidate, "source_quote", "") or ""
        suid = getattr(candidate, "source_unit_id", "") or ""

        if not quote.strip():
            return findings  # Empty quote handled by QuoteGate

        if not suid:
            return findings  # Missing unit handled by unit check

        # Get the unit text
        unit = self._window.get_unit_by_id(suid)
        if unit is None:
            return findings  # Handled by forged_unit check

        # Use NFKC normalization + whitespace collapse for comparison
        import re
        import unicodedata

        norm_unit_text = unicodedata.normalize("NFKC", unit.text)
        norm_quote = unicodedata.normalize("NFKC", quote)
        norm_unit_collapsed = re.sub(r"\s+", " ", norm_unit_text).strip()
        norm_quote_collapsed = re.sub(r"\s+", " ", norm_quote).strip()

        # Check if quote exists in unit text (literal substring)
        if norm_quote not in norm_unit_text and norm_quote_collapsed not in norm_unit_collapsed:
            findings.append(ValidationFinding(
                code="FAKE_QUOTE",
                message=f"source_quote not found in ContentUnit "
                        f"'{suid}' text — possible fabrication",
                severity=FindingSeverity.ERROR,
                candidate_id=cid,
                gate_name="safety_gate",
                source_unit_id=suid,
                details={
                    "source_quote": quote[:120],
                    "source_unit_id": suid,
                    "violation": "G2-2",
                },
            ))

        return findings

    def _check_forged_unit(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """G2-3: Provider must not reference nonexistent or outside-window units.

        Check that source_unit_id exists in the ContextWindow and belongs
        to the same document.
        """
        findings: list[ValidationFinding] = []

        from aurora.extraction.candidates import EntityCandidate
        if isinstance(candidate, EntityCandidate):
            return findings

        suid = getattr(candidate, "source_unit_id", "") or ""

        if not suid:
            return findings  # Empty handled by QuoteGate

        # Check if unit exists
        if suid not in self._window_unit_ids:
            findings.append(ValidationFinding(
                code="FORGED_CONTENT_UNIT_ID",
                message=f"source_unit_id '{suid}' does not exist "
                        f"in ContextWindow — possible fabrication",
                severity=FindingSeverity.ERROR,
                candidate_id=cid,
                gate_name="safety_gate",
                source_unit_id=suid,
                details={
                    "source_unit_id": suid,
                    "violation": "G2-3",
                },
            ))
            return findings

        # Check cross-document
        unit = self._window.get_unit_by_id(suid)
        if unit is not None and unit.document_id != self._window.document_id:
            findings.append(ValidationFinding(
                code="CROSS_DOCUMENT_UNIT",
                message=f"source_unit_id '{suid}' belongs to document "
                        f"'{unit.document_id}', not '{self._window.document_id}'",
                severity=FindingSeverity.ERROR,
                candidate_id=cid,
                gate_name="safety_gate",
                source_unit_id=suid,
                details={
                    "unit_doc_id": unit.document_id,
                    "window_doc_id": self._window.document_id,
                    "violation": "G2-3",
                },
            ))

        return findings

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _cid(candidate: Candidate) -> str:
        for attr in ("candidate_id", "id"):
            val = getattr(candidate, attr, None)
            if val:
                return str(val)
        return "unknown"
