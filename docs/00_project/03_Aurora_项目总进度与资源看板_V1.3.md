# Aurora 项目总进度与资源看板 V1.3

> 更新：2026-07-13 13:40 CST  
> 当前基线：M2-003B Gate 1 PASS，已 merge main (`88c5892`)

---

## 📐 协作规则（大黄 2026-07-13 定）

| 规则 | 说明 |
|---|---|
| 前置标准 | 每阶段开始前，婉儿+大G co-author 验收 checklist |
| 回复规范 | 大G 任务需逐条回答 checklist，不得跳过 |
| 角色定义 | 大G = 技术负责人（代码+设计），婉儿 = 方向监控+细节检查（防跑偏） |
| Review 上限 | 每部分最多两轮，未解决问题进 `05_待优化事项清单`，大节点后统一修正 |

---

## 1. 总体进度

```text
总体工程进度：42%
████████░░░░░░░░░░░░ 42%
```

| 阶段 | 权重 | 完成度 | 加权贡献 | 状态 |
|---|---:|---:|---:|---|
| M0 项目基线 | 10% | 100% | 10% | ✅ 完成 |
| M1 对象模型与知识标准 | 20% | 100% | 20% | ✅ QA_PASSED |
| M2 MVP认知闭环 | 35% | 34% | 12% | 🔄 进行中 |
| M3 个人稳定版 | 25% | 0% | 0% | ⏳ 未开始 |
| M4 平台化探索 | 10% | 0% | 0% | ⏳ 未开始 |

**M2 子项进度：**

| 子阶段 | 状态 | 说明 |
|---|---|---|
| M2-001 离线统一输入与内容单元化 | ✅ CLOSED | |
| M2-002 解析与定位基础设施 | ✅ CLOSED | |
| M2-003A 黄金期望集合与 Gate 0 | ✅ CLOSED | Gate 0 35/35 FINAL_PASS |
| M2-003B 真实垂直切片与 Gate 1 | ✅ PASS | 345/345 tests, 96% coverage, merge main |
| Gate 2 认知安全验证 | 🔜 READY | 下一节点 |

---

## 2. Issue 状态

```text
M1-001：CLOSED
M1-002：CLOSED / QA_PASSED
M1-003A：CLOSED
M1-003B：CLOSED / QA_PASSED
M1 Exit Review：DRAFT

M2-001：CLOSED
M2-002：CLOSED
M2-003A：CLOSED / Gate 0 FINAL_PASS
M2-003B：Gate 1 PASS / Gate 2 READY
```

---

## 3. 最近完成（M2-003B Gate 1）

**Commit**: `88c5892` (merge to main)

- ContextWindow V2：规范化 JSON Hash（含 document_id / unit_id / unit_type / locator / text_sha256）
- FixtureProvider：从独立 provider_responses/ 读取，三类数据（Source/Provider/Expected）完全分离
- QuoteGate V2：NFKC literal 子串 + token_set 100%（仅 TABLE/TABLE_ROW）
- ReviewBundle V2：不可变 frozen dataclass + 防篡改 bundle_sha256
- 三个真实垂直切片：Case A HTML / Case B Transcript / Case C PDF
- Gate 1 七项硬门禁 27/27 PASS（每项×3案例）
- 支撑性工程门禁 13/13 PASS
- 10×3 确定性验证全部一致
- 全量 345/345 tests · 覆盖率 96%
- V1.1 核心 Schema 零变更 · 零新增 Alembic

**独立 QA 报告**: `docs/qa/M2-003B_Gate1_独立QA报告.md`

---

## 4. 当前阻塞

无技术阻塞。

**流程状态：**

```text
大G Gate 1 实现 ✅ (d1dc91b)
→ 婉儿独立 QA ✅ (5778030 / adfd593)
→ 大黄确认 merge ✅ (88c5892)
→ Gate 2 认知安全验证 ← 当前
```

---

## 5. 当前资源

已具备：

- Alibaba Cloud Linux
- Python 3.11.13 · SQLite 3.26+
- GitHub 公开仓库 `dahuangbuchifou/Aurora`
- 三个真实案例 Material + Provider Fixture + Expected Results
- 大G 技术负责人 + 婉儿 QA 官流程
- 冻结 ContentUnit 快照、Provider 独立 Fixture、345 测试用例
- 协作规则 V1.0（前置标准 / 回复规范 / 角色定义 / 两轮封顶）

当前不需要：

- GPU · Docker · 向量数据库 · 商业 LLM API · Web 前端 · 新服务器

---

## 6. 下一步

### Gate 2 认知安全验证（属于 M2-003B）

范围待大G 出 Issue。预计包含：
- 污染数据测试（幻觉/冲突/跨文档混淆）
- Entity 误关联检测
- Fact 过早晋升检测
- 全量回归（345 测试不变）

### 看板维护

- 婉儿在每次节点闭合后更新本文件和 `05_待优化事项清单`
- 大G 产出的 OPT 由婉儿归集到清单

---

_婉儿维护 · 每次节点闭合更新_ 🎋
