# M2-003B Gate 2 Review Checklist V1.0

> 大G与婉儿必须使用同一份Checklist。

## A. Git与范围
- [ ] A-01 Base Commit已记录
- [ ] A-02 分支名称正确
- [ ] A-03 工作区交付前clean
- [ ] A-04 Changed Files全部属于允许范围
- [ ] A-05 无范围外功能
- [ ] A-06 无远程Provider或真实LLM调用

## B. 冻结资产
- [ ] B-01 开发前SHA清单存在
- [ ] B-02 开发后SHA全部匹配
- [ ] B-03 V1/V1.1核心Schema未变化
- [ ] B-04 Gate 0资产未变化
- [ ] B-05 Gate 1冻结契约未变化或有批准记录
- [ ] B-06 无Alembic Revision

## C. 对抗Fixture
- [ ] C-01 Prediction污染
- [ ] C-02 估值建议污染
- [ ] C-03 Prompt Injection
- [ ] C-04 虚假Quote
- [ ] C-05 伪造/窗外/跨Document Unit
- [ ] C-06 高confidence污染
- [ ] C-07 independence_group越权
- [ ] C-08 Provider Fixture与Expected Results独立

## D. 硬门禁
- [ ] G2-1 Fact污染率=0
- [ ] G2-2 虚假Quote接受率=0
- [ ] G2-3 非法Unit接受率=0
- [ ] G2-4 Prompt Injection越权率=0
- [ ] G2-5 Provider独立性越权接受率=0
- [ ] G2-6 高confidence改变知识状态次数=0

## E. 行为与审计
- [ ] E-01 失败候选不进入accepted列表
- [ ] E-02 失败候选进入rejected列表
- [ ] E-03 Finding code稳定
- [ ] E-04 Finding severity正确
- [ ] E-05 ReviewBundle Hash可重放
- [ ] E-06 输入对象不被修改
- [ ] E-07 不创建核心Fact
- [ ] E-08 不写认知对象数据库

## F. 确定性
- [ ] F-01 每个对抗Fixture重复10次
- [ ] F-02 Candidate排序稳定
- [ ] F-03 Finding排序稳定
- [ ] F-04 accepted/rejected稳定
- [ ] F-05 Bundle Hash稳定

## G. 测试
- [ ] G-01 collect-only成功
- [ ] G-02 全量pytest 0 failed
- [ ] G-03 0 warnings
- [ ] G-04 总Coverage>=90%
- [ ] G-05 新增模块Coverage>=90%
- [ ] G-06 Python 3.11.7本地通过
- [ ] G-07 Python 3.11.13目标环境待QA/通过

## H. 文档与节点
- [ ] H-01 Gate 2报告完整
- [ ] H-02 Round 1共同记录完整
- [ ] H-03 待优化清单更新
- [ ] H-04 项目看板更新
- [ ] H-05 BLOCKER=0
- [ ] H-06 下一节点结论明确
