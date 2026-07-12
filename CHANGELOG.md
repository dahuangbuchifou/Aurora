# Changelog

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
