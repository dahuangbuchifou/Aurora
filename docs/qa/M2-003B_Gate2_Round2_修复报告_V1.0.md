# M2-003B Gate 2 Round 2 修复报告 V1.0

> 任务：M2-003B Gate 2 — Round 1 Review → Round 2 修复
> 日期：2026-07-14 10:15 CST
> Round 1 复核：大G → FAIL (7 BLOCKER + 2 MAJOR)
> Round 2 修复：婉儿

---

## 1. 修复的BLOCKER

### B01: 原始Provider Payload 禁用字段检查 ✅
- `_check_raw_payload_fields()` 现在在DTO构建前检查原始JSON中所有4个禁用字段
- 支持 `raw_payloads` 参数传入原始payload
- 无原始payload时fallback到DTO getattr

### B02: independence_group 不作为禁用字段 ✅
- `PROVIDER_FORBIDDEN_FIELDS` 移除 `independence_group`
- EvidenceCandidate.independence_group 是合法Provider字段
- 其他4个禁用字段仍然被拒绝：source_quality_tier / evidence_strength /
  verification_status / epistemic_status
- 正常EvidenceCandidate（含independence_group）不会被SafetyGate误杀

### B03: Provider promotable=True → 无条件ERROR ✅
- `_check_provider_promotable()` 新增
- FactCandidate.promotable=True → PROVIDER_SET_PROMOTABLE ERROR
- ClaimCandidate.promotable_to_fact=True + 不可晋级类型 → FACT_POLLUTION_VALUATION ERROR

### B04: Fact污染通过target_claim_id引用 ✅
- `_check_fact_claim_graph()` 新增
- 构建candidate_index → 查找FactCandidate.target_claim_id → 校验Claim类型
- prediction/recommendation/value_judgment等不可晋级类型 → ERROR
- 关键词检测保留为辅助手段

### B05: Prompt Injection检查完整ContentUnit ✅
- `_check_prompt_injection_full()` → 读取完整ContentUnit文本
- 非Candidate子串 → 防止子串规避
- source_unit_id不可用时fallback到candidate字段

### B06: 真实ReviewBundle集成 ✅
- 管道：QuoteGate → SafetyGate → ReviewBundle.create()
- accepted/rejected_candidate_ids 由真实ReviewBundle提供
- bundle_sha256稳定（10×确定性运行）
- deterministic run_id 确保hash可重放

### B07: 移除SafetyGate中弱化QuoteGate ✅
- SafetyGate不再复制QuoteGate/ReferenceGate
- Fake quote和forged unit检查被移除（归入QuoteGate）
- SafetyGate通过 `existing_findings` 参数消费QuoteGate输出
- 不重复产生相同finding

---

## 2. 修复的MAJOR

### M01: INFO/WARNING不计为失败 ✅
- SafetyGateReport V2: `failed_count` → `error_count` (只计ERROR)
- `accepted_count` / `rejected_candidate_ids` / `accepted_candidate_ids` 新增
- INFO-level finding不影响error_count

### M02: 看板状态回退 ✅
- 总体进退回42%
- Gate 2: REVIEW_ROUND_1_FAILED
- Gate 3: BLOCKED_BY_GATE2

---

## 3. 测试结果

```text
全量：405 passed, 0 failed
总 Coverage：92.24% (≥90% ✅)
SafetyGate 模块：新增分支覆盖
冻结资产：60/60 SHA-256 全部匹配
核心Schema：零变更
Alembic：零新增
```

---

## 4. 待大G确认

1. B01-B07 修复是否完整
2. 10×确定性运行验证
3. 正常Evidence不被误杀（Case A/B/C回归）
4. ReviewBundle accepted/rejected与SafetyGate一致

---

_婉儿 🎋 2026-07-14_
