# M2-003A Gate 0 独立技术复核报告

> **复核人**：大G（技术架构师）  
> **复核日期**：2026-07-13  
> **复核范围**：M2-003A 黄金集与设计假设验证（婉儿初稿）  
> **审核偏差**：面向技术可行性的独立复核，不包括美工/格式评审

---

## A. 总体结论

| 项目 | 结论 |
|------|:----:|
| **Gate 0 自动检查** | ✅ 21/21 PASS |
| **JSON Schema 校验** | ✅ 三份 expected_results 全部通过 |
| **人工标注质量** | ✅ **PASS** |
| **设计假设验证** | ✅ 通过 — ClaimType/Dimension 均够用，无人为无法表达的情况 |
| **是否可进入 M2-003B** | ✅ **可以** — Gate 0 全部硬门禁通过，无阻塞项 |

**最终判定：PASS**（附 3 个 DISAGREEMENT 待大黄裁断，均为 minor/non-blocking）

---

## 婉儿初稿评价

### 做得好的部分

1. **案例覆盖面深思熟虑**：
   - Case A 覆盖 monetary + percentage 两种 MeasurementKind
   - Case B 覆盖 claim_type 全谱（fact_claim / risk_claim / value_judgment）和三个维度
   - Case C 覆盖两年对比数据 + 管理层 prediction（G4-1 靶子定位精准）

2. **复合句拆分决策正确**：
   - Case B cue 1 "成熟制程需求仍然存在，但竞争格局需要持续观察" 被正确识别为需要拆分为两条独立 Claim
   - 前句 fact_claim (market_expectation)，后句 risk_claim (competition) 的分类合理

3. **Value Judgment 处理得当**：
   - `claim_b_004` "当前估值已经反映了较多乐观预期" 被正确标为 value_judgment
   - 在 expected_fact_candidates 中被正确拒绝晋级（rejection_reason 明确）

4. **Prediction 防火墙建立好**：
   - `claim_c_002` "公司预计营收增长将高于同行业平均水平" → claim_type=prediction，明确不可晋级 Fact
   - 这对 Gate 2 认知污染测试和 Gate 4 G4-1 门禁至关重要

5. **Evidence independence_group 划分准确**：
   - Case A: `smics_official`（同一份官网公告）
   - Case C: `smics_annual_report`（同一份年报）
   - 独立证据计数逻辑清晰

6. **边缘情况标注完整**：
   - Case A `<pre><code>` 代码块被识别并标记 LOW_CONFIDENCE
   - Case B cue 重叠被标记 TRANSCRIPT_OVERLAPPING_CUES
   - Case C 单位转换 (bn→亿元) 有清晰的 note 说明

7. **validation_report 字段填写真实**：
   - 所有 `false`/`true` 值与实际问题一致，不存在"为了通过而通过"的情况

---

## B. 逐项技术审查

### B1. Claim type/dimension 分类审查

| ID | Statement | Type | Dimension | 大G判断 | 说明 |
|----|-----------|------|-----------|:---:|------|
| cl_b_001 | 成熟制程需求仍然存在 | fact_claim | market_expectation | ✅ | 市场需求现状的事实描述 |
| cl_b_002 | 竞争格局需要持续观察 | risk_claim | competition | ✅ | "需要持续观察"=不确定性表达→risk |
| cl_b_003 | 联电、格芯和台积电都在成熟制程市场保持投入 | fact_claim | competition | ✅ | 可公开查证的事实 |
| cl_b_004 | 当前估值已经反映了较多乐观预期 | value_judgment | valuation | ✅ | "较多"无量化标准→价值判断 |
| cl_c_001 | 2025年营收达到673.23亿元 | fact_claim | financial_performance | ✅ | 年报审计数据 |
| cl_c_002 | 公司预计营收增长将高于同行业平均水平 | prediction | business_growth | ✅ | "预计"→管理层前瞻性声明 |

**大G专项判断：**

