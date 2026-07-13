# M2-003A Gate 0 最终报告 V1.2

> **状态**: FINAL_PASS ✅  
> **报告日期**: 2026-07-13 10:45 CST  
> **Checker**: V1.2b (35/35 — 含 R2 补验 + 负向测试)  
> **Git Commit**: `TBD (after push)`  
> **Python**: 3.11.13 · **jsonschema**: 4.26.0

---

## 修订历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V1.0 | 07-12 | 婉儿初稿标注 |
| V1.1 | 07-13 | 大G复核 + Revision 1 (D-001~D-010) |
| V1.2 | 07-13 | Gate 0 Checker 真实性补验 (R2-001~R2-004) |
| V1.2b | 07-13 | 负向测试 + 严格datetime + REVISE 完整Payload + Case C 去伪REVISE |

---

## Gate 0 V1.2b 门禁结果

```
Gate 0 V1.2b FINAL: PASS ✅
35/35 gates passed
```

### 每案例门禁明细 (11项×3)

| Gate | Case A | Case B | Case C |
|------|:---:|:---:|:---:|
| SCHEMA_V12 (FormatChecker + 完备枚举) | ✅ | ✅ | ✅ |
| SHA256_FILE (material_path 实际文件) | ✅ | ✅ | ✅ |
| QUOTE_GATE (NFKC literal/token_set) | ✅ | ✅ | ✅ |
| ENUMS | ✅ | ✅ | ✅ |
| ID_UNIQUE | ✅ | ✅ | ✅ |
| REFERENCES (incl. review_decisions) | ✅ | ✅ | ✅ |
| FC_RULES | ✅ | ✅ | ✅ |
| PREDICTION | ✅ | ✅ | ✅ |
| DATETIME (ISO 8601 月/日/时/分/秒范围) | ✅ | ✅ | ✅ |
| REVIEWER | ✅ | ✅ | ✅ |
| DISAGREEMENTS_RESOLVED | ✅ | ✅ | ✅ |

### 跨案例门禁 (2项)

| Gate | 结果 |
|------|:---:|
| independence_group A/C一致性 (smics_annual_report_2025) | ✅ |
| G0-7 三类 ReviewDecision 跨案例全覆盖 (APPROVE/REJECT/REVISE) | ✅ |

---

## 4项负向测试

| # | 场景 | 预期 | 实际 |
|---|------|------|------|
| N1 | 篡改源文件（+1字节） | SHA门禁失败 | ✅ tampered≠reported |
| N2 | 虚假Quote（原文不存在的字符串） | Quote Gate失败 | ✅ "literal match FAILED — quote not found in ContentUnits" |
| N3 | 非法date-time（month=99） | DateTime门禁失败 | ✅ "month=99 out of [1,12]" |
| N4 | REVISE缺少revised_payload | ReviewDecision失败 | ✅ "REVISE_AND_APPROVE requires non-empty revised_payload" |

---

## 源文件 SHA-256

| Case | 文件 | SHA-256 |
|------|------|---------|
| A | `tests/fixtures/m2_002/case_a_web.html` | `c5b1ddbacf5d…59afaa` |
| B | `tests/fixtures/m2_002/case_b_video.srt` | `0d189817a12f…ca360` |
| C | `tests/fixtures/m2_002/case_c_report.pdf` | `78de39b7ea1e…d2d777` |

---

## Quote Gate 命中明细

| Case | 总候选 | literal | token_set | 命中 | 失败 |
|------|:---:|:---:|:---:|:---:|:---:|
| A | 9 | 6 (claims+evidence+rejects) | 2 (table DPs) | 8 | 0 |
| B | 7 | 7 (claims+evidence) | 0 | 7 | 0 |
| C | 13 | 13 (DPs+claims+evidence) | 0 | 13 | 0 |

---

## ReviewDecision 跨案例覆盖

| 动作 | 来源 | 案例 |
|------|------|:---:|
| APPROVE | 高质量事实候选 | A(Case C 年报数据) |
| REJECT | 循环自证 / 非事实类型 | B(UP主观点) / C(prediction) |
| REVISE_AND_APPROVE | 管理层prediction → 完整双层Claim Payload | A(大黄裁决方案A) |

---

## 裁决汇总 (14项全部解决)

| # | 问题 | 裁决 |
|------|------|:---:|
| D-001 | A 代码片段→rejects | ✅ |
| D-002 | A 管理层意图→prediction（大黄方案A） | ✅ |
| D-003 | A/C independence_group 统一 | ✅ |
| D-004 | B 删除中芯国际实体 | ✅ |
| D-005 | B 循环自证修复 | ✅ |
| D-006 | C 删除16.5% | ✅ |
| D-007 | C prediction time_horizon | ✅ |
| D-008 | Schema 严格化 | ✅ |
| D-009 | 命名空间迁移 | ✅ |
| D-010 | Checker 语义验证 | ✅ |
| R2-001 | 真实 Quote Gate | ✅ |
| R2-002 | 实际文件 SHA-256 | ✅ |
| R2-003 | FormatChecker + 手动datetime | ✅ |
| R2-004 | 显式 ReviewDecision (含负向测试) | ✅ |

---

## 下一阶段

- **M2-003A**: CLOSED ✅  
- **M2-003B**: READY — Gate 1 代码已交付 (7/7 PASS)，Gate 2 污染测试待推进

---

_婉儿 V1.2b · 大G复核 · 大黄裁断_ 🎋
