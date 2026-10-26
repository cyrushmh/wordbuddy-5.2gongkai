# tools · 统一打包器与引导脚本

这里放**全仓库通用**的几件东西，共同点是：**只用多数系统默认就有的语言**。

| 文件 | 语言 | 为什么用它 |
|---|---|---|
| `syspkg.py` | Python 3.8+ | 多数 Linux / macOS / BSD 发行版默认自带；只用标准库（zipapp / zipfile / tarfile），不需要 setuptools、wheel、pip、build |
| `bootstrap.sh` | POSIX sh | 所有 Unix / macOS / BSD 都有，Windows 也有 Git Bash |
| `bootstrap.ps1` | PowerShell 5.1+ | Windows 各版本自带 |
| `push_via_api.py` | Python 3.8+ | `git push` 卡在 TLS 层时的备用通道：走 GitHub Git Data API 推分支，只传变更 blob |
| `ci_triage.py` | Python 3.8+ | Actions 红了之后一条命令定位「哪个 job 的哪一步、为什么」，错误先行、警告靠后 |
| `disposable-env.sh` | bash 4+ | 一次性隔离环境：变量注入 + 私有 HOME/TMPDIR + 退出自动还原，手动版 chroot，零 mount 依赖 |

## syspkg.py —— 一个命令打全部

```bash
python3 tools/syspkg.py probe      # 探测本机有哪些语言工具链 / 能产出什么
python3 tools/syspkg.py targets    # 列出支持的（系统 × 硬件）矩阵
python3 tools/syspkg.py pyz        # 单文件 .pyz（zipapp）★ 语言底层首选产物
python3 tools/syspkg.py wheel      # 纯标准库手写 wheel（pip 可装，PEP 427）
python3 tools/syspkg.py sdist      # 源码分发 tar.gz
python3 tools/syspkg.py smoke      # 对 dist/ 里的 .pyz 冒烟（能跑 + 知识库完整）
python3 tools/syspkg.py go         # Go 交叉编译（7 个 系统 × 架构）
python3 tools/syspkg.py rust       # cargo 构建 Windows 子项目
python3 tools/syspkg.py android    # Gradle 构建 Android 14 APK（按 ABI 拆分）
python3 tools/syspkg.py all        # 能打的都打，缺工具链自动跳过
```

通用参数：`--out DIR`（默认仓库根 `dist/`）、`--version X.Y.Z`、`--only a,b`（仅部分目标）、`--json`。

### 语言分层

| 层 | 语言 | 产物 | 缺失时 |
|---|---|---|---|
| **L0 语言底层** | Python 3.8+ | `.pyz` / wheel / sdist（noarch，跨系统跨硬件） | 不可能缺——脚本自己就是 Python |
| **L0 壳** | POSIX sh / PowerShell | `bootstrap.sh` / `bootstrap.ps1` | 见下方安装命令 |
| **L1 可选加速** | Go 1.21 / Rust | 静态二进制（7 目标）、Windows PE 工具 | 自动跳过 |
| **L2 端上** | Kotlin / ART（安卓自带） | Android 14 APK（arm64-v8a / armeabi-v7a / x86_64 + universal） | 自动跳过，改用 adb 只读审计 |

`probe` 的输出里，"跳过"项只说明缺哪个工具链，**不计为失败**——这是刻意的：
保证任何一台只有 python3 的机器都能拿到可用产物。

## 单文件 .pyz 怎么用

```bash
python3 tools/syspkg.py pyz --out dist
python3 dist/sysweeper-0000.0000.0000.0003.20261023.pyz detect          # 显式交给 python
./dist/sysweeper-0000.0000.0000.0003.20261023.pyz detect                # 已带 shebang + 可执行位
```

`.pyz` 是 zipapp 归档：包内 `sysweeper/data/*.json` 知识库在 zip 中同样读得到
（Python 3.11+ 由 zipimport 原生支持；3.9 / 3.10 由 `sysweeper/_zipres.py` 补 shim），
不会出现"能跑但知识库为空"。

## bootstrap —— 只负责找 python3

```bash
sh tools/bootstrap.sh detect          # 自动找 python3 → 找 dist/*.pyz → 跑
sh tools/bootstrap.sh android         # Android 只读审计
```

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\bootstrap.ps1 detect
```

找不到 Python 时只打印各系统的安装命令，**绝不自动下载安装**：

| 系统 | 安装命令 |
|---|---|
| Debian / Ubuntu | `sudo apt-get install -y python3` |
| RHEL / Fedora | `sudo dnf install -y python3` |
| Arch | `sudo pacman -S python` |
| Alpine | `apk add python3` |
| openSUSE | `sudo zypper install python3` |
| macOS | `xcode-select --install` 或 `brew install python3` |
| FreeBSD | `pkg install python3` |
| OpenBSD | `pkg_add python3` |
| NetBSD | `pkgin install python3` |
| Windows | `winget install Python.Python.3.12` |

## 跟 GitHub 打交道：推不上去 / CI 红了

```bash
export GH_TOKEN=<PAT>                      # 或从 origin 的 URL 里自动提取

python3 tools/ci_triage.py                 # 最近一次 FAIL 的运行：直接给出失败 step 与错误上下文
python3 tools/ci_triage.py --run 37682971131 --context 12
python3 tools/push_via_api.py --dry-run    # 看看要推哪些文件
python3 tools/push_via_api.py --branch main
```

- `ci_triage.py` 的使用要点：**别从日志末尾读**。末尾常常是
  `##[warning]Node.js 20 is deprecated ...` 这类噪音，脚本会把 `##[error]` 单独提到前面。