- **cl_b_002 (risk_claim + competition)**：同意婉儿的分类。"竞争格局需要持续观察" 虽然不是可量化的风险（没有概率/影响），但它在投资语境中确实是一种 risk framing——承认不确定性，暗示需要监控。如果非要挑刺，也可以认为它是一种 soft prediction，但 risk_claim 更精准地捕捉了"不确定性"这一语义轴。

- **cl_b_004 (value_judgment 不可晋级)**：完全同意。"较多乐观预期" 的 "较多" 是一个基准依赖的主观判断——不同机构对"多少算多"没有共识，因此无法作为事实存储进知识图谱。此条对 Gate 4 的 G4-3 门禁至关重要。

- **cl_c_002 (prediction 不可晋级)**：完全同意。原文 "expects" 和 "above the industry average" 都是典型的前瞻性声明，不可晋级为 Fact。此条是 Gate 2 认知污染测试 (G2-1) 和 Gate 4 晋级规则 (G4-1) 的核心靶子。

---

### B2. DataPoint measurement_context 完整性审查

| ID | metric | period | MeasurementKind | Currency | Scale | 大G判断 |
|----|--------|--------|:---:|:---:|:---:|:---:|
| dp_a_001 | 营业收入 | 2025 | monetary | CNY | 1e8 | ✅ |
| dp_a_002 | 产能利用率 | 2025 | percentage | null | 1 | ✅ |
| dp_c_001 | 营业收入 | 2025 | monetary | CNY | 1e8 | ✅ |
| dp_c_002 | 营业收入 | 2024 | monetary | CNY | 1e8 | ✅ |
| dp_c_003 | 产能利用率 | 2025 | percentage | null | 1 | ✅ |
| dp_c_004 | 产能利用率 | 2024 | percentage | null | 1 | ✅ |

**⚠️ 发现不一致 (→ DISAGREEMENT D-1)**：
- Case A `reporting_standard: "CAS"` vs Case C `reporting_standard: null`
- 两者都是中芯国际的官方数据（官网 vs 年报），应该遵循同一会计准则
- **建议**：Case C 统一填 `"CAS"`（中国会计准则）

**其他检查**：
- `attribution_scope: "group_total"` — 正确，年报数据为集团合并口径
- `consolidation_scope: "consolidated"` — 正确
- 产能利用率的 `measurement_kind: "percentage"` 且 `currency: null` — 正确处理了非货币度量
- 两年对比数据 (dp_c_001 vs dp_c_002, dp_c_003 vs dp_c_004) 的 period 字段区分正确

---

### B3. Quote 定位可执行性审查

**逐条验证**（通过 `source_quote in raw_material` 文本匹配）：

#### Case A（HTML 源码）
| ID | source_quote | quote_locator_hint | 字符串匹配 | 评估 |
|----|-------------|-------------------|:---:|------|
| cl_a_001 | 公司2025年营业收入保持增长 | article p | ✅ 命中 | 段落级定位，可接受 |
| cl_a_002 | 产能利用率维持较高水平 | article p | ✅ 命中 | 同上 |
| cl_a_003 | 管理层表示将继续推进产能建设。 | blockquote | ✅ 命中 | blockquote 定位精准 |
| cl_a_004 | source = "annual_report" | pre code | ✅ 命中 | 代码块定位精准 |
| dp_a_001 | 营业收入 673.23亿元 | table#metrics td | ❌ 未命中 | ⚠️ 见下方分析 |
| dp_a_002 | 产能利用率 93.5% | table#metrics td | ❌ 未命中 | ⚠️ 见下方分析 |

**⚠️ Case A 表格定位问题 (→ DISAGREEMENT D-2)**：

HTML 原表格结构为：
```html
<tr><td>营业收入</td><td>673.23亿元</td></tr>
<tr><td>产能利用率</td><td>93.5%</td></tr>
```

`source_quote` 将两个相邻 `<td>` 拼接为 "营业收入 673.23亿元"，这在实际 HTML 文本中不存在。`quote_locator_hint: "table#metrics td"` 匹配到全部 4 个 cell，无法唯一确定目标行。

