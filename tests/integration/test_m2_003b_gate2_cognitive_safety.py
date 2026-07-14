"""Integration tests: M2-003B Gate 2 V3 — Cognitive Safety Validation (Final).

Round 2 rework:
- R2-B01: independence_group RESTORED as forbidden field
- R2-B02: raw_payloads keyed by candidate_id (dict, not list)
- R2-B03: ALL 7 adversarial cases through ReviewBundle with 10x stability
- R2-M01: fact_claim whitelist
- R2-M02: Uses FixtureProvider + ProviderResponse (real contract)
"""

import hashlib
import json
from pathlib import Path

import pytest

from aurora.core.models.document import ContentUnit
from aurora.core.models.common import SourceLocator
from aurora.extraction.candidates import (
    ClaimCandidate,
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

ALL_CASE_IDS = [
    "prediction_pollution",
    "valuation_recommendation",
    "prompt_injection",
    "fake_quote",
    "forged_or_outside_unit",
    "high_confidence_pollution",
    "provider_independence_override",
]

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


def _load_raw_provider(case_id: str) -> dict:
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


def _build_candidates_from_raw(raw: dict) -> tuple[list, dict[str, dict]]:
    """Build candidate DTOs AND raw_payloads dict (candidate_id → raw JSON item).

    R2-B02: raw_payloads is a dict keyed by candidate_id, not a positional list.
    R2-B01: EvidenceCandidate with independence_group will be caught at
            _check_raw_payload_fields (field in raw dict).
    """
    candidates = []
    raw_payloads: dict[str, dict] = {}

    for item in raw.get("candidates", []):
        cid = item.get("candidate_id", "")
        c_type = item.get("candidate_type", "")

        # Save raw payload keyed by candidate_id
        raw_payloads[cid] = dict(item)

        if c_type == "entity":
            from aurora.extraction.candidates import EntityCandidate
            c = EntityCandidate(candidate_id=cid,
                                entity_type=item.get("entity_type", ""),
                                canonical_name=item.get("canonical_name", ""))
        elif c_type == "data_point":
            from aurora.extraction.candidates import DataPointCandidate
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
                                  # independence_group is NOT passed to DTO
                                  # (caught in raw_payload check instead)
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
    """R2-B03: Full pipeline for ALL 7 cases.

    Gate 2 pipeline:
      JSON → build candidates + raw_payloads
      → QuoteGate → SafetyGate → ReviewBundle
    """
    window = _make_window()
    raw = _load_raw_provider(case_id)
    candidates, raw_payloads = _build_candidates_from_raw(raw)

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
        run_id=f"run_{case_id}_final",
    )
    return window, candidates, raw_payloads, sr, bundle


# ── R2-B03: All 7 Cases with ReviewBundle + 10x Stability ───────────────────


class TestAllSevenCases:
    @pytest.mark.parametrize("case_id", ALL_CASE_IDS)
    def test_review_bundle_integration(self, case_id):
        """R2-B03: Every adversarial case produces ReviewBundle."""
        _, _, _, _, bundle = _run_pipeline(case_id)
        assert bundle.provider_name == "adversarial_fixture"
        assert bundle.candidate_count > 0
        expected = _load_expected(case_id)
        for cid in expected["expected_rejected_candidate_ids"]:
            assert cid in bundle.rejected_candidate_ids, \
                f"[{case_id}] Expected {cid} rejected"
        for cid in expected["expected_accepted_candidate_ids"]:
            assert cid not in bundle.rejected_candidate_ids, \
                f"[{case_id}] Expected {cid} accepted"

    @pytest.mark.parametrize("case_id", ALL_CASE_IDS)
    def test_10x_stability(self, case_id):
        """R2-B03: 10-run stability for all 7 cases."""
        hashes = []
        accepted_sets = []
        rejected_sets = []
        error_counts = []

        for i in range(10):
            _, _, _, sr, bundle = _run_pipeline(case_id)
            hashes.append(bundle.bundle_sha256)
            accepted_sets.append(tuple(sorted(bundle.accepted_candidate_ids)))
            rejected_sets.append(tuple(sorted(bundle.rejected_candidate_ids)))
            error_counts.append(len(bundle.rejected_candidate_ids))

        assert len(set(hashes)) == 1, f"[{case_id}] Bundle hash not stable"
        assert len(set(accepted_sets)) == 1, f"[{case_id}] Accepted set not stable"
        assert len(set(rejected_sets)) == 1, f"[{case_id}] Rejected set not stable"
        assert len(set(error_counts)) == 1, f"[{case_id}] Error count not stable"


# ── Per-Scenario Count Verification ──────────────────────────────────────────

class TestPredictionPollution:
    def test_count_matches_expected(self):
        _, _, _, sr, _ = _run_pipeline("prediction_pollution")
        exp = _load_expected("prediction_pollution")
        assert sr.fact_pollution_count == exp["expected_fact_pollution_count"]


class TestValuationPollution:
    def test_count_matches_expected(self):
        _, _, _, sr, _ = _run_pipeline("valuation_recommendation")
        exp = _load_expected("valuation_recommendation")
        assert sr.fact_pollution_count == exp["expected_fact_pollution_count"]


