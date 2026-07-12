# Aurora 项目总进度与资源看板 V1.6

> 更新时间：2026-07-12

## 1. 总体进度

```text
总体进度：35%
███████░░░░░░░░░░░░░ 35%
```

| 阶段 | 权重 | 完成度 | 状态 |
|---|---:|---:|---|
| M0 | 10% | 100% | CLOSED |
| M1 | 20% | 100% | CLOSED |
| M2 | 35% | 35% | IN_PROGRESS |
| M3 | 25% | 0% | NOT_STARTED |
| M4 | 10% | 0% | NOT_STARTED |

M2内部进度：

```text
M2-001：CLOSED
M2-002：READY_FOR_QA
M2-003：PLANNED
M2-004：PLANNED
M2-005：PLANNED
```

> M2内部完成度按已完成M2-001的15%和已实现待QA的M2-002 20%展示为35%；总体治理进度只有在QA通过后再更新。

## 2. 当前资源

需要：

- Python 3.11.13；
- SQLite 3.26+；
- `parsers`可选依赖；
- 本地HTML/PDF/SRT/VTT Fixture；
- 婉儿目标服务器QA。

不需要：

- GPU；
- Docker；
- 浏览器；
- OCR；
- ASR；
- LLM；
- 向量数据库。

## 3. 当前状态

```text
大G实现：完成
本地测试：PASS
目标服务器QA：待执行
技术阻塞：无
```

M2-002 QA PASS后：

```text
总体进度：约42%
M2-002：CLOSED
M2-003：READY_FOR_DESIGN_REVIEW
```
