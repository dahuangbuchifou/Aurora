"""CLI for Aurora extraction pipeline.

Commands:
    aurora-extract run     Generate ReviewBundle from a case
    aurora-review generate  Create review_decisions.json template
    aurora-review apply     Apply human review decisions

Usage:
    aurora-extract run --case case_a_web --provider fixture --mode deterministic
    aurora-review generate --bundle review_bundle_a.json --decisions-output review_decisions_a.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from aurora.core.models.document import ContentUnit
from aurora.extraction.context_window import ContentUnitRef, ContextWindow
from aurora.extraction.envelope import ExtractionEnvelope
from aurora.extraction.providers.fixture_provider import CASE_FILES, FixtureProvider
from aurora.extraction.quote_gate import QuoteGate
from aurora.extraction.review_bundle import ExtractionError, ReviewBundle
from aurora.extraction.review_decision import ReviewDecision, ReviewDecisionDecision


def _load_context_window_for_case(case_id: str) -> ContextWindow:
    """Build a minimal ContextWindow for a case using expected results text.

    Since we don't always have access to the actual parsed ContentUnits in CLI mode,
    we use the source_quotes from the expected JSON to build a synthetic window.
    """
    provider = FixtureProvider()

    # Determine fixture path
    file_name = CASE_FILES.get(case_id)
    if not file_name:
        raise ValueError(f"Unknown case_id: {case_id}. Known: {list(CASE_FILES)}")

    # Create synthetic ContentUnits from expected results
    from aurora.core.models.common import SourceLocator
    from aurora.core.models.enums import ContentUnitType

    # Load expected results to extract source_quotes
    fixture_path = provider._fixture_dir / file_name
    with open(fixture_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # Collect all unique source_quotes
    quotes: list[str] = []
    for section in [
        "expected_claims",
        "expected_evidence",
        "expected_data_points",
        "expected_rejects",
    ]:
        for item in expected.get(section, []):
            sq = item.get("source_quote", "")
            if sq and sq not in quotes:
                quotes.append(sq)

    # Build synthetic ContentUnits
    synth_units: list[ContentUnit] = []
    doc_id = f"synth_doc_{case_id}"
    for i, quote in enumerate(quotes):
        unit = ContentUnit(
            id=f"synth_cu_{case_id}_{i:04d}",
            document_id=doc_id,
            unit_type=ContentUnitType.PARAGRAPH,
            sequence_no=i,
            text=quote,
            locator=SourceLocator(block_no=i + 1),
        )
        synth_units.append(unit)

    # Also add a combined text unit for complex quotes
    all_text = " ".join(quotes)
    if all_text:
        synth_units.append(
            ContentUnit(
                id=f"synth_cu_{case_id}_combined",
                document_id=doc_id,
                unit_type=ContentUnitType.PARAGRAPH,
                sequence_no=len(quotes),
                text=all_text,
                locator=SourceLocator(block_no=9999),
            )
        )

    return ContextWindow.from_content_units(doc_id, synth_units)


def _generate_bundle(case_id: str, provider_name: str, mode: str) -> ReviewBundle:
    """Generate a ReviewBundle for a given case."""
    window = _load_context_window_for_case(case_id)
    provider = FixtureProvider()

    if provider_name != "fixture":
        raise ValueError(f"Only 'fixture' provider is supported, got: {provider_name}")
    if mode != "deterministic":
        raise ValueError(f"Only 'deterministic' mode is supported, got: {mode}")

    # Don't use extract() since window doesn't match naming convention
    envelope = provider.extract_for_case(case_id, window)

    # Run QuoteGate validation
    gate = QuoteGate(window)
    report = gate.validate(envelope.candidates)

    # Collect quote gate failures as errors
    errors: list[ExtractionError] = []
    for failure in report.failures:
        errors.append(
            ExtractionError(
                code="QUOTE_GATE_FAILURE",
                message=failure.reason,
                candidate_id=failure.candidate_id,
            )
        )

    bundle = ReviewBundle.create(
        document_id=window.document_id,
        provider_name=provider.name,
        provider_version=provider.version,
        deterministic_mode=True,
        candidates=envelope.candidates,
        content_unit_window=window.units,
        errors=tuple(errors),
        case_id=case_id,
    )

    return bundle


def cmd_extract_run(args) -> int:
    """aurora-extract run command."""
    try:
        bundle = _generate_bundle(
            case_id=args.case,
            provider_name=args.provider,
            mode=args.mode,
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output_data = {
        "bundle": bundle.to_json_dict(),
        "candidates": [c.model_dump() for c in bundle.candidates],
        "quote_gate_errors": [e.message for e in bundle.errors if e.code == "QUOTE_GATE_FAILURE"],
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"ReviewBundle written to {output_path}")
    else:
        print(json.dumps(output_data, indent=2, ensure_ascii=False, default=str))

    return 0


def cmd_review_generate(args) -> int:
    """Generate a review_decisions.json template from a ReviewBundle."""
    input_path = Path(args.bundle)
    if not input_path.exists():
        print(f"Error: bundle file not found: {input_path}", file=sys.stderr)
        return 1

    with open(input_path, "r", encoding="utf-8") as f:
        bundle_data = json.load(f)

    candidates = bundle_data.get("candidates", [])
    decisions: list[dict] = []

    for candidate in candidates:
        decision = ReviewDecision(
            run_id=bundle_data["bundle"]["run_id"],
            bundle_sha256=bundle_data["bundle"]["bundle_sha256"],
            candidate_id=candidate.get("candidate_id", candidate.get("id", "")),
            decision=ReviewDecisionDecision.REJECT,
            reviewer="",
            reviewer_role="",
            note="TODO: review this candidate",
        )
        decisions.append(decision.to_dict())

    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_sha256": bundle_data["bundle"]["bundle_sha256"],
        "decisions": decisions,
    }

    output_path = Path(args.decisions_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"Review decisions template written to {output_path}")
    print(f"Total candidates: {len(decisions)}")
    return 0


def cmd_review_apply(args) -> int:
    """Apply review decisions."""
    print("Not yet implemented — waiting for Gate 4 (persist_drafts)", file=sys.stderr)
    return 1


def build_extract_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aurora extraction pipeline")
    subparsers = parser.add_subparsers(dest="command")

    # aurora-extract run
    run_parser = subparsers.add_parser("run", help="Generate ReviewBundle from a case")
    run_parser.add_argument("--case", required=True, choices=list(CASE_FILES.keys()))
    run_parser.add_argument("--provider", default="fixture", choices=["fixture"])
    run_parser.add_argument("--mode", default="deterministic", choices=["deterministic"])
    run_parser.add_argument("--output", help="Output path for ReviewBundle JSON")

    return parser


def build_review_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aurora review pipeline")
    subparsers = parser.add_subparsers(dest="command")

    # aurora-review generate
    gen_parser = subparsers.add_parser("generate", help="Generate review_decisions.json template")
    gen_parser.add_argument("--bundle", required=True, help="Path to ReviewBundle JSON")
    gen_parser.add_argument("--decisions-output", required=True, help="Output path for decisions JSON")

    # aurora-review apply
    apply_parser = subparsers.add_parser("apply", help="Apply human review decisions")
    apply_parser.add_argument("--bundle", required=True, help="Path to ReviewBundle JSON")
    apply_parser.add_argument("--decisions", required=True, help="Path to review_decisions.json")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for aurora-extract CLI."""
    parser = build_extract_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return cmd_extract_run(args)
    else:
        parser.print_help()
        return 1


def review_main(argv: Sequence[str] | None = None) -> int:
    """Entry point for aurora-review CLI."""
    parser = build_review_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return cmd_review_generate(args)
    elif args.command == "apply":
        return cmd_review_apply(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
