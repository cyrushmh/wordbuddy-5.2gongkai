# GitHub Actions 排错手册（含本仓库一次真实复盘）

这份文档回答一个问题：**CI 红了，怎么在 5 分钟内知道到底哪一步、为什么红的。**

结论先行：**日志里最后出现的那行，往往不是原因。** 本次事故里，日志末尾是
`Node.js 20 is deprecated ... actions/download-artifact@v4`，看上去像是它搞挂的，
实际上那个 action 状态是 `success`——它只是"路过时刷了条警告"。真正的凶手在
往上十几行的 `##[error]` 里。

---

## 一、怎么读一份 Actions 日志

### 1. 先分清「警告」和「错误」

| 前缀 | 含义 | 会让 job 红吗 |
|---|---|---|
| `##[error]` | 这一步真的失败了 | **会**，紧跟其后的 `Process completed with exit code N` 就是它 |
| `##[warning]` | 提示，通常是生态演进（Node 版本、弃用 API） | 不会 |
| `##[group]` / `##[endgroup]` | 折叠块的起止，纯排版 | 不会 |
| `(node:PID) [DEPxxxx] DeprecationWarning` | action 自身的 Node 依赖过时 | 不会 |

**实操**：拿到日志先 `grep -n "##\[error\]"`，从上往下读第一条。**不要从末尾读。**

### 2. 常见退出码速查

| 退出码 | 常见来源 |
|---|---|
| `1` | 脚本里 Python / Node 抛了未捕获异常；或命令返回非零 |
| `2` | shell 语法错误、参数错误 |
| `120` | **Python 的特征码**：解释器退出阶段 flush stdout 失败（典型 `BrokenPipeError`） |
| `124` | `timeout` 命令超时 |
| `125`–`127` | `docker run` 失败 / 命令找不到 |
| `128+N` | 被信号 N 杀死；`141` = `128+13` = `SIGPIPE`（管道下游先关了） |
| `143` | `128+15` = `SIGTERM`，通常是 job 被取消或超时 |

看到 `120` 基本可以直接锁定"往已关闭的管道写东西"；看到 `141` 同理但进程是被信号杀的。

### 3. 拉日志的正确姿势（不用开网页）

本仓库已经把这套流程固化成脚本，先试它：

```bash
export GH_TOKEN=<你的 PAT>
python3 tools/ci_triage.py                  # 最近一次失败的运行
python3 tools/ci_triage.py --run <RUN_ID> --context 12
```

输出是：run 概览 → 各 job 成败 → **每个失败 job 的 step 列表 + `##[error]` 上下文**
→ 警告汇总（明确标注"不是失败原因"）。手工做的话，命令如下：

```bash
# 1) 最近的 run：id / 状态 / 结论 / 工作流名
gh api /repos/<owner>/<repo>/actions/runs \
  -q '.workflow_runs[] | "\(.id)\t\(.status)\t\(.conclusion)\t\(.name)\t\(.head_branch)"'

# 2) 某个 run 的 jobs 与 steps —— 一眼看出是"哪个 job 的哪一步"红的
gh api /repos/<owner>/<repo>/actions/runs/<RUN_ID>/jobs \
  -q '.jobs[] | "JOB \(.id)\t\(.name)\t\(.conclusion)"'
gh api /repos/<owner>/<repo>/actions/runs/<RUN_ID>/jobs \
  -q '.jobs[] | .steps[] | "  \(.number) \(.name) => \(.conclusion)"'

# 3) 拉具体 job 的文本日志（这步才是真相）
gh api /repos/<owner>/<repo>/actions/jobs/<JOB_ID>/logs > job.log
grep -n "##\[error\]" job.log
```

自己写脚本拉日志时有两个坑（本仓库脚本都处理了）：

- **`Accept` 必须是 `application/vnd.github+json`**，传 `text/plain` 会 415；
- **日志下载会 302 到 Azure blob**，重定向请求**不能带 GitHub 的 Authorization**，
  否则 Azure 回 401 `InvalidAuthenticationInfo`；要么用 `gh api`（它自己会处理），
  要么手动接 302 的 `Location` 再发一个不带凭据的请求。

