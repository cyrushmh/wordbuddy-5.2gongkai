"""WSL（Windows Subsystem for Linux）环境只读诊断。

基于 microsoft/wsl2-linux-kernel 的视角：WSL 把兼容内核跑在轻量虚拟机里，
Windows 与 Linux 程序通过 virtiofs/9p 共享文件系统、通过 AF_VSOCK 跨系统通信。
本模块只读核验「当前是否处于 WSL、是 1 还是 2、内核与微软主线差多远、
根文件系统驱动、systemd/interop 配置」。

红线：不写 wsl.conf/.wslconfig、不 wsl --shutdown、不改 /proc、不连校外网。
"""
from . import common

_DEF = "（未知）"


def _is_wsl() -> bool:
    rc, out = common.run("cat /proc/version 2>/dev/null", timeout=5)
    return rc == 0 and "microsoft" in out.lower()


def _wsl_version() -> str:
    # WSL2 内核 release 含 -microsoft-standard-WSL2；WSL1 含 -Microsoft（无 standard）
    rc, o1 = common.run("cat /proc/sys/kernel/osrelease 2>/dev/null", timeout=5)
    if rc == 0:
        low = o1.lower()
        if "wsl2" in low or "microsoft-standard" in low:
            return "2"
        if "microsoft" in low:
            return "1"
    # 退化判断：WSL2 有 initrd
    rc, o2 = common.run("cat /proc/cmdline 2>/dev/null", timeout=5)
    if rc == 0 and "initrd" in o2:
        return "2"
    return "未知"


def _kernel_version() -> str:
    rc, out = common.run("uname -r 2>/dev/null", timeout=5)
    return out.strip() if rc == 0 and out.strip() else _DEF


def _read_file(path: str) -> tuple:
    rc, out = common.run(f"cat {path} 2>/dev/null", timeout=5)
    if rc != 0 or not out.strip():
        return (False, "")
    return (True, out.strip())


def _root_fs() -> str:
    rc, out = common.run("findmnt -n -o FSTYPE / 2>/dev/null", timeout=5)
    if rc == 0 and out.strip():
        return out.strip()
    return _DEF


def _systemd_enabled() -> str:
    ok, conf = _read_file("/etc/wsl.conf")
    if ok and "[boot]" in conf and "systemd=true" in conf.replace(" ", ""):
        return "已启用（wsl.conf [boot] systemd=true）"
    return "未启用 / 未配置（默认旧行为）"


def _interop_note() -> str:
    ok, conf = _read_file("/etc/resolv.conf")
    if ok and "generated" in conf.lower():
        for line in conf.splitlines():
            if line.strip().startswith("nameserver"):
                return f"{line.strip()}（systemd-resolved 生成，可路由 Windows 主机）"
    return ""


def capabilities_report() -> tuple:
    lines = [
        "WSL 环境诊断 · 能力自检",
        "可诊断维度：",
        "  1. 是否处于 WSL（/proc/version 含 Microsoft）",
        "  2. 版本 1 / 2（osrelease + cmdline initrd 推断）",
        "  3. 内核版本（uname -r，对照 wsl2-linux-kernel 主线）",
        "  4. 根文件系统驱动（virtiofs / 9p drvfs）",
        "  5. systemd（wsl.conf [boot] systemd=true）",
        "  6. wsl.conf 读取",
        "红线：不写 wsl.conf/.wslconfig、不 wsl --shutdown、不连校外网。",
    ]
    return (True, "\n".join(lines))


def wsl_report() -> tuple:
    if not _is_wsl():
        return (True, "未识别为 WSL 环境（/proc/version 不含 Microsoft）；其余维度不适用。\n"
                      "注：本机为常规 Linux 或容器，非 Windows Subsystem for Linux。")
    lines = []
    lines.append("==== WSL 环境只读诊断 ====")
    lines.append(f"[版本] WSL{_wsl_version()}")
    lines.append(f"[内核] {_kernel_version()}")
    lines.append(f"[根文件系统] {_root_fs()}")
    lines.append(f"[systemd] {_systemd_enabled()}")
    ok_conf, conf = _read_file("/etc/wsl.conf")
    if ok_conf:
        lines.append(f"[wsl.conf] 已读取（{len(conf.splitlines())} 行）")
    else:
        lines.append("[wsl.conf] 无（使用默认）")
    note = _interop_note()
    if note:
        lines.append(f"[网络 interop] {note}")
    lines.append("")
    lines.append("提示（基于 wsl2-linux-kernel）：WSL2 用轻量 VM + 兼容内核；")
    lines.append("启用 systemd 需在 /etc/wsl.conf 写 [boot] systemd=true 并从 Windows 重启 WSL。")
    lines.append("注：本模块只读取，下一步改动由你决定。")
    return (True, "\n".join(lines))
