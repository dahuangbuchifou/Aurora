# Aurora V1.1 Payload迁移运行手册 V1.0

## 1. 前置检查

```bash
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
pytest -q
```

迁移前复制数据库文件，并确保没有其他写入任务。

## 2. Dry-run

```bash
aurora-migrate-payloads \
  --database sqlite:///./data/aurora.db \
  --from 1.0 \
  --to 1.1 \
  --dry-run \
  --report ./data/migration_reports/m1_003_dry_run.json
```

检查：

- `failed_count = 0`；
- `selected_count`符合预期；
- 数据库中的V1.0记录没有变化。

## 3. 正式迁移

```bash
aurora-migrate-payloads \
  --database sqlite:///./data/aurora.db \
  --from 1.0 \
  --to 1.1 \
  --backup-dir ./data/migration_backups/m1_003 \
  --report ./data/migration_reports/m1_003_result.json
```

生成：

```text
data/migration_backups/m1_003/
├── manifest.json
├── objects_v1_0.jsonl
└── objects_v1_0.sha256
```

## 4. 验证

```bash
pytest -q
alembic current
```

核查：

- V1.0和V1.1混合读取正常；
- 新对象写1.1；
- 三个真实案例回溯正常；
- 未知版本明确报错。

## 5. 恢复

```bash
aurora-restore-payloads \
  --database sqlite:///./data/aurora.db \
  --manifest ./data/migration_backups/m1_003/manifest.json \
  --backup-current-dir ./data/migration_backups/pre_restore \
  --report ./data/migration_reports/m1_003_restore.json
```

恢复命令会先校验SHA-256。校验失败必须停止，不允许强制绕过。

## 6. 注意事项

- Alembic只处理表和索引；
- Payload迁移必须显式执行；
- 读取V1.0不会自动写回；
- 当前迁移支持幂等重试；
- 正式环境不要直接执行 `alembic downgrade base`。
