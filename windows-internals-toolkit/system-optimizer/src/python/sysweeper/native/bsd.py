"""BSD 原生接口：覆盖 FreeBSD / OpenBSD / NetBSD / DragonFly。

设计「不麻烦、靠系统本身」：
- 发行版识别：优先 /etc/os-release（FreeBSD/NetBSD 提供），再用 libc 的
  sysctlbyname（kern.ostype / kern.osrelease / kern.version）读内核态，最后降级 uname。
- 包管理：pkg（FreeBSD/DragonFly）/ pkg_add（OpenBSD）/ pkgin（NetBSD），用 which 探测。
- 清理：直接调用对应包管理器的原生清理命令（pkg clean -y / pkg autoremove -y 等）。

非 BSD 平台 import 不崩溃；任何 BSD 专属调用检测不到就返回 None/False，由上层降级。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys

from . import common


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "bsd_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 BSD 接口的文档参考（含 protocols 与 interfaces）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 BSD 接口文档参考。"""
    return REFS


def _is_bsd() -> bool:
    return sys.platform in ("freebsd", "openbsd", "netbsd", "dragonfly")


def _libc():
    if not _is_bsd():
        return None
    try:
        import ctypes.util
        path = ctypes.util.find_library("c")  # type: ignore
        return __import__("ctypes").CDLL(path) if path else None
    except Exception:  # noqa: BLE001
        return None


def sysctl(name: str) -> str | None:
    """读 libc sysctlbyname 字符串值（BSD 原生内核接口；非 BSD 返回 None）。"""
    ctypes = __import__("ctypes")
    libc = _libc()
    if libc is None:
        return None
    try:
        buf = ctypes.create_string_buffer(256)
        size = ctypes.c_size_t(256)
        libc.sysctlbyname.argtypes = [
            ctypes.c_char_p, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
        libc.sysctlbyname.restype = ctypes.c_int
        rc = libc.sysctlbyname(name.encode(), buf, ctypes.byref(size), None, 0)
        if rc != 0:
            return None
        return buf.value.decode("utf-8", "ignore").rstrip("\x00")
    except Exception:  # noqa: BLE001
        return None


def read_os_release(path: str = "/etc/os-release") -> dict:
    """解析 LSB 风格的 /etc/os-release（FreeBSD/NetBSD 提供）。"""
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k] = v.strip().strip('"').strip("'")
    except OSError:
        return {}
    return out


def _uname() -> dict:
    rc, out = common.run("uname -a 2>/dev/null")
    res = {}
    if rc == 0 and out:
        for m in re.finditer(r"^(\S+)\s+(\S+)\s+(\S+)", out):
            res["sysname"], res["nodename"], res["release"] = m.group(1), m.group(2), m.group(3)
        rc2, vs = common.run("uname -v 2>/dev/null")
        if rc2 == 0:
            res["version"] = vs.strip()
    return res


def detect_distro() -> dict:
    """综合探测 BSD 发行版，返回 {id, version_id, pretty, name, pkg_manager}。"""
    if not _is_bsd():
        # 非 BSD 环境（如被 --platform bsd 手动指定）：诚实降级，不误报 Linux 发行版
        return {"id": "bsd", "version_id": "", "pretty": "(当前非 BSD 环境，以下为通用信息)",
                "name": "BSD", "pkg_manager": pkg_manager()}
    rel = read_os_release()
    if rel:
        base = {
            "id": rel.get("ID", ""),
            "version_id": rel.get("VERSION_ID", ""),
            "pretty": rel.get("PRETTY_NAME", ""),
            "name": rel.get("NAME", ""),
        }
    else:
        # 用 sysctlbyname / uname 兜底
        ostype = sysctl("kern.ostype") or ""
        osrelease = sysctl("kern.osrelease") or ""
        u = _uname()
        id_ = (ostype or u.get("sysname", "")).lower() or "bsd"
        base = {
            "id": id_,
            "version_id": osrelease or u.get("release", ""),
            "pretty": f"{ostype or id_.title()} {osrelease}".strip(),
            "name": ostype or id_.title(),
        }
    base["pkg_manager"] = pkg_manager()
    return base


