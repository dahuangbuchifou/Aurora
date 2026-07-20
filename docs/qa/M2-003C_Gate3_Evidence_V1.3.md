# M2-003C Gate 3 Evidence V1.3（最终治理状态已同步）

> **文档状态**：FINALIZED_FOR_CONDITIONAL_CLOSURE
> **独立验证人**：婉儿
> **验收日期/时区**：2026-07-18 / Asia/Shanghai（UTC+08:00）
> **独立 QA 状态**：COMPLETED
> **独立 QA 裁决**：CONDITIONAL_PASS
> **Closure 转录校验**：TRANSCRIPTION_CONFIRMED
> **独立 QA 建议关闭方式**：CLOSE_WITH_FOLLOW_UPS
> **Closure 决定**：CLOSE_WITH_FOLLOW_UPS
> **项目负责人决定**：APPROVE_CLOSE_WITH_FOLLOW_UPS
> **项目负责人**：大黄
> **项目负责人确认日期**：2026-07-19
> **Gate 3 生命周期状态**：CONDITIONALLY_CLOSED_BY_OWNER
> **PR #1 合并状态**：NOT_MERGED
> **Gate 4 状态**：NOT_STARTED
> **对应报告**：[M2-003C_Gate3_独立QA报告_V1.3.md](M2-003C_Gate3_独立QA报告_V1.3.md)
> **Review Closure**：[20260719_M2-003C_Gate3_Review_Closure_V1.3.md](20260719_M2-003C_Gate3_Review_Closure_V1.3.md)
> **Repository**：`dahuangbuchifou/Aurora`
> **Code baseline**：`44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1`

## 证据状态说明

- **仓库内只读核验**：Git 基线、workflow、任务卡与测试代码已核对；
- **婉儿独立核验**：E12-A 日志 ZIP SHA-256 已独立复算一致，CI、测试与 Coverage 已从原始日志核验；
- **辅助证据边界**：E12-B / E12-C PNG 未取得原文件独立复算；风险已被项目负责人接受，不阻塞 Closure；
- **独立验收**：状态为 `COMPLETED`，最终裁决为 `CONDITIONAL_PASS`，G3-1～G3-7 全部 PASS，BLOCKER 为 0；
- **治理状态**：Closure 转录校验为 `TRANSCRIPTION_CONFIRMED`；Closure 决定为 `CLOSE_WITH_FOLLOW_UPS`；项目负责人决定为 `APPROVE_CLOSE_WITH_FOLLOW_UPS`；
- **生命周期状态**：Gate 3 为 `CONDITIONALLY_CLOSED_BY_OWNER`；PR #1 为 `NOT_MERGED`；Gate 4 为 `NOT_STARTED`。

## E1 Git 基线与 merge-base 复核

| 字段 | 内容 |
|---|---|
| Evidence ID | E1 |
| 来源 | 本地 Git 只读命令 |
| Branch/Head | `feature/m2-003c-gate3-draft-persistence` / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 当前 main | `4691e53f8465c3e33ca378f27368b39915eb4200` |
| 当前 origin/main | `4691e53f8465c3e33ca378f27368b39915eb4200` |
| PR #1 base_sha | `4691e53f8465c3e33ca378f27368b39915eb4200` |
| 当前 merge-base | `4691e53f8465c3e33ca378f27368b39915eb4200` |
| 历史 Gate 2 merge commit | `f71aee47e6cb762e06793355aae4cc2eb00ba951` |
| 祖先关系 | `f71aee4...` 是 `4691e53...` 的历史祖先，不是本次 PR 的实际 merge-base |
| 差异裁决 | `RESOLVED / 草案原值正确` |
| 结果 | main、origin/main、PR base 与实际 merge-base 一致；该差异不再是 Closure 前置条件 |
| 核验状态 | 仓库内只读核验完成 |

## E2 PR 和 Head Commit

