# Gate0 Checker V1.1 修订要求

## 必须新增

1. 使用 Draft 2020-12 JSON Schema 和 FormatChecker；
2. 固定要求三个文件名；
3. 校验 fixture_source_hash；
4. 加载 M2-002 解析后的 ContentUnit snapshot；
5. 对 source_quote 做 Unicode/空白规范化子串匹配；
6. 校验所有 enum；
7. 校验全局ID唯一；
8. 校验 entity/claim/evidence/fact-candidate引用；
9. FactCandidate必须且只能引用 DataPoint 或 Claim 之一；
10. promotable=true 时 valid_time 和 Evidence 必须存在；
11. promotable=false 时 rejection_reason 必须存在；
12. prediction 必须有 time_horizon；
13. reviewed_by/reviewed_at 在 final 模式必须非空；
14. disagreements 在 final 模式必须全部有 resolution；
15. Case A/C independence_group必须按派生关系一致；
16. G0-7必须覆盖 APPROVE、REJECT、REVISE_AND_APPROVE 三类；
17. 输出区分：
    - preliminary_pass
    - semantic_review_pass
    - final_gate_pass

## CLI建议

```bash
python scripts/gate0_check.py \
  tests/fixtures/m2_003/expected \
  --schema schemas/extraction/v1/expected_results.schema.json \
  --content-snapshots tests/fixtures/m2_003/content_units \
  --mode final
```

## 退出码

```text
0 = final gate pass
1 = validation failure
2 = environment/input error
```