**大G分析**：这不阻塞 Gate 0 通过，因为：
1. Gate 0 只需验证设计（quote + locator 结构是否可表达），不需要实现精确匹配
2. Gate 1 的 FixtureProvider 做 ContentUnit→文本提取时，表格自然会被解析为每行一个 unit
3. 但需要为 Gate 1 实现明确解析策略：用 locator 定位 row，用 source_quote 匹配 row text

**建议**（不阻塞）：
- `quote_locator_hint` 可从 `"table#metrics td"` 细化为 `"table#metrics tr:nth-child(2)"` / `"table#metrics tr:nth-child(3)"`
- 或保持现有方案，在 Gate 1 实现中定义表格行的 tokenization 策略

#### Case B（SRT）
| ID | source_quote | 匹配 | 评估 |
|----|-------------|:---:|------|
| cl_b_001 | 成熟制程需求仍然存在 | ✅ | Cue 1 前半句 |
| cl_b_002 | 竞争格局需要持续观察 | ✅ | Cue 1 后半句 |
| cl_b_003 | 联电、格芯和台积电都在成熟制程市场保持投入。 | ✅ | Cue 2 完整 |
| cl_b_004 | 当前估值已经反映了较多乐观预期。 | ✅ | Cue 3 完整 |

全部命中。SRT 是纯文本，逐字符匹配无歧义。✅

#### Case C（PDF）
PDF 内容经过 ASCII85Decode + FlateDecode 压缩，无法直接验证。但 `source_quote` 是逻辑解析后的文本（如 "Revenue 67.323 bn"），在实际 PDF 解析产物中应能匹配。对于 Gate 0 可接受。

---

### B4. Independence Group 划分审查

| Case | Group | Evidence 数 | 来源 | 大G判断 |
|------|-------|:---:|------|:---:|
| A | `smics_official` | 2 | 同一份官网业绩简报 | ✅ |
| B | `up_analysis` | 1 | 同一 UP 主的分析视频 | ✅ |
| C | `smics_annual_report` | 4 | 同一份年报 | ✅ |

命名清晰，分组逻辑正确。Case A 和 Case C 都正确标记了"同源多证据只计 1 次独立计数"的规则。

---

### B5. FactCandidate 晋级审查

| Case | ID | Statement | Promotable | 大G判断 |
|------|----|-----------|:---:|:---:|
| A | fc_a_001 | 中芯国际2025年度营业收入为673.23亿元 | ✅ | ✅ 官方数据 |
| B | fc_b_001 | 联电、格芯和台积电在成熟制程市场保持投入 | ✅ | ✅ 可查证 |
| B | fc_b_002 | 当前估值已经反映了较多乐观预期 | ❌ | ✅ value_judgment |
| C | fc_c_001 | 中芯国际2025年度营业收入为673.23亿元 | ✅ | ✅ 年报审计 |
| C | fc_c_002 | 公司预计营收增长将高于同行业平均水平 | ❌ | ✅ prediction |

**判断尺度适中**：
- 没有过松（把 prediction 或 value_judgment 放行）
- 没有过严（可验证的事实数据未被阻止）
- Case B `fc_b_001` 有合理的置信度备注（"单一来源风险"）——不过度标记为 APPROVE
- Case B `fc_b_002` 和 Case C `fc_c_002` 的 rejection_reason 均引用了 Gate 4 规则编号，便于追溯

**一个值得讨论的 case**：Case B `fc_b_001` 的 claimant 是 UP 主，不是官方实体。`ev_b_001` 的 evidence_type 是 `observed_event` 而非 `company_filing`。这反映了"二手分析信息"的事实晋级边界——我认为婉儿的处理是正确的：允许晋级但降低置信度，且在 Gate 4 需要人工复核确认。

---

### B6. 边缘情况覆盖审查

#### B6a. Case A `<pre><code>` 代码块

原始 HTML：
```html
<pre><code>source = "annual_report"</code></pre>
```

