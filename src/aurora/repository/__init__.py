"""Aurora repositories and validation helpers."""

from .claim_linter import ClaimLintIssue, LintSeverity, lint_claim_atomicity
from .evidence_aggregation import (
    EvidenceGroupKey,
    IndependenceValidationReport,
    count_independent_evidence,
    effective_independence_group,
    group_independent_evidence,
    validate_independence_groups,
)
from .object_repository import (
    ConcurrentUpdateError,
    DuplicateObjectError,
    ObjectNotFoundError,
    ObjectRepository,
    RawObjectRecord,
)
from .traceability import (
    GraphValidationReport,
    ReferenceEdge,
    RepositoryTraceabilityService,
    build_object_map,
    extract_reference_edges,
    group_evidence_by_independence,
    trace_cognitive_chain,
    trace_to_sources,
    validate_object_graph,
)

__all__ = [
    "ObjectRepository",
    "RawObjectRecord",
    "ObjectNotFoundError",
    "DuplicateObjectError",
    "ConcurrentUpdateError",
    "ReferenceEdge",
    "GraphValidationReport",
    "RepositoryTraceabilityService",
    "extract_reference_edges",
    "build_object_map",
    "validate_object_graph",
    "trace_to_sources",
    "trace_cognitive_chain",
    "group_evidence_by_independence",
    "EvidenceGroupKey",
    "IndependenceValidationReport",
    "effective_independence_group",
    "group_independent_evidence",
    "count_independent_evidence",
    "validate_independence_groups",
    "ClaimLintIssue",
    "LintSeverity",
    "lint_claim_atomicity",
]
