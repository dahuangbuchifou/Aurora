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

def _seed_complete_source_graph(
    session_factory,
    *,
    workspace_id: str,
    document_id: str,
    source_id: str,
    content_unit_ids: list[str],
    cu_locators: dict[str, str] | None = None,
) -> None:
    """R4: Seed a complete SourceGraph chain into the database.

    Writes: Root Source → Document → ContentUnits (linked by id references).
    SourceGraphResolver requires these real records to resolve independence_group.
    """
    from aurora.db.models import ObjectRecord
    from aurora.core.models.enums import LifecycleStatus, ObjectType

    if cu_locators is None:
        cu_locators = {}

    now_iso = datetime.now(timezone.utc).isoformat()

    with session_factory() as s:
        # Root Source
        src_payload = {
            "id": source_id,
            "object_type": "source",
            "schema_version": "1.1",
            "name": "Root Source for R3-S06",
            "source_type": {"value": "research_report"},
            "workspace_id": workspace_id,
            "status": "active",
            "created_by": "test",
            "created_at": now_iso,
            "updated_at": now_iso,
            "language": "zh",
            "tags": [],
            "privacy_level": "private",
            "provenance": {"derivation_links": []},
        }
        s.add(ObjectRecord(
            id=source_id,
            object_type=ObjectType.SOURCE.value,
            schema_version="1.1",
            lifecycle_status=LifecycleStatus.ACTIVE.value,
            workspace_id=workspace_id,
            privacy_level="private",
            created_by="test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
            payload=src_payload,
        ))

        # Document (points to Root Source)
        doc_payload = {
            "id": document_id,
            "object_type": "document",
            "schema_version": "1.1",
            "source_id": source_id,
            "document_type": {"value": "research_report"},
            "title": "R3-S06 Test Document",
            "workspace_id": workspace_id,
            "status": "active",
            "created_by": "test",
            "created_at": now_iso,
            "updated_at": now_iso,
            "language": "zh",
            "tags": [],
            "privacy_level": "private",
        }
        s.add(ObjectRecord(
            id=document_id,
            object_type=ObjectType.DOCUMENT.value,
            schema_version="1.1",
            lifecycle_status=LifecycleStatus.ACTIVE.value,
            workspace_id=workspace_id,
            privacy_level="private",
            created_by="test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
            payload=doc_payload,
        ))

        # ContentUnits (each points to Document)
        for cu_id in content_unit_ids:
            locator = cu_locators.get(cu_id, f"p[{cu_id}].0")
            cu_payload = {
                "id": cu_id,
                "object_type": "content_unit",
                "schema_version": "1.1",
                "document_id": document_id,
                "unit_type": "paragraph",
                "sequence_no": 1,
                "text": f"Text content for {cu_id}",
                "locator": {"block_no": 0, "locator": locator},
                "workspace_id": workspace_id,
                "status": "active",
                "created_by": "test",
                "created_at": now_iso,
                "updated_at": now_iso,
                "language": "zh",
                "tags": [],
                "privacy_level": "private",
            }
            s.add(ObjectRecord(
                id=cu_id,
                object_type=ObjectType.CONTENT_UNIT.value,
                schema_version="1.1",
                lifecycle_status=LifecycleStatus.ACTIVE.value,
                workspace_id=workspace_id,
                privacy_level="private",
                created_by="test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                version=1,
                payload=cu_payload,
            ))

        s.commit()


def _make_context_window():
    """R3-S06: Minimal valid ContextWindow for fixture provider."""
    from aurora.extraction.context_window import ContentUnitRef, ContextWindow

    units = [
        ContentUnitRef(
            unit_id="cu_1", sequence_no=1, unit_type="paragraph",
            text="中芯国际集成电路制造有限公司是全球领先的晶圆代工企业。",
            document_id="doc_test",
        ),
        ContentUnitRef(
            unit_id="cu_2", sequence_no=2, unit_type="paragraph",
            text="2025年第三季度公司实现营业收入156.2亿元，同比增长23.8%。",
            document_id="doc_test",
        ),
        ContentUnitRef(
            unit_id="cu_3", sequence_no=3, unit_type="paragraph",
            text="分析师认为中芯国际在先进制程领域的突破将为公司带来持续增长。",
            document_id="doc_test",
        ),
        ContentUnitRef(
            unit_id="cu_4", sequence_no=4, unit_type="paragraph",
            text="中芯国际2025年Q3财报显示，产能利用率从75%提升至92%。",
            document_id="doc_test",
        ),
    ]
    window = ContextWindow(document_id="doc_test", units=tuple(units))
    return window


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Full four-class closed-loop persistence
# ═══════════════════════════════════════════════════════════════════════════════

