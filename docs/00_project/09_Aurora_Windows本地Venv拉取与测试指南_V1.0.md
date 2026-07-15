# Aurora Windows 本地 Venv、拉取与测试指南 V1.0

> 适用环境：Windows PowerShell  
> 本地仓库：`E:\Aurora`  
> Python：3.11  
> 虚拟环境：`E:\Aurora\.venv`  
> 本地定位：复验、故障排查和服务器资源不足时的备用环境  
> 主要执行环境：婉儿服务器

## 1. 使用原则

本地用于：

```text
偶发验证
复现CI失败
关键节点交叉测试
服务器资源不足时接管
紧急排查
```

不得在服务器和本地同时修改同一任务分支。

本地接管前确认：

```text
当前Branch
服务器HEAD Commit
服务器git status
是否有未推送Commit
本地需执行的具体任务
```

## 2. 一次性环境基线

检查Python：

```powershell
py -0p
py -3.11 --version
```

进入仓库：

```powershell
Set-Location E:\Aurora
```

仅在`.venv`不存在时创建：

```powershell
py -3.11 -m venv .venv
```

## 3. PowerShell执行策略

若激活时报错：

```text
无法加载Activate.ps1，因为在此系统上禁止运行脚本
```

为当前用户设置：

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

检查：

```powershell
Get-ExecutionPolicy
Get-ExecutionPolicy -List
```

仅临时允许当前窗口：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

关闭窗口后，`Process`设置失效。

## 4. 每次开始工作的标准入口

```powershell
Set-Location E:\Aurora
.\.venv\Scripts\Activate.ps1
```

成功后提示符出现：

```text
(.venv)
```

验证：

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -m pip --version
```

预期解释器：

```text
E:\Aurora\.venv\Scripts\python.exe
```

若不是该路径，不要继续安装依赖或测试。

## 5. 检查仓库状态

```powershell
git status
git branch --show-current
git remote -v
git log -1 --oneline
git status --short
```

工作区干净时再切换分支或拉取。

## 6. 工作区不干净时

### 需要保留

提交到正确feature分支：

```powershell
git add <明确文件>
git commit -m "<规范提交信息>"
```

### 临时变更

```powershell
git stash push -u -m "local temporary work"
git stash list
git stash pop
```

### 不确定变更

不要直接执行：

```text
git reset --hard
git clean -fd
```

先备份或确认。

## 7. 同步main

```powershell
Set-Location E:\Aurora
git switch main
git pull --ff-only origin main
git status
git log -1 --oneline
```

预期：

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

`--ff-only`只接受快进更新，本地与远程分叉时会停止，不生成意外Merge Commit。

`main`受Ruleset保护，不在本地直接推送开发Commit。

## 8. 拉取远程feature分支

更新远程引用：

```powershell
git fetch origin --prune
git branch -a
```

本地已有分支：

```powershell
git switch feature/m2-003c-gate3-draft-persistence
git pull --ff-only origin feature/m2-003c-gate3-draft-persistence
```

本地没有分支：

```powershell
git switch --track origin/feature/m2-003c-gate3-draft-persistence
```

验证：

```powershell
git branch --show-current
git rev-parse HEAD
git log -1 --oneline
git status
```

将`git rev-parse HEAD`与婉儿提供的Commit核对。

## 9. 安装或更新依赖

新环境：

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,parsers]"
```

以下文件变化时重新安装：

```text
pyproject.toml
requirements*.txt
构建配置
可选依赖定义
```

推荐始终使用：

```powershell
python -m pip
```

避免裸`pip`指向旧Python。

## 10. 环境快速验证

```powershell
python -c "import aurora, sys; print('Aurora:', aurora.__version__); print('Python:', sys.version); print('Executable:', sys.executable)"
```

解析依赖验证：

```powershell
python -c "import bs4, lxml, httpx, pdfplumber, webvtt; print('Parser dependencies verified')"
```

确认`.venv`被Git忽略：

```powershell
git check-ignore .venv
```

预期：

```text
.venv
```

## 11. 测试分级

### 测试收集

```powershell
python -m pytest --collect-only -q
```

这里失败通常属于：

```text
依赖缺失
模块导入错误
测试配置错误
```

### 单文件

```powershell
python -m pytest tests/unit/test_example.py -q
```

### 单测试

```powershell
python -m pytest tests/unit/test_example.py::test_name -q
```

