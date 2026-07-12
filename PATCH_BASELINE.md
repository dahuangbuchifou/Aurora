# M2-002 Patch Baseline

```text
Base version: Aurora 0.4.0
Base milestone: M2-001 CLOSED / QA_PASSED
Expected base tests: 129
Target version: Aurora 0.5.0
Target issue: M2-002
```

本包是增量覆盖包，不是完整仓库快照。

必须采用覆盖式复制，并在复制前后执行 SHA-256、Manifest、`pytest --collect-only` 和全量回归。
