# Aurora 待优化事项清单

> 发现的问题不能只在聊天中提一下，必须登记。
> 格式：编号 · 严重等级 · 发现阶段 · 真实案例 · 影响对象 · 建议方案 · 兼容影响 · 目标阶段 · 处理状态

**严重等级：** BLOCKER → MAJOR → MINOR → ENHANCEMENT  
**状态：** 📝 待处理 · ⏳ 处理中 · ✅ 已完成 · ❌ 搁置

---

## 当前待处理

| ID | 问题 | 等级 | 发现阶段 | 案例 | 影响对象 | 目标阶段 | 状态 |
|----|------|------|----------|------|----------|----------|------|
| OPT-001 | DataPoint 缺少币种、数量级、会计准则、归属/合并范围 | MAJOR | M1-002 | Case C | DataPoint | M1-003 | 📝 |
| OPT-002 | Evidence 独立性仅有标签，无法程序化去重 | MAJOR | M1-002 | Case A+C | Evidence | M1-003 | 📝 |
| OPT-003 | Claim 缺少增长/估值/风险/行动建议等分析维度 | MAJOR | M1-002 | Case A+B | Claim | M1-003 | 📝 |
| OPT-004 | Provenance 无法结构化区分 summarizes/reposts/calculated_from | MAJOR | M1-002 | Case A+C | Provenance | M1-003 | 📝 |
| OPT-005 | Claim 缺少原子性约束，可混入风险判断+可验证数值 | MAJOR | M1-002 | Case B | Claim | M1-003 | 📝 |
| OPT-006 | SQLite 锁等待策略缺失（busy_timeout） | MINOR | M1-001 | — | session.py | M1-003 | 📝 |
| OPT-007 | schema_registry.py / session.py 单元测试覆盖不足 | MINOR | M1-001 | — | 测试 | M1-003 | 📝 |
| OPT-008 | PersonalOpinion 缺少快速记录低门槛模式 | ENHANCEMENT | M1-001 | — | PersonalOpinion | M2+ | 📝 |
| OPT-009 | 单表 JSON 长期查询效率 — 后续需规范化部分高频表 | ENHANCEMENT | M1-001 | — | DB | M3 | 📝 |
| OPT-010 | dangling reference 检查对 ProcessingRun 类审计引用过于严格 | MINOR | M1-002 | All | traceability.py | M1-003 | 📝 |
| OPT-011 | object_repository.py 覆盖率 85%, 部分异常分支未测 | MINOR | M1-001 | — | repository | M2 | 📝 |
| OPT-012 | PersonalOpinion 激活门槛 6 条件，日常场景略繁琐 | MINOR | M1-001 | — | PersonalOpinion | M2+ | 📝 |
| OPT-013 | 黄金测试集不足 20 条 | ENHANCEMENT | M1-002 | — | 测试 | M3 | 📝 |
| OPT-014 | Evidence Role 边界容易混淆（QUALIFY vs REFUTE vs CONTEXT） | MAJOR | M1-002 | Case B | Evidence, enums | M1-003 | 📝 |
| OPT-015 | V1.0 → V1.1 兼容策略未成文 | MINOR | M1-002 | — | 全部 | M1-003 | 📝 |

---

## 已完成

| ID | 问题 | 等级 | 完成阶段 | 备注 |
|----|------|------|----------|------|
| — | _（暂无已关闭项）_ | | | |

---

_最后更新：2026-07-12 · M1-002 QA 后_
_维护规则：发现即登记，处理完打 ✅ 并移至「已完成」_