def pkg_manager() -> str:
    """探测 BSD 包管理器：pkg / pkg_add / pkgin。"""
    for pm in ("pkg", "pkg_add", "pkgin"):
        if shutil.which(pm):
            return pm
    return ""


def disk_usage(path: str = "/") -> dict | None:
    """标准库 shutil.disk_usage 封装。"""
    return common.disk_usage(path)


def pkg_clean(force: bool = False) -> tuple:
    """清理已下载的包缓存，返回 (ok, msg)。按发行版选命令。"""
    if not _is_bsd():
        return False, "当前非 BSD，无法调用包管理清理"
    pm = pkg_manager()
    if pm == "pkg":                       # FreeBSD / DragonFly
        cmd = "pkg clean -y" + (" -a" if force else "")
    elif pm == "pkgin":                   # NetBSD
        cmd = "pkgin clean"
    elif pm == "pkg_add":                 # OpenBSD
        cmd = "pkg_delete -a"             # 仅删无依赖的孤包
    else:
        return False, "未识别的 BSD 包管理器"
    rc, out = common.run(cmd)
    return rc == 0, out


def autoremove() -> tuple:
    """移除不再被需要的依赖，返回 (ok, msg)。"""
    if not _is_bsd():
        return False, "当前非 BSD，无法调用包管理"
    pm = pkg_manager()
    if pm == "pkg":
        cmd = "pkg autoremove -y"
    elif pm == "pkgin":
        cmd = "pkgin autoremove"
    elif pm == "pkg_add":
        cmd = "pkg_delete -a"
    else:
        return False, "未识别的 BSD 包管理器"
    rc, out = common.run(cmd)
    return rc == 0, out


def freebsd_pkg_cache_size() -> str:
    """用 pkg 取缓存占用（仅展示用）。"""
    rc, out = common.run("pkg clean -n 2>/dev/null | tail -1")
    return out if rc == 0 else ""


# --------------------------------------------------------------------------- #
# 文档跟踪层：BSD 各系统接口只读探测（返回 (ok, msg)）。                         #
# 全部只读：仅列出可用接口/版本/配置，不禁用、不删除、不写任何系统项。           #
# 非 BSD 环境工具不存在，优雅返回 (False, 说明)，由上层降级为文档指引。          #
# --------------------------------------------------------------------------- #

def version_report() -> tuple:
    """读 BSD 发行版（detect_distro，只读）。"""
    d = detect_distro()
    if not d.get("pretty") and not d.get("id"):
        return False, "未探测到 BSD 发行版（非 BSD 环境，降级为文档指引）"
    pm = d.get("pkg_manager") or "(未识别)"
    return True, f"{d.get('pretty') or d.get('id')}  包管理器={pm}"


