# Aurora 协作与评审规范 V2.1

> **文档路径**：`docs/00_project/06_Aurora_协作与评审规范_V2.1.md`
> **状态**：FROZEN / EFFECTIVE
> **适用范围**：Aurora 全项目，自 M2-003B Gate 2 起正式执行
> **项目负责人**：大黄
> **技术负责人**：大G
> **方向监控与独立检查**：婉儿
> **版本日期**：2026-07-13

---

## 1. 制定目的

本规范用于同时实现以下目标：

1. 保证 Aurora 的技术方向、数据正确性和认知安全；
2. 减少重复开发、反复补充标准和无边界 Review；
3. 让大G对技术交付承担完整责任；
4. 让婉儿能够了解并检查大G的完整工作过程；
5. 让大黄只处理范围、优先级和重大争议；
6. 通过前置标准、证据化交付和最多两轮联合 Review 提高整体效率。

核心协作关系：

```text
大G生产完整技术交付与证据
→ 婉儿按冻结标准独立检查
→ 双方共同完成每一轮Review并形成统一记录
→ 大黄只裁断重大争议和BLOCKER
```

禁止形成：

```text
大G实现一套
→ 婉儿重新实现一套
→ 大黄比较两套结果
```

---

## 2. 基本原则

### 2.1 标准前置

每个任务必须先建立并共同确认：

```text
任务范围
非目标
输入
输出
允许修改目录
禁止修改目录
验收Checklist
测试命令
质量门禁
交付证据
退出条件
```

任务卡冻结后，验收原则上只按该 Checklist 执行。

### 2.2 单一技术责任人

同一任务只能有一个主要技术交付责任人。

默认：

```text
大G = Technical Lead + Delivery Owner
```

婉儿不与大G并行开发同一套生产实现，除非大黄明确安排独立验证实验。

### 2.3 证据化验收

"已完成""测试通过""效果正常"不能作为独立验收结论。

正式交付必须包含：

```text
Git Commit
Changed Files
测试命令
测试结果
Coverage
Schema Diff
Artifact Hash
已知限制
Checklist逐项结果
```

### 2.4 Review不扩大任务范围

Review中发现的新事项必须先分类：

```text
原任务缺陷
新BLOCKER
变更请求
待优化事项
```

新功能或范围扩展不得直接作为原任务未通过的理由。

### 2.5 BLOCKER不得通过延期绕过

两轮 Review 上限适用于普通 Review，不适用于绕过以下问题：

```text
数据损坏
安全漏洞
核心Schema错误
幂等或身份错误
证据链错误
事务错误
硬门禁失败
严重回归
不可复现
敏感数据泄露
```

存在上述 BLOCKER 时，节点不得关闭，必须提交大黄裁断。

### 2.6 冻结资产保护

每个阶段开始时，任务卡必须列出冻结资产，并生成 SHA-256 清单。

冻结资产至少包括适用的：

```text
核心Schema
黄金Fixture
Gate报告
验收基线
已关闭阶段的关键脚本
不可变ReviewBundle
```

执行规则：

1. 冻结资产清单必须记录文件路径、SHA-256、冻结Commit和责任节点；
2. 开发期间，任何未在任务卡中明确授权的冻结资产修改均视为 BLOCKER；
3. 确需修改冻结资产时，必须先停止当前节点，说明原因并取得大G与婉儿共同确认；
4. 修改可能影响已关闭Gate时，必须重跑对应Gate；
5. 节点关闭前必须重新计算并核对全部冻结资产Hash；
6. Hash不一致且无批准记录时，节点不得关闭。

建议清单路径：

```text
docs/qa/<task-id>_frozen_assets.sha256
```

---

## 3. 角色与职责

## 3.1 大黄：Project Owner / Final Arbiter

大黄负责：

- 项目目标；
- 优先级；
- 资源投入；
- 里程碑范围；
- 核心架构争议；
- BLOCKER裁断；
- 重大延期；
- 是否接受非阻塞遗留问题；
- 大节点最终关闭。

