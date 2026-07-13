# Aurora M2-003B：真实垂直切片与 Gate 1 Issue V1.0

> **状态**：READY_FOR_IMPLEMENTATION  
> **前置条件**：M2-003A CLOSED / Gate 0 FINAL_PASS  
> **代码基线**：Git Commit `78d8b90`  
> **目标**：用 M2-002 真实 Parser 与真实 ContentUnit 跑通可重放、可审计、无持久化副作用的最小提取链。

---

## 1. Gate 0 关闭结论

M2-003A 已完成：

```text
Gate 0 V1.2c：35/35 PASS
真实负向测试：5/5 PASS
全量测试：256/256 PASS
```

已验证：

- 三份人工黄金结果；
- 严格 Expected Results Schema；
- 实际材料 SHA-256；
- 冻结 ContentUnit 快照；
- `source_unit_id` 精确定位；
- `literal` 与 `token_set` Quote Gate；
- 跨 Document 拒绝；
- 三类 ReviewDecision；
- Prediction 与 Fact 边界。

M2-003A 正式关闭，不再调整黄金集语义。

---

## 2. M2-003B 目标链

本期必须跑通：

```text
M2-002 原始材料 Fixture
→ 真实 Collector / Parser
→ 真实 Document + ContentUnit
→ 确定性 ContextWindow
→ FixtureProvider
→ ExtractionEnvelope
→ QuoteGate
→ ValidationFinding
→ 不可变 ReviewBundle
```

这里的“真实”是指：

- ContextWindow 必须来自 M2-002 Parser 的实际输出；
- 不得从 `expected_results.json` 或候选 Quote 反向构造 ContentUnit；
- Provider Fixture、输入 ContentUnit、人工 Expected Results 三者必须独立；
- ReviewBundle 不写 Entity、DataPoint、Claim、Evidence 或 Fact 到数据库。

---

## 3. 本期范围

### 3.1 包含

1. `ExtractionRequest` 最小合同；
2. `ContextWindowBuilder`；
3. `FixtureProvider`；
4. `ExtractionEnvelope`；
5. Candidate DTO；
6. `QuoteGate`；
7. 基础 Reference Gate；
8. ValidationFinding；
9. 不可变 ReviewBundle；
10. ReviewBundle SHA-256；
11. 三个真实案例垂直切片；
12. Gate 1 七项硬门禁；
13. 全量回归。

### 3.2 不包含

```text
远程模型 Provider
OpenAI-compatible API
persist_drafts
apply_review
Fact 持久化
实体模糊合并
跨 Document 候选合并
复杂 Evidence 独立性计算
CLI 交互式审核
```

这些不得提前进入本 Issue。

---

## 4. 输入独立性要求

必须维护三个互相独立的数据面：

### A. Source Fixture

```text
tests/fixtures/m2_003/materials/
```

包含真实 HTML、SRT/VTT、PDF 或稳定的合成 PDF。

### B. Provider Fixture

```text
tests/fixtures/m2_003/provider_responses/
```

模拟 Provider 返回的 ExtractionEnvelope。

Provider Fixture 可以引用 `source_unit_id`，但不得用于生成 ContextWindow。

### C. Expected Results

```text
tests/fixtures/m2_003/expected/
```

只用于断言，不得参与输入构造。

禁止：

```text
expected quote
→ 生成 ContentUnit
→ 再验证 expected quote
```

---

## 5. ContextWindowBuilder

### 5.1 输入

```text
document_id
ordered ContentUnits
max_context_chars
overlap_units
```

### 5.2 基本规则

- 所有 ContentUnit 必须属于 `document_id`；
- 按 `sequence_no` 升序；
- 相同 `sequence_no` 按稳定 `unit_id` 排序；
- 不切断单个 ContentUnit；
- TABLE 与其 TABLE_ROW 尽量同窗；
- Transcript Cue 不拆分；
- 空窗口拒绝；
- 重复 `unit_id` 拒绝；
- 重复 `(sequence_no, unit_id)` 拒绝；
- 输入顺序变化不影响输出顺序。

### 5.3 Context Hash V1

当前基线只哈希 `sequence_no + text`，不足以作为审计身份。

本期必须改为规范化 JSON：

