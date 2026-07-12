import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from aurora.core.schema_registry import parse_object


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "schemas" / "examples" / "v1_1"
SCHEMAS = ROOT / "schemas" / "v1_1"


def test_v1_1_examples_pass_pydantic_and_json_schema():
    files = sorted(EXAMPLES.glob("*.json"))
    assert len(files) == 3
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        schema = json.loads(
            (SCHEMAS / f"{payload['object_type']}.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(payload)
        parsed = parse_object(payload)
        assert parsed.schema_version == "1.1"