| 字段 | 内容 |
|---|---|
| Evidence ID | E2 |
| 来源 | 任务已确认 PR 元数据；本地 Git commit metadata |
| Branch/Commit | 当前 Head branch / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 结果 | PR `#1 feat: start M2-003C Gate 3 draft persistence`；Head 提交为 R4 keyword-only migration 修复 |
| 支持 | PR、Head、R4 修复基线 |
| 路径 | Git commit `44c875e`; PR URL 待人工补录 |
| SHA-256 | 不适用 |
| 核验状态 | Commit 已只读核验；PR URL 待补录 |

## E3 quality-gate Run #14 总结

| 字段 | 内容 |
|---|---|
| Evidence ID | E3 |
| 来源 | GitHub Actions Workflow Run/Job 元数据、CI summary 与婉儿原始日志核验 |
| Repository | `dahuangbuchifou/Aurora` |
| PR | `#1 feat: start M2-003C Gate 3 draft persistence` |
| Branch/Commit | `feature/m2-003c-gate3-draft-persistence` / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| Workflow / Run number | `quality-gate` / `14` |
| Run URL | https://github.com/dahuangbuchifou/Aurora/actions/runs/29635417889 |
| Run database ID | `29635417889` |
| Trigger | `pull_request / synchronize` |
| Run created_at / started_at | `2026-07-18T07:15:04Z` / `2026-07-18T07:15:04Z` |
| Run updated_at | `2026-07-18T07:15:39Z`；仅表示记录最后更新时间 |
| Run status / conclusion | `completed` / `success` |
| Job URL | https://github.com/dahuangbuchifou/Aurora/actions/runs/29635417889/job/88056793497 |
| Job database ID / name | `88056793497` / `gate (3.11)` |
| Runner group / name | `GitHub Actions` / `GitHub Actions 1000000040` |
| Job started_at / completed_at | `2026-07-18T07:15:06Z` / `2026-07-18T07:15:38Z` |
| Job status / conclusion | `completed` / `success` |
| OS / Python | `Ubuntu 24.04` / `3.11.15` |
| 结果 | `644 passed / 0 failed / 0 skipped`；总 Coverage `92.64%`、门槛 `90%`；pytest、coverage、frozen-assets、schema-diff、alembic-check 均为 `success` |
| 支持 | 正式 CI Checklist、G3 全量回归 |
| 外部证据 | E12-A；E12-B/E12-C 为辅助证据 |
| 核验状态 | 婉儿已从 E12-A 原始日志独立核验 |

时间均为 GitHub API 原始时间（UTC ISO-8601）。`updated_at` 不作为或改写为 `run_completed_at`。

## E4 普通 pytest 结果

| 字段 | 内容 |
|---|---|
| Evidence ID | E4 |
| 来源 | Run #14 `pytest` step；E12-A 原始日志 |
| Branch/Commit | 当前 Head branch / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 命令 | `python -m pytest -q --tb=short` |
| 结果 | `644 passed / 0 failed / 0 skipped`；`success` |
| 精确 duration | `4.72s` |
| collected / warnings | `pytest -q` 未输出 collected 行，不视为缺口；warnings 未显示不视为异常 |
| 支持 | 全量回归；G3-1～G3-7 |
| 路径 | [quality-gate.yml](../../.github/workflows/quality-gate.yml)；E12-A |
| 核验状态 | 婉儿已从原始日志独立核验 |

## E5 Coverage pytest 结果

| 字段 | 内容 |
|---|---|
| Evidence ID | E5 |
| 来源 | Run #14 `coverage` step；E12-A 原始日志 |
| Branch/Commit | 当前 Head branch / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 命令 | `python -m pytest --cov=aurora --cov-branch --cov-fail-under=90 -q` |
| 结果 | `644 passed / 0 failed / 0 skipped`；`success` |
| 精确 duration | `7.79s` |
| collected / warnings | `pytest -q` 未输出 collected 行，不视为缺口；warnings 未显示不视为异常 |
| 支持 | Coverage Checklist；G3-1～G3-7 |
| 路径 | [quality-gate.yml](../../.github/workflows/quality-gate.yml)；E12-A |
| 核验状态 | 婉儿已从原始日志独立核验 |

