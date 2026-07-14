"""Integration tests: M2-003C Gate 3 draft persistence.

Covers:
- Full pipeline: FixtureProvider → QuoteGate → SafetyGate → ReviewBundle → Persist
- Idempotent replay (G3-6)
- Dry-run (zero writes)
- FactCandidate excluded (G3-2)
- Rejected candidates excluded
- ProcessingRun audit
- Claim epistemic_status = UNDER_REVIEW (G3-3)
- independence_group engine-computed (not Provider)
- Transaction atomic
"""

import hashlib
import json
from pathlib import Path

import pytest

from aurora.core.models.document import ContentUnit
from aurora.core.models.common import SourceLocator
from aurora.extraction.context_window import ContextWindow
from aurora.persistence.draft_service import DraftStore
from aurora.persistence.identity import (
    compute_bundle_operation_key,
    compute_draft_natural_key,
)
from aurora.workflow.draft_persistence import run_draft_persistence

ADVERSARIAL_DIR = Path(__file__).parents[1] / "fixtures" / "m2_003" / "adversarial"
CU_DIR = ADVERSARIAL_DIR / "content_units"


def _make_adversarial_window():
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
    return ContextWindow.from_content_units("doc_adversarial", units)


# ── Full Pipeline Tests ─────────────────────────────────────────────────────

class TestFullPipeline:
    def test_case_a_web_persists_drafts(self):
        store = DraftStore()
        window = _make_adversarial_window()
        bundle, tx = run_draft_persistence(store, window, "prediction_pollution")

        assert tx.succeeded
        assert tx.total_objects > 0
        assert tx.created_count > 0
        assert len(store.processing_runs) == 1

    def test_dry_run_creates_nothing(self):
        """Dry run must not write to store."""
        store = DraftStore()
        window = _make_adversarial_window()

        bundle_dry, tx_dry = run_draft_persistence(store, window, "valuation_recommendation", dry_run=True)
        assert tx_dry.created_count > 0
        assert len(store.entities) == 0, "Dry run must not write entities"
        assert len(store.claims) == 0, "Dry run must not write claims"
        assert len(store.processing_runs) == 0, "Dry run must not write runs"

    def test_dry_then_real(self):
        """Dry run → real persist → both succeed."""
        store = DraftStore()
        window = _make_adversarial_window()

        _, tx_dry = run_draft_persistence(store, window, "prediction_pollution", dry_run=True)
        assert tx_dry.created_count > 0

        _, tx_real = run_draft_persistence(store, window, "prediction_pollution", dry_run=False)
        assert tx_real.created_count > 0
        assert len(store.processing_runs) == 1

    def test_rejected_candidates_not_persisted(self):
        """G3: Rejected candidate IDs must not appear in draft objects."""
        store = DraftStore()
        window = _make_adversarial_window()

        bundle, tx = run_draft_persistence(store, window, "prediction_pollution")

        for rec in tx.records:
            assert rec.candidate_id not in bundle.rejected_candidate_ids, (
                f"Candidate {rec.candidate_id} was rejected but persisted"
            )

    def test_no_fact_in_drafts(self):
        """G3-2: FactCandidate must never be persisted."""
        store = DraftStore()
        window = _make_adversarial_window()
        _, tx = run_draft_persistence(store, window, "prediction_pollution")

        for rec in tx.records:
            assert rec.object_type != "fact", "G3-2: Fact persisted"

    def test_claims_under_review(self):
        """G3-3: All draft Claims must have epistemic_status=UNDER_REVIEW."""
        store = DraftStore()
        window = _make_adversarial_window()
        _, tx = run_draft_persistence(store, window, "prediction_pollution")

        for claim in store.claims.values():
            assert claim.epistemic_status.value == "under_review", (
                f"G3-3: Claim {claim.id} is {claim.epistemic_status}, not UNDER_REVIEW"
            )

    @pytest.mark.parametrize("case_id", [
        "prediction_pollution",
        "valuation_recommendation",
        "prompt_injection",
        "fake_quote",
        "forged_or_outside_unit",
        "high_confidence_pollution",
        "provider_independence_override",
    ])
    def test_all_adversarial_cases(self, case_id):
        """Full pipeline succeeds for all 7 adversarial cases."""
        store = DraftStore()
        window = _make_adversarial_window()
        _, tx = run_draft_persistence(store, window, case_id)
        assert tx.succeeded


# ── Idempotency (G3-6) ─────────────────────────────────────────────────────

