# [M1-002] 使用三个真实案例验证 Aurora 核心对象模型与认知回溯链路

**状态：** 待下发（案例素材已就绪）  
**前置：** M1-001 QA PASS  
**分支：** 待创建 `feature/m1-002-case-validation`

---

## 一、目标

验证以下完整链路：

```
Source
→ Document
→ ContentUnit
→ Claim / DataPoint
→ Evidence
→ Fact
→ KnowledgeObject
→ Insight
→ PersonalOpinion
→ OutputArtifact
```

并确认对象可以：

```
创建 → Schema校验 → 数据库存储 → 查询 → 反序列化 → 关联回溯
```

---

## 二、三个案例（已确认）

**主题：** 中芯国际（688981）— 半导体代工产业链分析

三个案例围绕同一主题，覆盖三种载体类型。完整素材见 `m1_002_materials/` 目录。

| 案例 | 载体 | 内容 | 主要验证 |
|------|------|------|----------|
| Case A | 网页（SMIC官网新闻）| 中芯国际 2025 年报 PR 稿 | Source→Document→ContentUnit→Claim→Evidence |
| Case B | 视频（B站 UP主分析）| 半导体板块及中芯估值分析 | Speaker, 时间戳, Claim归属, 正反观点 |
| Case C | PDF（年报财务章节）| 中芯国际 2025 年报 P15-18 | DataPoint→Fact→页码定位→Evidence→KnowledgeObject |

### 关键跨案例关联（验证 Provenance 机制）

- Case A（PR新闻）中引用的财务数据来源于 Case C（年报）
- Case B（UP主）的估值判断部分基于 Case A/C 的公开数据
- Case B 对中芯国际的观点与 Case A 中的管理层表述存在冲突：
  - Case A · 管理层："2026 年将保持两位数增长"（乐观）
  - Case B · UP主："长期看好但短期偏贵"（谨慎）
- 三个案例共享核心实体：中芯国际、北方华创、半导体产业链

### 数据统计

- **实体：** 12 个（公司/产品/行业/政策）
- **数据点：** 20+ 个（财务指标，含单位、期间、来源）
- **主张：** 16 条（含预测型/判断型/评估型）
- **事实：** 9 条（均含证据链）
- **验证维度：** 7 项（段落定位、时间戳定位、页码定位、观点归属、数据口径、证据链、来源冲突）

---

## 三、案例素材位置

完整素材已准备在仓库中：

```
m1_002_materials/
├── case_a_web/README.md           （网页新闻 · 中芯2025年报PR）
├── case_b_video/README.md         （视频片段 · B站半导体分析）
└── case_c_pdf/README.md           （年报摘录 · 财务数据 P15-18）
```

每个 README 包含：
- 来源元数据
- 关键段落/时间戳的完整文本
- 人工标注的 Claim/DataPoint/Fact/Entity
- 案例间交叉引用说明

---

## 四、本期范围

### 包括：

- 三个真实案例的完整结构化 JSON
- 案例导入脚本或 Fixture
- Repository 存储与查询
- 对象引用关系回溯
- Claim → Evidence → Fact 链路
- Knowledge → Insight → PersonalOpinion 链路
- Markdown 案例审计报告
- 模型缺陷和修订建议（不现场修改 Schema，写入 review.md）

### 不包括：

- 自动抓取网页
- PDF自动解析
- 音视频自动转写
- LLM自动提取
- Web API
- 向量检索
- 自动生成投资建议

---

## 五、交付目录结构

```
schemas/examples/m1_002/
├── case_a_web/
│   ├── source_metadata.json
│   ├── objects.json
│   ├── expected_links.json
│   └── review.md
├── case_b_media/
│   ├── source_metadata.json
│   ├── transcript_excerpt.md
│   ├── objects.json
│   ├── expected_links.json
│   └── review.md
├── case_c_pdf/
│   ├── source_metadata.json
│   ├── extracted_excerpt.md
│   ├── objects.json
│   ├── expected_links.json
│   └── review.md
└── cross_case/
    ├── topic_summary.json
    ├── insight.json
    ├── personal_opinion.json
    └── research_brief.md

tests/
├── fixtures/m1_002/
├── integration/test_m1_002_case_import.py
├── integration/test_m1_002_traceability.py
└── e2e/test_m1_002_cognitive_chain.py
```

---

## 六、对象引用规范

单个 `objects.json` 采用数组格式：

```json
{
  "case_id": "case_a_web",
  "schema_version": "1.0",
  "objects": [
    {"object_type": "source", ...},
    {"object_type": "document", ...},
    {"object_type": "content_unit", ...},
    {"object_type": "claim", ...},
    {"object_type": "evidence", ...}
  ]
}
```

