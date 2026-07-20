# M2-003C Gate 3 独立 QA 报告 V1.3（独立验收结果已回填）

> **文档版本**：V1.3<br>
> **文档状态**：REVIEWED / 婉儿独立验收已完成<br>
> **独立验收状态**：COMPLETED<br>
> **独立验收裁决**：CONDITIONAL_PASS<br>
> **Closure 转录校验**：TRANSCRIPTION_CONFIRMED<br>
> **Gate 3 生命周期状态**：CONDITIONALLY_CLOSED_BY_OWNER<br>
> **Task ID**：M2-003C Gate 3 Draft Persistence<br>
> **草案编制**：Codex（仅吸收并整理权威验收结论，不是独立 QA 验证人）<br>
> **独立验证人**：婉儿<br>
> **报告更新日期**：2026-07-19 CST

## 1. 文档定位

本报告已吸收婉儿独立验收结论 `CONDITIONAL_PASS`，记录 G3-1～G3-7 的独立裁决、CI 原始日志核验结果和后续问题分级。婉儿建议按 `CLOSE_WITH_FOLLOW_UPS` 关闭，项目负责人已于 2026-07-19 作出 `APPROVE_CLOSE_WITH_FOLLOW_UPS` 决定，Gate 3 生命周期状态为 `CONDITIONALLY_CLOSED_BY_OWNER`。

证据索引见 [M2-003C_Gate3_Evidence_V1.3.md](M2-003C_Gate3_Evidence_V1.3.md)，外部证据哈希见 [M2-003C_Gate3_external_evidence.sha256](M2-003C_Gate3_external_evidence.sha256)，正式签署后的 Closure 见 [20260719_M2-003C_Gate3_Review_Closure_V1.3.md](20260719_M2-003C_Gate3_Review_Closure_V1.3.md)。Codex 仅转录已提供的婉儿独立验收签署和项目负责人决定，不自行代替任一角色作出裁决。

## 2. 验证范围与非范围

### 2.1 范围内

- 核对 Git Base、Branch、Head 和 merge-base；
- 汇总 PR #1 与 GitHub Actions `quality-gate` Run #14 的已提供结果；
- 核对正式 workflow 中 pytest、coverage、frozen-assets、schema-diff、alembic-check 的定义；
- 按 [Gate 3 任务卡](../01_requirements/16_M2-003C_Gate3_草案持久化验证_任务卡_V1.0.md) 建立 G3-1～G3-7 证据映射；
- 引用当前 Head 中的测试代码和 R4 提交说明；
- 登记证据缺口并预留婉儿独立验收区域。

### 2.2 非范围

- 不重新运行 pytest 或 coverage；
- 不下载、解压或复制 CI 二进制证据；
- 不复核外部日志 ZIP 的实际内容；
- 不修改源码、测试、workflow、任务卡、看板、CHANGELOG 或待优化事项；
- 不生成最终 Review Closure；
- 不自行代替婉儿或项目负责人作出裁决。

## 3. Git 与任务基线

| 字段 | 值 | 证据 |
|---|---|---|
| Repository | `dahuangbuchifou/Aurora` | E1 |
| Base branch | `main` | E1 |
| 当前 main | `4691e53f8465c3e33ca378f27368b39915eb4200` | E1 |
| origin/main | `4691e53f8465c3e33ca378f27368b39915eb4200` | E1 |
| PR #1 base_sha | `4691e53f8465c3e33ca378f27368b39915eb4200` | E1 |
| Head branch | `feature/m2-003c-gate3-draft-persistence` | E1 |
| Code baseline Commit | `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` | E1、E2 |
| Merge-base | `4691e53f8465c3e33ca378f27368b39915eb4200` | E1 |
| 工作区 | 基线核验时 clean | E1 |
| PR | `#1 feat: start M2-003C Gate 3 draft persistence` | E2 |

## 4. CI 环境与结果

