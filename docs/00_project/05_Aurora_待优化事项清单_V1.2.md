# Aurora 待优化事项清单 V1.2

> 更新：M1-003B 已实现，等待目标服务器QA。

| ID | 等级 | 类别 | 当前状态 | M1-003B结果 | 后续动作 |
|---|---|---|---|---|---|
| OPT-001 | MAJOR | DataPoint | IN_PROGRESS | MeasurementContext已实现 | QA通过后DONE |
| OPT-002 | MAJOR | Evidence | IN_PROGRESS | 独立组聚合/计数已实现 | QA通过后DONE |
| OPT-003 | MAJOR | Claim | IN_PROGRESS | ClaimDimension已实现，含competition | QA通过后DONE |
| OPT-004 | MAJOR | Provenance | IN_PROGRESS | DerivationLink已实现 | QA通过后DONE |
| OPT-005 | MAJOR | Claim | IN_PROGRESS | 警告式Linter已实现 | QA通过后DONE |
| OPT-006 | MINOR | Database | IN_PROGRESS | timeout/busy_timeout已实现 | QA通过后DONE |
| OPT-007 | MINOR | Testing | IN_PROGRESS | 测试扩展至84项 | QA通过后DONE |
| OPT-008 | ENHANCEMENT | Opinion | DEFERRED | 未进入本轮 | M2/M3 |
| OPT-009 | ENHANCEMENT | Persistence | DEFERRED | 继续单表JSON | M3 |
| OPT-010 | ENHANCEMENT | Collaboration | DEFERRED | Public只读协作可用 | M2评估 |
| OPT-011 | MINOR | Governance | DONE | 进度看板运行中 | 持续维护 |
| OPT-012 | MINOR | Governance | DONE | 固定上下轮评估模板 | 持续维护 |
| OPT-013 | ENHANCEMENT | Quality | PLANNED | 黄金测试集仍为3个主题案例 | M2初期扩至20条 |
| OPT-014 | MAJOR | Semantics | IN_PROGRESS | EvidenceRole规则与测试已实现 | QA通过后DONE |
| OPT-015 | MINOR | Versioning | IN_PROGRESS | 双版本、迁移、恢复已实现 | QA通过后DONE |
| OPT-016 | MINOR | Traceability | IN_PROGRESS | non-dependency降噪已实现 | QA通过后DONE |
| OPT-017 | ENHANCEMENT | Taxonomy | NEW | reporting/attribution/scope仍为自由字符串 | M2真实数据后评估受控词表 |
| OPT-018 | ENHANCEMENT | Migration | NEW | 大规模迁移尚无断点续跑检查点 | 数据量显著增长后评估 |

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
