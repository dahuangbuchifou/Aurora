# CHANGELOG.md 追加：M2-002

## [0.5.0] - 2026-07-12

### Added

- 本地静态 HTML 解析；
- 显式单 URL 静态 HTML Collector；
- SSRF、DNS和重定向复检；
- PDF页码范围、文本与best-effort表格解析；
- SRT和WebVTT解析；
- ParserConfigHash；
- Raw/Semantic双Hash；
- ParseReport与PARTIALLY_PARSED；
- HTML/PDF表格父子ContentUnit；
- 应用层Ingestion Schema 1.1；
- HTML、URL、PDF、Transcript CLI子命令；
- 多载体E2E测试与性能观察脚本。

### Changed

- Aurora版本升级至0.5.0；
- Document幂等键增加parser_config_hash；
- IngestionResult增加hash、parse_status和metrics；
- 多载体解析依赖进入`parsers`可选Extra。

### Security

- URL仅允许HTTP(S)；
- 默认阻止私网、回环、链路本地、多播和保留地址；
- 每次重定向重新校验网络目标；
- HTTPX不继承环境代理和认证；
- 输入大小、PDF页数、timeout和redirect均有限制。

### Validated

- 197 tests passed；
- 0 failed；
- 0 warnings；
- 95.40% coverage；
- 核心Schema v1/v1_1无变化。
