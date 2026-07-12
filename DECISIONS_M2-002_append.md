# DECISIONS.md 追加：M2-002

## ADR-018：HTML使用Beautiful Soup与lxml

- 状态：Accepted
- 决定：解析静态HTML，支持DOM主体选择、结构块和可重放Locator。
- 不采用：浏览器运行时和JavaScript执行。

## ADR-019：显式单URL使用HTTPX同步客户端

- 状态：Accepted
- 决定：只采集用户显式提交的单个静态HTTP(S)地址。
- 不采用：异步爬虫、递归链接和批量任务。

## ADR-020：URL默认阻止私有网络

- 状态：Accepted
- 决定：DNS与每次redirect均重新校验地址；私网默认禁止。

## ADR-021：PDF使用pdfplumber

- 状态：Accepted
- 决定：支持机器生成PDF文本、布局与best-effort表格。
- 不采用：OCR和扫描件识别。

## ADR-022：字幕采用确定性SRT/WebVTT适配层

- 状态：Accepted with implementation note
- 决定：一Cue一单元，Aurora负责稳定时间校验、错误码和speaker提取。
- 依赖：`webvtt-py`保留在可选parsers Extra中用于生态兼容；核心输出由Aurora确定性适配层规范化，避免第三方版本改变错误语义。

## ADR-023：多载体依赖使用可选Extra

- 状态：Accepted
- 决定：`beautifulsoup4/lxml/httpx/pdfplumber/webvtt-py`不成为核心对象层强依赖。

## ADR-024：限制输入资源

- 状态：Accepted
- 决定：HTML和Transcript默认10MiB，PDF默认50MiB/500页，URL timeout 15秒、redirect 5次。

## ADR-025：M2-002不修改V1.1 SourceLocator

- 状态：Accepted
- 决定：PDF使用page_no/block_no/row_no，bbox延期到真实案例证明必要时再评审。

## ADR-026：ParserConfigHash进入Document身份

- 状态：Accepted
- 决定：所有改变分段结果的配置参与Document幂等键。

## ADR-027：Raw Hash与Semantic Hash分离

- 状态：Accepted
- 决定：原始字节用于采集审计，规范化语义序列用于Document复用。
