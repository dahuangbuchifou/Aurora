from aurora.core.models import Evidence, EvidenceRole, EvidenceType
from aurora.repository import (
    count_independent_evidence,
    effective_independence_group,
    group_independent_evidence,
    validate_independence_groups,
)


def _evidence(eid, role=EvidenceRole.SUPPORT, group="annual_report"):
    return Evidence(
        id=eid,
        evidence_role=role,
        evidence_type=EvidenceType.COMPANY_FILING,
        target_object_id="clm_001",
        source_ref="cu_001",
        summary="披露数据",
        independence_group=group,
    )


def test_same_target_role_and_group_counts_once():
    items = [_evidence("evi_1"), _evidence("evi_2")]
    groups = group_independent_evidence(items)
    assert len(groups) == 1
    assert count_independent_evidence(items) == 1


def test_different_roles_count_separately():
    items = [
        _evidence("evi_1", EvidenceRole.SUPPORT),
        _evidence("evi_2", EvidenceRole.REFUTE),
    ]
    assert count_independent_evidence(items) == 2
    assert count_independent_evidence(items, evidence_role=EvidenceRole.SUPPORT) == 1


def test_blank_legacy_group_is_treated_as_unique_without_crashing():
    first = _evidence("evi_1").model_copy(update={"independence_group": ""})
    second = _evidence("evi_2").model_copy(update={"independence_group": ""})
    assert effective_independence_group(first) == "__evidence__:evi_1"
    assert count_independent_evidence([first, second]) == 2
    report = validate_independence_groups([first, second])
    assert report.empty_group_evidence_ids == ["evi_1", "evi_2"]