def pkg_report() -> tuple:
    """列已装包/版本/安全（pkg info / version / audit，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，pkg 不可用（降级为文档指引）"
    pm = pkg_manager()
    if not pm:
        return False, "未识别的 BSD 包管理器（pkg/pkgin/pkg_add 均无）"
    lines = [f"包管理器: {pm}"]
    if pm == "pkg":
        rc, out = common.run("pkg info 2>/dev/null | wc -l")
        n = (out or "").strip()
        lines.append(f"   已装包: {n} 个（pkg info）")
        rc2, a = common.run("pkg audit 2>/dev/null | head -10")
        if rc2 == 0 and (a or "").strip():
            lines.append("   安全审计(pkg audit): " + (a or "").strip().splitlines()[0])
        else:
            lines.append("   安全审计(pkg audit): 无已知漏洞")
    elif pm == "pkgin":
        lines.append("   （NetBSD pkgin：pkgin list 查看已装）")
    elif pm == "pkg_add":
        lines.append("   （OpenBSD pkg_add：pkg_info -a 查看已装）")
    return True, "\n".join(lines)


def rc_conf_report() -> tuple:
    """列已启用服务（service -e，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，service 不可用（降级为文档指引）"
    if not shutil.which("service"):
        return False, "未安装 service（FreeBSD 应自带）"
    rc, out = common.run("service -e 2>/dev/null | head -25")
    if rc != 0 or not (out or "").strip():
        return False, "service -e 无输出（可能 OpenBSD，用 rcctl ls started）"
    n = len([l for l in out.splitlines() if l.strip()])
    lines = [f"已启用服务（service -e，前 {n} 项，只读）："]
    for l in out.splitlines()[:10]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def sysctl_report() -> tuple:
    """读 BSD 内核参数（sysctl，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，sysctl 不可用（降级为文档指引）"
    if not shutil.which("sysctl"):
        return False, "未安装 sysctl（BSD 应自带）"
    rc, out = common.run("sysctl -n kern.osrelease hw.ncpu 2>/dev/null")
    if rc != 0 or not (out or "").strip():
        return False, "sysctl 读取失败"
    vals = (out or "").split()
    rel = vals[0] if vals else "?"
    ncpu = vals[1] if len(vals) > 1 else "?"
    return True, f"内核版本={rel}  CPU 核数={ncpu}（sysctl 只读）"


def pf_report() -> tuple:
    """看 pf 规则/状态（pfctl -s，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，pfctl 不可用（降级为文档指引）"
    if not shutil.which("pfctl"):
        return False, "未安装 pfctl（OpenBSD/FreeBSD 防火墙）"
    rc, out = common.run("pfctl -s info 2>&1 | head -12")
    if rc != 0 or not (out or "").strip():
        return False, "pfctl -s info 无输出（可能 pf 未启用）"
    lines = ["pf 状态（pfctl -s info，只读）："]
    for l in out.splitlines()[:6]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def zfs_report() -> tuple:
    """列 ZFS 存储池/数据集（zpool list / zfs list，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，zpool 不可用（降级为文档指引）"
    if not shutil.which("zpool"):
        return False, "未安装 ZFS（zpool），跳过"
    rc, out = common.run("zpool list -H -o name,health,cap 2>/dev/null")
    if rc != 0 or not (out or "").strip():
        return False, "未发现 ZFS 存储池（zpool list 无输出）"
    lines = ["ZFS 存储池（zpool list，只读）："]
    for l in out.splitlines():
        if l.strip():
            p = l.split("\t")
            lines.append(f"   · {p[0] if p else l.strip()}  健康={p[1] if len(p)>1 else ''}  容量={p[2] if len(p)>2 else ''}")
    return True, "\n".join(lines)


def periodic_report() -> tuple:
    """看 periodic 脚本配置（cat periodic.conf / ls 目录，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，periodic 不可用（降级为文档指引）"
    import glob
    dirs = ["/etc/periodic/daily", "/etc/periodic/weekly",
            "/etc/periodic/monthly", "/etc/periodic/security"]
    found = [d for d in dirs if glob.glob(os.path.join(d, "*"))]
    if not found:
        return False, "未发现 /etc/periodic 脚本目录"
    lines = ["periodic 周期脚本（只读）："]
    for d in found:
        n = len(glob.glob(os.path.join(d, "*")))
        lines.append(f"   · {d}: {n} 个脚本")
    if os.path.exists("/etc/periodic.conf"):
        lines.append("   · 存在 /etc/periodic.conf（自定义覆盖）")
    return True, "\n".join(lines)


