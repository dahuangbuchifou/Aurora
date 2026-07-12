# Case C 模型验证记录

## 结论

页码定位、数据点、证据和事实链可以完整表达。

## 发现

- **MAJOR**：DataPoint 缺少独立的 `currency`、`scale`、`accounting_standard`、`attribution_scope`、`consolidation_scope`。
- **MAJOR**：当前用 `unit="CNY_100_million"` 合并币种和数量级，机器可读性和口径比较能力不足。
- **MINOR**：Fact 与 DataPoint 的职责仍需进一步定义，避免同一数值重复维护。
- **ENHANCEMENT**：建议支持区间值，方便表达收入增长10%-15%和毛利率23%-26%。