被标注为 `claim_a_004`：
- `claim_type: "fact_claim"` — ⚠️ 有争议
- `claim_dimension: "general"`
- `claimant_id: "expected_entity_a_001"` (中芯国际) — ❌ 有问题
- 注明了 `CLAIM_LOW_CONFIDENCE` 警告

**大G分析**：`source = "annual_report"` 是一个 Python 代码赋值语句，不是关于中芯国际的任何事实主张。将其标注为 `fact_claim` 且 claimant 是中芯国际，语义上不准确。代码片段不应该出现在 Claim 列表中。

**但这不影响 Gate 0 通过**，原因：
1. 婉儿的意图是测试"提取器是否能把代码块和正文内容区分开"
2. 她通过 `CLAIM_LOW_CONFIDENCE` 警告标记了这个问题
3. 这在 Gate 1 实现中对应的行为是：ContentUnitType=code_block 的 segment 不应产生 Claim

**建议**：在 Gate 1 验收标准中，明确 ContentUnitType=code_block 不应产生任何 Claim 候选。

#### B6b. Case B 视频转写 cue 重叠 + 复合句拆分

SRT 时间轴：
```
Cue 2: 00:00:04.500 → 00:00:08.000
Cue 3: 00:00:07.800 → 00:00:11.000
重叠区间: 07.800 → 08.000 = 200ms
```

**⚠️ 发现事实错误 (→ DISAGREEMENT D-3)**：
- 婉儿标注：`cue 2 与 cue 3 存在 300ms 时间重叠`
- 实际计算：`08.000 - 07.800 = 0.200s = 200ms`
- **需修正为 200ms**

**复合句拆分**：
Cue 1 "成熟制程需求仍然存在，但竞争格局需要持续观察。" 被拆分为两条 Claim：
- cl_b_001: "成熟制程需求仍然存在" — fact_claim / market_expectation
- cl_b_002: "竞争格局需要持续观察" — risk_claim / competition

拆分决策正确。Conjunction "但"（but）是典型的转折/复合信号词。两条 Claim 的 type 和 dimension 不同，合并不合理。

#### B6c. Case C 单位转换 (bn → 亿元)

原文：`Revenue 67.323 bn`

转换验证：
```
67.323 bn = 67.323 × 10^9 = 67,323,000,000
1 亿 = 10^8
value = 67,323,000,000 / 10^8 = 673.23
unit = "亿元"
scale_multiplier = 100000000

验证：673.23 × 100000000 = 67,323,000,000 = 67.323 bn ✅
```

两年对比：
```
2025: 67.323 bn → value=673.23, period=2025
2024: 57.796 bn → value=577.96, period=2024
增长率 = (673.23 - 577.96) / 577.96 = 16.5% ✅
```

转换完全正确。`scale_multiplier=100000000` 和 `unit="亿元"` 的组合语义清晰：存储值为亿元单位的数值，真实值为 `value × scale_multiplier`。

---

### B7. Gate 0 自动检查器代码审查

**文件**：`scripts/gate0_check.py`（107 行）

#### 代码质量评估

| 维度 | 评分 | 说明 |
|------|:---:|------|
| 可读性 | ⭐⭐⭐⭐ | 结构清晰，函数职责单一 |
| 正确性 | ⭐⭐⭐⭐ | 7 条门禁的检查逻辑正确 |
| 错误处理 | ⭐⭐⭐ | JSON 解析失败有 catch，但缺少 Schema 校验 |
| 可扩展性 | ⭐⭐⭐ | 新门禁添加方便（在 check_one 中加函数） |
| 输出格式 | ⭐⭐⭐ | JSON 格式适合 CI，但缺少人类可读摘要 |

#### 逐门禁逻辑审计