## E6 总 Coverage

| 字段 | 内容 |
|---|---|
| Evidence ID | E6 |
| 来源 | Run #14 E12-A 原始 coverage 日志 |
| Branch/Commit | 当前 Head branch / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 结果 | 精确总 Coverage `92.64%`；门槛 `90%`；coverage job `success` |
| 支持 | Coverage ≥90% Checklist |
| 路径 | `external://Aurora-Gate3-Evidence/CI/quality-gate_run-14_44c875e_logs.zip` |
| SHA-256 | `fb1993c94c80fa8c77b48561466452792d2d714e113944c780f56ef88f036711` |
| 核验状态 | 婉儿已从原始日志独立核验 |

## E7 Persistence 逐文件 Coverage

| 文件 | 历史值 | Run #14 当前值 | 独立核验 |
|---|---:|---:|---|
| `src/aurora/persistence/__init__.py` | 未记录 | 100% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/contracts.py` | 96%（`39a1b42`） | 96% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/draft_service.py` | 90%（`39edc4f`） | 92% | 历史 90%，当前 92% |
| `src/aurora/persistence/identity.py` | 100%（`39a1b42`） | 100% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/mapper.py` | 92%（`39edc4f`） | **88%** | **MAJOR-01；进入 Gate 4 前必须提升至 ≥90%** |
| `src/aurora/persistence/persistence_policy.py` | 未记录 | 100% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/source_graph.py` | 99%（`39a1b42`） | 99% | 婉儿已从原始日志核验 |
| `src/aurora/persistence/validation.py` | 98%（`39edc4f`） | 96% | 历史 98%，当前 96% |
| `src/aurora/workflow/draft_persistence.py` | 未记录 | 100% | 婉儿已从原始日志核验 |

| 字段 | 内容 |
|---|---|
| Evidence ID | E7 |
| 来源 | GitHub Actions `quality-gate` Run #14 E12-A 原始 coverage 日志 |
| Branch/Commit | `feature/m2-003c-gate3-draft-persistence` / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 正式门槛 | 全项目总 Coverage ≥90%；实际 92.64%，coverage job `success` |
| MAJOR-01 | `mapper.py` 当前 88%；不阻塞 Gate 3 Closure，进入 Gate 4 前必须通过增加边界测试提升至 ≥90%，不得删除防御性代码换取覆盖率 |
| 支持 | Coverage Checklist；精确逐文件证据 |
| 路径 | E12-A；E12-C 为辅助截图 |
| 核验状态 | 婉儿已从原始日志独立核验 |

## E8 frozen-assets

| 字段 | 内容 |
|---|---|
| Evidence ID | E8 |
| 来源 | Run #14 `frozen-assets` step；workflow 与 frozen manifest |
| Branch/Commit | 当前 Head / `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 结果 | `success` |
| 支持 | 冻结资产未被未授权修改 |
| 路径 | [quality-gate.yml](../../.github/workflows/quality-gate.yml)；[M2-003B_Gate2_frozen_assets.sha256](M2-003B_Gate2_frozen_assets.sha256)；E12-A |
| 核验状态 | 婉儿已从原始日志独立核验 |

## E9 schema-diff

| 字段 | 内容 |
|---|---|
| Evidence ID | E9 |
| 来源 | Run #14 `schema-diff` step；workflow |
| Base → Head | `4691e53f8465c3e33ca378f27368b39915eb4200` → `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 结果 | `success` |
| 支持 | 核心/应用 Schema 未发生 workflow 判定的未授权变化 |
| 路径 | [quality-gate.yml](../../.github/workflows/quality-gate.yml)；E12-A |
| 核验状态 | 婉儿已从原始日志独立核验 |

