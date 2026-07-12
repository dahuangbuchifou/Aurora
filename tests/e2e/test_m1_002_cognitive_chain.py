from aurora.core.models import Claim, Fact, PersonalOpinion
from aurora.repository import build_object_map, trace_cognitive_chain
from tests.fixtures.m1_002.loader import load_objects

def test_cognitive_chain_and_draft_gate():
    objects=load_objects(); mapping=build_object_map(objects)[0]
    opinion=mapping['opn_m1002_smic_draft']
    assert isinstance(opinion,PersonalOpinion)
    assert opinion.opinion_status.value=='draft'
    assert opinion.confirmed_by_user is False
    paths=trace_cognitive_chain(opinion.id,mapping)
    assert paths
    assert all(path[0]==opinion.id for path in paths)

def test_claim_not_promoted_to_fact():
    objects=load_objects()
    video_claims={obj.id:obj.statement for obj in objects if isinstance(obj,Claim) and obj.id.startswith('clm_m1002_b_')}
    facts=[obj for obj in objects if isinstance(obj,Fact)]
    assert video_claims
    assert all(fact.statement not in set(video_claims.values()) for fact in facts)
    assert all(not fact.id.startswith('fac_m1002_b_') for fact in facts)

def test_growth_and_valuation_are_qualified_not_directly_refuted():
    mapping=build_object_map(load_objects())[0]
    evidence=mapping['evi_m1002_valuation_qualifies_growth']
    assert evidence.evidence_role.value=='qualify'
    assert evidence.target_object_id=='clm_m1002_a_c01'


def test_official_data_refutes_inconsistent_pr_claim():
    mapping=build_object_map(load_objects())[0]
    evidence=mapping['evi_m1002_utilization_refutes_pr_claim']
    claim=mapping['clm_m1002_a_c03']
    assert evidence.evidence_role.value=='refute'
    assert evidence.target_object_id==claim.id
    assert claim.epistemic_status.value=='disputed'