> 沙箱里 `git push` 常年 `GnuTLS recv error (-110)` / 443 超时，但 **HTTPS API 通常是通的**。
> 推不上去的时候别急着判"网断了"，可以改用 API 读日志；要写回仓库则可用
> Git Data API 直接移 ref（`PATCH /repos/{repo}/git/refs/heads/{ref}`），
> 本仓库的 `tools/sync_to_github.py` 走的就是这条路。

### 4. Node.js 20 弃用警告要不要管

```text
##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are
being forced to run on Node.js 24: actions/download-artifact@v4.
```

- 它**不是错误**，当前只是被强制跑在 Node 24 上，能正常工作；
- 但 runner 日后会真的停掉 Node 20 运行时，届时声明 node20 的 action 才会挂；
- **实测（2026-10-08）：把 v4 升到 v5 之后，这条警告原样还在**——
  `... actions/download-artifact@v5.`，一字不差，只是版本号变了。
  也就是说"升版本消警告"这个想当然的做法**没用**，v5 自身仍声明 node20。
  正确的处置是：认清它是噪音、别让它干扰你找真正的 `##[error]`，然后等上游发版。
  （升级本身仍然值得做——为了在 Node 20 真正下线时不被打个措手不及；
  但**同一条流水线里 upload 与 download 必须一起升**，两头的 artifact 后端是配套的。）

---

## 二、本仓库的真实复盘：exit 120 与 exit 1

2026-10-07，`Build Python Layer` 工作流在 **Linux 与 Windows** 上红、macOS 绿，
三条 job 报错长得不一样，但实际是**两个互不相干的 bug**。

### 失败 A：Linux / macOS / Windows 三平台 job 里的 exit 120

日志关键行：

```text
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
##[error]Process completed with exit code 120.
```

工作流里写的是：

```bash
"$PY" "$PYZ" hardware | head -6
```

**机理**：`head` 读满 6 行就退出并关闭管道读端。Python 侧输出被重定向到管道时是
**块缓冲**，`print` 常常一路成功，错误憋到**解释器退出阶段那最后一次 flush** 才爆发——
那时已经跑出 `main()` 的 `try` 之外，抓不到，于是解释器打印 `Exception ignored ...`
并把退出码抬成 **120**。再叠加 GitHub runner 默认给 bash 加的 `set -o pipefail`，
整步判失败。

> macOS 那次是绿的：同样的写法，但那台机器上输出量/时序恰好没触发，属于**竞态**。
> 这种"有时红有时绿"的失败，十有八九是竞态或环境差异，不要当成玄学跳过。

**修法（两边都做了）**：

1. 产品侧 `cli.main()`：捕获 `BrokenPipeError` → 把 fd 1 指向 `/dev/null` 再返回 0；
   并且在返回前**主动 flush 一次**标准流，专门覆盖"退出阶段才炸"这条路径。
2. 工作流侧：不再写 `cmd | head -n`，改成先落盘再取前几行——截断与退出码互不干扰。

```bash
"$PY" "$PYZ" hardware > hardware.txt
head -6 hardware.txt
```

顺带一条通用经验：**CI 里不要用 `| head` / `| head -n` 去截断一个你自己写的程序的输出。**
要么让程序自己支持 `--limit`，要么落盘再截。

### 失败 B：Windows job 的 exit 1

日志关键行：

```text
File "...\encodings\cp1252.py", line 19, in encode
UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-4: character maps to <undefined>
##[error]Process completed with exit code 1.
```

**机理**：Windows 上 Python 拿**控制台 ANSI 代码页**当 stdout 编码——英文 runner 镜像是
`cp1252`，中文 Windows 常见 `cp936/gbk`。本 CLI 大量输出中文以及 `→` `✓` 这类符号，
在 cp1252 下**第一次 print 就崩**。这不是 CI 特有的问题：**任何英文版 Windows 用户
在 cmd/PowerShell 里跑 `sysweeper detect` 都会崩**。macOS/Linux 是 UTF-8，所以永远测不出来。

**修法**：`cli.harden_streams()` 在 `main()` 最开头把 stdout/stderr `reconfigure` 成
UTF-8（`errors="replace"`）；`reconfigure` 不可用就退一步只改 `errors`，宁可显示成问号也不崩。