def bsdconfig_report() -> tuple:
    """探测 bsdconfig 是否可用（which，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，bsdconfig 不可用（降级为文档指引）"
    if not shutil.which("bsdconfig"):
        return False, "未安装 bsdconfig（FreeBSD 控制台配置向导）"
    return True, "bsdconfig 可用（FreeBSD 文本配置向导；进入模块查看即只读）"


def ports_report() -> tuple:
    """清点 ports 缓存（du -sh distfiles，只读）。"""
    if not _is_bsd():
        return False, "非 BSD 环境，ports 不可用（降级为文档指引）"
    if not os.path.isdir("/usr/ports"):
        return False, "未发现 /usr/ports（Ports Collection 未检出）"
    rc, out = common.run("du -sh /usr/ports/distfiles 2>/dev/null")
    if rc == 0 and (out or "").strip():
        return True, "distfiles 缓存：" + (out or "").strip().split()[0] + "（清理用 make distclean）"
    return True, "发现 /usr/ports，但无 distfiles 缓存"


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("version_report", "BSD 发行版（detect_distro / sysctlbyname，只读）"),
    ("pkg_report", "包管理（pkg info / version / audit 只读）"),
    ("rc_conf_report", "开机服务（service -e 只读，禁用改 rc.conf）"),
    ("sysctl_report", "内核参数（sysctl 只读，写需 root）"),
    ("pf_report", "防火墙（pfctl -s 只读）"),
    ("zfs_report", "ZFS 存储池（zpool list 只读）"),
    ("periodic_report", "周期脚本（/etc/periodic 只读）"),
    ("bsdconfig_report", "控制台配置（bsdconfig 可用性）"),
    ("ports_report", "Ports 缓存（distfiles 占用，只读）"),
)


def environment_report() -> list:
    """返回本机 BSD 系统接口可用性概览（✓ 可用 / ✗ 未装/非 BSD）。"""
    lines = ["BSD 系统接口可用性（文档跟踪层）："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def bsd_doc_list() -> list:
    """返回 BSD 接口文档参考清单（供 CLI/GUI 展示）。"""
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
#   · sysctl   : sysctl -w <mib>=<val>（BSD MIB；写前先读，只上调不盲改）
#   · zpool    : zpool set autotrim=on / zpool scrub（OpenZFS 官方子命令）
#   · pfctl    : pfctl -e -f /etc/pf.conf（只启用加载，绝不做 pfctl -d / -F all）
#   · periodic : periodic <daily|weekly|monthly|security>（官方周期脚本入口）
# 关键约束：runner 以 fn() 无参派发，故池名/内存大小/当前值一律自动探测。       #
# --------------------------------------------------------------------------- #

def _sysctl_read(name: str) -> str:
    """读一个 sysctl MIB 的当前值（sysctl -n，只读）。"""
    rc, out = common.run(f"sysctl -n {name} 2>/dev/null")
    return (out or "").strip() if rc == 0 else ""


def _sysctl_write(pairs: list) -> tuple:
    """按官方接口写多个 sysctl（sysctl -w k=v ...），返回 (ok, msg)。"""
    if not _is_bsd():
        return False, "当前非 BSD，sysctl 写接口不可用（降级为文档指引）"
    if not shutil.which("sysctl"):
        return False, "未安装 sysctl（BSD 应自带），跳过"
    args = " ".join(f"{k}={v}" for k, v in pairs)
    rc, out = common.run(f"sysctl -w {args}")
    if rc != 0:
        return False, out or "sysctl -w 写入失败（需 root 权限）"
    return True, out or f"sysctl -w {args}"


def _to_int(text: str, default: int = 0) -> int:
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


def _zpool_names() -> list:
    """列出 ZFS 池名（zpool list -H -o name，只读）。"""
    rc, out = common.run("zpool list -H -o name 2>/dev/null")
    if rc != 0:
        return []
    return [l.strip() for l in (out or "").splitlines() if l.strip()]


def _physmem_bytes() -> int:
    """读物理内存字节数（sysctl -n hw.physmem，只读）。"""
    return _to_int(_sysctl_read("hw.physmem"))


def tcp_rfc1323(on: bool = True) -> tuple:
    """启用 TCP 高性能扩展（sysctl -w net.inet.tcp.rfc1323，RFC 7323）。

    RFC 7323 = 窗口缩放 + 时间戳 + PAWS，长肥管道（高带宽时延积）下吞吐更高。
    """
    if not _is_bsd():
        return False, "当前非 BSD，net.inet.tcp.rfc1323 写接口不可用（降级为文档指引）"
    cur = _sysctl_read("net.inet.tcp.rfc1323")
    if not cur:
        return False, "读取 net.inet.tcp.rfc1323 失败（该 BSD 无此 MIB，跳过）"
    val = "1" if on else "0"
    if cur == val:
        return True, f"net.inet.tcp.rfc1323 已是 {val}，无需改动（RFC 7323）"
    ok, msg = _sysctl_write([("net.inet.tcp.rfc1323", val)])
    return ok, (msg + "（RFC 7323 TCP 高性能扩展：窗口缩放 + 时间戳 + PAWS）" if ok else msg)


def tcp_buffers(recvspace: int = 65536, sendspace: int = 65536) -> tuple:
    """调大 TCP 收发缓冲（sysctl -w net.inet.tcp.recvspace/sendspace）。

    只上调不降低：当前值已大于等于目标时不动，避免覆盖内核自动调优的结果。
    """
    if not _is_bsd():
        return False, "当前非 BSD，TCP 缓冲写接口不可用（降级为文档指引）"
    pairs = []
    for mib, target in (("net.inet.tcp.recvspace", recvspace),
                        ("net.inet.tcp.sendspace", sendspace)):
        cur = _to_int(_sysctl_read(mib), -1)
        if cur < 0:
            return False, f"读取 {mib} 失败（该 BSD 无此 MIB，跳过）"
        if cur < target:
            pairs.append((mib, target))
    if not pairs:
        return True, (f"TCP 缓冲已 >= recvspace={recvspace}/sendspace={sendspace}，"
                      "无需改动（不覆盖内核自动调优）")
    ok, msg = _sysctl_write(pairs)
    return ok, (msg + "（仅上调，未降低任何既有值）" if ok else msg)


def maxfiles(maxfiles: int = 65536, per_proc: int = 32768) -> tuple:
    """调高文件描述符上限（sysctl -w kern.maxfiles/kern.maxfilesperproc）。"""
    if not _is_bsd():
        return False, "当前非 BSD，kern.maxfiles 写接口不可用（降级为文档指引）"
    pairs = []
    for mib, target in (("kern.maxfiles", maxfiles),
                        ("kern.maxfilesperproc", per_proc)):
        cur = _to_int(_sysctl_read(mib), -1)
        if cur < 0:
            return False, f"读取 {mib} 失败（该 BSD 无此 MIB，跳过）"
        if cur < target:
            pairs.append((mib, target))
    if not pairs:
        return True, (f"kern.maxfiles/perproc 已 >= {maxfiles}/{per_proc}，无需改动"
                      "（持久化写 /etc/sysctl.conf）")
    ok, msg = _sysctl_write(pairs)
    return ok, (msg + "（持久化写 /etc/sysctl.conf）" if ok else msg)


def zfs_autotrim() -> tuple:
    """对 ZFS 池开启 autotrim（zpool set autotrim=on <pool>，OpenZFS 官方接口）。"""
    if not _is_bsd():
        return False, "当前非 BSD，zpool 写接口不可用（降级为文档指引）"
    if not shutil.which("zpool"):
        return False, "未安装 ZFS（zpool），跳过"
    pools = _zpool_names()
    if not pools:
        return False, "未发现 ZFS 存储池（zpool list 无输出），跳过"
    done, errs = [], []
    for p in pools:
        rc, out = common.run(f"zpool set autotrim=on {p}")
        (done if rc == 0 else errs).append(p if rc == 0 else f"{p}: {out}")
    if errs and not done:
        return False, "autotrim 设置失败: " + "; ".join(errs)
    msg = f"已开启 autotrim 的池: {', '.join(done)}（OpenZFS 官方接口，SSD 回收空闲块）"
    return True, msg + ("；失败: " + "; ".join(errs) if errs else "")


def zfs_scrub() -> tuple:
    """对 ZFS 池启动 scrub 校验（zpool scrub <pool>，OpenZFS 官方接口）。

    scrub 遍历校验所有块的校验和并自动修复（有冗余时），属官方维护动作，
    但会带来 IO 开销，故为 medium 风险、需 opt-in + --yes。
    """
    if not _is_bsd():
        return False, "当前非 BSD，zpool scrub 不可用（降级为文档指引）"
    if not shutil.which("zpool"):
        return False, "未安装 ZFS（zpool），跳过"
    pools = _zpool_names()
    if not pools:
        return False, "未发现 ZFS 存储池（zpool list 无输出），跳过"
    done, errs = [], []
    for p in pools:
        rc, out = common.run(f"zpool scrub {p}")
        (done if rc == 0 else errs).append(p if rc == 0 else f"{p}: {out}")
    if errs and not done:
        return False, "scrub 启动失败: " + "; ".join(errs)
    msg = f"已启动 scrub 的池: {', '.join(done)}（进度用 zpool status 查看）"
    return True, msg + ("；失败: " + "; ".join(errs) if errs else "")


def zfs_arc_max(fraction: float = 0.5) -> tuple:
    """限制 ZFS ARC 上限（sysctl -w vfs.zfs.arc_max=<bytes>），把内存让给应用。

    目标 = 物理内存 × fraction；仅当未设置（0）或当前上限大于目标时才下调。
    """
    if not _is_bsd():
        return False, "当前非 BSD，vfs.zfs.arc_max 写接口不可用（降级为文档指引）"
    if _sysctl_read("vfs.zfs.arc_max") == "":
        return False, "未加载 ZFS（vfs.zfs.arc_max 不存在），跳过"
    mem = _physmem_bytes()
    if not mem:
        return False, "无法读取 hw.physmem，不敢盲设 ARC 上限，跳过"
    target = int(mem * fraction)
    cur = _to_int(_sysctl_read("vfs.zfs.arc_max"), 0)
    if cur and cur <= target:
        return True, (f"vfs.zfs.arc_max 已是 {cur}（<= 目标 {target}，无需改动；"
                      f"物理内存 {mem} 的 {fraction:.0%}）")
    ok, msg = _sysctl_write([("vfs.zfs.arc_max", target)])
    if not ok:
        return ok, msg
    return True, (f"vfs.zfs.arc_max={target}（物理内存 {mem} 的 {fraction:.0%}，"
                  "给应用/页缓存留出内存）")


def pf_enable(rules: str = "/etc/pf.conf") -> tuple:
    """启用 pf 并加载规则集（pfctl -e -f <rules>，官方写接口；只启用不停用）。"""
    if not _is_bsd():
        return False, "当前非 BSD，pfctl 写接口不可用（降级为文档指引）"
    if not shutil.which("pfctl"):
        return False, "未安装 pfctl（OpenBSD/FreeBSD 防火墙），跳过"
    if not os.path.exists(rules):
        return False, f"规则集 {rules} 不存在，拒绝盲目启用 pf（先写规则再启用）"
    rc, out = common.run(f"pfctl -e -f {rules}")
    if rc != 0:
        low = (out or "").lower()
        if "already" in low:
            return True, f"pf 已处于启用状态，已重新加载 {rules}"
        return False, out or f"pfctl -e -f {rules} 失败（需 root 权限）"
    return True, f"pf 已启用并加载 {rules}（官方接口；本工具绝不做 pfctl -d / -F all）"


def periodic_run(period: str = "daily") -> tuple:
    """手动跑一遍 periodic 维护脚本（periodic <period>，官方入口）。"""
    if period not in ("daily", "weekly", "monthly", "security"):
        return False, f"不支持的周期 {period}（可选 daily/weekly/monthly/security）"
    if not _is_bsd():
        return False, "当前非 BSD，periodic 不可用（降级为文档指引）"
    import glob
    if not shutil.which("periodic") and not any(
            glob.glob(os.path.join(f"/etc/periodic/{period}", "*"))):
        return False, f"未发现 periodic 命令或 /etc/periodic/{period} 脚本，跳过"
    rc, out = common.run(f"periodic {period} 2>/dev/null")
    if rc != 0:
        return False, out or f"periodic {period} 执行失败（需 root 权限）"
    return True, f"periodic {period} 已执行（官方周期维护脚本，输出见系统日志）"


# 官方写接口清单（仅用于展示，**不在展示时调用**——调用即写系统）。
# 每项：(函数名, 官方写子命令说明)
TUNES = (
    ("tcp_rfc1323", "sysctl -w net.inet.tcp.rfc1323=1（RFC 7323 窗口缩放 + 时间戳 + PAWS）"),
    ("tcp_buffers", "sysctl -w net.inet.tcp.recvspace/sendspace（只上调，不覆盖内核自动调优）"),
    ("maxfiles", "sysctl -w kern.maxfiles / kern.maxfilesperproc（提文件描述符上限）"),
    ("zfs_autotrim", "zpool set autotrim=on <pool>（OpenZFS 官方：SSD 空闲块自动回收）"),
    ("zfs_scrub", "zpool scrub <pool>（OpenZFS 官方校验，进度 zpool status 查看）"),
    ("zfs_arc_max", "sysctl -w vfs.zfs.arc_max=<物理内存×50%>（把内存让给应用）"),
    ("pf_enable", "pfctl -e -f /etc/pf.conf（启用 pf 并加载规则集，只启不停）"),
    ("periodic_run", "periodic daily（官方周期维护脚本入口）"),
)


def bsd_tune_list() -> list:
    """返回 BSD 官方写接口（深度调优）清单，供 CLI/GUI 展示。只读展示，不执行。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