大黄不承担日常代码Review。

以下事项必须提交大黄：

```text
修改冻结核心Schema
新增核心对象类型
改变里程碑范围
降低安全或认知门禁
引入明显费用
远程发送PRIVATE以上数据
两轮Review后仍存在BLOCKER
大G与婉儿无法达成一致
```

---

## 3.2 大G：Technical Lead / Delivery Owner / Architecture Owner

大G负责：

- 任务技术拆解；
- 架构设计；
- 数据合同；
- 生产代码；
- 测试代码；
- Fixture；
- 迁移或Schema；
- 文档；
- 分支和Commit；
- Pull Request；
- 自我QA；
- 交付证据；
- Review问题集中修复；
- 技术风险登记；
- 节点交付完整性。

在已经冻结的任务范围内，大G可直接决定：

```text
内部模块拆分
类和函数的内部实现
测试组织
不改变公共接口的依赖注入方式
不改变外部错误契约的内部错误处理
确定性实现细节
不改变已冻结契约的非核心DTO内部调整
不影响公共接口和冻结资产的内部重构
```

不需要逐项重新取得批准。

以下变化虽可由大G提出技术方案，但实施前必须知会婉儿，并在任务卡或PR中明确记录：

```text
已有模块公共API变化
外部可观察错误码或状态变化
跨模块依赖方向变化
大规模重写替代原实现
冻结DTO字段增删或语义变化
对既有Fixture生成方式的变化
```

"重构"不作为规避Review的理由。无法证明公共接口、数据契约和行为兼容时，应按"重写或接口变更"处理。

大G不得单方面决定：

```text
修改核心Schema
新增核心对象
降低硬门禁
扩大任务范围
直接合并main
更改仓库保护策略
```

---

## 3.3 婉儿：Direction Monitor / Independent Reviewer / QA Inspector

婉儿负责：

- 共同确认前置任务标准；
- 检查实现是否偏离项目方向；
- 按冻结 Checklist 独立核查；
- 检查 Commit、测试、Coverage、Schema Diff 和 Artifact；
- 检查边界条件和回归；
- 审查大G工作证据；
- 一次性汇总问题；
- 与大G共同形成每轮 Review 结论；
- 检查总进度看板和待优化事项是否按节点更新。

婉儿提出问题时必须包含：

```text
Checklist编号
严重等级
文件或对象位置
复现步骤
实际结果
预期结果
是否阻塞
建议处理方式
```

婉儿原则上不：

- 并行重写大G的生产代码；
- 在 Review 中追加未冻结的新功能；
- 用模拟结果代替对真实交付的核查；
- 只给结论而不给证据；
- 将建议项标记为BLOCKER。

---

## 4. GitHub权限和安全规范

## 4.1 权限模型

大G获得仓库级、最小必要的分支和 Pull Request 工作权限。

当前建议的最小权限：

| GitHub权限 | 建议 | 用途 |
|---|---|---|
| Metadata | Read-only（必需） | 读取仓库基础元数据 |
| Contents | Read and write | 创建分支、提交和推送任务代码 |
| Pull requests | Read and write | 创建、更新和回复PR |
| Actions | Read-only | 查看CI运行与日志 |
| Commit statuses | Read-only | 查看提交状态 |
| Issues | No access（当前） | 项目当前未正式使用Issue Tracker |
| Merge queues | No access | 当前不使用Merge Queue |
| Workflows | No access（默认） | 仅在任务明确要求修改`.github/workflows/`时临时增加 |

如果后续正式启用GitHub Issue Tracker，再将 `Issues` 调整为 `Read and write`。

仅在冻结任务卡明确需要时增加其他权限；任务结束后应重新评估并移除临时权限。

默认禁止：

```text
直接Push main
Force Push
删除受保护分支
修改Branch Protection
管理Repository Secrets
修改成员或管理员权限
修改仓库可见性
未经批准创建Release或Tag
```

正式流程：

