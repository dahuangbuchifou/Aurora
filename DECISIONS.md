# DECISIONS.md 追加内容：M1-003A

## ADR-005：DataPoint使用可选MeasurementContext

- 状态：Proposed
- 决定：以嵌套对象表达币种、数量级、报告标准和归属范围。
- 原因：保持Aurora通用模型，避免财务字段散落。

## ADR-006：ClaimType与ClaimDimension正交

- 状态：Proposed
- 决定：新增单值claim_dimension，默认general。
- 原因：区分主张形式和分析维度，支持观点矩阵。

## ADR-007：Provenance增加DerivationLink

- 状态：Proposed
- 决定：新增结构化派生关系，保留origin_object_ids。
- 原因：区分摘要、转载、计算、翻译、提取和推断。

## ADR-008：Evidence独立性在聚合层实现

- 状态：Accepted
- 决定：同一target、role和independence_group只计一个独立证据。
- 原因：保留来源，同时避免重复计数。

## ADR-009：Claim原子性使用规范和警告Linter

- 状态：Accepted
- 决定：M1阶段不使用硬性语义拦截。
- 原因：静态规则无法可靠判断语义原子性。

## ADR-010：EvidenceRole使用同范围直接性原则

- 状态：Accepted
- 决定：主体、时间、口径和维度一致时才使用support/refute。
- 原因：防止增长观点与估值观点被误判为冲突。

## ADR-011：非依赖审计引用不参与悬空错误

- 状态：Accepted
- 决定：processing_run_id缺失不破坏认知链完整性。

## ADR-012：V1.1采用双版本读取和混合存储

- 状态：Proposed
- 决定：读取时适配，禁止读取自动写回。

## ADR-013：JSON Payload迁移不由Alembic隐式执行

- 状态：Proposed
- 决定：Alembic处理DDL，Payload使用显式迁移命令。
# DECISIONS.md 追加：M1 Exit

## ADR-015：Aurora V1.1作为M2 MVP对象契约冻结

- 状态：Accepted
- 决定：17类核心对象及MeasurementContext、ClaimDimension、DerivationLink作为M2冻结契约。
- 影响：M2模块围绕该契约开发，不得直接改变已有语义。
- 变更门槛：Issue、ADR、兼容矩阵、Migration判断、QA和项目负责人确认。

## ADR-016：M2先建立离线确定性输入链

- 状态：Accepted
- 决定：M2-001只支持本地Markdown、纯文本和结构化分段JSON。
- 原因：先解决幂等、分段、定位、事务和ProcessingRun，再引入网络、PDF、ASR和LLM。
- 非目标：网页抓取、PDF解析、ASR、LLM和向量数据库。

## ADR-017：应用DTO不进入核心对象注册表

- 状态：Accepted
- 决定：IngestionRequest、ParserResult、WorkflowState等属于模块DTO，不成为第18类核心对象。
- 原因：避免将传输和执行状态污染知识对象契约。
