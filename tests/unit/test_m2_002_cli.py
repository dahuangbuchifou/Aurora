import json
from pathlib import Path

from aurora.cli.ingest import _request_from_args, build_parser, main
from aurora.db import Base, create_db_engine
from aurora.ingestion.contracts import IngestionInputType, PdfTableMode


FIXTURES = Path(__file__).parents[1] / "fixtures" / "m2_002"


def _database(tmp_path: Path) -> str:
    url = f"sqlite:///{tmp_path / 'm2_002_cli.db'}"
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return url


def test_cli_html_json_output(tmp_path: Path, capsys):
    database = _database(tmp_path)
    code = main(
        [
            "html",
            str(FIXTURES / "case_a_web.html"),
            "--source-name",
            "SMIC",
            "--source-type",
            "official_website",
            "--database",
            database,
            "--output",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["parser"]["name"] == "html"
    assert payload["content_unit_count"] > 0
    assert payload["parser_config_hash"]


def test_cli_transcript_and_pdf_commands(tmp_path: Path, capsys):
    database = _database(tmp_path)
    assert main(
        [
            "transcript",
            str(FIXTURES / "case_b_video.vtt"),
            "--source-name",
            "Video",
            "--database",
            database,
            "--output",
            "json",
        ]
    ) == 0
    transcript = json.loads(capsys.readouterr().out)
    assert transcript["parser"]["name"] == "vtt"

    assert main(
        [
            "pdf",
            str(FIXTURES / "case_c_report.pdf"),
            "--source-name",
            "Report",
            "--pages",
            "1",
            "--table-mode",
            "off",
            "--database",
            database,
            "--output",
            "json",
        ]
    ) == 0
    pdf = json.loads(capsys.readouterr().out)
    assert pdf["parser"]["name"] == "pdf"
    assert pdf["parse_status"] == "partially_parsed"


def test_cli_url_request_contract_and_private_flag():
    parser = build_parser()
    args = parser.parse_args(
        [
            "url",
            "https://example.com/a",
            "--source-name",
            "Example",
            "--allow-private-network",
        ]
    )
    request = _request_from_args(args)
    assert request.input_type == IngestionInputType.URL
    assert str(request.url) == "https://example.com/a"
    assert request.allow_private_network is True


def test_cli_pdf_request_options():
    parser = build_parser()
    args = parser.parse_args(
        [
            "pdf",
            "report.pdf",
            "--source-name",
            "Report",
            "--pages",
            "15-18",
            "--max-pages",
            "200",
            "--table-mode",
            "off",
        ]
    )
    request = _request_from_args(args)
    assert request.input_type == IngestionInputType.PDF
    assert request.page_selection == "15-18"
    assert request.max_pages == 200
    assert request.table_mode == PdfTableMode.OFF


def test_cli_transcript_explicit_format_overrides_suffix():
    parser = build_parser()
    args = parser.parse_args(
        [
            "transcript",
            "captions.txt",
            "--format",
            "srt",
            "--source-name",
            "Video",
        ]
    )
    request = _request_from_args(args)
    assert request.input_type == IngestionInputType.SRT