守护用例（三平台 job 都跑）：

```bash
PYTHONIOENCODING=cp1252 "$PY" "$PYZ" detect > cp1252.txt
PYTHONIOENCODING=ascii  "$PY" "$PYZ" detect > ascii.txt    # 最坏情况：任何非 ASCII 都编不出来
```

### 修完之后的验证

- 本地复现旧行为：`rc=120`（含一模一样的 `Exception ignored ... BrokenPipeError` 两行）；
  修复后同一条命令 `rc=0`。
- 本地复现旧崩溃：`PYTHONIOENCODING=cp1252` 下 `UnicodeEncodeError`；修复后 `rc=0` 且中文正常。
- 新增 `tests/test_streams.py`（10 个用例，单元级 + 子进程级两层覆盖）。
- 全量：`PYTHONPATH=src/python python3 -m pytest -q` → **418 passed / 3 skipped**。
- **真机 CI 绿灯（run 37682971131）**：Linux / macOS / Windows 三个 job 全 `success`，
  Windows 上新增的「窄编码控制台不崩」步骤确实打印出了中文「探测结果：`platform: windows`」，
  cp1252 与 ascii 两种编码都没崩 —— 之前"只在 Linux 上模拟"的未验证项至此坐实。
- **一个被打脸的推测**：原以为把 artifact action 升到 v5 就能消掉 Node 20 警告，
  真机日志证明**消不掉**（`... download-artifact@v5.` 照样警告）。已在上文改正。

---

## 三、秒败且没有日志：Actions 分钟额度墙（2026-10-22 复盘）

这一节讲一类**完全没有日志可看**的失败。2026-10-20 07:42 UTC 起，本仓库
`Build Python Layer`、`Audit Standards EOL`、`Audit Concept Mesh` 三个工作流
**每次推送必红**，且换了任何 commit 都红——包括刚刚还全绿的那几个文件。

### 1. 症状签名（三条同时满足）

```text
job.conclusion = "failure"
job.steps       = []          # 一步都没执行
job.runner_id   = 0           # 从未分配到 runner
job.runner_name = ""
started_at → completed_at ≈ 3 秒
拉日志 → HTTP 404 "The specified blob does not exist"（BlobNotFound）
```

`gh api` 一眼判定：

```bash
gh api repos/{owner}/{repo}/actions/runs/<RUN_ID>/jobs \
  --jq '.jobs[] | {name, conclusion, steps: (.steps|length), runner_id, started_at, completed_at}'
```

### 2. 为什么这不是代码问题

- **同一文件刚才还绿**：`build-python.yml` 自仓库重构后一个字节没改，
  10-20 06:22 还 success，07:42 同样文件的 run 就红了；
- **翻转是齐刷刷的**：所有消耗 runner 的工作流在同一时刻一起红，
  与每次推送改了什么毫无关系；
- **不耗分钟的作业不受影响**：GitHub 托管的 Graph Update（依赖图）始终 success
  ——它跑在 GitHub 基础设施上，不记入账户分钟额度；
- **本地全步骤复现通过**（Python 3.11 与 3.12 双版本实跑）：

  | CI 步骤 | 本地 rc |
  |---|---|
  | `scripts/check_repo_guard.py` | 0 |
  | `scripts/audit_standards_eol.py --stale-days 180` | 0（90 库、需复核 0） |
  | `tools/syspkg.py probe / pyz / wheel / sdist / smoke` | 0（全过） |
  | `tools/audit_concepts.py --strict` | 0（不一致 0） |
  | `tools/check_concept_mesh.py --strict` | 0（悬空 0 / 孤岛 0） |

结论：**作业在 runner 编排/排队阶段就被中止，是账户级问题。** 私有仓库
（个人账户免费 2000 分钟/月）最常见原因是**分钟额度耗尽或支付失败/
消费限额为 0**——作业代理直接拒派 runner。仓库/组织策略禁用 runner、
GitHub 侧临时故障也可能，但概率次之。

### 3. 怎么处置

账户级，任选其一：绑定支付方式/提高消费限额（Settings → Billing）；
等待月度重置（按账期日）；仓库转公开（公开仓库 Linux 分钟免费不限量）；
注册自托管 runner（零计费分钟，checks 照常上报）。

