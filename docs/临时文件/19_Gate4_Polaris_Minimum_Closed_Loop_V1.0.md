# Gate 4 北极星最小闭环 Design Spec V1.0

> **状态**：DRAFT（待三方确认后转为 DESIGN_APPROVED）  
> **冻结基线**：main @ `c94e8dc1f6ce715b4571805a6039eaa7c401254e`  
> **目标**：Aurora 第一条完整端到端链路 — 从资料输入到 Markdown 研究简报输出  
> **管辖范围**：本 Spec 为 Gate 4 的设计契约，不是实现约束

---

## 0. 设计原则

1. **先跑通，再跑好。** 第一条链路用最简方案 — FixtureProvider（预制数据）、模板化输出、单主题硬分组。
2. **每一段可独立验证。** 链路拆分为 4 个模块，每个模块有自己的单元测试、自己的退出标准。
3. **输出必须可评价、可回溯、可复用。** 这是北极星闭环的成功定义。
4. **不修改已冻结资产。** 核心 Schema V1.1、Alembic、mapper.py 契约、ReviewBundle 格式均不改变。

---

## 1. 端到端链路定义

```
① 资料输入
   aurora-ingest pdf → ContentUnit
   （已有 M2-001 + M2-002）

② 候选提取
   FixtureProvider → ExtractionEnvelope → Candidate
   （已有 M2-003B）

③ 草案持久化
   mapper.py → draft_service.py → Entity/DataPoint/Claim/Evidence in SQLite
   （已有 M2-003C CLOSED）

④ ─── Gate 4 新增 ───

⑤ 知识聚合
   knowledge_assembler: Core Objects → KnowledgeObject
   【新模块：src/aurora/knowledge/assembler.py】

⑥ 观点矩阵
   opinion_matrix: KnowledgeObject.claims → 正反观点对比表
   【新模块：src/aurora/knowledge/opinion_matrix.py】

⑦ 观点草案
   opinion_drafter: 正反矩阵 → PersonalOpinion Draft
   【新模块：src/aurora/brief/drafter.py】

⑧ 简报输出
   brief_exporter: KnowledgeObject + PersonalOpinion → Markdown
   【新模块：src/aurora/brief/exporter.py】

⑨ CLI 入口
   aurora-brief generate → 一键执行 ⑤⑥⑦⑧
   【新模块：src/aurora/cli/brief.py】
```

---

## 2. 模块详细设计

### 2.1 knowledge_assembler — 知识聚合器

**文件：** `src/aurora/knowledge/assembler.py`

**输入：**
```python
assemble_knowledge(
    run_id: str,
    entities: list[Entity],
    data_points: list[DataPoint],
    claims: list[Claim],
    evidence_list: list[Evidence],
    topic: str,           # 聚合主题（最低可行：固定字符串）
) -> KnowledgeObject
```

**编排逻辑：**
1. 创建一个 `KnowledgeObject`，`knowledge_type = KnowledgeType.TOPIC_SUMMARY`
2. 将输入的所有 Entity ID 写入 `related_entity_ids`
3. 将输入的所有 Fact/DataPoint/Claim/Evidence ID 写入对应字段
4. 从 Draft 中提取 `title`（取第一个 Claim 的 statement 前 80 字符）
5. `knowledge_status = KnowledgeStatus.DRAFT`
6. 持久化到 object_records（复用现有 Repository.write）

**最低可行策略：**
- 单 KnowledgeObject 生成（不拆分多主题）
- 主题由 CLI 参数 `--topic` 指定
- 聚合不做去重/排序/优先级判断

**退出标准：**
```
K1: KnowledgeObject 能成功写入 SQLite 并返回 ko_* ID
K2: KnowledgeObject.related_entity_ids 包含所有输入 Entity ID
K3: KnowledgeObject.fact_ids/data_point_ids/claim_ids/evidence_ids 包含所有输入 Core Object ID
K4: KnowledgeObject.knowledge_status == DRAFT
K5: 使用现有 Repository API，不引入新的 DB 访问方式
```

---

### 2.2 opinion_matrix — 正反观点矩阵