引用必须使用真实对象 ID，不允许仅凭数组位置建立关系。

---

## 七、验收标准

### 数据与 Schema
- [ ] 三个案例所有对象均通过 Pydantic 校验
- [ ] 所有对象均通过对应 JSON Schema
- [ ] 不存在悬空对象引用
- [ ] 对象 ID 全局唯一
- [ ] 所有派生对象具有 Provenance

### 来源定位
- [ ] 网页内容可定位到段落
- [ ] 音视频内容可定位到时间戳
- [ ] PDF内容可定位到页码
- [ ] Fact 和 Claim 能回溯到具体 ContentUnit

### 认知边界
- [ ] 文章作者观点未被错误升级为 Fact
- [ ] 财务数据包含单位、期间和来源
- [ ] Prediction 包含时间范围
- [ ] Evidence 能区分支持与反驳
- [ ] Insight 被明确标记为推断
- [ ] PersonalOpinion 只有用户确认后才能 Active

### 持久化
- [ ] 所有对象可写入 SQLite
- [ ] 所有对象可正确读取并恢复原始类型
- [ ] 按 object_type 查询正确
- [ ] 软删除不破坏其他对象
- [ ] Repository 可完成完整回溯

### 跨案例
- [ ] 三个案例至少共享一个主题或实体
- [ ] 能识别至少一组支持观点
- [ ] 能识别至少一组反方或限制性证据
- [ ] 能生成一个 Insight
- [ ] 能形成一个 PersonalOpinion 草案
- [ ] 能生成一个 Markdown 研究简报

### 模型审计
- [ ] 列出字段不足
- [ ] 列出冗余字段
- [ ] 列出边界模糊点
- [ ] 说明是否需要 V1.1
- [ ] 不因单个案例特殊性盲目修改通用模型

---

## 八、模型修改纪律

发现问题后流程：

```
发现问题 → 写入 review.md → 标记严重级别 → 汇总至模型审计报告
→ 大G与婉儿评审 → 决定是否进入 V1.1 → 单独 Migration / Schema Issue
```

严重级别：

```
BLOCKER  - 无法表达核心信息，案例无法完成
MAJOR    - 可表达但语义错误或追溯链不可靠
MINOR    - 字段命名、可选性或使用体验问题
ENHANCEMENT - 当前可用，未来可增强
```

M1-002 中不允许为了通过案例而随意向 `metadata` 添加大量自由字段。

---

## 九、当前 M1-001 合并后目录树

```
Aurora/
├── alembic/
│   ├── env.py           （已修复：自动添加 src/ 到 sys.path）
│   ├── script.py.mako
│   └── versions/
│       └── 20260711_0001_create_object_records.py
├── alembic.ini
├── CHANGELOG.md
├── docs/
│   ├── 03_data_model/
│   │   └── 05_M1-001_持久化设计决策.md
│   ├── M1-001_BUILD_TEST_REPORT.json
│   └── M1-001_交付说明.md
├── pyproject.toml
├── schemas/
│   ├── examples/
│   │   ├── claim.example.json
│   │   ├── personal_opinion.example.json
│   │   └── source.example.json
│   └── v1/
│       ├── claim.schema.json ... (17 schemas)
│       └── registry.json
├── scripts/
│   └── export_schemas.py
├── src/aurora/
│   ├── core/
│   │   ├── models/
│   │   │   ├── application.py  (OutputArtifact, Feedback, ProcessingRun)
│   │   │   ├── atoms.py        (Entity, Event, DataPoint, Claim, Evidence, Fact)
│   │   │   ├── cognition.py    (Insight, PersonalOpinion)
│   │   │   ├── common.py       (Bases, Provenance, TimeRange, etc.)
│   │   │   ├── document.py     (Document, ContentUnit)
│   │   │   ├── enums.py        (All enumerations)
│   │   │   ├── knowledge.py    (KnowledgeObject, Relation, TimelineEntry)
│   │   │   └── source.py       (Source)
│   │   └── schema_registry.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── session.py
│   └── repository/
│       └── object_repository.py
├── tests/
│   ├── conftest.py
│   ├── integration/
│   │   ├── test_migration.py   （已修复：monkeypatch AURORA_DATABASE_URL）
│   │   └── test_repository.py
│   └── unit/
│       ├── test_models.py
│       └── test_schema_registry.py
└── 临时文件/                    （交付中转目录）
```

---

## 十、待婉儿确认后下发

Issue 正式下发需要：

1. 三个案例的素材就位
2. 与大黄确认最终案例选择
3. 在 GitHub 创建正式 Issue 并链接此文档
