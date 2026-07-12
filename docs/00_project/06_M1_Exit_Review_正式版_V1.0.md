# Aurora M1 Exit Review 正式版 V1.0

> 评审日期：2026-07-12  
> 评审范围：M1 核心对象模型、真实案例验证、V1.1 兼容升级与迁移  
> 评审结论：**PASS / APPROVED**

## 1. 阶段目标

M1 建立并验证 Aurora 的稳定认知对象契约：

```text
Source
→ Document
→ ContentUnit
→ DataPoint / Claim / Evidence / Fact
→ KnowledgeObject
→ Insight
→ PersonalOpinion
→ OutputArtifact
```

同时具备 Pydantic、JSON Schema、SQLite、Alembic、Repository、版本兼容、来源追溯、数据迁移和真实案例回归。

## 2. 任务完成情况

### M1-001

```text
CLOSED / QA_PASSED
13 passed
87% coverage
```

完成 17 类核心对象、Pydantic V2、JSON Schema、SQLAlchemy 2、SQLite、Alembic、Repository、乐观版本和软删除。

### M1-002

```text
CLOSED / QA_PASSED
24 passed
91% coverage
120 objects
17 object types
```

完成网页、视频、PDF 三类真实案例验证，包括来源定位、同源证据去重、观点污染防护、冲突保留和完整回溯。

### M1-003A

```text
DESIGN_APPROVED
```

冻结 MeasurementContext、ClaimDimension、DerivationLink、Evidence 独立组规则、EvidenceRole 判定、Claim 原子性 Linter、双版本读取和独立 Payload 迁移。

### M1-003B

```text
QA_PASSED
Python 3.11.13
SQLite 3.26+
84 passed
0 failed
0 warnings
96.34% coverage
```

非空迁移补验：

```text
dry-run：通过且未写库
正式迁移：migrated=1 / errors=0
SHA-256：通过
restore：restored=1 / errors=0
恢复后payload：一致
```

## 3. 核心验收

| 验收项 | 结果 |
|---|---|
| 17类对象可表达真实材料 | PASS |
| V1.1加法式、零破坏升级 | PASS |
| V1.0数据可读且读取不自动写回 | PASS |
| V1.0/V1.1混合存储与读取 | PASS |
| JSON Schema双版本确定性 | PASS |
| 来源、证据和认知链可追溯 | PASS |
| 同源证据不重复计数 | PASS |
| 观点不会自动升级为事实 | PASS |
| PersonalOpinion不自动激活 | PASS |
| Alembic升降级 | PASS |
| Payload迁移、备份和恢复 | PASS |
| Python 3.11目标环境 | PASS |
| 覆盖率门禁≥90% | PASS |

## 4. 项目负责人确认

项目负责人已确认：

```text
MeasurementContext
ClaimDimension
DerivationLink
```

作为 M2 使用的 MVP 对象契约。

## 5. 残余问题

M1 结束时不存在 BLOCKER 或未解决的 MAJOR。

以下事项不阻塞 M2：

- OPT-008：PersonalOpinion 快速捕获；
- OPT-009：单表 JSON 后期规范化；
- OPT-010：仓库协作自动化；
- OPT-013：扩展到20条黄金集；
- OPT-017：MeasurementContext受控词表；
- OPT-018：大规模迁移断点续跑。

## 6. 阶段裁决

```text
M1 Exit Review：PASS
M1：CLOSED
V1.1 MVP Object Contract：FROZEN
M2：READY
```

总体进度：

```text
30%
██████░░░░░░░░░░░░░░ 30%
```

## 7. 发布建议

```text
版本：0.3.0
Git Tag：v0.3.0-m1
```

建立 Tag 前确认：

- M1-003B 已合并；
- QA Gate 报告已入库；
- 本 Exit Review 已入库；
- `schemas/v1_1/` 已提交；
- CHANGELOG 和 DECISIONS 已更新。

## 8. M2启动约束

1. 不修改冻结的 V1.1 核心语义；
2. 不新增核心对象，除非单独 ADR 和项目负责人确认；
3. 先建立离线、确定性输入链；
4. M2-001 不引入 LLM、网络抓取、PDF解析或 ASR；
5. 先验证 Source → Document → ContentUnit → ProcessingRun 的稳定落库和幂等性。
