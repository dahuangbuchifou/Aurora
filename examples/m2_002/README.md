# M2-002 多载体导入示例

这些示例均为离线、合成或节选 Fixture，用于验证 M2-002 的解析链。

```bash
aurora-ingest html examples/m2_002/case_a_web.html \
  --source-name "SMIC Official Website" \
  --source-type official_website \
  --output json

aurora-ingest transcript examples/m2_002/case_b_video.vtt \
  --source-name "Semiconductor Observation" \
  --source-type video_platform \
  --output json

aurora-ingest pdf examples/m2_002/case_c_report.pdf \
  --source-name "SMIC Annual Report" \
  --source-type company_filing \
  --pages 1-2 \
  --table-mode best_effort \
  --output json
```

M2-002 只生成 Source、Document、ContentUnit 和 ProcessingRun，不生成 Fact、Claim 或 Evidence。
