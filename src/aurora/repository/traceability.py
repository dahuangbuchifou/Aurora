"""Reference-graph validation and source traceability for Aurora objects.

This module deliberately remains small. It validates object bundles and follows
explicit IDs; it is not a general-purpose knowledge-graph engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from aurora.core.models import (
    Claim, ContentUnit, DataPoint, Document, Entity, Event, Evidence, Fact,
    Feedback, Insight, KnowledgeObject, OutputArtifact, PersonalOpinion,
    ProcessingRun, Relation, Source, TimelineEntry,
)
from aurora.core.models.common import BaseObject
from aurora.core.models.enums import ObjectType, OriginType
from aurora.repository.object_repository import ObjectRepository

_ID_PREFIXES = (
    "src_", "doc_", "cu_", "ent_", "evt_", "dat_", "clm_", "evi_",
    "fac_", "knw_", "rel_", "tml_", "ins_", "opn_", "out_", "fbk_", "run_",
)

@dataclass(frozen=True)
class ReferenceEdge:
    source_id: str
    target_id: str
    field_name: str
    dependency: bool = True

@dataclass
class GraphValidationReport:
    duplicate_ids: list[str] = field(default_factory=list)
    dangling_references: list[ReferenceEdge] = field(default_factory=list)
    derived_without_origins: list[str] = field(default_factory=list)
    dependency_cycles: list[list[str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (
            self.duplicate_ids
            or self.dangling_references
            or self.derived_without_origins
            or self.dependency_cycles
        )


def looks_like_object_id(value: object) -> bool:
    return isinstance(value, str) and value.startswith(_ID_PREFIXES)


def _append(edges: list[ReferenceEdge], obj: BaseObject, field_name: str,
            values: object, *, dependency: bool = True) -> None:
    if values is None:
        return
    seq = values if isinstance(values, (list, tuple, set)) else [values]
    for value in seq:
        if looks_like_object_id(value):
            edges.append(ReferenceEdge(obj.id, value, field_name, dependency))


def extract_reference_edges(obj: BaseObject) -> list[ReferenceEdge]:
    """Return all explicit object-ID references, including reverse/audit links."""
    edges: list[ReferenceEdge] = []
    _append(edges, obj, "source_refs", obj.source_refs)
    _append(edges, obj, "provenance.origin_object_ids", obj.provenance.origin_object_ids)
    _append(edges, obj, "provenance.processing_run_id", obj.provenance.processing_run_id, dependency=False)

    if isinstance(obj, Document):
        _append(edges, obj, "source_id", obj.source_id)
        _append(edges, obj, "parent_document_id", obj.parent_document_id)
        _append(edges, obj, "duplicate_of_document_id", obj.duplicate_of_document_id)
    elif isinstance(obj, ContentUnit):
        _append(edges, obj, "document_id", obj.document_id)
        _append(edges, obj, "parent_unit_id", obj.parent_unit_id)
    elif isinstance(obj, Entity):
        _append(edges, obj, "possible_same_as", obj.possible_same_as)
    elif isinstance(obj, Event):
        _append(edges, obj, "entity_ids", obj.entity_ids)
    elif isinstance(obj, DataPoint):
        _append(edges, obj, "entity_id", obj.entity_id)
        _append(edges, obj, "source_ref", obj.source_ref)
    elif isinstance(obj, Claim):
        _append(edges, obj, "subject_entity_ids", obj.subject_entity_ids)
        _append(edges, obj, "asserted_by", obj.asserted_by)
        _append(edges, obj, "source_ref", obj.source_ref)
    elif isinstance(obj, Evidence):
        _append(edges, obj, "target_object_id", obj.target_object_id, dependency=False)
        _append(edges, obj, "source_ref", obj.source_ref)
    elif isinstance(obj, Fact):
        _append(edges, obj, "subject_entity_ids", obj.subject_entity_ids)
        _append(edges, obj, "evidence_ids", obj.evidence_ids)
    elif isinstance(obj, KnowledgeObject):
        for name in ("topic_ids", "fact_ids", "data_point_ids", "claim_ids",
                     "evidence_ids", "related_entity_ids"):
            _append(edges, obj, name, getattr(obj, name))
    elif isinstance(obj, Relation):
        _append(edges, obj, "subject_id", obj.subject_id)
        _append(edges, obj, "object_id", obj.object_id)
        _append(edges, obj, "evidence_ids", obj.evidence_ids)
    elif isinstance(obj, TimelineEntry):
        _append(edges, obj, "target_object_id", obj.target_object_id)
        _append(edges, obj, "referenced_object_ids", obj.referenced_object_ids)
    elif isinstance(obj, Insight):
        _append(edges, obj, "supporting_object_ids", obj.supporting_object_ids)
        _append(edges, obj, "counter_evidence_ids", obj.counter_evidence_ids)
    elif isinstance(obj, PersonalOpinion):
        _append(edges, obj, "topic_ids", obj.topic_ids)
        _append(edges, obj, "supporting_ids", obj.supporting_ids)
        _append(edges, obj, "counter_evidence_ids", obj.counter_evidence_ids)
        _append(edges, obj, "previous_version_id", obj.previous_version_id)
    elif isinstance(obj, OutputArtifact):
        _append(edges, obj, "knowledge_refs", obj.knowledge_refs)
        _append(edges, obj, "insight_refs", obj.insight_refs)
        _append(edges, obj, "opinion_refs", obj.opinion_refs)
    elif isinstance(obj, Feedback):
        _append(edges, obj, "target_object_id", obj.target_object_id)
    elif isinstance(obj, ProcessingRun):
        _append(edges, obj, "input_object_ids", obj.input_object_ids)
        _append(edges, obj, "output_object_ids", obj.output_object_ids, dependency=False)
    return edges


def build_object_map(objects: Iterable[BaseObject]) -> tuple[dict[str, BaseObject], list[str]]:
    object_map: dict[str, BaseObject] = {}
    duplicates: list[str] = []
    for obj in objects:
        if obj.id in object_map:
            duplicates.append(obj.id)
        else:
            object_map[obj.id] = obj
    return object_map, sorted(set(duplicates))


def _dependency_graph(objects: Mapping[str, BaseObject]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {object_id: [] for object_id in objects}
    for obj in objects.values():
        graph[obj.id] = [
            edge.target_id for edge in extract_reference_edges(obj)
            if edge.dependency and edge.target_id in objects
        ]
    return graph


def _find_cycles(graph: Mapping[str, list[str]]) -> list[list[str]]:
    color: dict[str, int] = {node: 0 for node in graph}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        color[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if color.get(nxt, 0) == 0:
                visit(nxt)
            elif color.get(nxt) == 1:
                index = stack.index(nxt)
                cycle = stack[index:] + [nxt]
                if cycle not in cycles:
                    cycles.append(cycle)
        stack.pop()
        color[node] = 2

    for node in graph:
        if color[node] == 0:
            visit(node)
    return cycles


def validate_object_graph(objects: Iterable[BaseObject]) -> GraphValidationReport:
    object_list = list(objects)
    object_map, duplicates = build_object_map(object_list)
    dangling: list[ReferenceEdge] = []
    derived_without_origins: list[str] = []
    for obj in object_list:
        for edge in extract_reference_edges(obj):
            if edge.target_id not in object_map:
                dangling.append(edge)
        if obj.provenance.origin_type == OriginType.DERIVED and not obj.provenance.origin_object_ids:
            derived_without_origins.append(obj.id)
    return GraphValidationReport(
        duplicate_ids=duplicates,
        dangling_references=dangling,
        derived_without_origins=derived_without_origins,
        dependency_cycles=_find_cycles(_dependency_graph(object_map)),
    )


def trace_to_sources(start_id: str, object_map: Mapping[str, BaseObject],
                     *, max_depth: int = 64) -> list[list[str]]:
    """Return dependency paths from an object to every reachable Source."""
    if start_id not in object_map:
        raise KeyError(f"unknown object id: {start_id}")
    paths: list[list[str]] = []

    def walk(current: str, path: list[str]) -> None:
        if len(path) > max_depth:
            raise RuntimeError(f"trace depth exceeded for {start_id}")
        obj = object_map[current]
        if isinstance(obj, Source):
            paths.append(path)
            return
        dependencies = [
            edge.target_id for edge in extract_reference_edges(obj)
            if edge.dependency and edge.target_id in object_map
        ]
        for target in dependencies:
            if target not in path:
                walk(target, path + [target])

    walk(start_id, [start_id])
    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for path in paths:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def trace_cognitive_chain(start_id: str, object_map: Mapping[str, BaseObject]) -> list[list[str]]:
    """Alias with domain wording for Opinion/Output → Source tracing."""
    return trace_to_sources(start_id, object_map)


def group_evidence_by_independence(objects: Iterable[BaseObject]) -> dict[str, list[Evidence]]:
    groups: dict[str, list[Evidence]] = {}
    for obj in objects:
        if isinstance(obj, Evidence):
            groups.setdefault(obj.independence_group, []).append(obj)
    return groups


class RepositoryTraceabilityService:
    """Traceability facade over ObjectRepository for M1 validation workflows."""
    def __init__(self, repository: ObjectRepository):
        self.repository = repository

    def load_object_map(self) -> dict[str, BaseObject]:
        objects = self.repository.list(
            workspace_id=None,
            include_deleted=True,
            limit=1000,
        )
        return build_object_map(objects)[0]

    def validate(self) -> GraphValidationReport:
        return validate_object_graph(self.load_object_map().values())

    def trace_to_sources(self, object_id: str) -> list[list[str]]:
        return trace_to_sources(object_id, self.load_object_map())

    def trace_cognitive_chain(self, object_id: str) -> list[list[str]]:
        return trace_cognitive_chain(object_id, self.load_object_map())