```json
{
  "context_schema_version": "1.0",
  "document_id": "doc_xxx",
  "units": [
    {
      "unit_id": "cu_xxx",
      "sequence_no": 0,
      "unit_type": "paragraph",
      "text_sha256": "...",
      "locator_sha256": "..."
    }
  ]
}
```

然后：

```text
UTF-8
+ sort_keys=true
+ separators=(",", ":")
+ SHA-256
```

要求：

- 不允许字段拼接造成边界歧义；
- 不同 Document 即使文本相同，Hash也不同；
- Unit顺序变化后经确定性排序，Hash不变；
- Unit文本、类型、Locator或ID变化，Hash改变。

---

## 6. FixtureProvider

接口建议：

```python
class ExtractionProvider(Protocol):
    def extract(
        self,
        *,
        request: ExtractionRequest,
        context: ContextWindow,
    ) -> ProviderResponse:
        ...
```

FixtureProvider：

- 从独立 Provider Fixture 读取响应；
- 不访问网络；
- 不读取 Expected Results；
- 不创建核心对象；
- 原始响应必须保留；
- Provider内的 Candidate顺序可以故意打乱，用于验证系统排序；
- 支持注入非法Unit、虚假Quote和非法字段。

---

## 7. Candidate DTO

本期最少支持：

```text
EntityCandidate
DataPointCandidate
ClaimCandidate
EvidenceCandidate
FactCandidate
```

其中 DataPoint、Claim、Evidence 和 FactCandidate 必须包含：

```text
source_unit_id
supporting_quote
quote_match_mode
```

Provider的 `candidate_id` 只在单次 Envelope 内使用。

### Candidate核心字段

用于 G1-7 漂移检查：

```text
candidate_type
statement / canonical_name / metric
claim_type
claim_dimension
claimant / asserted_by
confidence
source_unit_id
```

### 稳定排序

建议排序键：

```text
source_unit.sequence_no
→ CandidateType固定顺序
→ normalized primary field
→ candidate_id
```

CandidateType顺序必须冻结为常量，不依赖字典遍历顺序。

---

## 8. QuoteGate

### 8.1 literal

```text
NFKC
→ 折叠空白
→ supporting_quote 是目标 ContentUnit.text 的连续子串
```

只检查 `source_unit_id` 指向的单元，不搜索全窗口。

### 8.2 token_set

仅允许：

```text
TABLE
TABLE_ROW
```

规则：

- Quote Token 100%命中；
- 不允许跨 Unit；
- 数值、年份、币种、单位不得被过滤；
- 空 Token 集拒绝；
- 记录命中的 `source_unit_id`；
- 不自动把 token_set 降级为 literal 或模糊匹配。

### 8.3 强制拒绝

- Unit不存在；
- Unit不在当前ContextWindow；
- Unit属于其他Document；
- Quote为空；
- Quote无法匹配；
- token_set用于非表格单元；
- Provider试图引用整个Document而非具体Unit。

---

## 9. ReviewBundle

ReviewBundle必须不可变，至少包含：

```text
run_id
request
document_id
context_hashes
provider
provider_response_hash
prompt/profile版本占位
candidates
validation_findings
accepted_candidate_ids
rejected_candidate_ids
created_at
bundle_schema_version
bundle_sha256
```

### Bundle Hash

计算方式：

1. 复制Bundle；
2. 移除 `bundle_sha256`；
3. 转为规范化JSON；
4. SHA-256；
5. 写回 `bundle_sha256`。

必须测试：

```text
同一输入 → 同一Bundle Hash
修改任一Candidate → Hash变化
修改Finding → Hash变化
修改Context Hash → Hash变化
```

本期 ReviewBundle 只落本地 Artifact，不写认知核心对象。

---

## 10. ProcessingRun与副作用

本 Issue 的最小实现允许：

```text
创建 ProcessingRun
保存 ReviewBundle Artifact
```

禁止：

```text
创建 Entity
创建 DataPoint
创建 Claim
创建 Evidence
创建 Fact
修改输入 Document
修改输入 ContentUnit
```

若本期尚未接入 Repository，允许先以纯内存运行，但必须保证接口可在后续接入 ProcessingRun。

---

