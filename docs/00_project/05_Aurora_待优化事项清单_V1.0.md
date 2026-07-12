# Aurora 待优化事项清单 V1.0

> 用途：集中记录模型缺陷、工程债务、性能、安全、协作和产品优化。  
> 原则：记录不等于立即实现；进入开发前必须评审。

## 1. 等级与状态

严重等级：

```text
BLOCKER / MAJOR / MINOR / ENHANCEMENT
```

状态：

```text
NEW / UNDER_REVIEW / APPROVED / PLANNED / IN_PROGRESS / DONE / REJECTED / DEFERRED
```

## 2. 当前清单

| ID | 等级 | 类别 | 问题 | 建议方向 | 目标阶段 | 状态 |
|---|---|---|---|---|---|---|
| OPT-001 | MAJOR | DataPoint | 缺少币种、数量级、会计准则、归属和合并范围 | 增加结构化财务口径 | M1-003 | UNDER_REVIEW |
| OPT-002 | MAJOR | Evidence | independence_group不能阻止重复计数 | 增加独立组验证和聚合规则 | M1-003 | UNDER_REVIEW |
| OPT-003 | MAJOR | Claim | 缺少增长、估值、风险、行动建议维度 | 评估claim_dimension | M1-003 | UNDER_REVIEW |
| OPT-004 | MAJOR | Provenance | 无法表达summarizes/reposts/calculated_from | 增加派生关系类型 | M1-003 | UNDER_REVIEW |
| OPT-005 | MAJOR | Claim | 缺少原子性约束 | 建立原子Claim规范和测试 | M1-003 | UNDER_REVIEW |
| OPT-006 | MINOR | Database | SQLite锁等待策略未标准化 | Engine配置timeout/busy_timeout | M1-003/M2 | NEW |
| OPT-007 | MINOR | Testing | schema_registry和session测试不足 | 补充异常与事务测试 | M1-003 | NEW |
| OPT-008 | ENHANCEMENT | Opinion | 快速记录观点门槛较高 | 评估QUICK_CAPTURE/Inbox状态 | M2/M3 | DEFERRED |
| OPT-009 | ENHANCEMENT | Persistence | 单表JSON后期查询效率有限 | 按真实负载逐步规范化 | M3 | DEFERRED |
| OPT-010 | ENHANCEMENT | Collaboration | 大G无法直接写私有仓库 | 评估自动化中转 | M2 | DEFERRED |
| OPT-011 | MINOR | Governance | 缺少统一进度看板 | ✅ 已建立 | 当前 | DONE | | 使用项目总进度看板 | 当前 | DONE |
| OPT-012 | MINOR | Governance | 每轮缺少上下轮评估和要求 | ✅ 已建立 | 当前 | DONE | | 使用双助手协作协议 | 当前 | DONE |
| OPT-013 | ENHANCEMENT | Quality | 真实案例仅3条 | 扩展至20条黄金测试集 | M1/M2 | PLANNED |
| OPT-014 | MAJOR | Semantics | support/refute/qualify/context容易混淆 | 定义Evidence Role判定标准 | M1-003 | UNDER_REVIEW |
| OPT-015 | MINOR | Versioning | V1.0到V1.1兼容策略未成文 | 建立兼容矩阵和迁移规则 | M1-003 | NEW |

## 3. 新增事项模板

```markdown
## OPT-XXX：标题
- 等级：
- 类别：
- 发现阶段：
- 发现人：
- 当前状态：
- 影响对象：
- 问题描述：
- 真实案例：
- 当前绕行方案：
- 推荐方案：
- 兼容影响：
- 数据迁移：
- 测试要求：
- 目标阶段：
- 是否需要项目负责人确认：
```

## 4. 进入开发的条件

- 有真实案例或测试证据
- 影响范围明确
- 有验收标准
- 有兼容性判断
- 有迁移方案或明确无需迁移
- 婉儿和大G共同评审
- 重大事项由项目负责人确认

## 5. 维护规则

每轮结束前：

1. 婉儿补充产品和QA发现；
2. 大G补充架构和工程发现；
3. 合并重复项；
4. 更新状态和目标阶段；
5. 已完成项保留历史记录。
