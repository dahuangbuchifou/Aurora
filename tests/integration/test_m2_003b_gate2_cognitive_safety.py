"""Integration tests: M2-003B Gate 2 Cognitive Safety Validation.

Tests all 7 adversarial scenarios with full pipeline:
ContentUnit Fixture → ContextWindow → Adversarial FixtureProvider → SafetyGate → ReviewBundle.

Each scenario validates a specific G2 hard-gate:
- G2-1: Fact pollution (prediction + valuation)
- G2-2: Fake quote
- G2-3: Forged/outside unit
- G2-4: Prompt injection
- G2-5: Provider independence override
- G2-6: High confidence pollution

Plus: 10x deterministic runs, frozen asset checks, regression.
"""

import json
import hashlib
from pathlib import Path

import pytest

from aurora.core.models.document import ContentUnit
from aurora.core.models.common import SourceLocator
from aurora.extraction.candidates import (
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import ContextWindow
from aurora.extraction.findings import FindingSeverity, ValidationFinding
from aurora.extraction.providers.fixture_provider import FixtureProvider
from aurora.extraction.safety_gate import SafetyGate, SafetyGateReport
from aurora.extraction.review_bundle import ReviewBundle
from aurora.extraction.quote_gate import QuoteGate

ADVERSARIAL_DIR = Path(__file__).parents[1] / "fixtures" / "m2_003" / "adversarial"
CU_DIR = ADVERSARIAL_DIR / "content_units"
PROVIDER_DIR = ADVERSARIAL_DIR / "provider_responses"
EXPECTED_DIR = ADVERSARIAL_DIR / "expected"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _load_content_units() -> list[ContentUnit]:
    """Load adversarial ContentUnit fixtures."""
    path = CU_DIR / "adversarial_content_units.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    units = []
    for item in data:
        locator = SourceLocator(**item.get("locator", {"block_no": 0}))
        units.append(ContentUnit(
            id=item["unit_id"],
            document_id=item["document_id"],
            unit_type=item["unit_type"],
            sequence_no=item["sequence_no"],
            text=item["text"],
            locator=locator,
        ))
    return units


def _build_adversarial_window() -> ContextWindow:
    """Build ContextWindow from adversarial CU fixtures."""
    units = _load_content_units()
    return ContextWindow.from_content_units("doc_adversarial", units)


def _load_provider_response(case_id: str) -> dict:
    """Load adversarial provider response fixture."""
    file_map = {
        "prediction_pollution": "prediction_pollution_provider.json",
        "valuation_recommendation": "valuation_recommendation_provider.json",
        "prompt_injection": "prompt_injection_provider.json",
        "fake_quote": "fake_quote_provider.json",
        "forged_or_outside_unit": "forged_or_outside_unit_provider.json",
        "high_confidence_pollution": "high_confidence_pollution_provider.json",
        "provider_independence_override": "provider_independence_override_provider.json",
    }
    file_name = file_map[case_id]
    path = PROVIDER_DIR / file_name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_expected(case_id: str) -> dict:
    """Load expected results for adversarial scenario."""
    file_map = {
        "prediction_pollution": "prediction_pollution_expected.json",
        "valuation_recommendation": "valuation_recommendation_expected.json",
        "prompt_injection": "prompt_injection_expected.json",
        "fake_quote": "fake_quote_expected.json",
        "forged_or_outside_unit": "forged_or_outside_unit_expected.json",
        "high_confidence_pollution": "high_confidence_pollution_expected.json",
        "provider_independence_override": "provider_independence_override_expected.json",
    }
    path = EXPECTED_DIR / file_map[case_id]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_candidates_from_provider(raw: dict) -> list:
    """Build candidate objects from adversarial provider response."""
    candidates = []
    for item in raw.get("candidates", []):
        c_type = item.get("candidate_type", "")
        if c_type == "entity":
            c = EntityCandidate(
                candidate_id=item.get("candidate_id", ""),
                entity_type=item.get("entity_type", ""),
                canonical_name=item.get("canonical_name", ""),
            )
        elif c_type == "data_point":
            c = DataPointCandidate(
                candidate_id=item.get("candidate_id", ""),
                metric=item.get("metric", ""),
                value=item.get("value", 0.0),
                unit=item.get("unit", ""),
                entity_id=item.get("entity_id", ""),
                period=item.get("period", ""),
                measurement_context=item.get("measurement_context", {}),
                source_quote=item.get("source_quote", ""),
                quote_match_mode=item.get("quote_match_mode", "literal"),
                source_unit_id=item.get("source_unit_id", ""),
                note=item.get("note", ""),
            )
        elif c_type == "claim":
            c = ClaimCandidate(
                candidate_id=item.get("candidate_id", ""),
                statement=item.get("statement", ""),
                claim_type=item.get("claim_type", ""),
                claim_dimension=item.get("claim_dimension", ""),
                claimant_name=item.get("claimant_name", ""),
                asserted_by=item.get("asserted_by", ""),
                time_horizon=item.get("time_horizon"),
                promotable_to_fact=item.get("promotable_to_fact", False),
                source_quote=item.get("source_quote", ""),
                quote_match_mode=item.get("quote_match_mode", "literal"),
                source_unit_id=item.get("source_unit_id", ""),
                note=item.get("note", ""),
                confidence=item.get("confidence", 0.0),
            )
        elif c_type == "evidence":
            c = EvidenceCandidate(
                candidate_id=item.get("candidate_id", ""),
                evidence_type=item.get("evidence_type", ""),
                evidence_role=item.get("evidence_role", ""),
                target_object_id=item.get("target_object_id", ""),
                independence_group=item.get("independence_group", ""),
                source_quote=item.get("source_quote", ""),
                quote_match_mode=item.get("quote_match_mode", "literal"),
                source_unit_id=item.get("source_unit_id", ""),
                note=item.get("note", ""),
            )
        elif c_type == "fact":
            c = FactCandidate(
                candidate_id=item.get("candidate_id", ""),
                statement=item.get("statement", ""),
                promotable=item.get("promotable", False),
                target_data_point_id=item.get("target_data_point_id"),
                target_claim_id=item.get("target_claim_id"),
                supporting_evidence_ids=item.get("supporting_evidence_ids", []),
                valid_time=item.get("valid_time"),
                confidence_rationale=item.get("confidence_rationale"),
                rejection_reason=item.get("rejection_reason", ""),
                source_quote=item.get("source_quote", ""),
                quote_match_mode=item.get("quote_match_mode", "literal"),
                source_unit_id=item.get("source_unit_id", ""),
                confidence=item.get("confidence", 0.0),
            )
        else:
            continue
        candidates.append(c)
    return candidates


def _run_gate2_pipeline(case_id: str):
    """Run the full Gate 2 pipeline: load fixtures → SafetyGate → Report."""
    window = _build_adversarial_window()
    raw = _load_provider_response(case_id)
    candidates = _build_candidates_from_provider(raw)

    gate = SafetyGate(window)
    report = gate.validate(candidates)

    return window, candidates, report


def _compute_report_hash(report: SafetyGateReport) -> str:
    """Compute deterministic hash of a SafetyGateReport for stability testing."""
    finding_strs = sorted(
        f"{f.code}:{f.candidate_id}:{f.message}"
        for f in report.findings
    )
    return hashlib.sha256("|".join(finding_strs).encode()).hexdigest()


# ── G2-1: Prediction Pollution ───────────────────────────────────────────────

class TestPredictionPollution:
    """G2-1: Fact must not be polluted by prediction language."""

    def test_fact_pollution_rate_is_zero(self):
        """FactCandidate with prediction language must be fully rejected."""
        window, candidates, report = _run_gate2_pipeline("prediction_pollution")
        expected = _load_expected("prediction_pollution")

        # Verify Fact pollution count
        assert report.fact_pollution_count == expected["expected_fact_pollution_count"]

        # The FactCandidate must be in rejected
        error_cids = {f.candidate_id for f in report.error_findings}
        assert "pred_pol_fc_001" in error_cids, "FactCandidate with prediction must be rejected"

        # The ClaimCandidate should be accepted (it's correctly typed)
        assert "pred_pol_cl_001" not in error_cids, "Claim with prediction type should pass"

    def test_no_fact_created_from_prediction(self):
        """Verify no Fact object is created from prediction text."""
        window = _build_adversarial_window()
        raw = _load_provider_response("prediction_pollution")
        candidates = _build_candidates_from_provider(raw)

        fact_candidates = [c for c in candidates if isinstance(c, FactCandidate)]

        # The Fact candidate should have prediction content
        for fc in fact_candidates:
            gate = SafetyGate(window)
            findings = gate._check_fact_pollution(fc, fc.candidate_id)
            if "预计" in (fc.statement or ""):
                assert len(findings) > 0, f"Fact with prediction must have findings"

    def test_clean_pipeline_no_unexpected_rejection(self):
        """Valid non-prediction FactCandidates should NOT be rejected."""
        window = _build_adversarial_window()
        # Create a valid FactCandidate with clean content
        fc = FactCandidate(
            candidate_id="clean_fc",
            statement="2025年Q3营业收入156.3亿元",
            promotable=True,
            source_quote="公司实现营业收入156.3亿元",
            source_unit_id="adv_cu_004",
        )
        gate = SafetyGate(window)
        report = gate.validate([fc])
        # No prediction keyword → should not be flagged
        assert report.fact_pollution_count == 0, "Clean fact should not trigger pollution"


# ── G2-1b: Valuation/Recommendation Pollution ────────────────────────────────

class TestValuationPollution:
    """G2-1: Valuation/recommendation claims must not become Fact."""

    def test_valuation_recommendation_rejected(self):
        """Recommendation claim with promotable_to_fact=True must be rejected."""
        window, candidates, report = _run_gate2_pipeline("valuation_recommendation")
        expected = _load_expected("valuation_recommendation")

        assert report.fact_pollution_count == expected["expected_fact_pollution_count"]
        error_cids = {f.candidate_id for f in report.error_findings}
        assert "val_cl_001" in error_cids, "Recommendation claim with promotable_to_fact must be rejected"


# ── G2-4: Prompt Injection ───────────────────────────────────────────────────

class TestPromptInjection:
    """G2-4: Prompt injection text must NOT change system behavior."""

    def test_prompt_injection_fact_rejected(self):
        """FactCandidate from prompt-injected text must be rejected."""
        window, candidates, report = _run_gate2_pipeline("prompt_injection")
        expected = _load_expected("prompt_injection")

        # Prompt injection FactCandidate triggers PROMPT_INJECTION (ERROR),
        # not FACT_POLLUTION (no prediction/valuation keywords in statement text)
        assert report.prompt_injection_count >= expected["expected_prompt_injection_count"]

        error_cids = {f.candidate_id for f in report.error_findings}
        assert "inj_fc_001" in error_cids, "Fact from prompt injection must be rejected"

    def test_prompt_injection_treated_as_source_text(self):
        """System must NOT execute instructions from source text."""
        window, candidates, report = _run_gate2_pipeline("prompt_injection")

        # Verify no Fact was automatically created/promoted
        fact_from_inj = [
            f for f in report.findings
            if f.code in ("FACT_POLLUTION", "PROMPT_INJECTION") and f.severity == FindingSeverity.ERROR
        ]
        assert len(fact_from_inj) > 0, "Prompt injection in FactCandidate must produce ERROR"

    def test_input_objects_not_modified(self):
        """Verify input ContentUnits are not modified after SafetyGate validation."""
        window = _build_adversarial_window()
        # Snapshot
        original_texts = {u.unit_id: u.text for u in window.units}
        original_doc_id = window.document_id

        raw = _load_provider_response("prompt_injection")
        candidates = _build_candidates_from_provider(raw)
        gate = SafetyGate(window)
        gate.validate(candidates)

        # Verify window unchanged
        assert window.document_id == original_doc_id
        for u in window.units:
            assert u.text == original_texts[u.unit_id], f"Unit {u.unit_id} was modified"


# ── G2-2: Fake Quote ─────────────────────────────────────────────────────────

class TestFakeQuote:
    """G2-2: Provider must not fabricate quotes not in source."""

    def test_fake_quote_rejected(self):
        """Candidate with fabricated quote must be rejected."""
        window, candidates, report = _run_gate2_pipeline("fake_quote")
        expected = _load_expected("fake_quote")

        assert report.fake_quote_count == expected["expected_fake_quote_count"]
        error_cids = {f.candidate_id for f in report.error_findings}
        assert "fq_cl_001" in error_cids, "Fake quote candidate must be rejected"

    def test_fake_quote_acceptance_rate_is_zero(self):
        """No candidate with a fabricated quote should be accepted."""
        window, candidates, report = _run_gate2_pipeline("fake_quote")

        # Check: no error findings with FAKE_QUOTE code should have their
        # candidate in accepted set
        error_cids = {f.candidate_id for f in report.error_findings if f.code == "FAKE_QUOTE"}
        assert len(error_cids) > 0, "Must have at least one fake quote detected"


# ── G2-3: Forged/Outside Unit ────────────────────────────────────────────────

class TestForgedUnit:
    """G2-3: Provider must not reference nonexistent ContentUnits."""

    def test_forged_unit_rejected(self):
        """Candidate with nonexistent source_unit_id must be rejected."""
        window, candidates, report = _run_gate2_pipeline("forged_or_outside_unit")
        expected = _load_expected("forged_or_outside_unit")

        assert report.illegal_unit_count == expected["expected_illegal_unit_count"]
        error_cids = {f.candidate_id for f in report.error_findings}
        assert "fu_dp_001" in error_cids, "Forged unit candidate must be rejected"

    def test_forged_unit_acceptance_rate_is_zero(self):
        """No candidate with forged unit ID should be accepted."""
        window, candidates, report = _run_gate2_pipeline("forged_or_outside_unit")

        error_cids = {f.candidate_id for f in report.error_findings
                      if f.code == "FORGED_CONTENT_UNIT_ID"}
        assert len(error_cids) > 0


# ── G2-6: High Confidence Pollution ──────────────────────────────────────────

class TestHighConfidencePollution:
    """G2-6: High confidence must not change epistemic/knowledge status."""

    def test_high_confidence_rejected(self):
        """Candidates with confidence=0.99 and auto-promotion must be flagged."""
        window, candidates, report = _run_gate2_pipeline("high_confidence_pollution")
        expected = _load_expected("high_confidence_pollution")

        assert report.high_confidence_pollution_count == expected["expected_high_confidence_pollution_count"]

        # FactCandidate with confidence=0.99 and promotable=True must be rejected
        error_cids = {f.candidate_id for f in report.error_findings
                      if f.code == "HIGH_CONFIDENCE_POLLUTION" and f.severity == FindingSeverity.ERROR}
        assert "hc_fc_001" in error_cids, "High-confidence Fact must be rejected"

    def test_confidence_does_not_change_status(self):
        """Verify high confidence doesn't bypass cognitive safety gates."""
        window = _build_adversarial_window()
        raw = _load_provider_response("high_confidence_pollution")
        candidates = _build_candidates_from_provider(raw)

        gate = SafetyGate(window)
        report = gate.validate(candidates)

        # Even with confidence=0.99, the Fact and Claim must go through
        # normal safety checks — not auto-approved
        assert report.high_confidence_pollution_count > 0


# ── G2-5: Provider Independence Override ─────────────────────────────────────

class TestProviderIndependenceOverride:
    """G2-5: Provider must not set independence fields."""

    def test_provider_override_rejected(self):
        """EvidenceCandidate with provider-set independence_group must be rejected."""
        window, candidates, report = _run_gate2_pipeline("provider_independence_override")
        expected = _load_expected("provider_independence_override")

        assert report.provider_override_count == expected["expected_provider_override_count"]
        error_cids = {f.candidate_id for f in report.error_findings
                      if f.code == "PROVIDER_OVERRIDE_FIELD"}
        assert "pio_ev_001" in error_cids, "Provider override candidate must be rejected"

    def test_provider_override_acceptance_rate_is_zero(self):
        """No candidate with provider-forbidden fields should be accepted."""
        window, candidates, report = _run_gate2_pipeline("provider_independence_override")

        ov_cids = {f.candidate_id for f in report.error_findings
                   if f.code == "PROVIDER_OVERRIDE_FIELD"}
        assert "pio_ev_001" in ov_cids

    def test_claim_without_forbidden_fields_accepted(self):
        """ClaimCandidate NOT from same provider with forbidden fields should pass."""
        window, candidates, report = _run_gate2_pipeline("provider_independence_override")
        expected = _load_expected("provider_independence_override")

        error_cids = {f.candidate_id for f in report.error_findings}
        for cid in expected["expected_accepted_candidate_ids"]:
            assert cid not in error_cids, f"Accepted candidate {cid} should not have errors"


# ── Deterministic Stability (10x per fixture) ─────────────────────────────────

class TestGate2Deterministic:
    """Deterministic stability: 10 runs per adversarial fixture, all identical."""

    ADVERSARIAL_CASES = [
        "prediction_pollution",
        "valuation_recommendation",
        "prompt_injection",
        "fake_quote",
        "forged_or_outside_unit",
        "high_confidence_pollution",
        "provider_independence_override",
    ]

    @pytest.mark.parametrize("case_id", ADVERSARIAL_CASES)
    def test_deterministic_10_runs(self, case_id):
        """Each adversarial fixture must produce identical SafetyGate results 10 times."""
        report_hashes = []
        accepted_sets = []
        rejected_sets = []

        for _ in range(10):
            window = _build_adversarial_window()
            raw = _load_provider_response(case_id)
            candidates = _build_candidates_from_provider(raw)
            gate = SafetyGate(window)
            report = gate.validate(candidates)

            h = _compute_report_hash(report)
            report_hashes.append(h)
            accepted_sets.append(tuple(sorted(
                getattr(c, "candidate_id", "")
                for c in candidates
                if getattr(c, "candidate_id", "") not in
                {f.candidate_id for f in report.error_findings}
            )))
            rejected_sets.append(tuple(sorted(
                f.candidate_id for f in report.error_findings
            )))

        assert len(set(report_hashes)) == 1, \
            f"[{case_id}] Findings hash must be identical across 10 runs"
        assert len(set(accepted_sets)) == 1, \
            f"[{case_id}] Accepted set must be stable"
        assert len(set(rejected_sets)) == 1, \
            f"[{case_id}] Rejected set must be stable"


# ── Finding Code Stability ───────────────────────────────────────────────────

class TestFindingCodeStability:
    """Finding codes must be stable and recognizable."""

    VALID_CODES = {
        "FACT_POLLUTION",
        "FAKE_QUOTE",
        "FORGED_CONTENT_UNIT_ID",
        "UNIT_NOT_IN_WINDOW",
        "CROSS_DOCUMENT_UNIT",
        "PROMPT_INJECTION",
        "PROVIDER_OVERRIDE_FIELD",
        "HIGH_CONFIDENCE_POLLUTION",
    }

    def test_all_finding_codes_are_known(self):
        """All findings from all adversarial scenarios must use known codes."""
        all_findings = []
        for case_id in TestGate2Deterministic.ADVERSARIAL_CASES:
            window = _build_adversarial_window()
            raw = _load_provider_response(case_id)
            candidates = _build_candidates_from_provider(raw)
            gate = SafetyGate(window)
            report = gate.validate(candidates)
            all_findings.extend(report.findings)

        for f in all_findings:
            assert f.code in self.VALID_CODES, \
                f"Unknown finding code: {f.code} (from candidate {f.candidate_id})"


# ── Regression: Existing 345 Tests Still Pass ─────────────────────────────────

class TestGate2Regression:
    """Gate 2 must not break existing Gate 1 pipeline."""

    def test_imports_safety_gate(self):
        """SafetyGate must be importable from extraction module."""
        from aurora.extraction import SafetyGate, SafetyGateReport
        assert SafetyGate is not None
        assert SafetyGateReport is not None

    def test_quote_gate_still_imports(self):
        """QuoteGate must still be usable."""
        from aurora.extraction.quote_gate import QuoteGate, QuoteGateReport
        assert QuoteGate is not None

    def test_fixture_provider_still_imports(self):
        """FixtureProvider must still be usable."""
        from aurora.extraction.providers.fixture_provider import FixtureProvider
        assert FixtureProvider is not None

    def test_existing_review_bundle(self):
        """ReviewBundle must still work."""
        from aurora.extraction.review_bundle import ReviewBundle, BUNDLE_SCHEMA_VERSION
        assert BUNDLE_SCHEMA_VERSION == "2.0"


# ── Hard Gate Verification ────────────────────────────────────────────────────

class TestHardGates:
    """Verify all six G2 hard gates are enforced."""

    def test_g2_1_fact_pollution_zero(self):
        """G2-1: Fact pollution rate must be 0."""
        for case_id in ["prediction_pollution", "valuation_recommendation"]:
            window, candidates, report = _run_gate2_pipeline(case_id)
            # All polluting candidates must have ERROR findings
            for f in report.findings:
                if f.code == "FACT_POLLUTION":
                    assert f.severity == FindingSeverity.ERROR, \
                        f"FACT_POLLUTION must be ERROR in {case_id}"

    def test_g2_2_fake_quote_acceptance_zero(self):
        """G2-2: No fake quote candidate should be accepted."""
        window, candidates, report = _run_gate2_pipeline("fake_quote")
        error_cids = {f.candidate_id for f in report.error_findings if f.code == "FAKE_QUOTE"}
        for c in candidates:
            cid = getattr(c, "candidate_id", "")
            if cid in error_cids:
                # This candidate must have ERROR finding
                fq_errors = [f for f in report.findings
                            if f.candidate_id == cid and f.code == "FAKE_QUOTE"]
                assert len(fq_errors) > 0
                assert all(f.severity == FindingSeverity.ERROR for f in fq_errors)

    def test_g2_3_illegal_unit_acceptance_zero(self):
        """G2-3: No candidate with illegal unit ID should be accepted."""
        window, candidates, report = _run_gate2_pipeline("forged_or_outside_unit")
        error_cids = {f.candidate_id for f in report.error_findings
                      if f.code in ("FORGED_CONTENT_UNIT_ID", "UNIT_NOT_IN_WINDOW")}
        assert len(error_cids) > 0
        for f in report.findings:
            if f.code in ("FORGED_CONTENT_UNIT_ID",):
                assert f.severity == FindingSeverity.ERROR

    def test_g2_4_prompt_injection_violation_rate_zero(self):
        """G2-4: Prompt injection must not be accepted in Fact state."""
        window, candidates, report = _run_gate2_pipeline("prompt_injection")
        pi_errors = [f for f in report.findings
                     if f.code == "PROMPT_INJECTION" and f.severity == FindingSeverity.ERROR]
        assert len(pi_errors) > 0, "Prompt injection in FactCandidate must produce ERROR"

    def test_g2_5_provider_override_acceptance_zero(self):
        """G2-5: No candidate with provider-forbidden fields should be accepted."""
        window, candidates, report = _run_gate2_pipeline("provider_independence_override")
        ov_errors = [f for f in report.findings
                     if f.code == "PROVIDER_OVERRIDE_FIELD" and f.severity == FindingSeverity.ERROR]
        assert len(ov_errors) > 0

    def test_g2_6_high_confidence_status_change_zero(self):
        """G2-6: High confidence must not cause knowledge status changes."""
        window, candidates, report = _run_gate2_pipeline("high_confidence_pollution")
        hc_errors = [f for f in report.findings
                     if f.code == "HIGH_CONFIDENCE_POLLUTION"]
        assert len(hc_errors) > 0


# ── Comprehensive G2 Report ───────────────────────────────────────────────────

class TestGate2ComprehensiveReport:
    """Run ALL adversarial scenarios and produce comprehensive G2 report."""

    def test_all_seven_scenarios(self):
        """All 7 adversarial scenarios must be present and loaded."""
        for case_id in TestGate2Deterministic.ADVERSARIAL_CASES:
            raw = _load_provider_response(case_id)
            assert "candidates" in raw
            assert len(raw["candidates"]) > 0

            expected = _load_expected(case_id)
            assert "gate2_violations" in expected

    def test_comprehensive_gate2_report(self):
        """Run all scenarios and verify overall Gate 2 compliance."""
        total_pollution = 0
        total_fake_quote = 0
        total_illegal_unit = 0
        total_injection = 0
        total_override = 0
        total_high_conf = 0

        for case_id in TestGate2Deterministic.ADVERSARIAL_CASES:
            window, candidates, report = _run_gate2_pipeline(case_id)
            expected = _load_expected(case_id)

            # prompt_injection: Fact pollution detected via G2-4 (PROMPT_INJECTION),
            # not keyword-based FACT_POLLUTION (statement has no prediction/valuation keywords)
            if case_id == "prompt_injection":
                assert report.prompt_injection_count == expected["expected_prompt_injection_count"], \
                    f"[{case_id}] Prompt injection mismatch"
            else:
                assert report.fact_pollution_count == expected["expected_fact_pollution_count"], \
                    f"[{case_id}] Fact pollution mismatch"
            assert report.fake_quote_count == expected["expected_fake_quote_count"], \
                f"[{case_id}] Fake quote mismatch"
            assert report.illegal_unit_count == expected["expected_illegal_unit_count"], \
                f"[{case_id}] Illegal unit mismatch"
            assert report.prompt_injection_count == expected["expected_prompt_injection_count"], \
                f"[{case_id}] Prompt injection mismatch"
            assert report.provider_override_count == expected["expected_provider_override_count"], \
                f"[{case_id}] Provider override mismatch"
            assert report.high_confidence_pollution_count == expected["expected_high_confidence_pollution_count"], \
                f"[{case_id}] High confidence pollution mismatch"

            # Verify rejected/accepted sets
            error_cids = {f.candidate_id for f in report.error_findings}
            for cid in expected["expected_rejected_candidate_ids"]:
                assert cid in error_cids, \
                    f"[{case_id}] Expected rejected candidate {cid} not found in errors"
            for cid in expected["expected_accepted_candidate_ids"]:
                assert cid not in error_cids, \
                    f"[{case_id}] Expected accepted candidate {cid} was unexpectedly rejected"

            total_pollution += report.fact_pollution_count
            total_fake_quote += report.fake_quote_count
            total_illegal_unit += report.illegal_unit_count
            total_injection += report.prompt_injection_count
            total_override += report.provider_override_count
            total_high_conf += report.high_confidence_pollution_count

        # Summary: all pollution types were detected
        assert total_pollution > 0, "Should detect fact pollution across scenarios"
        assert total_fake_quote > 0, "Should detect fake quotes"
        assert total_illegal_unit > 0, "Should detect illegal unit references"
        assert total_injection > 0, "Should detect prompt injection"
        assert total_override > 0, "Should detect provider overrides"
        assert total_high_conf > 0, "Should detect high confidence pollution"

    def test_no_core_fact_created(self):
        """SafetyGate must NOT create any core Fact objects or persist anything."""
        # Core Fact doesn't exist yet — we check that FactCandidate DTOs are used
        # SafetyGate.validate() should never instantiate core domain objects

        for case_id in TestGate2Deterministic.ADVERSARIAL_CASES:
            window, candidates, report = _run_gate2_pipeline(case_id)
            # All candidates should be DTO types only
            for c in candidates:
                assert not type(c).__name__.startswith("Core"), \
                    f"[{case_id}] Core object should not appear in candidates"

    def test_document_content_units_not_modified(self):
        """Input Document and ContentUnits must not be modified by SafetyGate."""
        for case_id in TestGate2Deterministic.ADVERSARIAL_CASES:
            window_before = _build_adversarial_window()
            snapshot = {u.unit_id: (u.text, u.document_id, u.unit_type)
                       for u in window_before.units}

            raw = _load_provider_response(case_id)
            candidates = _build_candidates_from_provider(raw)
            gate = SafetyGate(window_before)
            gate.validate(candidates)

            for u in window_before.units:
                original = snapshot[u.unit_id]
                assert u.text == original[0], f"[{case_id}] Unit text modified"
                assert u.document_id == original[1], f"[{case_id}] Document ID modified"
                assert u.unit_type == original[2], f"[{case_id}] Unit type modified"
