"""FixtureProvider V2 — deterministic extraction from independent provider fixture files.

Reads from tests/fixtures/m2_003/provider_responses/ — NOT from expected_results.
No network, no expected_results read. Returns ProviderResponse with candidates
that have source_unit_id for QuoteGate validation.
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
from aurora.extraction.envelope import ProviderMetadata
from aurora.extraction.providers.base import ExtractionProvider, ProviderResponse

PROVIDER_CASE_FILES = {
    "case_a_web": "case_a_web_provider.json",
    "case_b_video": "case_b_video_provider.json",
    "case_c_pdf": "case_c_pdf_provider.json",
    # Adversarial cases (Gate 2/3)
    "prediction_pollution": "prediction_pollution_provider.json",
    "valuation_recommendation": "valuation_recommendation_provider.json",
    "prompt_injection": "prompt_injection_provider.json",
    "fake_quote": "fake_quote_provider.json",
    "forged_or_outside_unit": "forged_or_outside_unit_provider.json",
    "high_confidence_pollution": "high_confidence_pollution_provider.json",
    "provider_independence_override": "provider_independence_override_provider.json",
}

PROVIDER_FIXTURE_DIR = (
    Path(__file__).parents[4] / "tests" / "fixtures" / "m2_003" / "provider_responses"
)# Frozen candidate type ordering for G1-6 stability
_CANDIDATE_TYPE_ORDER: tuple[str, ...] = (
    "entity",
    "data_point",
    "claim",
    "evidence",
    "fact",
)


class FixtureProvider(ExtractionProvider):
    """Deterministic provider that reads from independent provider fixture files.

    V2 changes:
    - Reads from provider_responses/ directory (NOT expected_results)
    - Returns ProviderResponse (raw pre-envelope contract)
    - No network access
    - No expected_results read
    - Supports injected illegal units and fake quotes for adversarial testing
    - Candidate order can be deliberately shuffled for stability testing
    """

    name: str = "fixture"
    version: str = "2.0"

    def __init__(
        self,
        fixture_dir: Path | None = None,
        shuffle_candidates: bool = False,
    ):
        self._fixture_dir = fixture_dir or PROVIDER_FIXTURE_DIR
        self._shuffle_candidates = shuffle_candidates

    def _load_provider_fixture(self, case_id: str) -> dict[str, Any]:
        file_name = PROVIDER_CASE_FILES.get(case_id)
        if not file_name:
            raise ValueError(
                f"Unknown case_id: {case_id}. Known: {list(PROVIDER_CASE_FILES)}"
            )
        file_path = self._fixture_dir / file_name
        if not file_path.exists():
            # Try adversarial subdirectory
            alt_path = self._fixture_dir.parent / "adversarial" / "provider_responses" / file_name
            if alt_path.exists():
                file_path = alt_path
            else:
                raise FileNotFoundError(f"Provider fixture not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def extract(self, window: ContextWindow) -> ProviderResponse:
        """Extract candidates from the provider fixture for the given window.

        Uses document_id to infer case_id, then reads from independent
        provider_responses fixture file.
        """
        case_id = self._infer_case_id(window)
        return self.extract_for_case(case_id, window)

    def extract_for_case(
        self, case_id: str, window: ContextWindow
    ) -> ProviderResponse:
        """Extract for a specific case_id from provider fixture.

        Resolves provider fixture source_unit_ids against the given
        ContextWindow by matching source_quote text content.
        """
        fixture = self._load_provider_fixture(case_id)
        raw_candidates = fixture.get("candidates", [])
        raw_metadata = fixture.get("provider_metadata", {})
        warnings: list[str] = list(fixture.get("warnings", []))
        errors: list[str] = list(fixture.get("errors", []))

        # OPT-069: Scan for provider-owned epistemic fields in raw payload
        _FORBIDDEN_EPISTEMIC = ("independence_group", "promotable", "promotable_to_fact")

        candidates: list[Any] = []
        for raw in raw_candidates:
            c_type = raw.get("candidate_type", "")
            cid = raw.get("candidate_id", "")

            # OPT-069: Detect provider-owned epistemic fields in raw payload
            for field in _FORBIDDEN_EPISTEMIC:
                if field in raw and raw[field] not in (None, "", [], {}, False):
                    warnings.append(
                        f"Provider raw payload sets forbidden field "
                        f"'{field}={raw[field]!r}' on candidate {cid} — "
                        f"field was dropped at DTO construction, "
                        f"SafetyGate will flag it as PROVIDER_OVERRIDE_FIELD"
                    )

            candidate = self._build_candidate(raw, c_type)
            if candidate is not None:
                # Resolve source_unit_id against the actual ContextWindow
                self._resolve_source_unit_id(candidate, raw, window)
                candidates.append(candidate)

        # Optional shuffle BEFORE sorting for adversarial stability testing
        # This verifies that sort is deterministic regardless of input order
        if self._shuffle_candidates:
            import random
            random.seed(42)
            random.shuffle(candidates)

        # Deterministic sort by frozen type order (ALWAYS after any shuffle)
        candidates.sort(key=self._candidate_sort_key)

        return ProviderResponse(
            candidates=tuple(candidates),
            provider_metadata=ProviderMetadata(
                name=raw_metadata.get("name", self.name),
                version=raw_metadata.get("version", self.version),
                deterministic_mode=raw_metadata.get("deterministic_mode", True),
                case_id=case_id,
                extra=raw_metadata.get("extra", {}),
            ),
            raw_payload=fixture,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    @staticmethod
    def _resolve_source_unit_id(
        candidate: Any, raw: dict[str, Any], window: ContextWindow
    ) -> None:
        """Resolve candidate source_unit_id against the actual ContextWindow.

        The provider fixture may reference frozen snapshot unit IDs.
        We resolve by finding a window unit whose text contains the
        candidate's source_quote.

        For token_set mode (TABLE/TABLE_ROW), uses token matching since
        real parser output may differ in formatting from frozen snapshots.
        """
        if not hasattr(candidate, "source_quote"):
            return

        source_quote = getattr(candidate, "source_quote", "") or ""
        current_suid = getattr(candidate, "source_unit_id", "") or ""
        match_mode = getattr(candidate, "quote_match_mode", "literal") or "literal"

        # If source_unit_id is already valid in window, keep it
        if current_suid and window.has_unit(current_suid):
            return

        # Empty quote — can't resolve
        if not source_quote.strip():
            candidate.source_unit_id = ""
            return

        import re
        import unicodedata

        norm_quote = unicodedata.normalize("NFKC", source_quote)
        norm_quote_collapsed = re.sub(r"\s+", " ", norm_quote).strip()

        # Try exact substring match first
        for unit in window.units:
            norm_text = unicodedata.normalize("NFKC", unit.text)
            if norm_quote in norm_text:
                candidate.source_unit_id = unit.unit_id
                return

        # Try collapsed whitespace substring
        for unit in window.units:
            norm_text = unicodedata.normalize("NFKC", unit.text)
            norm_text_collapsed = re.sub(r"\s+", " ", norm_text).strip()
            if norm_quote_collapsed in norm_text_collapsed:
                candidate.source_unit_id = unit.unit_id
                return

        # Try token_set matching (for TABLE/TABLE_ROW units)
        if match_mode == "token_set":
            quote_tokens = set(re.findall(r"\S+", norm_quote_collapsed))
            if not quote_tokens:
                candidate.source_unit_id = ""
                return

            for unit in window.units:
                unit_type = unit.unit_type.lower()
                if unit_type in ("table", "table_row"):
                    norm_text = unicodedata.normalize("NFKC", unit.text)
                    norm_text_collapsed = re.sub(r"\s+", " ", norm_text).strip()
                    unit_tokens = set(re.findall(r"\S+", norm_text_collapsed))
                    if quote_tokens.issubset(unit_tokens):
                        candidate.source_unit_id = unit.unit_id
                        return

        # Could not resolve — leave empty (will fail QuoteGate)

    @staticmethod
    def _candidate_sort_key(c: Any) -> tuple[int, str, str]:
        """Stable sort: type_order → normalized primary field → candidate_id."""
        c_type = FixtureProvider._infer_candidate_type_name(c)
        try:
            type_idx = _CANDIDATE_TYPE_ORDER.index(c_type)
        except ValueError:
            type_idx = 99

        # Normalized primary field for disambiguation
        primary = ""
        if hasattr(c, "statement"):
            primary = c.statement or ""
        elif hasattr(c, "metric"):
            primary = c.metric or ""
        elif hasattr(c, "canonical_name"):
            primary = c.canonical_name or ""
        elif hasattr(c, "evidence_type"):
            primary = c.evidence_type or ""

        cid = getattr(c, "candidate_id", "") or ""
        return (type_idx, primary, cid)

    @staticmethod
    def _infer_candidate_type_name(c: Any) -> str:
        if isinstance(c, EntityCandidate):
            return "entity"
        elif isinstance(c, DataPointCandidate):
            return "data_point"
        elif isinstance(c, ClaimCandidate):
            return "claim"
        elif isinstance(c, EvidenceCandidate):
            return "evidence"
        elif isinstance(c, FactCandidate):
            return "fact"
        return "unknown"

    @staticmethod
    def _build_candidate(raw: dict[str, Any], c_type: str) -> Any | None:
        if c_type == "entity":
            return EntityCandidate(
                candidate_id=raw.get("candidate_id", ""),
                entity_type=raw.get("entity_type", ""),
                canonical_name=raw.get("canonical_name", ""),
            )
        elif c_type == "data_point":
            return DataPointCandidate(
                candidate_id=raw.get("candidate_id", ""),
                metric=raw.get("metric", ""),
                value=raw.get("value", 0.0),
                unit=raw.get("unit", ""),
                entity_id=raw.get("entity_id", ""),
                period=raw.get("period", ""),
                measurement_context=raw.get("measurement_context", {}),
                source_quote=raw.get("source_quote", ""),
                quote_locator_hint=raw.get("quote_locator_hint", ""),
                quote_match_mode=raw.get("quote_match_mode", "literal"),
                source_unit_id=raw.get("source_unit_id", ""),
                note=raw.get("note", ""),
            )
        elif c_type == "claim":
            return ClaimCandidate(
                candidate_id=raw.get("candidate_id", ""),
                statement=raw.get("statement", ""),
                claim_type=raw.get("claim_type", ""),
                claim_dimension=raw.get("claim_dimension", ""),
                claimant_name=raw.get("claimant_name", ""),
                asserted_by=raw.get("asserted_by", ""),
                time_horizon=raw.get("time_horizon"),
                # OPT-069: promotable_to_fact NOT read from Provider
                # SafetyGate catches it in raw_payload if present
                source_quote=raw.get("source_quote", ""),
                quote_locator_hint=raw.get("quote_locator_hint", ""),
                quote_match_mode=raw.get("quote_match_mode", "literal"),
                source_unit_id=raw.get("source_unit_id", ""),
                note=raw.get("note", ""),
            )
        elif c_type == "evidence":
            return EvidenceCandidate(
                candidate_id=raw.get("candidate_id", ""),
                evidence_type=raw.get("evidence_type", ""),
                evidence_role=raw.get("evidence_role", ""),
                target_object_id=raw.get("target_object_id", ""),
                # OPT-069: independence_group NOT read from Provider
                # SafetyGate catches it in raw_payload if present
                source_quote=raw.get("source_quote", ""),
                quote_match_mode=raw.get("quote_match_mode", "literal"),
                source_unit_id=raw.get("source_unit_id", ""),
                note=raw.get("note", ""),
            )
        elif c_type == "fact":
            return FactCandidate(
                candidate_id=raw.get("candidate_id", ""),
                statement=raw.get("statement", ""),
                # OPT-069: promotable NOT read from Provider
                # SafetyGate catches it in raw_payload if present
                target_data_point_id=raw.get("target_data_point_id"),
                target_claim_id=raw.get("target_claim_id"),
                supporting_evidence_ids=raw.get("supporting_evidence_ids", []),
                valid_time=raw.get("valid_time"),
                confidence_rationale=raw.get("confidence_rationale"),
                rejection_reason=raw.get("rejection_reason", ""),
                source_quote=raw.get("source_quote", ""),
                quote_match_mode=raw.get("quote_match_mode", "literal"),
                source_unit_id=raw.get("source_unit_id", ""),
            )
        return None

    def _infer_case_id(self, window: ContextWindow) -> str:
        doc_id = window.document_id.lower()
        if "case_a" in doc_id or "web" in doc_id:
            return "case_a_web"
        elif "case_b" in doc_id or "video" in doc_id or "srt" in doc_id:
            return "case_b_video"
        elif "case_c" in doc_id or "pdf" in doc_id or "report" in doc_id:
            return "case_c_pdf"
        return "case_a_web"
