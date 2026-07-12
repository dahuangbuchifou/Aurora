import json
from pathlib import Path

from aurora.cli.ingest import main
from aurora.db.base import Base
from aurora.db.session import create_db_engine


def _database(tmp_path: Path) -> str:
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return url


def test_cli_json_output_and_reuse(tmp_path: Path, capsys):
    path = tmp_path / "cli.md"
    path.write_text("# CLI\n\nText", encoding="utf-8")
    database = _database(tmp_path)
    args = [
        "file",
        str(path),
        "--source-name",
        "CLI Source",
        "--database",
        database,
        "--output",
        "json",
    ]
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["content_unit_count"] == 2
    assert first["reused"] is False
    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["reused"] is True


def test_cli_text_dry_run_and_unsupported_extension(tmp_path: Path, capsys):
    database = _database(tmp_path)
    text_path = tmp_path / "a.txt"
    text_path.write_text("One", encoding="utf-8")
    code = main(
        [
            "file",
            str(text_path),
            "--source-name",
            "Source",
            "--database",
            database,
            "--dry-run",
        ]
    )
    assert code == 0
    assert "Would import 1 content units" in capsys.readouterr().out

    bad = tmp_path / "a.bin"
    bad.write_text("text", encoding="utf-8")
    code = main(
        [
            "file",
            str(bad),
            "--source-name",
            "Source",
            "--database",
            database,
            "--output",
            "json",
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    error = json.loads(captured.err)
    assert error["error_code"] == "INGEST_UNSUPPORTED_CONTENT"


def test_cli_segments_manifest(tmp_path: Path, capsys):
    database = _database(tmp_path)
    path = tmp_path / "segments.json"
    path.write_text(
        json.dumps(
            {
                "source": {"name": "S", "source_type": "local_file"},
                "document": {"title": "D"},
                "segments": [
                    {
                        "sequence_no": 0,
                        "unit_type": "paragraph",
                        "text": "x",
                        "locator": {"paragraph_no": 1},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert main(
        ["segments", str(path), "--database", database, "--output", "json"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["content_unit_count"] == 1


def test_cli_helper_branches_and_warning_output(tmp_path: Path, capsys):
    from aurora.cli.ingest import (
        _input_type_from_path,
        _print_error,
        _print_result,
        build_parser,
    )
    from aurora.ingestion.contracts import IngestionInputType, IngestionRequest, IngestionResult, ParserDescriptor
    from pydantic import ValidationError

    assert _input_type_from_path(tmp_path / "unknown", "text") == IngestionInputType.TEXT

    result = IngestionResult(
        processing_run_id="run_1",
        source_id="src_1",
        document_id="doc_1",
        content_unit_ids=[],
        content_unit_count=0,
        content_hash="abc",
        idempotency_key="key",
        dry_run=False,
        parser=ParserDescriptor(name="text", version="1"),
        warnings=["name differs"],
    )
    _print_result(result, "text")
    captured = capsys.readouterr()
    assert "Imported 0 content units" in captured.out
    assert "warning: name differs" in captured.err

    try:
        IngestionRequest(
            path=tmp_path / "x.md",
            input_type=IngestionInputType.MARKDOWN,
        )
    except ValidationError as error:
        _print_error(error, "json")
    assert json.loads(capsys.readouterr().err)["error_code"] == "INGEST_REQUEST_INVALID"

    _print_error(ValueError("bad option"), "text")
    assert "INGEST_CLI_ERROR" in capsys.readouterr().err

    parser = build_parser()
    args = parser.parse_args(
        [
            "file",
            str(tmp_path / "x.md"),
            "--source-name",
            "S",
            "--max-size-mb",
            "0",
        ]
    )
    from aurora.cli.ingest import _request_from_args
    import pytest
    with pytest.raises(ValueError):
        _request_from_args(args)
