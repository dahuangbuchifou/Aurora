"""Seed a test database with V1.0 objects for migration QA-GATE-002."""
import json, os, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from aurora.db.base import Base

utcnow = datetime.now(timezone.utc)

# Build V1.0 payloads
v1_0_objects = [
    ("source", "seed_src_001", {
        "schema_version": "1.0", "object_type": "source", "id": "seed_src_001",
        "title": "中芯国际2025年报", "source_type": "financial_report",
        "document_ids": [], "content_unit_ids": []}),
    ("document", "seed_doc_001", {
        "schema_version": "1.0", "object_type": "document", "id": "seed_doc_001",
        "title": "SMIC 2025 Annual Report", "source_id": "seed_src_001",
        "document_type": "pdf", "content_unit_ids": []}),
    ("content_unit", "seed_cu_001", {
        "schema_version": "1.0", "object_type": "content_unit", "id": "seed_cu_001",
        "title": "营收段落", "document_id": "seed_doc_001", "content_type": "text"}),
    ("data_point", "seed_dp_001", {
        "schema_version": "1.0", "object_type": "data_point", "id": "seed_dp_001",
        "value": 578.3, "unit": "reported_unit", "period": "2025",
        "evidence_ids": ["seed_ev_001"], "calculation_method": "raw",
        "comparison_value": None, "comparison_label": None, "comparison_note": None}),
    ("claim", "seed_cl_001", {
        "schema_version": "1.0", "object_type": "claim", "id": "seed_cl_001",
        "statement": "2025年营收578.3亿元，同比增长21%",
        "claim_type": "factual", "claimant_id": "seed_enty_001",
        "evidence_ids": ["seed_ev_001"]}),
    ("evidence", "seed_ev_001", {
        "schema_version": "1.0", "object_type": "evidence", "id": "seed_ev_001",
        "evidence_type": "direct_observation", "evidence_role": "support",
        "target_object_id": "seed_dp_001", "source_refs": [],
        "independence_group": "annual_report"}),
    ("entity", "seed_enty_001", {
        "schema_version": "1.0", "object_type": "entity", "id": "seed_enty_001",
        "entity_type": "organization", "name": "中芯国际"}),
    ("fact", "seed_fact_001", {
        "schema_version": "1.0", "object_type": "fact", "id": "seed_fact_001",
        "content": "2025年营收578.3亿元",
        "evidence_refs": ["seed_ev_001"], "confidence": 0.95}),
    ("knowledge_object", "seed_ko_001", {
        "schema_version": "1.0", "object_type": "knowledge_object", "id": "seed_ko_001",
        "summary": "中芯国际2025年营收578.3亿元",
        "fact_refs": ["seed_fact_001"], "insight_ids": []}),
]


def main():
    url = os.environ.get("AURORA_DATABASE_URL", "sqlite:///./data/m1_003b_nonempty.db")
    engine = create_engine(url)
    Base.metadata.create_all(engine)

    from aurora.db.models import ObjectRecord

    with Session(engine) as session:
        for ot, oid, payload_data in v1_0_objects:
            rec = ObjectRecord(
                id=oid, object_type=ot, schema_version="1.0",
                lifecycle_status="draft", workspace_id="seed_ws",
                privacy_level="private", created_by="qa_gate",
                created_at=utcnow, updated_at=utcnow,
                payload=payload_data,
            )
            session.add(rec)
        session.commit()

    print(f"Seeded {len(v1_0_objects)} V1.0 objects")
    for ot, oid, _ in v1_0_objects:
        print(f"  {oid} ({ot})")

if __name__ == "__main__":
    main()
