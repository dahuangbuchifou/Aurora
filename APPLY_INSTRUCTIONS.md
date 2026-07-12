# Aurora M2-002 应用与验证说明

## 1. 基线

本包是基于以下状态的增量包：

```text
Aurora 0.4.0
M1：CLOSED
M2-001：CLOSED / QA_PASSED
129 tests
```

应用前确认：

```bash
python -c "import aurora; print(aurora.__version__)"
```

预期基线：

```text
0.4.0
```

## 2. 分支

```bash
git checkout main
git pull
git checkout -b feature/m2-002-multicarrier-parsers
```

## 3. 解压与完整性校验

```bash
unzip Aurora_M2-002_交付_V1.0.zip
cd Aurora_M2-002_交付_V1.0
sha256sum -c SHA256SUMS.txt
```

必须全部显示：

```text
OK
```

## 4. 覆盖式复制

从交付目录执行：

```bash
cp -a . /path/to/Aurora/
```

不要只复制新目录。本交付会修改已有文件，包括：

```text
pyproject.toml
src/aurora/cli/ingest.py
src/aurora/workflow/ingestion.py
src/aurora/ingestion/contracts.py
```

## 5. 安装

```bash
cd /path/to/Aurora
source .venv/bin/activate
pip install -e ".[dev,parsers]"
```

## 6. Schema

应用层 Schema 已包含在包内：

```text
schemas/ingestion/v1_1/
```

需要重建时：

```bash
aurora-export-ingestion-schemas \
  --output schemas/ingestion/v1_1
```

禁止覆盖：

```text
schemas/ingestion/v1/
schemas/v1/
schemas/v1_1/
```

## 7. 全量测试

```bash
pytest --collect-only -q
pytest -q
pytest \
  --cov=aurora \
  --cov-branch \
  --cov-report=term-missing \
  --cov-fail-under=90
```

本地参考：

```text
197 collected
197 passed
95.40% coverage
```

## 8. CLI检查

```bash
aurora-ingest --help
aurora-ingest html --help
aurora-ingest url --help
aurora-ingest pdf --help
aurora-ingest transcript --help
```

## 9. 核心Schema检查

对比：

```text
schemas/v1/
schemas/v1_1/
```

预期无文件增删或内容变化。

## 10. 注意

正式QA不要访问公共网站。URL测试应使用本地HTTP测试服务器与注入Resolver，避免网络波动和SSRF风险。