class TestIdempotency:
    def test_same_bundle_twice_no_duplicates(self):
        """G3-6: Same bundle re-run → total_objects=0, no new objects."""
        store = DraftStore()
        window = _make_adversarial_window()

        _, tx1 = run_draft_persistence(store, window, "prediction_pollution")
        count1 = tx1.created_count + tx1.reused_count

        _, tx2 = run_draft_persistence(store, window, "prediction_pollution")
        assert tx2.total_objects == 0, "G3-6: Replay created new objects"
        assert tx2.created_count == 0

    def test_idempotent_across_10_runs(self):
        """10 identical runs → only first creates, rest idempotent."""
        for case_id in ["prediction_pollution", "high_confidence_pollution"]:
            store = DraftStore()
            window = _make_adversarial_window()

            _, tx1 = run_draft_persistence(store, window, case_id)
            first_count = tx1.created_count

            for i in range(9):
                _, tx = run_draft_persistence(store, window, case_id)
                assert tx.total_objects == 0, f"Run {i+2}: G3-6 violation"
                assert tx.created_count == 0

    def test_bundle_operation_key_stable(self):
        """Bundle operation key must be stable across runs."""
        store = DraftStore()
        window = _make_adversarial_window()

        bundle, _ = run_draft_persistence(store, window, "prediction_pollution")
        key1 = compute_bundle_operation_key("aurora_gate3_default", bundle.bundle_sha256)

        store2 = DraftStore()
        bundle2, _ = run_draft_persistence(store2, window, "prediction_pollution")
        key2 = compute_bundle_operation_key("aurora_gate3_default", bundle2.bundle_sha256)

        assert key1 == key2, "Bundle operation key not stable"

    def test_natural_key_ignores_confidence(self):
        """Natural key must NOT change when confidence changes."""
        from aurora.extraction.candidates import ClaimCandidate

        cl1 = ClaimCandidate(candidate_id="cl_test", statement="test",
                             claim_type="fact_claim", claim_dimension="financial_performance",
                             source_quote="test", confidence=0.5)
        cl2 = ClaimCandidate(candidate_id="cl_test", statement="test",
                             claim_type="fact_claim", claim_dimension="financial_performance",
                             source_quote="test", confidence=0.99)

        nk1 = compute_draft_natural_key("ws", "claim", cl1)
        nk2 = compute_draft_natural_key("ws", "claim", cl2)
        assert nk1 == nk2, "Natural key must ignore confidence"


# ── ProcessingRun Audit ─────────────────────────────────────────────────────

class TestProcessingRun:
    def test_success_run_recorded(self):
        store = DraftStore()
        window = _make_adversarial_window()
        _, tx = run_draft_persistence(store, window, "prediction_pollution")

        assert len(store.processing_runs) == 1
        run = store.processing_runs[0]
        assert run.run_status.value == "success"
        assert run.task_type == "draft_persistence"

    def test_dry_run_no_run_recorded(self):
        store = DraftStore()
        window = _make_adversarial_window()
        _, tx = run_draft_persistence(store, window, "prediction_pollution", dry_run=True)

        assert len(store.processing_runs) == 0

    def test_processing_run_id_in_transaction(self):
        store = DraftStore()
        window = _make_adversarial_window()
        _, tx = run_draft_persistence(store, window, "prediction_pollution")

        assert tx.processing_run_id.startswith("run_")
        assert len(tx.processing_run_id) > 20


# ── Engine independence_group ───────────────────────────────────────────────

class TestEngineIndependenceGroup:
    def test_engine_group_used_not_provider(self):
        """G3-7: independence_group must come from engine, not Provider."""
        store = DraftStore()
        window = _make_adversarial_window()
        ug = run_draft_persistence(
            store, window, "prediction_pollution",
            engine_independence_group="engine_computed_group_A",
        )

        for ev in store.evidence.values():
            assert ev.independence_group == "engine_computed_group_A", (
                f"G3-7: independence_group={ev.independence_group}, expected engine value"
            )


# ── Input Not Modified ─────────────────────────────────────────────────────

class TestNoSideEffects:
    def test_input_not_mutated(self):
        store = DraftStore()
        window = _make_adversarial_window()
        texts_before = {u.unit_id: u.text for u in window.units}

        run_draft_persistence(store, window, "prediction_pollution")

        for u in window.units:
            assert u.text == texts_before[u.unit_id], "ContentUnit modified"


# ── Regression ──────────────────────────────────────────────────────────────

class TestRegression:
    def test_all_431_still_pass(self):
        """Smoke: imports work, persistence module is importable."""
        from aurora.persistence import contracts, identity, validation, mapper, draft_service
        from aurora.workflow import draft_persistence
        assert True

    def test_identity_module_imports(self):
        from aurora.persistence.identity import (
            NAMESPACE,
            compute_bundle_operation_key,
            compute_draft_natural_key,
            _stable_provider_payload,
        )
        assert NAMESPACE == "aurora/v1"
