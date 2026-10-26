"""macOS 原生接口：用 libc sysctlbyname（真实系统库调用）+ 系统命令。

- sysctlbyname 通过 ctypes 调 libSystem（/usr/lib/libc.dylib），读取内核状态，
  例如硬件型号、内存、CPU 核心数——这是底层「系统接口」。
- 发行版/版本用 sw_vers（Apple 官方命令）。
- 文档跟踪层（data/macos_docs.json）：launchd / sysctl / defaults / softwareupdate /
  diskutil / pmset / tmutil / spctl / networksetup，每个接口按**自身的协议与接口**核对。
非 macOS 平台导入不崩溃，函数一律返回 None / (False, 说明) 供上层降级为指引。"""

from __future__ import annotations

import json
import shutil
import sys

from . import common


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "macos_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 macOS 接口的文档参考（含 protocols 与 interfaces）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 macOS 接口文档参考。"""
    return REFS


def _libc():
    if sys.platform != "darwin":
        return None
    try:
        return __import__("ctypes").CDLL("/usr/lib/libc.dylib")
    except Exception:  # noqa: BLE001
        return None


def _is_darwin() -> bool:
    return sys.platform == "darwin"


def sysctl(name: str) -> str | None:
    """读 sysctlbyname 的字符串值（如 'hw.model' / 'kern.osproductversion'）。"""
    ctypes = __import__("ctypes")
    libc = _libc()
    if libc is None:
        return None
    try:
        buf = ctypes.create_string_buffer(256)
        size = ctypes.c_size_t(256)
        libc.sysctlbyname.argtypes = [
            ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
        libc.sysctlbyname.restype = ctypes.c_int
        rc = libc.sysctlbyname(name.encode(), buf, ctypes.byref(size), None, 0)
        if rc != 0:
            return None
        return buf.value.decode("utf-8", "ignore").rstrip("\x00")
    except Exception:  # noqa: BLE001
        return None


def sw_vers() -> dict:
    """读 macOS 版本（sw_vers 官方命令）。"""
    out = {}
    rc, txt = common.run("sw_vers")
    if rc == 0 and txt:
        import re
        for m in re.finditer(r"^ProductName:\s*(.+)$", txt, re.M):
            out["product"] = m.group(1).strip()
        for m in re.finditer(r"^ProductVersion:\s*(.+)$", txt, re.M):
            out["version"] = m.group(1).strip()
        for m in re.finditer(r"^BuildVersion:\s*(.+)$", txt, re.M):
            out["build"] = m.group(1).strip()
    return out


def disk_usage(path: str = "/") -> dict | None:
    return common.disk_usage(path)


def launchctl_bootout_domain(user: bool = True) -> tuple:
    """示例：用 launchctl 退出某个 domain（一般不必，仅演示系统接口）。"""
    domain = "gui/$(id -u)" if user else "system"
    rc, out = common.run(f"launchctl bootout {domain} 2>&1")
    return rc == 0, out


# --------------------------------------------------------------------------- #
# 文档跟踪层：macOS 各系统接口只读探测（返回 (ok, msg)）。                       #
# 全部只读：仅列出可用接口/版本/配置，不禁用、不删除、不写任何系统项。           #
# 非 macOS 环境工具不存在，优雅返回 (False, 说明)，由上层降级为文档指引。        #
# --------------------------------------------------------------------------- #

def version_report() -> tuple:
    """读 macOS 版本（sw_vers 官方命令，只读）。"""
    sv = sw_vers()
    if not sv:
        if not _is_darwin():
            return False, "非 macOS 环境，sw_vers 不可用（降级为文档指引）"
        return False, "sw_vers 未返回版本信息"
    parts = [sv.get("product", ""), sv.get("version", ""),
             f"(build {sv.get('build','')})"]
    return True, "  ".join(p for p in parts if p)


def launchd_report() -> tuple:
    """列出当前 launchd 用户域代理（launchctl list，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，launchctl 不可用（降级为文档指引）"
    if not shutil.which("launchctl"):
        return False, "未安装 launchctl（macOS 应自带），跳过"
    rc, out = common.run("launchctl list 2>/dev/null | head -20")
    if rc != 0 or not (out or "").strip():
        return False, "launchctl list 无输出（可能无用户级代理）"
    n = len([l for l in out.splitlines() if l.strip()])
    lines = [f"launchd 当前域作业（前 {n} 行）："]
    for l in out.splitlines()[:8]:
        lines.append("   · " + l.strip())
    lines.append("   · 审查启动项：launchctl list；禁用用 launchctl disable gui/$(id -u)/<label>")
    return True, "\n".join(lines)


def sysctl_report() -> tuple:
    """读 XNU 内核参数（sysctl，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，sysctl 不可用（降级为文档指引）"
    if not shutil.which("sysctl"):
        return False, "未安装 sysctl（macOS 应自带），跳过"
    rc, out = common.run("sysctl -n hw.ncpu hw.memsize kern.osrelease 2>/dev/null")
    if rc != 0 or not (out or "").strip():
        return False, "sysctl 读取失败"
    vals = (out or "").split()
    ncpu = vals[0] if vals else "?"
    mem = vals[1] if len(vals) > 1 else "?"
    rel = vals[2] if len(vals) > 2 else "?"
    mem_h = f"{int(mem)/1024/1024/1024:.2f} GiB" if mem.isdigit() else mem
    return True, f"内核版本={rel}  CPU 核数={ncpu}  内存={mem_h}（sysctl 只读）"


def diskutil_report() -> tuple:
    """列 APFS 容器/宗卷（diskutil apfs list，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，diskutil 不可用（降级为文档指引）"
    if not shutil.which("diskutil"):
        return False, "未安装 diskutil（macOS 应自带），跳过"
    rc, out = common.run("diskutil apfs list 2>/dev/null | head -30")
    if rc != 0 or not (out or "").strip():
        return False, "diskutil apfs list 无输出（可能无 APFS 容器）"
    lines = ["APFS 容器/宗卷（diskutil apfs list，只读）："]
    for l in out.splitlines()[:12]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 清理本地快照见 tmutil；一致性检查 diskutil verifyVolume <vol>")
    return True, "\n".join(lines)


def pmset_report() -> tuple:
    """读电源管理配置（pmset -g，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，pmset 不可用（降级为文档指引）"
    if not shutil.which("pmset"):
        return False, "未安装 pmset（macOS 应自带），跳过"
    rc, out = common.run("pmset -g 2>/dev/null | head -25")
    if rc != 0 or not (out or "").strip():
        return False, "pmset -g 无输出"
    lines = ["电源管理（pmset -g，只读）："]
    for l in out.splitlines()[:10]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def softwareupdate_report() -> tuple:
    """列可用软件更新（softwareupdate -l，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，softwareupdate 不可用（降级为文档指引）"
    if not shutil.which("softwareupdate"):
        return False, "未安装 softwareupdate（macOS 应自带），跳过"
    rc, out = common.run("softwareupdate -l 2>/dev/null | head -20")
    if rc != 0 or not (out or "").strip():
        return False, "当前无可用软件更新（softwareupdate -l 空）"
    lines = ["可用软件更新（softwareupdate -l，只读）："]
    for l in out.splitlines()[:8]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def spctl_report() -> tuple:
    """读 Gatekeeper 状态（spctl --status / --assess，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，spctl 不可用（降级为文档指引）"
    if not shutil.which("spctl"):
        return False, "未安装 spctl（macOS 应自带），跳过"
    rc, out = common.run("spctl --status 2>&1 | head -5")
    if rc != 0 and not (out or "").strip():
        return False, "spctl --status 读取失败"
    return True, "Gatekeeper 状态：" + ((out or "").strip().splitlines()[0] if (out or "").strip() else "(未知)") + "（只读评估）"


def networksetup_report() -> tuple:
    """列网络服务（networksetup -listallnetworkservices，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，networksetup 不可用（降级为文档指引）"
    if not shutil.which("networksetup"):
        return False, "未安装 networksetup（macOS 应自带），跳过"
    rc, out = common.run("networksetup -listallnetworkservices 2>/dev/null | head -15")
    if rc != 0 or not (out or "").strip():
        return False, "networksetup 无输出"
    lines = ["网络服务（networksetup -listallnetworkservices，只读）："]
    for l in out.splitlines()[1:9]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def defaults_report() -> tuple:
    """列偏好域（defaults domains，只读）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，defaults 不可用（降级为文档指引）"
    if not shutil.which("defaults"):
        return False, "未安装 defaults（macOS 应自带），跳过"
    rc, out = common.run("defaults domains 2>/dev/null | head -5")
    if rc != 0 or not (out or "").strip():
        return False, "defaults domains 无输出"
    return True, "偏好域（defaults domains，只读）：" + ((out or "").strip()[:120])


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("version_report", "macOS 版本（sw_vers 官方命令，只读）"),
    ("launchd_report", "launchd 启动项（launchctl list 只读，禁用用 disable）"),
    ("sysctl_report", "XNU 内核参数（sysctl 只读，写需 root）"),
    ("diskutil_report", "APFS 容器/宗卷（diskutil apfs list 只读）"),
    ("pmset_report", "电源管理（pmset -g 只读）"),
    ("softwareupdate_report", "可用软件更新（softwareupdate -l 只读）"),
    ("spctl_report", "Gatekeeper 状态（spctl --status 只读评估）"),
    ("networksetup_report", "网络服务（networksetup -listallnetworkservices 只读）"),
    ("defaults_report", "偏好域（defaults domains 只读）"),
)


