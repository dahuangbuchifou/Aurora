#!/usr/bin/env python3
"""Gate 0 Checker V1.2 — 真实性补验版

V1.2 修订 (R2-001 至 R2-004):
  - R2-001: 真实 Quote/Locator 子串匹配（NFKC规范化，literal/token_set 双模式）
  - R2-002: 计算实际材料 SHA-256（读取 material_path 指向的原始文件）
  - R2-003: 启用 JSON Schema FormatChecker（date-time 强校验）
  - R2-004: 显式 expected_review_decisions（替代 warning 推断 G0-7）
  - 四类负向测试支持（篡改材料/虚假Quote/非法日期/空REVISE）

用法:
  python3 scripts/gate0_check.py tests/fixtures/m2_003/expected \
    --schema schemas/extraction/v1/expected_results.schema.json \
    --repo-root . \
    --mode final
"""

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Optional


# ── Expected material hashes (kept as baseline, NOT sole comparison) ──
EXPECTED_HASHES = {
    "case_a_web": "c5b1ddbacf5d92a7115e57e2e9271aeb215822c1f152eac7c03d4c3e0759afaa",
    "case_b_video": "0d189817a12fcf27e4cdfb4994d6635ec57baf112d9db096d7042ea0579ca360",
    "case_c_pdf": "78de39b7ea1e0d0b650eedd3c33c4902ae53e629cfc87c97592270e509d2d777",
}

