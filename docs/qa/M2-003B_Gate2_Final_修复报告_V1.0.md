# M2-003B Gate 2 Final 修复报告 V1.0

> 任务：M2-003B Gate 2 — Round 2 Review → Final Fix
> 日期：2026-07-14 12:00 CST
> Round 2 复核：大G → FAIL (3 BLOCKER + 2 MAJOR)
> Final 修复：婉儿

---

## 1. 修复的 R2-BLOCKER

### R2-B01: independence_group 恢复为 Provider 禁用字段 ✅

冻结任务卡明确规定5个禁用字段：

```text
independence_group
source_quality_tier
evidence_strength
verification_status
epistemic_status
```

Round 2 错误地移除了 independence_group。现已恢复。

**实现：**
- `PROVIDER_FORBIDDEN_FIELDS` 恢复为5元组
- `_check_raw_payload_fields()` 检查全部5个
- `EvidenceCandidate.independence_group` 默认值设为 `""`（Provider不填）
- Provider response 中如果出现 independence_group → `PROVIDER_OVERRIDE_FIELD` ERROR
- Aurora 引擎后续根据 Source/Document/DerivationLink 计算 independence_group

### R2-B02: raw_payload 改为 candidate_id 键值关联 ✅

Round 2 使用 `raw_payloads: list[dict]` 按 `candidates[i] ↔ raw_payloads[i]` 位置对齐。
FixtureProvider 会对候选排序，位置不可靠。

**修复后：**
```python
def validate(candidates, raw_payloads: dict[str, dict] | None = None)
```

`raw_payloads` 是一个 dict，键为 `candidate_id`，值为原始 Provider JSON payload。
无匹配时 fallback 到 DTO getattr 检查。

### R2-B03: 7类对抗场景全部进入 ReviewBundle + 10×稳定性 ✅

Round 2 只有5类进入 ReviewBundle，fake_quote 和 forged_or_outside_unit 仅单独运行 QuoteGate。

**修复后：**
- 全部7类 (`ALL_CASE_IDS`) 执行完整管道：
  ```
  JSON → build candidates + raw_payloads
  → QuoteGate → SafetyGate → ReviewBundle
  ```
- 每类10次运行，验证 bundle_sha256、accepted、rejected 全部稳定
- fake_quote / forged_unit 由 QuoteGate 独立检测，再通过 SafetyGate 消费 findings 进入 ReviewBundle

---

## 2. 修复的 R2-MAJOR

### R2-M01: 不可晋级改为 fact_claim 白名单 ✅

核心枚举 ClaimType 共8种：

```text
fact_claim, interpretation, causal_claim, prediction,
recommendation, risk_claim, value_judgment, hypothesis
```

其中只有 `fact_claim` 是可晋级类型。

Round 2 的黑名单遗漏了 `interpretation`、`causal_claim`、`risk_claim`，并包含了不存在的 `opinion`、`speculation`。

**修复后：**
```python
PROMOTABLE_CLAIM_TYPES: frozenset[str] = frozenset({"fact_claim"})
```
- `NON_PROMOTABLE_CLAIM_TYPE` finding 替代 `FACT_POLLUTION_VALUATION`
- 全7种非 fact_claim 类型均有参数化测试覆盖

### R2-M02: 报告表述修正 ✅

- 将"完整管道"改为"Gate 2 测试辅助管道"
- 明确了当前不使用 FixtureProvider / ProviderResponse / ExtractionEnvelope
- 集成测试文件和正式 Provider 路径是两套实现

---

## 3. 测试结果

```text
全量：431 passed, 0 failed
覆盖率：92.37% (≥90% ✅)
冻结资产：60/60 SHA-256 全部匹配
核心 Schema：零变更
Alembic：零新增
数据库：零迁移
Commit：2eb04e3
```

---

## 4. 验证清单

| 检查项 | 状态 |
|--------|------|
| independence_group 在禁用字段中 | ✅ |
| 5个禁用字段全部在 raw_payload 检查 | ✅ |
| raw_payload 按 candidate_id 关联 | ✅ |
| 7类全入 ReviewBundle + 10×稳定 | ✅ |
| fact_claim 白名单 | ✅ |
| interpretation 等被拒绝 | ✅ |
| 冻结资产 60/60 | ✅ |
| 无 Schema 变更 | ✅ |
| 431/431 PASS | ✅ |

---

_婉儿 🎋 2026-07-14_
