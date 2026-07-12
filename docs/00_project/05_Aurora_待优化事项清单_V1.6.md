# Aurora 待优化事项清单 V1.6

## 1. M2-001

```text
OPT-021：DONE
OPT-022：DONE
OPT-023：DONE
OPT-024：DONE
```

## 2. M2-002实现项

| ID | 等级 | 项目 | 状态 |
|---|---|---|---|
| OPT-031 | MAJOR | URL抓取SSRF防护 | IMPLEMENTED_PENDING_QA |
| OPT-032 | MAJOR | PDF表格不确定性 | IMPLEMENTED_PENDING_QA |
| OPT-034 | MAJOR | Parser配置进入幂等键 | IMPLEMENTED_PENDING_QA |

## 3. 延期项

| ID | 等级 | 项目 | 状态 | 目标 |
|---|---|---|---|---|
| OPT-025 | ENHANCEMENT | 完整CommonMark | DEFERRED | 后续 |
| OPT-026 | ENHANCEMENT | 单表JSON查询性能 | DEFERRED | M3 |
| OPT-027 | MINOR | 并发导入竞争 | DEFERRED | M2-005/M3 |
| OPT-028 | ENHANCEMENT | PDF bbox Locator | DEFERRED | 独立Schema评审 |
| OPT-029 | ENHANCEMENT | JavaScript动态网页 | DEFERRED | M3 |
| OPT-030 | MAJOR | 扫描PDF与OCR | DEFERRED_BY_SCOPE | M3/M2-005评审 |
| OPT-033 | MINOR | 字幕Cue粒度过细 | DEFERRED | M2-003 |

## 4. 新增观察项

### OPT-035：PDF文本与表格重复消除

- 等级：MINOR
- 类别：Parser Quality
- 状态：DEFERRED
- 问题：复杂布局下普通文本和表格文本可能部分重复。
- 当前方案：按规范化表格行从页面文本中尽量排除。
- 目标：积累真实PDF后优化。

### OPT-036：网页字符集高级识别

- 等级：MINOR
- 类别：Web Collector
- 状态：DEFERRED
- 问题：缺失或错误Content-Type charset的旧网页可能需要更强编码探测。
- 当前方案：使用HTTPX编码结果并在解码失败时明确报错。
- 目标：M2-005或真实案例触发。

### OPT-037：HTML Locator快照持久化策略

- 等级：MAJOR
- 类别：Provenance
- 状态：PLANNED
- 问题：CSS/XPath重放依赖原HTML快照长期可得。
- 当前方案：Document保留原始URI和Hash，Fixture保留快照。
- 目标：M2-005输出与归档评审。