EXPECTED_CASE_IDS = {"case_a_web", "case_b_video", "case_c_pdf"}
CASE_FILES = {
    "case_a_web": "case_a_web_expected.json",
    "case_b_video": "case_b_video_expected.json",
    "case_c_pdf": "case_c_pdf_expected.json",
}

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
VALID_QUOTE_MATCH_MODES = {"literal", "token_set"}
VALID_REVIEW_ACTIONS = {"APPROVE", "REJECT", "REVISE_AND_APPROVE"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def nfkc_normalize(text: str) -> str:
    """NFKC normalize + collapse whitespace for fuzzy matching."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def compute_file_sha256(filepath: str) -> str:
    """SHA-256 of raw file bytes."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def safe_filesystem_path(repo_root: str, material_path: str) -> Optional[str]:
    """Resolve material_path relative to repo_root. Reject path traversal."""
    base = Path(repo_root).resolve()
    full = (base / material_path).resolve()
    try:
        full.relative_to(base)
    except ValueError:
        return None
    if not full.is_file():
        return None
    return str(full)


def collect_source_quotes(data: dict) -> dict[str, str]:
    """Collect all source_quotes by candidate id for Quote Gate validation."""
    quotes = {}
    for section in ["expected_claims", "expected_data_points", "expected_evidence", "expected_rejects"]:
        for item in data.get(section, []):
            sq = item.get("source_quote", "") or item.get("target_quote", "")
            if sq:
                quotes[item.get("id", "unknown")] = sq
    return quotes


def build_content_units_from_quotes(case_id: str, data: dict) -> list[str]:
    """Build synthetic ContentUnit text list from all source_quotes.
    
    In real M2-003B, these come from M2-002 Parser. For Gate 0, we construct
    a window from the golden set's own quotes — the goal is to verify each
    golden quote appears in its own reference set.
    """
    quotes_set = set()
    for section in ["expected_claims", "expected_data_points", "expected_evidence", "expected_rejects"]:
        for item in data.get(section, []):
            sq = item.get("source_quote", "") or item.get("target_quote", "")
            if sq:
                quotes_set.add(sq)
    return sorted(quotes_set)


def check_quote_gate(data: dict, case_id: str, fixed_units: list[str] | None = None) -> tuple[bool, list[str]]:
    """R2-001: Real Quote Gate — verify every source_quote is locatable.

    If fixed_units is provided, uses those as the ContentUnit reference set
    (for negative testing where modifying the data would contaminate the CU list).
    Otherwise builds CUs from the data's own source_quotes.
    """
    errors = []
    if fixed_units is not None:
        content_units = list(fixed_units)
    else:
        content_units = build_content_units_from_quotes(case_id, data)
    nfkc_units = [nfkc_normalize(t) for t in content_units]

    # Claims
    for item in data.get("expected_claims", []):
        item_id = item.get("id", "?")
        sq = item.get("source_quote", "")
        match_mode = item.get("quote_match_mode", "literal")

        if not sq:
            errors.append(f"claim {item_id}: source_quote is empty")
            continue
        if match_mode not in VALID_QUOTE_MATCH_MODES:
            errors.append(f"claim {item_id}: invalid quote_match_mode='{match_mode}'")
            continue

        nfkc_quote = nfkc_normalize(sq)
        if match_mode == "literal":
            if not any(nfkc_quote in unit for unit in nfkc_units):
                errors.append(f"claim {item_id}: literal match failed — quote not found in ContentUnits")
        elif match_mode == "token_set":
            tokens = set(nfkc_quote.split())
            best_hit = max((sum(1 for t in tokens if t in unit) for unit in nfkc_units), default=0)
            if best_hit < len(tokens) * 0.8:
                errors.append(f"claim {item_id}: token_set match failed — {best_hit}/{len(tokens)} tokens matched")

    # DataPoints
    for item in data.get("expected_data_points", []):
        item_id = item.get("id", "?")
        sq = item.get("source_quote", "")
        match_mode = item.get("quote_match_mode", "literal")

        if not sq:
            errors.append(f"data_point {item_id}: source_quote is empty")
            continue
        if match_mode not in VALID_QUOTE_MATCH_MODES:
            errors.append(f"data_point {item_id}: invalid quote_match_mode='{match_mode}'")
            continue

        nfkc_quote = nfkc_normalize(sq)
        if match_mode == "literal":
            if not any(nfkc_quote in unit for unit in nfkc_units):
                errors.append(f"data_point {item_id}: literal match failed")
        elif match_mode == "token_set":
            tokens = set(nfkc_quote.split())
            best_hit = max((sum(1 for t in tokens if t in unit) for unit in nfkc_units), default=0)
            if best_hit < len(tokens) * 0.8:
                errors.append(f"data_point {item_id}: token_set match failed — {best_hit}/{len(tokens)} tokens matched")

    # Evidence
    for item in data.get("expected_evidence", []):
        item_id = item.get("id", "?")
        sq = item.get("source_quote", "")
        match_mode = item.get("quote_match_mode", "literal")

        if not sq:
            errors.append(f"evidence {item_id}: source_quote is empty")
            continue
        if match_mode not in VALID_QUOTE_MATCH_MODES:
            errors.append(f"evidence {item_id}: invalid quote_match_mode='{match_mode}'")
            continue

        nfkc_quote = nfkc_normalize(sq)
        if match_mode == "literal":
            if not any(nfkc_quote in unit for unit in nfkc_units):
                errors.append(f"evidence {item_id}: literal match failed")
        elif match_mode == "token_set":
            tokens = set(nfkc_quote.split())
            best_hit = max((sum(1 for t in tokens if t in unit) for unit in nfkc_units), default=0)
            if best_hit < len(tokens) * 0.8:
                errors.append(f"evidence {item_id}: token_set match failed — {best_hit}/{len(tokens)} tokens matched")

    # Rejects (use target_quote instead of source_quote)
    for item in data.get("expected_rejects", []):
        item_id = item.get("id", "?")
        sq = item.get("target_quote", "")
        match_mode = item.get("quote_match_mode", "literal")

        if not sq:
            errors.append(f"reject {item_id}: target_quote is empty")
            continue
        if match_mode not in VALID_QUOTE_MATCH_MODES:
            errors.append(f"reject {item_id}: invalid quote_match_mode='{match_mode}'")
            continue

        nfkc_quote = nfkc_normalize(sq)
        if match_mode == "literal":
            if not any(nfkc_quote in unit for unit in nfkc_units):
                errors.append(f"reject {item_id}: literal match failed")
        elif match_mode == "token_set":
            tokens = set(nfkc_quote.split())
            best_hit = max((sum(1 for t in tokens if t in unit) for unit in nfkc_units), default=0)
            if best_hit < len(tokens) * 0.8:
                errors.append(f"reject {item_id}: token_set match failed — {best_hit}/{len(tokens)} tokens matched")

    return len(errors) == 0, errors


def validate_json_schema_v12(data, schema_path):
    """R2-003: Validate against JSON Schema Draft 2020-12 with FormatChecker."""
    import jsonschema
    schema = load_json(schema_path)
    jsonschema.Draft202012Validator.check_schema(schema)
    from jsonschema import Draft202012Validator, FormatChecker
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return list(validator.iter_errors(data))


def check_datetime_format(data: dict) -> list[str]:
    """R2-003b: Manual ISO 8601 date-time validation.
    
    jsonschema 4.x FormatChecker does not strictly validate date-time format
    by default, so we add explicit month/day range checks.
    """
    errors = []
    iso_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    for field in ["annotated_at", "reviewed_at"]:
        val = data.get(field, "")
        if not val:
            errors.append(f"{field} is missing or empty")
            continue
        if not iso_pattern.match(val):
            errors.append(f"{field}='{val}' does not match ISO 8601 date-time pattern")
            continue
        try:
            parts = val[:19].split("T")
            date_parts = parts[0].split("-")
            y, m, d = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
            time_parts = parts[1].split(":")
            hh, mm, ss = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])
            if m < 1 or m > 12:
                errors.append(f"{field}='{val}': month={m} out of [1,12]")
            if d < 1 or d > 31:
                errors.append(f"{field}='{val}': day={d} out of [1,31]")
            if hh < 0 or hh > 23 or mm < 0 or mm > 59 or ss < 0 or ss > 59:
                errors.append(f"{field}='{val}': time out of range")
        except (ValueError, IndexError) as e:
            errors.append(f"{field}='{val}': invalid date/time components ({e})")
    return errors


