# M2-003A：黄金集与设计假设验证 Issue

> **基于：** `M2-003 阶段验证与质量门禁计划 V1.1`  
> **状态：** READY  
> **前置条件：** M2-002 CLOSED，验证计划 APPROVED  
> **目标：** 在编码前用人工标注验证设计假设

---

## 1. 目标

1. 用 Case A/B/C 的三份人工标注期望结果，验证提取设计是否能表达真实的网页/视频/年报内容
2. 建立 Gate 0 的 7 条硬门禁基线
3. 通过 Gate 0 后，才进入 M2-003B（FixtureProvider + Context Window + ReviewBundle）

---

## 2. 输入材料

| Case | 材料 | 路径 | SHA-256 |
|------|------|------|---------|
| A | 中芯国际官网网页 | `tests/fixtures/m2_002/case_a_web.html` | `c5b1d...59afaa` |
| B | 视频转写 | `tests/fixtures/m2_002/case_b_video.srt` | `0d189...ca360` |
| C | 年报 PDF | `tests/fixtures/m2_002/case_c_report.pdf` | `78de3...d2d777` |

---

## 3. 交付清单

### 必须交付

| # | 产物 | 路径 |
|---|------|------|
| 1 | Case A 人工期望结果 | `tests/fixtures/m2_003/expected/case_a_web_expected.json` |
| 2 | Case B 人工期望结果 | `tests/fixtures/m2_003/expected/case_b_video_expected.json` |
| 3 | Case C 人工期望结果 | `tests/fixtures/m2_003/expected/case_c_pdf_expected.json` |
| 4 | Expected Results JSON Schema | `schemas/ingestion/v1_1/expected_results.schema.json` |
| 5 | Gate 0 自动检查器 | `scripts/gate0_check.py` |
| 6 | Gate 0 报告模板 | `docs/qa/M2-003A_Gate0_报告.md` |
| 7 | 污染测试集目录骨架 | `tests/fixtures/m2_003/adversarial/README.md` |
| 8 | 评价指标定义文档 | `docs/qa/M2-003_评价指标定义_V1.0.md` |

### 标注与复核责任

| 角色 | 职责 |
|------|------|
| 婉儿 | 初稿标注（已完成 ✅） |
| 大G | 独立复核 + 标记 disagreements |
| 大黄 | 争议裁断 |

### 非目标

本 Issue 不实现：

- FixtureProvider
- Context Window
- ReviewBundle 运行链
- 远程 Provider
- Draft 持久化
- Fact 晋级

---

## 4. Gate 0 验收标准

| 编号 | 门禁 | 判定 |
|------|------|:---:|
| G0-1 | 三个案例的 18 个顶层 key 全部存在 | ✅ |
| G0-2 | validation_report.core_schema_change_needed = false | ✅ |
| G0-3 | 无无法解释的候选状态（所有 Claim 有 type+dimension，所有 DataPoint 有 measurement_context） | ✅ |
| G0-4 | validation_report.new_core_object_needed = false | ✅ |
| G0-5 | 每条 Claim 和 DataPoint 均可定位原文 Quote（有 source_quote + quote_locator_hint） | ✅ |
| G0-6 | MeasurementContext 覆盖全部 DataPoint（measurement_kind 非空） | ✅ |
| G0-7 | ReviewBundle 支持 APPROVE / REJECT / REVISE_AND_APPROVE 三类决策 | ✅ |

**运行方式：**

```bash
python3 scripts/gate0_check.py tests/fixtures/m2_003/expected/
```

---

## 5. 案例摘要

### Case A — 中芯国际官网业绩摘要（网页）

| 提取类别 | 数量 | 关键点 |
|----------|:---:|------|
| Entity | 1 | 中芯国际 |
| DataPoint | 2 | 营业收入 673.23 亿 (monetary) + 产能利用率 93.5% (percentage) |
| Claim | 4 | fact_claim×3 (business_growth/operations) + 代码片段标识 |
| Evidence | 2 | 同一 independence_group `smics_official`，独立计数=1 |
| FactCandidate | 1 | 营收数据可晋级 |
| 边缘情况 | — | `<pre><code>` 块需与真实声明区分 |

### Case B — 视频转写（SRT），UP 主分析

| 提取类别 | 数量 | 关键点 |
|----------|:---:|------|
| Entity | 4 | 中芯国际、联电、格芯、台积电 |
| Claim | 4 | fact_claim (market_expectation/competition) + risk_claim (competition) + value_judgment (valuation) |
| Cue 重叠 | — | cue 2/3 有 300ms 重叠 |
| 复合句 | — | cue 1 应拆分为两条独立 Claim |
| FactCandidate | 2 | claim_b_003 可晋级 (fact_claim)，claim_b_004 不可晋级 (value_judgment) |

### Case C — 中芯国际年报（PDF）

| 提取类别 | 数量 | 关键点 |
|----------|:---:|------|
| DataPoint | 4 | 营收 2025/2024 + 产能利用率 2025/2024（两年对比） |
| Claim | 2 | fact_claim×1 (financial_performance) + prediction×1 (business_growth) |
| Evidence | 4 | 同一 independence_group `smics_annual_report` |
| **G4-1 靶子** | — | 管理层 prediction "营收增长将高于行业平均" **不可晋级 Fact** |
| 单位转换 | — | 原文 "bn" → 需 scale_multiplier=100000000 |

---

## 6. 验收检查单

- [ ] 三份 expected_results.json 通过 JSON Schema 校验
- [ ] `python3 scripts/gate0_check.py` 返回 overall_pass=true
- [ ] 20/20 门禁通过（3×7=21，经核定）
- [ ] Case A `claim_a_004`（代码片段）标注被复核人确认
- [ ] Case B `claim_b_002`（risk_claim+competition 维度）标注被复核人确认
- [ ] Case C `claim_c_002`（prediction 不可晋级 Fact）标注被复核人确认
- [ ] 大G disagreements 为空或已裁断
- [ ] `annotated_by`、`reviewed_by`、`adjudication_note` 已填写

---

## 7. 启动条件确认

- [x] M2-002 CLOSED
- [x] 验证计划 APPROVED（V1.1）
- [x] 三份期望结果初稿已完成（婉儿）
- [ ] 大G 复核完成
- [ ] Gate 0 通过后启动 M2-003B
