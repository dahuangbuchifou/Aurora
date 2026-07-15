"""Aurora persistence layer — Gate 3 draft persistence.

Modules:
- contracts: DraftRecord, DraftTransaction, DraftAction
- identity: stable ID generation (M-C3-01)
- validation: ReviewBundle preflight checks (B03)
- mapper: Candidate → core object mapping (B05)
- source_graph: independence_group computation (B04)
- draft_service: transactional draft persistence (B01/B02/B06/M01)
"""

from aurora.persistence.contracts import DraftAction, DraftRecord, DraftTransaction
from aurora.persistence.draft_service import persist_drafts, persist_drafts_with_separate_run
from aurora.persistence.identity import compute_bundle_operation_key, compute_draft_natural_key
from aurora.persistence.mapper import map_accepted_candidates
from aurora.persistence.source_graph import SourceGraphError, compute_independence_group, resolve_root_source
from aurora.persistence.validation import PreflightError, validate_bundle_preflight

__all__ = [
    "DraftAction",
    "DraftRecord",
    "DraftTransaction",
    "PreflightError",
    "SourceGraphError",
    "compute_bundle_operation_key",
    "compute_draft_natural_key",
    "compute_independence_group",
    "map_accepted_candidates",
    "persist_drafts",
    "persist_drafts_with_separate_run",
    "resolve_root_source",
    "validate_bundle_preflight",
]