| 字段 | 值 | 证据 |
|---|---|---|
| Repository | `dahuangbuchifou/Aurora` | E1、E3 |
| PR | `#1 feat: start M2-003C Gate 3 draft persistence` | E2、E3 |
| Workflow | `quality-gate` | E3 |
| Run number | `14` | E3 |
| Run URL | https://github.com/dahuangbuchifou/Aurora/actions/runs/29635417889 | E3 |
| Run database ID | `29635417889` | E3 |
| Head SHA | `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` | E2、E3 |
| Trigger | `pull_request / synchronize` | E3 |
| Run created_at | `2026-07-18T07:15:04Z` | E3 |
| Run started_at | `2026-07-18T07:15:04Z` | E3 |
| Run updated_at | `2026-07-18T07:15:39Z` | E3 |
| Run status | `completed` | E3 |
| Run conclusion | `success` | E3 |
| Job URL | https://github.com/dahuangbuchifou/Aurora/actions/runs/29635417889/job/88056793497 | E3 |
| Job database ID | `88056793497` | E3 |
| Job name | `gate (3.11)` | E3 |
| Runner group | `GitHub Actions` | E3 |
| Runner name | `GitHub Actions 1000000040` | E3 |
| Job started_at | `2026-07-18T07:15:06Z` | E3 |
| Job completed_at | `2026-07-18T07:15:38Z` | E3 |
| Job status | `completed` | E3 |
| Job conclusion | `success` | E3 |
| CI OS | `Ubuntu 24.04` | E3 |
| Python | `3.11.15` | E3 |
| CI conclusion（显示值） | `Success` | E3 |
| pytest | `success` | E3、E4 |
| coverage | `success` | E3、E5、E6 |
| frozen-assets | `success` | E3、E8 |
| schema-diff | `success` | E3、E9 |
| alembic-check | `success` | E3、E10 |

上述时间均为 GitHub API 原始时间（UTC ISO-8601）。`updated_at` 仅表示 Workflow Run 记录最后更新时间，不等同于、也不表述为 `run_completed_at`。婉儿已从 E12-A 原始日志独立核验 CI、测试和 Coverage 结果。

### 4.1 外部证据登记

| Evidence ID | Artifact basename | external:// 逻辑路径 | SHA-256 | 来源及对应基线 | 核验状态 |
|---|---|---|---|---|---|
| E12-A | `quality-gate_run-14_44c875e_logs.zip` | `external://Aurora-Gate3-Evidence/CI/quality-gate_run-14_44c875e_logs.zip` | `fb1993c94c80fa8c77b48561466452792d2d714e113944c780f56ef88f036711` | GitHub Actions `quality-gate` Run #14；Head `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` | 婉儿已独立复算 SHA-256 一致，并从原始日志核验 CI、测试与 Coverage |
| E12-B | `quality-gate_run-14_summary.png` | `external://Aurora-Gate3-Evidence/CI/quality-gate_run-14_summary.png` | `cd85b49b1eeb24a8708b093ad0bb262f24edd00bbcc7e05f38d1e97fee55de35` | GitHub Actions `quality-gate` Run #14 辅助截图；同一 Head | 婉儿未取得 PNG 原文件，未独立复算；辅助证据，不阻塞 Closure |
| E12-C | `quality-gate_run-14_coverage.png` | `external://Aurora-Gate3-Evidence/CI/quality-gate_run-14_coverage.png` | `25bbcc7fb637e902e0fae98b314a9ac8abba37b4ed0f4aefdfdd15ecd8e658ed` | GitHub Actions `quality-gate` Run #14 Coverage 辅助截图；同一 Head | 婉儿未取得 PNG 原文件，未独立复算；Coverage 已从原始日志核验，不阻塞 Closure |

## 5. pytest 结果

| 执行 | 正式命令 | 结果 | 精确 duration | 独立核验 |
|---|---|---|---:|---|
| 普通 pytest | `python -m pytest -q --tb=short` | `644 passed / 0 failed / 0 skipped`；`success` | 4.72s | 婉儿已从 E12-A 原始日志核验 |
| coverage pytest | `python -m pytest --cov=aurora --cov-branch --cov-fail-under=90 -q` | `644 passed / 0 failed / 0 skipped`；`success` | 7.79s | 婉儿已从 E12-A 原始日志核验 |

- `pytest -q` 未输出 collected 行，不视为证据缺口。
- warnings 未显示，不视为异常，也不推断具体 warnings 数量。
- CI Python 为 `3.11.15`，运行环境为 `Ubuntu 24.04`。

## 6. Coverage 结果

| 指标 | 结果 | 状态 |
|---|---:|---|
| 精确总 Coverage | 92.64% | 婉儿已从 Run #14 原始日志独立核验 |
| 最低门槛 | 90% | 正式 Workflow 硬门槛 |
| coverage gate | success | 独立核验一致 |

### 6.1 Persistence 逐文件 Coverage

历史值与 Run #14 当前值严格分栏。当前值来自 GitHub Actions `quality-gate` Run #14 原始 coverage 日志，并与 CI summary、`644 passed` 和总 Coverage `92.64%` 交叉核对。