## 11. 三个真实垂直切片

### Case A：HTML

```text
HTML Fixture
→ HtmlDocumentParser
→ HEADING/PARAGRAPH/TABLE/TABLE_ROW
→ ContextWindow
→ FixtureProvider
→ QuoteGate
→ ReviewBundle
```

重点：

- 表格 `token_set`；
- 管理层 Prediction；
- 代码块 Reject；
- Candidate排序。

### Case B：Transcript

```text
SRT/VTT Fixture
→ TranscriptParser
→ TRANSCRIPT_SEGMENT
→ ContextWindow
→ FixtureProvider
→ QuoteGate
→ ReviewBundle
```

重点：

- Speaker；
- Cue边界；
- 错误Unit引用；
- UP主观点不生成Fact。

### Case C：PDF

```text
PDF Fixture
→ PdfDocumentParser
→ PARAGRAPH/TABLE/TABLE_ROW
→ ContextWindow
→ FixtureProvider
→ QuoteGate
→ ReviewBundle
```

重点：

- 页码；
- Financial DataPoint；
- Prediction time_horizon；
- FactCandidate不持久化。

---

## 12. Gate 1 七项硬门禁

| 编号 | 门禁 | 判定 |
|---|---|---:|
| G1-1 | 非法Unit引用进入ReviewBundle | 0 |
| G1-2 | 无法定位Quote的候选被接受 | 0 |
| G1-3 | 自动创建Fact | 0 |
| G1-4 | 读取后自动修改原Document/ContentUnit | 0 |
| G1-5 | 同一Fixture重复运行结果不一致 | 0 |
| G1-6 | Candidate排序漂移 | 0 |
| G1-7 | Candidate核心字段漂移 | 0 |

### 重复运行要求

每个案例至少运行：

```text
10次相同输入
+ 10次随机打乱Provider候选输入顺序
+ 10次随机打乱ContentUnit传入顺序
```

最终 ReviewBundle 的规范化候选顺序和核心字段必须完全一致。

---

## 13. 支撑性工程门禁

以下不计入 G1-1～G1-7，但必须通过：

1. 三个案例均从真实 M2-002 Parser 开始；
2. Expected Results 不参与 ContextWindow构造；
3. Provider Fixture 不参与 ContentUnit构造；
4. Context Hash canonicalization测试；
5. ReviewBundle SHA防篡改测试；
6. 跨Document ContextWindow拒绝；
7. 重复Unit拒绝；
8. 空窗口拒绝；
9. 全量测试0失败、0警告；
10. 总覆盖率与新增模块覆盖率均≥90%；
11. Python 3.11.13和SQLite 3.26+通过；
12. 核心 V1.1 Schema无变化；
13. 无Alembic Revision。

---

## 14. 建议目录

```text
src/aurora/extraction/
├── request.py
├── context_window.py
├── candidates.py
├── provider.py
├── fixture_provider.py
├── envelope.py
├── quote_gate.py
├── findings.py
└── review_bundle.py

tests/
├── unit/
│   ├── test_context_window.py
│   ├── test_fixture_provider.py
│   ├── test_quote_gate.py
│   └── test_review_bundle.py
├── integration/
│   └── test_m2_003b_real_vertical_slice.py
└── fixtures/m2_003/
    ├── materials/
    ├── provider_responses/
    ├── expected/
    └── content_units/
```

冻结快照继续用于Gate 0，不代替Gate 1真实Parser链路。

---

## 15. 交付要求

大G交付：

```text
生产代码
单元测试
三个真实垂直切片
Gate 1报告
全量测试报告
Coverage报告
核心Schema Diff
Manifest
SHA256SUMS
应用说明
```

婉儿QA：

```text
Git Commit SHA
Python/SQLite依赖版本
G1-1—G1-7逐项结果
真实Parser链路证据
10×3确定性运行结果
ReviewBundle Hash防篡改
全量pytest和coverage
核心Schema Diff
PASS / FAIL
```

---

## 16. 阶段切换

通过后：

```text
M2-003B Gate 1：PASS
→ 立即进入 Gate 2 认知安全验证
```

Gate 2仍属于M2-003B，但必须单独交付、单独QA，不与 Draft Persistence 合并。
