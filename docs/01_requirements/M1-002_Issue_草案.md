# [M1-002] 使用三个真实案例验证 Aurora 核心对象模型与认知回溯链路

**状态：** 草案（等待案例素材确认）  
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

## 二、三个案例设计

建议围绕同一主题（如半导体设备/AI芯片/先进制程产业链），覆盖三种载体类型：

| 案例 | 载体 | 内容重点 | 主要验证对象 |
|------|------|----------|-------------|
| Case A | 网页 | 半导体行业或政策解读 | Source, Document, ContentUnit, Claim, Evidence |
| Case B | 视频/播客 | 某只半导体股票或产业链分析 | Speaker, 时间戳, Claim, 风险观点, 观点归属 |
| Case C | PDF | 公司年报或行业研报，含财务数据 | DataPoint, Fact, 页码定位, Evidence, KnowledgeObject |

验证维度：

- 网页段落定位
- 音视频时间戳定位
- PDF页码定位
- 观点主体归属
- 数据口径
- 事实证据链
- 多来源观点冲突
- 个人观点形成流程

---

## 三、需婉儿/大黄提供的案例素材

在下发 Issue 前需要确认：

1. 三个案例的标题和来源类型
2. 来源链接或脱敏后的本地文件说明
3. 网页关键段落
4. 音视频关键片段及时间戳
5. PDF关键页码和摘录
6. 人工预期的事实、观点和数据

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
