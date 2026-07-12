# Aurora M1 Exit Review 草案 V1.0

> 当前状态：DRAFT  
> 完成条件：M1-003B目标服务器QA PASS。

## 1. M1目标

建立并验证 Aurora 的核心对象契约、来源证据链、版本兼容和基础持久化，使M2可以在稳定的数据宪法上开发自动化输入与理解能力。

## 2. 已完成

- 17类核心对象；
- Pydantic和JSON Schema；
- SQLite/SQLAlchemy/Alembic；
- Repository、软删除、乐观版本；
- 三类真实材料和完整认知链；
- Traceability与观点污染防护；
- Schema V1.1加法式升级；
- V1.0/V1.1双版本读取；
- Payload备份、迁移和恢复；
- 项目治理、进度看板和优化清单。

## 3. 待确认

- [ ] Python 3.11.13全量测试通过；
- [ ] 覆盖率不低于90%；
- [ ] Alembic升级/降级通过；
- [ ] dry-run不写库；
- [ ] backup/restore通过；
- [ ] 三个M1-002案例回归通过；
- [ ] 无BLOCKER；
- [ ] MAJOR全部DONE或明确延期。

## 4. M2进入建议

M1关闭后，M2第一项不应直接接入所有来源，而应先实现：

```text
人工提交Markdown/TXT
→ ContentUnit
→ 规则化/人工辅助提取
→ Fact/Claim/Evidence
→ KnowledgeObject
→ Markdown简报
```

网页、PDF、ASR和LLM随后按接口逐步接入。
