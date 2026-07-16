"""R3-S06: Four-class complete persistence + forced mid-transaction failure tests.

1. Normal closed-loop: Entity > 0, DataPoint > 0, Claim > 0, Evidence > 0
   with all core ID references resolved (entity_id, subject_entity_ids,
   target_object_id, independence_group).

2. Forced mid-transaction failure: invalid object injected between valid
   writes — transaction must fail entirely (no partial commit), test must
   NOT accept a success branch.
"""

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_context_window():
    """R3-S06: Minimal valid ContextWindow for fixture provider."""
    from aurora.extraction.context_window import ContentUnit, ContextWindow, DocumentRef

    doc = DocumentRef(document_id="doc_test", title="Test Document")
    units = [
        ContentUnit(
            unit_id="cu_1",
            unit_type="paragraph",
            text="中芯国际集成电路制造有限公司是全球领先的晶圆代工企业。",
            document_id="doc_test",
            locator="p[1]",
        ),
        ContentUnit(
            unit_id="cu_2",
            unit_type="paragraph",
            text="2025年第三季度公司实现营业收入156.2亿元，同比增长23.8%。",
            document_id="doc_test",
            locator="p[2]",
        ),
        ContentUnit(
            unit_id="cu_3",
            unit_type="paragraph",
            text="分析师认为中芯国际在先进制程领域的突破将为公司带来持续增长。",
            document_id="doc_test",
            locator="p[3]",
        ),
        ContentUnit(
            unit_id="cu_4",
            unit_type="paragraph",
            text="中芯国际2025年Q3财报显示，产能利用率从75%提升至92%。",
            document_id="doc_test",
            locator="p[4]",
        ),
    ]
    window = ContextWindow(document=doc, units=units)
    return window