**文件：** `src/aurora/knowledge/opinion_matrix.py`

**输入：**
```python
build_matrix(
    knowledge_object: KnowledgeObject,
    claims: list[Claim],
    evidence_list: list[Evidence],
) -> OpinionMatrix
```

**OpinionMatrix 数据结构（Pydantic）：**
```python
class MatrixEntry(BaseModel):
    asserted_by: str              # 断言方
    statement: str                # 主张内容
    claim_id: str                 # 追溯 Claim ID
    claim_type: ClaimType
    supporting_evidence: list[str]  # 支持该主张的 Evidence ID
    opposing_evidence: list[str]    # 反对该主张的 Evidence ID

class OpinionMatrix(BaseModel):
    topic: str
    entries: list[MatrixEntry]
```

**编排逻辑：**
1. 遍历 `claims`，为每个 Claim 创建 `MatrixEntry`
2. 将 `evidence_list` 按 `target_object_id` 匹配到对应的 Claim
3. 将 `EvidenceRole.SUPPORT` 归入 `supporting_evidence`
4. 将 `EvidenceRole.REFUTE` 归入 `opposing_evidence`
5. 按 `asserted_by` 聚类（同一说法的不同断言方放在一起）

**最低可行策略：**
- 不做语义聚类/自动分类
- 不检测矛盾
- 不生成统计数据

**退出标准：**
```
M1: 所有 Claim 都有对应的 MatrixEntry
M2: SUPPORT/REFUTE evidence 正确归属
M3: OpinionMatrix 可序列化/反序列化
M4: 空输入 → 空 entries（不抛异常）
```

---

### 2.3 opinion_drafter — 观点草案生成

**文件：** `src/aurora/brief/drafter.py`

**输入：**
```python
draft_opinion(
    knowledge_object: KnowledgeObject,
    matrix: OpinionMatrix,
) -> PersonalOpinion
```

**编排逻辑：**
1. 创建 `PersonalOpinion`，`opinion_status = OpinionStatus.DRAFT`
2. `confirmed_by_user = False`
3. 从 matrix 中提取：
   - `supporting_ids` — 所有标记为 SUPPORT 的 Evidence ID
   - `counter_evidence_ids` — 所有标记为 REFUTE 的 Evidence ID
4. `key_assumptions` — 使用**固定规则模板**生成（例如："基于已提取的 N 条主张和 M 条证据"）
5. `unknown_variables` — 空列表（最低可行不做自动推断）
6. `invalidation_conditions` — 空列表
7. 持久化到 object_records

**最低可行策略：**
- 模板化 Draft，不是 AI 生成
- key_assumptions 用规则模板，不做语义提取
- 后续 M3/M4 再接入 LLM 生成

**退出标准：**
```
D1: PersonalOpinion 能成功写入 SQLite 并返回 opn_* ID
D2: opinion_status == DRAFT
D3: confirmed_by_user == False
D4: supporting_ids / counter_evidence_ids 来自 opinion_matrix 输入
D5: validate_activation() 对 DRAFT 状态不报错（DRAFT 允许字段为空）
```

---

### 2.4 brief_exporter — Markdown 简报输出

**文件：** `src/aurora/brief/exporter.py`

**输入：**
```python
export_brief(
    knowledge_object: KnowledgeObject,
    opinion: PersonalOpinion,
    entities: list[Entity],
    claims: list[Claim],
    evidence_list: list[Evidence],
    matrix: OpinionMatrix,
    output_path: Path,
) -> Path
```

**输出格式（Markdown 模板）：**
```markdown
# Aurora 研究简报

**主题：** {topic}
**生成时间：** {timestamp}
**处理 Run ID：** {run_id}

---

## 1. 知识概览

- 实体：{N} 个
- 数据点：{M} 个
- 主张：{P} 条
- 证据：{Q} 条

## 2. 关键实体

| 名称 | 类型 | 来源 |
|------|------|------|
{entities table}

## 3. 正反观点

### 支持性观点

{for each SUPPORT}
- **{asserted_by}**：{statement}
  - 证据：[{evidence_id}](target_link)
{end}

### 反对性观点 / 风险提示

{for each REFUTE}
- **{asserted_by}**：{statement}
  - 证据：[{evidence_id}](target_link)
{end}

## 4. 数据点摘要

{data_points table}

## 5. 个人观点草案

**状态：** DRAFT（未经人工确认）

**支持依据：** {N} 条证据
**反对依据：** {M} 条证据
**关键假设：** {key_assumptions}

---

_本简报由 Aurora 自动生成。所有结论可回溯至原始文档。_
```

