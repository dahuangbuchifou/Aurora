"""Workflow: draft persistence — single method to go from FixtureProvider → persisted drafts.

Stages:
  FixtureProvider → ProviderResponse → QuoteGate → SafetyGate
  → ReviewBundle → Preflight → Map → Persist

This is the SINGLE entry point for Gate 3 — no duplicate candidate builders.
"""

from __future__ import annotations

from aurora.extraction.context_window import ContextWindow
from aurora.extraction.providers.fixture_provider import FixtureProvider
from aurora.extraction.quote_gate import QuoteGate
from aurora.extraction.review_bundle import ReviewBundle
from aurora.extraction.safety_gate import SafetyGate
from aurora.persistence.draft_service import DraftStore, DraftTransaction, persist_drafts


def run_draft_persistence(
    store: DraftStore,
    window: ContextWindow,
    case_id: str,
    workspace_id: str = "aurora_gate3_default",
    engine_independence_group: str = "",
    dry_run: bool = False,
) -> tuple[ReviewBundle, DraftTransaction]:
    """End-to-end draft persistence pipeline.

    1. FixtureProvider extracts candidates from fixture JSON
    2. QuoteGate validates source quotes
    3. SafetyGate validates cognitive safety
    4. ReviewBundle assembled
    5. Preflight checks
    6. Map → Persist (or dry-run)

    Returns (bundle, transaction).
    """
    # Stage 1: Provider extraction
    provider = FixtureProvider()
    provider_response = provider.extract_for_case(case_id, window)

    # Build raw_payloads dict for SafetyGate (candidate_id → raw item)
    raw_payload = provider_response.raw_payload
    raw_candidates = raw_payload.get("candidates", []) if raw_payload else []
    raw_payloads: dict[str, dict] = {
        rc.get("candidate_id", ""): rc for rc in raw_candidates
        if rc.get("candidate_id")
    }

    # Stage 2: QuoteGate
    qg = QuoteGate(window)
    qr = qg.validate(provider_response.candidates)

    # Stage 3: SafetyGate
    sg = SafetyGate(window, existing_findings=qr.findings)
    sr = sg.validate(provider_response.candidates, raw_payloads=raw_payloads)

    # Stage 4: ReviewBundle
    all_findings = tuple(list(qr.findings) + sr.findings)
    bundle = ReviewBundle.create(
        document_id=window.document_id,
        provider_name=provider_response.provider_metadata.name,
        provider_version=provider_response.provider_metadata.version,
        deterministic_mode=provider_response.provider_metadata.deterministic_mode,
        candidates=provider_response.candidates,
        content_unit_window=window.units,
        validation_findings=all_findings,
        context_hashes={"window_sha256": window.window_sha256},
        case_id=case_id,
        run_id=f"run_{case_id}_persist",
    )

    # Stage 5-6: Preflight + Persist
    tx = persist_drafts(
        store=store,
        bundle=bundle,
        workspace_id=workspace_id,
        engine_independence_group=engine_independence_group,
        dry_run=dry_run,
    )

    return bundle, tx