- `ci_triage.py` 还能识别**额度墙**：job 秒败、steps 空、无 runner、日志 404
  BlobNotFound —— 那是私有仓库 Actions 分钟额度耗尽/支付失败，作业没分配到
  runner，与代码无关；脚本会直接打印诊断与处置清单（去 Billing，别改代码）。
- `push_via_api.py` 只在 `git push` 不可用（`GnuTLS recv error (-110)`、443 超时）时用；
  它推的是 HEAD 这一个提交的内容（等价 squash），不重放历史。
- 两者都用标准库，且**凭据只在内存里**：从 `GH_TOKEN` 或 origin URL 取，不落盘、不进版本库。

详情与踩过的坑（中文路径被 git 转义、日志下载 302 到 Azure blob 不能带 token）
见 [`docs/CI-排错.md`](../docs/CI-排错.md)。

## disposable-env.sh —— 一次性隔离环境（手动版 chroot）

跑一个**可能到处拉屎**的命令（装工具、试配置、跑第三方脚本），又不想弄脏系统？
把它关进一次性环境：**进去随便折腾，退出全部还原**。

真正的 chroot 要重配动态链接器、挂 `/proc`、`/dev`，多数还要 root。
这里换一条路达到同等隔离效果——**不 chroot、不 mount、不 root、不 Docker**：

| 手段 | 做法 | 退出时 |
|---|---|---|
| 私有 HOME/TMPDIR/XDG_* | 全部指向 `mktemp` 出的私有区 | 整体删除，真实 HOME 零污染 |
| `--guard FILE` | 进入前整文件备份 | `cp -a` 原样还原（内容、权限、属主、mtime） |
| `--ro PATH` | 进入前算 sha256 清单 | 复算比对，**改动即报警**（只报不改） |

### 用法

```bash
tools/disposable-env.sh CMD [ARGS...]                  # 跑命令，退出即还原
tools/disposable-env.sh                                # 不带命令：进交互 bash（需终端）
tools/disposable-env.sh -s FOO=bar -c env.conf CMD     # 注入变量（-c 先行，-s 覆盖）
tools/disposable-env.sh -g ~/.gitconfig git commit ... # 真实配置：进入备份、退出还原
tools/disposable-env.sh -r /etc/hosts cat /etc/hosts   # 只读校验区：改动即报警
tools/disposable-env.sh --no-restore CMD               # 调试：退出不还原，保留现场
```

| 选项 | 说明 |
|---|---|
| `-s, --set KEY=VALUE` | 注入环境变量，可重复；值整体传参，不做二次展开（`$(...)` 安全） |
| `-c, --config FILE` | 配置文件：每行 `KEY=VALUE`，`#` 注释、空行跳过；与 `-s` 可混用，`-s` 覆盖 `-c` |
| `-g, --guard FILE` | 接管真实配置文件，退出还原；同一文件重复指定只接管一次 |
| `-r, --ro PATH` | 只读校验区（文件或目录），退出复算 sha256，报警并给 diff 明细 |
| `-n, --no-restore` | 调试开关：不还原、不删临时区，报告里给出保留路径 |
| `-h, --help` | 用法 |

### 行为约定

- **退出码透传**：所跑命令返回什么，外层就收到什么；被 Ctrl-C / `kill` 时为 130 / 143。
- **退出报告**：还原了哪些变量、guard 还原结果、ro 校验结论（含 diff 明细）、退出码。
- **信号安全**：`trap` 覆盖 EXIT/INT/TERM——长命令运行中被中断，还原照样执行、临时区照样删除。
- **参数即错即退**：非法变量名、guard 目标不存在、配置文件缺失等一律退出码 2，且**临时区不会泄漏**。
- **私有区权限**：`mktemp` + `0700`；退出时 `rm -rf`，报告确认已删除。

### 实测结论（本机留证）

| 场景 | 结果 |
|---|---|
| `-s` / `-c` 注入与覆盖 | 生效；报告去重 |
| 私有 HOME/TMPDIR/XDG_* | 环境内写入全部落私有区；真实 HOME 无 canary；外部变量原样 |
| `--guard` 涂改/删除目标 | 退出后内容与权限（含 600）完整还原 |
| `--ro` 无变更 / 篡改+删+增 | 分别报「无变更」/「已变更！」+ diff 明细 |
| 退出码 0/1/42/127、命令不存在 | 逐一透传 |
| INT / TERM 进程组广播（等价 Ctrl-C） | 130 / 143 透传，guard 还原，零残留 |
| 交互模式（伪造 tty）`exit 7` | 7 透传，guard 还原 |
| 参数错误四连发 | 全部退出 2，残留临时区 0 个 |
| `bash -n` + `shellcheck` | 零告警 |

## 安全底线

只读 + 只写 `dist/`（push_via_api.py 例外：它会写远端分支，但只在显式调用时）。
不改任何系统设置、不下载安装任何解释器、不碰用户数据。

`disposable-env.sh` 的两个「写」都指向**用户显式指定的目标**，且都有退出还原兜底：
`--guard` 写的是「把用户自己指定的配置文件恢复原状」，`--ro` 全程只读、只报警不改写；
私有区是 `mktemp` 出的 `0700` 目录，退出即删。不指定 `-g/-r` 时，它对系统的全部影响
就是「改自己进程的环境变量」。
