from aurora.core.models import Claim, ClaimType
from aurora.repository import lint_claim_atomicity


def _claim(statement, claim_type=ClaimType.INTERPRETATION):
    return Claim(
        claim_type=claim_type,
        statement=statement,
        asserted_by="ent_analyst",
        source_ref="cu_001",
    )


def test_simple_atomic_claim_has_no_warning():
    assert lint_claim_atomicity(_claim("成熟制程竞争加剧")) == []


def test_mixed_prediction_and_recommendation_is_flagged():
    issues = lint_claim_atomicity(
        _claim("未来利润可能增长，因此建议买入", ClaimType.RECOMMENDATION)
    )
    codes = {issue.code for issue in issues}
    assert "MIXED_PREDICTION_RECOMMENDATION" in codes
    assert "RECOMMENDATION_CONTAINS_FORECAST" in codes


def test_multiple_sentences_and_numbers_are_advisory_only():
    issues = lint_claim_atomicity(
        _claim("收入增长10%。毛利率达到20%；产能利用率为80%。")
    )
    codes = {issue.code for issue in issues}
    assert "MULTIPLE_SENTENCES" in codes
    assert "MULTIPLE_NUMERIC_ASSERTIONS" in codes
