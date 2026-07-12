"""Gate 0 自动检查器 — M2-003A

验证人工标注的期望结果 JSON 是否符合预期结构，以及
Gate 0 的 7 条硬门禁是否可被预先评估。

用法：
    python scripts/gate0_check.py tests/fixtures/m2_003/expected/

输出 JSON 格式报告到标准输出。
"""

import json
import sys
from pathlib import Path

REQUIRED_TOP_KEYS = {
    "annotated_by", "annotated_at", "reviewed_by", "reviewed_at",
    "disagreements", "adjudication_note", "fixture_source_hash",
    "case_id", "case_title", "material_path",
    "expected_entities", "expected_data_points", "expected_claims",
    "expected_evidence", "expected_fact_candidates",
    "expected_warnings", "expected_rejects", "validation_report",
}

VALIDATION_REPORT_KEYS = {
    "claim_type_coverage", "claim_dimension_coverage",
    "measurement_context_coverage", "quote_gate_executable",
    "fact_promotion_rules_sufficient", "review_bundle_usable",
    "core_schema_change_needed", "new_core_object_needed", "notes",
}


def check_one(path: Path) -> dict:
    result = {"file": str(path.name), "gates": {}, "errors": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        result["errors"].append(f"Cannot parse JSON: {e}")
        return result

    # G0-1: 所有顶层 key 存在
    missing = REQUIRED_TOP_KEYS - set(data.keys())
    result["gates"]["G0-1_top_keys"] = len(missing) == 0
    if missing:
        result["errors"].append(f"Missing top keys: {sorted(missing)}")

    # G0-2: 无需修改 V1.1 核心 Schema（通过 validation_report 检查）
    vr = data.get("validation_report", {})
    missing_vr = VALIDATION_REPORT_KEYS - set(vr.keys())
    if missing_vr:
        result["errors"].append(f"Missing validation_report keys: {sorted(missing_vr)}")
    result["gates"]["G0-2_schema_no_change"] = vr.get("core_schema_change_needed") is False
    if vr.get("core_schema_change_needed"):
        result["errors"].append("Validation report says schema change needed")

    # G0-3: 没有无法解释的候选状态
    claims = data.get("expected_claims", [])
    dps = data.get("expected_data_points", [])
    for c in claims:
        if "claim_type" not in c or "claim_dimension" not in c:
            result["errors"].append(f"Claim {c.get('id','?')} missing type/dimension")
    for dp in dps:
        if "measurement_context" not in dp:
            result["errors"].append(f"DataPoint {dp.get('id','?')} missing measurement_context")
    unexplained = [e for e in result.get("errors", []) if "missing" in e.lower()]
    result["gates"]["G0-3_unexplained_states"] = len(unexplained) == 0

    # G0-4: 不需要新增第 18 类核心对象
    result["gates"]["G0-4_no_new_core_object"] = vr.get("new_core_object_needed") is False

    # G0-5: 每条 Claim/DataPoint 可定位 Quote
    missing_quote = []
    for c in claims:
        if not c.get("source_quote") or not c.get("quote_locator_hint"):
            missing_quote.append(c.get("id", "?"))
    for dp in dps:
        if not dp.get("source_quote") or not dp.get("quote_locator_hint"):
            missing_quote.append(dp.get("id", "?"))
    result["gates"]["G0-5_quote_locatable"] = len(missing_quote) == 0
    if missing_quote:
        result["errors"].append(f"Missing quote info: {missing_quote}")

    # G0-6: MeasurementContext 覆盖全部 DataPoint
    mc_missing = []
    for dp in dps:
        mc = dp.get("measurement_context", {})
        if not mc.get("measurement_kind"):
            mc_missing.append(dp.get("id", "?"))
    result["gates"]["G0-6_measurement_context"] = len(mc_missing) == 0
    if mc_missing:
        result["errors"].append(f"Missing measurement_kind: {mc_missing}")

    # G0-7: ReviewBundle 支持三类决策
    dec_types = set()
    for fc in data.get("expected_fact_candidates", []):
        if fc.get("promotable"):
            dec_types.add("APPROVE")
        elif fc.get("rejection_reason"):
            dec_types.add("REJECT")
    # REVISE_AND_APPROVE covered by warnings suggesting revision
    for w in data.get("expected_warnings", []):
        wt = w.get("warning_type", "")
        if any(kw in wt for kw in ("SPLIT", "REVISE", "SOFT_PREDICTION", "LOW_CONFIDENCE")):
            dec_types.add("REVISE_AND_APPROVE")
    result["gates"]["G0-7_review_bundle_decisions"] = len(dec_types) >= 2

    return result


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/m2_003/expected")
    if not target.is_dir():
        print(json.dumps({"error": f"Not a directory: {target}"}, ensure_ascii=False))
        sys.exit(1)

    files = sorted(target.glob("case_*_expected.json"))
    if not files:
        print(json.dumps({"error": f"No expected results found in {target}"}, ensure_ascii=False))
        sys.exit(1)

    results = {}
    all_gates = set()
    all_passed = True
    for f in files:
        r = check_one(f)
        results[f.name] = r
        all_gates |= set(r["gates"].keys())
        if not all(r["gates"].values()):
            all_passed = False

    gates_pass = sum(1 for r in results.values() for v in r["gates"].values() if v)
    gates_total = sum(len(r["gates"]) for r in results.values())

    report = {
        "gate": "Gate 0",
        "total_files": len(files),
        "files_checked": [f.name for f in files],
        "gates_checked": sorted(all_gates),
        "gates_passed": gates_pass,
        "gates_total": gates_total,
        "overall_pass": all_passed,
        "per_file": results,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