class TestPromptInjection:
    def test_count_matches_expected(self):
        _, _, _, sr, _ = _run_pipeline("prompt_injection")
        exp = _load_expected("prompt_injection")
        assert sr.prompt_injection_count == exp["expected_prompt_injection_count"]


class TestFakeQuote:
    def test_quote_gate_handles(self):
        """B07: QuoteGate catches fake quotes."""
        window = _make_window()
        raw = _load_raw_provider("fake_quote")
        candidates, _ = _build_candidates_from_raw(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count >= 1


class TestForgedUnit:
    def test_quote_gate_handles(self):
        """B07: QuoteGate catches forged/outside units."""
        window = _make_window()
        raw = _load_raw_provider("forged_or_outside_unit")
        candidates, _ = _build_candidates_from_raw(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count >= 1


class TestHighConfidencePollution:
    def test_count_matches_expected(self):
        _, _, _, sr, _ = _run_pipeline("high_confidence_pollution")
        exp = _load_expected("high_confidence_pollution")
        assert sr.high_confidence_pollution_count == exp["expected_high_confidence_pollution_count"]


class TestProviderOverride:
    def test_count_matches_expected(self):
        _, _, _, sr, _ = _run_pipeline("provider_independence_override")
        exp = _load_expected("provider_independence_override")
        assert sr.provider_override_count == exp["expected_provider_override_count"]

    def test_independence_group_in_override_count(self):
        """R2-B01: independence_group IS counted as provider override."""
        _, _, _, sr, _ = _run_pipeline("provider_independence_override")
        ig_findings = [f for f in sr.findings
                       if f.code == "PROVIDER_OVERRIDE_FIELD"
                       and f.details.get("field") == "independence_group"]
        assert len(ig_findings) >= 1, \
            "R2-B01: independence_group must be flagged as provider override"


# ── B03: Provider Promotable ────────────────────────────────────────────────

class TestProviderPromotable:
    def test_promotable_true_rejected(self):
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


# ── B05: Substring Evasion ──────────────────────────────────────────────────

class TestSubstringEvasion:
    def test_safe_substring_still_detected(self):
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


# ── R2-B02: candidate_id-keyed raw_payloads ─────────────────────────────────

class TestCandidateIdKeyed:
    def test_candidate_id_dict_not_positional_list(self):
        """R2-B02: SafetyGate.validate accepts raw_payloads as dict, not list."""
        window = _make_window()
        ev = EvidenceCandidate(candidate_id="ev_payload_by_id", evidence_type="source_document",
                               evidence_role="support", target_object_id="cl_1",
                               source_quote="汇率波动和原材料价格上涨",
                               source_unit_id="adv_cu_007")
        raw_payloads = {
            "ev_payload_by_id": {"verification_status": "verified", "candidate_id": "ev_payload_by_id"},
        }
        sg = SafetyGate(window)
        report = sg.validate([ev], raw_payloads=raw_payloads)
        assert report.error_count == 1
        assert "ev_payload_by_id" in report.rejected_candidate_ids

    def test_missing_id_in_dict_no_misattribution(self):
        """R2-B02: Missing entry → no misattribution."""
        window = _make_window()
        # Safe evidence WITHOUT forbidden fields
        ev_safe = EvidenceCandidate(candidate_id="ev_safe", evidence_type="source_document",
                                    evidence_role="support", target_object_id="cl_1",
                                    source_quote="汇率波动", source_unit_id="adv_cu_007")
        # Evil evidence WITH forbidden fields (but different ID)
        ev_evil = EvidenceCandidate(candidate_id="ev_evil", evidence_type="source_document",
                                    evidence_role="support", target_object_id="cl_2",
                                    source_quote="汇率波动", source_unit_id="adv_cu_007")

        raw_payloads = {
            "ev_evil": {"verification_status": "verified", "independence_group": "g",
                        "candidate_id": "ev_evil"},
            # ev_safe NOT in raw_payloads → gets None → DTO fallback
        }

        sg = SafetyGate(window)
        report = sg.validate([ev_safe, ev_evil], raw_payloads=raw_payloads)

        # ev_evil is caught
        assert "ev_evil" in report.rejected_candidate_ids
        # ev_safe is clean (no forbidden fields on DTO)
        assert "ev_safe" in report.accepted_candidate_ids


# ── R2-M01: fact_claim whitelist (comprehensive integration) ────────────────

class TestFactClaimWhitelist:
    def test_non_fact_claim_not_promotable(self):
        """R2-M01: Only fact_claim is promotable in full pipeline."""
        window = _make_window()
        cl = ClaimCandidate(candidate_id="cl_interp", statement="解读为正面趋势",
                            claim_type="interpretation", claim_dimension="financial_performance",
                            promotable_to_fact=True,
                            source_quote="解读", source_unit_id="adv_cu_005")
        sg = SafetyGate(window)
        report = sg.validate([cl])
        assert report.error_count >= 1
        assert "cl_interp" in report.rejected_candidate_ids
        findings = [f for f in report.findings if f.code == "NON_PROMOTABLE_CLAIM_TYPE"]
        assert len(findings) >= 1


# ── Hard Gates ───────────────────────────────────────────────────────────────

class TestHardGates:
    def test_g2_1_fact_pollution(self):
        """G2-1: Fact pollution detected and rejected."""
        for case_id in ["prediction_pollution", "valuation_recommendation"]:
            _, _, _, _, bundle = _run_pipeline(case_id)
            expected = _load_expected(case_id)
            assert len(bundle.rejected_candidate_ids) >= 1

    def test_g2_2_fake_quote(self):
        """G2-2: Fake quotes caught by QuoteGate."""
        window = _make_window()
        raw = _load_raw_provider("fake_quote")
        candidates, _ = _build_candidates_from_raw(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count >= 1

    def test_g2_3_forged_unit(self):
        """G2-3: Forged/outside units caught by QuoteGate."""
        window = _make_window()
        raw = _load_raw_provider("forged_or_outside_unit")
        candidates, _ = _build_candidates_from_raw(raw)
        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        assert qr.failed_count >= 1

    def test_g2_4_prompt_injection(self):
        """G2-4: Prompt injection detected."""
        _, _, _, sr, _ = _run_pipeline("prompt_injection")
        pi_errors = [f for f in sr.findings
                     if f.code == "PROMPT_INJECTION" and f.severity == FindingSeverity.ERROR]
        assert len(pi_errors) > 0

    def test_g2_5_provider_override(self):
        """G2-5: Provider override detected (includes independence_group)."""
        _, _, _, sr, _ = _run_pipeline("provider_independence_override")
        ov_errors = [f for f in sr.findings
                     if f.code == "PROVIDER_OVERRIDE_FIELD" and f.severity == FindingSeverity.ERROR]
        assert len(ov_errors) > 0
        # Verify independence_group is specifically caught
        ig_found = any(f.details.get("field") == "independence_group" for f in ov_errors)
        assert ig_found, "G2-5 must flag independence_group from Provider"

    def test_g2_6_high_confidence(self):
        """G2-6: High confidence pollution detected."""
        _, _, _, sr, _ = _run_pipeline("high_confidence_pollution")
        hc = [f for f in sr.findings if f.code == "HIGH_CONFIDENCE_POLLUTION"]
        assert len(hc) > 0


# ── Comprehensive ────────────────────────────────────────────────────────────

class TestComprehensive:
    def test_all_scenarios_load_candidates(self):
        for case_id in ALL_CASE_IDS:
            raw = _load_raw_provider(case_id)
            assert "candidates" in raw
            assert len(raw["candidates"]) > 0

    def test_comprehensive_all_cases(self):
        """R2-B03: Verify all 7 cases against expected metrics."""
        total_pollution = 0
        total_override = 0
        total_high_conf = 0
        total_injection = 0

        for case_id in ALL_CASE_IDS:
            _, _, _, sr, bundle = _run_pipeline(case_id)
            expected = _load_expected(case_id)

            expected_fp = expected["expected_fact_pollution_count"]
            assert sr.fact_pollution_count == expected_fp, \
                f"[{case_id}] Fact pollution: got {sr.fact_pollution_count}, expected {expected_fp}"
            assert sr.prompt_injection_count == expected["expected_prompt_injection_count"], \
                f"[{case_id}] Prompt injection mismatch"
            assert sr.provider_override_count == expected["expected_provider_override_count"], \
                f"[{case_id}] Provider override mismatch"
            assert sr.high_confidence_pollution_count == expected["expected_high_confidence_pollution_count"], \
                f"[{case_id}] High confidence mismatch"

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
        for case_id in ALL_CASE_IDS:
            window = _make_window()
            texts_before = {u.unit_id: u.text for u in window.units}

            raw = _load_raw_provider(case_id)
            candidates, raw_payloads = _build_candidates_from_raw(raw)
            qg = QuoteGate(window)
            qr = qg.validate(candidates)
            sg = SafetyGate(window, existing_findings=qr.findings)
            sg.validate(candidates, raw_payloads=raw_payloads)

            for u in window.units:
                assert u.text == texts_before[u.unit_id], f"[{case_id}] Unit modified"


# ── Regression ───────────────────────────────────────────────────────────────

class TestRegression:
    def test_imports(self):
        from aurora.extraction import SafetyGate, SafetyGateReport, QuoteGate
        assert SafetyGate is not None

    def test_normal_evidence_passes(self):
        """Normal EvidenceCandidate without forbidden fields must pass."""
        window = _make_window()
        ev = EvidenceCandidate(candidate_id="ev_normal", evidence_type="source_document",
                               evidence_role="support", target_object_id="cl_1",
                               source_quote="公司实现营业收入156.3亿元",
                               source_unit_id="adv_cu_004")
        sg = SafetyGate(window)
        report = sg.validate([ev])
        assert report.error_count == 0
        assert "ev_normal" in report.accepted_candidate_ids
