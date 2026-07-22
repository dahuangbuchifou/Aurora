# M2-003C Gate 3 Governance Authority Clarification V1.0

> **状态**：ACTIVE / 权威澄清
> **适用范围**：M2-003C Gate 3 的 G3-1～G3-7 定义、证据解释与后续引用

## 1. 唯一规范来源

[16_M2-003C_Gate3_草案持久化验证_任务卡_V1.0.md](../01_requirements/16_M2-003C_Gate3_草案持久化验证_任务卡_V1.0.md) 是 G3-1～G3-7 编号及业务含义的唯一规范来源。Evidence、QA、Closure、阶段计划与 Backlog 只能证明、解释或引用 Gate，不得另行定义 Gate。

## 2. G3-7 正式含义

G3-7 的正式含义是：**Provider 控制或越权语义直接进入持久化核心对象的数量必须为 0**。

G3-7 的验收必须扫描最终数据库 payload，以最终持久化结果作为判定依据。

Provider 不得通过输入字段决定 Aurora 的置信度、认知状态、晋级资格、核验状态或来源独立性等内部语义。

## 3. Provider 字段与 independence_group 边界

- Provider 输入中的 independence_group 属于越权字段，不能直接进入持久化对象，也不能成为授权依据。
- Aurora 可以依据 SourceGraph、来源谱系或其他受控内部逻辑计算并写入独立性分组；这是 Aurora 自有推导结果，不是 Provider 语义透传。
- 由 Aurora 计算的 independence_group 不违反 G3-7；直接接受或映射 Provider 提供的同名语义属于 G3-7 审计范围。

## 4. 冲突项重新编号

阶段计划中原以 G3-7 表述的“ProcessingRun Draft 回滚后仍存在”保留审计要求，但重新编号为 **G3-AUDIT-01**。它是失败审计与运行记录完整性检查，不是正式 Gate 定义。

`12_M2-003_阶段验证与质量门禁计划_V1.0.md` 中保留的旧 G3-7 行属于历史表达，已由 V1.1 治理勘误和本澄清文件 superseded；历史文件保持不改，引用时必须按 G3-AUDIT-01 解读。

## 5. 文档优先级

发生冲突时按以下顺序解释：

1. 本澄清文件解决已识别的治理冲突；
2. 16 号正式任务卡定义 G3-1～G3-7；
3. 经签署的 Closure 与独立 QA 记录裁决；
4. Evidence 提供证明与边界；
5. 阶段计划、Backlog、README 和其他索引仅作引用或规划。

## 6. 后续 Gate 定义变更规则

变更 G3 编号、含义或判定标准，必须先形成有版本号的治理决定并更新正式任务卡，再同步 Evidence、QA、Closure、阶段计划和索引。不得通过测试名称、Evidence、Backlog 或后续 Gate 文档隐式重定义已关闭 Gate，也不得无说明地追溯改写历史裁决。
