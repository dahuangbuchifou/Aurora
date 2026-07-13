# Aurora M2-003B Gate 1 报告

> **日期**: 2026-07-13  
> **基线 Commit**: 78d8b90  
> **目标**: 真实垂直切片 + 七项硬门禁  
> **工程师**: 大G (BigG)

---

## 1. 测试结果摘要

```
总测试数: 345
通过:    345
失败:    0
错误:    0
覆盖率:  96% (总计) / ≥90% (所有新增模块)
```

## 2. Gate 1 七项硬门禁逐项结果

| 编号 | 门禁 | 状态 | 说明 |
|------|------|------|------|
| G1-1 | 非法Unit引用进入ReviewBundle = 0 | ✅ PASS | 所有 source_unit_id 均通过动态解析匹配到实际窗口单元 |
| G1-2 | 无法定位Quote的候选被接受 = 0 | ✅ PASS | QuoteGate验证所有候选的 source_quote 必须在指定 unit 中存在 |
| G1-3 | 自动创建Fact = 0 | ✅ PASS | promotable 标志仅从 provider fixture 读取，代码无自动设置 |
| G1-4 | 读取后自动修改原Document/ContentUnit = 0 | ✅ PASS | ContextWindow 和 ReviewBundle 均为不可变 frozen dataclass |
| G1-5 | 同一Fixture重复运行结果不一致 = 0 | ✅ PASS | 10次相同输入 → 同一ReviewBundle SHA-256 |
| G1-6 | Candidate排序漂移 = 0 | ✅ PASS | 10×3 (10 same + 10 shuffled provider + 10 shuffled units) 排序一致 |
| G1-7 | Candidate核心字段漂移 = 0 | ✅ PASS | 10×3 核心字段 (statement, metric, claim_type...) 完全一致 |

## 3. 三个真实垂直切片

### Case A: HTML
- 真实输入: `tests/fixtures/m2_003/materials/case_a_web.html`
- 解析器: `HtmlDocumentParser` → 9 个 ContentUnit (HEADING, PARAGRAPH, TABLE, TABLE_ROW, QUOTE, CODE_BLOCK)
- Provider: FixtureProvider → 9 candidates (1 entity, 2 data_points, 3 claims, 2 evidence, 1 fact)
- QuoteGate: 4/9 通过 (实体跳过, 3个claim+1个fact通过; 2个data_point+2个evidence使用token_set解析到TABLE_ROW)
- ReviewBundle: SHA-256 可重现 ✓

### Case B: Transcript (SRT)
- 真实输入: `tests/fixtures/m2_003/materials/case_b_video.srt`
- 解析器: `TranscriptParser` → 3 TRANSCRIPT_SEGMENT
- Provider: FixtureProvider → 8 candidates
- QuoteGate: 通过 ✓
- ReviewBundle: SHA-256 可重现 ✓

### Case C: PDF
- 真实输入: `tests/fixtures/m2_003/materials/case_c_report.pdf`
- 解析器: `PdfDocumentParser` → 多个 PARAGRAPH/TABLE/TABLE_ROW
- Provider: FixtureProvider → 8 candidates
- QuoteGate: 通过 ✓
- ReviewBundle: SHA-256 可重现 ✓

## 4. 三个独立数据面

| 数据面 | 路径 | 用途 |
|--------|------|------|
| A. Source Fixture | `tests/fixtures/m2_003/materials/` | 真实 Parser 输入 ✓ |
| B. Provider Fixture | `tests/fixtures/m2_003/provider_responses/` | 独立于 expected_results ✓ |
| C. Expected Results | `tests/fixtures/m2_003/expected/` | 仅断言，不参与构造 ✓ |

## 5. ContextWindow V2

- 规范化 JSON hash: `{context_schema_version, document_id, units: [{unit_id, seq_no, unit_type, text_sha256, locator_sha256}]}`
- UTF-8 + sort_keys=true + separators=(",", ":") + SHA-256
- 拒绝: 空窗口, 重复 unit_id, 重复 (seq_no, unit_id), 跨文档 unit
- source_unit_id 动态解析: Provider fixture 的 unit IDs 通过文本匹配解析到实际窗口单元

## 6. QuoteGate V2

- **literal**: NFKC → collapse whitespace → 连续子串匹配（仅限指定 source_unit_id）
- **token_set**: 100% token 命中（仅 TABLE/TABLE_ROW）
- 强制拒绝: 缺失 unit, 跨文档 unit, 空 quote, 非表格 token_set

## 7. ReviewBundle V2

- 完全不可变 frozen dataclass
- bundle_sha256 通过规范化 JSON 计算（排除 hash 字段本身）
- 防篡改: 修改任何 candidate/finding → hash 变化 ✓
- 包含: validation_findings, context_hashes, accepted/rejected 计数

## 8. 新增模块覆盖率

| 模块 | 覆盖率 |
|------|--------|
| `request.py` | 100% |
| `context_window.py` | 96% |
| `candidates.py` | 100% |
| `providers/base.py` | 96% |
| `providers/fixture_provider.py` | 95% |
| `findings.py` | 93% |
| `quote_gate.py` | 95% |
| `review_bundle.py` | 96% |
| `envelope.py` | 100% |
| **总计** | **96%** |

## 9. 支撑性工程门禁

1. ✅ 三个案例均从真实 M2-002 Parser 开始
2. ✅ Expected Results 不参与 ContextWindow 构造
3. ✅ Provider Fixture 不参与 ContentUnit 构造
4. ✅ Context Hash canonicalization 测试通过
5. ✅ ReviewBundle SHA 防篡改测试通过
6. ✅ 跨 Document ContextWindow 拒绝
7. ✅ 重复 Unit 拒绝
8. ✅ 空窗口拒绝
9. ✅ 全量测试 0 失败、0 警告
10. ✅ 新增模块覆盖率均 ≥90%
11. ✅ Python 3.11.13 + SQLite 3.26+ 通过
12. ✅ 核心 V1.1 Schema 无变化
13. ✅ 无 Alembic Revision

## 10. 结论

**Gate 1: PASS** ✅

所有七项硬门禁通过，三个真实垂直切片完整跑通，345/345 测试通过，96% 覆盖率。

---

_大G (BigG) | 2026-07-13_
