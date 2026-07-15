# M2-003C Gate 3 Review Round 2 — 大G独立复核 V1.0

> Review对象：`feature/m2-003c-gate3-draft-persistence`  
> Base Commit：`cdd07aa`  
> 功能修复Commit：`990acd7`  
> Head Commit：`10949fa`  
> 正确PR：`#1`  
> Review轮次：Round 2  
> 裁决：**FAIL / OWNER_CORRECTIVE_ACTION_REQUIRED**  
> 允许merge main：**NO**

## 1. 已确认修复

以下项目已经形成有效代码变化：

```text
B01 Workflow入口改为接收sessionmaker
M01 未知object_type不再默认Entity
M02 CI冻结资产/Schema/Alembic由WARN改为失败
M03 checkout/setup-python升级
自然键和operation key写入external_ids
```

但Round 1固定范围仍有核心缺口，现有457项测试没有覆盖这些缺口。

## 2. BLOCKER

### R2-B01：Bundle Hash“重算”实际上没有执行

`ReviewBundle`只有：

```text
_compute_hash()
```

没有：

```text
compute_sha256()
```

当前Preflight使用：

```python
bundle.compute_sha256() if hasattr(bundle, "compute_sha256") else None
```

所以结果永远进入`None`分支，Hash篡改不会被重新计算发现。

同时，ContextWindow Hash只检查字符串长度，没有从`content_unit_window`重建并比对。

#### 修复

- 为ReviewBundle提供公开、稳定的`compute_sha256()`；
- 或明确调用冻结的内部Hash函数并增加回归；
- 从`document_id + content_unit_window`重建ContextWindow Hash；
- Hash缺失也必须失败；
- 增加篡改Candidate、Finding、Context Unit文本、Context Hash的负向测试。

### R2-B02：Preflight宣称完整，实际缺少Workspace、Provider/Profile和引用图校验

当前代码没有实现：

```text
Workspace一致性
Provider允许列表
Profile允许列表
DataPoint.entity_id引用解析
Evidence.target_object_id引用解析
Claim相关实体引用解析
accepted依赖对象或已存在核心对象检查
```

当前所谓“Candidate引用可解析”只检查accepted ID是否存在于Candidate列表。

#### 修复

Preflight接收明确的：

```text
workspace_id
allowed_providers
allowed_profiles
existing_object_resolver
```

逐个校验Candidate依赖关系。任何悬空、跨Workspace或不允许的Provider/Profile必须在写库前失败。

### R2-B03：SourceGraphResolver的fallback绕过所有安全失败

`compute_independence_group()`捕获所有`SourceGraphError`，包括：

```text
Cycle
Dangling
Cross-workspace
ContentUnit不存在
Document不存在
Source不存在
```

然后改用`document_id`或`content_unit_id`生成fallback group。

这使任务要求的“环、悬空、跨Workspace、无法解析根Source必须失败”全部失效。

#### 修复

- 删除生产路径fallback；
- `SourceGraphError`必须原样向上抛出并导致整笔事务失败；
- 测试必须在SQLite中真实写入Source、Document、ContentUnit和DerivationLink；
- 分别验证同根、异根、环、悬空、跨Workspace；
- 测试Fixture缺少谱系对象时，应补齐Fixture，不能通过fallback绕过。

### R2-B04：Mapper仍大量编造默认值，并未Fail-closed

当前Mapper仍使用：

```text
无效EntityType → ORGANIZATION
DataPoint.value缺失 → 0
measurement_context缺失 → 默认UNKNOWN
period缺失 → 当前时间
reported_at → 当前时间
无效ClaimType → FACT_CLAIM
Prediction time_horizon → 空TimeRange
无效EvidenceRole → 默认值
无效EvidenceType → 默认值
directness → UNKNOWN
source_quality_tier → S5
evidence_strength → E1
```

`_validate_mapped_object()`只检查少数字段，无法阻止这些默认值进入数据库。

#### 修复

- 在构造核心对象前验证Candidate；
- 枚举非法、期间缺失、引用缺失立即失败；
- 使用Candidate的真实period、time_horizon、measurement_context；
- 不使用当前时间补来源期间；
- ClaimType不得默认`fact_claim`；
- EntityType、EvidenceRole、EvidenceType不得默认转换。

### R2-B05：Evidence映射链没有真正工作，Candidate引用未转为核心对象ID

`map_evidence()`直接构造：

```text
Evidence(independence_group="")
```

而核心Evidence要求`independence_group`最小长度为1，因此只要存在accepted EvidenceCandidate，该映射就应失败。

与此同时：

