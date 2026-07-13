"""FixtureProvider — deterministic extraction from golden set expected results.

Pure Python, no LLM/API calls. Reads expected JSON from
tests/fixtures/m2_003/expected/ and generates deterministic candidate lists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aurora.extraction.candidates import (
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
    FactCandidate,
)
from aurora.extraction.context_window import ContextWindow
from aurora.extraction.envelope import ExtractionEnvelope, ProviderMetadata
from aurora.extraction.providers.base import ExtractionProvider

FIXTURE_DIR = Path(__file__).parents[4] / "tests" / "fixtures" / "m2_003" / "expected"

CASE_FILES = {
    "case_a_web": "case_a_web_expected.json",
    "case_b_video": "case_b_video_expected.json",
    "case_c_pdf": "case_c_pdf_expected.json",
}


class FixtureProvider(ExtractionProvider):
    """Deterministic provider that returns golden set candidates.

    Reads expected results from the M2-003A golden set and generates
    candidate objects with deterministic ordering.

    No external API or LLM calls — pure data transformation.
    """

    name: str = "fixture"
    version: str = "1.0"

    def __init__(self, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir or FIXTURE_DIR

    def _load_expected(self, case_id: str) -> dict[str, Any]:
        file_name = CASE_FILES.get(case_id)
        if not file_name:
            raise ValueError(f"Unknown case_id: {case_id}. Known: {list(CASE_FILES)}")

        file_path = self._fixture_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"Expected file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def extract(self, window: ContextWindow) -> ExtractionEnvelope:
        """Extract candidates from the context window using golden set data.

        Uses document_id to determine the case_id by matching against known
        material file paths.
        """
        # Determine case from context window
        case_id = self._infer_case_id(window)
        expected = self._load_expected(case_id)

        candidates: list[Any] = []
        warnings: list[str] = []

        # 1. Extract entities
        for ent_data in expected.get("expected_entities", []):
            candidates.append(
                EntityCandidate(
                    id=ent_data["id"],
                    entity_type=ent_data["entity_type"],
                    canonical_name=ent_data["canonical_name"],
                )
            )

        # 2. Extract data points
        for dp_data in expected.get("expected_data_points", []):
            candidates.append(
                DataPointCandidate(
                    id=dp_data["id"],
                    metric=dp_data["metric"],
                    value=dp_data["value"],
                    unit=dp_data["unit"],
                    entity_id=dp_data["entity_id"],
                    period=dp_data["period"],
                    measurement_context=dp_data["measurement_context"],
                    source_quote=dp_data["source_quote"],
                    quote_locator_hint=dp_data.get("quote_locator_hint", ""),
                    note=dp_data.get("note", ""),
                )
            )

        # 3. Extract claims
        for cl_data in expected.get("expected_claims", []):
            candidates.append(
                ClaimCandidate(
                    id=cl_data["id"],
                    statement=cl_data["statement"],
                    claim_type=cl_data["claim_type"],
                    claim_dimension=cl_data["claim_dimension"],
                    claimant_id=cl_data.get("claimant_id"),
                    claimant_name=cl_data.get("claimant_name", ""),
                    asserted_by=cl_data.get("asserted_by", ""),
                    time_horizon=cl_data.get("time_horizon"),
                    promotable_to_fact=cl_data.get("promotable_to_fact", False),
                    source_quote=cl_data["source_quote"],
                    quote_locator_hint=cl_data.get("quote_locator_hint", ""),
                    note=cl_data.get("note", ""),
                )
            )

        # 4. Extract evidence
        for ev_data in expected.get("expected_evidence", []):
            candidates.append(
                EvidenceCandidate(
                    id=ev_data["id"],
                    evidence_type=ev_data["evidence_type"],
                    evidence_role=ev_data["evidence_role"],
                    target_object_id=ev_data["target_object_id"],
                    independence_group=ev_data["independence_group"],
                    source_quote=ev_data["source_quote"],
                    note=ev_data.get("note", ""),
                )
            )

        # 5. Extract fact candidates
        for fc_data in expected.get("expected_fact_candidates", []):
            candidates.append(
                FactCandidate(
                    id=fc_data["id"],
                    target_data_point_id=fc_data.get("target_data_point_id"),
                    target_claim_id=fc_data.get("target_claim_id"),
                    supporting_evidence_ids=fc_data.get("supporting_evidence_ids", []),
                    statement=fc_data["statement"],
                    valid_time=fc_data.get("valid_time"),
                    confidence_rationale=fc_data.get("confidence_rationale"),
                    promotable=fc_data.get("promotable", False),
                    rejection_reason=fc_data.get("rejection_reason", ""),
                )
            )

        # 6. Collect warnings
        for warn in expected.get("expected_warnings", []):
            warnings.append(
                f"[{warn.get('warning_type', 'other')}] {warn['target_id']}: {warn['note']}"
            )

        # Sort candidates deterministically by (type_order, id) for stability
        type_order = {
            EntityCandidate: 0,
            DataPointCandidate: 1,
            ClaimCandidate: 2,
            EvidenceCandidate: 3,
            FactCandidate: 4,
        }

        def sort_key(c: Any) -> tuple[int, str]:
            order = type_order.get(type(c), 99)
            return (order, getattr(c, "id", ""))

        candidates.sort(key=sort_key)

        return ExtractionEnvelope(
            candidates=tuple(candidates),
            provider_metadata=ProviderMetadata(
                name=self.name,
                version=self.version,
                deterministic_mode=True,
                case_id=case_id,
            ),
            warnings=tuple(warnings),
        )

    def _infer_case_id(self, window: ContextWindow) -> str:
        """Infer case_id from ContextWindow's document_id.

        Falls back to case_a_web if inference fails (for testing compatibility).
        """
        doc_id = window.document_id.lower()
        if "case_a" in doc_id or "web" in doc_id:
            return "case_a_web"
        elif "case_b" in doc_id or "video" in doc_id or "srt" in doc_id:
            return "case_b_video"
        elif "case_c" in doc_id or "pdf" in doc_id or "report" in doc_id:
            return "case_c_pdf"
        # Default fallback for testing
        return "case_a_web"

    def extract_for_case(self, case_id: str, window: ContextWindow) -> ExtractionEnvelope:
        """Extract for a specific case_id, bypassing inference."""
        expected = self._load_expected(case_id)

        # Override the window-based inference
        candidates: list[Any] = []

        for ent_data in expected.get("expected_entities", []):
            candidates.append(
                EntityCandidate(
                    id=ent_data["id"],
                    entity_type=ent_data["entity_type"],
                    canonical_name=ent_data["canonical_name"],
                )
            )

        for dp_data in expected.get("expected_data_points", []):
            candidates.append(
                DataPointCandidate(
                    id=dp_data["id"],
                    metric=dp_data["metric"],
                    value=dp_data["value"],
                    unit=dp_data["unit"],
                    entity_id=dp_data["entity_id"],
                    period=dp_data["period"],
                    measurement_context=dp_data["measurement_context"],
                    source_quote=dp_data["source_quote"],
                    quote_locator_hint=dp_data.get("quote_locator_hint", ""),
                    note=dp_data.get("note", ""),
                )
            )

        for cl_data in expected.get("expected_claims", []):
            candidates.append(
                ClaimCandidate(
                    id=cl_data["id"],
                    statement=cl_data["statement"],
                    claim_type=cl_data["claim_type"],
                    claim_dimension=cl_data["claim_dimension"],
                    claimant_id=cl_data.get("claimant_id"),
                    claimant_name=cl_data.get("claimant_name", ""),
                    asserted_by=cl_data.get("asserted_by", ""),
                    time_horizon=cl_data.get("time_horizon"),
                    promotable_to_fact=cl_data.get("promotable_to_fact", False),
                    source_quote=cl_data["source_quote"],
                    quote_locator_hint=cl_data.get("quote_locator_hint", ""),
                    note=cl_data.get("note", ""),
                )
            )

        for ev_data in expected.get("expected_evidence", []):
            candidates.append(
                EvidenceCandidate(
                    id=ev_data["id"],
                    evidence_type=ev_data["evidence_type"],
                    evidence_role=ev_data["evidence_role"],
                    target_object_id=ev_data["target_object_id"],
                    independence_group=ev_data["independence_group"],
                    source_quote=ev_data["source_quote"],
                    note=ev_data.get("note", ""),
                )
            )

        for fc_data in expected.get("expected_fact_candidates", []):
            candidates.append(
                FactCandidate(
                    id=fc_data["id"],
                    target_data_point_id=fc_data.get("target_data_point_id"),
                    target_claim_id=fc_data.get("target_claim_id"),
                    supporting_evidence_ids=fc_data.get("supporting_evidence_ids", []),
                    statement=fc_data["statement"],
                    valid_time=fc_data.get("valid_time"),
                    confidence_rationale=fc_data.get("confidence_rationale"),
                    promotable=fc_data.get("promotable", False),
                    rejection_reason=fc_data.get("rejection_reason", ""),
                )
            )

        type_order = {
            EntityCandidate: 0,
            DataPointCandidate: 1,
            ClaimCandidate: 2,
            EvidenceCandidate: 3,
            FactCandidate: 4,
        }

        def sort_key(c: Any) -> tuple[int, str]:
            order = type_order.get(type(c), 99)
            return (order, getattr(c, "id", ""))

        candidates.sort(key=sort_key)

        warnings: list[str] = []
        for warn in expected.get("expected_warnings", []):
            warnings.append(
                f"[{warn.get('warning_type', 'other')}] {warn['target_id']}: {warn['note']}"
            )

        return ExtractionEnvelope(
            candidates=tuple(candidates),
            provider_metadata=ProviderMetadata(
                name=self.name,
                version=self.version,
                deterministic_mode=True,
                case_id=case_id,
            ),
            warnings=tuple(warnings),
        )
