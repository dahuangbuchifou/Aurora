from aurora.core.models import Claim, DataPoint
from aurora.core.schema_registry import parse_object
from aurora.repository import validate_object_graph
from tests.fixtures.m1_002.loader import load_raw_objects


def test_all_m1_002_v1_0_examples_upgrade_to_v1_1_without_mutating_assets():
    raw_objects = load_raw_objects()
    parsed = [parse_object(raw) for raw in raw_objects]
    assert parsed
    assert all(obj.schema_version == "1.1" for obj in parsed)
    assert all(raw["schema_version"] == "1.0" for raw in raw_objects)
    report = validate_object_graph(parsed)
    assert report.dangling_references == []


def test_v1_0_case_defaults_are_conservative():
    parsed = [parse_object(raw) for raw in load_raw_objects()]
    data_points = [obj for obj in parsed if isinstance(obj, DataPoint)]
    claims = [obj for obj in parsed if isinstance(obj, Claim)]
    assert data_points and claims
    assert all(point.measurement_context.measurement_kind.value == "unknown" for point in data_points)
    assert all(claim.claim_dimension.value == "general" for claim in claims)