```text
Evidence.target_object_id
DataPoint.entity_id
```

仍保留Candidate侧ID或空ID，没有通过：

```text
candidate_id → core_object_id
```

映射表转换。

当前集成测试对四种对象数量使用`cnt >= 0`，该断言永远成立，无法证明Evidence真的写入。

#### 修复

- Mapper先产生中间Draft DTO，不要在来源组计算前构造最终Evidence；
- 按依赖顺序创建Entity/Claim/DataPoint，再解析Evidence；
- 建立Candidate ID到Core Object ID映射；
- 每种允许对象必须至少实际写入1条；
- 断言Evidence.target_object_id确实指向数据库中存在的核心对象；
- 删除`cnt >= 0`这类无效断言。

### R2-B06：B02故障回滚测试并没有故障注入

名为：

```text
test_fault_injection_rollback
```

的测试实际执行正常写入，并断言成功，没有抛出异常，也没有验证：

```text
业务对象数量=0
FAILED ProcessingRun保留
新Session可查询FAILED
```

此外，更新已有ProcessingRun失败状态时写入的是：

```text
run_status = "failure"
```

核心枚举要求：

```text
failed
```

`_finalize_success_run()`和`_finalize_failed_run()`发生异常时只记录日志，主流程仍可能返回成功或无法留下审计证据。

#### 修复

- 增加明确故障注入点；
- 在第N个对象写入后抛错；
- 新Session检查四类业务对象均为0；
- ProcessingRun状态必须为`failed`；
- error_code与error_message存在；
- Phase 3审计更新失败时，主流程不得返回成功。

### R2-B07：Operation Key重放未区分SUCCESS、FAILED和RUNNING

当前只要找到相同operation key的ProcessingRun，就直接返回：

```text
succeeded=True
total_objects=0
```

即使旧Run是：

```text
FAILED
RUNNING
```

也会被误报为成功，导致失败任务无法安全重试。

#### 修复

```text
SUCCESS → 幂等返回成功
FAILED → 允许受控重试或明确返回旧失败
RUNNING → 返回冲突/进行中，不得报告成功
```

增加FAILED重试、RUNNING冲突、SUCCESS重放测试。

### R2-B08：并发幂等仍无保障

自然键虽然写入JSON并全量扫描，但：

```text
查询
→ 判断不存在
→ 插入
```

之间没有数据库唯一约束或确定性主键。两个Session并发执行时仍可能创建重复对象。

#### 修复方案二选一

A. 使用`draft_natural_key`生成确定性对象ID，使主键承担唯一约束；  
B. 单独提出Alembic子任务，增加可索引且唯一的自然键列。

必须增加双Session竞争测试。不得只做先后顺序的跨Session测试。

## 3. MAJOR

### R2-M01：PR编号错误

交付汇总写的是：

```text
PR #3
```

但功能分支对应的是：

```text
PR #1
```

PR #3是Round 1实施指令文档分支。后续报告必须修正，避免误合并。

### R2-M02：CI授权Schema/Migration变更没有放行机制

当前任何Schema或Alembic新增都会直接失败。Gate 3本身没有授权变化，因此本轮可接受；但未来合法Migration任务也会被永久阻断。

需要登记：

```text
任务授权清单或显式CI参数
```

只有已批准Migration任务可以放行。

### R2-M03：新增模块独立Coverage证据缺失

只报告总Coverage约90%，没有证明：

```text
persistence新增模块各自>=90%
```

需要提供逐文件Coverage，尤其：

```text
validation.py
source_graph.py
mapper.py
draft_service.py
workflow/draft_persistence.py
```

## 4. Round 2结论

```text
Round 2：FAIL
剩余BLOCKER：8
剩余MAJOR：3
CI绿灯：必要但不足
允许merge PR #1：NO
允许关闭Gate 3：NO
总体治理进度：保持44%
```

按协作规范，两轮普通Review已用尽。后续属于：

```text
OWNER-DIRECTED CORRECTIVE ACTION
```

不再扩大范围，只修复本文件列出的固定项目。

## 5. 下一次Closure Verification证据

```text
1. Bundle与Context Hash真实篡改测试
2. Provider/Profile/Workspace校验
3. 完整Candidate引用图校验
4. 无fallback的真实Source谱系测试
5. Mapper零默认造值
6. Evidence真实写入和核心ID引用
7. 真故障注入与FAILED ProcessingRun
8. FAILED/RUNNING/SUCCESS三种operation key行为
9. 双Session竞争幂等
10. 新增模块逐文件Coverage
11. PR明确为#1
12. 最新gate (3.11)成功
```
