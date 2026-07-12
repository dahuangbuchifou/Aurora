import json

import pytest

from aurora.core.models.common import SCHEMA_VERSION
from aurora.core.schema_registry import (
    MODEL_REGISTRY,
    export_json_schemas,
    export_root_registry,
)


def test_export_json_schemas(tmp_path):
    written = export_json_schemas(tmp_path)
    assert len(written) == len(MODEL_REGISTRY) + 1
    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert registry["schema_version"] == SCHEMA_VERSION
    assert set(registry["objects"]) == {
        object_type.value for object_type in MODEL_REGISTRY
    }


def test_export_root_registry(tmp_path):
    target = export_root_registry(tmp_path)
    registry = json.loads(target.read_text(encoding="utf-8"))
    assert registry["latest"] == "1.1"
    assert registry["versions"]["1.0"] == "v1/registry.json"
    assert registry["versions"]["1.1"] == "v1_1/registry.json"


def test_cannot_regenerate_frozen_v1_schema(tmp_path):
    with pytest.raises(ValueError, match="only export"):
        export_json_schemas(tmp_path, schema_version="1.0")


def test_parse_object_rejects_missing_or_unknown_object_type():
    from aurora.core.schema_registry import parse_object

    with pytest.raises(ValueError, match="missing object_type"):
        parse_object({"schema_version": "1.1"})
    with pytest.raises(ValueError, match="unsupported object_type"):
        parse_object({"schema_version": "1.1", "object_type": "not_real"})


def test_schema_cli_exports_current_version(tmp_path, monkeypatch, capsys):
    from aurora.core import schema_registry

    output = tmp_path / "v1_1"
    root = tmp_path / "schemas"
    monkeypatch.setattr(
        "sys.argv",
        [
            "aurora-export-schemas",
            "--output",
            str(output),
            "--schema-root",
            str(root),
        ],
    )
    schema_registry.main()
    assert (output / "registry.json").exists()
    assert (root / "registry.json").exists()
    assert "Exported 17 object schemas" in capsys.readouterr().out
