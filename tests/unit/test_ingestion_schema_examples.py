import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_ingestion_examples_validate_against_their_schemas():
    root = Path(__file__).resolve().parents[2] / "schemas" / "ingestion" / "v1"
    pairs = [
        ("ingestion_request.schema.json", "ingestion_request.example.json"),
        ("ingestion_result.schema.json", "ingestion_result.example.json"),
        ("structured_segments.schema.json", "structured_segments.example.json"),
    ]
    for schema_name, example_name in pairs:
        schema = json.loads((root / schema_name).read_text(encoding="utf-8"))
        example = json.loads(
            (root / "examples" / example_name).read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(example)
