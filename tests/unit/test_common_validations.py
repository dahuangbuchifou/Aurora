from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from aurora.core.models import (
    HumanReview,
    HumanReviewStatus,
    LifecycleStatus,
    MeasurementContext,
    Source,
    SourceLocator,
    SourceType,
    TimeRange,
    ValidityWindow,
)


def test_human_review_requires_reviewer_and_time():
    with pytest.raises(ValidationError):
        HumanReview(status=HumanReviewStatus.REVIEWED)
    review = HumanReview(
        status=HumanReviewStatus.REVIEWED,
        reviewed_by="user",
        reviewed_at=datetime.now(UTC),
    )
    assert review.reviewed_by == "user"


def test_locator_requires_position_and_orders_ranges():
    with pytest.raises(ValidationError, match="at least one"):
        SourceLocator()
    with pytest.raises(ValidationError, match="end_seconds"):
        SourceLocator(start_seconds=10, end_seconds=5)
    with pytest.raises(ValidationError, match="line_end"):
        SourceLocator(line_start=10, line_end=5)


def test_time_and_validity_ranges_reject_reverse_order():
    with pytest.raises(ValidationError, match="time range"):
        TimeRange(start=date(2026, 2, 1), end=date(2026, 1, 1))
    with pytest.raises(ValidationError, match="valid_to"):
        ValidityWindow(
            as_of_date=date(2026, 1, 1),
            valid_from=date(2026, 2, 1),
            valid_to=date(2026, 1, 1),
        )


def test_measurement_context_accepts_explicit_none_currency():
    assert MeasurementContext(currency=None).currency is None


def test_base_object_state_validation():
    now = datetime.now(UTC)
    with pytest.raises(ValidationError, match="schema_version"):
        Source(
            name="Bad Version",
            source_type=SourceType.BLOG,
            schema_version="1.0",
        )
    with pytest.raises(ValidationError, match="updated_at"):
        Source(
            name="Bad Time",
            source_type=SourceType.BLOG,
            created_at=now,
            updated_at=now - timedelta(seconds=1),
        )
    with pytest.raises(ValidationError, match="deleted_at is required"):
        Source(
            name="Deleted",
            source_type=SourceType.BLOG,
            status=LifecycleStatus.DELETED,
        )
    with pytest.raises(ValidationError, match="must be null"):
        Source(
            name="Active",
            source_type=SourceType.BLOG,
            deleted_at=now,
        )
