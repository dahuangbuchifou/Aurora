"""Coverage gap tests for mapper.py — target 75% → 90%+.

Tests for: _safe_enum across all enum types, _convert_time_horizon branches,
map_entity, map_data_point, map_claim, map_evidence, map_accepted_candidates.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from pydantic_core import ValidationError as PydanticValidationError

from aurora.core.models.common import TimeRange
from aurora.core.models.enums import (
    ClaimType,
    EntityType,
    EvidenceRole,
    EvidenceType,
)
from aurora.extraction.candidates import (
    ClaimCandidate,
    DataPointCandidate,
    EntityCandidate,
    EvidenceCandidate,
)
from aurora.persistence.mapper import (
    _convert_time_horizon,
    _parse_period_string,
    _safe_enum,
    map_accepted_candidates,
    map_claim,
    map_data_point,
    map_entity,
    map_evidence,
)


# ── _safe_enum across all enum types ─────────────────────────────────────────


class TestSafeEnum:
    def test_entity_type_valid(self):
        assert _safe_enum(EntityType, "company") == EntityType.COMPANY

    def test_entity_type_invalid(self):
        assert _safe_enum(EntityType, "not_a_type") is None

    def test_entity_type_none(self):
        assert _safe_enum(EntityType, None) is None

    def test_entity_type_empty(self):
        assert _safe_enum(EntityType, "") is None

    def test_claim_type_valid(self):
        """Cover _safe_enum with ClaimType enum."""
        assert _safe_enum(ClaimType, "prediction") == ClaimType.PREDICTION

    def test_claim_type_invalid(self):
        assert _safe_enum(ClaimType, "invalid_claim_type") is None

    def test_evidence_role_valid(self):
        """Cover _safe_enum with EvidenceRole enum."""
        assert _safe_enum(EvidenceRole, "support") == EvidenceRole.SUPPORT

    def test_evidence_type_valid(self):
        """Cover _safe_enum with EvidenceType enum."""
        assert _safe_enum(EvidenceType, "direct_quote") == EvidenceType.DIRECT_QUOTE

    def test_evidence_type_invalid(self):
        assert _safe_enum(EvidenceType, "not_an_evidence_type") is None


# ── _convert_time_horizon ────────────────────────────────────────────────────


class TestConvertTimeHorizon:
    def test_none(self):
        """_convert_time_horizon with None → None."""
        assert _convert_time_horizon(None) is None

    def test_empty_dict(self):
        """Empty dict → TimeRange with no dates."""
        tr = _convert_time_horizon({})
        assert tr is not None
        assert tr.start is None
        assert tr.end is None

    def test_with_string_dates(self):
        """Date strings in YYYY-MM-DD format."""
        tr = _convert_time_horizon({"start": "2025-01-15", "end": "2025-06-30"})
        assert tr is not None
        assert tr.start == datetime(2025, 1, 15)
        assert tr.end == datetime(2025, 6, 30)

    def test_with_year_month_format(self):
        """Date strings in YYYY-MM format."""
        tr = _convert_time_horizon({"start": "2025-01", "end": "2025-12"})
        assert tr is not None
        assert tr.start == datetime(2025, 1, 1)
        assert tr.end == datetime(2025, 12, 1)

    def test_with_year_only_format(self):
        """Date strings in YYYY format."""
        tr = _convert_time_horizon({"start": "2025", "end": "2026"})
        assert tr is not None
        assert tr.start == datetime(2025, 1, 1)
        assert tr.end == datetime(2026, 1, 1)

    def test_with_datetime_objects(self):
        """Already datetime objects passed through."""
        dt_start = datetime(2025, 3, 15)
        dt_end = datetime(2025, 9, 30)
        tr = _convert_time_horizon({"start": dt_start, "end": dt_end})
        assert tr.start == dt_start
        assert tr.end == dt_end

    def test_with_timestamp_numbers(self):
        """Numeric timestamp → datetime."""
        ts_start = datetime(2025, 1, 1).timestamp()
        ts_end = datetime(2025, 12, 31).timestamp()
        tr = _convert_time_horizon({"start": ts_start, "end": ts_end})
        assert tr is not None
        assert tr.start is not None
        assert tr.end is not None

    def test_with_invalid_date_string(self):
        """Invalid date string → None for that field."""
        tr = _convert_time_horizon({"start": "not_a_date", "end": "2025-06-30"})
        assert tr is not None
        assert tr.start is None
        assert tr.end == datetime(2025, 6, 30)

    def test_with_precision_granularity(self):
        """Precision field used from dict."""
        tr = _convert_time_horizon({
            "start": "2025-01-01", "end": "2025-12-31",
            "precision": "day"
        })
        assert tr is not None

    def test_with_granularity_fallback(self):
        """Granularity as fallback for precision."""
        tr = _convert_time_horizon({
            "start": "2025-01-01", "end": "2025-12-31",
            "granularity": "month"
        })
        assert tr is not None


# ── map_entity ───────────────────────────────────────────────────────────────


class TestMapEntity:
    def test_valid_entity(self):
        """Map valid entity → returns Entity with correct fields."""
        c = EntityCandidate(canonical_name="Test Corp", entity_type="company")
        e = map_entity("cid1", c)
        assert e.entity_type == EntityType.COMPANY
        assert e.canonical_name == "Test Corp"

    def test_unknown_entity_type_raises_validation(self):
        """Unknown entity_type → entity_type=None → Pydantic rejects."""
        c = EntityCandidate(canonical_name="Unknown Type", entity_type="weird_type")
        with pytest.raises(PydanticValidationError):
            map_entity("cid2", c)


# ── map_data_point ───────────────────────────────────────────────────────────


class TestMapDataPoint:
    def test_basic(self):
        """Basic DataPoint mapping."""
        c = DataPointCandidate(
            metric="revenue", value=100.0, unit="CNY",
            entity_id="ent1", period="2025Q3",
            measurement_context={}, source_quote="Q"
        )
        dp = map_data_point("dp1", c)
        assert dp.metric == "revenue"
        assert dp.value == 100.0
        assert dp.unit == "CNY"
        assert dp.entity_id == "ent1"
        assert dp.period is not None
        assert dp.source_ref == "candidate:dp1"

    def test_period_time_range_branch(self):
        """When candidate has period_time_range attr (via mock)."""
        ptr = TimeRange(start=datetime(2025, 1, 1), end=datetime(2025, 12, 31))
        mc = MagicMock()
        mc.metric = "revenue"
        mc.value = 200.0
        mc.unit = "USD"
        mc.entity_id = "ent2"
        mc.period_time_range = ptr
        mc.period = None
        mc.measurement_context = None
        dp = map_data_point("dp_pt", mc)
        assert dp.period == ptr

    def test_str_period_conversion(self):
        """String period converted via _parse_period_string."""
        c = DataPointCandidate(
            metric="rev", value=300.0, unit="CNY",
            entity_id="ent1", period="2025H1",
            measurement_context={}, source_quote="Q"
        )
        dp = map_data_point("dp_h1", c)
        assert dp.period is not None
        assert dp.period.start.month == 1

    def test_period_str_branch_mock(self):
        """Period as str goes through _parse_period_string via mock."""
        mc = MagicMock()
        mc.metric = "m"
        mc.value = 1.0
        mc.unit = "u"
        mc.entity_id = "e1"
        mc.period_time_range = None
        mc.period = "2025Q3"
        mc.measurement_context = None
        dp = map_data_point("dp_s", mc)
        assert dp.period is not None
        assert dp.period.start.month == 7

    def test_with_measurement_context(self):
        """Measurement context passed through when set."""
        from aurora.core.models.common import MeasurementContext as MC
        c = DataPointCandidate(
            metric="rev", value=400.0, unit="CNY",
            entity_id="ent1", period="2025",
            measurement_context=MC().model_dump(), source_quote="Q"
        )
        dp = map_data_point("dp_mc", c)
        assert dp.measurement_context is not None

    def test_none_period_raises_validation(self):
        """DataPoint with None period fails Pydantic validation."""
        mc = MagicMock()
        mc.metric = "rev"
        mc.value = 50.0
        mc.unit = "CNY"
        mc.entity_id = "ent1"
        mc.period_time_range = None
        mc.period = None
        mc.measurement_context = None
        with pytest.raises(PydanticValidationError):
            map_data_point("dp_none", mc)


# ── map_claim ────────────────────────────────────────────────────────────────


class TestMapClaim:
    def test_basic(self):
        """Basic claim mapping."""
        c = ClaimCandidate(
            claim_type="prediction", statement="Will grow 20%",
            asserted_by="Analyst A", claim_dimension="factual",
            time_horizon={"start": "2025-01-01", "end": "2025-12-31"},
            source_quote="Will grow 20%",
        )
        cl = map_claim("cl1", c)
        assert cl.claim_type == ClaimType.PREDICTION
        assert cl.statement == "Will grow 20%"
        assert cl.asserted_by == "Analyst A"
        assert cl.source_ref == "candidate:cl1"
        assert cl.time_horizon is not None

    def test_no_time_horizon_non_prediction(self):
        """Claim of non-prediction type without time_horizon passes."""
        c = ClaimCandidate(
            claim_type="fact_claim", statement="A fact",
            asserted_by="Analyst B", claim_dimension="factual",
            time_horizon=None,
            source_quote="A fact",
        )
        cl = map_claim("cl_noth", c)
        assert cl.time_horizon is None

    def test_prediction_no_time_horizon_raises(self):
        """Prediction claim without time_horizon → Pydantic rejects."""
        c = ClaimCandidate(
            claim_type="prediction", statement="Will grow",
            asserted_by="Analyst C", claim_dimension="factual",
            time_horizon=None,
            source_quote="Will grow",
        )
        with pytest.raises(PydanticValidationError):
            map_claim("cl_fail", c)

    def test_claimant_name_fallback(self):
        """asserted_by falls back to claimant_name if asserted_by empty."""
        c = ClaimCandidate(
            claim_type="fact_claim", statement="S",
            asserted_by="", claimant_name="Claimant X",
            claim_dimension="factual",
            time_horizon=None, source_quote="S",
        )
        cl = map_claim("cl3", c)
        assert cl.asserted_by == "Claimant X"

    def test_invalid_claim_type_raises_validation(self):
        """Invalid claim_type → None → Pydantic rejects."""
        c = ClaimCandidate(
            claim_type="unknown_type", statement="S",
            asserted_by="A", claim_dimension="factual",
            time_horizon=None, source_quote="S",
        )
        with pytest.raises(PydanticValidationError):
            map_claim("cl4", c)

    def test_empty_statement_rejected(self):
        """Claim with empty statement → Pydantic rejects."""
        c = ClaimCandidate(
            claim_type="fact_claim", statement="",
            asserted_by="A", claim_dimension="factual",
            time_horizon=None, source_quote="",
        )
        with pytest.raises(PydanticValidationError):
            map_claim("cl5", c)


# ── map_evidence ─────────────────────────────────────────────────────────────


class TestMapEvidence:
    def test_basic(self):
        """Basic evidence mapping."""
        c = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id="target1", independence_group="",
            source_quote="Source text", note="A note",
        )
        ev = map_evidence("ev1", c, independence_group="ig_test")
        assert ev.evidence_role == EvidenceRole.SUPPORT
        assert ev.evidence_type == EvidenceType.DIRECT_QUOTE
        assert ev.target_object_id == "target1"
        assert ev.source_ref == "candidate:ev1"
        assert ev.independence_group == "ig_test"

    def test_with_candidate_to_core_map(self):
        """target_object_id resolved via candidate_to_core map."""
        c = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id="target_cand", independence_group="",
            source_quote="Source text",
        )
        c2c = {"target_cand": "core_obj_123"}
        ev = map_evidence("ev2", c, candidate_to_core=c2c, independence_group="ig_test")
        assert ev.target_object_id == "core_obj_123"

    def test_candidate_to_core_no_match(self):
        """target not in candidate_to_core → uses original."""
        c = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id="unknown_cand", independence_group="",
            source_quote="Source text",
        )
        c2c = {"other": "core_other"}
        ev = map_evidence("ev3", c, candidate_to_core=c2c, independence_group="ig_test")
        assert ev.target_object_id == "unknown_cand"

    def test_invalid_role_and_type(self):
        """Invalid enum values → None → Pydantic rejects."""
        c = EvidenceCandidate(
            evidence_role="bad_role", evidence_type="bad_type",
            target_object_id="t1", independence_group="",
            source_quote="Q",
        )
        with pytest.raises(PydanticValidationError):
            map_evidence("ev4", c, independence_group="ig_test")

    def test_independence_group_placeholder(self):
        """independence_group is provided from SourceGraph resolution."""
        c = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id="t1", independence_group="",
            source_quote="Q",
        )
        ev = map_evidence("ev5", c, independence_group="resolved_ig_001")
        assert ev.independence_group == "resolved_ig_001"

    def test_source_quote_or_note_fallback(self):
        """Summary uses source_quote or note."""
        c1 = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id="t1", independence_group="",
            source_quote="Full quote", note="Short note",
        )
        ev1 = map_evidence("ev6", c1, independence_group="ig_test")
        assert ev1.summary == "Full quote"

        c2 = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id="t1", independence_group="",
            source_quote="", note="Only note",
        )
        ev2 = map_evidence("ev7", c2, independence_group="ig_test")
        assert ev2.summary == "Only note"


# ── map_accepted_candidates ──────────────────────────────────────────────────


class TestMapAcceptedCandidates:
    def test_empty(self):
        """Empty accepted list → empty results."""
        entities, dps, claims, evs, c2c = map_accepted_candidates([], [])
        assert entities == []
        assert dps == []
        assert claims == []
        assert evs == []
        assert c2c == {}

    def test_all_types(self):
        """Full mapping with all candidate types."""
        ent = EntityCandidate(canonical_name="Test Entity", entity_type="company")
        dp = DataPointCandidate(
            metric="revenue", value=100.0, unit="CNY",
            entity_id=ent.candidate_id, period="2025Q3",
            measurement_context={}, source_quote="Q"
        )
        cl = ClaimCandidate(
            claim_type="prediction", statement="Will grow 20%",
            asserted_by="Analyst", claim_dimension="factual",
            time_horizon={"start": "2025-01-01", "end": "2025-12-31"},
            source_quote="Will grow 20%"
        )
        ev = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id=cl.candidate_id, independence_group="",
            source_quote="Backing evidence", source_unit_id="default",
        )

        all_candidates = [ent, dp, cl, ev]
        acc_ids = [ent.candidate_id, dp.candidate_id, cl.candidate_id, ev.candidate_id]

        entities, dps, claims, evs, c2c = map_accepted_candidates(acc_ids, all_candidates,
            independence_group_map={"default": "resolved_ig"})

        assert len(entities) == 1
        assert len(dps) == 1
        assert len(claims) == 1
        assert len(evs) == 1
        assert len(c2c) == 4

        # Evidence target should be resolved via c2c
        assert evs[0].target_object_id == claims[0].id

    def test_not_in_accepted_skipped(self):
        """Candidates not in accepted list are skipped."""
        ent = EntityCandidate(canonical_name="Test", entity_type="company")
        all_candidates = [ent]
        acc_ids = ["some_other_id"]

        entities, dps, claims, evs, c2c = map_accepted_candidates(acc_ids, all_candidates)

        assert len(entities) == 0
        assert len(c2c) == 0

    def test_entity_only(self):
        """Only entities accepted."""
        ent = EntityCandidate(canonical_name="E1", entity_type="organization")
        acc_ids = [ent.candidate_id]
        entities, dps, claims, evs, c2c = map_accepted_candidates(acc_ids, [ent])
        assert len(entities) == 1
        assert len(dps) == 0
        assert c2c[ent.candidate_id] == entities[0].id

    def test_dependency_order(self):
        """DataPoint mapped after Entity, Evidence after Claim."""
        ent = EntityCandidate(canonical_name="E", entity_type="person")
        dp = DataPointCandidate(
            metric="m", value=1.0, unit="u",
            entity_id=ent.candidate_id, period="2025",
            measurement_context={}, source_quote="Q"
        )
        cl = ClaimCandidate(
            claim_type="prediction", statement="S",
            asserted_by="A", claim_dimension="factual",
            time_horizon={"start": "2025-01-01", "end": "2025-12-31"},
            source_quote="S"
        )
        ev = EvidenceCandidate(
            evidence_role="support", evidence_type="direct_quote",
            target_object_id=cl.candidate_id, independence_group="",
            source_quote="Q", source_unit_id="default",
        )

        all_c = [ent, dp, cl, ev]
        acc_ids = [ent.candidate_id, dp.candidate_id, cl.candidate_id, ev.candidate_id]

        entities, dps, claims, evs, c2c = map_accepted_candidates(acc_ids, all_c,
            independence_group_map={"default": "resolved_ig"})
        assert len(entities) == 1
        assert len(dps) == 1
        assert len(claims) == 1
        assert len(evs) == 1
        # Evidence should reference the mapped claim's core ID
