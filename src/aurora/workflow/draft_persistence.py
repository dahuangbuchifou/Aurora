"""Workflow: draft persistence — single entry point using sessionmaker.

B01: Workflow receives sessionmaker, owns session lifecycle internally.

Stages:
  FixtureProvider → ProviderResponse → QuoteGate → SafetyGate
  → ReviewBundle → Preflight → Map → Persist via persist_drafts
"""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from aurora.extraction.context_window import ContextWindow
from aurora.extraction.providers.fixture_provider import FixtureProvider
from aurora.extraction.quote_gate import QuoteGate
from aurora.extraction.review_bundle import ReviewBundle
from aurora.extraction.safety_gate import SafetyGate
from aurora.persistence.draft_service import (
    DraftTransaction,
    persist_drafts,
)
from aurora.persistence.persistence_policy import PersistencePolicy


def run_draft_persistence(
    repo_factory: sessionmaker,
    window: ContextWindow,
    case_id: str,
    workspace_id: str = "aurora_gate3_default",
    dry_run: bool = False,
    preflight_kwargs: dict[str, Any] | None = None,
    policy: PersistencePolicy | None = None,
) -> tuple[ReviewBundle, DraftTransaction]:
    """B01: End-to-end draft persistence pipeline (workflow-owned session).

    1. FixtureProvider extracts candidates from fixture JSON
    2. QuoteGate validates source quotes
    3. SafetyGate validates cognitive safety
    4. ReviewBundle assembled
    5. Preflight → Map → Persist (workflow owns session, B01)
    """
    provider = FixtureProvider()
    provider_response = provider.extract_for_case(case_id, window)

    raw_payload = provider_response.raw_payload
    raw_candidates = raw_payload.get("candidates", []) if raw_payload else []
    raw_payloads: dict[str, dict] = {
        rc.get("candidate_id", ""): rc for rc in raw_candidates
        if rc.get("candidate_id")
    }

    qg = QuoteGate(window)
    qr = qg.validate(provider_response.candidates)

    sg = SafetyGate(window, existing_findings=qr.findings)
    sr = sg.validate(provider_response.candidates, raw_payloads=raw_payloads)

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

    # R3-01: Build a default policy from available params if none provided
    if policy is None:
        pk = preflight_kwargs or {}
        policy = PersistencePolicy(
            allowed_providers=pk.get("allowed_providers", frozenset({"fixture_provider"})),
            allowed_profiles=pk.get("allowed_profiles", frozenset({"adversarial_profile"})),
            workspace_id=workspace_id,
            existing_object_resolver=pk.get("existing_object_resolver"),
            dry_run=dry_run,
        )

    tx = persist_drafts(
        repo_factory=repo_factory,
        bundle=bundle,
        workspace_id=workspace_id,
        dry_run=dry_run,
        preflight_kwargs=preflight_kwargs,
        policy=policy,
    )

    return bundle, tx
