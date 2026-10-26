"""WSL 环境诊断任务（platform="any"，v0.6.15「导入分析学习应用 wsl2-linux-kernel」）。

立项：把 microsoft/wsl2-linux-kernel 的视角吸收进本工具——WSL 把兼容内核跑在
轻量 VM 里，Windows 与 Linux 程序通过 virtiofs/9p + AF_VSOCK 互通。本任务只读诊断
「本机是否 WSL、1 还是 2、内核与微软主线差多远、systemd/interop 配置」。

参照（权威文档，仅用于把「该看什么」钉死）：
- github.com/microsoft/wsl2-linux-kernel —— WSL2 内核（mainline + MS 补丁；config-wsl /
  init / virtio / 9p；最新已到 6.18；WSL1 用 NT 兼容层而非独立内核）
- WSL 文档 —— wsl.conf [boot] systemd=true、.wslconfig（Windows 侧 %USERPROFILE%）
"""
from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

WSL_KERNEL = ("[微软] microsoft/wsl2-linux-kernel（WSL2 兼容内核：mainline + MS 补丁；"
              "config-wsl / init / virtio / 9p；WSL1 用 NT 兼容层而非独立内核）")


TASKS = [
    Task(
        id="wsl_report",
        platform="any",
        title="WSL 环境只读诊断（Microsoft wsl2-linux-kernel 坐标系）",
        category="maintenance",
        risk="low",
        desc="只读核验本机是否处于 WSL、版本 1/2、内核版本、根文件系统驱动、systemd 与 "
             "interop 配置——判断这台 WSL 与微软主线内核差多远、哪些能力可用。",
        actions=[
            N("wsl.capabilities_report", "能力自检：各维度是否可诊断 + 红线声明"),
            N("wsl.wsl_report", "输出 WSL 整体只读诊断（每项附结论与修复提示）"),
            M("需启用 systemd 时，在 /etc/wsl.conf 写 [boot] systemd=true，"
              "再从 Windows 侧 `wsl --shutdown` 重启（写操作，由你决定做不做）",
              "启用 systemd（写操作，opt-in）"),
        ],
        standards=[WSL_KERNEL],
        notes=[
            "是否 WSL：看 /proc/version 是否含 Microsoft；WSL2 内核 release 含 "
            "-microsoft-standard-WSL2，WSL1 含 -Microsoft 但无 standard。",
            "根文件系统：WSL2 新版默认 virtiofs、旧版 9p(drvfs)，用 findmnt 看 / 的 FSTYPE。",
            "systemd：wsl.conf [boot] systemd=true 才启用；否则是旧 init 行为。",
            "interop：/etc/resolv.conf 由 systemd-resolved 生成，nameserver 即 Windows 主机 IP，"
            "是 Linux↔Windows 网络互通的关键。",
            "内核版本对照 wsl2-linux-kernel 标签（最新已到 6.18）；落后多说明没更新 WSL。",
        ],
        caveats=[
            "只读任务：不写 wsl.conf/.wslconfig、不 wsl --shutdown、不连校外网。",
            ".wslconfig 位于 Windows 侧 %USERPROFILE%，本模块无法读取，属已知边界。",
        ],
    ),
]
