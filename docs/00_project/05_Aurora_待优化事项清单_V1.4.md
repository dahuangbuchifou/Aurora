# Aurora 待优化事项清单 V1.4

## M2-001处理项

| ID | 项目 | 状态 |
|---|---|---|
| OPT-021 | 输入幂等性规则 | IMPLEMENTED_PENDING_QA |
| OPT-022 | ContentUnit分段稳定性 | IMPLEMENTED_PENDING_QA |
| OPT-023 | ProcessingRun失败与重试语义 | IMPLEMENTED_PENDING_QA |
| OPT-024 | Source身份与Document幂等边界 | IMPLEMENTED_PENDING_QA |

## 新增观察项

### OPT-025：完整CommonMark兼容

- 等级：ENHANCEMENT
- 类别：Parser
- 状态：DEFERRED
- 目标：M2-002或后续
- 说明：当前 Markdown Parser 只覆盖 heading、paragraph、list、quote、code block。

### OPT-026：JSON单表身份查询性能

- 等级：ENHANCEMENT
- 类别：Repository
- 状态：DEFERRED
- 目标：M3
- 说明：`find_by_external_id` 当前应用层扫描，适合 MVP 数据量；规模扩大后评估索引或规范化。

### OPT-027：并发导入竞争处理

- 等级：MINOR
- 类别：Ingestion
- 状态：DEFERRED
- 目标：M2-005/M3
- 说明：当前面向单用户顺序执行；未来需要对确定性ID并发插入增加重试或任务锁。