## E10 alembic-check

| 字段 | 内容 |
|---|---|
| Evidence ID | E10 |
| 来源 | Run #14 `alembic-check` step；workflow |
| Base → Head | `4691e53f8465c3e33ca378f27368b39915eb4200` → `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 结果 | `success` |
| 支持 | 未新增 workflow 判定为未授权的 Alembic revision |
| 路径 | [quality-gate.yml](../../.github/workflows/quality-gate.yml)；E12-A |
| 核验状态 | 婉儿已从原始日志独立核验 |

## E11 G3-1～G3-7 测试映射与独立裁决

| Gate / Evidence ID | 关键测试与断言语义 | 路径 | 婉儿裁决 |
|---|---|---|---|
| G3-1 / E11-G3-1 | `test_fault_injection_rollback`、`test_forced_mid_transaction_failure`；失败后业务对象为 0，FAILED ProcessingRun 保留 | [Gate 3 integration](../../tests/integration/test_m2_003c_gate3_draft_persistence.py)、[R3-S06](../../tests/unit/persistence/test_draft_service_r3s06.py) | PASS |
| G3-2 / E11-G3-2 | `test_no_fact`；数据库 `ObjectType.FACT` 记录数为 0 | [Gate 3 integration](../../tests/integration/test_m2_003c_gate3_draft_persistence.py) | PASS |
| G3-3 / E11-G3-3 | `test_claims_under_review`；持久化 Claim 为 `under_review` | [Gate 3 integration](../../tests/integration/test_m2_003c_gate3_draft_persistence.py) | PASS |
| G3-4 / E11-G3-4 | `test_rejected_not_persisted`：rejected 不进入持久化记录；`test_candidate_in_both_accepted_and_rejected`：交集触发 `PreflightError`；`test_accepted_not_found_in_candidates`：缺失 accepted ID 触发 `PreflightError`。三组断言共同支持悬空 Candidate 引用为零，不仅依赖测试名称 | [Gate 3 integration](../../tests/integration/test_m2_003c_gate3_draft_persistence.py)、[validation coverage](../../tests/unit/persistence/test_validation_coverage.py) | PASS |
| G3-5 / E11-G3-5 | `test_four_class_full_persistence` 与 Evidence/DataPoint/Claim unresolved-reference 负向测试 | [R3-S06](../../tests/unit/persistence/test_draft_service_r3s06.py)、[validation coverage](../../tests/unit/persistence/test_validation_coverage.py) | PASS |
| G3-6 / E11-G3-6 | `test_same_bundle_twice_no_duplicates`、`test_cross_session_idempotent`、`test_idempotent_same_bundle_twice`；二次运行零新增 | [Gate 3 integration](../../tests/integration/test_m2_003c_gate3_draft_persistence.py) | PASS |
| G3-7 / E11-G3-7 | Provider 越权检测、`test_rejected_not_persisted`、`test_all_adversarial_cases[provider_independence_override]`、Gate 2 对抗测试构成组合证据链 | [Gate 2 safety](../../tests/integration/test_m2_003b_gate2_cognitive_safety.py)、[SafetyGate](../../tests/unit/test_safety_gate.py)、[fixture provider](../../tests/unit/test_fixture_provider.py)、[Gate 3 integration](../../tests/integration/test_m2_003c_gate3_draft_persistence.py) | PASS |

### E11-G3-7 证据边界

- 组合证据包括 Provider 越权检测、rejected candidate 不持久化、provider independence override 路径及 Gate 2 相关对抗测试；
- 尚未发现单一测试直接扫描最终数据库 payload，并一次性断言所有 Provider 越权字段为零；
- 婉儿裁决当前组合证据足以支持 G3-7 PASS；该建议登记为 RECOMMENDATION-01，不阻塞 Gate 3 Closure，也不是 Gate 4 强制前置。

## E12 外部证据

| Evidence ID | Artifact basename | external:// 逻辑路径 | SHA-256 | 独立核验状态 |
|---|---|---|---|---|
| E12-A | `quality-gate_run-14_44c875e_logs.zip` | `external://Aurora-Gate3-Evidence/CI/quality-gate_run-14_44c875e_logs.zip` | `fb1993c94c80fa8c77b48561466452792d2d714e113944c780f56ef88f036711` | 婉儿已独立复算一致；CI、测试、Coverage 已从原始日志核验 |
| E12-B | `quality-gate_run-14_summary.png` | `external://Aurora-Gate3-Evidence/CI/quality-gate_run-14_summary.png` | `cd85b49b1eeb24a8708b093ad0bb262f24edd00bbcc7e05f38d1e97fee55de35` | 婉儿未取得 PNG 原文件独立复算；辅助证据，不阻塞 Closure |
| E12-C | `quality-gate_run-14_coverage.png` | `external://Aurora-Gate3-Evidence/CI/quality-gate_run-14_coverage.png` | `25bbcc7fb637e902e0fae98b314a9ac8abba37b4ed0f4aefdfdd15ecd8e658ed` | 婉儿未取得 PNG 原文件独立复算；Coverage 已从 E12-A 确认，不阻塞 Closure |

