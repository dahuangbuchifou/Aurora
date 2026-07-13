# M2-003B Gate 1 报告 — 最小垂直切片验证

> **日期**: 2026-07-13  
> **检查者**: 大G（架构师）  
> **前置**: M2-003A Gate 0 PASS (29/29) ✅  
> **结论**: Gate 1 PASS (7/7) ✅  

---

## 执行结果

```bash
python3 scripts/gate1_check.py tests/fixtures/m2_003/expected/ --runs 2
```

```
============================================================
Gate 1 Checker — M2-003B 硬门禁验证
============================================================

--- Run 1/2 ---
  case_a_web: 9 candidates, SHA-256=803be8c34be56b78…, errors=0
  case_b_video: 10 candidates, SHA-256=2a684ecfcd82d6e5…, errors=0
  case_c_pdf: 13 candidates, SHA-256=3ff01d29f39f915a…, errors=0

--- Run 2/2 ---
  case_a_web: 9 candidates, SHA-256=803be8c34be56b78…, errors=0
  case_b_video: 10 candidates, SHA-256=2a684ecfcd82d6e5…, errors=0
  case_c_pdf: 13 candidates, SHA-256=3ff01d29f39f915a…, errors=0

============================================================
Gate Checks
============================================================

G1-1 非法 Unit 引用: ✅ PASS (0 violations)
G1-2 无法定位 Quote: ✅ PASS (0 violations)
G1-3 自动创建 Fact: ✅ PASS (0 violations)
G1-4 读取后修改原对象: ✅ PASS (0 violations)
G1-5 两次运行 SHA-256 一致: ✅ PASS (0 violations)
G1-6 Candidate 排序不漂移: ✅ PASS (0 violations)
G1-7 Candidate 核心字段不漂移: ✅ PASS (0 violations)

============================================================
Gate 1 结果: 7/7 PASS
============================================================
✅ Gate 1 PASS — all 7 hard gates satisfied
```

---

## 交付清单

### 源代码模块

| # | 文件 | 行数 | 说明 |
|---|------|:---:|------|
| 1 | `src/aurora/extraction/__init__.py` | 29 | 包导出 |
| 2 | `src/aurora/extraction/context_window.py` | 115 | ContextWindow + ContentUnitRef 构建 |
| 3 | `src/aurora/extraction/candidates.py` | 88 | Entity/DataPoint/Claim/Evidence/FactCandidate DTO |
| 4 | `src/aurora/extraction/envelope.py` | 82 | ExtractionEnvelope + ProviderMetadata |
| 5 | `src/aurora/extraction/quote_gate.py` | 136 | QuoteGate Unicode 规范化子串匹配 |
| 6 | `src/aurora/extraction/review_bundle.py` | 168 | ReviewBundle 不可变审计包 |
| 7 | `src/aurora/extraction/review_decision.py` | 120 | ReviewDecision 可编辑人工决策 |
| 8 | `src/aurora/extraction/providers/__init__.py` | 6 | Provider 包导出 |
| 9 | `src/aurora/extraction/providers/base.py` | 22 | ExtractionProvider 抽象基类 |
| 10 | `src/aurora/extraction/providers/fixture_provider.py` | 238 | FixtureProvider 确定性提取器 |
| 11 | `src/aurora/cli/extract.py` | 269 | CLI: aurora-extract + aurora-review |

### 测试

| # | 文件 | 用例数 | 说明 |
|---|------|:---:|------|
| 12 | `tests/unit/test_context_window.py` | 14 | 排序稳定性、SHA-256、CU 引用 |
| 13 | `tests/unit/test_fixture_provider.py` | 12 | Case 完整性、候选字段、排序 |
| 14 | `tests/unit/test_quote_gate.py` | 10 | 子串匹配、Unicode 规范化、失败上报 |
| 15 | `tests/unit/test_review_bundle.py` | 9 | 不可变性、SHA-256 计算 |
| 16 | `tests/integration/test_m2_003b_vertical_slice.py` | 13 | 三 Case 完整链路验证 |

### 验证脚本

| # | 文件 | 说明 |
|---|------|------|
| 17 | `scripts/gate1_check.py` | Gate 1 7 项硬门禁自动检查 |

---

## 设计决策

### SHA-256 确定性

ReviewBundle SHA-256 计算**排除 UUID**（review_bundle_id、run_id、candidate_id、unit_id），仅基于数据内容：
- ContextWindow: 仅 hash `(sequence_no, text)` → 同数据同哈希
- ReviewBundle: 仅 hash `(document_id, provider, candidates_data, unit_texts, errors)` → 同数据同哈希

这确保同一提取结果在不同运行时产生相同的 bundle_sha256，满足 G1-5 要求。

### 排序稳定性

- ContextWindow: `sequence_no ASC` 排序，同值时 `unit_id ASC` 打破平局
- FixtureProvider: `(type_order, id)` 排序，类型顺序: Entity < DataPoint < Claim < Evidence < FactCandidate

### Quote Gate 设计

- NFKC Unicode 规范化后子串匹配
- 失败候选 → QuoteGateFailure 记录（静默丢弃 = 0）
- Entity 类候选（无 source_quote）豁免检查

### 不可变性

- ReviewBundle: `@dataclass(frozen=True)`，生成后不可修改
- ContentUnitRef: `@dataclass(frozen=True)`
- ContextWindow: `@dataclass(frozen=True)`
- 人工决策存储于独立 `ReviewDecision`（mutable）

---

## 测试覆盖

```
================= 58 passed in 0.38s =================
   14  test_context_window.py     (排序 / SHA / 引用)
   12  test_fixture_provider.py   (完整性 / 字段 / 排序)
   10  test_quote_gate.py         (匹配 / 规范化 / 失败)
    9  test_review_bundle.py      (不可变 / SHA / 属性)
   13  test_m2_003b_vertical_slice.py (集成 / 三Case)
-------------------------------------------
   58  TOTAL
```

现存测试无回归（150 用例全部通过）。

---

## 下一步：Gate 2

Gate 2 涉及 6 项认知安全门禁（污染测试集），需实现：
- `scripts/gate2_check.py`
- `tests/fixtures/m2_003/adversarial/` 下的 5 个污染测试 JSON
- 6 项硬门禁：Fact 污染率、虚假 Quote 接受率、窗外 Unit 接受率、Prompt Injection 越权率、自生成 independence_group 接受率、高置信度不影响判定

---

_大G · 2026-07-13_ 🏗️