代码侧能做的只有**省分钟**（本次已做）：三个失败工作流都加了
`concurrency: group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true`
——同一 ref 上被顶掉的旧跑立即取消，不再重复烧分钟；以及收窄
`pull_request` 触发路径、把重活留给 tag/dispatch。

### 4. 工具侧：`ci_triage.py` 已能自动识别

```bash
python3 tools/ci_triage.py            # 命中签名时直接打印额度墙诊断，不再去拉日志
```

脚本判定逻辑（`preflight_failure()`）：steps 为空 + 无 runner + 60 秒内结束
→ 打印「排队阶段即被中止」的完整证据链与处置清单。**这类失败不要改代码，
也不要反复重试**——重试只会继续烧（本就不存在的）额度。早期版本遇到
BlobNotFound 会抛未捕获的 `HTTPError` 崩溃，已修为优雅报告。

---

## 四、推不上去：`git push` 卡在 TLS 层时怎么办

症状（受限网络 / 容器 / 部分 CI 环境）：

```text
fatal: unable to access 'https://github.com/...': GnuTLS recv error (-110):
       The TLS connection was non-properly terminated.
fatal: ... Failed to connect to github.com port 443 after 132514 ms: Couldn't connect to server
```

重试通常没用（实测连试四次全败）。但**同一时刻 HTTPS 的 REST API 往往是通的** ——
先用 `gh api /repos/<o>/<r>` 或 `curl -sI https://api.github.com` 验证这一点。

确认 API 通之后，改用 Git Data API 直接推（`tools/push_via_api.py`）：

```bash
python3 tools/push_via_api.py --dry-run              # 先看会推哪些文件
python3 tools/push_via_api.py --branch main
```

流程是：取远端分支当前 sha → `git diff --no-renames` 算变更 → 逐个 POST blob →
基于远端 base tree 建 tree → 建 commit（parent 是远端当前 sha）→ `PATCH` 分支 ref。

写这类脚本的三个坑，本仓库都踩过并已处理：

1. **中文路径**：git 默认把非 ASCII 路径转义成 `"docs/CI-\346\216\222\351\224\231.md"`，
   `open()` 直接 `FileNotFoundError`。所有 git 调用都要加 `-c core.quotePath=false`。
2. **删除与重命名**：删除的文件在 tree 条目里写 `sha: null`；
   重命名用 `--no-renames` 拆成一次 D + 一次 A，否则 status 是 `R100 old new` 不好处理。
3. **基线对象不在本地**：脚本自己建的 commit 只存在于远端，本地 `git diff <那个 sha>`
   会报 `fatal: bad object`。所以 **diff 基线**和 **commit parent** 必须分开解析 ——
   parent 固定用远端 ref 当前 sha，diff 基线在本地找不到时回退到本地的 `origin/*` 引用。

代价要说清楚：这样推上去的是 **HEAD 这一个提交的内容快照**，等价于把本地若干提交
squash 成一个，不会重放中间历史。够用，但别指望它保住每个 commit 的独立记录。

## 五、一份最小检查清单

CI 红了之后按顺序做，不要跳步：

1. `grep -n "##\[error\]" job.log` —— 定位**第一条**错误，忽略末尾的 warning。
2. 看错误行紧邻的 `Process completed with exit code N`，对照上面的退出码表。
3. 看这个 step 的**命令原文**（日志里 `##[group]Run ...` 之后会回显脚本），
   问自己：它在 CI 环境和在我本机有什么不同？（shell 选项、编码、PATH、权限、网络）
4. 特别留意 runner 给 shell 自动加的选项：`bash --noprofile --norc -e -o pipefail`，
   其中 **`-e`（出错即停）和 `pipefail`（管道任一环失败即整条失败）是 CI 特有的放大器**，
   本机交互式 shell 通常没开，所以"本机好好的"很常见。
5. **如果连日志都没有**（steps 空 + 无 runner + 秒败 + BlobNotFound）：
   先按第三节判定是不是分钟额度墙——是的话去 Billing 处理，别改代码；
   不是的话再怀疑 runner 策略与临时故障。
6. 修完之后必须加一条**能复现该失败的回归测试**，否则它一定会回来。