```text
大G创建任务分支
→ 提交代码和证据
→ 创建Pull Request
→ 大G与婉儿联合Review
→ 满足退出条件
→ 由获授权人员合并main
```

## 4.2 凭证安全

个人访问令牌属于敏感凭证。

禁止：

```text
在Chat、Issue、PR、Markdown、日志或截图中公开Token
将Token写入仓库
将Token写入.env.example
在命令历史中长期保留明文Token
```

凭证应存放在：

```text
操作系统凭证管理器
Git credential manager
受控环境变量
GitHub Actions Secret
受批准的密钥管理服务
```

Token只授予：

```text
指定Aurora仓库
有限有效期
最小必要权限
```

长期自动化接入优先评估 GitHub App。

## 4.3 分支规则

分支命名：

```text
feature/<task-id>-<short-name>
fix/<task-id>-<short-name>
docs/<task-id>-<short-name>
```

每个任务必须记录：

```text
base_commit
branch_name
head_commit
merge_base
```

任务分支不得混入其他任务的无关修改。

---

## 5. 任务前置标准

每个任务开始前建立任务卡。

## 5.1 任务卡分级

任务卡分为：

```text
完整任务卡
轻量任务卡
```

### 完整任务卡

以下任一条件成立时必须使用完整任务卡：

- 新功能或新模块；
- 修改公共API、Schema、状态机、事务或持久化；
- 涉及安全、隐私、凭证或远程服务；
- 涉及冻结资产；
- 修改超过一个主要模块；
- 需要Gate或里程碑验收；
- 可能影响数据正确性或后续架构。

固定字段：

```text
任务ID：
任务名称：
目标：
业务价值：
Git基线Commit：
输入：
输出：
范围内：
范围外：
允许修改目录：
禁止修改目录：
冻结资产：
依赖：
交付文件：
验收Checklist：
测试命令：
Coverage要求：
安全门禁：
性能观察：
证据要求：
已知限制：
退出条件：
目标分支：
计划节点：
```

### 轻量任务卡

同时满足以下条件时可以使用：

- 仅文档、测试补充、拼写修复或局部内部实现修正；
- 不修改公共API；
- 不修改核心或应用Schema；
- 不修改冻结资产，或修改已在任务卡中明确授权；
- 不改变数据语义、状态机、事务和安全边界；
- 可在一次提交和一组局部测试中完成。

固定字段：

```text
任务ID：
目标：
Git基线Commit：
允许修改文件：
禁止事项：
验收Checklist：
测试命令：
交付Commit：
退出条件：
```

如执行中发现不再满足轻量条件，必须升级为完整任务卡，且升级确认不计入Review轮次。

## 5.2 共同确认

任务卡需由大G和婉儿共同确认。

确认过程不计入 Review 轮次。

确认结果：

```text
TASK_SPEC_APPROVED
```

出现分歧时：

- 技术实现分歧：大G给出方案和依据；
- 方向或范围分歧：婉儿提出偏离证据；
- 无法一致：提交大黄裁断。

任务卡确认后方可进入生产实现。

---

## 6. 交付回复标准

## 6.1 大G正式交付格式

大G交付必须严格按以下顺序：

### 1. 当前状态

```text
IN_PROGRESS / READY_FOR_REVIEW / BLOCKED
```

### 2. Git证据

```text
Base Commit
Branch
Head Commit
PR
```

### 3. Checklist完成情况

逐项列出：

```text
ID
结果
证据
```

### 4. Changed Files

按：

```text
Added
Changed
Deleted
```

分类。

### 5. 测试与Coverage

包含：

```text
collect数量
passed
failed
warnings
执行时间
总Coverage
新增模块Coverage
```

### 6. 架构与Schema变化

明确：

```text
核心Schema是否变化
应用Schema是否变化
Alembic是否变化
```

### 7. 安全与回归

列出硬门禁和全量回归结果。

### 8. 已知限制

不得隐藏或使用模糊描述。

### 9. 待优化事项

列出新增、关闭和延期项。

