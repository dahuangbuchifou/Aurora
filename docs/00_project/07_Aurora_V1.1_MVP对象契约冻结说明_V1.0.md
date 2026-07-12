# Aurora V1.1 MVP 对象契约冻结说明 V1.0

> 状态：FROZEN  
> 生效阶段：M2  
> Schema版本：1.1  
> 代码版本建议：0.3.0

## 1. 冻结对象

以下17类对象作为M2核心契约：

```text
Source
Document
ContentUnit
Entity
Event
DataPoint
Claim
Evidence
Fact
KnowledgeObject
Relation
TimelineEntry
Insight
PersonalOpinion
OutputArtifact
Feedback
ProcessingRun
```

同时冻结：

```text
MeasurementContext
ClaimDimension
DerivationLink
```

## 2. 冻结含义

M2期间不得未经评审：

- 删除或重命名字段；
- 改变字段必填性或语义；
- 缩窄已支持值域；
- 修改ID、Provenance和生命周期基本含义；
- 删除、重命名或改变已有枚举值语义。

`schemas/v1/` 与 `schemas/v1_1/` 均作为历史契约保留，不得覆盖。

## 3. 允许的变化

可以提出：

- 新增可选字段；
- 新增枚举值；
- 修复验证器Bug；
- 新增DTO、Service、Parser、Workflow；
- 新增Repository查询；
- 新增索引；
- 新增Schema版本目录。

即使是加法式变更，也必须经过：

```text
真实案例
→ Issue
→ ADR
→ 兼容矩阵
→ Migration判断
→ 测试
→ QA
```

## 4. 不属于核心契约的对象

以下可以作为模块DTO，不加入17类核心注册表：

- IngestionRequest；
- ParserResult；
- WorkflowState；
- CLI参数；
- Provider配置；
- 临时错误对象；
- 测试Fixture。

## 5. 语义红线

- Claim 不是 Fact；
- AI输出不是 Evidence；
- OutputArtifact 不是外部来源；
- PersonalOpinion 只能生成 Draft，不能自动激活；
- 同一 independence_group 不重复计数；
- M2模块不得绕过 Repository 假设全部数据库对象都是V1.1。

## 6. 解冻权限

以下事项必须由项目负责人确认：

- 删除或重命名核心字段；
- 新增第18类核心对象；
- 破坏性迁移；
- 改变 Claim、Fact、Evidence、Insight、PersonalOpinion 语义；
- 终止 V1.0 读取支持。

## 7. 冻结裁决

```text
Aurora V1.1
正式作为M2 MVP对象契约冻结。
```
