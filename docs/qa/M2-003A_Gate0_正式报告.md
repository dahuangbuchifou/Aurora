# M2-003A Gate 0 正式报告

> **状态**: FINAL_PASS ✅  
> **报告日期**: 2026-07-13  
> **Checker**: V1.1 (29/29)

---

## 裁决汇总

| 编号 | 案例 | 问题 | 严重度 | 最终裁决 |
|------|------|------|:---:|------|
| D-001 | A | 代码片段在 expected_claims | BLOCKER | ✅ 移入 expected_rejects |
| D-002 | A | 管理层意图 claim_type | MAJOR | ✅ 大黄裁决：prediction（方案A） |
| D-003 | A/C | independence_group 不一致 | BLOCKER | ✅ 统一为 smics_annual_report_2025 |
| D-004 | B | 中芯国际实体无原文依据 | BLOCKER | ✅ 删除 |
| D-005 | B | UP主观点循环自证 | BLOCKER | ✅ evidence 改 direct_quote/attribution，FC promotable=false |
| D-006 | C | 16.5%无原文依据 | BLOCKER | ✅ 删除，statement 仅保留绝对值 |
| D-007 | C | Prediction 缺 time_horizon | BLOCKER | ✅ 新增 precision=unknown |
| D-008 | Schema | Schema 过于宽松 | MAJOR | ✅ V1.1 严格化：enums, additionalProperties, 条件约束 |
| D-009 | Arch | 命名空间错配 | MINOR | ✅ 迁移到 schemas/extraction/v1/ |
| D-010 | Checker | 弱结构检查≠语义验证 | BLOCKER | ✅ V1.1 重写，16项语义规则 |

---

## Gate 0 门禁结果

```
Gate 0 V1.1 FINAL: PASS ✅
29/29 gates passed

Case A (case_a_web):     9/9 ✅
Case B (case_b_video):    9/9 ✅
Case C (case_c_pdf):      9/9 ✅
Cross-case independence:  PASS ✅
Cross-case G0-7:          PASS ✅
```

### 每案例门禁明细

| Gate | Case A | Case B | Case C |
|------|:---:|:---:|:---:|
| JSON Schema V1.1 | ✅ | ✅ | ✅ |
| SHA-256 | ✅ | ✅ | ✅ |
| Enums | ✅ | ✅ | ✅ |
| ID Uniqueness | ✅ | ✅ | ✅ |
| References | ✅ | ✅ | ✅ |
| FactCandidate Rules | ✅ | ✅ | ✅ |
| Prediction Rules | ✅ | ✅ | ✅ |
| Reviewer Metadata | ✅ | ✅ | ✅ |
| Disagreements Resolved | ✅ | ✅ | ✅ |

---

## 案例覆盖统计

| | Case A(网页) | Case B(视频) | Case C(PDF) |
|---|---|---|---|
| Entity | 1 | 3 | 1 |
| DataPoint | 2 | 0 | 4 |
| Claim | 3 | 4 | 2 |
| claim_type | fact_claim×2, prediction×1 | fact_claim×2, risk_claim×1, value_judgment×1 | fact_claim×1, prediction×1 |
| claim_dimension | business_growth, operations | market_expectation, competition, valuation | financial_performance, business_growth |
| Evidence | 2(support) | 1(attribution) | 4(3 support, 1 context) |
| FactCandidate | 1 promotable | 2 non-promotable | 1 promotable + 1 non-promotable |
| Reject | 1(code block) | 0 | 0 |
| Warning | 1 | 2 | 1 |

---

## 关键设计验证

| 验证项 | 结果 |
|--------|:---:|
| ClaimType 枚举覆盖 | ✅ fact_claim/prediction/risk_claim/value_judgment 全部用到 |
| ClaimDimension 枚举覆盖 | ✅ 5个维度有实际案例 |
| Quote Gate 可执行 | ✅ 所有Claim/DataPoint有source_quote+locator_hint |
| MeasurementContext 完整 | ✅ monetary/percentage，CAS，scale_multiplier |
| Fact 晋级规则 | ✅ prediction/value_judgment 不可晋级，需要独立证据 |
| EvidenceRole 区分 | ✅ support/context/attribution 各自场景 |
| ReviewBundle 可审核 | ✅ APPROVE/REJECT/REVISE_AND_APPROVE 三类全覆盖 |
| 独立组一致性 | ✅ A/C 统一为 smics_annual_report_2025 |

---

## 下一阶段

- **M2-003A**: CLOSED ✅
- **M2-003B**: READY — FixtureProvider + Context Window + ReviewBundle
- **阻塞项**: 无

---

_婉儿生成 · 大G复核 · 大黄裁断_ 🎋
