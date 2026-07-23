from __future__ import annotations

import inspect
from dataclasses import MISSING, fields
from typing import get_type_hints

from aurora.persistence.contracts import DraftAction, DraftRecord, DraftTransaction


def test_persistence_contract_public_signatures_are_frozen() -> None:
    assert tuple(DraftAction.__members__) == ("CREATED", "REUSED")
    assert {
        name: member.value for name, member in DraftAction.__members__.items()
    } == {
        "CREATED": 1,
        "REUSED": 2,
    }

    draft_record_fields = fields(DraftRecord)
    assert tuple(field.name for field in draft_record_fields) == (
        "object_type",
        "object_id",
        "stable_identity_hash",
        "action",
        "candidate_id",
    )
    assert get_type_hints(DraftRecord) == {
        "object_type": str,
        "object_id": str,
        "stable_identity_hash": str,
        "action": DraftAction,
        "candidate_id": str | None,
    }
    assert tuple(field.default for field in draft_record_fields) == (
        MISSING,
        MISSING,
        MISSING,
        MISSING,
        None,
    )
    assert tuple(field.default_factory for field in draft_record_fields) == (
        MISSING,
        MISSING,
        MISSING,
        MISSING,
        MISSING,
    )
    assert DraftRecord.__dataclass_params__.frozen is True

    draft_record_signature = inspect.signature(DraftRecord)
    assert tuple(
        (parameter.name, parameter.kind, parameter.default)
        for parameter in draft_record_signature.parameters.values()
    ) == (
        (
            "object_type",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.empty,
        ),
        ("object_id", inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.empty),
        (
            "stable_identity_hash",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.empty,
        ),
        ("action", inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.empty),
        ("candidate_id", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
    )

    draft_transaction_fields = fields(DraftTransaction)
    assert tuple(field.name for field in draft_transaction_fields) == (
        "records",
        "total_objects",
        "created_count",
        "reused_count",
        "processing_run_id",
        "succeeded",
        "error_message",
    )
    assert get_type_hints(DraftTransaction) == {
        "records": tuple[DraftRecord, ...],
        "total_objects": int,
        "created_count": int,
        "reused_count": int,
        "processing_run_id": str,
        "succeeded": bool,
        "error_message": str | None,
    }
    assert tuple(field.default for field in draft_transaction_fields) == (
        MISSING,
        MISSING,
        MISSING,
        MISSING,
        MISSING,
        True,
        None,
    )
    assert tuple(field.default_factory for field in draft_transaction_fields) == (
        MISSING,
        MISSING,
        MISSING,
        MISSING,
        MISSING,
        MISSING,
        MISSING,
    )
    assert DraftTransaction.__dataclass_params__.frozen is True

    draft_transaction_signature = inspect.signature(DraftTransaction)
    assert tuple(
        (parameter.name, parameter.kind, parameter.default)
        for parameter in draft_transaction_signature.parameters.values()
    ) == (
        ("records", inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.empty),
        (
            "total_objects",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.empty,
        ),
        (
            "created_count",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.empty,
        ),
        (
            "reused_count",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.empty,
        ),
        (
            "processing_run_id",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.empty,
        ),
        ("succeeded", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
        ("error_message", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
    )

    is_empty_descriptor = DraftTransaction.__dict__["is_empty"]
    assert isinstance(is_empty_descriptor, property)
    assert is_empty_descriptor.fget is not None
    assert get_type_hints(is_empty_descriptor.fget)["return"] is bool


def test_draft_transaction_empty_contract() -> None:
    record = DraftRecord(
        object_type="claim",
        object_id="cl_test_001",
        stable_identity_hash="a" * 64,
        action=DraftAction.CREATED,
        candidate_id="cl_cand_test_001",
    )

    empty_success = DraftTransaction(
        records=(),
        total_objects=0,
        created_count=0,
        reused_count=0,
        processing_run_id="pr_empty_success",
        succeeded=True,
    )
    empty_failure = DraftTransaction(
        records=(),
        total_objects=0,
        created_count=0,
        reused_count=0,
        processing_run_id="pr_empty_failure",
        succeeded=False,
        error_message="expected failure",
    )
    non_empty_success = DraftTransaction(
        records=(record,),
        total_objects=1,
        created_count=1,
        reused_count=0,
        processing_run_id="pr_non_empty_success",
        succeeded=True,
    )
    non_empty_failure = DraftTransaction(
        records=(record,),
        total_objects=1,
        created_count=0,
        reused_count=1,
        processing_run_id="pr_non_empty_failure",
        succeeded=False,
        error_message="expected failure",
    )

    records_present_zero_total = DraftTransaction(
        records=(record,),
        total_objects=0,
        created_count=0,
        reused_count=0,
        processing_run_id="pr_records_present_zero_total",
        succeeded=True,
    )
    records_empty_nonzero_total = DraftTransaction(
        records=(),
        total_objects=1,
        created_count=0,
        reused_count=0,
        processing_run_id="pr_records_empty_nonzero_total",
        succeeded=True,
    )

    assert empty_success.is_empty is True
    assert empty_failure.is_empty is True
    assert non_empty_success.is_empty is False
    assert non_empty_failure.is_empty is False
    assert type(empty_success.is_empty) is bool
    assert type(empty_failure.is_empty) is bool
    assert type(non_empty_success.is_empty) is bool
    assert type(non_empty_failure.is_empty) is bool
    assert records_present_zero_total.is_empty is True
    assert type(records_present_zero_total.is_empty) is bool
    assert records_empty_nonzero_total.is_empty is False
    assert type(records_empty_nonzero_total.is_empty) is bool
