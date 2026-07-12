# Aurora 待优化事项清单 V1.3

> 更新时间：M1 Exit Review

## 1. M1完成项

| ID | 等级 | 项目 | 最终状态 |
|---|---|---|---|
| OPT-001 | MAJOR | DataPoint MeasurementContext | DONE |
| OPT-002 | MAJOR | Evidence独立组聚合 | DONE |
| OPT-003 | MAJOR | ClaimDimension | DONE |
| OPT-004 | MAJOR | DerivationLink | DONE |
| OPT-005 | MAJOR | Claim原子性Linter | DONE |
| OPT-006 | MINOR | SQLite timeout/busy_timeout | DONE |
| OPT-007 | MINOR | Registry/Session/Migration测试 | DONE |
| OPT-011 | MINOR | 项目进度看板 | DONE |
| OPT-012 | MINOR | 双助手固定评估结构 | DONE |
| OPT-014 | MAJOR | EvidenceRole判定标准 | DONE |
| OPT-015 | MINOR | V1.0/V1.1兼容与迁移 | DONE |
| OPT-016 | MINOR | 非依赖dangling降噪 | DONE |
| OPT-019 | MAJOR | QA与交付完整性门禁 | DONE |
| OPT-020 | MINOR | Schema Registry确定性测试 | DONE |

## 2. 延后与计划项

| ID | 等级 | 项目 | 状态 | 目标阶段 |
|---|---|---|---|---|
| OPT-008 | ENHANCEMENT | PersonalOpinion快速捕获状态 | DEFERRED | M2/M3 |
| OPT-009 | ENHANCEMENT | 单表JSON规范化 | DEFERRED | M3 |
| OPT-010 | ENHANCEMENT | 仓库协作自动化 | DEFERRED | M2 |
| OPT-013 | ENHANCEMENT | 20条黄金测试集 | PLANNED | M2 |
| OPT-017 | ENHANCEMENT | MeasurementContext受控词表 | DEFERRED | M2/M3 |
| OPT-018 | ENHANCEMENT | 大规模迁移断点续跑 | DEFERRED | M3 |

## 3. M2新增观察项

### OPT-021：输入幂等性规则

- 等级：MAJOR
- 类别：Ingestion
- 状态：PLANNED
- 问题：同一文件、同一来源或内容相同但路径不同的文件可能重复导入。
- 目标：M2-001
- 建议：规范化URI、content_hash、idempotency_key和重复处理策略。

### OPT-022：内容分段稳定性

- 等级：MAJOR
- 类别：Parser
- 状态：PLANNED
- 问题：Parser版本变化可能改变ContentUnit ID、顺序和定位。
- 目标：M2-001/M2-002
- 建议：确定性分段、parser_version、稳定序号和回归Fixture。

### OPT-023：ProcessingRun失败语义

- 等级：MINOR
- 类别：Workflow
- 状态：PLANNED
- 问题：失败、部分成功和重试对已创建对象的影响需要统一。
- 目标：M2-001
- 建议：定义事务边界、失败状态、错误代码和重试规则。

## 4. 维护规则

M2每个Issue结束时必须：

1. 更新本清单；
2. 为新问题分配OPT编号；
3. 区分当前修复和延期；
4. 不删除DONE历史；
5. 影响冻结契约的问题单独升级为Schema Issue。