### 关键词

```powershell
python -m pytest -k "draft_persistence" -q
```

### 全量测试

```powershell
python -m pytest -q
```

### Coverage

```powershell
python -m pytest --cov=aurora --cov-branch --cov-report=term-missing --cov-fail-under=90
```

Aurora总Coverage门槛：

```text
>= 90%
```

新增模块还应满足任务卡规定的独立Coverage。

## 12. 与GitHub Actions对齐

本地复现CI至少执行：

```powershell
python -m pip install -e ".[dev,parsers]"
python -m pytest -q
python -m pytest --cov=aurora --cov-branch --cov-report=term-missing --cov-fail-under=90
```

CI失败而本地成功时检查：

```text
Python版本
依赖组
操作系统差异
环境变量
SQLite版本
路径大小写
冻结资产
Workflow安装步骤
```

GitHub Runner是全新环境，不会继承本地未声明依赖。

## 13. 测试后的仓库检查

```powershell
git status --short
```

理想结果为空。

通常不提交：

```text
.coverage
htmlcov/
.pytest_cache/
__pycache__/
临时SQLite数据库
日志文件
```

除非仓库规范明确要求。

## 14. 本地验证报告模板

```text
【Aurora本地验证】

Branch：
HEAD Commit：
Python：
Executable：
Aurora Version：

Target tests：
Collected：
Passed：
Failed：
Warnings：
Coverage：

git status：
异常摘要：
日志/截图：
```

辅助命令：

```powershell
git branch --show-current
git rev-parse HEAD
python --version
python -c "import sys; print(sys.executable)"
git status --short
```

## 15. PR合并后更新本地

```powershell
Set-Location E:\Aurora
git switch main
git pull --ff-only origin main
git fetch origin --prune
```

确认分支已合并：

```powershell
git branch --merged main
```

安全删除本地分支：

```powershell
git branch -d feature/<branch-name>
```

`-d`会拒绝删除未合并分支，比`-D`安全。

## 16. 退出虚拟环境

```powershell
deactivate
```

## 17. 常见故障

### Activate.ps1被禁止

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Python指向错误目录

```powershell
where.exe python
python -c "import sys; print(sys.executable)"
```

正确第一项：

```text
E:\Aurora\.venv\Scripts\python.exe
```

### pip指向旧Python

```powershell
python -m pip --version
```

统一使用`python -m pip`。

### 缺少bs4

```text
ModuleNotFoundError: No module named 'bs4'
```

修复：

```powershell
python -m pip install -e ".[dev,parsers]"
```

### pull --ff-only失败

```powershell
git status
git log --oneline --graph --decorate --all -20
```

不要立即`reset --hard`或force push。

### 重建.venv

```powershell
deactivate
Remove-Item -Recurse -Force .venv
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,parsers]"
```

### Git认证失败

```powershell
git credential-manager github list
git remote -v
git fetch origin
```

按《Aurora GitHub Token与GCM授权操作指南》处理。

## 18. 推荐日常命令块

验证main：

```powershell
Set-Location E:\Aurora
.\.venv\Scripts\Activate.ps1

git switch main
git pull --ff-only origin main
git status

python --version
python -c "import sys; print(sys.executable)"
python -m pytest -q
```

验证feature分支：

```powershell
Set-Location E:\Aurora
.\.venv\Scripts\Activate.ps1

git fetch origin --prune
git switch feature/<branch-name>
git pull --ff-only origin feature/<branch-name>

git rev-parse HEAD
python -m pip install -e ".[dev,parsers]"
python -m pytest -q
python -m pytest --cov=aurora --cov-branch --cov-report=term-missing --cov-fail-under=90
git status --short
```

## 19. 验收清单

```text
[ ] 当前目录为E:\Aurora
[ ] (.venv)已激活
[ ] Python为3.11
[ ] sys.executable指向E:\Aurora\.venv
[ ] git status已检查
[ ] main通过--ff-only同步
[ ] feature HEAD与服务器一致
[ ] dev和parsers依赖已安装
[ ] collect-only成功
[ ] 全量pytest成功
[ ] Coverage达标
[ ] 测试后工作区clean
[ ] 结果按模板反馈
```

## 20. 官方参考

- Python Docs：venv — Creation of virtual environments
- Git Documentation：git pull
- pytest Documentation：How to invoke pytest
