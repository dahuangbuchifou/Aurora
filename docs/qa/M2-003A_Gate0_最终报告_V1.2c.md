# M2-003A Gate 0 最终报告 V1.2c

> **状态**: FINAL_PASS ✅  
> **报告日期**: 2026-07-13 11:45 CST  
> **Checker**: V1.2c (35/35 — 真实Quote + 冻结ContentUnit快照 + 真实负向测试)

---

## V1.2c 核心变更

V1.2b 的 Quote Gate 用 golden set 自己的 quotes 反向构建合成 ContentUnit（循环自证）。V1.2c 彻底解决：

### 冻结 ContentUnit 快照
- `tests/fixtures/m2_003/content_units/case_a_content_units.json`
- `tests/fixtures/m2_003/content_units/case_b_content_units.json`  
- `tests/fixtures/m2_003/content_units/case_c_content_units.json`

每份快照包含 `document_id, parser_name, parser_version, parser_config_hash, semantic_content_hash, snapshot_sha256, units[]`。

### 真实 Quote Gate (V1.2c)
```
冻结CU快照 → 按 source_unit_id 定位具体 ContentUnit
→ 验证 unit 存在且属于正确文档
→ NFKC 规范化子串匹配（literal）/ 100% token 命中（token_set）
```

### Candidate 新增 source_unit_id
DataPointCandidate, ClaimCandidate, EvidenceCandidate 均增加 `source_unit_id` 字段。Gate 0 期望结果中每个候选都指向冻结快照中的一个 ContentUnit。

### ContextWindow 文档归属校验
`ContextWindow.from_content_units()` 现在强制执行：
```python
if unit.document_id != document_id:
    raise ContextWindowError(...)
```

---

## Gate 0 V1.2c 门禁结果

```
Gate 0 V1.2c: 35/35 PASS ✅
final_gate_pass: true
```

| Gate | Case A | Case B | Case C |
|------|:---:|:---:|:---:|
| SCHEMA_V12 | ✅ | ✅ | ✅ |
| SHA256_FILE | ✅ | ✅ | ✅ |
| QUOTE_GATE (V1.2c 真实) | ✅ | ✅ | ✅ |
| ENUMS | ✅ | ✅ | ✅ |
| ID_UNIQUE | ✅ | ✅ | ✅ |
| REFERENCES | ✅ | ✅ | ✅ |
| FC_RULES | ✅ | ✅ | ✅ |
| PREDICTION | ✅ | ✅ | ✅ |
| DATETIME (含日历校验) | ✅ | ✅ | ✅ |
| REVIEWER | ✅ | ✅ | ✅ |
| DISAGREEMENTS_RESOLVED | ✅ | ✅ | ✅ |

---

## 真实负向测试 (5/5 PASS — 全部真实)

| # | 场景 | 行为 |
|---|------|------|
| N5 | 正确Quote + 错误source_unit_id | ❌ not found in frozen snapshot → 正确拒绝 |
| N6 | 正确Quote但分配给错误的Unit | ❌ literal match FAILED → 正确拒绝 |
| N7 | token_set中缺失一个关键token | ❌ token_set match FAILED (missing tokens) → 正确拒绝 |
| N8 | 跨Document的unit引用 | ❌ not found in foreign snapshot → 正确拒绝 |
| N9 | 2026-02-31 calendar拒绝 | ❌ day=31 exceeds month 2 last day (28) → 正确拒绝 |

---

## 三类 ReviewDecision 跨案例覆盖

| 动作 | 来源 |
|------|------|
| APPROVE | A: FactCandidate (年报数据) / C: FactCandidate (年报数据) |
| REJECT | A: Reject (代码块) / B: UP主观断 (循环自证) / C: prediction |
| REVISE | A: 管理层 prediction → 完整双层Claim Payload |

---

## 项目状态

```text
M2-003A语义黄金集：PASS ✅
Schema与ReviewDecision：PASS ✅
SHA实际文件校验：PASS ✅
Quote Gate真实性 (V1.2c)：PASS ✅ (非循环自证)
负向测试框架：PASS ✅ (9项 + 5项真实 = 14项全部通过)
Gate 0：FINAL_PASS ✅
M2-003B：READY (Gate 1 组件预检查 7/7 — 待升级为真实ContentUnit链路)
```

---

_婉儿 V1.2c · 大G复核 · 大黄裁断_ 🎋
