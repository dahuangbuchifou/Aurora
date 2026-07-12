# Aurora 待优化事项清单 V1.1

> 更新：M1-002 QA 完成，M1-003A 设计评审。

| ID | 等级 | 类别 | 状态 | M1-003A 决定 | 目标 |
|---|---|---|---|---|---|
| OPT-001 | MAJOR | DataPoint | APPROVED | 增加MeasurementContext | M1-003B |
| OPT-002 | MAJOR | Evidence | APPROVED | 聚合层按独立组去重 | M1-003B |
| OPT-003 | MAJOR | Claim | APPROVED | 增加单值ClaimDimension | M1-003B |
| OPT-004 | MAJOR | Provenance | APPROVED | 增加DerivationLink，保留旧字段 | M1-003B |
| OPT-005 | MAJOR | Claim | APPROVED_PARTIAL | 规范+警告Linter，不硬拦截 | M1-003B |
| OPT-006 | MINOR | Database | APPROVED | Engine统一timeout/busy_timeout | M1-003B |
| OPT-007 | MINOR | Testing | APPROVED | 补齐异常、事务和兼容测试 | M1-003B |
| OPT-008 | ENHANCEMENT | Opinion | DEFERRED | 不进入本轮 | M2/M3 |
| OPT-009 | ENHANCEMENT | Persistence | DEFERRED | 继续单表JSON | M3 |
| OPT-010 | ENHANCEMENT | Collaboration | DEFERRED | 当前Public只读协作可用 | M2 |
| OPT-011 | MINOR | Governance | DONE | 进度看板已建立 | 完成 |
| OPT-012 | MINOR | Governance | DONE | 双助手评估模板已建立 | 完成 |
| OPT-013 | ENHANCEMENT | Quality | PLANNED | 不进入M1-003B | M2初期 |
| OPT-014 | MAJOR | Semantics | APPROVED | 冻结EvidenceRole判定矩阵 | M1-003B |
| OPT-015 | MINOR | Versioning | APPROVED | 双版本读取和显式迁移 | M1-003B |
| OPT-016 | MINOR | Traceability | APPROVED | 非依赖引用跳过dangling error | M1-003B |

## OPT-016 详情

- 发现阶段：M1-002 QA
- 发现人：婉儿
- 真实表现：109 个 processing_run_id dangling references
- 原因：案例未包含统一的 ProcessingRun 对象
- 影响：增加噪音，但不破坏认知链
- 决定：`dependency=false` 的 Edge 不进入 dangling error
- 兼容影响：无 Schema 变更
- 测试：缺失 processing_run 不报错，缺失强依赖仍报错
