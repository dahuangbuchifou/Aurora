import json
from pathlib import Path

from jsonschema import Draft202012Validator


def _validate(schema_path: Path, example_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(example)


def test_frozen_v1_ingestion_examples_remain_valid():
    root = Path(__file__).resolve().parents[2] / "schemas" / "ingestion" / "v1"
    pairs = [
        ("ingestion_request.schema.json", "ingestion_request.example.json"),
        ("ingestion_result.schema.json", "ingestion_result.example.json"),
        ("structured_segments.schema.json", "structured_segments.example.json"),
    ]
    for schema_name, example_name in pairs:
        _validate(root / schema_name, root / "examples" / example_name)


def test_v1_1_multicarrier_request_examples_validate():
    root = Path(__file__).resolve().parents[2] / "schemas" / "ingestion" / "v1_1"
    for example_name in [
        "html_request.example.json",
        "pdf_request.example.json",
        "transcript_request.example.json",
    ]:
        _validate(
            root / "ingestion_request.schema.json",
            root / "examples" / example_name,
        )


def test_v1_1_ingestion_result_example_validates():
    root = Path(__file__).resolve().parents[2] / "schemas" / "ingestion" / "v1_1"
    _validate(
        root / "ingestion_result.schema.json",
        root / "examples" / "ingestion_result.example.json",
    )
