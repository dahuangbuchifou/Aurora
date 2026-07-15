# Aurora GitHub Token 与 GCM 授权操作指南 V1.0

> 适用环境：Windows 10/11、Git for Windows、Git Credential Manager、HTTPS Remote  
> Aurora 本地仓库：`E:\Aurora`  
> GitHub 仓库：`dahuangbuchifou/Aurora`  
> 认证方案：Fine-grained Personal Access Token + Git Credential Manager

## 1. 目标

```text
创建或调整Fine-grained PAT
→ 权限限制到Aurora单一仓库
→ 由GCM保存
→ 在GCM授权窗口中输入Token
→ 验证fetch、branch push、workflow push
```

## 2. 安全红线

不得：

```text
把Token粘贴到聊天、Issue、PR或Markdown
把Token写进Remote URL、PowerShell脚本、批处理或.env
通过截图暴露完整Token
把Token提交到GitHub
```

错误示例：

```text
https://<TOKEN>@github.com/dahuangbuchifou/Aurora.git
$env:GITHUB_TOKEN = "<真实PAT>"
```

正确原则：

```text
Token只粘贴到受信任的GCM/Git认证窗口
Git命令和仓库文件中不出现Token
Token泄漏后立即Revoke并重新生成
```

## 3. Fine-grained PAT配置

进入：

```text
GitHub头像
→ Settings
→ Developer settings
→ Personal access tokens
→ Fine-grained tokens
```

基本配置：

```text
Resource owner：dahuangbuchifou
Repository access：Only select repositories
Selected repositories：dahuangbuchifou/Aurora
Expiration：设置明确到期日
```

推荐权限：

| 权限 | 建议值 | 用途 |
|---|---|---|
| Metadata | Read-only | GitHub强制基础权限 |
| Contents | Read and write | 拉取和推送代码/文档 |
| Pull requests | Read and write | PR和Review |
| Actions | Read-only | 查看CI |
| Commit statuses | Read-only | 查看Commit状态 |
| Workflows | Read and write | 修改`.github/workflows/*.yml` |

暂不开放：

```text
Administration
Secrets
Variables
Environments
Webhooks
Deployments
Merge queues
Repository deletion
Actions Read and write
```

## 4. 检查Remote

```powershell
Set-Location E:\Aurora
git remote -v
```

预期：

```text
origin  https://github.com/dahuangbuchifou/Aurora.git (fetch)
origin  https://github.com/dahuangbuchifou/Aurora.git (push)
```

## 5. 检查GCM

```powershell
git credential-manager --version
git config --show-origin --get-all credential.helper
git credential-manager github list
```

预期账号：

```text
dahuangbuchifou
```

若System配置已有`manager`，但Global存在重复项，可清除Global重复配置：

```powershell
git config --global --unset-all credential.helper
git config --show-origin --get-all credential.helper
```

不要随意删除System级Helper。

## 6. 在GCM弹窗中录入Token

进入仓库并触发认证：

```powershell
Set-Location E:\Aurora
git fetch origin
```

GCM界面可能显示：

```text
Sign in with your browser
Sign in with a code
Personal Access Token
Username / Password
```

浏览器方式：

1. 确认打开GitHub官方页面；
2. 登录`dahuangbuchifou`；
3. 完成授权；
4. 返回PowerShell等待命令结束。

Token方式：

```text
Username：dahuangbuchifou
Password / Token：粘贴Fine-grained PAT
```

PAT用于替代HTTPS密码。只在GCM或Git认证窗口粘贴，不要先粘贴到PowerShell。

认证成功后，凭据由Windows Credential Manager保存。

## 7. 验证读取权限

```powershell
git fetch origin
git status
git remote -v
```

读取成功不代表写权限已验证。

## 8. 验证分支推送

禁止在`main`上测试。

```powershell
Set-Location E:\Aurora
git switch main
git pull --ff-only origin main

$branch = "test/gcm-auth-check-" + (Get-Date -Format "yyyyMMdd-HHmmss")
git switch -c $branch
git commit --allow-empty -m "chore: verify GCM authentication"
git push -u origin $branch
```

清理：

```powershell
git switch main
git push origin --delete $branch
git branch -D $branch
git status
```

最终应为：

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

## 9. 验证Workflows权限

修改`.github/workflows/*.yml`需要：

```text
Workflows：Read and write
```

在feature分支测试：

```powershell
git switch feature/m2-003c-gate3-draft-persistence
git add .github/workflows/
git commit -m "ci: verify workflow permission"
git push
```

判断：

```text
push成功
→ Workflows权限有效

refusing to allow ... create or update workflow
→ 权限不足或GCM缓存旧凭据
```

GitHub Actions优先使用仓库自动提供的`GITHUB_TOKEN`，不要把PAT写入Workflow。

## 10. 修改PAT权限

```text
头像
→ Settings
→ Developer settings
→ Personal access tokens
→ Fine-grained tokens
→ 选择Token
→ Edit
→ Update
```

通常Token字符串不变。修改后直接验证：

```powershell
git fetch origin
git push
```

## 11. 清理旧凭据

进入：

```text
控制面板
→ Credential Manager
→ Windows Credentials
```

查找：

```text
git:https://github.com
github.com
GitHub
```

确认对应当前GitHub凭据后删除，再执行：

```powershell
Set-Location E:\Aurora
git fetch origin
```

GCM会重新弹出认证窗口。

## 12. 常见错误

### 403 Forbidden

检查：

```text
Token是否过期或撤销
Repository access是否包含Aurora
Contents是否Read and write
当前账号是否为dahuangbuchifou
GCM是否缓存旧Token
```

### 可以fetch但不能push

可能是：

```text
Contents只有Read
或main受Ruleset保护
```

正确流程：

```text
feature分支push
→ Pull Request
→ Required Checks
→ merge main
```

### 工作流无法推送

检查：

```text
Workflows = Read and write
```

### GCM不弹窗

```powershell
git credential-manager github list
git fetch origin
```

需要强制更换凭据时，通过Windows Credential Manager删除对应记录。

### GitHub连接失败

检查代理：

```powershell
git config --show-origin --get http.proxy
git config --show-origin --get https.proxy
```

不再需要代理时：

```powershell
git config --global --unset http.proxy
git config --global --unset https.proxy
```

删除前确认当前网络不依赖代理。

## 13. Token轮换

```text
创建或调整新Token
→ 清理GCM旧凭据
→ 重新认证
→ fetch验证
→ 临时分支push验证
→ 撤销旧Token
```

Token泄漏时立即Revoke。

## 14. 验收清单

```text
[ ] Remote为HTTPS
[ ] GCM可用
[ ] credential.helper无冲突
[ ] GCM账号为dahuangbuchifou
[ ] Token仅授权Aurora
[ ] Metadata Read-only
[ ] Contents Read and write
[ ] Pull requests Read and write
[ ] Actions Read-only
[ ] Commit statuses Read-only
[ ] Workflows Read and write
[ ] git fetch成功
[ ] 临时分支push成功并清理
[ ] workflow文件可推送
[ ] Token未出现在URL、日志和仓库
```

## 15. 官方参考

- GitHub Docs：Managing your personal access tokens
- GitHub Docs：Permissions required for fine-grained personal access tokens
- Git Credential Manager：Command-line usage
