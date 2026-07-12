import json

from aurora.ingestion.schema_registry import CONTRACTS, export_ingestion_schemas


def test_export_ingestion_schemas(tmp_path):
    written = export_ingestion_schemas(tmp_path)
    assert len(written) == len(CONTRACTS) + 1
    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert registry["schema_version"] == "1.0"
    assert set(registry["contracts"]) == set(CONTRACTS)
    structured = json.loads(
        (tmp_path / "structured_segments.schema.json").read_text(encoding="utf-8")
    )
    assert structured["$id"].endswith("structured_segments.schema.json")


def test_ingestion_schema_cli_main(tmp_path, monkeypatch, capsys):
    from aurora.ingestion.schema_registry import main

    target = tmp_path / "schemas"
    monkeypatch.setattr("sys.argv", ["export", "--output", str(target)])
    main()
    assert "Exported 3 ingestion schemas" in capsys.readouterr().out
    assert (target / "registry.json").exists()
