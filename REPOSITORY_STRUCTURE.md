# Aurora 仓库结构说明

```text
Aurora/
├── README.md
├── GITHUB_SETUP.md
├── REPOSITORY_STRUCTURE.md
├── ROADMAP.md
├── DECISIONS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE.md
├── .gitignore
├── .env.example
├── pyproject.toml
│
├── docs/
│   ├── 00_project/              # 立项、理念、路线图
│   ├── 01_requirements/         # 用户场景、MVP、优先级
│   ├── 02_architecture/         # 总体架构、边界、数据流
│   ├── 03_data_model/           # 对象模型、证据、标签
│   ├── 04_engines/              # 各核心引擎设计
│   ├── 05_integrations/         # WQRS等应用接入
│   ├── 06_operations/           # 运维、安全、备份
│   └── 99_archive/              # 历史和废弃版本
│
├── src/aurora/
│   ├── core/
│   ├── config/
│   ├── collector/
│   ├── parser/
│   ├── understanding/
│   ├── knowledge/
│   ├── search/
│   ├── insight/
│   ├── opinion/
│   ├── workflow/
│   ├── outputs/
│   ├── sdk/
│   └── api/
│
├── schemas/                     # JSON Schema与接口契约
├── prompts/                     # 提示词及版本
├── config/                      # 非敏感运行配置
├── data/                        # 本地数据，真实内容默认不提交
├── tests/                       # 单元/集成/E2E/黄金测试集
├── examples/                    # 脱敏样例
├── scripts/                     # 初始化与维护脚本
├── apps/                        # CLI、Web、WQRS适配
├── deployments/                 # 本地与Docker部署
├── logs/                        # 运行日志
└── .github/                     # Issue、PR、Actions
```

## 关键原则

- `docs/` 是正式设计基线。
- `src/aurora/` 只放可复用底层能力。
- WQRS等专业逻辑放在 `apps/` 或独立仓库。
- `schemas/` 是 Aurora 的“数据宪法”。
- 真实个人资料、原始音视频和数据库不得直接上传公开仓库。