**退出标准：**
```
E1: 输出有效的 Markdown 文件到指定路径
E2: 包含所有 6 个章节
E3: 每一条 Claim 可追溯到 Claim ID
E4: 每一条 Evidence 可追溯到 Evidence ID
E5: Markdown 文件无语法错误（可用任何标准渲染器打开）
```

---

### 2.5 CLI 入口

**文件：** `src/aurora/cli/brief.py`

**命令：**
```bash
aurora-brief generate <run_id> \
  --topic "半导体行业" \
  --output-dir ./outputs/
```

**编排流程：**
1. 读取 `run_id` 对应的 ProcessingRun
2. 加载该 Run 下的所有 Draft 对象（Entity / DataPoint / Claim / Evidence）
3. 依次调用：`assembler → matrix → drafter → exporter`
4. 输出文件到 `--output-dir`
5. 打印简报路径和摘要统计

**退出标准：**
```
C1: aurora-brief generate 能成功执行端到端
C2: 输出文件在指定目录
C3: 打印摘要统计（Entity/DataPoint/Claim/Evidence 数量）
C4: --help 输出完整的参数说明
```

---

## 3. 测试要求

### 3.1 单元测试

每个新模块独立测试，不依赖 SQLite 文件：

| 模块 | 最低测试数 | 关键场景 |
|------|:--:|------|
| `assembler.py` | 5 | 正常聚合 · 空输入 · 单对象 · 多对象 · status=DRAFT |
| `opinion_matrix.py` | 5 | 正常矩阵 · SUPPORT归属 · REFUTE归属 · 多asserted_by · 空输入 |
| `drafter.py` | 4 | 正常Draft · 空matrix · status=DRAFT · validate不报错 |
| `exporter.py` | 4 | 完整输出 · 空Claims · 空Evidence · 文件名合法 |
| `brief.py` (CLI) | 3 | 端到端 · --help · 缺少参数报错 |

### 3.2 集成测试

| 场景 | 描述 |
|------|------|
| 端到端 | 从 FixtureProvider 输入 → 完整 Markdown 输出 |
| 空集输入 | 0 Entity / 0 Claim → 输出不崩溃，简报说明"无可用数据" |
| Case C 年报 | 使用 M1-002 中芯国际年报 PDF 的 fixture，走完整链路 |

### 3.3 端到端测试契约

端到端测试是一个独立的 pytest 函数，测试整个 Gate 4 链路：

```python
def test_gate4_end_to_end_case_c(tmp_path):
    """M1-002 Case C (中芯国际年报) → 完整 Markdown 简报."""
```

---

## 4. 门禁条件（Gate 4 Exit）

| 编号 | 门禁 | 判定方法 |
|------|------|----------|
| G4-1 | `aurora-brief generate` 端到端可执行 | CLI 测试 |
| G4-2 | 输出 Markdown 包含全部 6 章节 | 解析测试 |
| G4-3 | 所有 Claim/Evidence 可追溯 ID | 正则匹配 |
| G4-4 | 无自动创建 Fact（由 Brief 流程触发） | 断言 |
| G4-5 | Opinion 状态为 DRAFT，未确认 | 断言 |
| G4-6 | 3 个 M1-002 案例全部通过端到端 | 参数化测试 |
| G4-7 | **不修改 mapper.py 或 draft_service.py 核心逻辑** | git diff |
| G4-8 | 完整回归 ≥ 648 tests / 0 failures | CI |
| G4-9 | Total Coverage ≥ 92.90% | CI |
| G4-10 | 六项 CI 门禁全部 SUCCESS | CI |

---

## 5. 文件所有权边界

### Gate 4 独占修改（新模块）