def environment_report() -> list:
    """返回本机 macOS 系统接口可用性概览（✓ 可用 / ✗ 未装/非 macOS）。"""
    lines = ["macOS 系统接口可用性（文档跟踪层）："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def macos_doc_list() -> list:
    """返回 macOS 接口文档参考清单（供 CLI/GUI 展示）。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    协议:")
        for p in ref.get("protocols", []):
            lines.append(f"      - {p}")
        lines.append("    接口:")
        for i in ref.get("interfaces", []):
            lines.append(f"      - {i}")
        lines.append(f"    建议: {ref.get('summary', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 官方写接口（深度调优）：只往「安全方向」写，且只用各工具自己的官方写子命令。   #
#   · pmset        : pmset -a <key> <val>（机型/参数自动探测）
#   · sysctl       : sysctl -w kern.*（XNU sysctl(8) 官方写接口）
#   · networksetup : networksetup -setdnsservers <服务> empty（empty 为官方取值）
#   · tmutil       : tmutil thinlocalsnapshots <mount> <amount>（APFS 官方瘦身）
#   · defaults     : defaults write <domain> <key>（CFPreferences plist 后端）
#   · softwareupdate: softwareupdate --schedule on（SUS 官方排程接口）
#   · spctl        : spctl --master-enable（只开不关，绝不做 --master-disable）
#   · diskutil     : diskutil verifyVolume（只校验不修复）
# 关键约束：runner 以 fn() 无参派发，故机型/网络服务/宗卷一律自动探测。         #
# --------------------------------------------------------------------------- #

def _hw_model() -> str:
    """读机型标识（sysctl hw.model，只读；笔记本含 Book）。"""
    m = sysctl("hw.model")
    if m:
        return m
    rc, out = common.run("sysctl -n hw.model 2>/dev/null")
    return (out or "").strip() if rc == 0 else ""


def _primary_network_service() -> str:
    """自动探测主网络服务名（networksetup 写接口所需，只读）。

    优先 Wi-Fi / Ethernet，其次第一个未禁用（不以 * 开头）的服务。
    """
    rc, out = common.run("networksetup -listallnetworkservices 2>/dev/null")
    if rc != 0:
        return ""
    first = ""
    for raw in (out or "").splitlines():
        name = raw.strip()
        if not name or name.startswith("*") or name.lower().startswith("an asterisk"):
            continue
        low = name.lower()
        if "wi-fi" in low or "ethernet" in low:
            return name
        if not first:
            first = name
    return first


def pmset_hibernatemode(mode: int | None = None) -> tuple:
    """按机型设置休眠模式（pmset -a hibernatemode，官方写接口）。

    - 3：安全休眠（内存保持供电 + 落盘镜像），笔记本默认；
    - 0：不写休眠镜像，台式机可省掉与内存等大的 /private/var/vm/sleepimage。
    """
    if not _is_darwin():
        return False, "非 macOS 环境，pmset 写接口不可用（降级为文档指引）"
    if not shutil.which("pmset"):
        return False, "未安装 pmset（macOS 应自带），跳过"
    if mode is None:
        mode = 3 if "book" in _hw_model().lower() else 0
    rc, out = common.run(f"sudo pmset -a hibernatemode {mode}")
    if rc != 0:
        return False, out or "pmset -a 写入失败（需管理员权限）"
    tail = ("笔记本：安全休眠（内存供电 + 落盘镜像）" if mode == 3
            else "台式机：不写休眠镜像，省出与内存等大的空间")
    return True, f"pmset -a hibernatemode {mode} 已设置（{tail}）"


def pmset_standby_delay(seconds: int = 86400) -> tuple:
    """延长进入待机前的等待（pmset -a standbydelayhigh/low，官方写接口）。

    待机会把内存镜像落盘再断电；延后触发可减少频繁落盘写入、延长 SSD 寿命，
    代价是合盖待机期间稍微耗电。旧版 macOS 只有 standbydelay，自动回退。
    """
    if not _is_darwin():
        return False, "非 macOS 环境，pmset 写接口不可用（降级为文档指引）"
    if not shutil.which("pmset"):
        return False, "未安装 pmset（macOS 应自带），跳过"
    rc, out = common.run(
        f"sudo pmset -a standbydelayhigh {seconds} standbydelaylow {seconds} 2>/dev/null"
        f" || sudo pmset -a standbydelay {seconds}")
    if rc != 0:
        return False, out or "pmset -a 写入失败（需管理员权限）"
    return True, (f"pmset -a standbydelay(-high/-low) {seconds}s 已设置"
                  f"（约 {seconds // 3600} 小时后才进入待机落盘）")


def sysctl_maxfiles(maxfiles: int = 65536, per_proc: int = 32768) -> tuple:
    """调高文件描述符上限（sysctl -w kern.maxfiles / kern.maxfilesperproc）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，XNU sysctl 写接口不可用（降级为文档指引）"
    if not shutil.which("sysctl"):
        return False, "未安装 sysctl（macOS 应自带），跳过"
    rc, out = common.run(
        f"sudo sysctl -w kern.maxfiles={maxfiles} kern.maxfilesperproc={per_proc}")
    if rc != 0:
        return False, out or "sysctl -w 写入失败（需管理员权限）"
    return True, (f"kern.maxfiles={maxfiles}  kern.maxfilesperproc={per_proc}"
                  "（sysctl -w；持久化写 /etc/sysctl.conf）")


def networksetup_dns(servers: str = "empty") -> tuple:
    """把主网络服务的 DNS 交回 DHCP（networksetup -setdnsservers <服务> empty）。

    empty 是官方取值：清空手工 DNS、改由 DHCP/路由器下发。可自愈被软件改写
    或被劫持的 DNS，且不引入任何第三方解析器（安全方向）。
    """
    if not _is_darwin():
        return False, "非 macOS 环境，networksetup 写接口不可用（降级为文档指引）"
    if not shutil.which("networksetup"):
        return False, "未安装 networksetup（macOS 应自带），跳过"
    svc = _primary_network_service()
    if not svc:
        return False, "未探测到可用的网络服务（networksetup -listallnetworkservices 无输出）"
    rc, out = common.run(f"networksetup -setdnsservers {svc!r} {servers}")
    if rc != 0:
        return False, out or f"networksetup -setdnsservers 写入失败（服务: {svc}）"
    return True, f"{svc}: DNS 已交回 DHCP（-setdnsservers empty，官方接口）"


def tmutil_thin_snapshots(mount: str = "/", purge_amount: str = "1g") -> tuple:
    """按 APFS 官方接口瘦身本地快照（tmutil thinlocalsnapshots <mount> <amount>）。

    与直接删快照不同：thin 由系统按自身策略回收，不误删备份磁盘上的历史备份。
    """
    if not _is_darwin():
        return False, "非 macOS 环境，tmutil 写接口不可用（降级为文档指引）"
    if not shutil.which("tmutil"):
        return False, "未安装 tmutil（macOS 应自带），跳过"
    rc, out = common.run(f"sudo tmutil thinlocalsnapshots {mount} {purge_amount}")
    if rc != 0:
        return False, out or "tmutil thinlocalsnapshots 执行失败（无本地快照或需管理员权限）"
    return True, (f"{mount} 本地快照已瘦身，目标回收 {purge_amount}"
                  "（tmutil 官方接口，不碰备份磁盘历史）")


def defaults_dock_autohide(on: bool = True) -> tuple:
    """Dock 自动隐藏 + 去弹出延迟（defaults write com.apple.dock + killall Dock）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，defaults 写接口不可用（降级为文档指引）"
    if not shutil.which("defaults"):
        return False, "未安装 defaults（macOS 应自带），跳过"
    val = "true" if on else "false"
    rc, out = common.run(
        f"defaults write com.apple.dock autohide -bool {val}; "
        f"defaults write com.apple.dock autohide-delay -float 0; "
        f"killall Dock 2>/dev/null")
    if rc != 0:
        return False, out or "defaults write 写入失败"
    return True, f"Dock 自动隐藏={on}（defaults write CFPreferences plist + killall Dock 生效）"


def softwareupdate_schedule(on: bool = True) -> tuple:
    """软件更新自动排程（softwareupdate --schedule on|off，官方写接口）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，softwareupdate 写接口不可用（降级为文档指引）"
    if not shutil.which("softwareupdate"):
        return False, "未安装 softwareupdate（macOS 应自带），跳过"
    state = "on" if on else "off"
    rc, out = common.run(f"sudo softwareupdate --schedule {state}")
    if rc != 0:
        return False, out or "softwareupdate --schedule 写入失败（需管理员权限）"
    return True, f"softwareupdate --schedule {state}（按 SUS catalog 自动检查更新，官方接口）"


def spctl_master_enable() -> tuple:
    """启用 Gatekeeper（spctl --master-enable，官方写接口；只开不关）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，spctl 写接口不可用（降级为文档指引）"
    if not shutil.which("spctl"):
        return False, "未安装 spctl（macOS 应自带），跳过"
    rc, out = common.run("sudo spctl --master-enable")
    if rc != 0:
        return False, out or "spctl --master-enable 失败（需管理员权限）"
    return True, ("Gatekeeper 已启用（spctl --master-enable，官方接口；"
                  "本工具绝不做 --master-disable）")


def diskutil_verify(volume: str = "/") -> tuple:
    """宗卷一致性校验（diskutil verifyVolume，官方校验接口；只校验不修复）。"""
    if not _is_darwin():
        return False, "非 macOS 环境，diskutil 校验接口不可用（降级为文档指引）"
    if not shutil.which("diskutil"):
        return False, "未安装 diskutil（macOS 应自带），跳过"
    rc, out = common.run(f"diskutil verifyVolume {volume}")
    if rc != 0:
        return False, out or f"diskutil verifyVolume {volume} 未通过（只校验不修复，请按输出排查）"
    return True, f"{volume} 一致性校验通过（diskutil verifyVolume，只校验不改动）"


# 官方写接口清单（仅用于展示，**不在展示时调用**——调用即写系统）。
# 每项：(函数名, 官方写子命令说明)
TUNES = (
    ("pmset_hibernatemode", "pmset -a hibernatemode <3|0>（按机型自动选：笔记本安全休眠 / 台式机省镜像）"),
    ("pmset_standby_delay", "pmset -a standbydelayhigh/low <秒>（延后待机落盘，旧版回退 standbydelay）"),
    ("sysctl_maxfiles", "sysctl -w kern.maxfiles / kern.maxfilesperproc（提文件描述符上限）"),
    ("networksetup_dns", "networksetup -setdnsservers <服务> empty（DNS 交回 DHCP，官方取值）"),
    ("tmutil_thin_snapshots", "tmutil thinlocalsnapshots / 1g（APFS 官方瘦身，不碰备份历史）"),
    ("defaults_dock_autohide", "defaults write com.apple.dock autohide + killall Dock（CFPreferences 后端）"),
    ("softwareupdate_schedule", "softwareupdate --schedule on（SUS 官方更新排程接口）"),
    ("spctl_master_enable", "spctl --master-enable（启用 Gatekeeper，只开不关）"),
    ("diskutil_verify", "diskutil verifyVolume /（APFS 一致性校验，只校验不修复）"),
)


def macos_tune_list() -> list:
    """返回 macOS 官方写接口（深度调优）清单，供 CLI/GUI 展示。只读展示，不执行。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
