# Aurora 待优化事项清单 V1.7

> 更新：2026-07-13 13:40 CST  
> 合并 M2-003A/B 全部 OPT（大G + 婉儿 QA）

---

## 📐 优化规则（大黄 2026-07-13 定）

1. 每个阶段 review 最多两轮，未解决问题放入本清单
2. 大节点完成后统一修正，不卡当前阶段
3. 本清单由婉儿维护，每次节点闭合时更新

---

## 0. M1 阶段

| ID | 等级 | 项目 | 状态 |
|---|---|---|---|
| OPT-001 | MAJOR | DataPoint 财务和测量口径不足 | DONE |
| OPT-002 | MAJOR | independence_group 无程序化去重规则 | DONE |
| OPT-003 | MAJOR | Claim 缺少分析维度 | DONE |
| OPT-004 | MAJOR | Provenance 派生关系不够结构化 | DONE |
| OPT-005 | MAJOR | Claim 缺少原子性规范 | DONE |
| OPT-006 | MINOR | SQLite 锁等待策略未标准化 | DONE |
| OPT-007 | MINOR | schema_registry 与 session 测试不足 | DONE |
| OPT-014 | MAJOR | Evidence Role 语义容易混淆 | DONE |
| OPT-015 | MINOR | V1.0 到 V1.1 兼容策略未成文 | DONE |
| OPT-016 | MINOR | 非依赖 processing_run_id 产生 dangling 噪音 | DONE |
| OPT-017 | — | — | DONE |
| OPT-018 | — | — | DONE |
| OPT-019 | — | — | DONE |
| OPT-020 | — | — | DONE |

---

## 1. M2-001

```text
OPT-021：DONE
OPT-022：DONE
OPT-023：DONE
OPT-024：DONE
```

---

## 2. M2-002 实现项

| ID | 等级 | 项目 | 状态 |
|---|---|---|---|
| OPT-031 | MAJOR | URL抓取SSRF防护 | IMPLEMENTED_PENDING_QA |
| OPT-032 | MAJOR | PDF表格不确定性 | IMPLEMENTED_PENDING_QA |
| OPT-034 | MAJOR | Parser配置进入幂等键 | IMPLEMENTED_PENDING_QA |

---

## 3. M2-003A (Gate 0) — 大G产生

| ID | 等级 | 项目 | 状态 | 说明 |
|---|---|---|---|---|
| OPT-052 | — | — | DONE | Gate 0 V1.2 实装 |
| OPT-053 | — | — | DONE | |
| OPT-054 | — | — | DONE | |
| OPT-055 | — | — | DONE | |
| OPT-056 | — | — | DONE | |
| OPT-057 | — | — | DONE | |
| OPT-058 | — | — | DONE | |

---

## 4. M2-003B (Gate 1) — 大G产生

| ID | 等级 | 项目 | 状态 | 说明 |
|---|---|---|---|---|
| OPT-061 | MAJOR | ContextWindow 规范化 Hash | IN_PROGRESS | 大G Gate 1 已实现 V2 Hash，待最终确认 |
| OPT-062 | MAJOR | 真实 Parser 链与冻结快照谱系核对 | IN_PROGRESS | 大G Gate 1 三案例已用真实 Parser |
| OPT-063 | MAJOR | Git 基线与比较基线混淆 | IN_PROGRESS | 婉儿已修正：父基线 f0627d9 / 代码比较基线 78d8b90 |
| OPT-064 | BLOCKER | Gate 0 冻结资产被后续阶段修改 | ✅ CLOSED | 婉儿 QA Pass：8/8 资产 Hash 未修改 |

---

## 5. M2-003B (Gate 1) — 婉儿 QA 发现

| ID | 等级 | 项目 | 状态 | 说明 |
|---|---|---|---|---|
| OPT-065 | LOW | `gate1_check.py` ExtractionError 不支持排序 | OPEN | 旧版 Checker 与新 ReviewBundle API 不兼容；不影响集成测试 38/38 PASS |
| OPT-066 | LOW | `review_decision.py` 覆盖率 89%（低于 90%） | OPEN | 该模块不在 M2-003B 变更范围，后续统一补齐 |

---

## 6. 延期项（跨阶段）

| ID | 等级 | 项目 | 状态 | 目标 |
|---|---|---|---|---|
| OPT-025 | ENHANCEMENT | 完整 CommonMark | DEFERRED | 后续 |
| OPT-026 | ENHANCEMENT | 单表 JSON 查询性能 | DEFERRED | M3 |
| OPT-027 | MINOR | 并发导入竞争 | DEFERRED | M2-005/M3 |
| OPT-028 | ENHANCEMENT | PDF bbox Locator | DEFERRED | 独立 Schema 评审 |
| OPT-029 | ENHANCEMENT | JavaScript 动态网页 | DEFERRED | M3 |
| OPT-030 | MAJOR | 扫描 PDF 与 OCR | DEFERRED_BY_SCOPE | M3/M2-005 评审 |
| OPT-033 | MINOR | 字幕 Cue 粒度过细 | DEFERRED | M2-003 |
| OPT-035 | MINOR | PDF 文本与表格重复消除 | DEFERRED | 积累真实 PDF 后优化 |
| OPT-036 | MINOR | 网页字符集高级识别 | DEFERRED | M2-005 或真实案例触发 |
| OPT-037 | MAJOR | HTML Locator 快照持久化策略 | PLANNED | M2-005 输出与归档评审 |

---

## 7. 开放项汇总

| ID | 等级 | 项目 | 解决节点 |
|---|---|---|---|
| OPT-061 | MAJOR | ContextWindow 规范化 Hash | M2-003B Gate 1 最终确认 |
| OPT-062 | MAJOR | 真实 Parser 链与快照谱系核对 | M2-003B Gate 1 最终确认 |
| OPT-063 | MAJOR | Git 基线与比较基线混淆 | M2-003B Gate 1 最终确认 |
| OPT-065 | LOW | gate1_check.py Error 排序 | 后续统一修正 |
| OPT-066 | LOW | review_decision.py 覆盖率 | 后续统一修正 |
| OPT-031~034 | MAJOR | M2-002 QA 待验证 | M2-002 收尾 |

---

_婉儿维护 · 每次节点闭合更新_ 🎋
