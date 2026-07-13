# Aurora 待优化事项清单 V1.7

> 更新时间：2026-07-13

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
