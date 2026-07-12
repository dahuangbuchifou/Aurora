# Aurora 项目总进度与资源看板 V1.2

> 更新时间：2026-07-12 16:43  
> 当前基线：M1-003B QA PASS，全门禁通过。M1 Exit Review：READY。

## 1. 总体进度

```text
总体工程进度：30%
██████░░░░░░░░░░░░░░ 30%
```

| 阶段 | 权重 | 完成度 | 加权贡献 | 状态 |
|---|---:|---:|---:|---|
| M0 项目基线 | 10% | 100% | 10% | 完成 |
| M1 对象模型与知识标准 | 20% | 100% | 20% | QA_PASSED, 待Exit Review |
| M2 MVP认知闭环 | 35% | 0% | 0% | 未开始 |
| M3 个人稳定版 | 25% | 0% | 0% | 未开始 |
| M4 平台化探索 | 10% | 0% | 0% | 未开始 |

## 2. Issue 状态

```text
M1-001：CLOSED
M1-002：CLOSED / QA_PASSED
M1-003A：DESIGN_APPROVED
M1-003B：READY_FOR_QA
M1 Exit Review：DRAFT
```

## 3. 本轮完成

- Schema V1.1 三项加法式扩展；
- V1.0/V1.1 双版本读取；
- 混合版本 Repository；
- Evidence 独立性聚合；
- Claim 原子性 Linter；
- Traceability 非依赖引用降噪；
- SQLite timeout；
- Alembic索引迁移；
- Payload dry-run、备份、迁移和恢复；
- V1.1 JSON Schema与示例；
- 84项本地测试，覆盖率96%。

## 4. 当前阻塞

无技术阻塞。

流程依赖：

```text
婉儿 QA PASS ✅
→ 项目负责人确认三项 Schema 变更 ← 当前
→ 大G M1 Exit Review
→ 项目负责人确认进入 M2
```

## 5. 当前资源

已具备：

- Alibaba Cloud Linux；
- Python 3.11.13；
- SQLite 3.26+；
- GitHub公开仓库；
- M1-001/M1-002测试与三个真实案例；
- 大G代码交付与婉儿QA流程。

当前不需要：

- GPU；
- Docker；
- 向量数据库；
- 商业LLM API；
- Web前端；
- 新服务器。

## 6. 下一步

### 项目负责人（大黄）

确认三项 Schema 变更：

```text
项目负责人确认 Aurora V1.1 的三项加法式 Schema 变更：
- MeasurementContext：确认
- ClaimDimension：确认
- DerivationLink：确认
同意其作为 M2 使用的 MVP 对象契约。
```

### 大G

1. 复核补验报告 (`docs/qa/M1-003B_QA_Gate_补验报告.md`)；
2. 更新 OPT-016/019/020 状态；
3. 输出 M1 Exit Review 正式版；
4. 冻结 V1.1 契约；
5. 给出 M2 总体拆分和 M2-001 任务边界。
