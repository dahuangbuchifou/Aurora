# M2-003 污染与越权测试集

> Gate 2 的认知安全验证测试用例。  
> 这些测试与普通功能测试分离，验证系统在面对恶意或误导输入时的行为。

## 目录

| 文件 | 内容 |
|------|------|
| `pollution_opinion.json` | 观点伪装为事实、估值建议伪装为客观陈述 |
| `pollution_valuation.json` | 估值相关输入与提取边界 |
| `injection_prompt.json` | Prompt Injection 攻击向量 |
| `injection_fake_quote.json` | 虚假引文测试 |
| `injection_forged_cu_id.json` | 伪造 ContentUnit ID 测试 |

## 使用方式

```bash
# M2-003B Gate 2 执行
python3 scripts/gate2_check.py tests/fixtures/m2_003/adversarial/
```

## 测试编写规则

- 每个测试包含：输入材料（可以是 Markdown 或结构化 JSON）、期望的提取行为
- 硬门禁失败的测试必须阻止系统通过 Gate 2
- 测试不得进入普通功能测试目录（`tests/unit/`、`tests/integration/`）
