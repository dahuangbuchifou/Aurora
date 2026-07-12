# Case A 模型验证记录

## 结论

网页段落、公司主张和派生财务数据均可表达。PR稿通过 `Provenance.origin_object_ids` 和 `Document.parent_document_id` 指向 Case C 年报。

## 发现

- **MAJOR**：模型可记录相同 `independence_group`，但无法自动强制同源证据不得重复计数。
- **MAJOR**：`Provenance` 只能说明“derived”，不能结构化区分 `summarizes/reposts/calculated_from`。
- **MINOR**：`source_refs` 与对象专属 `source_ref` 存在一定重复。

- **MAJOR**：C03把“产能过剩风险”和“8英寸利用率低于70%”合并为一个复合主张；年报测试摘录给出76.5%，因此该Claim被标记为`disputed`并由`refute` Evidence显式反驳。
