"""Command-line interface for M2-001 offline ingestion."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from aurora.core.models.enums import DocumentType, SourceType
from aurora.db.session import create_db_engine, create_session_factory
from aurora.ingestion.contracts import (
    DuplicateStrategy,
    IngestionInputType,
    IngestionRequest,
    IngestionResult,
)
from aurora.ingestion.errors import IngestionError, UnsupportedInputError
from aurora.workflow import IngestionService

DEFAULT_DATABASE_URL = "sqlite:///./data/aurora.db"


def _input_type_from_path(path: Path, explicit: str | None) -> IngestionInputType:
    if explicit:
        return IngestionInputType(explicit)
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return IngestionInputType.MARKDOWN
    if suffix in {".txt", ".text"}:
        return IngestionInputType.TEXT
    raise UnsupportedInputError(
        "file extension is not supported; use --input-type markdown|text",
        context={"path": str(path), "suffix": suffix},
    )


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--database",
        default=os.getenv("AURORA_DATABASE_URL", DEFAULT_DATABASE_URL),
    )
    parser.add_argument("--workspace")
    parser.add_argument(
        "--duplicate-strategy",
        choices=[item.value for item in DuplicateStrategy],
        default=DuplicateStrategy.REUSE.value,
    )
    parser.add_argument("--max-size-mb", type=float)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--created-by", default="cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aurora-ingest",
        description="Import local deterministic content into Aurora",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    file_parser = subparsers.add_parser(
        "file",
        help="Import a Markdown or UTF-8 plain-text file",
    )
    file_parser.add_argument("path", type=Path)
    file_parser.add_argument("--input-type", choices=["markdown", "text"])
    file_parser.add_argument("--source-name", required=True)
    file_parser.add_argument(
        "--source-type",
        choices=[item.value for item in SourceType],
        default=SourceType.LOCAL_FILE.value,
    )
    file_parser.add_argument("--source-key")
    file_parser.add_argument("--source-homepage-url")
    file_parser.add_argument("--title")
    file_parser.add_argument(
        "--document-type",
        choices=[item.value for item in DocumentType],
    )
    file_parser.add_argument("--language")
    file_parser.add_argument("--tag", action="append", default=[])
    file_parser.add_argument("--idempotency-key")
    _add_common_options(file_parser)

    segments_parser = subparsers.add_parser(
        "segments",
        help="Import a Structured Segments JSON manifest",
    )
    segments_parser.add_argument("path", type=Path)
    segments_parser.add_argument("--source-name")
    segments_parser.add_argument(
        "--source-type",
        choices=[item.value for item in SourceType],
    )
    segments_parser.add_argument("--source-key")
    segments_parser.add_argument("--source-homepage-url")
    segments_parser.add_argument("--title")
    segments_parser.add_argument(
        "--document-type",
        choices=[item.value for item in DocumentType],
    )
    segments_parser.add_argument("--language")
    segments_parser.add_argument("--tag", action="append", default=[])
    segments_parser.add_argument("--idempotency-key")
    _add_common_options(segments_parser)
    return parser


def _request_from_args(args: argparse.Namespace) -> IngestionRequest:
    input_type = (
        _input_type_from_path(args.path, args.input_type)
        if args.command == "file"
        else IngestionInputType.STRUCTURED_SEGMENTS
    )
    max_bytes = None
    if args.max_size_mb is not None:
        if args.max_size_mb <= 0:
            raise ValueError("--max-size-mb must be positive")
        max_bytes = int(args.max_size_mb * 1024 * 1024)
    return IngestionRequest(
        path=args.path,
        input_type=input_type,
        workspace_id=args.workspace,
        source_name=args.source_name,
        source_type=SourceType(args.source_type) if args.source_type else None,
        source_key=args.source_key,
        source_homepage_url=args.source_homepage_url,
        title=args.title,
        document_type=(
            DocumentType(args.document_type) if args.document_type else None
        ),
        language=args.language,
        tags=args.tag,
        idempotency_key=args.idempotency_key,
        duplicate_strategy=DuplicateStrategy(args.duplicate_strategy),
        max_bytes=max_bytes,
        dry_run=args.dry_run,
        created_by=args.created_by,
    )


def _result_text(result: IngestionResult) -> str:
    verb = "Would reuse" if result.dry_run and result.reused else (
        "Would import" if result.dry_run else (
            "Reused" if result.reused else "Imported"
        )
    )
    return (
        f"{verb} {result.content_unit_count} content units from 1 document "
        f"(document_id={result.document_id}, "
        f"run_id={result.processing_run_id}, reused={str(result.reused).lower()})"
    )


def _print_result(result: IngestionResult, output: str) -> None:
    if output == "json":
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False))
    else:
        print(_result_text(result))
        for warning in result.warnings:
            print(f"warning: {warning}", file=sys.stderr)


def _print_error(error: Exception, output: str) -> None:
    if isinstance(error, IngestionError):
        payload = error.to_dict()
    elif isinstance(error, ValidationError):
        payload = {
            "status": "error",
            "error_code": "INGEST_REQUEST_INVALID",
            "error_message": "ingestion request validation failed",
            "context": {"errors": error.errors(include_url=False)},
        }
    else:
        payload = {
            "status": "error",
            "error_code": "INGEST_CLI_ERROR",
            "error_message": str(error),
            "context": {},
        }
    if output == "json":
        print(json.dumps(payload, ensure_ascii=False, default=str), file=sys.stderr)
    else:
        print(
            f"{payload['error_code']}: {payload['error_message']}",
            file=sys.stderr,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        request = _request_from_args(args)
        engine = create_db_engine(args.database)
        try:
            factory = create_session_factory(engine)
            result = IngestionService(factory).ingest(request)
        finally:
            engine.dispose()
        _print_result(result, args.output)
        return 0
    except Exception as exc:
        _print_error(exc, getattr(args, "output", "text"))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
