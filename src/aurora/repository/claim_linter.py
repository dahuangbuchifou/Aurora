"""Advisory Claim atomicity linter.

The linter never blocks storage. It identifies statements that may combine
multiple independently verifiable judgments and should be reviewed manually.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from aurora.core.models import Claim
from aurora.core.models.enums import ClaimType


class LintSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"


@dataclass(frozen=True)
class ClaimLintIssue:
    code: str
    severity: LintSeverity
    message: str


_PREDICTION_TERMS = re.compile(r"预计|预测|未来|将会|有望|可能")
_RECOMMENDATION_TERMS = re.compile(r"买入|卖出|不买|建议|加仓|减仓|回避")
_MULTI_CLAUSE_TERMS = re.compile(r"而且|同时|另外|此外|但是|但|并且|以及")
_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")
_SENTENCE_BREAKS = re.compile(r"[。！？；;]")


def lint_claim_atomicity(claim: Claim) -> list[ClaimLintIssue]:
    issues: list[ClaimLintIssue] = []
    statement = claim.statement.strip()

    if len(statement) > 240:
        issues.append(
            ClaimLintIssue(
                code="CLAIM_TOO_LONG",
                severity=LintSeverity.WARNING,
                message="Claim statement exceeds 240 characters; review atomicity.",
            )
        )

    sentence_count = len([part for part in _SENTENCE_BREAKS.split(statement) if part.strip()])
    if sentence_count > 1:
        issues.append(
            ClaimLintIssue(
                code="MULTIPLE_SENTENCES",
                severity=LintSeverity.WARNING,
                message="Claim contains multiple sentences and may need splitting.",
            )
        )

    if _MULTI_CLAUSE_TERMS.search(statement):
        issues.append(
            ClaimLintIssue(
                code="MULTIPLE_CLAUSE_MARKERS",
                severity=LintSeverity.INFO,
                message="Claim contains conjunctions that may join independent judgments.",
            )
        )

    if _PREDICTION_TERMS.search(statement) and _RECOMMENDATION_TERMS.search(statement):
        issues.append(
            ClaimLintIssue(
                code="MIXED_PREDICTION_RECOMMENDATION",
                severity=LintSeverity.WARNING,
                message="Prediction and action recommendation appear in one Claim.",
            )
        )

    if len(_NUMBER_PATTERN.findall(statement)) > 2:
        issues.append(
            ClaimLintIssue(
                code="MULTIPLE_NUMERIC_ASSERTIONS",
                severity=LintSeverity.INFO,
                message="Claim contains several numeric assertions; consider DataPoints or split Claims.",
            )
        )

    if (
        claim.claim_type == ClaimType.RECOMMENDATION
        and _PREDICTION_TERMS.search(statement)
    ):
        issues.append(
            ClaimLintIssue(
                code="RECOMMENDATION_CONTAINS_FORECAST",
                severity=LintSeverity.INFO,
                message="Recommendation includes forecast language; verify type boundaries.",
            )
        )
    return issues
