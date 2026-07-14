# M2-003B Gate 2 Review Round 2 — 大G复核 V1.0

> 建议临时路径：`临时文件/20260714_M2-003B_Gate2_Review_Round2_大G复核_V1.0.md`  
> 分支：`feature/m2-003b-gate2-cognitive-safety`  
> Head Commit：`60b2428`  
> Review轮次：Round 2  
> 大G裁决：**FAIL / ESCALATE_TO_OWNER**  
> 说明：两轮普通Review已用尽，剩余BLOCKER提交大黄裁决。

---

## 1. 已解决项

Round 1中的以下事项已得到有效处理：

- B03：`FactCandidate.promotable=True` 无条件产生ERROR；
- B05：Prompt Injection改为读取完整ContentUnit；
- B07：SafetyGate不再重复实现QuoteGate；
- M01：INFO/WARNING不再计入ERROR；
- M02：项目看板回退至42%，Gate 3保持阻塞；
- ReviewBundle已在集成测试辅助链路中创建；
- 测试、Coverage、冻结资产、Schema和Alembic证据齐全。

---

## 2. 剩余BLOCKER

### R2-B01：`independence_group`处理违反冻结任务卡

冻结任务卡明确要求：

```text
Provider响应出现independence_group
→ 严格拒绝
→ ERROR Finding
```

Round 2实现却：

```text
从PROVIDER_FORBIDDEN_FIELDS移除independence_group
→ 允许Provider直接设置
```

这不是修复B02，而是改变了已冻结的认知安全规则。

正确处理应为：

```text
ProviderEvidenceCandidate
  不包含independence_group

Aurora引擎补全阶段
  根据Source / Document / DerivationLink计算independence_group

EngineEnrichedEvidenceCandidate
  才允许携带independence_group
```

在完成分层前，不得允许Provider直接写入来源独立组。

---

### R2-B02：原始Provider字段校验未接入真实Provider合同

当前SafetyGate接口：

```text
validate(candidates, raw_payloads=list[dict])
```

依赖“候选与原始payload按数组索引一一对齐”。

但现有FixtureProvider：

```text
ProviderResponse.raw_payload = 整份fixture dict
candidates = 构建后再确定性排序
```

Round 2集成测试没有调用FixtureProvider或ExtractionEnvelope，而是测试辅助函数：

```text
读取JSON
→ 手工构建Candidate
→ 手工生成raw_payloads列表
→ SafetyGate
```

因此B01只在测试辅助路径成立，真实ProviderResponse路径仍没有可靠的禁用字段校验。

索引对齐还会在以下情况失效：

- Candidate排序；
- 未知Candidate被跳过；
- Decoder过滤Candidate；
- Provider响应候选缺失或重复。

正确接口应使用：

```text
candidate_id → raw_candidate_payload
```

或在Decoder构造DTO前完成Schema/Forbidden Field Gate，并把Finding带入ExtractionEnvelope。

---

### R2-B03：七类Fixture没有全部进入ReviewBundle与10次确定性验证

冻结任务卡要求：

```text
每个对抗Fixture至少运行10次
Candidate排序稳定
Finding排序稳定
accepted/rejected稳定
ReviewBundle Hash稳定
```

当前ReviewBundle链只覆盖5类：

```text
prediction_pollution
valuation_recommendation
prompt_injection
high_confidence_pollution
provider_independence_override
```

以下两类只单独调用QuoteGate一次：

```text
fake_quote
forged_or_outside_unit
```

它们没有进入ReviewBundle，也没有进行10次bundle_sha256、accepted/rejected集合稳定性验证。

因此E-01、E-02、E-05、F-01至F-05仍未对七类Fixture全部满足。

---

## 3. 剩余MAJOR

### R2-M01：不可晋级ClaimType集合不完整

当前核心ClaimType包含：

```text
fact_claim
interpretation
causal_claim
prediction
recommendation
risk_claim
value_judgment
hypothesis
```

当前`NON_PROMOTABLE_CLAIM_TYPES`缺少：

```text
interpretation
causal_claim
risk_claim
```

却加入了核心枚举中不存在的：

```text
opinion
speculation
```

按照M2-003冻结的Fact晋级策略，MVP阶段只有`fact_claim`可以进入Fact复核候选；其他类型默认不可晋级。

建议直接采用白名单：

```text
claim_type == fact_claim
```

而不是维护容易遗漏的黑名单。

---

### R2-M02：Round 2报告中的“完整管道”表述不准确

当前实际测试链是：

```text
手工JSON加载
→ 手工Candidate构建
→ QuoteGate
→ SafetyGate
→ ReviewBundle
```

尚不是：

```text
FixtureProvider
→ ProviderResponse
→ ExtractionEnvelope
→ QuoteGate
→ SafetyGate
→ ReviewBundle
```

报告应修正，避免把测试辅助链描述为正式Provider编排链。

---

## 4. Round 2裁决

```text
Round 1：FAIL
Round 2：FAIL

剩余BLOCKER：3
剩余MAJOR：2

允许merge main：NO
允许进入M2-003C：NO
Gate 2状态：BLOCKED / OWNER_DECISION_REQUIRED
总体治理进度：42%
```

---

## 5. 大黄裁决建议

建议大黄选择：

```text
继续完成3个BLOCKER和2个MAJOR
```

原因：问题都位于Provider边界与证据独立性核心，不适合进入待优化清单延期。

该处理属于“两轮Review后的Owner-directed corrective action”，不是第三轮普通Review。

最小修复范围：

1. 恢复`independence_group`为Provider禁用字段；
2. 拆分Provider Evidence与Engine Enriched Evidence；
3. 原始payload按candidate_id校验，或在DTO前Decoder Gate完成；
4. 正式使用FixtureProvider / ProviderResponse / ExtractionEnvelope；
5. 七类Fixture全部进入ReviewBundle并执行10次稳定性验证；
6. Fact晋级改为`fact_claim`白名单；
7. 修订Round 2报告表述。

修复完成后只做一次“Owner Closure Verification”，检查上述固定项，不再扩展Review范围。
