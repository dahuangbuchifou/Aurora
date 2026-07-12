# Aurora M2-002 交付包

本包是相对于 Aurora 0.4.0 / M2-001 CLOSED 基线的增量覆盖包。

应用顺序：

1. 阅读 `PATCH_BASELINE.md`；
2. 执行 `sha256sum -c SHA256SUMS.txt`；
3. 按 `APPLY_INSTRUCTIONS.md` 覆盖式复制；
4. 安装 `.[dev,parsers]`；
5. 在 Python 3.11.13 运行全量测试；
6. 按 `docs/qa/M2-002_QA_验收清单_V1.0.md` 输出QA报告。

本包不包含数据库、虚拟环境、`.git`、缓存或外部真实网页/PDF。