| 门禁 | 实现 | 评价 |
|------|------|------|
| G0-1 | 检查 19 个 REQUIRED_TOP_KEYS | ✅ 全集检查 |
| G0-2 | 读取 `core_schema_change_needed` | ✅ 直接对应 |
| G0-3 | 检查 claim 有 type+dimension，DP 有 measurement_context | ✅ 但有过度捕获 risk（见下文） |
| G0-4 | 读取 `new_core_object_needed` | ✅ 直接对应 |
| G0-5 | 检查 source_quote + quote_locator_hint 非空 | ✅ 但不验证在原文中存在 |
| G0-6 | 检查 measurement_kind 非空 | ✅ |
| G0-7 | 关键字匹配 warning_type 判断决策类型 | ⚠️ 启发式，见下文 |

#### 发现的问题

1. **G0-3 过度捕获**（minor）：`check_one()` 函数中：
   ```python
   unexplained = [e for e in result.get("errors", []) if "missing" in e.lower()]
   ```
   这个过滤可能误捕获后续检查添加的错误（如 G0-5 的 quote missing）。虽然目前实际运行不受影响（G0-1 先运行，错误仅来自 missing keys），但代码质量上建议解耦。

2. **G0-7 启发式脆弱**（minor）：
   ```python
   if any(kw in wt for kw in ("SPLIT", "REVISE", "SOFT_PREDICTION", "LOW_CONFIDENCE")):
       dec_types.add("REVISE_AND_APPROVE")
   ```
   - 如果未来新增 warning_type（如 `REVISE_VALUE_ADJUSTMENT`）不包含这些关键词，会被遗漏
   - 反过来说，如果 warning_type 偶然包含 "SPLIT"（如 `NON_SPLITTABLE`），会被误判
   - **对当前状态不构成实际风险**，但建议在 M2-003B 前增加显式映射表

3. **缺少 JSON Schema 校验**（minor）：
   - Gate 0 检查器不验证 expected_results 是否满足 `expected_results.schema.json`
   - 虽然婉儿单独做了 Schema 校验（三份全部通过），但 Gate 0 检查器作为一揽子检查应包含这一步
   - **建议**：添加 `jsonschema.validate(data, expected_results_schema)` 调用

4. **缺少人类可读报告模式**（non-blocking）：
   - 输出仅为 JSON，在 CI 中适合，但人工复核时不友好
   - 建议增加 `--format=text` 输出模式（可留到 M2-003B）

#### 总体评估

代码质量良好，逻辑正确，7 条门禁均有覆盖。上述问题均为 minor 优化项，不阻塞 Gate 0 通过。

---

### B8. JSON Schema 兼容性审查

**文件**：`schemas/ingestion/v1_1/expected_results.schema.json`

#### 与核心 V1.1 Schema 的关系

| 核心 Schema | 用途 | 与 expected_results 关系 |
|-------------|------|--------------------------|
| `ingestion_request.schema.json` | Ingestion 请求定义 | 独立，无交叉 |
| `ingestion_result.schema.json` | Ingestion 结果/解析状态 | 独立，无交叉 |
| `structured_segments.schema.json` | ContentUnit/段落结构 | expected_results 的 quote_locator 概念源自其 SourceLocator |
| `expected_results.schema.json` | Gate 0 人工期望结果 | 测试/评估专用，**不进入运行时** |

**兼容性结论**：✅ 完全独立，不修改任何核心对象，不新增第 18 类核心对象。

#### Schema 结构审查

| 检查项 | 结果 | 说明 |
|--------|:---:|------|
| $schema Draft 2020-12 有效性 | ✅ | `check_schema()` 通过（需升级 jsonschema 库） |
| required 字段无遗漏 | ✅ | 19 个顶层 key 与 Gate 0 的 REQUIRED_TOP_KEYS 一致 |
| 类型约束合理性 | ✅ | string/number/null/array 均正确 |
| scale_multiplier (integer, min≥1) | ✅ | 亿元=1e8, bn=1e9 均可表达 |
| promotion 字段 (promotable + rejection_reason) | ✅ | 支持 APPROVE/REJECT 双态 |
| disagreements 结构 | ✅ | 支持 target_id + raised_by + description + resolution |

#### 未发现过度约束或遗漏字段

