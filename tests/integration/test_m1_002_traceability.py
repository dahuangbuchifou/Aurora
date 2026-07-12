from aurora.core.models import Evidence
from aurora.repository import ObjectRepository, RepositoryTraceabilityService, build_object_map, group_evidence_by_independence, trace_to_sources
from tests.fixtures.m1_002.loader import load_objects

def test_fact_claim_and_output_trace_to_expected_sources():
    objects=load_objects(); mapping=build_object_map(objects)[0]
    fact_paths=trace_to_sources('fac_m1002_c_revenue',mapping)
    assert any(path[-1]=='src_m1002_smic_annual_report' for path in fact_paths)
    claim_paths=trace_to_sources('clm_m1002_b_c07',mapping)
    assert any(path[-1]=='src_m1002_bilibili_up' for path in claim_paths)
    output_paths=trace_to_sources('out_m1002_research_brief',mapping)
    reached={path[-1] for path in output_paths}
    assert {'src_m1002_smic_annual_report','src_m1002_smic_news','src_m1002_bilibili_up'}<=reached

def test_pr_and_annual_report_share_independence_group():
    groups=group_evidence_by_independence(load_objects())
    ids={obj.id for obj in groups['smic_fy2025_revenue']}
    assert {'evi_m1002_a_revenue','evi_m1002_c_revenue'}<=ids

def test_repository_traceability_service(db_session):
    repo=ObjectRepository(db_session)
    for obj in load_objects(): repo.create(obj)
    db_session.commit()
    service=RepositoryTraceabilityService(repo)
    assert service.validate().ok
    paths=service.trace_cognitive_chain('opn_m1002_smic_draft')
    assert any(path[-1]=='src_m1002_smic_annual_report' for path in paths)
    assert any(path[-1]=='src_m1002_bilibili_up' for path in paths)
