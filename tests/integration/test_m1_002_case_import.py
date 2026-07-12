import json
from jsonschema import Draft202012Validator, FormatChecker
from aurora.core.models.enums import ObjectType
from aurora.repository import ObjectRepository, validate_object_graph
from tests.fixtures.m1_002.loader import SCHEMAS, load_objects, load_raw_objects

def test_all_objects_pass_pydantic_and_json_schema():
    raw_objects=load_raw_objects(); parsed=load_objects()
    assert len(raw_objects)==len(parsed)
    for raw in raw_objects:
        schema=json.loads((SCHEMAS/f"{raw['object_type']}.schema.json").read_text(encoding='utf-8'))
        Draft202012Validator(schema,format_checker=FormatChecker()).validate(raw)

def test_ids_are_unique_and_references_are_complete():
    objects=load_objects(); report=validate_object_graph(objects)
    assert report.duplicate_ids==[]
    assert report.dangling_references==[]
    assert report.derived_without_origins==[]
    assert report.dependency_cycles==[]

def test_all_seventeen_object_types_are_exercised():
    represented={obj.object_type for obj in load_objects()}
    assert represented==set(ObjectType)

def test_repository_import_query_and_roundtrip(db_session):
    repo=ObjectRepository(db_session); objects=load_objects()
    for obj in objects: repo.create(obj)
    db_session.commit()
    assert repo.count()==len(objects)
    for obj in objects:
        restored=repo.get_required(obj.id)
        assert type(restored) is type(obj)
        assert restored.id==obj.id
    assert len(repo.list(object_type=ObjectType.CLAIM,workspace_id=None,limit=1000))>=16
