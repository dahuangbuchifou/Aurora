import json

from aurora.core.schema_registry import MODEL_REGISTRY, export_json_schemas


def test_export_json_schemas(tmp_path):
    written = export_json_schemas(tmp_path)
    assert len(written) == len(MODEL_REGISTRY) + 1
    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert registry["schema_version"] == "1.0"
    assert set(registry["objects"]) == {
        object_type.value for object_type in MODEL_REGISTRY
    }