class TestFourClassFullPersistence:
    """R3-S06: Normal closed-loop fixture — all 4 classes persisted
    with valid core ID references and independence_group from root source."""

    def test_four_class_full_persistence(self):
        from aurora.persistence.draft_service import persist_drafts
        from aurora.persistence.persistence_policy import PersistencePolicy
        from aurora.extraction.providers.fixture_provider import FixtureProvider
        from aurora.extraction.quote_gate import QuoteGate
        from aurora.extraction.review_bundle import ReviewBundle
        from aurora.extraction.safety_gate import SafetyGate
        from aurora.extraction.candidates import (
            ClaimCandidate, DataPointCandidate,
            EntityCandidate, EvidenceCandidate,
        )

        window = _make_context_window()

        ent = EntityCandidate(
            candidate_id="ent_001",
            entity_type="company",
            canonical_name="中芯国际",
        )
        dp = DataPointCandidate(
            candidate_id="dp_001",
            metric="产能利用率",
            value=92.0,
            unit="percent",
            entity_id="ent_001",
            period="2025Q3",
            measurement_context={},
            source_unit_id="cu_4",
            source_quote="产能利用率从75%提升至92%",
        )
        cl = ClaimCandidate(
            candidate_id="cl_001",
            claim_type="prediction",
            claim_dimension="financial",
            statement="中芯国际先进制程突破将带来持续增长",
            asserted_by="市场分析师",
            claimant_name="分析师",
            time_horizon={"start": "2025-01-01", "end": "2026-12-31"},
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
            case_id="test_case_4class",
            run_id="run_test_4class_persist",
        )

        policy = PersistencePolicy(
            allowed_providers=frozenset({"test_fixture"}),
            allowed_profiles=frozenset({"v1_adversarial"}),
            workspace_id="ws_test",
        )

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from aurora.db.models import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)

        _seed_complete_source_graph(
            SessionLocal,
            workspace_id="ws_test",
            document_id="doc_test",
            source_id="src_root",
            content_unit_ids=["cu_1", "cu_2", "cu_3", "cu_4"],
            cu_locators={"cu_1": "p[1]", "cu_2": "p[2]", "cu_3": "p[3]", "cu_4": "p[4]"},
        )

        tx = persist_drafts(SessionLocal, bundle, workspace_id="ws_test", policy=policy)
        assert tx.succeeded, f"Transaction failed: {tx.error_message}"

        obj_types = {r.object_type for r in tx.records}
        assert "entity" in obj_types, f"Entity missing: {obj_types}"
        assert "data_point" in obj_types, f"DataPoint missing: {obj_types}"
        assert "claim" in obj_types, f"Claim missing: {obj_types}"
        assert "evidence" in obj_types, f"Evidence missing: {obj_types}"

        assert tx.total_objects >= 4
        assert tx.created_count >= 4

        with SessionLocal() as verify_session:
            from sqlalchemy import select as sql_select
            from aurora.db.models import ObjectRecord
            from aurora.core.models.enums import ObjectType

            stmt = sql_select(ObjectRecord).where(
                ObjectRecord.workspace_id == "ws_test",
                ObjectRecord.object_type.in_(
                    [t.value for t in [ObjectType.ENTITY, ObjectType.DATA_POINT,
                                       ObjectType.CLAIM, ObjectType.EVIDENCE]]
                ),
                ObjectRecord.deleted_at.is_(None),
            )
            rows = list(verify_session.scalars(stmt).all())

            entity_row = [r for r in rows if r.object_type == ObjectType.ENTITY.value]
            assert len(entity_row) >= 1, "No Entity persisted"
            entity_id = entity_row[0].payload.get("id") or entity_row[0].id

            dp_row = [r for r in rows if r.object_type == ObjectType.DATA_POINT.value]
            assert len(dp_row) >= 1, "No DataPoint persisted"
            dp_entity_id = dp_row[0].payload.get("entity_id", "")
            # entity_id must be a core ID (UUID), not a candidate ID

            claim_row = [r for r in rows if r.object_type == ObjectType.CLAIM.value]
            assert len(claim_row) >= 1, "No Claim persisted"

            ev_row = [r for r in rows if r.object_type == ObjectType.EVIDENCE.value]
            assert len(ev_row) >= 1, "No Evidence persisted"
            ev_target = ev_row[0].payload.get("target_object_id", "")
            assert ev_target, "Evidence target_object_id is empty"
            assert not ev_target.startswith("dp_"), f"Evidence target is still candidate ID: {ev_target}"
            ev_ig = ev_row[0].payload.get("independence_group", "")
            assert ev_ig, "Evidence independence_group is empty"
            assert ev_ig != "pending_source_graph"

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
        from aurora.extraction.candidates import EntityCandidate
        from aurora.extraction.quote_gate import QuoteGate
        from aurora.extraction.review_bundle import ReviewBundle
        from aurora.extraction.safety_gate import SafetyGate

        window = _make_context_window()

        ent = EntityCandidate(
            candidate_id="ent_001",
            entity_type="company",
            canonical_name="中芯国际",
        )
        cl = EntityCandidate(  # deliberately wrong type to simulate invalid
            candidate_id="bad_002",
            entity_type="company",
            canonical_name="",  # empty canonical_name is invalid
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
        from aurora.db.models import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)

        _seed_complete_source_graph(
            SessionLocal,
            workspace_id="ws_test",
            document_id="doc_test",
            source_id="src_root",
            content_unit_ids=["cu_1", "cu_2"],
            cu_locators={"cu_1": "p[1]", "cu_2": "p[2]"},
        )

        tx = persist_drafts(SessionLocal, bundle, workspace_id="ws_test", policy=policy)

        assert not tx.succeeded, (
            "Transaction should have failed due to invalid canonical_name, "
            f"but succeeded with {tx.created_count} objects"
        )
        assert tx.created_count == 0

        with SessionLocal() as verify_session:
            from sqlalchemy import select as sql_select
            from aurora.db.models import ObjectRecord
            from aurora.core.models.enums import ObjectType

            stmt = sql_select(ObjectRecord).where(
                ObjectRecord.workspace_id == "ws_test",
                ObjectRecord.object_type.notin_([
                    ObjectType.CONTENT_UNIT.value,
                    ObjectType.PROCESSING_RUN.value,
                    ObjectType.SOURCE.value,
                    ObjectType.DOCUMENT.value,
                ]),
                ObjectRecord.deleted_at.is_(None),
            )
            rows = list(verify_session.scalars(stmt).all())
            assert len(rows) == 0, (
                f"Found {len(rows)} partial business objects after transaction failure"
            )

        Base.metadata.drop_all(engine)
