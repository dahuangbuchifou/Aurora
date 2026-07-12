import json
from pathlib import Path

from aurora.ingestion.schema_registry import (
    CONTRACTS,
    INGESTION_CONTRACT_VERSION,
    export_ingestion_schemas,
)


def test_export_ingestion_schemas_emits_deterministic_v1_1_registry(tmp_path):
    written = export_ingestion_schemas(tmp_path)
    assert len(written) == len(CONTRACTS) + 1

    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert INGESTION_CONTRACT_VERSION == "1.1"
    assert registry["schema_version"] == "1.1"
    assert set(registry["contracts"]) == set(CONTRACTS)

    structured = json.loads(
        (tmp_path / "structured_segments.schema.json").read_text(encoding="utf-8")
    )
    assert structured["$id"].endswith(
        "/schemas/ingestion/v1_1/structured_segments.schema.json"
    )


def test_checked_in_ingestion_registries_are_version_specific():
    root = Path(__file__).resolve().parents[2] / "schemas" / "ingestion"
    frozen_v1 = json.loads((root / "v1" / "registry.json").read_text(encoding="utf-8"))
    current_v1_1 = json.loads(
        (root / "v1_1" / "registry.json").read_text(encoding="utf-8")
    )
    top_level = json.loads((root / "registry.json").read_text(encoding="utf-8"))

    assert frozen_v1["schema_version"] == "1.0"
    assert current_v1_1["schema_version"] == "1.1"
    assert top_level["latest"] == "1.1"
    assert top_level["versions"] == {
        "1.0": "v1/registry.json",
        "1.1": "v1_1/registry.json",
    }


def test_ingestion_schema_cli_main_defaults_to_v1_1(tmp_path, monkeypatch, capsys):
    from aurora.ingestion.schema_registry import main

    target = tmp_path / "schemas"
    monkeypatch.setattr("sys.argv", ["export", "--output", str(target)])
    main()
    assert "Exported 3 ingestion schemas" in capsys.readouterr().out
    registry = json.loads((target / "registry.json").read_text(encoding="utf-8"))
    assert registry["schema_version"] == "1.1"