### 10. 请求婉儿核查的项目

必须是明确清单，不得只写"请检查"。

---

## 6.2 婉儿正式Review格式

婉儿必须严格按以下顺序：

### 1. 总体裁决

```text
PASS
CONDITIONAL_PASS
FAIL
```

### 2. Checklist逐项结果

每项包含证据。

### 3. BLOCKER

没有则明确写：

```text
None
```

### 4. MAJOR

没有则明确写：

```text
None
```

### 5. MINOR / ENHANCEMENT

单独列出，不与阻塞项混合。

### 6. 测试与证据核查

包括：

```text
Commit
Changed Files
pytest
Coverage
Schema Diff
Artifact Hash
```

### 7. 是否允许进入下一节点

```text
YES / NO / YES_WITH_BACKLOG
```

### 8. 大G需要修正的清单

必须一次性列出，使用问题编号。

---

## 7. 两轮联合Review规则

每一轮 Review 必须由大G和婉儿共同完成。

单方检查或单方声明不构成完整 Review 轮次。

## 7.1 每轮共同流程

每轮包含四个步骤：

### Step 1：大G交付前自检

大G按冻结 Checklist：

- 逐项检查；
- 提供证据；
- 修复自检发现的原任务缺陷；
- 运行必要回归；
- 确认冻结资产Hash；
- 给出自检结论。

大G自检发现的原任务缺陷必须在正式交付前修复，不应作为"已知问题"递交婉儿继续发现。

只有同时满足以下条件时，任务才能标记：

```text
READY_FOR_REVIEW
```

- 自检Checklist已完成；
- BLOCKER为0；
- 已知MAJOR不违反退出条件；
- 非阻塞限制已登记；
- 测试和交付证据齐全。

交付中的"已知限制"只允许记录非阻塞限制、明确范围外事项和已登记Backlog，不能代替对原任务缺陷的修复。

### Step 2：婉儿独立检查

婉儿使用同一 Checklist：

- 独立验证；
- 不依赖大G结论；
- 汇总全部问题；
- 给出初步裁决。

### Step 3：联合收敛

双方共同确认：

```text
哪些问题成立
严重等级
修复范围
是否属于原任务
是否转待优化
统一Review结论
```

### Step 4：形成统一记录

每轮必须形成一份共同记录：

```text
Review Round
大G结论
婉儿结论
共同结论
问题清单
处理决定
双方确认
```

双方对记录确认后，该轮才算完成。

---

## 7.2 Review Round 1

前置条件：

```text
大G自检通过
任务状态 = READY_FOR_REVIEW
```

目标：

- 对完整首次交付进行联合 Review；
- 婉儿独立验证大G已通过自检的交付；
- 一次性发现并登记自检未覆盖的问题；
- 在联合收敛后冻结修复清单。

Round 1不是把大G已知但未修复的问题转交给婉儿处理的阶段。

Round 1完成后，大G集中修复联合确认的问题。

Round 1结束后不得以普通问题形式追加新范围。

---

## 7.3 Review Round 2

只检查：

```text
Round 1问题是否解决
修复是否引入回归
原Checklist是否全部满足
```

Round 2原则上不得增加新功能要求。

在Round 2中新发现的问题：

- 原修复导致的回归：属于本轮；
- 原任务中漏检的BLOCKER：立即登记并提交裁断；
- 新需求或建议：进入待优化清单。

---

## 7.4 两轮后的处理

### BLOCKER

```text
节点不得关闭
→ 提交大黄裁断
→ 决定继续修复、回滚或调整范围
```

不允许仅写入待优化清单后继续。

### MAJOR但非阻塞

仅在同时满足以下条件时可延期：

- 不影响数据正确性；
- 不影响安全；
- 不违反核心Schema；
- 不破坏后续架构；
- 有可接受的临时方案；
- 有明确责任人；
- 有明确目标节点。

处理：

```text
CONDITIONAL_PASS
→ 登记待优化清单
→ YES_WITH_BACKLOG
```