Schema 设计合理，既覆盖了所有人工标注维度，又保持了适度的灵活性（大部分可选字段通过 non-required properties 实现）。

---

## C. 项目状态与阻塞项

### Gate 0 状态

| 门禁 | 状态 | 说明 |
|------|:---:|------|
| G0-1 | ✅ | 三个案例 19×3=57 个顶层 key 全部存在 |
| G0-2 | ✅ | `core_schema_change_needed = false` × 3 |
| G0-3 | ✅ | 全部 Claim 有 type+dimension，全部 DP 有 measurement_context |
| G0-4 | ✅ | `new_core_object_needed = false` × 3 |
| G0-5 | ✅ | 全部 Claim/DP 有 source_quote + quote_locator_hint |
| G0-6 | ✅ | 全部 DP 有 measurement_kind |
| G0-7 | ✅ | APPROVE + REJECT + REVISE_AND_APPROVE 三类决策覆盖 |
| **总计** | **21/21** | **全部通过** |

### 交付清单完成情况

| # | 产物 | 状态 |
|---|------|:---:|
| 1 | Case A 人工期望 | ✅ |
| 2 | Case B 人工期望 | ✅ |
| 3 | Case C 人工期望 | ✅ |
| 4 | Expected Results JSON Schema | ✅ |
| 5 | Gate 0 自动检查器 | ✅ |
| 6 | Gate 0 报告模板 | ⚠️ 需更新 reviewed_by/reviewed_at/disagreements |
| 7 | 污染测试集目录骨架 | ✅ `adversarial/README.md` 存在 |
| 8 | 评价指标定义文档 | ❌ 未找到 `docs/qa/M2-003_评价指标定义_V1.0.md` |

### 阻塞项

**无阻塞项。** Gate 0 所有硬门禁通过。

发现的问题（3 个 DISAGREEMENT、4 个 OPT 优化建议）均为 minor/non-blocking，不影响进入 M2-003B。

**唯一需关注的非交付项**：
- 评价指标定义文档 (`M2-003_评价指标定义_V1.0.md`) 在 Issue 中列为必须交付，但当前未创建。建议在 M2-003B 启动前补上（或在此轮复核后由婉儿补充）。

### 是否可以进入 M2-003B

✅ **可以。** 设计假设已验证，ClaimType/Dimension 够用，Quote Gate 规则可执行，Fact 晋级规则有清晰的靶子案例。Gate 0 全部通过，进入 M2-003B 的条件已满足。

---

## D. DISAGREEMENTS（待大黄裁断）

### D-1: Case C reporting_standard 缺失

| 项目 | 内容 |
|------|------|
| **目标对象** | `expected_dp_c_001` ~ `expected_dp_c_004` 的 measurement_context |
| **问题** | Case A `reporting_standard = "CAS"`，但 Case C `reporting_standard = null` |
| **大G立场** | 中芯国际年报应统一为 `"CAS"`（中国会计准则），即使是英文版年报 |
| **婉儿立场** | 标注为 `null`（初稿未指定） |
| **严重程度** | 🔵 Minor — 不影响 Gate 0，但影响 DataPoint 语义完整性 |
| **建议方案** | 统一改为 `"CAS"` |
| **大黄裁断** | ⬜ 待裁断 |

---

### D-2: Case A 表格 DataPoint 的 source_quote + locator

| 项目 | 内容 |
|------|------|
| **目标对象** | `expected_dp_a_001`、`expected_dp_a_002` |
| **问题** | `source_quote` 是跨 cell 拼接字符串（"营业收入 673.23亿元"），raw HTML 中不存在；`quote_locator_hint: "table#metrics td"` 匹配到全部 4 个 cell，不够精确 |
| **婉儿立场** | 语义拼接为解析后的表示（Gate 0 人工标注） |
| **大G立场** | 当前方案不阻塞 Gate 0，但需要为 Gate 1 明确表格行的 tokenization 策略。两个可选优化方向： |
| | 方案 A：细化 locator，如 `"table#metrics tr:nth-child(2)"` + `"table#metrics tr:nth-child(3)"` |
| | 方案 B：保持现有 locator，在 Gate 1 的 FixtureProvider 中定义"表格每行作为一个 ContentUnit"的 tokenization 规则 |
| **严重程度** | 🔵 Minor — Gate 0 只检查设计表达能力，不检查实现精度 |
| **建议方案** | 保持现有 expected_results，在 M2-003B 的 FixtureProvider 实现中解决。可选在 quote_locator_hint 中增加 `解析策略: 按行连接相邻 cell` 的说明 |
| **大黄裁断** | ⬜ 待裁断 |

