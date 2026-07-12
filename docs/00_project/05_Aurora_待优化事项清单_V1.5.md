# Aurora 待优化事项清单 V1.5

## 1. M2-001完成项

```text
OPT-021：DONE
OPT-022：DONE
OPT-023：DONE
OPT-024：DONE
```

## 2. 已延期

| ID | 等级 | 项目 | 状态 | 目标 |
|---|---|---|---|---|
| OPT-025 | ENHANCEMENT | 完整CommonMark兼容 | DEFERRED | 后续 |
| OPT-026 | ENHANCEMENT | 单表JSON身份查询性能 | DEFERRED | M3 |
| OPT-027 | MINOR | 并发导入竞争 | DEFERRED | M2-005/M3 |

## 3. M2-002候选

### OPT-028：PDF精确坐标Locator

- 等级：ENHANCEMENT
- 类别：Provenance
- 状态：DEFERRED
- 问题：V1.1 SourceLocator没有PDF bbox。
- 当前方案：page_no + block_no + row_no。
- 升级条件：真实案例证明页级定位不足。
- 目标：M3或独立Schema Issue。

### OPT-029：动态网页与JavaScript

- 等级：ENHANCEMENT
- 类别：Web Collector
- 状态：DEFERRED
- 问题：静态HTTP不能解析JS渲染页面。
- 当前方案：保存HTML快照或手工转Markdown。
- 目标：M3。

### OPT-030：扫描PDF与OCR

- 等级：MAJOR
- 类别：PDF
- 状态：DEFERRED_BY_SCOPE
- 问题：扫描PDF没有文本层。
- 当前方案：PARTIALLY_PARSED或明确失败。
- 目标：M3或M2-005评审。

### OPT-031：URL抓取SSRF风险

- 等级：MAJOR
- 类别：Security
- 状态：PLANNED
- 目标：M2-002
- 方案：协议白名单、DNS和redirect复检、私网默认禁止、大小与超时限制。

### OPT-032：PDF表格不确定性

- 等级：MAJOR
- 类别：Parser Quality
- 状态：PLANNED
- 目标：M2-002
- 方案：固定参数、版本化、best-effort、质量警告、合成和真实Fixture。

### OPT-033：字幕Cue粒度过细

- 等级：MINOR
- 类别：Understanding Input
- 状态：DEFERRED
- 当前方案：M2-002一Cue一单元。
- 目标：M2-003上下文窗口。

### OPT-034：Parser配置未进入幂等键

- 等级：MAJOR
- 类别：Identity
- 状态：PLANNED
- 目标：M2-002
- 问题：页码范围或table_mode变化可能错误复用Document。
- 方案：新增应用层parser_config_hash并进入Document身份。
