"""Integration tests: M2-003B Gate 2 V2 — Cognitive Safety Validation.

Round 2 rework with B01-B07 + M01-M02 fixes.
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
from aurora.extraction.findings import FindingSeverity
from aurora.extraction.quote_gate import QuoteGate
from aurora.extraction.review_bundle import ReviewBundle
from aurora.extraction.safety_gate import SafetyGate

ADVERSARIAL_DIR = Path(__file__).parents[1] / "fixtures" / "m2_003" / "adversarial"
CU_DIR = ADVERSARIAL_DIR / "content_units"
PROVIDER_DIR = ADVERSARIAL_DIR / "provider_responses"
EXPECTED_DIR = ADVERSARIAL_DIR / "expected"

CASE_IDS = [
    "prediction_pollution", "valuation_recommendation",
    "prompt_injection", "high_confidence_pollution",
    "provider_independence_override",
]
FAKE_QUOTE_CASES = ["fake_quote", "forged_or_outside_unit"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_cus() -> list[ContentUnit]:
    path = CU_DIR / "adversarial_content_units.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    units = []
    for item in data:
        locator = SourceLocator(**item.get("locator", {"block_no": 0}))
        units.append(ContentUnit(
            id=item["unit_id"], document_id=item["document_id"],
            unit_type=item["unit_type"], sequence_no=item["sequence_no"],
            text=item["text"], locator=locator,
        ))
    return units


def _make_window():
    return ContextWindow.from_content_units("doc_adversarial", _load_cus())


def _load_provider(case_id: str) -> dict:
    file_map = {
        "prediction_pollution": "prediction_pollution_provider.json",
        "valuation_recommendation": "valuation_recommendation_provider.json",
        "prompt_injection": "prompt_injection_provider.json",
        "fake_quote": "fake_quote_provider.json",
        "forged_or_outside_unit": "forged_or_outside_unit_provider.json",
        "high_confidence_pollution": "high_confidence_pollution_provider.json",
        "provider_independence_override": "provider_independence_override_provider.json",
    }
    path = PROVIDER_DIR / file_map[case_id]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_expected(case_id: str) -> dict:
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


def _build_candidates(raw: dict):
    """Build candidates AND collect raw payloads."""
    candidates = []
    raw_payloads = []
    for item in raw.get("candidates", []):
        c_type = item.get("candidate_type", "")
        raw_payloads.append(dict(item))
        cid = item.get("candidate_id", "")
        if c_type == "entity":
            c = EntityCandidate(candidate_id=cid,
                                entity_type=item.get("entity_type", ""),
                                canonical_name=item.get("canonical_name", ""))
        elif c_type == "data_point":
            c = DataPointCandidate(candidate_id=cid,
                                   metric=item.get("metric", ""), value=item.get("value", 0.0),
                                   unit=item.get("unit", ""), entity_id=item.get("entity_id", ""),
                                   period=item.get("period", ""),
                                   measurement_context=item.get("measurement_context", {}),
                                   source_quote=item.get("source_quote", ""),
                                   quote_match_mode=item.get("quote_match_mode", "literal"),
                                   source_unit_id=item.get("source_unit_id", ""),
                                   note=item.get("note", ""))
        elif c_type == "claim":
            c = ClaimCandidate(candidate_id=cid,
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
                               confidence=item.get("confidence", 0.0))
        elif c_type == "evidence":
            c = EvidenceCandidate(candidate_id=cid,
                                  evidence_type=item.get("evidence_type", ""),
                                  evidence_role=item.get("evidence_role", ""),
                                  target_object_id=item.get("target_object_id", ""),
                                  independence_group=item.get("independence_group", ""),
                                  source_quote=item.get("source_quote", ""),
                                  quote_match_mode=item.get("quote_match_mode", "literal"),
                                  source_unit_id=item.get("source_unit_id", ""),
                                  note=item.get("note", ""))
        elif c_type == "fact":
            c = FactCandidate(candidate_id=cid,
                              statement=item.get("statement", ""),
                              promotable=item.get("promotable", False),
                              target_data_point_id=item.get("target_data_point_id"),
                              target_claim_id=item.get("target_claim_id"),
                              supporting_evidence_ids=item.get("supporting_evidence_ids", []),
                              valid_time=item.get("valid_time"),
                              rejection_reason=item.get("rejection_reason", ""),
                              source_quote=item.get("source_quote", ""),
                              quote_match_mode=item.get("quote_match_mode", "literal"),
                              source_unit_id=item.get("source_unit_id", ""),
                              confidence=item.get("confidence", 0.0))
        else:
            continue
        candidates.append(c)
    return candidates, raw_payloads


def _run_pipeline(case_id: str):
    """Full Gate 2 pipeline: QuoteGate → SafetyGate → ReviewBundle."""
    window = _make_window()
    raw = _load_provider(case_id)
    candidates, raw_payloads = _build_candidates(raw)

    qg = QuoteGate(window)
    qr = qg.validate(candidates)

    sg = SafetyGate(window, existing_findings=qr.findings)
    sr = sg.validate(candidates, raw_payloads=raw_payloads)

    all_findings = tuple(list(qr.findings) + sr.findings)
    bundle = ReviewBundle.create(
        document_id=window.document_id,
        provider_name="adversarial_fixture",
        provider_version="1.0",
        deterministic_mode=True,
        candidates=tuple(candidates),
        content_unit_window=window.units,
        validation_findings=all_findings,
        context_hashes={"window_sha256": window.window_sha256},
        case_id=case_id,
        run_id=f"run_{case_id}_test",  # Deterministic run_id for stable hash
    )
    return window, candidates, raw_payloads, sr, bundle


def _bundle_hash(bundle: ReviewBundle) -> str:
    return hashlib.sha256(
        f"{bundle.candidate_count}:{bundle.accepted_count}:{bundle.rejected_count}"
        f":{','.join(sorted(bundle.accepted_candidate_ids))}"
        f":{','.join(sorted(bundle.rejected_candidate_ids))}".encode()
    ).hexdigest()


# ── B06: ReviewBundle Integration ────────────────────────────────────────────

class TestReviewBundleIntegration:
    def test_accepted_rejected_match_expected(self):
        """B06: ReviewBundle accepted/rejected matches expected."""
        for case_id in CASE_IDS:
            _, _, _, sr, bundle = _run_pipeline(case_id)
            expected = _load_expected(case_id)
            for cid in expected["expected_rejected_candidate_ids"]:
                assert cid in bundle.rejected_candidate_ids, \
                    f"[{case_id}] Expected rejected {cid}"
            for cid in expected["expected_accepted_candidate_ids"]:
                assert cid not in bundle.rejected_candidate_ids, \
                    f"[{case_id}] Expected accepted {cid} was rejected"

    def test_bundle_hash_stable_10_runs(self):
        """B06: Bundle hash must be stable across 10 runs."""
        for case_id in CASE_IDS:
            hashes = []
            accepted_list = []
            rejected_list = []
            for _ in range(10):
                _, _, _, _, bundle = _run_pipeline(case_id)
                hashes.append(bundle.bundle_sha256)
                accepted_list.append(tuple(sorted(bundle.accepted_candidate_ids)))
                rejected_list.append(tuple(sorted(bundle.rejected_candidate_ids)))
            assert len(set(hashes)) == 1, f"[{case_id}] Bundle SHA256 not stable"
            assert len(set(accepted_list)) == 1, f"[{case_id}] Accepted set not stable"
            assert len(set(rejected_list)) == 1, f"[{case_id}] Rejected set not stable"


# ── Per-Scenario Tests ──────────────────────────────────────────────────────

class TestPredictionPollution:
    def test_rejected(self):
        _, _, _, sr, _ = _run_pipeline("prediction_pollution")
        expected = _load_expected("prediction_pollution")
        assert sr.fact_pollution_count == expected["expected_fact_pollution_count"]


class TestValuationPollution:
    def test_rejected(self):
        _, _, _, sr, _ = _run_pipeline("valuation_recommendation")
        expected = _load_expected("valuation_recommendation")
        assert sr.fact_pollution_count == expected["expected_fact_pollution_count"]


class TestPromptInjection:
    def test_full_content_unit_detected(self):
        _, _, _, sr, _ = _run_pipeline("prompt_injection")
        expected = _load_expected("prompt_injection")
        assert sr.prompt_injection_count == expected["expected_prompt_injection_count"]


class TestFakeQuote:
    def test_quote_gate_handles(self):
        """B07: Fake quote is QuoteGate's job."""
        window = _make_window()
        raw = _load_provider("fake_quote")
        candidates, _ = _build_candidates(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count == 1


class TestForgedUnit:
    def test_quote_gate_handles(self):
        """B07: Forged unit is QuoteGate's job."""
        window = _make_window()
        raw = _load_provider("forged_or_outside_unit")
        candidates, _ = _build_candidates(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count == 1


class TestHighConfidencePollution:
    def test_rejected(self):
        _, _, _, sr, _ = _run_pipeline("high_confidence_pollution")
        expected = _load_expected("high_confidence_pollution")
        assert sr.high_confidence_pollution_count == expected["expected_high_confidence_pollution_count"]
        assert sr.fact_pollution_count == expected["expected_fact_pollution_count"]


class TestProviderOverride:
    def test_raw_payload_forbidden_fields(self):
        """B01: Raw payload forbidden fields detected before DTO."""
        _, _, _, sr, _ = _run_pipeline("provider_independence_override")
        expected = _load_expected("provider_independence_override")
        assert sr.provider_override_count == expected["expected_provider_override_count"]

    def test_independence_group_not_flagged(self):
        """B02: independence_group NOT flagged as provider override."""
        window = _make_window()
        raw = _load_provider("provider_independence_override")
        candidates, raw_payloads = _build_candidates(raw)
        sg = SafetyGate(window)
        report = sg.validate(candidates, raw_payloads=raw_payloads)
        ig_findings = [f for f in report.findings
                       if f.code == "PROVIDER_OVERRIDE_FIELD"
                       and f.details.get("field") == "independence_group"]
        assert len(ig_findings) == 0


# ── B03: Provider Promotable ────────────────────────────────────────────────

class TestProviderPromotable:
    def test_provider_promotable_true_rejected(self):
        window = _make_window()
        fc = FactCandidate(candidate_id="fc_pp", statement="收入数据",
                           promotable=True,
                           source_quote="营业收入156.3亿元",
                           source_unit_id="adv_cu_004")
        sg = SafetyGate(window)
        report = sg.validate([fc])
        assert report.error_count >= 1
        pp_findings = [f for f in report.findings if f.code == "PROVIDER_SET_PROMOTABLE"]
        assert len(pp_findings) == 1
        assert "fc_pp" in report.rejected_candidate_ids


# ── B05: Substring Evasion ───────────────────────────────────────────────────

class TestSubstringEvasion:
    def test_safe_substring_still_detected(self):
        """B05: Full ContentUnit check catches injection prefix even when
        Provider extracts only safe substring."""
        window = _make_window()
        fc = FactCandidate(candidate_id="fc_evasion", statement="公司财务数据真实可靠",
                           promotable=False,
                           source_quote="公司财务数据真实可靠",
                           source_unit_id="adv_cu_003")
        sg = SafetyGate(window)
        report = sg.validate([fc])
        injection_errors = [f for f in report.findings
                           if f.code == "PROMPT_INJECTION"
                           and f.severity == FindingSeverity.ERROR]
        assert len(injection_errors) >= 1, "Substring evasion must be caught"


# ── Deterministic 10x ────────────────────────────────────────────────────────

class TestDeterministic10x:
    @pytest.mark.parametrize("case_id", CASE_IDS)
    def test_10x_stable(self, case_id):
        report_hashes = []
        accepted_sets = []
        rejected_sets = []
        for _ in range(10):
            _, _, _, sr, _ = _run_pipeline(case_id)
            finding_strs = sorted(f"{f.code}:{f.candidate_id}" for f in sr.findings)
            h = hashlib.sha256("|".join(finding_strs).encode()).hexdigest()
            report_hashes.append(h)
            accepted_sets.append(tuple(sorted(sr.accepted_candidate_ids)))
            rejected_sets.append(tuple(sorted(sr.rejected_candidate_ids)))
        assert len(set(report_hashes)) == 1, f"[{case_id}] Hash not stable"
        assert len(set(accepted_sets)) == 1, f"[{case_id}] Accepted not stable"
        assert len(set(rejected_sets)) == 1, f"[{case_id}] Rejected not stable"


# ── Comprehensive ────────────────────────────────────────────────────────────

class TestComprehensive:
    def test_all_scenarios_load(self):
        for case_id in CASE_IDS + FAKE_QUOTE_CASES:
            raw = _load_provider(case_id)
            assert "candidates" in raw
            assert len(raw["candidates"]) > 0

    def test_comprehensive(self):
        total_pollution = 0
        total_override = 0
        total_high_conf = 0
        total_injection = 0

        for case_id in CASE_IDS:
            _, _, _, sr, bundle = _run_pipeline(case_id)
            expected = _load_expected(case_id)

            assert sr.fact_pollution_count == expected["expected_fact_pollution_count"], \
                f"[{case_id}] Fact pollution mismatch"
            assert sr.prompt_injection_count == expected["expected_prompt_injection_count"], \
                f"[{case_id}] Prompt injection mismatch"
            assert sr.provider_override_count == expected["expected_provider_override_count"], \
                f"[{case_id}] Provider override mismatch"
            assert sr.high_confidence_pollution_count == expected["expected_high_confidence_pollution_count"], \
                f"[{case_id}] High conf mismatch"

            error_cids = set(bundle.rejected_candidate_ids)
            for cid in expected["expected_rejected_candidate_ids"]:
                assert cid in error_cids, f"[{case_id}] Expected rejected {cid}"
            for cid in expected["expected_accepted_candidate_ids"]:
                assert cid not in error_cids, f"[{case_id}] Expected accepted {cid}"

            total_pollution += sr.fact_pollution_count
            total_override += sr.provider_override_count
            total_high_conf += sr.high_confidence_pollution_count
            total_injection += sr.prompt_injection_count

        assert total_pollution > 0
        assert total_override > 0
        assert total_high_conf > 0
        assert total_injection > 0

    def test_input_not_modified(self):
        all_cases = CASE_IDS + FAKE_QUOTE_CASES
        for case_id in all_cases:
            window_before = _make_window()
            texts_before = {u.unit_id: u.text for u in window_before.units}

            raw = _load_provider(case_id)
            candidates, raw_payloads = _build_candidates(raw)
            qg = QuoteGate(window_before)
            qr = qg.validate(candidates)
            sg = SafetyGate(window_before, existing_findings=qr.findings)
            sg.validate(candidates, raw_payloads=raw_payloads)

            for u in window_before.units:
                assert u.text == texts_before[u.unit_id], f"[{case_id}] Unit modified"


# ── Hard Gates ───────────────────────────────────────────────────────────────

class TestHardGates:
    def test_g2_1_fact_pollution(self):
        for case_id in ["prediction_pollution", "valuation_recommendation"]:
            _, _, _, _, bundle = _run_pipeline(case_id)
            expected = _load_expected(case_id)
            for cid in expected["expected_rejected_candidate_ids"]:
                assert cid in bundle.rejected_candidate_ids

    def test_g2_2_fake_quote(self):
        window = _make_window()
        raw = _load_provider("fake_quote")
        candidates, _ = _build_candidates(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count >= 1

    def test_g2_3_forged_unit(self):
        window = _make_window()
        raw = _load_provider("forged_or_outside_unit")
        candidates, _ = _build_candidates(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count >= 1

    def test_g2_4_prompt_injection(self):
        _, _, _, sr, _ = _run_pipeline("prompt_injection")
        pi_errors = [f for f in sr.findings
                     if f.code == "PROMPT_INJECTION" and f.severity == FindingSeverity.ERROR]
        assert len(pi_errors) > 0

    def test_g2_5_provider_override(self):
        _, _, _, sr, _ = _run_pipeline("provider_independence_override")
        ov_errors = [f for f in sr.findings
                     if f.code == "PROVIDER_OVERRIDE_FIELD" and f.severity == FindingSeverity.ERROR]
        assert len(ov_errors) > 0

    def test_g2_6_high_confidence(self):
        _, _, _, sr, _ = _run_pipeline("high_confidence_pollution")
        hc = [f for f in sr.findings if f.code == "HIGH_CONFIDENCE_POLLUTION"]
        assert len(hc) > 0


# ── Regression ───────────────────────────────────────────────────────────────

class TestRegression:
    def test_imports(self):
        from aurora.extraction import SafetyGate, SafetyGateReport, QuoteGate
        assert SafetyGate is not None

    def test_normal_evidence_not_rejected(self):
        """B02: Normal EvidenceCandidate with independence_group must pass."""
        window = _make_window()
        ev = EvidenceCandidate(candidate_id="ev_normal", evidence_type="source_document",
                               evidence_role="support", target_object_id="cl_1",
                               independence_group="case_a_group",
                               source_quote="公司实现营业收入156.3亿元",
                               source_unit_id="adv_cu_004")
        sg = SafetyGate(window)
        report = sg.validate([ev])
        assert report.error_count == 0, "Normal Evidence must not be rejected"
        assert "ev_normal" in report.accepted_candidate_ids
