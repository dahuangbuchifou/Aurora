# Aurora 项目总进度与资源看板 V1.5

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
| M2 | 35% | 15% | IN_PROGRESS |
| M3 | 25% | 0% | NOT_STARTED |
| M4 | 10% | 0% | NOT_STARTED |

## 2. M2状态

```text
M2-001：CLOSED / QA_PASSED
M2-002：READY_FOR_DESIGN_REVIEW
M2-003：PLANNED
M2-004：PLANNED
M2-005：PLANNED
```

## 3. M2-002资源

需要：

- Python 3.11.13；
- SQLite 3.26+；
- M2-001当前main；
- HTML合成Fixture；
- PDF合成Fixture；
- SRT/VTT Fixture；
- M1-002三案例QA材料；
- 大G实现；
- 婉儿设计评审和服务器QA。

建议新增可选依赖：

```text
beautifulsoup4
lxml
httpx
pdfplumber
webvtt-py
```

不需要：

- GPU；
- Docker；
- LLM；
- 浏览器；
- OCR；
- ASR；
- 向量数据库；
- 新服务器。

## 4. 当前流程

```text
M2-002设计评审
→ 冻结Issue
→ 大G编码
→ 婉儿QA
→ M2-002关闭
```

M2-002 QA通过后，预计总体治理进度更新至约42%。
