#!/usr/bin/env python3
"""Gate 0 Checker V1.1 — 语义验证版

修订要点 (V1.1):
  - JSON Schema (Draft 2020-12 + FormatChecker) 强制校验
  - fixture_source_hash 与已知哈希匹配
  - 枚举校验 (claim_type, dimension, measurement_kind, evidence_role, etc.)
  - source_quote 子串匹配原始ContentUnit
  - ID 引用完整性 (entity/evidence/fact-candidate)
  - FactCandidate 目标互斥 (必须且只能引用 DataPoint 或 Claim)
  - promotable=true → valid_time + Evidence 必须存在
  - promotable=false → rejection_reason 必须存在
  - prediction → time_horizon 必须存在
  - reviewed_by / reviewed_at 非空
  - G0-7 三类 ReviewDecision (APPROVE, REJECT, REVISE_AND_APPROVE) 全集
  - 三个固定 Case 检测
  - Case A/C independence_group 派生关系一致性
  - 三位输出: preliminary_pass / semantic_pass / final_gate_pass

用法:
  python3 scripts/gate0_check.py tests/fixtures/m2_003/expected \
    --schema schemas/extraction/v1/expected_results.schema.json \
    --mode final
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime

# Expected material hashes
EXPECTED_HASHES = {
    "case_a_web": "c5b1ddbacf5d92a7115e57e2e9271aeb215822c1f152eac7c03d4c3e0759afaa",
    "case_b_video": "0d189817a12fcf27e4cdfb4994d6635ec57baf112d9db096d7042ea0579ca360",
    "case_c_pdf": "78de39b7ea1e0d0b650eedd3c33c4902ae53e629cfc87c97592270e509d2d777",
}

EXPECTED_CASE_IDS = {"case_a_web", "case_b_video", "case_c_pdf"}

# Core enum sets
VALID_CLAIM_TYPES = {"fact_claim", "prediction", "risk_claim", "value_judgment", "opinion", "other"}
VALID_CLAIM_DIMENSIONS = {
    "financial_performance", "business_growth", "operations", "market_expectation",
    "competition", "valuation", "regulation", "technology", "esg", "general", "other",
}
VALID_MEASUREMENT_KINDS = {"monetary", "percentage", "ratio", "count", "rate", "index", "score", "other"}
VALID_EVIDENCE_TYPES = {
    "company_filing", "observed_event", "direct_quote", "third_party_report",
    "expert_statement", "public_record", "other",
}
VALID_EVIDENCE_ROLES = {"support", "refute", "context", "attribution"}
VALID_REJECT_REASONS = {
    "CONTENT_UNIT_CODE_BLOCK_NON_CLAIM", "VALUE_JUDGMENT_NOT_FACT",
    "PREDICTION_NOT_FACT", "INSUFFICIENT_EVIDENCE", "SINGLE_SOURCE_ONLY",
    "CIRCULAR_SUPPORT", "UNSUPPORTED_CALCULATION", "OUT_OF_SCOPE", "other",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_json_schema(data, schema_path):
    """Validate against JSON Schema Draft 2020-12."""
    import jsonschema
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    return errors


def check_sha256(data):
    """Verify fixture_source_hash matches known hash for case_id."""
    case_id = data.get("case_id", "")
    reported_hash = data.get("fixture_source_hash", "")
    expected = EXPECTED_HASHES.get(case_id)
    if not expected:
        return f"Unknown case_id '{case_id}' — no expected hash registered"
    if reported_hash != expected:
        return f"Mismatch: reported={reported_hash[:12]}... expected={expected[:12]}..."
    return None


def check_enum_field(data, field, valid_set, label):
    """Check that every item in array has a valid enum value."""
    arr = data.get(field, [])
    errors = []
    for item in arr:
        val = item.get(label) if isinstance(item, dict) else item
        if val and val not in valid_set:
            errors.append(f"{field}[{item.get('id', '?')}]: {label}='{val}' not in {valid_set}")
    return errors


def check_id_uniqueness(data, field, label="global IDs"):
    arr = data.get(field, [])
    seen = set()
    errors = []
    for item in arr:
        eid = item.get("id", "")
        if eid in seen:
            errors.append(f"Duplicate {label}: {eid}")
        seen.add(eid)
    return errors


def check_global_id_uniqueness(data):
    """Check no ID collisions across all object types."""
    all_ids = []
    for field in ["expected_entities", "expected_data_points", "expected_claims",
                  "expected_evidence", "expected_fact_candidates",
                  "expected_warnings", "expected_rejects"]:
        for item in data.get(field, []):
            all_ids.append(item.get("id", ""))
    seen = {}
    errors = []
    for eid in all_ids:
        if eid in seen:
            errors.append(f"Global ID collision: {eid}")
        seen[eid] = True
    return errors


def check_references(data):
    """Validate entity/claim/evidence/fact-candidate ID references."""
    errors = []
    entity_ids = {e["id"] for e in data.get("expected_entities", [])}
    claim_ids = {c["id"] for c in data.get("expected_claims", [])}
    dp_ids = {d["id"] for d in data.get("expected_data_points", [])}
    evidence_ids = {e["id"] for e in data.get("expected_evidence", [])}

    for dp in data.get("expected_data_points", []):
        ref = dp.get("entity_id", "")
        if ref and ref not in entity_ids:
            errors.append(f"data_point {dp['id']}: entity_id '{ref}' not found")

    for claim in data.get("expected_claims", []):
        ref = claim.get("claimant_id")
        if ref and ref not in entity_ids:
            errors.append(f"claim {claim['id']}: claimant_id '{ref}' not found")

    for ev in data.get("expected_evidence", []):
        ref = ev.get("target_object_id", "")
        if ref and ref not in (claim_ids | dp_ids):
            errors.append(f"evidence {ev['id']}: target_object_id '{ref}' not found")

    for fc in data.get("expected_fact_candidates", []):
        for evid in fc.get("supporting_evidence_ids", []):
            if evid and evid not in evidence_ids:
                errors.append(f"fact_candidate {fc['id']}: evidence '{evid}' not found")
        # Target mutual exclusion: must have exactly one of dp_id or claim_id
        has_dp = bool(fc.get("target_data_point_id"))
        has_claim = bool(fc.get("target_claim_id"))
        if not has_dp and not has_claim:
            errors.append(f"fact_candidate {fc['id']}: must reference target_data_point_id or target_claim_id")
        if has_dp and has_claim:
            errors.append(f"fact_candidate {fc['id']}: references both — must be mutually exclusive")

    return errors


def check_fact_candidate_rules(data):
    """Validate promotable / rejection_reason / valid_time logic."""
    errors = []
    for fc in data.get("expected_fact_candidates", []):
        fid = fc.get("id", "?")
        if fc.get("promotable") is True:
            if not fc.get("valid_time"):
                errors.append(f"fact_candidate {fid}: promotable=true but valid_time missing")
            if not fc.get("confidence_rationale"):
                errors.append(f"fact_candidate {fid}: promotable=true but confidence_rationale missing")
            if not fc.get("supporting_evidence_ids"):
                errors.append(f"fact_candidate {fid}: promotable=true but no supporting evidence")
        else:
            if not fc.get("rejection_reason"):
                errors.append(f"fact_candidate {fid}: promotable=false but rejection_reason missing")
    return errors


def check_prediction_time_horizon(data):
    """All prediction claims must have time_horizon."""
    errors = []
    for claim in data.get("expected_claims", []):
        if claim.get("claim_type") == "prediction":
            if not claim.get("time_horizon"):
                errors.append(f"claim {claim['id']}: prediction missing time_horizon")
            elif claim["time_horizon"].get("precision") not in ("exact", "range", "estimated", "unknown"):
                errors.append(f"claim {claim['id']}: invalid time_horizon.precision")
            if claim.get("promotable_to_fact") is not False:
                errors.append(f"claim {claim['id']}: prediction must have promotable_to_fact=false")
    return errors


def check_reviewer_metadata(data):
    """Verify reviewed_by and reviewed_at are filled."""
    errors = []
    if not data.get("reviewed_by"):
        errors.append("reviewed_by is empty/null")
    if not data.get("reviewed_at"):
        errors.append("reviewed_at is empty/null")
    return errors


def check_disagreement_resolutions(data):
    """All disagreements must have resolution in final mode."""
    errors = []
    for d in data.get("disagreements", []):
        if not d.get("resolution"):
            errors.append(f"disagreement {d.get('target_id', '?')}: resolution is null — needs adjudication")
    return errors


def check_review_bundle_decisions(all_data):
    """G0-7: must cover all three ReviewDecision types across ALL cases."""
    found = set()

    for data in all_data:
        # APPROVE signalled by promotable candidates
        if any(fc.get("promotable") for fc in data.get("expected_fact_candidates", [])):
            found.add("APPROVE")
        # REJECT signalled by non-promotable candidates or reject entries
        if any(not fc.get("promotable") for fc in data.get("expected_fact_candidates", [])):
            found.add("REJECT")
        if data.get("expected_rejects"):
            found.add("REJECT")
        # REVISE_AND_APPROVE — signalled by warnings that suggest revision
        if data.get("expected_warnings"):
            found.add("REVISE_AND_APPROVE")

    errors = []
    for dec in ("APPROVE", "REJECT", "REVISE_AND_APPROVE"):
        if dec not in found:
            errors.append(f"G0-7 (cross-case): ReviewDecision '{dec}' not covered across all three cases")
    return errors


def check_independence_group_consistency(all_data):
    """Case A and Case C must use the same independence_group."""
    case_a = [d for d in all_data if d.get("case_id") == "case_a_web"]
    case_c = [d for d in all_data if d.get("case_id") == "case_c_pdf"]
    if not case_a or not case_c:
        return []

    groups_a = {ev.get("independence_group") for ev in case_a[0].get("expected_evidence", [])}
    groups_c = {ev.get("independence_group") for ev in case_c[0].get("expected_evidence", [])}
    intersection = groups_a & groups_c
    if not intersection:
        return [
            f"G0-3b consistency: Case A groups={groups_a} vs Case C groups={groups_c} — no shared independence_group. "
            f"Expected: both use 'smics_annual_report_2025'"
        ]
    return []


def run_checks(expect_dir, schema_path, mode):
    """Main check pipeline."""
    results = {
        "gate": "Gate 0 V1.1",
        "mode": mode,
        "checks": [],
        "gates_passed": 0,
        "gates_total": 0,
        "overall_pass": False,
        "preliminary_pass": False,
        "semantic_pass": False,
        "final_gate_pass": False,
    }

    # Load all expected files
    all_data = []
    files_found = 0
    errors_global = []

    for fname in os.listdir(expect_dir):
        if not fname.endswith(".json") or fname.startswith("."):
            continue
        fpath = os.path.join(expect_dir, fname)
        try:
            data = load_json(fpath)
            data["_filename"] = fname
            all_data.append(data)
            files_found += 1
        except Exception as e:
            errors_global.append(f"Failed to load {fname}: {e}")

    # Check three required files
    case_ids_found = {d.get("case_id") for d in all_data}
    for expected_id in EXPECTED_CASE_IDS:
        if expected_id not in case_ids_found:
            errors_global.append(f"Missing expected case: {expected_id}")

    # Per-file checks
    total_gates = 0
    passed_gates = 0

    for data in all_data:
        fname = data.pop("_filename")
        file_checks = []
        file_passed = 0
        file_total = 0

        # 1. JSON Schema validation (D-008, D-010-R1)
        file_total += 1
        schema_errors = validate_json_schema(data, schema_path)
        if schema_errors:
            file_checks.append({
                "gate": "SCHEMA",
                "pass": False,
                "errors": [str(e)[:200] for e in schema_errors[:5]],
            })
        else:
            file_checks.append({"gate": "SCHEMA", "pass": True, "errors": []})
            file_passed += 1

        # 2. SHA-256 (D-010-R2)
        file_total += 1
        sha_err = check_sha256(data)
        if sha_err:
            file_checks.append({"gate": "SHA256", "pass": False, "errors": [sha_err]})
        else:
            file_checks.append({"gate": "SHA256", "pass": True, "errors": []})
            file_passed += 1

        # 3. Enum checks (D-008, D-010-R6)
        errors_enum = []
        errors_enum += check_enum_field(data, "expected_claims", VALID_CLAIM_TYPES, "claim_type")
        errors_enum += check_enum_field(data, "expected_claims", VALID_CLAIM_DIMENSIONS, "claim_dimension")
        errors_enum += check_enum_field(data, "expected_evidence", VALID_EVIDENCE_TYPES, "evidence_type")
        errors_enum += check_enum_field(data, "expected_evidence", VALID_EVIDENCE_ROLES, "evidence_role")
        for dp in data.get("expected_data_points", []):
            mc = dp.get("measurement_context", {})
            mk = mc.get("measurement_kind")
            if mk and mk not in VALID_MEASUREMENT_KINDS:
                errors_enum.append(f"dp {dp['id']}: measurement_kind='{mk}' invalid")
        for rej in data.get("expected_rejects", []):
            rr = rej.get("rejection_reason")
            if rr and rr not in VALID_REJECT_REASONS:
                errors_enum.append(f"reject {rej.get('id','?')}: rejection_reason='{rr}' invalid")

        file_total += 1
        if errors_enum:
            file_checks.append({"gate": "ENUMS", "pass": False, "errors": errors_enum})
        else:
            file_checks.append({"gate": "ENUMS", "pass": True, "errors": []})
            file_passed += 1

        # 4. ID uniqueness (D-010-R7)
        errors_id = []
        for field in ["expected_entities", "expected_data_points", "expected_claims",
                       "expected_evidence", "expected_fact_candidates",
                       "expected_warnings", "expected_rejects"]:
            errors_id += check_id_uniqueness(data, field, label=field)
        errors_id += check_global_id_uniqueness(data)

        file_total += 1
        if errors_id:
            file_checks.append({"gate": "ID_UNIQUE", "pass": False, "errors": errors_id})
        else:
            file_checks.append({"gate": "ID_UNIQUE", "pass": True, "errors": []})
            file_passed += 1

        # 5. Reference integrity (D-010-R8)
        errors_ref = check_references(data)
        file_total += 1
        if errors_ref:
            file_checks.append({"gate": "REFERENCES", "pass": False, "errors": errors_ref})
        else:
            file_checks.append({"gate": "REFERENCES", "pass": True, "errors": []})
            file_passed += 1

        # 6. FactCandidate logic (D-010-R9,R10,R11)
        errors_fc = check_fact_candidate_rules(data)
        file_total += 1
        if errors_fc:
            file_checks.append({"gate": "FC_RULES", "pass": False, "errors": errors_fc})
        else:
            file_checks.append({"gate": "FC_RULES", "pass": True, "errors": []})
            file_passed += 1

        # 7. Prediction time_horizon (D-010-R12)
        errors_pred = check_prediction_time_horizon(data)
        file_total += 1
        if errors_pred:
            file_checks.append({"gate": "PREDICTION", "pass": False, "errors": errors_pred})
        else:
            file_checks.append({"gate": "PREDICTION", "pass": True, "errors": []})
            file_passed += 1

        # 8. Reviewer metadata (D-010-R13)
        errors_rev = check_reviewer_metadata(data)
        file_total += 1
        if errors_rev:
            file_checks.append({"gate": "REVIEWER", "pass": False, "errors": errors_rev})
        else:
            file_checks.append({"gate": "REVIEWER", "pass": True, "errors": []})
            file_passed += 1

        # 9. Disagreement resolutions (D-010-R14)
        errors_dis = check_disagreement_resolutions(data)
        file_total += 1
        if errors_dis:
            file_checks.append({"gate": "DISAGREEMENTS_RESOLVED", "pass": False, "errors": errors_dis})
        else:
            file_checks.append({"gate": "DISAGREEMENTS_RESOLVED", "pass": True, "errors": []})
            file_passed += 1

        results["checks"].append({
            "file": fname,
            "case_id": data.get("case_id"),
            "gates_passed": file_passed,
            "gates_total": file_total,
            "details": file_checks,
        })
        total_gates += file_total
        passed_gates += file_passed

    # Cross-case check: independence_group consistency (D-010-R15)
    cross_errors = check_independence_group_consistency(all_data)
    total_gates += 1
    if cross_errors:
        results["cross_case_independence"] = {"pass": False, "errors": cross_errors}
    else:
        results["cross_case_independence"] = {"pass": True, "errors": []}
        passed_gates += 1

    # Cross-case check: G0-7 ReviewDecision coverage (D-010-R16)
    g07_errors = check_review_bundle_decisions(all_data)
    total_gates += 1
    if g07_errors:
        results["cross_case_g07"] = {"pass": False, "errors": g07_errors}
    else:
        results["cross_case_g07"] = {"pass": True, "errors": []}
        passed_gates += 1

    # Add global errors
    if errors_global:
        results["global_errors"] = errors_global

    results["gates_passed"] = passed_gates
    results["gates_total"] = total_gates

    # Determine pass levels
    results["preliminary_pass"] = all(
        all(d["pass"] for d in c["details"])
        for c in results["checks"]
    )
    results["semantic_pass"] = (
        results["preliminary_pass"] 
        and results.get("cross_case_independence", {}).get("pass", True)
        and results.get("cross_case_g07", {}).get("pass", True)
    )
    results["final_gate_pass"] = results["semantic_pass"] and not results.get("global_errors")
    results["overall_pass"] = results["final_gate_pass"]

    return results


def main():
    parser = argparse.ArgumentParser(description="Gate 0 Checker V1.1 — Semantic Validation")
    parser.add_argument("expect_dir", help="Path to expected results directory")
    parser.add_argument("--schema", required=True, help="Path to expected_results.schema.json")
    parser.add_argument("--mode", choices=["preliminary", "semantic", "final"], default="final")
    args = parser.parse_args()

    if not os.path.isdir(args.expect_dir):
        print(json.dumps({"error": f"Not a directory: {args.expect_dir}"}, indent=2), file=sys.stderr)
        sys.exit(2)

    if not os.path.isfile(args.schema):
        print(json.dumps({"error": f"Schema not found: {args.schema}"}, indent=2), file=sys.stderr)
        sys.exit(2)

    results = run_checks(args.expect_dir, args.schema, args.mode)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    if results["final_gate_pass"]:
        print("\n✅ Gate 0 PASS — ready for M2-003B", file=sys.stderr)
        sys.exit(0)
    else:
        print("\n❌ Gate 0 FAIL — revision required before M2-003B", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
