"""把 Windows 平台的适用任务「固化」成一个自包含的 .bat 脚本。

设计目标（与整个 system-optimizer 一致：默认只分析、不乱删、不强求安装）：

- 纯标准库生成，零第三方依赖；输出物是 Windows 自带 cmd/powershell/schtasks 能跑的 .bat
- 生成时把每个任务**展开**成静态批处理代码（不是运行时再去读 Python）
- 三种调用方式：
    optimize.bat            分析模式：仅 echo 将要执行的命令，不修改系统
    optimize.bat apply      执行：低风险直接跑；中/高风险用 choice 逐一确认
    optimize.bat schedule   用 schtasks 把本 .bat 注册成「每周一 09:00 以最高权限 apply」
- native 动作（如清空回收站）映射成等价的 PowerShell 一行命令
- 仅 Windows 端有意义；本模块在 Linux 上只负责「生成文本」，由用户在 Windows 上运行

编码（——可使用 UTF-8 以上——）：
- 默认 utf-8-sig（UTF-8 + BOM）；现代 Windows 10/11 上 cmd 可直接正确显示中文。
- 若目标系统中文显示异常，可改 gbk（sysweeper genbat --encoding gbk）。

用法：
    from sysweeper.windows_bat import generate
    text = generate(version="11", risk_limit="low")
    open("sysweeper_optimize.bat", "w", encoding="utf-8-sig").write(text)
"""

from __future__ import annotations

from . import registry
from .models import RISK_ORDER

# native 动作 -> 等价的 Windows 命令（PowerShell 一行）。不在表内的 native 退化为手动提示。
NATIVE_BAT = {
    "windows.empty_recycle_bin": 'powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"',
}


def _runnable(cmd: str) -> str:
    """把动作命令转成可在 .bat 里直接执行的单行命令（native 做映射）。"""
    if cmd in NATIVE_BAT:
        return NATIVE_BAT[cmd]
    return cmd


def _emit_task(t) -> list:
    """为一个 Task 生成批处理代码行（已展开，无全局状态）。"""
    out = []
    cat = t.category
    out.append(f'echo [任务] {t.title}  [{cat}/{t.risk}]')
    if t.desc:
        out.append(f'echo   {t.desc}')
    for c in t.caveats:
        out.append(f'echo   [风险] {c}')
    for n in t.notes:
        out.append(f'echo   [注意] {n}')

    if not t.actions:
        # 纯提醒类任务（如 Win10 EOL），无需执行任何动作
        out.append("")
        return out

    for a in t.actions:
        cmd = _runnable(a.command)
        if a.kind == "manual":
            out.append(f'echo   (手动) {a.description or a.command}')
            continue
        # 分析模式：打印将要执行的命令
        out.append(f'echo   (分析) {cmd}')
        if t.risk == "low":
            # 低风险：apply 时直接执行
            out.append(f'if /i "%MODE%"=="apply" {cmd}')
        else:
            # 中/高风险：apply 时需用户逐一确认
            out.append(f'if /i not "%MODE%"=="apply" goto end_{t.id}_{id(a)}')
            out.append(f'choice /C YN /M "执行「{t.title}」? (Y=执行 N=跳过)"')
            out.append(f'if errorlevel 2 goto end_{t.id}_{id(a)}')
            out.append(cmd)
            out.append(f':end_{t.id}_{id(a)}')
    out.append("")
    return out


def generate(version: str = "11", risk_limit: str = "low",
             task_name: str = "Sysweeper.Optimize") -> str:
    """生成完整的 .bat 文本。version 为目标 Windows 版本，risk_limit 为纳入的风险上限。"""
    tasks = registry.applicable("windows", version, max_risk=risk_limit,
                                 include_opt_in=False)
    # 只固化 Windows 专属任务：跨平台任务（语言缓存/硬件 S.M.A.R.T./网络开关）由
    # Python CLI 自身处理，且其 native 动作（如 hardware.smart_health）不可直接写进 .bat
    tasks = [t for t in tasks if t.platform == "windows"]

    L = []
    L.append("@echo off")
    L.append("setlocal enableextensions")
    L.append('set "MODE=%~1"')
    L.append('if "%MODE%"=="" set "MODE=analyze"')
    L.append("")
    L.append("echo ============================================================")
    L.append(f"echo  Sysweeper Windows 优化脚本  (目标 Windows {version}, 风险上限 {risk_limit})")
    L.append("echo   无参数        分析模式：仅显示命令，不修改系统")
    L.append("echo   apply         执行：低风险直接跑，中/高风险逐一确认")
    L.append("echo   schedule      注册为每周一 09:00 的计划任务（最高权限）")
    L.append("echo ============================================================")
    L.append("")

    # schedule 模式：注册计划任务后退出，避免接着做清理
    L.append('if /i "%MODE%"=="schedule" (')
    L.append(f'  echo 正在注册计划任务 {task_name} ...')
    L.append(f'  schtasks /create /tn "{task_name}" /tr "\\"%~f0\\" apply" '
             f'/sc weekly /d MON /st 09:00 /rl HIGHEST /f')
    L.append(f'  echo 完成。可用「任务计划程序」或 schtasks /delete /tn "{task_name}" 移除。')
    L.append("  goto :eof")
    L.append(")")
    L.append("")

    L.append(f"echo 适用任务共 {len(tasks)} 项（分析模式）：")
    L.append("")
    for t in tasks:
        L.extend(_emit_task(t))

    L.append("echo.")
    L.append('echo 完成。若需真正执行，请以「管理员」运行：%~nx0 apply')
    L.append("echo （注册定时自动执行：%~nx0 schedule）")
    L.append("endlocal")
    return "\n".join(L) + "\n"


def write_bat(path: str, version: str = "11", risk_limit: str = "low",
              task_name: str = "Sysweeper.Optimize", encoding: str = "utf-8-sig") -> int:
    """生成并写入 .bat 文件，返回写入字节数。默认 utf-8-sig（UTF-8+BOM），
    兼容现代 Windows 中文显示；需最旧系统兼容时可传 encoding="gbk"。"""
    text = generate(version=version, risk_limit=risk_limit, task_name=task_name)
    with open(path, "w", encoding=encoding, newline="\r\n") as f:
        f.write(text)
    return len(text.encode(encoding))
