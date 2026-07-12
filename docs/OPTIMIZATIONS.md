# 待优化项记录

> 记录开发过程中发现的缺陷、优化方向和改进想法。
> 按严重程度排序：🔴 P0 阻塞 → 🟠 P1 重要 → 🟡 P2 改进 → 🔵 P3 未来考虑

---

## 🔴 P0 — 阻塞

_（当前无 P0 项）_

---

## 🟠 P1 — 重要（M1-003 处理）

| # | 问题 | 来源 | 状态 |
|---|------|------|------|
| P1-01 | DataPoint 缺少币种、数量级、会计准则、归属范围和合并范围 | M1-002 审计 | ⏳ 待 M1-003 |
| P1-02 | `independence_group` 目前只有标签，尚未建立禁止重复计数的程序规则 | M1-002 审计 | ⏳ 待 M1-003 |
| P1-03 | Claim 缺少增长、估值、风险、行动建议等分析维度 | M1-002 审计 | ⏳ 待 M1-003 |
| P1-04 | Provenance 无法结构化区分 summarizes / reposts / calculated_from | M1-002 审计 | ⏳ 待 M1-003 |
| P1-05 | Claim 没有原子性约束，可能把风险判断和可验证数值混入同一主张 | M1-002 审计 | ⏳ 待 M1-003 |
| P1-06 | `schema_registry.py` 单元测试缺失（77% 覆盖，缺 8 行） | M1-001 QA | ⏳ 待 M1-003 |
| P1-07 | `session.py` 单元测试缺失，`session_scope` 和 `create_db_engine` 未覆盖 | M1-001 QA | ⏳ 待 M1-003 |
| P1-08 | SQLite connection timeout / busy_timeout 配置 | 婉儿建议 | ⏳ 待 M1-003 |

---

## 🟡 P2 — 改进

| # | 问题 | 来源 | 状态 |
|---|------|------|------|
| P2-01 | PersonalOpinion 激活门槛偏严，日常快速记录可能不够方便 | M1-001 评估 | 📝 后续按需增加 QUICK_CAPTURE |
| P2-02 | Dangling reference 检查过于严格（ProcessingRun 的悬空引用不应影响 validation） | 婉儿观察 | 📝 考虑增加 reference_severity 分级 |
| P2-03 | `object_repository.py` 覆盖率 85%，部分异常分支未测试 | M1-001 QA | 📝 后续补充 |

---

## 🔵 P3 — 未来考虑

| # | 问题 | 来源 | 状态 |
|---|------|------|------|
| P3-01 | Aurora ↔ WQRS 接入（M3 阶段） | MEMORY.md | 📝 M3 |
| P3-02 | 单表 JSON → 规范化表迁移方案（Entity/Claim/Evidence/Relation 优先） | M1-001 架构设计 | 📝 稳定版后 |
| P3-03 | 向量检索 | ROADMAP | 📝 M3 |
| P3-04 | Web API / REST / MCP | ROADMAP | 📝 M4 |

---

_最后更新：2026-07-12_
_维护规则：发现问题随时追加，处理完毕打 ✅_
