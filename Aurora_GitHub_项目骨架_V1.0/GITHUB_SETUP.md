# GitHub 建库与上传说明

## 推荐仓库名

```text
aurora-intelligence-platform
```

## 建库步骤

1. GitHub 右上角 `+` → `New repository`。
2. 建议先设为 `Private`。
3. 不勾选自动生成 README、.gitignore 或 License。
4. 创建仓库后，将本骨架解压并上传。

## 推荐上传方式

```bash
git clone https://github.com/<你的用户名>/<仓库名>.git
cd <仓库名>

# 将骨架内全部文件复制到当前目录

git add .
git commit -m "chore: initialize Aurora repository structure"
git push origin main
```

## 现有 Markdown 文档放置位置

| 文档 | 目录 |
|---|---|
| 项目定义、核心理念、总路线图 | `docs/00_project/` |
| 用户场景、MVP、需求优先级 | `docs/01_requirements/` |
| 总体架构、边界、核心数据流 | `docs/02_architecture/` |
| 核心对象模型、证据标准、标签 | `docs/03_data_model/` |
| Collector/Parser/Understanding 等引擎 | `docs/04_engines/` |
| WQRS 接口 | `docs/05_integrations/WQRS/` |
| 安全、备份、部署 | `docs/06_operations/` |

## 命名规范

```text
两位序号_中文名称_版本号.md
```

例如：

```text
01_Aurora_核心理念与认知闭环设计_V1.0.md
02_Aurora_项目全流程路线图_V1.0.md
```

## 注意

- GitHub 不保存空目录，因此骨架使用 `.gitkeep` 或 README。
- `data/`、`logs/`、数据库、Cookie、API密钥默认不提交。
- `.env` 禁止提交，只提交 `.env.example`。
