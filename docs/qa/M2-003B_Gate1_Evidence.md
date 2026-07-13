# M2-003B Gate 1 交付证据清单

> **交付时间**: 2026-07-13
> **分支**: `feature/m2-003b-real-vertical-slice`
> **HEAD**: `d1dc91b4fd561f17d9ffb3440345ac218cb05471`
> **验证人**: 大G (BigG) + 婉儿

---

## 14 项交付证据

### E1: 分支 HEAD
```
分支: feature/m2-003b-real-vertical-slice
HEAD: d1dc91b4fd561f17d9ffb3440345ac218cb05471
Message: M2-003B: Real Vertical Slice + Gate 1 Implementation
```

### E2: 父基线验证
```
f0627d9 — ✅ IS ancestor of HEAD
git merge-base HEAD f0627d9 == f0627d9
Commit msg: "chore: clear 临时文件 after archive"
```

### E3: Gate 0 代码比较基线验证
```
78d8b90 — ✅ merge-base 确认
git merge-base HEAD 78d8b90 == 78d8b904c2ad5...
```

### E4: G1-1 → G1-7 完整通过
| 门禁 | 描述 | 状态 |
|------|------|------|
| G1-1 | 非法 Unit 引用 = 0 | ✅ |
| G1-2 | 无法定位 Quote 的候选 = 0 | ✅ |
| G1-3 | 自动 Fact 创建 = 0 | ✅ |
| G1-4 | 修改 Document/CU = 0 | ✅ |
| G1-5 | 10 次重复运行一致 | ✅ |
| G1-6 | Candidate 排序稳定 (10×3) | ✅ |
| G1-7 | 核心字段稳定 (10×3) | ✅ |

### E5: 30 轮确定性验证
```
模式 1: 10 次相同输入 → 同一 ReviewBundle SHA-256  ✅
模式 2: 10 次随机打乱 provider candidates → 排序一致 ✅
模式 3: 10 次随机打乱 ContentUnits → 核心字段一致  ✅

总计: 30/30 PASS
```

### E6: Hash 防篡改验证
```
✅ ContextWindow: 规范化 JSON → SHA-256 (修改任何 field → hash 变化)
✅ ReviewBundle: 规范化 JSON → SHA-256 (修改 candidate/finding → hash 变化)
✅ bundle_sha256 从 CR 的 JSON 中派生 (排除自身 hash 字段)
```

### E7: pytest 结果
```
345 passed, 0 failed, 0 errors, 0 warnings
执行时间: ~8.6s
Python: 3.11.13
```

### E8: Coverage 结果
```
总覆盖率: 96%

新增模块覆盖率:
  request.py:           100%
  context_window.py:     96%
  candidates.py:        100%
  providers/base.py:     96%
  providers/fixture_provider.py: 95%
  findings.py:           93%
  quote_gate.py:         95%
  review_bundle.py:      96%
  envelope.py:          100%
  __init__.py:          100%

所有新增模块 ≥ 90% ✅
```

### E9: Gate 0 冻结资产 Hash 复核
```
Case A expected:     dee2ed3a… ✅
Case B expected:     b8c78122… ✅
Case C expected:     f2bc095e… ✅
Case A content_units: e952250f… ✅
Case B content_units: caa98f1a… ✅
Case C content_units: bfc48b06… ✅
expected_results.schema.json: 05e9ac03… ✅
gate0_check.py:      5099f94b… ✅

8/8 冻结资产 Hash 一致 ✅
Gate 0 资产在本分支的修改文件: (空) ✅
```

### E10: Schema Diff
```
Core V1.1 Schema (schemas/core/v1*/ schemas/persistence/v1*):
  git diff f0627d9..HEAD → (空输出) ✅
  无任何 schema 文件被修改 ✅
```

### E11: Alembic 版本检查
```
现有 revision: 3
新增 revision: 0 (git diff f0627d9..HEAD -- alembic/ → 空) ✅
```

### E12: 三类数据面独立性
```
A. Source Fixture (tests/fixtures/m2_003/materials/):
   HTML/SRT/VTT/PDF — 纯 Parser 输入，不参与 validation

B. Provider Fixture (tests/fixtures/m2_003/provider_responses/):
   3 个独立 JSON — provider candidate 快照，不依赖 Expected

C. Expected Results (tests/fixtures/m2_003/expected/):
   3 个 JSON — 仅用于断言，不参与 ContextWindow 或 Provider 构造

三者互不生成、互不推导 ✅
```

### E13: 范围守门
```
无 persist_drafts      ✅
无 apply_review         ✅
无 Fact 持久化           ✅
无 远程 Provider        ✅
无 实体合并              ✅
```

### E14: Gate 0 独立复核
```
Gate 0 V1.2 checker (final mode):
  3/3 案例
  11/11 gates per case
  35/35 total gates
  跨案例独立性: ✅
  跨案例 G07: ✅
  overall_pass: ✅
  preliminary_pass: ✅
  semantic_pass: ✅
  final_gate_pass: ✅
```

---

## 判定

**Gate 1: PASS** ✅
**14/14 证据齐全** ✅
**Gate 0 复核: PASS** ✅

---

_大G (BigG) + 婉儿 | 2026-07-13_