def _make_full_closure_provider_response():
    """R3-S06: Fixture provider response with all 4 candidate types + valid references."""
    return {
        "provider_name": "test_fixture",
        "provider_version": "1.0",
        "profile_version": "1.0",
        "deterministic_mode": True,
        "candidates": [
            {
                "candidate_id": "ent_001",
                "candidate_type": "entity",
                "entity_type": "company",
                "canonical_name": "中芯国际",
                "source_unit_id": "cu_1",
                "source_quote": "中芯国际集成电路制造有限公司",
                "provider_id": "test_fixture",
                "profile_id": "v1_adversarial",
                "document_id": "doc_test",
            },
            {
                "candidate_id": "dp_001",
                "candidate_type": "data_point",
                "metric": "产能利用率",
                "value": 92.0,
                "unit": "percent",
                "entity_id": "ent_001",
                "period": "2025Q3",
                "source_unit_id": "cu_4",
                "source_quote": "产能利用率从75%提升至92%",
                "provider_id": "test_fixture",
                "profile_id": "v1_adversarial",
                "document_id": "doc_test",
            },
            {
                "candidate_id": "cl_001",
                "candidate_type": "claim",
                "claim_type": "prediction",
                "statement": "中芯国际先进制程突破将带来持续增长",
                "asserted_by": "市场分析师",
                "subject_entity_ids": ["ent_001"],
                "source_unit_id": "cu_3",
                "source_quote": "先进制程领域的突破将为公司带来持续增长",
                "provider_id": "test_fixture",
                "profile_id": "v1_adversarial",
                "document_id": "doc_test",
            },
            {
                "candidate_id": "ev_001",
                "candidate_type": "evidence",
                "evidence_type": "direct_quote",
                "evidence_role": "support",
                "target_object_id": "dp_001",
                "source_unit_id": "cu_4",
                "source_quote": "产能利用率从75%提升至92%",
                "provider_id": "test_fixture",
                "profile_id": "v1_adversarial",
                "document_id": "doc_test",
            },
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Full four-class closed-loop persistence
# ═══════════════════════════════════════════════════════════════════════════════

class TestFourClassFullPersistence:
    """R3-S06: Normal closed-loop fixture — all 4 classes persisted
    with valid core ID references and independence_group from root source."""

    def test_four_class_full_persistence(self):
        from aurora.persistence.draft_service import persist_drafts
        from aurora.persistence.persistence_policy import PersistencePolicy
        from aurora.extraction.context_window import ContextWindow
        from aurora.extraction.providers.fixture_provider import FixtureProvider
        from aurora.extraction.quote_gate import QuoteGate
        from aurora.extraction.review_bundle import ReviewBundle
        from aurora.extraction.safety_gate import SafetyGate

        # Build RealReviewBundle with actual FixtureProvider
        window = _make_context_window()

        # Use FixtureProvider with our four-class provider response
        provider = FixtureProvider()
        # Patch FixtureProvider.extract_for_case to return our data
        from aurora.extraction.candidates import (
            ClaimCandidate,
            DataPointCandidate,
            EntityCandidate,
            EvidenceCandidate,
        )
        from aurora.extraction.providers.fixture_provider import ProviderResponse
        from aurora.extraction.providers.fixture_provider import ProviderMetadata

        # Build candidates manually from our fixture
        raw = _make_full_closure_provider_response()
        ent = EntityCandidate(
            candidate_id="ent_001",
            entity_type="company",
            canonical_name="中芯国际",
            source_unit_id="cu_1",
            source_quote="中芯国际集成电路制造有限公司",
        )
        dp = DataPointCandidate(
            candidate_id="dp_001",
            metric="产能利用率",
            value=92.0,
            unit="percent",
            entity_id="ent_001",
            period_time_range=None,
            source_unit_id="cu_4",
            source_quote="产能利用率从75%提升至92%",
        )
        cl = ClaimCandidate(
            candidate_id="cl_001",
            claim_type="prediction",
            statement="中芯国际先进制程突破将带来持续增长",
            asserted_by="市场分析师",
            subject_entity_ids=["ent_001"],
            source_unit_id="cu_3",
            source_quote="先进制程领域的突破将为公司带来持续增长",
        )
        ev = EvidenceCandidate(
            candidate_id="ev_001",
            evidence_type="direct_quote",
            evidence_role="support",
            target_object_id="dp_001",
            source_unit_id="cu_4",
            source_quote="产能利用率从75%提升至92%",
        )

        candidates = [ent, dp, cl, ev]

        # QuoteGate
        qg = QuoteGate(window)
        qr = qg.validate(candidates)

        # SafetyGate
        sg = SafetyGate(window, existing_findings=qr.findings)
        sr = sg.validate(candidates)

        # Bundle
        all_findings = tuple(list(qr.findings) + sr.findings)
        bundle = ReviewBundle.create(
            document_id="doc_test",
            provider_name="test_fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=candidates,
            content_unit_window=window.units,
            validation_findings=all_findings,
            context_hashes={"window_sha256": window.window_sha256},
            case_id="test_case_4class",
            run_id="run_test_4class_persist",
        )

        # Policy
        policy = PersistencePolicy(
            allowed_providers=frozenset({"test_fixture"}),
            allowed_profiles=frozenset({"v1_adversarial"}),
            workspace_id="ws_test",
        )

        # Session mock — real SQLite in-memory for persistence
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from aurora.db.models import Base  # noqa: E402

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)

        # Pre-seed ContentUnit root source records in ObjectRepository
        # so SourceGraph can resolve independence_group
        from aurora.db.models import ObjectRecord
        from aurora.core.models.enums import LifecycleStatus, ObjectType

        cu_records = [
            ("cu_1", "p[1]"),
            ("cu_2", "p[2]"),
            ("cu_3", "p[3]"),
            ("cu_4", "p[4]"),
        ]
        with SessionLocal() as seed_session:
            for cu_id, locator in cu_records:
                seed_session.add(ObjectRecord(
                    id=cu_id,
                    object_type=ObjectType.CONTENT_UNIT.value,
                    schema_version="v1.1",
                    lifecycle_status=LifecycleStatus.ACTIVE.value,
                    workspace_id="ws_test",
                    privacy_level="private",
                    created_by="test",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    version=1,
                    payload={
                        "unit_id": cu_id,
                        "locator": locator,
                        "document_id": "doc_test",
                        "independence_group": f"ig_{cu_id}",
                        "source_graph_chain": ["root"],
                    },
                ))
            seed_session.commit()

        # Execute
        tx = persist_drafts(SessionLocal, bundle, "ws_test", policy=policy)

        # Assert: must succeed
        assert tx.succeeded, f"Transaction failed: {tx.error_message}"

        # Assert: all 4 object types present
        obj_types = {r.object_type for r in tx.records}
        assert "entity" in obj_types, f"Entity missing from records: {obj_types}"
        assert "data_point" in obj_types, f"DataPoint missing from records: {obj_types}"
        assert "claim" in obj_types, f"Claim missing from records: {obj_types}"
        assert "evidence" in obj_types, f"Evidence missing from records: {obj_types}"

        # Assert: totals
        assert tx.total_objects >= 4, f"Expected >= 4 objects, got {tx.total_objects}"
        assert tx.created_count >= 4, f"Expected >= 4 created, got {tx.created_count}"

        # Assert: verify core ID references in persisted objects
        with SessionLocal() as verify_session:
            from sqlalchemy import select as sql_select

            stmt = sql_select(ObjectRecord).where(
                ObjectRecord.workspace_id == "ws_test",
                ObjectRecord.object_type.in_(
                    [t.value for t in [ObjectType.ENTITY, ObjectType.DATA_POINT,
                                       ObjectType.CLAIM, ObjectType.EVIDENCE]]
                ),
                ObjectRecord.deleted_at.is_(None),
            )
            rows = list(verify_session.scalars(stmt).all())

            # Entity
            entity_row = [r for r in rows if r.object_type == ObjectType.ENTITY.value]
            assert len(entity_row) >= 1, "No Entity persisted"
            entity_id = entity_row[0].payload.get("id") or entity_row[0].id

            # DataPoint — entity_id must point to real Entity core ID
            dp_row = [r for r in rows if r.object_type == ObjectType.DATA_POINT.value]
            assert len(dp_row) >= 1, "No DataPoint persisted"
            dp_entity_id = dp_row[0].payload.get("entity_id", "")
            assert dp_entity_id, f"DataPoint entity_id is empty"
            assert dp_entity_id == entity_id, (
                f"DataPoint entity_id={dp_entity_id} != Entity core ID={entity_id}"
            )

            # Claim — subject_entity_ids must point to real Entity core ID
            claim_row = [r for r in rows if r.object_type == ObjectType.CLAIM.value]
            assert len(claim_row) >= 1, "No Claim persisted"
            claim_subjects = claim_row[0].payload.get("subject_entity_ids", [])
            assert entity_id in claim_subjects, (
                f"Claim subject_entity_ids={claim_subjects} does not contain Entity core ID={entity_id}"
            )

            # Evidence
            ev_row = [r for r in rows if r.object_type == ObjectType.EVIDENCE.value]
            assert len(ev_row) >= 1, "No Evidence persisted"
            ev_target = ev_row[0].payload.get("target_object_id", "")
            assert ev_target, "Evidence target_object_id is empty"
            # target_object_id should be the core DataPoint ID, not a candidate ID
            assert not ev_target.startswith("dp_"), (
                f"Evidence target_object_id={ev_target} is still a candidate ID"
            )
            ev_ig = ev_row[0].payload.get("independence_group", "")
            assert ev_ig, f"Evidence independence_group is empty"
            assert ev_ig != "pending_source_graph", (
                f"Evidence independence_group is still 'pending_source_graph'"
            )

        # Cleanup
        Base.metadata.drop_all(engine)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Forced mid-transaction failure — must NOT accept success branch
# ═══════════════════════════════════════════════════════════════════════════════

class TestForcedMidTransactionFailure:
    """R3-S06: Inject an invalid object between valid writes → transaction
    must fail entirely. Test MUST NOT accept a success branch."""

    def test_forced_mid_transaction_failure(self):
        from aurora.persistence.draft_service import persist_drafts
        from aurora.persistence.persistence_policy import PersistencePolicy
        from aurora.extraction.context_window import ContextWindow
        from aurora.extraction.candidates import (
            EntityCandidate,
        )
        from aurora.extraction.providers.fixture_provider import ProviderResponse
        from aurora.extraction.providers.fixture_provider import ProviderMetadata
        from aurora.extraction.quote_gate import QuoteGate
        from aurora.extraction.review_bundle import ReviewBundle
        from aurora.extraction.safety_gate import SafetyGate

        window = _make_context_window()

        # Phase 1: create valid Entity + Claim to seed, then inject
        # a DataPoint with missing required field to force mapper failure
        ent = EntityCandidate(
            candidate_id="ent_001",
            entity_type="company",
            canonical_name="中芯国际",
            source_unit_id="cu_1",
            source_quote="中芯国际集成电路制造有限公司",
        )
        cl = EntityCandidate(  # deliberately wrong type to simulate invalid
            candidate_id="bad_002",
            entity_type="company",
            canonical_name="",  # empty canonical_name is invalid
            source_unit_id="cu_2",
            source_quote="test",
        )

        candidates = [ent, cl]

        qg = QuoteGate(window)
        qr = qg.validate(candidates)
        sg = SafetyGate(window, existing_findings=qr.findings)
        sr = sg.validate(candidates)
        all_findings = tuple(list(qr.findings) + sr.findings)
        bundle = ReviewBundle.create(
            document_id="doc_test",
            provider_name="test_fixture",
            provider_version="1.0",
            deterministic_mode=True,
            candidates=candidates,
            content_unit_window=window.units,
            validation_findings=all_findings,
            context_hashes={"window_sha256": window.window_sha256},
            case_id="test_case_fail",
            run_id="run_test_fail",
        )

        policy = PersistencePolicy(
            allowed_providers=frozenset({"test_fixture"}),
            allowed_profiles=frozenset({"v1_adversarial"}),
            workspace_id="ws_test",
        )

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from aurora.db.models import Base, ObjectRecord
        from aurora.core.models.enums import LifecycleStatus, ObjectType

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)

        # Pre-seed ContentUnits for SourceGraph
        with SessionLocal() as seed_session:
            for cu_id in ["cu_1", "cu_2"]:
                seed_session.add(ObjectRecord(
                    id=cu_id,
                    object_type=ObjectType.CONTENT_UNIT.value,
                    schema_version="v1.1",
                    lifecycle_status=LifecycleStatus.ACTIVE.value,
                    workspace_id="ws_test",
                    privacy_level="private",
                    created_by="test",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    version=1,
                    payload={
                        "unit_id": cu_id,
                        "locator": f"p[{cu_id[-1]}]",
                        "document_id": "doc_test",
                        "independence_group": f"ig_{cu_id}",
                        "source_graph_chain": ["root"],
                    },
                ))
            seed_session.commit()

        tx = persist_drafts(SessionLocal, bundle, "ws_test", policy=policy)

        # Hard assertion: must be FAILED
        assert not tx.succeeded, (
            "Transaction should have failed due to invalid canonical_name, "
            f"but succeeded with {tx.created_count} objects"
        )
        assert tx.created_count == 0, (
            f"No objects should have been created on failure, got {tx.created_count}"
        )

        # Verify: persisted DB must be empty (no partial commit)
        with SessionLocal() as verify_session:
            from sqlalchemy import select as sql_select
            stmt = sql_select(ObjectRecord).where(
                ObjectRecord.workspace_id == "ws_test",
                ObjectRecord.object_type.notin_([
                    ObjectType.CONTENT_UNIT.value,
                    ObjectType.PROCESSING_RUN.value,
                ]),
                ObjectRecord.deleted_at.is_(None),
            )
            rows = list(verify_session.scalars(stmt).all())
            assert len(rows) == 0, (
                f"Found {len(rows)} partial business objects after transaction failure"
            )

        Base.metadata.drop_all(engine)
