# Aurora 项目总进度与资源看板 V1.2

> 更新时间：2026-07-12  
> 当前基线：M1-003B 大G实现完成，等待婉儿目标服务器 QA。

## 1. 总体进度

```text
总体工程进度：27%
█████▍░░░░░░░░░░░░░░ 27%
```

| 阶段 | 权重 | 完成度 | 加权贡献 | 状态 |
|---|---:|---:|---:|---|
| M0 项目基线 | 10% | 100% | 10% | 完成 |
| M1 对象模型与知识标准 | 20% | 85% | 17% | M1-003B待QA |
| M2 MVP认知闭环 | 35% | 0% | 0% | 未开始 |
| M3 个人稳定版 | 25% | 0% | 0% | 未开始 |
| M4 平台化探索 | 10% | 0% | 0% | 未开始 |

M1-003B QA PASS 并关闭 M1 后：

```text
总体进度：30%
M1完成度：100%
```

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
婉儿执行Python 3.11目标服务器QA
→ Bug修复（如有）
→ M1 Exit Review
→ 项目负责人确认进入M2
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

### 婉儿

1. 合并M1-003B增量文件到独立分支；
2. 在Python 3.11.13执行全量测试；
3. 验证Alembic、dry-run、正式迁移、备份和恢复；
4. 输出QA报告；
5. 更新优化清单状态。

### 大G

1. 评估QA结论；
2. 修复阻塞问题；
3. 输出M1 Exit Review正式版；
4. 设计M2-001范围。

### 项目负责人

M1-003B QA通过后，只需确认：

```text
关闭M1
进入M2 MVP认知闭环
```
