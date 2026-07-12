from datetime import date

import pytest
from pydantic import ValidationError

from aurora.core.models import (
    Claim,
    ClaimDimension,
    ClaimType,
    DataPoint,
    DerivationLink,
    DerivationRelationType,
    MeasurementContext,
    MeasurementKind,
    OriginType,
    Provenance,
    TimeRange,
)


def test_measurement_context_supports_financial_scope():
    point = DataPoint(
        metric="revenue",
        value=578.3,
        unit="reported_unit",
        measurement_context=MeasurementContext(
            measurement_kind=MeasurementKind.MONETARY,
            currency="CNY",
            scale_multiplier=100_000_000,
            reporting_standard="CAS",
            attribution_scope="group_total",
            consolidation_scope="consolidated",
        ),
        entity_id="ent_smic",
        period=TimeRange(start=date(2025, 1, 1), end=date(2025, 12, 31)),
        source_ref="cu_report_p15",
    )
    assert point.schema_version == "1.1"
    assert point.measurement_context.currency == "CNY"
    assert point.measurement_context.scale_multiplier == 100_000_000


@pytest.mark.parametrize("currency", ["cny", "CN", "CNY1", "人民币"])
def test_currency_must_be_uppercase_three_letter_code(currency):
    with pytest.raises(ValidationError):
        MeasurementContext(currency=currency)


def test_scale_multiplier_must_be_positive():
    with pytest.raises(ValidationError):
        MeasurementContext(scale_multiplier=0)


def test_claim_dimension_defaults_to_general_and_supports_competition():
    general = Claim(
        claim_type=ClaimType.INTERPRETATION,
        statement="行业周期正在修复。",
        asserted_by="ent_analyst",
        source_ref="cu_001",
    )
    competition = Claim(
        claim_type=ClaimType.INTERPRETATION,
        claim_dimension=ClaimDimension.COMPETITION,
        statement="成熟制程竞争格局正在变化。",
        asserted_by="ent_analyst",
        source_ref="cu_002",
    )
    assert general.claim_dimension == ClaimDimension.GENERAL
    assert competition.claim_dimension == ClaimDimension.COMPETITION


def test_derived_provenance_accepts_structured_link_without_legacy_origins():
    provenance = Provenance(
        origin_type=OriginType.DERIVED,
        derivation_links=[
            DerivationLink(
                object_id="cu_001",
                relation_type=DerivationRelationType.SUMMARIZES,
            )
        ],
    )
    assert provenance.derivation_links[0].relation_type == DerivationRelationType.SUMMARIZES


def test_duplicate_derivation_link_is_rejected():
    link = DerivationLink(
        object_id="cu_001",
        relation_type=DerivationRelationType.DERIVED_FROM,
    )
    with pytest.raises(ValidationError, match="duplicate derivation link"):
        Provenance(
            origin_type=OriginType.DERIVED,
            derivation_links=[link, link],
        )
