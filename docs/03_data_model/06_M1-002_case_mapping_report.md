# M1-002 真实案例对象映射报告

## 1. 范围

围绕中芯国际测试主题，使用网页PR、视频转写和PDF年报摘录验证17类对象的表达、持久化和回溯能力。

## 2. 对象覆盖

本案例包覆盖全部17类对象：Source、Document、ContentUnit、Entity、Event、DataPoint、Claim、Evidence、Fact、KnowledgeObject、Relation、TimelineEntry、Insight、PersonalOpinion、OutputArtifact、Feedback、ProcessingRun。

## 3. 核心映射

| 案例 | 定位 | 核心对象 | 关键验证 |
|---|---|---|---|
| A 网页PR | paragraph_no | Claim、DataPoint、Evidence | 二次传播追溯至年报；同源证据不重复计数 |
| B 视频 | start/end_seconds | Claim、DataPoint、Evidence | 说话人归属；观点不能升级为Fact |
| C PDF | page_no、block_no | DataPoint、Evidence、Fact | 财务数据口径、页码定位、事实链 |
| Cross-case | 对象ID | Knowledge、Insight、Opinion、Output | 增长与估值观点按维度整合 |

## 4. DataPoint 字段不足（M1-003输入）

当前 DataPoint 能保存 `metric/value/unit/period/source_ref`，但真实财务和市场数据还需要：

1. `currency`：CNY、USD等；
2. `scale`：元、万元、亿元；
3. `accounting_standard`：CAS、IFRS、US GAAP；
4. `attribution_scope`：归母、少数股东、公司整体等；
5. `consolidation_scope`：合并报表、母公司、分部；
6. `observed_at`：价格、估值等时点型数据；
7. `value_low/value_high` 或区间对象：用于目标区间和预测区间；
8. `original_display_value`：保留来源原始展示口径。

当前测试使用复合 unit（如 `CNY_100_million`）临时表达币种和数量级，但这不是稳定方案。

## 5. 显式冲突验证

Case A 的复合主张包含“部分8英寸产线利用率低于70%”，而 Case C 年报测试摘录记录为76.5%。本交付未擅自修正素材，而是：

- 将PR Claim标记为 `disputed`；
- 创建 `EvidenceRole.REFUTE`；
- 保留两个ContentUnit和独立来源路径；
- 将“复合Claim应原子化”纳入M1-003评审。

## 6. 结论

对象链可以跑通，没有BLOCKER。MAJOR问题集中在财务口径、证据独立性约束和Claim分析维度，应进入M1-003评审，不在本任务中现场修改Schema。