| 文件 | 历史提交说明 | Run #14 当前精确值 | 核验状态 |
|---|---:|---:|---|
| `src/aurora/persistence/__init__.py` | 未记录 | 100% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/contracts.py` | 96%（`39a1b42`） | 96% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/draft_service.py` | 90%（`39edc4f`） | 92% | 历史 90%，当前 92% |
| `src/aurora/persistence/identity.py` | 100%（`39a1b42`） | 100% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/mapper.py` | 92%（`39edc4f`） | **88%** | **历史 92%，当前 88%；MAJOR-01** |
| `src/aurora/persistence/persistence_policy.py` | 未记录 | 100% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/source_graph.py` | 99%（`39a1b42`） | 99% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/validation.py` | 98%（`39edc4f`） | 96% | 历史 98%，当前 96% |
| `src/aurora/workflow/draft_persistence.py` | 未记录 | 100% | 婉儿已从原始日志核验 |

正式 Workflow 的硬门槛是全项目总 Coverage ≥90%；实际总 Coverage 为 92.64%，coverage job 已通过。`mapper.py` 当前 Coverage 为 **88%**，不阻塞 Gate 3 Closure，但必须在 Gate 4 前通过增加边界测试提升至 ≥90%，不得为覆盖率删除防御性代码。

## 7. CI 保护门禁

| 门禁 | 已提供结果 | 仓库定义 | 证据 |
|---|---|---|---|
| frozen-assets | success | 校验 `docs/qa/M2-003B_Gate2_frozen_assets.sha256` 中的冻结资产 | E8 |
| schema-diff | success | 对 PR base SHA 与 Head 的 `schemas/` 差异执行硬失败检查 | E9 |
| alembic-check | success | 对 PR base SHA 与 Head 的新增 Alembic revision 执行硬失败检查 | E10 |

## 8. G3-1～G3-7 独立验收裁决矩阵

独立验证人婉儿已结合测试代码、Run #14 原始日志与 Evidence 编号作出裁决。

| Gate | 任务卡硬条件 | 关键证据 | Evidence | 婉儿裁决 |
|---|---|---|---|---|
| G3-1 | 事务残留对象 = 0 | 回滚与强制中途失败断言；FAILED ProcessingRun 保留 | E4、E5、E11-G3-1 | PASS |
| G3-2 | 自动 Fact = 0 | `test_no_fact` 数据库零记录断言 | E4、E5、E11-G3-2 | PASS |
| G3-3 | 未复核 Claim 被标 confirmed = 0 | Claim `epistemic_status=under_review` | E4、E5、E11-G3-3 | PASS |
| G3-4 | 悬空 Candidate 引用 = 0 | rejected 不持久化、accepted/rejected 交集拒绝、accepted ID 缺失报错 | E4、E5、E11-G3-4 | PASS |
| G3-5 | 悬空核心对象引用 = 0 | 四类对象闭环及 unresolved-reference 负向测试 | E4、E5、E11-G3-5 | PASS |
| G3-6 | 重复运行产生严格重复对象 = 0 | 同 bundle 与跨 session 幂等断言 | E4、E5、E11-G3-6 | PASS |
| G3-7 | Provider 越权字段进入持久化对象 = 0 | Provider 越权检测、rejected 不持久化、provider independence override 路径、Gate 2 对抗测试组成的证据链 | E4、E5、E11-G3-7、E13、E14 | PASS |

### 8.1 G3-7 证据边界与后续建议

G3-7 当前仍属于组合证据链：

1. Provider 越权字段由 SafetyGate 检测并产生 `PROVIDER_OVERRIDE_FIELD`；
2. rejected candidate 由 Gate 3 测试验证不进入持久化记录；
3. `provider_independence_override` 对抗路径进入 Gate 3 SQLite 流程；
4. Gate 2 对抗测试识别 `independence_group` 等 Provider 越权字段。

尚未发现单一测试直接扫描最终数据库 payload，并一次性断言所有 Provider 越权字段为零。婉儿裁决当前组合证据足以支持 G3-7 PASS，因此该项不阻塞 Gate 3 Closure；建议在 Gate 4 前增加端到端全字段扫描测试。

## 9. R4 关键修复项

当前 Head `44c875e` 的提交说明记录了三组修复：

### A. Provider Policy

- 新增 `_policy_for_adversarial_bundle()` 测试辅助函数；
- 替换多个只允许 `fixture` 的局部 `PersistencePolicy`；
- 修复 `backward_compat_wrapper_dry` 的 `workspace_id` 不一致；
- 目标是使迁移后的 keyword-only policy 调用在当前测试路径中无失败。

### B. independence_group / Evidence

- 空 `independence_group` 改由 Pydantic 模型层拒绝；
- `pending_source_graph` 相关断言改为真实已解析值的正向验证；
- `forged_or_outside_unit` 独立保留为负向测试；
- Evidence 使用真实 resolved `independence_group` 的路径得到覆盖。

### C. R3-S06 闭环场景

- 新增 `_seed_complete_source_graph()`，构造真实 Source → Document → ContentUnit 链；
- 修复 EntityCandidate 模型兼容性；
- 四类完整持久化和强制事务中途失败两个场景在提交说明中记录为无 skip/xfail；
- 当前 CI 摘要记录 `644 passed / 0 failed / 0 skipped`。

上述内容来自 Git 提交元数据和当前测试代码；其运行结果仍以 E12 原始 CI 日志为最终独立核验依据。

## 10. 独立验收问题分级

| 分类 | 数量 | 正式编号 |
|---|---:|---|
| BLOCKER | 0 | 无 |
| MAJOR | 1 | MAJOR-01 |
| MINOR | 1 | MINOR-01 |
| RECOMMENDATION | 1 | RECOMMENDATION-01 |
| RESOLVED | 1 | RESOLVED-01 |

### BLOCKER

0 项。

### MAJOR-01：`mapper.py` Coverage 88%

- 不阻塞 Gate 3 Closure；
- 进入 Gate 4 前必须通过增加边界测试提升至 ≥90%；
- 不得为覆盖率删除防御性代码。

### RECOMMENDATION-01：增加最终数据库 payload 全字段扫描测试

- G3-7 当前裁决为 PASS；
- 当前组合证据链已被婉儿认定充分；
- 建议后续增加单一端到端全字段扫描测试；
- 不阻塞 Gate 3 Closure；
- 不是 Gate 4 强制前置。

### MINOR-01：E12-B / E12-C PNG 未独立复算

- 婉儿未取得两张 PNG 原文件；
- E12-A 日志 ZIP SHA-256 已独立复算一致；
- Coverage 和 CI 结论已从原始日志确认；
- PNG 为辅助证据，不阻塞 Closure。

### RESOLVED-01：merge-base 核验差异

- 当前 `main`、`origin/main`、PR #1 `base_sha` 与实际 merge-base 均为 `4691e53f8465c3e33ca378f27368b39915eb4200`；
- `f71aee47e6cb762e06793355aae4cc2eb00ba951` 是 `4691e53...` 的历史祖先，不是 PR #1 的 base 或实际 merge-base；
- 结论：`RESOLVED / 草案原值正确`；不再属于 MINOR 或 Closure 前置条件。

## 11. 已知限制与治理边界

- Codex 不是独立 QA 验证人，仅吸收婉儿权威裁决；
- `pytest -q` 未输出 collected 行不视为缺口，warnings 未显示不视为异常；
- E12-A 日志 ZIP SHA 已由婉儿独立复算一致，测试和 Coverage 已从原始日志核验；
- E12-B / E12-C PNG 未由婉儿取得原文件独立复算；
- MAJOR-01 是唯一明确的 Gate 4 强制前置；RECOMMENDATION-01 是非阻塞建议项；
- 项目负责人已确认 `APPROVE_CLOSE_WITH_FOLLOW_UPS`；Gate 3 生命周期状态为 `CONDITIONALLY_CLOSED_BY_OWNER`。

## 12. 独立验收结论

~~~text
CONDITIONAL_PASS
~~~

- G3-1～G3-7：全部 PASS；
- BLOCKER：0；
- 独立 QA 建议关闭方式：`CLOSE_WITH_FOLLOW_UPS`；
- Gate 3 生命周期状态：`CONDITIONALLY_CLOSED_BY_OWNER`；
- 正式签署后的 Review Closure：[20260719_M2-003C_Gate3_Review_Closure_V1.3.md](20260719_M2-003C_Gate3_Review_Closure_V1.3.md)。

## 13. 婉儿独立验收区域

- 独立验证人：婉儿
- 验收日期/时区：2026-07-18 / Asia/Shanghai（UTC+08:00）
- 独立验收状态：`COMPLETED`
- 最终裁决：`CONDITIONAL_PASS`
- Closure 转录校验：`TRANSCRIPTION_CONFIRMED`
- Run #14 原始日志已核验：是
- E12-A 日志 ZIP SHA-256 已独立复算一致：是
- E12-B / E12-C PNG 原文件已独立复算：否（未取得原文件，不阻塞）
- Persistence 逐文件 Coverage 已从原始日志核验：是
- G3-1：PASS
- G3-2：PASS
- G3-3：PASS
- G3-4：PASS
- G3-5：PASS
- G3-6：PASS
- G3-7：PASS
- BLOCKER：0
- MAJOR：1 项（MAJOR-01）
- MINOR：1 项（MINOR-01）
- RECOMMENDATION：1 项（RECOMMENDATION-01）
- RESOLVED：1 项（RESOLVED-01）
- 独立 QA 建议关闭方式：`CLOSE_WITH_FOLLOW_UPS`
- 签署：婉儿 🎋
