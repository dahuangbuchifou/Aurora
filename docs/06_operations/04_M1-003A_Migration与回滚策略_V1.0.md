# M1-003A：V1.0 → V1.1 Migration 与回滚策略 V1.0

---

## 1. 迁移原则

1. DDL 与领域 Payload 分离；
2. 不在 Alembic 中静默批量改写 JSON；
3. 所有 Payload 迁移先 dry-run；
4. 迁移前生成可验证备份；
5. 单个对象失败不应破坏其他对象；
6. 迁移结果必须再次通过 Pydantic 和 JSON Schema；
7. 支持混合版本运行，不要求一次性迁完。

---

## 2. Alembic 方案

M1-003B 建议新增 Revision：

```text
202607xx_0002_add_schema_version_index
```

内容：

```text
upgrade:
  create index ix_object_records_schema_version

downgrade:
  drop index ix_object_records_schema_version
```

不在该 Revision 中执行：

- JSON 字段补充；
- schema_version 批量改写；
- origin_object_ids 转 derivation_links；
- ClaimDimension 自动分类；
- 财务口径猜测。

### 原因

Alembic 适合数据库结构变更，不适合需要逐对象业务校验、备份和人工审计的知识资产转换。

---

## 3. Payload 迁移命令

M1-003B 建议实现：

```bash
aurora-migrate-payloads \
  --from 1.0 \
  --to 1.1 \
  --database sqlite:///./data/aurora.db \
  --dry-run
```

正式执行：

```bash
aurora-migrate-payloads \
  --from 1.0 \
  --to 1.1 \
  --database sqlite:///./data/aurora.db \
  --backup-dir ./data/migration_backups/m1_003
```

建议选项：

```text
--dry-run
--batch-size
--object-type
--workspace-id
--backup-dir
--fail-fast
--continue-on-error
--report
```

---

## 4. 备份格式

```text
data/migration_backups/m1_003/
├── manifest.json
├── objects_v1_0.jsonl
├── objects_v1_0.sha256
└── migration_report.json
```

`manifest.json` 至少包含：

```json
{
  "migration_id": "m1_003_v1_0_to_v1_1",
  "created_at": "ISO-8601",
  "database_url_redacted": "sqlite:///...",
  "from_version": "1.0",
  "to_version": "1.1",
  "object_count": 120,
  "sha256": "..."
}
```

禁止在报告中输出：

- API Key；
- Cookie；
- 完整敏感正文；
- 未脱敏数据库 URL。

---

## 5. 迁移算法

```text
查询 schema_version=1.0
        ↓
复制原payload到备份
        ↓
upgrade_payload_v1_0_to_v1_1(copy)
        ↓
Pydantic V1.1校验
        ↓
JSON Schema V1.1校验
        ↓
逐对象事务写入
        ↓
重新读取并比对ID、类型、来源链
        ↓
记录结果
```

默认采用：

```text
逐批事务
```

而不是全库一个大事务。

建议：

```text
batch_size = 100
```

对于当前 120 个对象，仍可一次完成，但代码应支持批次。

---

## 6. 回滚策略

### 场景A：Alembic DDL失败

执行：

```bash
alembic downgrade -1
```

该回滚只删除索引，不影响 payload。

### 场景B：Payload迁移部分失败

- 成功对象保持已迁移；
- 失败对象保持 V1.0；
- 数据库继续混合版本运行；
- 根据报告修复后重试；
- 迁移命令必须幂等。

### 场景C：需要全部恢复V1.0

执行：

```bash
aurora-restore-payloads \
  --manifest ./data/migration_backups/m1_003/manifest.json
```

恢复前必须：

- 校验 SHA-256；
- 检查 object id；
- 检查数据库目标；
- 生成当前状态二次备份。

### 场景D：代码回滚

在启用 V1.1 写入前：

```text
可直接回滚代码
```

启用 V1.1 写入后：

```text
旧代码不能保证读取新字段
```

必须：

- 保留支持双读的版本；
- 或先执行 payload 恢复；
- 不允许直接部署只支持 V1.0 的旧代码。

---

## 7. 发布顺序

### Step 1：准备

- 合并 M1-003B；
- 全量测试；
- 数据库文件备份；
- 生成迁移 dry-run 报告。

### Step 2：部署双读版本

- 支持 V1.0/V1.1；
- 暂不批量迁移；
- 验证 M1-002 案例。

### Step 3：启用 V1.1 新写入

- 新对象写 1.1；
- 旧对象保持 1.0；
- 观察错误和性能。

### Step 4：可选批量迁移

- 先备份；
- 先 dry-run；
- 分批迁移；
- 验证追溯链。

### Step 5：阶段冻结

- 确认无回滚需求；
- 更新 CHANGELOG、DECISIONS 和进度看板；
- 关闭 M1。

---

## 8. 运维验收

- [ ] Alembic upgrade/downgrade通过；
- [ ] dry-run不写库；
- [ ] 备份SHA-256可验证；
- [ ] 迁移命令可重复执行；
- [ ] 单个失败不破坏其他对象；
- [ ] 恢复命令可还原原payload；
- [ ] 混合版本可正常查询；
- [ ] 不发生静默数据丢失；
- [ ] 迁移日志不泄露敏感数据。
