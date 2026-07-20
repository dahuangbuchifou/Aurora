# Aurora 待优化事项清单 V1.8

> 更新时间：2026-07-19
> 权威路径：`docs/00_project/05_Aurora_待优化事项清单_V1.7.md`
> 版本说明：保持权威文件路径不变，正文按原位维护惯例更新为 V1.8；历史 V1.0～V1.6 保持只读。

## 1. 本节点状态变化

| ID | 内容 | 状态 | 关闭/目标证据 |
|---|---|---|---|
| OPT-061 | ContextWindow规范化Hash | DONE | Gate 1 Context Hash V2测试 |
| OPT-062 | 真实Parser链与快照谱系 | DONE | Gate 1三个真实垂直切片 |
| OPT-063 | Git基线与比较基线混淆 | DONE | 本地仓库、协作规范V2.1 |
| OPT-064 | 冻结资产保护 | IN_PROGRESS | Gate 2 SHA清单与节点复核 |

## 2. Gate 2新增事项

### OPT-065：Extraction CLI零覆盖率

```text
等级：MAJOR（非Gate 2阻塞）
类别：Test Coverage
发现节点：Gate 2启动基线
现状：src/aurora/cli/extract.py Coverage = 0%
临时方案：Gate 2不调用CLI，直接测试领域层
责任人：大G
目标节点：M2-003C或CLI正式纳入范围时
状态：DEFERRED_BY_SCOPE
```

### OPT-066：Provider越权字段处理策略需冻结

```text
等级：MAJOR
类别：Epistemic Safety
发现节点：Gate 2任务卡
方案候选：
A. 严格Schema拒绝
B. 移除字段并产生ERROR Finding
建议：A
责任人：大G/婉儿共同确认
目标节点：Gate 2任务卡确认
状态：PROPOSED
```

### OPT-067：Prompt Injection只有数据隔离，没有真实模型验证

```text
等级：MINOR
类别：Model Safety
说明：Gate 2使用FixtureProvider，只能验证系统权限和输出门禁；
不能证明未来真实模型绝不受提示注入影响。
临时方案：来源内容UNTRUSTED标记 + 严格输出验证 + 无工具权限。
目标节点：M2-003D真实Provider小流量验证
状态：DEFERRED
```

## 3. 继续延期

```text
OPT-025 完整CommonMark
OPT-027 并发导入
OPT-028 PDF bbox
OPT-029 JavaScript网页
OPT-030 OCR
OPT-033 字幕语义合并
OPT-035 PDF高级去重
OPT-036 网页字符集高级识别
OPT-037 HTML快照长期归档
OPT-046 ReviewBundle长期归档
```


## 4. 从历史追加段汇入的 Gate 2 遗留项

> 来源：历史 V1.2 后续追加段，本次汇入权威 V1.7 清单。本节迁移事项保留原 ID、标题、等级、状态、背景、来源信息和完成标准。
> 等价性检查：本节迁移事项与现有 OPT-066 相关但不等价；OPT-066 记录策略冻结，迁移项分别记录正式编排链、DTO 所有权、统一 Decoder 和 Fact 晋级所有权，故保留独立 ID。

## OPT-068：Gate 2测试未使用正式FixtureProvider编排链

```text
等级：MAJOR
类别：Provider Integration / Test Fidelity
发现节点：M2-003B Gate 2 Owner Closure
状态：DEFERRED_BY_OWNER
责任人：大G
目标节点：M2-003C Gate 3 Review Round 1前
```

### 问题

Gate 2集成测试仍使用：

```text
读取Provider JSON
→ 测试辅助函数手工构造Candidate
→ QuoteGate
→ SafetyGate
→ ReviewBundle
```

没有实际执行：

```text
FixtureProvider
→ ProviderResponse
→ ExtractionEnvelope
→ QuoteGate
→ SafetyGate
→ ReviewBundle
```

### 完成标准

- 对抗Fixture通过正式FixtureProvider加载；
- ProviderResponse.raw_payload进入统一Decoder/Validation；
- ExtractionEnvelope进入正式链；
- 七类场景保持10次稳定；
- 不再由集成测试维护第二套Candidate构建器。