- 来源：GitHub Actions `quality-gate` Run #14；Head `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1`。
- 仓库内清单：[M2-003C_Gate3_external_evidence.sha256](M2-003C_Gate3_external_evidence.sha256)。
- 三项证据均保存在仓库外；截图不替代 E12-A 原始日志。

## E13 问题分级与处置

| ID | 级别 | 问题 | 处置与 Closure 影响 |
|---|---|---|---|
| MAJOR-01 | MAJOR | `mapper.py` 当前 Coverage 88% | 对应治理事项 `OPT-072`；状态 `APPROVED / 待执行`；不阻塞 Gate 3 Closure，但阻塞 Gate 4 启动；进入 Gate 4 前必须通过增加边界测试提升至 ≥90%，不得删除防御性代码换取覆盖率 |
| MINOR-01 | MINOR | E12-B / E12-C PNG 未由婉儿取得原文件独立复算 | E12-A 日志 ZIP 已独立复算一致；测试结果和 Coverage 已从原始日志核验；风险已被项目负责人接受；不阻塞 Closure |
| RECOMMENDATION-01 | RECOMMENDATION | 建议增加 G3-7 最终数据库 payload 全字段扫描测试 | 对应治理事项 `OPT-073`；G3-7 当前为 PASS，组合证据已被独立 QA 认定充分；属于建议补强，不阻塞 Gate 3 Closure，也不是 Gate 4 强制前置 |
| RESOLVED-01 | RESOLVED | merge-base 核验差异 | 正确 merge-base 为 `4691e53f8465c3e33ca378f27368b39915eb4200`；`f71aee47e6cb762e06793355aae4cc2eb00ba951` 是历史祖先；草案原记录正确，不再是 Closure 前置条件 |

| 分类 | 数量 |
|---|---:|
| BLOCKER | 0 |
| MAJOR | 1 |
| MINOR | 1 |
| RECOMMENDATION | 1 |
| RESOLVED | 1 |

## E14 婉儿独立验收裁决