```
src/aurora/knowledge/
├── __init__.py
├── assembler.py           ← Gate 4
├── opinion_matrix.py       ← Gate 4
└── models.py               ← Gate 4（OpinionMatrix Pydantic DTO）

src/aurora/brief/
├── __init__.py
├── drafter.py              ← Gate 4
└── exporter.py             ← Gate 4

src/aurora/cli/
└── brief.py                ← Gate 4

tests/unit/knowledge/
├── test_assembler.py
└── test_opinion_matrix.py

tests/unit/brief/
├── test_drafter.py
└── test_exporter.py

tests/e2e/
└── test_gate4_e2e.py
```

### Gate 4 只读消耗（已冻结）

```
src/aurora/persistence/    ← 只读，不修改
src/aurora/extraction/     ← 只读，不修改
src/aurora/core/models/    ← 只读，不修改（可读取 KnowledgeObject/PersonalOpinion）
src/aurora/workflow/       ← 只读，不修改
```

### OPT-073 独占（并行，不冲突）

```
tests/unit/persistence/    ← OPT-073 补充测试
tests/integration/         ← OPT-073 并发测试
```

---

## 6. 依赖图

```text
Gate 4 依赖：
  M1 Core Models       ✅ CLOSED（KnowledgeObject / PersonalOpinion 已就绪）
  M2-001 ContentUnit   ✅ CLOSED
  M2-002 Parsers       ✅ CLOSED
  M2-003B FixtureProvider ✅ CLOSED
  M2-003C Persistence  ✅ CLOSED（c94e8dc1...）
  OPT-073（M2.1）      ❌ 不依赖（完全并行）

Gate 4 不依赖：
  真实 AI Provider     → M3
  远程 API             → M3
  Web UI               → 未排期
  Gate 5（真实Provider）→ M2-003D，不阻塞
```

---

## 7. 非目标（不算失败）

```text
✗ AI 生成的报告文案（V1 用规则模板，V2 再接入 LLM）
✗ 多 KnowledgeObject 自动聚合
✗ 观点演化/版本对比
✗ HTML / PDF 输出（仅 Markdown）
✗ 实时增量更新
✗ 多语言支持
✗ PersonalOpinion 自动确认（必须 DRAFT，等待人工）
✗ Semantic Clustering / NLP
```

---

## 8. 成功定义（北极星闭环达标）

> **大黄从 `tests/fixtures/m2_003/materials/` 中任选一个测试案例，执行：**
>
> ```bash
> aurora-brief generate <run_id> --topic "半导体行业" --output-dir ./outputs/
> ```
>
> **得到一份 Markdown 简报文件，满足：**
>
> 1. **可评价** — 每条结论有 `claim_id` / `evidence_id`，可以判断对错
> 2. **可回溯** — 可以追溯到原始文档的特定 ContentUnit 位置
> 3. **可复用** — 输出的 Markdown 可以作为后续研究的起点

这就是北极星闭环。不是花哨的 AI 生成，不是精美 UI——是**一条能从真实文件走到可读简报的完整链路**。

---

## 9. 启动条件

| 条件 | 状态 |
|------|:--:|
| M2-003C CLOSED | ✅ |
| main HEAD 冻结基线确认 | ✅ `c94e8dc1f...` |
| OPT-073 不阻塞 Gate 4 的治理确认 | ✅ 三方已确认 |
| 文件所有权划分确认 | ✅ 本 Spec §5 |
| 大黄对北极星定义的批准 | ⏳ 待确认 |

---

## 10. 里程碑

```text
Design Spec APPROVED → 实施 Phase 1 (assembler + matrix)
                     → 实施 Phase 2 (drafter + exporter + CLI)
                     → 端到端测试（3 case）
                     → Gate 4 Exit 门禁全通过
                     → PR 合并 + 大黄本地复验
                     → Gate 4 CLOSED + M2 整体 CLOSED
                     → M3 正式启动
```

---

_待三方确认后转为 DESIGN_APPROVED。本 Spec 是 Gate 4 的设计契约，实施由大G领衔，婉儿实现，大黄验收。_ 🎋
