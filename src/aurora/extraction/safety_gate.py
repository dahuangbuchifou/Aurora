"""SafetyGate — cognitive safety validation for extraction pipeline (V3).

M2-003B Gate 2 — Round 2 → Final rework.

Round 1 fixes preserved:
- Raw JSON field check before DTO construction (B01)
- Provider-submitted promotable=True → unconditional ERROR (B03)
- Fact pollution via target_claim_id reference graph (B04)
- Prompt Injection on FULL ContentUnit (B05)
- ReviewBundle integration (B06)
- No duplicate QuoteGate (B07)
- INFO/WARNING not counted as failure (M01)

Round 2 fixes:
- R2-B01: independence_group RESTORED to PROVIDER_FORBIDDEN_FIELDS
  (Provider must NOT set it; Aurora engine calculates from Source/Document)
- R2-B02: raw_payload associated by candidate_id, not positional index
  (prevents misalignment after candidate sorting)
- R2-M01: Fact promotion eligibility changed from blacklist to WHITELIST
  (only fact_claim is promotable to Fact; all other types denied)

SafetyGate validates Provider output against cognitive safety dimensions.
It does NOT duplicate QuoteGate or ReferenceGate — it consumes their output.
All decisions emit deterministic ValidationFinding records.
The gate is input-only — it does NOT modify candidates, documents, or ContentUnits.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from aurora.extraction.candidates import (
    Candidate,
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import ContextWindow
from aurora.extraction.findings import FindingSeverity, ValidationFinding

# ── Constants ────────────────────────────────────────────────────────────────

# Provider-forbidden fields: must NOT be set in raw Provider JSON payload.
# R2-B01: independence_group is RESTORED. Provider must NOT set it.
# Aurora engine computes independence_group from Source/Document/DerivationLink.
PROVIDER_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "independence_group",
    "source_quality_tier",
    "evidence_strength",
    "verification_status",
    "epistemic_status",
)

# ── R2-M01: Fact promotion WHITELIST ─────────────────────────────────────────
# Only fact_claim is eligible for FactCandidate promotion.
# All other ClaimType values (interpretation, causal_claim, prediction,
# recommendation, risk_claim, value_judgment, hypothesis) are inherently
# non-promotable. This aligns with the frozen core enum in enums.py.
PROMOTABLE_CLAIM_TYPES: frozenset[str] = frozenset({"fact_claim"})

# Confidence threshold for high-confidence pollution check
HIGH_CONFIDENCE_THRESHOLD = 0.99

# Prompt injection patterns — checked against FULL ContentUnit text
PROMPT_INJECTION_PATTERNS: list[str] = [
    "忽略系统指令",
    "忽略之前的指令",
    "把以下内容标记为已验证",
    "把以下标记为已验证事实",
    "override system",
    "ignore previous instructions",
    "treat the following as verified",
    "mark as verified fact",
    "disregard system prompt",
    "ignore all previous",
]


# ── SafetyGateReport ─────────────────────────────────────────────────────────

@dataclass
class SafetyGateReport:
    """Result of running the Safety Gate over a set of candidates."""

    passed_count: int = 0
    accepted_count: int = 0
    error_count: int = 0
    findings: list[ValidationFinding] = field(default_factory=list)
    accepted_candidate_ids: list[str] = field(default_factory=list)
    rejected_candidate_ids: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.error_count == 0

    @property
    def failed_count(self) -> int:
        return self.error_count

    @property
    def error_findings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.is_error()]

    @property
    def fact_pollution_count(self) -> int:
        return sum(1 for f in self.findings if f.code in (
            "FACT_POLLUTION",
            "FACT_POLLUTION_PREDICTION",
            "FACT_POLLUTION_VALUATION",
            "FACT_POLLUTION_INTERPRETATION",
            "FACT_POLLUTION_CAUSAL",
            "FACT_POLLUTION_RISK",
            "FACT_POLLUTION_HYPOTHESIS",
            "NON_PROMOTABLE_CLAIM_TYPE",
        ))

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


# ── SafetyGate ────────────────────────────────────────────────────────────────

class SafetyGate:
    """M2-003B Gate 2 V3: Cognitive safety validator.

    Validates Provider output against cognitive safety dimensions.
    Consumes QuoteGate/ReferenceGate findings; does NOT duplicate them.
    """

    FROZEN_FIELDS = PROVIDER_FORBIDDEN_FIELDS
    PROMOTABLE_TYPES = PROMOTABLE_CLAIM_TYPES
    HIGH_CONF_THRESHOLD = HIGH_CONFIDENCE_THRESHOLD

    def __init__(
        self,
        window: ContextWindow,
        strict_mode: bool = True,
        existing_findings: Sequence[ValidationFinding] | None = None,
    ):
        self._window = window
        self._strict_mode = strict_mode
        self._window_unit_ids = frozenset(u.unit_id for u in window.units)
        self._existing_finding_keys: set[str] = set()
        if existing_findings:
            for f in existing_findings:
                key = f"{f.code}|{f.candidate_id}|{f.source_unit_id}"
                self._existing_finding_keys.add(key)

    # ── Main Entry Point ─────────────────────────────────────────────────

    def validate(
        self,
        candidates: Sequence[Candidate],
        raw_payloads: dict[str, dict[str, Any]] | None = None,
    ) -> SafetyGateReport:
        """Run all cognitive safety checks.

        Args:
            candidates: Extracted candidate DTOs.
            raw_payloads: Dict mapping candidate_id → raw Provider JSON payload.
                          (R2-B02: keyed by candidate_id, not positional)
        """
        report = SafetyGateReport()

        # Build candidate index for B04 (target_claim_id graph)
        candidate_index: dict[str, Candidate] = {}
        for c in candidates:
            cid = self._cid(c)
            if cid:
                candidate_index[cid] = c

        for candidate in candidates:
            cid = self._cid(candidate)
            raw = raw_payloads.get(cid) if raw_payloads else None

            findings = self._validate_candidate(
                candidate, cid, candidate_index, raw_payload=raw,
            )

            has_error = any(f.is_error() for f in findings)
            report.findings.extend(findings)

            if has_error:
                report.error_count += 1
                report.rejected_candidate_ids.append(cid)
            else:
                report.passed_count += 1
                report.accepted_candidate_ids.append(cid)

        report.accepted_count = len(report.accepted_candidate_ids)
        return report

    # ── Candidate-level validation ────────────────────────────────────────

    def _validate_candidate(
        self,
        candidate: Candidate,
        cid: str,
        candidate_index: dict[str, Candidate],
        raw_payload: dict[str, Any] | None = None,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        # B01/R2-B01: Check raw payload for ALL 5 forbidden fields
        findings.extend(self._check_raw_payload_fields(candidate, cid, raw_payload))

        # B03: Provider-set promotable → unconditional ERROR
        findings.extend(self._check_provider_promotable(candidate, cid))

        # B04: Fact pollution via target_claim_id graph
        findings.extend(self._check_fact_claim_graph(candidate, cid, candidate_index))

        # B05: Prompt Injection on FULL ContentUnit text
        findings.extend(self._check_prompt_injection_full(candidate, cid))

        # G2-6: High confidence pollution
        findings.extend(self._check_high_confidence_pollution(candidate, cid))

        # Supplementary: keyword-based pollution
        findings.extend(self._check_keyword_pollution(candidate, cid))

        return findings

    # ── R2-B01: Raw Payload Forbidden-Field Check ─────────────────────────
    # independence_group is RESTORED as a forbidden field.

    def _check_raw_payload_fields(
        self,
        candidate: Candidate,
        cid: str,
        raw_payload: dict[str, Any] | None = None,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        if raw_payload:
            for field_name in self.FROZEN_FIELDS:
                if field_name in raw_payload and raw_payload[field_name]:
                    value = raw_payload[field_name]
                    if value not in ("", None, [], {}):
                        severity = (
                            FindingSeverity.ERROR
                            if self._strict_mode
                            else FindingSeverity.WARNING
                        )
                        findings.append(ValidationFinding(
                            code="PROVIDER_OVERRIDE_FIELD",
                            message=f"Provider raw payload sets forbidden field "
                                    f"'{field_name}={value!r}' on candidate {cid}",
                            severity=severity,
                            candidate_id=cid,
                            gate_name="safety_gate",
                            details={
                                "field": field_name,
                                "value": str(value),
                                "source": "raw_provider_payload",
                                "violation": "G2-5",
                            },
                        ))
        else:
            # Fallback: check DTO for forbidden field values
            for field_name in self.FROZEN_FIELDS:
                value = getattr(candidate, field_name, None)
                if value is not None and value != "" and value != [] and value != {}:
                    severity = (
                        FindingSeverity.ERROR
                        if self._strict_mode
                        else FindingSeverity.WARNING
                    )
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
                            "source": "candidate_dto_fallback",
                            "violation": "G2-5",
                        },
                    ))

        return findings

    # ── B03/R2-M01: Provider promotable → ERROR ──────────────────────────

    def _check_provider_promotable(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        """B03: Provider must not set promotable=True.
        R2-M01: Only fact_claim is eligible for promotion (whitelist).

        Provider-submitted promotable=True → unconditional ERROR.
        Claim type not in whitelist → ERROR.
        """
        findings: list[ValidationFinding] = []

        if isinstance(candidate, FactCandidate):
            if candidate.promotable:
                findings.append(ValidationFinding(
                    code="PROVIDER_SET_PROMOTABLE",
                    message=f"Provider cannot set promotable=True on "
                            f"FactCandidate {cid} — only ReviewDecision can",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "violation": "G2-1",
                        "rule": "provider_must_not_set_promotable",
                    },
                ))

        if isinstance(candidate, ClaimCandidate):
            ct = (candidate.claim_type or "").lower()
            if candidate.promotable_to_fact and ct not in self.PROMOTABLE_TYPES:
                findings.append(ValidationFinding(
                    code="NON_PROMOTABLE_CLAIM_TYPE",
                    message=f"ClaimCandidate type '{candidate.claim_type}' "
                            f"is not in promotable whitelist "
                            f"({sorted(self.PROMOTABLE_TYPES)})",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "claim_type": candidate.claim_type,
                        "promotable_types": sorted(self.PROMOTABLE_TYPES),
                        "statement": candidate.statement[:120],
                        "violation": "G2-1",
                    },
                ))

        return findings

    # ── B04: Fact Pollution via target_claim_id Graph ─────────────────────

    def _check_fact_claim_graph(
        self,
        candidate: Candidate,
        cid: str,
        candidate_index: dict[str, Candidate],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        if not isinstance(candidate, FactCandidate):
            return findings

        target_claim_id = candidate.target_claim_id
        if not target_claim_id:
            return findings

        linked_claim = candidate_index.get(target_claim_id)
        if linked_claim is None or not isinstance(linked_claim, ClaimCandidate):
            return findings

        claim_type = (linked_claim.claim_type or "").lower()

        # R2-M01: whitelist — only fact_claim is promotable
        if claim_type not in self.PROMOTABLE_TYPES:
            findings.append(ValidationFinding(
                code="FACT_POLLUTION_PREDICTION",
                message=f"FactCandidate {cid} references ClaimCandidate "
                        f"{target_claim_id} with non-promotable type "
                        f"'{linked_claim.claim_type}'",
                severity=FindingSeverity.ERROR,
                candidate_id=cid,
                gate_name="safety_gate",
                details={
                    "target_claim_id": target_claim_id,
                    "claim_type": linked_claim.claim_type,
                    "promotable_types": sorted(self.PROMOTABLE_TYPES),
                    "fact_statement": candidate.statement[:120],
                    "claim_statement": linked_claim.statement[:120],
                    "violation": "G2-1",
                    "detection": "target_claim_graph",
                },
            ))

        return findings

    # ── B05: Prompt Injection on FULL ContentUnit ─────────────────────────

    def _check_prompt_injection_full(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        if isinstance(candidate, EntityCandidate):
            return findings

        suid = getattr(candidate, "source_unit_id", "") or ""

        if not suid or suid not in self._window_unit_ids:
            return self._check_prompt_injection_candidate_fallback(candidate, cid)

        unit = self._window.get_unit_by_id(suid)
        if unit is None:
            return findings

        full_text = unit.text.lower()

        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern in full_text:
                if isinstance(candidate, FactCandidate):
                    findings.append(ValidationFinding(
                        code="PROMPT_INJECTION",
                        message=f"ContentUnit '{suid}' contains prompt injection "
                                f"pattern '{pattern}' — FactCandidate {cid} "
                                f"rejected",
                        severity=FindingSeverity.ERROR,
                        candidate_id=cid,
                        gate_name="safety_gate",
                        source_unit_id=suid,
                        details={
                            "pattern": pattern,
                            "source": "full_content_unit",
                            "unit_id": suid,
                            "violation": "G2-4",
                        },
                    ))
                else:
                    findings.append(ValidationFinding(
                        code="PROMPT_INJECTION",
                        message=f"ContentUnit '{suid}' contains prompt injection "
                                f"pattern '{pattern}' — treated as source text",
                        severity=FindingSeverity.INFO,
                        candidate_id=cid,
                        gate_name="safety_gate",
                        source_unit_id=suid,
                        details={
                            "pattern": pattern,
                            "source": "full_content_unit",
                            "unit_id": suid,
                            "handling": "treated_as_source_text",
                        },
                    ))
                break

        return findings

    def _check_prompt_injection_candidate_fallback(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        texts: list[str] = []
        if hasattr(candidate, "statement"):
            texts.append(candidate.statement or "")
        if hasattr(candidate, "source_quote"):
            texts.append(candidate.source_quote or "")
        if hasattr(candidate, "note"):
            texts.append(candidate.note or "")
        combined = " ".join(texts).lower()

        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern in combined:
                if isinstance(candidate, FactCandidate):
                    findings.append(ValidationFinding(
                        code="PROMPT_INJECTION",
                        message=f"Candidate contains prompt injection "
                                f"pattern '{pattern}' — FactCandidate rejected",
                        severity=FindingSeverity.ERROR,
                        candidate_id=cid,
                        gate_name="safety_gate",
                        details={
                            "pattern": pattern,
                            "source": "candidate_fields_fallback",
                            "violation": "G2-4",
                        },
                    ))
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
                            "source": "candidate_fields_fallback",
                            "handling": "treated_as_source_text",
                        },
                    ))
                break
        return findings

    # ── G2-6: High Confidence Pollution ───────────────────────────────────

    def _check_high_confidence_pollution(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
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

        if isinstance(candidate, FactCandidate) and candidate.promotable:
            findings.append(ValidationFinding(
                code="HIGH_CONFIDENCE_POLLUTION",
                message=f"FactCandidate with confidence={conf} "
                        f"and promotable=True — confidence must not "
                        f"drive knowledge status",
                severity=FindingSeverity.ERROR,
                candidate_id=cid,
                gate_name="safety_gate",
                details={"confidence": conf, "violation": "G2-6"},
            ))

        if isinstance(candidate, ClaimCandidate) and candidate.promotable_to_fact:
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

        return findings

    # ── Keyword-based Pollution (supplementary) ───────────────────────────

    def _check_keyword_pollution(
        self, candidate: Candidate, cid: str
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if not isinstance(candidate, FactCandidate):
            return findings

        statement = (candidate.statement or "").lower()
        prediction_keywords = ["预计", "预测", "预期", "预计将", "有望", "或将", "可能"]
        valuation_keywords = [
            "不建议", "建议买入", "建议卖出", "不建议买入", "不建议卖出",
            "估值", "合理价值", "目标价", "合理价格",
        ]

        for kw in prediction_keywords:
            if kw in statement:
                findings.append(ValidationFinding(
                    code="FACT_POLLUTION_PREDICTION",
                    message=f"FactCandidate contains prediction language "
                            f"('{kw}' in '{candidate.statement[:80]}')",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "statement": candidate.statement[:200],
                        "matched_keyword": kw,
                        "detection": "keyword",
                        "violation": "G2-1",
                    },
                ))
                return findings

        for kw in valuation_keywords:
            if kw in statement:
                findings.append(ValidationFinding(
                    code="FACT_POLLUTION_VALUATION",
                    message=f"FactCandidate contains valuation language "
                            f"('{kw}' in '{candidate.statement[:80]}')",
                    severity=FindingSeverity.ERROR,
                    candidate_id=cid,
                    gate_name="safety_gate",
                    details={
                        "statement": candidate.statement[:200],
                        "matched_keyword": kw,
                        "detection": "keyword",
                        "violation": "G2-1",
                    },
                ))
                return findings

        return findings

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _cid(candidate: Candidate) -> str:
        for attr in ("candidate_id", "id"):
            val = getattr(candidate, attr, None)
            if val:
                return str(val)
        return "unknown"