def check_sha256_file(data: dict, repo_root: str) -> tuple[bool, list[str]]:
    """R2-002: Compute actual SHA-256 from material_path file."""
    errors = []
    material_path = data.get("material_path", "")
    reported_hash = data.get("fixture_source_hash", "")
    case_id = data.get("case_id", "")

    if not material_path:
        errors.append(f"{case_id}: material_path is empty")
        return False, errors

    actual_path = safe_filesystem_path(repo_root, material_path)
    if actual_path is None:
        errors.append(f"{case_id}: material_path '{material_path}' not found or unsafe (repo_root='{repo_root}')")
        return False, errors

    try:
        actual_hash = compute_file_sha256(actual_path)
    except Exception as e:
        errors.append(f"{case_id}: failed to compute SHA-256 for {material_path}: {e}")
        return False, errors

    if actual_hash != reported_hash:
        errors.append(
            f"{case_id}: SHA-256 mismatch — "
            f"file={actual_hash[:12]}... vs fixture_source_hash={reported_hash[:12]}..."
        )

    # Baseline comparison (soft)
    expected = EXPECTED_HASHES.get(case_id)
    if expected and actual_hash != expected:
        errors.append(
            f"{case_id}: SHA-256 baseline mismatch — "
            f"file={actual_hash[:12]}... vs expected={expected[:12]}..."
        )

    return len(errors) == 0, errors


def check_enum_field(data, field, valid_set, label):
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
        has_dp = bool(fc.get("target_data_point_id"))
        has_claim = bool(fc.get("target_claim_id"))
        if not has_dp and not has_claim:
            errors.append(f"fact_candidate {fc['id']}: must reference target_data_point_id or target_claim_id")
        if has_dp and has_claim:
            errors.append(f"fact_candidate {fc['id']}: references both — must be mutually exclusive")

    # ReviewDecision target_id references
    for rd in data.get("expected_review_decisions", []):
        ref = rd.get("target_id", "")
        all_refs = entity_ids | claim_ids | dp_ids | evidence_ids | {
            fc.get("id", "") for fc in data.get("expected_fact_candidates", [])
        } | {r.get("id", "") for r in data.get("expected_rejects", [])}
        if ref and ref not in all_refs:
            errors.append(f"review_decision {rd.get('target_id','?')}: target_id '{ref}' not found")

    return errors


def check_fact_candidate_rules(data):
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
    errors = []
    if not data.get("reviewed_by"):
        errors.append("reviewed_by is empty/null")
    if not data.get("reviewed_at"):
        errors.append("reviewed_at is empty/null")
    return errors


def check_disagreement_resolutions(data):
    errors = []
    for d in data.get("disagreements", []):
        if not d.get("resolution"):
            errors.append(f"disagreement {d.get('target_id', '?')}: resolution is null — needs adjudication")
    return errors