| 字段 | 结论 |
|---|---|
| Evidence ID | E14 |
| 独立验证人 | 婉儿 |
| 验收日期/时区 | 2026-07-18 / Asia/Shanghai（UTC+08:00） |
| 独立验收状态 | `COMPLETED` |
| 最终裁决 | `CONDITIONAL_PASS` |
| Closure 转录校验 | `TRANSCRIPTION_CONFIRMED` |
| 独立 QA 建议关闭方式 | `CLOSE_WITH_FOLLOW_UPS` |
| G3-1 | PASS |
| G3-2 | PASS |
| G3-3 | PASS |
| G3-4 | PASS |
| G3-5 | PASS |
| G3-6 | PASS |
| G3-7 | PASS |
| BLOCKER | 0 |
| MAJOR | 1 项（MAJOR-01） |
| MINOR | 1 项（MINOR-01） |
| RECOMMENDATION | 1 项（RECOMMENDATION-01） |
| RESOLVED | 1 项（RESOLVED-01） |
| pytest collected 行 | `pytest -q` 未输出，不视为缺口 |
| warnings | 未显示，不视为异常 |
| E12-A | SHA-256 独立复算一致；日志结果独立核验 |
| E12-B / E12-C | 未取得 PNG 原文件独立复算；不阻塞 |
| 项目负责人 | 大黄 |
| 项目负责人确认日期 | `2026-07-19` |
| 项目负责人决定 | `APPROVE_CLOSE_WITH_FOLLOW_UPS` |
| Closure 决定 | `CLOSE_WITH_FOLLOW_UPS` |
| Gate 3 生命周期状态 | `CONDITIONALLY_CLOSED_BY_OWNER` |
| PR #1 合并状态 | `NOT_MERGED` |
| Gate 4 状态 | `NOT_STARTED` |

## 治理文档引用与提交状态

### 仓库内治理文档

- [独立 QA 报告](M2-003C_Gate3_独立QA报告_V1.3.md)
- [Review Closure](20260719_M2-003C_Gate3_Review_Closure_V1.3.md)
- [外部证据 SHA-256 清单](M2-003C_Gate3_external_evidence.sha256)
- [项目总进度与资源看板](../00_project/03_Aurora_项目总进度与资源看板_V1.7.md)
- [待优化事项清单](../00_project/05_Aurora_待优化事项清单_V1.7.md)
- [Gate 3 正式任务卡](../01_requirements/16_M2-003C_Gate3_草案持久化验证_任务卡_V1.0.md)
- [根 CHANGELOG](../../CHANGELOG.md)
- [根 README](../../README.md)

以上路径均以 `docs/qa/` 为起点，并已按仓库实际层级登记。

### 当前提交与后续状态

| 字段 | 当前状态 |
|---|---|
| Gate 3 代码证据基线 | `44c875e632c4f12dcc67dbbf47ef4ef6180ddaf1` |
| 当前治理分支 HEAD | 以仓库当前 Git HEAD 为准 |
| 当前 Closure / QA / Governance 文档 | 已纳入本地治理提交，尚未推送 |
| 本地治理提交状态 | 已创建 |
| 提交 SHA | 以仓库当前 Git HEAD 为准 |
| Git push | 尚未执行 |
| 新一轮 GitHub Actions | 尚未执行 |
| PR #1 | `NOT_MERGED` |
| 大黄本地复验 | 尚未执行 |
| Gate 4 | `NOT_STARTED` |
| Gate 4 启动前置 | `mapper.py` Coverage ≥90% |

`mapper.py` Coverage ≥90% 是唯一 Gate 4 强制前置。G3-7 最终数据库 payload 全字段扫描测试保持为 RECOMMENDATION-01 / OPT-073，不是强制前置。Evidence 的治理同步不改变 PR 与 Gate 4 的未执行状态，未结事项继续保持开放。

## 独立验收结论

~~~text
CONDITIONAL_PASS
~~~

该独立裁决支持 Closure 决定 `CLOSE_WITH_FOLLOW_UPS`。项目负责人已作出 `APPROVE_CLOSE_WITH_FOLLOW_UPS` 决定，Gate 3 生命周期状态为 `CONDITIONALLY_CLOSED_BY_OWNER`。Evidence E1～E14 已建立索引；PR #1 仍为 `NOT_MERGED`，Gate 4 仍为 `NOT_STARTED`。