### MINOR / ENHANCEMENT

```text
登记待优化清单
→ 节点正常关闭
```

两轮后不进行第三轮普通Review。

---

## 8. Review联合记录模板

```markdown
# <Task ID> Review Round <1|2>

## 基本信息

- Base Commit:
- Head Commit:
- PR:
- Checklist Version:
- Review Date:

## 大G自检结论

- Result:
- Evidence:
- Known Issues:

## 婉儿独立检查结论

- Result:
- Evidence:
- Findings:

## 联合问题清单

| ID | Checklist | Severity | Finding | Decision | Owner | Target |
|---|---|---|---|---|---|---|

## 联合结论

- Final Result:
- Next Node:
- Backlog Items:
- Escalation Required:

## 双方确认

- 大G：CONFIRMED / DATE
- 婉儿：CONFIRMED / DATE
```

---

## 9. 待优化事项管理

文档：

```text
docs/00_project/05_Aurora_待优化事项清单_<version>.md
```

字段：

```text
ID
标题
等级
类别
发现节点
问题描述
临时方案
责任人
目标节点
状态
关闭证据
```

状态枚举：

```text
PROPOSED
APPROVED
IN_PROGRESS
IMPLEMENTED_PENDING_QA
DONE
DEFERRED
DEFERRED_BY_SCOPE
BLOCKED
```

更新规则：

- BLOCKER：发现后立即登记；
- MAJOR/MINOR：节点关闭时统一更新；
- 节点关闭后不得存在未登记遗留问题；
- DONE必须附Commit或QA证据；
- DEFERRED必须有目标节点或重新评审条件。

---

## 10. 项目总进度与资源看板

文档：

```text
docs/00_project/03_Aurora_项目总进度与资源看板_<version>.md
```

只在以下事件更新：

```text
任务正式启动
Gate通过
子阶段关闭
里程碑关闭
资源需求变化
范围或权重变化
```

不因为单个普通Bug修复修改总体进度。

每次更新必须包含：

```text
总体进度
里程碑状态
当前任务状态
下一任务
关键资源
当前BLOCKER
待决策事项
最后验证Commit
```

---

## 11. 节点关闭条件

一个节点只有在以下条件满足后才能关闭：

```text
任务Checklist完成
必要测试通过
硬门禁通过
两轮Review规则执行完成或Round 1直接PASS
BLOCKER为0
非阻塞遗留项已登记
总进度看板已更新
待优化事项清单已更新
共同Review记录已归档
```

Round 1直接PASS时无需为了形式执行Round 2。

---

## 12. 当前M2-003B适用方式

M2-003B Gate 1 已完成并合并，不因本规范回滚。

本规范从 Gate 2 任务卡确认开始正式执行：

```text
大G起草Gate 2任务卡
→ 婉儿共同确认
→ TASK_SPEC_APPROVED
→ 大G实施并完成交付前自检
→ READY_FOR_REVIEW
→ 双方完成Round 1
```

若Round 1 PASS：

```text
Gate 2关闭
→ 更新总进度看板与待优化事项清单
→ 进入下一节点
```

若Round 1存在问题：

```text
冻结Round 1修复清单
→ 大G集中修复
→ 双方共同完成Round 2
→ PASS / YES_WITH_BACKLOG / 大黄裁断
```

Gate 1相关遗留事项如非BLOCKER，统一登记到待优化事项清单，不重新开启普通Review。

---

## 13. 文档生效

本规范需完成：

```text
大黄确认
大G确认
婉儿确认
```

确认后状态变更为：

```text
FROZEN / EFFECTIVE
```

任何角色不得单方面修改本规范。

修改流程：

```text
提出变更
→ 大G评估技术影响
→ 婉儿评估治理影响
→ 大黄批准
→ 发布新版本
```

---

## 14. 签署

```text
大黄：APPROVED
日期：2026-07-13

大G：APPROVED
日期：2026-07-13

婉儿：APPROVED
日期：2026-07-13
```
