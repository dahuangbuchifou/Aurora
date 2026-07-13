# M2-003A Gate 0 正式报告 V1.2

> **状态**: FINAL_PASS ✅  
> **报告日期**: 2026-07-13  
> **Checker**: V1.2 (32/32 — R2-001 至 R2-004 补验完成)

---

## 修订历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V1.0 | 07-12 | 婉儿初稿标注，Gate 0 初验 |
| V1.1 | 07-13 | 大G独立复核 + Revision 1 (D-001—D-010) |
| V1.2 | 07-13 | Gate 0 Checker 真实性补验 (R2-001—R2-004) |

---

## 裁决汇总

| 编号 | 案例 | 问题 | 裁决 |
|------|------|------|:---:|
| D-001 | A | 代码片段在 expected_claims | ✅ → expected_rejects |
| D-002 | A | 管理层意图 claim_type | ✅ prediction 方案A（大黄） |
| D-003 | A/C | independence_group 不一致 | ✅ 统一 smics_annual_report_2025 |
| D-004 | B | 中芯国际实体无原文依据 | ✅ 删除 |
| D-005 | B | UP主观点循环自证 | ✅ evidence→attribution, FC→false |
| D-006 | C | 16.5%无原文依据 | ✅ 仅保留绝对值 |
| D-007 | C | Prediction 缺 time_horizon | ✅ 新增 precision=unknown |
| D-008 | Schema | 过于宽松 | ✅ V1.1 严格化 |
| D-009 | Arch | 命名空间错配 | ✅ ingestion→extraction |
| D-010 | Checker | 弱结构≠语义 | ✅ V1.1 16项语义规则 |
| R2-001 | Checker | Quote Gate 未真执行 | ✅ literal/token_set NFKC 匹配 |
| R2-002 | Checker | SHA-256 未读文件 | ✅ 根据 material_path 计算实际Hash |
| R2-003 | Checker | FormatChecker 未启用 | ✅ Draft202012Validator + FormatChecker |
| R2-004 | Checker | Warning 推断 REVISE | ✅ 显式 expected_review_decisions |

---

## Gate 0 V1.2 门禁结果

```
Gate 0 V1.2 FINAL: PASS ✅
32/32 gates passed
```

### 每案例门禁明细

| Gate | Case A | Case B | Case C |
|------|:---:|:---:|:---:|
| SCHEMA_V12 (FormatChecker) | ✅ | ✅ | ✅ |
| SHA256_FILE (实际文件) | ✅ | ✅ | ✅ |
| QUOTE_GATE (NFKC 子串匹配) | ✅ | ✅ | ✅ |
| ENUMS | ✅ | ✅ | ✅ |
| ID_UNIQUE | ✅ | ✅ | ✅ |
| REFERENCES | ✅ | ✅ | ✅ |
| FC_RULES | ✅ | ✅ | ✅ |
| PREDICTION | ✅ | ✅ | ✅ |
| REVIEWER | ✅ | ✅ | ✅ |
| DISAGREEMENTS_RESOLVED | ✅ | ✅ | ✅ |

### 跨案例门禁

| Gate | 结果 |
|------|:---:|
| independence_group 一致性 (A/C) | ✅ |
| G0-7 显式 ReviewDecision 三类全覆盖 | ✅ |

### V1.2 新增验证

| 新增门禁 | 说明 |
|----------|------|
| Quote Gate 真实子串匹配 | NFKC 规范化 + literal/token_set 双模式 |
| 实际文件 SHA-256 | material_path → 文件字节 → 对比 |
| FormatChecker | date-time 格式强校验 |
| 显式 ReviewDecision | APPROVE/REJECT/REVISE_AND_APPROVE 全部有修订内容 |

---

## 案例覆盖

| | Case A(网页) | Case B(视频) | Case C(PDF) |
|---|---|---|---|
| Entity | 1 | 3 | 1 |
| DataPoint | 2 (token_set) | 0 | 4 |
| Claim | 3 | 4 | 2 |
| Evidence | 2 | 1 | 4 |
| FactCandidate | 1 promotable | 2 non-promotable | 1+1 |
| Reject | 1 | 0 | 0 |
| ReviewDecision | APPROVE/REJECT/REVISE | REJECT×2/REVISE | APPROVE/REJECT/REVISE |

---

## 下一阶段

- **M2-003A**: CLOSED ✅  
- **M2-003B**: READY — M2-003B 代码已交付（Gate 1 7/7 PASS），可直接进入 Gate 2

---

_婉儿 V1.2 · 大G复核 · 大黄裁断_ 🎋
