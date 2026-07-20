# Changelog

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

## [0.2.0] - 2026-07-12

### Added
- 120 个对象的真实案例验证（3 案例 × 17 类型全覆盖）
- 参考图验证与来源回溯引擎（Traceability Engine）
- 任意对象到 Source 的完整路径追踪
- Evidence 独立分组与同源去重
- 认知链回溯：Fact → Knowledge → Insight → Opinion → Output
- 观点污染防护测试（claim_not_promoted_to_fact）
- jsonschema 开发依赖

### Verified
- 数据冲突处理（利用率 70% vs 76.5% → disputed）
- 管理层增长展望 vs UP主估值谨慎 → QUALIFY 而非 REFUTE
- PersonalOpinion 从未自动激活
- 单表 JSON 持久化在真实案例中工作正常

## [0.1.0] - 2026-07-12

### Added
- Aurora V1.0 十七类核心对象模型
- JSON Schema 导出与对象注册表
- SQLAlchemy 单表 JSON 持久化
- Alembic 初始迁移
- ObjectRepository、软删除和乐观版本控制
- 核心模型与数据库集成测试

### Fixed
- Alembic 运行时自动解析 `src/` 包路径
- Migration 测试隔离 `AURORA_DATABASE_URL` 环境变量

## [Unreleased]

### Added

- 初始化 Aurora GitHub 项目骨架。
- 新增 M2-003C Gate 3 独立 QA 报告、Evidence、外部证据 SHA 清单及 Review Closure V1.3。

### Changed

- Gate 3 生命周期更新为 `CONDITIONALLY_CLOSED_BY_OWNER`。
- Owner 决定为 `APPROVE_CLOSE_WITH_FOLLOW_UPS`。
- PR #1 当前仍为 `NOT_MERGED`。
- Gate 4 当前为 `NOT_STARTED`。

### Verified

- GitHub Actions `quality-gate` Run #14：success；
- 644 passed / 0 failed / 0 skipped；
- 普通 pytest：4.72s；
- Coverage pytest：7.79s；
- Total Coverage：92.64%；
- Coverage threshold：90%；
- G3-1～G3-7：全部 PASS；
- BLOCKER：0。

### Known follow-ups

- OPT-072 / MAJOR-01：`mapper.py` Coverage 88% → ≥90%，进入 Gate 4 前强制完成；
- OPT-073 / RECOMMENDATION-01：建议增加 G3-7 最终数据库 payload 全字段扫描测试，不是 Gate 4 强制前置；
- MINOR-01：E12-B / E12-C PNG 未独立复算，风险已接受，不阻塞 Closure。