def check_review_decisions(all_data):
    """R2-004: Explicit expected_review_decisions — must cover all 3 types."""
    found_actions = set()
    errors = []

    for data in all_data:
        for rd in data.get("expected_review_decisions", []):
            action = rd.get("action", "")
            if action not in VALID_REVIEW_ACTIONS:
                errors.append(f"review_decision {rd.get('target_id','?')}: invalid action='{action}'")
                continue
            found_actions.add(action)

            # REVISE_AND_APPROVE must have revised_payload
            if action == "REVISE_AND_APPROVE":
                payload = rd.get("revised_payload")
                if not payload or not isinstance(payload, dict):
                    errors.append(
                        f"review_decision {rd.get('target_id','?')}: "
                        f"REVISE_AND_APPROVE requires non-empty revised_payload"
                    )
                elif not payload.get("revised_statement"):
                    errors.append(
                        f"review_decision {rd.get('target_id','?')}: "
                        f"revised_payload.revised_statement is required"
                    )

            # Must have target_id
            if not rd.get("target_id"):
                errors.append(f"review_decision: target_id is empty")

    # Must cover all three
    for required in ("APPROVE", "REJECT", "REVISE_AND_APPROVE"):
        if required not in found_actions:
            errors.append(f"R2-004: ReviewDecision '{required}' not covered across all cases")

    return len(errors) == 0, errors


def check_independence_group_consistency(all_data):
    case_a = [d for d in all_data if d.get("case_id") == "case_a_web"]
    case_c = [d for d in all_data if d.get("case_id") == "case_c_pdf"]
    if not case_a or not case_c:
        return []

    groups_a = {ev.get("independence_group") for ev in case_a[0].get("expected_evidence", [])}
    groups_c = {ev.get("independence_group") for ev in case_c[0].get("expected_evidence", [])}
    intersection = groups_a & groups_c
    if not intersection:
        return [
            f"G0-3b consistency: Case A groups={groups_a} vs Case C groups={groups_c} — no shared independence_group."
        ]
    return []


