# Aurora 待优化事项清单 V1.2

> 更新：2026-07-12 M1-003B QA PASS，全门禁通过。84 passed / 96.34% 覆盖。

| ID | 等级 | 类别 | 当前状态 | M1-003B结果 | 后续动作 |
|---|---|---|---|---|---|
| OPT-001 | MAJOR | DataPoint | DONE | MeasurementContext已实现 | ✅ |
| OPT-002 | MAJOR | Evidence | DONE | 独立组聚合/计数已实现 | ✅ |
| OPT-003 | MAJOR | Claim | DONE | ClaimDimension已实现，含competition | ✅ |
| OPT-004 | MAJOR | Provenance | DONE | DerivationLink已实现 | ✅ |
| OPT-005 | MAJOR | Claim | DONE | 警告式Linter已实现 | ✅ |
| OPT-006 | MINOR | Database | DONE | timeout/busy_timeout已实现 | ✅ |
| OPT-007 | MINOR | Testing | DONE | 测试扩展至84项 | ✅ |
| OPT-008 | ENHANCEMENT | Opinion | DEFERRED | 未进入本轮 | M2/M3 |
| OPT-009 | ENHANCEMENT | Persistence | DEFERRED | 继续单表JSON | M3 |
| OPT-010 | ENHANCEMENT | Collaboration | DEFERRED | Public只读协作可用 | M2评估 |
| OPT-011 | MINOR | Governance | DONE | 进度看板运行中 | 持续维护 |
| OPT-012 | MINOR | Governance | DONE | 固定上下轮评估模板 | 持续维护 |
| OPT-013 | ENHANCEMENT | Quality | PLANNED | 黄金测试集仍为3个主题案例 | M2初期扩至20条 |
| OPT-014 | MAJOR | Semantics | DONE | EvidenceRole规则与测试已实现 | ✅ |
| OPT-015 | MINOR | Versioning | DONE | 双版本、迁移、恢复已实现 | ✅ |
| OPT-016 | MINOR | Traceability | IMPLEMENTED_PENDING_FINAL_QA | non-dependency降噪已实现，功能验证通过 | M1 Exit Review |
| OPT-017 | ENHANCEMENT | Taxonomy | NEW | reporting/attribution/scope仍为自由字符串 | M2真实数据后评估受控词表 |
| OPT-018 | ENHANCEMENT | Migration | NEW | 大规模迁移尚无断点续跑检查点 | 数据量显著增长后评估 |

## OPT-019：QA/Release Integrity — 交付包文件完整性

- **等级：** MAJOR
- **类别：** QA / Release Integrity
- **问题：** 交付包落地时测试文件数量与大G本地结果不一致，且发生代码文件漏复制（payload_migration.py、evidence_role_rules.py 等），可能导致部分代码+部分测试被误判为完整 PASS
- **影响：** 影响验收结论可信度
- **建议：**
  - 强制 SHA256SUMS 验证
  - 强制 MANIFEST 核对
  - 强制 pytest --collect-only 留档
  - CI 中设置 coverage fail-under
- **目标：** M1 退出前
- **状态：** IN_PROGRESS

---

## OPT-020：Schema Testing — Registry 版本测试

- **等级：** MINOR
- **类别：** Schema Testing
- **问题：** 首轮 QA 中 Registry 测试改为接受 1.0 或 1.1 宽泛匹配，缺少确定性
- **建议：** 分别验证冻结 V1.0、当前 V1.1 和顶层 latest
- **当前状态：** 大G 交付包中已改为确定性测试（5/5 passed），无需额外修改
- **目标：** M1 退出前
- **状态：** IN_PROGRESS

---

## OPT-017：MeasurementContext受控词表

- 问题：`reporting_standard`、`attribution_scope`、`consolidation_scope` 当前为字符串；
- 当前选择：保持通用、避免过早固化金融本体；
- 风险：长期可能出现 CAS/cas/企业会计准则 等标签漂移；
- 建议：积累20条以上真实数据后，评估别名映射和受控词表；
- 目标：M2或M3；
- 状态：NEW。

## OPT-018：大规模Payload迁移检查点

- 问题：当前迁移支持批次、幂等和逐对象错误，但没有持久化断点游标；
- 当前规模：约百级对象，不构成阻塞；
- 建议：对象达到万级后增加checkpoint与resume；
- 目标：M3运维强化；
- 状态：NEW。
# Aurora 待优化事项清单：Gate 2追加 V1.0

> 用于追加到正式 `05_Aurora_待优化事项清单`。  
> 状态：OWNER_ACCEPTED_BACKLOG

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
