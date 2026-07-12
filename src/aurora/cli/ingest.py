"""Command-line interface for deterministic Aurora ingestion."""

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
    PdfTableMode,
)
from aurora.ingestion.errors import IngestionError, UnsupportedInputError
from aurora.workflow import IngestionService

DEFAULT_DATABASE_URL = "sqlite:///./data/aurora.db"


def _input_type_from_path(path: Path, explicit: str | None) -> IngestionInputType:
    if explicit:
        return IngestionInputType(explicit)
    suffix = path.suffix.lower()
    mapping = {
        ".md": IngestionInputType.MARKDOWN,
        ".markdown": IngestionInputType.MARKDOWN,
        ".txt": IngestionInputType.TEXT,
        ".text": IngestionInputType.TEXT,
    }
    if suffix in mapping:
        return mapping[suffix]
    raise UnsupportedInputError(
        "file extension is not supported; use --input-type markdown|text",
        context={"path": str(path), "suffix": suffix},
    )


def _transcript_type(path: Path, explicit: str | None) -> IngestionInputType:
    value = explicit or path.suffix.lower().lstrip(".")
    if value == "srt":
        return IngestionInputType.SRT
    if value in {"vtt", "webvtt"}:
        return IngestionInputType.VTT
    raise UnsupportedInputError(
        "transcript must be SRT or WebVTT",
        context={"path": str(path), "format": value},
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


def _add_source_options(
    parser: argparse.ArgumentParser,
    *,
    required: bool = True,
    default_source_type: SourceType = SourceType.LOCAL_FILE,
) -> None:
    parser.add_argument("--source-name", required=required)
    parser.add_argument(
        "--source-type",
        choices=[item.value for item in SourceType],
        default=default_source_type.value if required else None,
    )
    parser.add_argument("--source-key")
    parser.add_argument("--source-homepage-url")
    parser.add_argument("--title")
    parser.add_argument(
        "--document-type",
        choices=[item.value for item in DocumentType],
    )
    parser.add_argument("--language")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--idempotency-key")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aurora-ingest",
        description="Import deterministic local and static content into Aurora",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    file_parser = subparsers.add_parser(
        "file", help="Import a Markdown or UTF-8 plain-text file"
    )
    file_parser.add_argument("path", type=Path)
    file_parser.add_argument("--input-type", choices=["markdown", "text"])
    _add_source_options(file_parser)
    _add_common_options(file_parser)

    segments_parser = subparsers.add_parser(
        "segments", help="Import a Structured Segments JSON manifest"
    )
    segments_parser.add_argument("path", type=Path)
    _add_source_options(segments_parser, required=False)
    _add_common_options(segments_parser)

    html_parser = subparsers.add_parser("html", help="Import a local static HTML file")
    html_parser.add_argument("path", type=Path)
    html_parser.add_argument("--content-selector")
    _add_source_options(html_parser)
    _add_common_options(html_parser)

    url_parser = subparsers.add_parser("url", help="Fetch and import one static HTML URL")
    url_parser.add_argument("url")
    url_parser.add_argument("--content-selector")
    url_parser.add_argument(
        "--allow-private-network",
        action="store_true",
        help="Explicitly allow private network targets; disabled by default",
    )
    _add_source_options(
        url_parser,
        default_source_type=SourceType.OFFICIAL_WEBSITE,
    )
    _add_common_options(url_parser)

    pdf_parser = subparsers.add_parser(
        "pdf", help="Import a local machine-generated PDF"
    )
    pdf_parser.add_argument("path", type=Path)
    pdf_parser.add_argument("--pages")
    pdf_parser.add_argument(
        "--table-mode",
        choices=[item.value for item in PdfTableMode],
        default=PdfTableMode.BEST_EFFORT.value,
    )
    pdf_parser.add_argument("--max-pages", type=int)
    _add_source_options(pdf_parser)
    _add_common_options(pdf_parser)

    transcript_parser = subparsers.add_parser(
        "transcript", help="Import an SRT or WebVTT transcript"
    )
    transcript_parser.add_argument("path", type=Path)
    transcript_parser.add_argument("--format", choices=["srt", "vtt"])
    _add_source_options(
        transcript_parser,
        default_source_type=SourceType.VIDEO_CHANNEL,
    )
    _add_common_options(transcript_parser)
    return parser


def _request_from_args(args: argparse.Namespace) -> IngestionRequest:
    path: Path | None = getattr(args, "path", None)
    url: str | None = getattr(args, "url", None)
    if args.command == "file":
        input_type = _input_type_from_path(path, args.input_type)  # type: ignore[arg-type]
    elif args.command == "segments":
        input_type = IngestionInputType.STRUCTURED_SEGMENTS
    elif args.command == "html":
        input_type = IngestionInputType.HTML
    elif args.command == "url":
        input_type = IngestionInputType.URL
    elif args.command == "pdf":
        input_type = IngestionInputType.PDF
    elif args.command == "transcript":
        input_type = _transcript_type(path, args.format)  # type: ignore[arg-type]
    else:  # pragma: no cover - argparse prevents this.
        raise ValueError(f"unknown command: {args.command}")

    max_bytes = None
    if args.max_size_mb is not None:
        if args.max_size_mb <= 0:
            raise ValueError("--max-size-mb must be positive")
        max_bytes = int(args.max_size_mb * 1024 * 1024)

    return IngestionRequest(
        path=path,
        url=url,
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
        max_pages=getattr(args, "max_pages", None),
        page_selection=getattr(args, "pages", None),
        table_mode=PdfTableMode(
            getattr(args, "table_mode", PdfTableMode.BEST_EFFORT.value)
        ),
        content_selector=getattr(args, "content_selector", None),
        allow_private_network=getattr(args, "allow_private_network", False),
        dry_run=args.dry_run,
        created_by=args.created_by,
    )


def _result_text(result: IngestionResult) -> str:
    verb = (
        "Would reuse"
        if result.dry_run and result.reused
        else (
            "Would import"
            if result.dry_run
            else ("Reused" if result.reused else "Imported")
        )
    )
    return (
        f"{verb} {result.content_unit_count} content units from 1 document "
        f"(document_id={result.document_id}, run_id={result.processing_run_id}, "
        f"reused={str(result.reused).lower()}, parse_status={result.parse_status.value})"
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
        print(f"{payload['error_code']}: {payload['error_message']}", file=sys.stderr)


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
