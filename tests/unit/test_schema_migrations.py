from copy import deepcopy

import pytest

from aurora.core.models import Claim, DataPoint
from aurora.core.schema_migrations import (
    MissingSchemaVersionError,
    UnsupportedSchemaVersionError,
    upgrade_payload,
    upgrade_payload_v1_0_to_v1_1,
)
from aurora.core.schema_registry import parse_object


BASE = {
    "id": "dat_legacy",
    "object_type": "data_point",
    "schema_version": "1.0",
    "status": "active",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "created_by": "system",
    "workspace_id": "default",
    "language": "zh-CN",
    "tags": [],
    "source_refs": [],
    "provenance": {
        "origin_type": "derived",
        "origin_object_ids": ["cu_001", "cu_001"],
        "processing_run_id": None,
        "human_review": {"status": "not_reviewed", "reviewed_by": None, "reviewed_at": None, "note": None},
        "derivation_note": None,
        "source_locator_required": False,
    },
    "privacy_level": "internal",
    "deleted_at": None,
    "external_ids": {},
    "metadata": {},
    "metric": "revenue",
    "value": 578.3,
    "unit": "亿元",
    "entity_id": "ent_smic",
    "period": {"start": "2025-01-01", "end": "2025-12-31", "precision": "year"},
    "reported_at": None,
    "calculation_method": "reported",
    "calculation_expression": None,
    "source_ref": "cu_001",
    "audited": True,
}


def test_upgrade_data_point_is_conservative_and_does_not_mutate_input():
    original = deepcopy(BASE)
    upgraded = upgrade_payload_v1_0_to_v1_1(BASE)
    assert BASE == original
    assert upgraded["schema_version"] == "1.1"
    assert upgraded["measurement_context"]["measurement_kind"] == "unknown"
    assert upgraded["measurement_context"]["currency"] is None
    links = upgraded["provenance"]["derivation_links"]
    assert len(links) == 1
    assert links[0]["relation_type"] == "derived_from"


def test_parse_legacy_data_point_returns_current_model():
    parsed = parse_object(BASE)
    assert isinstance(parsed, DataPoint)
    assert parsed.schema_version == "1.1"
    assert parsed.measurement_context.currency is None


def test_upgrade_legacy_claim_adds_general_dimension():
    payload = deepcopy(BASE)
    payload.update(
        {
            "id": "clm_legacy",
            "object_type": "claim",
            "claim_type": "interpretation",
            "statement": "成熟制程竞争加剧。",
            "subject_entity_ids": ["ent_smic"],
            "asserted_by": "ent_analyst",
            "asserted_at": None,
            "time_horizon": None,
            "conditions": [],
            "source_ref": "cu_001",
            "direct_quote": False,
            "epistemic_status": "asserted",
        }
    )
    for key in [
        "metric", "value", "unit", "entity_id", "period", "reported_at",
        "calculation_method", "calculation_expression", "audited",
    ]:
        payload.pop(key, None)
    parsed = parse_object(payload)
    assert isinstance(parsed, Claim)
    assert parsed.claim_dimension.value == "general"


def test_missing_and_unknown_versions_fail_explicitly():
    with pytest.raises(MissingSchemaVersionError):
        upgrade_payload({"object_type": "source"})
    with pytest.raises(UnsupportedSchemaVersionError):
        upgrade_payload({"schema_version": "9.9", "object_type": "source"})


def test_current_payload_returns_copy():
    payload = {"schema_version": "1.1", "object_type": "source"}
    copied = upgrade_payload(payload)
    assert copied == payload
    assert copied is not payload


def test_v1_0_adapter_rejects_wrong_version_and_object_type():
    with pytest.raises(UnsupportedSchemaVersionError):
        upgrade_payload_v1_0_to_v1_1({"schema_version": "1.1", "object_type": "source"})
    with pytest.raises(ValueError, match="unsupported object_type"):
        upgrade_payload_v1_0_to_v1_1({"schema_version": "1.0", "object_type": "unknown_x"})


def test_invalid_origin_list_is_not_invented():
    payload = deepcopy(BASE)
    payload["provenance"]["origin_object_ids"] = "cu_not_a_list"
    upgraded = upgrade_payload_v1_0_to_v1_1(payload)
    assert upgraded["provenance"]["derivation_links"] == []
