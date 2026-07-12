# Aurora 项目总进度与资源看板 V1.3

> 更新时间：2026-07-12

## 1. 总体进度

```text
总体进度：30%
██████░░░░░░░░░░░░░░ 30%
```

| 阶段 | 权重 | 完成度 | 加权贡献 | 状态 |
|---|---:|---:|---:|---|
| M0 项目基线 | 10% | 100% | 10% | CLOSED |
| M1 对象模型与知识标准 | 20% | 100% | 20% | CLOSED |
| M2 MVP认知闭环 | 35% | 0% | 0% | READY |
| M3 个人稳定版 | 25% | 0% | 0% | NOT_STARTED |
| M4 平台化探索 | 10% | 0% | 0% | NOT_STARTED |

## 2. M1状态

```text
M1-001：CLOSED
M1-002：CLOSED
M1-003A：DESIGN_APPROVED
M1-003B：QA_PASSED
M1 Exit Review：PASS
V1.1 Contract：FROZEN
```

## 3. M2拆分

| Issue | M2内部权重 | 状态 | 目标 |
|---|---:|---|---|
| M2-001 | 15% | READY_FOR_SPEC_REVIEW | 离线统一输入与内容单元化 |
| M2-002 | 20% | PLANNED | 网页/PDF/转写文本解析适配器 |
| M2-003 | 25% | PLANNED | Fact/Claim/Evidence提取引擎 |
| M2-004 | 20% | PLANNED | Knowledge/Insight/Opinion合成 |
| M2-005 | 20% | PLANNED | 工作流、Markdown简报和MVP验收 |

## 4. 当前资源

已有：

- Alibaba Cloud Linux；
- Python 3.11.13；
- SQLite 3.26+；
- Pydantic V2、SQLAlchemy 2、Alembic；
- GitHub；
- 3个真实案例；
- V1.1冻结契约；
- 84项自动化测试。

M2-001不需要：

- GPU；
- Docker；
- 商业LLM；
- 向量数据库；
- PDF库；
- OCR；
- ASR；
- Web UI。

## 5. 当前行动

### 婉儿

1. 合并M1 Exit Review；
2. 标记M1 CLOSED；
3. 建议建立 `v0.3.0-m1`；
4. 评审M2总体拆分和M2-001边界；
5. 创建M2-001 Issue。

### 大G

1. 等待M2-001正式Issue；
2. 复核当前main和接口；
3. 无阻塞后实现；
4. 不提前引入M2-002范围。

### 项目负责人

仅在M2范围变化、新增核心对象、引入付费或云端敏感处理时介入。