## OPT-069：FixtureProvider仍把Provider语义字段写入DTO

```text
等级：BLOCKER_BEFORE_PERSISTENCE
类别：Epistemic Ownership
发现节点：M2-003B Gate 2 Owner Closure
状态：DEFERRED_BY_OWNER
责任人：大G
目标节点：M2-003C Gate 3编码前置修复
```

### 问题

当前FixtureProvider仍会从原始Provider JSON读取：

```text
EvidenceCandidate.independence_group
ClaimCandidate.promotable_to_fact
FactCandidate.promotable
```

其中：

- `independence_group`应由Aurora根据来源链计算；
- `promotable`和`promotable_to_fact`不能成为Provider授权。

### 完成标准

- Provider层DTO不接受`independence_group`；
- Engine enrichment阶段单独写入来源独立组；
- Provider提供`promotable=True`或`promotable_to_fact=True`时产生ERROR；
- Gate 3持久化映射不读取上述Provider字段。

## OPT-070：缺少统一Provider Decoder/Forbidden Field Gate

```text
等级：MAJOR
类别：Architecture / Validation
发现节点：M2-003B Gate 2 Owner Closure
状态：DEFERRED_BY_OWNER
责任人：大G
目标节点：M2-003C Gate 3 Review Round 1前
```

### 完成标准

```text
Raw Provider Payload
→ Provider Decoder
→ Schema/Forbidden Field Gate
→ Candidate DTO
→ ExtractionEnvelope
```

所有Provider共用同一入口，并保留原始Payload Hash与Finding。

## OPT-071：ClaimCandidate的promotable_to_fact所有权未完全冻结

```text
等级：MAJOR
类别：Fact Promotion
发现节点：M2-003B Gate 2 Owner Closure
状态：DEFERRED_BY_OWNER
责任人：大G
目标节点：M2-003C Gate 3
```

### 决策建议

Provider不得设置任何晋级授权。`fact_claim`只表示类型上具备进入人工复核的可能，不表示已经获准晋级。

### 完成标准

- Provider设置`promotable_to_fact=True`一律ERROR；
- 引擎可计算`eligible_for_review`；
- 只有ReviewDecision可批准Fact创建。

## 5. M2-003C Gate 3 Closure 后续项

### OPT-072：mapper.py Coverage 恢复至逐文件 ≥90%

```text
来源：M2-003C Gate 3 Closure MAJOR-01
等级：MAJOR
类别：Test Coverage
状态：APPROVED
强制时间点：进入 Gate 4 前
责任人：大G
当前基线：src/aurora/persistence/mapper.py Coverage 88%
目标：Coverage ≥90%
```

#### 实现原则

- 通过增加边界测试覆盖缺失路径；
- 不得删除防御性代码换取 Coverage；
- 重点覆盖 combine / mapping edge cases；
- 修复后运行完整 pytest 和正式 `quality-gate`。

#### 完成标准

- `mapper.py` Coverage ≥90%；
- 总 Coverage 仍 ≥90%；
- 全量测试 0 failed / 0 skipped；
- 正式 CI success；
- 结果写入 Gate 4 启动检查。

#### 阻塞关系

- 不阻塞 Gate 3 Closure；
- 阻塞 Gate 4 启动。

### OPT-073：G3-7 最终数据库 payload 全字段扫描测试补强

```text
来源：M2-003C Gate 3 Closure RECOMMENDATION-01
等级：RECOMMENDATION
类别：Epistemic Safety / Test Coverage
状态：DEFERRED
```

#### 当前结论

- G3-7 已 PASS；
- 组合证据链已被独立 QA 认定充分；
- 当前不是 Gate 4 强制前置；
- 不阻塞 Gate 3 Closure。

#### 建议实现

增加一个端到端测试，扫描最终数据库持久化 payload，一次性断言 Provider 越权字段为零。

#### 完成标准

- 新测试通过；
- 不改变当前对象模型语义；
- 纳入完整回归；
- 在后续 QA 包或 Gate 验收中引用。

本建议项保持为非阻塞建议，不得提升为 MAJOR 或 Gate 4 强制前置。
