# Windows 自动化：把优化项固化成自包含 .bat

本目录把一个 Windows 平台的优化/清理清单**展开**成一个自包含的批处理脚本，用 Windows 自带
的 `cmd` / `powershell` / `schtasks` 即可运行——**零安装、不依赖 Python**。

## 怎么生成

```bash
# 在装了 system-optimizer 的环境里（任意平台都能生成，产物在 Windows 上运行）
export PYTHONPATH=$PWD/src/python
cd system-optimizer
python -m sysweeper genbat --version 11 --risk low  -o sysweeper_optimize_win11.bat
python -m sysweeper genbat --version 10 --risk medium -o sysweeper_optimize_win10.bat
```

- `--version`：目标 Windows 版本（10 / 11），决定任务集合（如 Win10 会多一条「终止支持提醒」）
- `--risk`：纳入的风险上限（low / medium / high），中/高风险在 .bat 内需逐一确认
- 编码默认 **UTF-8(BOM) + CRLF**（现代 Windows 10/11 中文显示正常）；最旧系统中文异常时用 `--encoding gbk`

> 本目录的 `example_sysweeper_optimize_win11.bat` 是一个已生成的样例（风险上限 medium）。

## 生成的 .bat 怎么用（在 Windows 上，建议右键「以管理员身份运行」）

```
sysweeper_optimize_win11.bat           分析模式：仅 echo 将要执行的命令，不修改系统
sysweeper_optimize_win11.bat apply     执行：低风险直接跑；中/高风险用 choice 逐一确认
sysweeper_optimize_win11.bat schedule  用 schtasks 把本 .bat 注册成「每周一 09:00 最高权限 apply」
```

## 设计要点（与 system-optimizer 一致：默认只分析、不乱删、不强求安装）

- **分析优先**：无参数只打印命令，绝不修改系统；加 `apply` 才执行。
- **风险分级确认**：低风险（临时文件/回收站/浏览器缓存…）直接跑；中/高风险（Prefetch、DISM、
  诊断数据）逐一弹 `choice Y/N` 确认，不强制。
- **原生动作映射**：`windows.empty_recycle_bin` 这类 native 动作映射成等价 PowerShell
  （`Clear-RecycleBin -Force`）。
- **只固化 Windows 专属任务**：跨平台任务（语言缓存、硬件 S.M.A.R.T.、网络/ITU 开关）不写进
  本 .bat——它们由 Python CLI 自身处理，且其 native 调用不可直接放进批处理。
- **计划任务**：`schedule` 模式用 `schtasks /create` 自我注册，可一键定时自动维护；移除用
  `schtasks /delete /tn "Sysweeper.Optimize"`。

## 与 Python CLI 的分工

| 场景 | 用什么 |
|---|---|
| 一次性手动维护 / 想看报告 | `python -m sysweeper scan/clean`（跨平台，含 `--report`） |
| 想做成「一键/定时」自动化 | 本目录生成的 `.bat`（Windows 专属，零依赖） |
| 图形点选 | `python -m sysweeper gui`（Python 自带 tkinter） |