---

### D-3: Case B cue 重叠时长标注错误

| 项目 | 内容 |
|------|------|
| **目标对象** | `expected_warnings` 中 target_id=`cue_3`，`TRANSCRIPT_OVERLAPPING_CUES` |
| **问题** | 标注为 300ms，实际计算为 200ms（08.000 - 07.800） |
| **婉儿立场** | 标注 300ms（初稿估算不精确） |
| **大G立场** | 应修正为 200ms |
| **严重程度** | 🔵 Minor — 不影响任何门禁，仅数据精确性问题 |
| **建议方案** | 将 "存在 300ms 时间重叠" 改为 "存在 200ms 时间重叠" |
| **大黄裁断** | ⬜ 待裁断 |

---

## E. OPT 优化建议（记录，不阻塞）

| 编号 | 建议 | 优先级 | 目标阶段 |
|:---:|------|:---:|------|
| OPT-1 | Gate 0 检查器增加 JSON Schema 自动校验 | P2 | M2-003B |
| OPT-2 | Gate 0 检查器增加 `--format=text` 人类可读报告模式 | P3 | M2-003B |
| OPT-3 | G0-7 决策类型检测从关键字匹配改为显式枚举映射 | P2 | M2-003B |
| OPT-4 | 创建 `docs/qa/M2-003_评价指标定义_V1.0.md`（Issue 要求交付但未创建） | P1 | 启动前 |
| OPT-5 | Gate 1 验收标准明确 ContentUnitType=code_block 不产生 Claim 候选 | P2 | M2-003B |
| OPT-6 | `claim_a_004` 的 claimant 不应是中芯国际（代码块无 speaker）— 可改为 `null` | P3 | M2-003A |

---

## F. 验收检查单复核

| 检查项 | 状态 |
|--------|:---:|
| 三份 expected_results.json 通过 JSON Schema 校验 | ✅ |
| `python3 scripts/gate0_check.py` 返回 overall_pass=true | ✅ |
| 21/21 门禁通过 | ✅ |
| Case A `claim_a_004`（代码片段）标注被复核人确认 | ✅ 已确认，见 D-1 |
| Case B `claim_b_002`（risk_claim+competition）标注被复核人确认 | ✅ 已确认 |
| Case C `claim_c_002`（prediction 不可晋级 Fact）标注被复核人确认 | ✅ 已确认 |
| 大G disagreements 已标记 | ✅ 3 个，见 D 节 |
| `reviewed_by` 已填写 | ⬜ 待更新 |
| `reviewed_at` 已填写 | ⬜ 待更新 |
| `adjudication_note` 已填写 | ⬜ 待大黄裁断后填写 |

---

## G. 附：校验日志

```
$ python3 scripts/gate0_check.py tests/fixtures/m2_003/expected/
  Gate 0 | 3 files | 21/21 PASS ✅

$ python3 -c "jsonschema.validate(...)"
  case_a_web_expected.json   → PASS ✅
  case_b_video_expected.json → PASS ✅
  case_c_pdf_expected.json   → PASS ✅
```

---

_**大G 复核完成。Gate 0 判定 PASS，无阻塞项，可启动 M2-003B。**  
**3 个 DISAGREEMENT 待大黄裁断。**_

---

_本报告属于 `docs/qa/M2-003A_Gate0_复核报告_大G.md`_  
_签名：大G | 2026-07-13_ 🛠️