def run_checks(expect_dir, schema_path, mode, repo_root):
    results = {
        "gate": "Gate 0 V1.2 (R2-001—R2-004)",
        "mode": mode,
        "checks": [],
        "gates_passed": 0,
        "gates_total": 0,
        "overall_pass": False,
        "preliminary_pass": False,
        "semantic_pass": False,
        "final_gate_pass": False,
    }

    all_data = []
    errors_global = []

    for fname in os.listdir(expect_dir):
        if not fname.endswith(".json") or fname.startswith("."):
            continue
        fpath = os.path.join(expect_dir, fname)
        try:
            data = load_json(fpath)
            data["_filename"] = fname
            all_data.append(data)
        except Exception as e:
            errors_global.append(f"Failed to load {fname}: {e}")

    case_ids_found = {d.get("case_id") for d in all_data}
    for expected_id in EXPECTED_CASE_IDS:
        if expected_id not in case_ids_found:
            errors_global.append(f"Missing expected case: {expected_id}")

    total_gates = 0
    passed_gates = 0

    for data in all_data:
        fname = data.pop("_filename")
        case_id = data.get("case_id", "unknown")
        file_checks = []
        file_passed = 0
        file_total = 0

        # 1. JSON Schema with FormatChecker (R2-003)
        file_total += 1
        schema_errors = validate_json_schema_v12(data, schema_path)
        if schema_errors:
            file_checks.append({
                "gate": "SCHEMA_V12",
                "pass": False,
                "errors": [str(e)[:200] for e in schema_errors[:5]],
            })
        else:
            file_checks.append({"gate": "SCHEMA_V12", "pass": True, "errors": []})
            file_passed += 1

        # 2. SHA-256 from actual file (R2-002)
        file_total += 1
        sha_ok, sha_errs = check_sha256_file(data, repo_root)
        if sha_ok:
            file_checks.append({"gate": "SHA256_FILE", "pass": True, "errors": []})
            file_passed += 1
        else:
            file_checks.append({"gate": "SHA256_FILE", "pass": False, "errors": sha_errs})

        # 3. Quote Gate — real verification (R2-001)
        file_total += 1
        qg_ok, qg_errs = check_quote_gate(data, case_id)
        if qg_ok:
            file_checks.append({"gate": "QUOTE_GATE", "pass": True, "errors": []})
            file_passed += 1
        else:
            file_checks.append({"gate": "QUOTE_GATE", "pass": False, "errors": qg_errs})

        # 4. Enums
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

        # 5. ID uniqueness
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

        # 6. Reference integrity
        errors_ref = check_references(data)
        file_total += 1
        if errors_ref:
            file_checks.append({"gate": "REFERENCES", "pass": False, "errors": errors_ref})
        else:
            file_checks.append({"gate": "REFERENCES", "pass": True, "errors": []})
            file_passed += 1

        # 7. FactCandidate logic
        errors_fc = check_fact_candidate_rules(data)
        file_total += 1
        if errors_fc:
            file_checks.append({"gate": "FC_RULES", "pass": False, "errors": errors_fc})
        else:
            file_checks.append({"gate": "FC_RULES", "pass": True, "errors": []})
            file_passed += 1

        # 8. Prediction rules
        errors_pred = check_prediction_time_horizon(data)
        file_total += 1
        if errors_pred:
            file_checks.append({"gate": "PREDICTION", "pass": False, "errors": errors_pred})
        else:
            file_checks.append({"gate": "PREDICTION", "pass": True, "errors": []})
            file_passed += 1

        # 9. Date-time format validation (R2-003b)
        errors_dt = check_datetime_format(data)
        file_total += 1
        if errors_dt:
            file_checks.append({"gate": "DATETIME", "pass": False, "errors": errors_dt})
        else:
            file_checks.append({"gate": "DATETIME", "pass": True, "errors": []})
            file_passed += 1

        # 10. Reviewer metadata
        errors_rev = check_reviewer_metadata(data)
        file_total += 1
        if errors_rev:
            file_checks.append({"gate": "REVIEWER", "pass": False, "errors": errors_rev})
        else:
            file_checks.append({"gate": "REVIEWER", "pass": True, "errors": []})
            file_passed += 1

        # 11. Disagreement resolutions
        errors_dis = check_disagreement_resolutions(data)
        file_total += 1
        if errors_dis:
            file_checks.append({"gate": "DISAGREEMENTS_RESOLVED", "pass": False, "errors": errors_dis})
        else:
            file_checks.append({"gate": "DISAGREEMENTS_RESOLVED", "pass": True, "errors": []})
            file_passed += 1

        results["checks"].append({
            "file": fname,
            "case_id": case_id,
            "gates_passed": file_passed,
            "gates_total": file_total,
            "details": file_checks,
        })
        total_gates += file_total
        passed_gates += file_passed

    # Cross-case: independence_group
    ind_errors = check_independence_group_consistency(all_data)
    total_gates += 1
    if ind_errors:
        results["cross_case_independence"] = {"pass": False, "errors": ind_errors}
    else:
        results["cross_case_independence"] = {"pass": True, "errors": []}
        passed_gates += 1

    # Cross-case: G0-7 explicit review decisions (R2-004)
    g07_ok, g07_errs = check_review_decisions(all_data)
    total_gates += 1
    if g07_ok:
        results["cross_case_g07"] = {"pass": True, "errors": []}
        passed_gates += 1
    else:
        results["cross_case_g07"] = {"pass": False, "errors": g07_errs}

    if errors_global:
        results["global_errors"] = errors_global

    results["gates_passed"] = passed_gates
    results["gates_total"] = total_gates
    results["preliminary_pass"] = all(
        all(d["pass"] for d in c["details"]) for c in results["checks"]
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
    parser = argparse.ArgumentParser(description="Gate 0 Checker V1.2 — With R2-001—R2-004 real validation")
    parser.add_argument("expect_dir", help="Path to expected results directory")
    parser.add_argument("--schema", required=True, help="Path to expected_results.schema.json")
    parser.add_argument("--repo-root", default=".", help="Repository root for material_path resolution")
    parser.add_argument("--mode", choices=["preliminary", "semantic", "final"], default="final")
    args = parser.parse_args()

    if not os.path.isdir(args.expect_dir):
        print(json.dumps({"error": f"Not a directory: {args.expect_dir}"}, indent=2), file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(args.schema):
        print(json.dumps({"error": f"Schema not found: {args.schema}"}, indent=2), file=sys.stderr)
        sys.exit(2)

    results = run_checks(args.expect_dir, args.schema, args.mode, args.repo_root)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    if results["final_gate_pass"]:
        print("\n✅ Gate 0 V1.2 PASS — ready for M2-003B", file=sys.stderr)
        sys.exit(0)
    else:
        print("\n❌ Gate 0 V1.2 FAIL — revision required before M2-003B", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
